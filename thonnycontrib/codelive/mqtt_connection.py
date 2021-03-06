import json
import os
import random
import string
import sys
import time
import uuid
import copy
import threading

import tkinter as tk
import paho.mqtt.client as mqtt_client
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.subscribe as mqtt_subscribe

import thonnycontrib.codelive.utils as utils
import thonnycontrib.codelive.client as thonny_client

from thonnycontrib.codelive.user import UserDecoder, UserEncoder
from thonny import get_workbench

WORKBENCH = get_workbench()

BROKER_URLS = [
    "test.mosquitto.org",
    "mqtt.eclipse.org",
    "broker.hivemq.com",
    "mqtt.fluux.io",
    "broker.emqx.io",
]

USER_COLORS = ["blue", "green", "red", "pink", "orange", "black", "white", "purple"]
SINGLE_PUBLISH_HEADER = b"CODELIVE_MSG:"

def broker_exists(broker):
    try:
        temp_client = mqtt_client.Client()
        temp_client.connect(host=broker)
        temp_client.disconnect()
        return True
    except Exception as e:
        return False

def topic_exists(topic, broker = "test.mosquitto.org", timeout = 4, broker_check = True):
    if broker_check and not broker_exists(broker):
        raise ValueError("Error: Unable to connect to broker.")

    my_id = -1
    reply_url = str(uuid.uuid4())

    greeting = {
        "id": my_id,
        "instr": {"type": "exist", "name": "Ablf3brhwb", "reply": reply_url},
    }
    MqttConnection.single_publish(
        topic, payload=json.dumps(greeting), hostname=broker
    )

    payload = MqttConnection.single_subscribe(
        topic + "/" + reply_url, hostname=broker, timeout= timeout
    )

    return payload != None


def generate_topic(broker = None, num_trials = 4):
    existing_names = set()

    for i in range(num_trials):
        name = "_".join(
            [USER_COLORS[random.randint(0, len(USER_COLORS) - 1)] for _ in range(4)]
        )
        name += ":" + "".join([str(random.randint(0, 9)) for _ in range(4)])

        if name in existing_names:
            continue

        if topic_exists(name, broker, 1):
            print("Topic %s is taken. Trying another random name..." % repr(name))
            existing_names.add(name)
        else:
            return name

    raise TimeoutError("Timeout: Unable to generate a free topic in the specified number of trials.")

def get_sender_id(json_msg):
    return json_msg["id"]


def get_instr(json_msg):
    return json_msg["instr"]


def get_unique_code(json_msg):
    return json_msg["unique_code"]


def get_id_assigned(json_msg):
    return json_msg["id_assigned"]


def need_id(my_id):
    min_valid_id = 0
    if isinstance(my_id, int) and my_id < min_valid_id:
        return True
    return False


def test_broker(url):
    client = mqtt_client.Client()
    try:
        # it seems as if keepalive only takes integers
        client.connect(url, 1883, 1)
        return True
    except Exception:
        return False


def get_default_broker():
    global BROKER_URLS

    for broker in BROKER_URLS:
        if test_broker(broker):
            return broker

    return None


def assign_broker(broker_url=None):
    if test_broker(broker_url):
        return broker_url
    else:
        return get_default_broker()


class MqttConnection(mqtt_client.Client):
    _single_msg = None

    def __init__(
        self,
        session,
        topic,
        broker_url,
        port=None,
        qos=0,
        delay=1.0,
        on_message=None,
        on_publish=None,
        on_connect=None,
    ):

        mqtt_client.Client.__init__(self)
        self.session = session  # can access current ID of client
        self.broker = assign_broker(
            broker_url
        )  # TODO: Handle assign_broker returning none
        self.port = port or self.get_port()
        self.qos = qos
        self.delay = delay
        self.topic = topic
        self.assigned_ids = dict()  # for handshake

    @classmethod
    def single_publish(cls, topic, payload, hostname):
        msg = SINGLE_PUBLISH_HEADER + bytes(payload, "utf-8")
        mqtt_publish.single(topic, payload=msg, hostname=hostname)

    @classmethod
    def single_subscribe(cls, topic, hostname, timeout=None):
        """
        A substitute for paho.mqtt.subscribe.simple. Adds a timeout to messages.

        if timeout is not provided, regular subscribe.simple command will be used
        """
        if timeout == None:
            return mqtt_subscribe.simple(topic, hostname=hostname).payload

        _lock = threading.Lock()

        def is_valid(msg):
            if msg.topic != topic:
                return False

            _msg = msg.payload

            return (
                len(_msg) >= len(SINGLE_PUBLISH_HEADER)
                and _msg[: len(SINGLE_PUBLISH_HEADER)] == SINGLE_PUBLISH_HEADER
            )

        def on_message(client, data, _msg):
            if is_valid(_msg):
                with _lock:
                    cls._single_msg = _msg.payload[len(SINGLE_PUBLISH_HEADER) :]

        temp_client = mqtt_client.Client()
        temp_client.on_message = on_message

        temp_client.connect(host=hostname)
        temp_client.loop_start()
        temp_client.subscribe(topic)

        # block as long as the message is None and time hasn't run out
        start_time = time.perf_counter()
        wait = True
        while wait:
            with _lock:
                wait = cls._single_msg == None
            wait = wait and time.perf_counter() - start_time < timeout

        # clean up
        temp_client.loop_stop()
        temp_client.disconnect()

        copy_msg = copy.deepcopy(cls._single_msg)
        cls._single_msg = None

        return copy_msg

    def get_port(self):
        return 1883

    def on_message(self, client, data, msg):
        if msg.topic == self.topic + "/" + str(self.session.user_id):
            self.addressed_msg(msg.payload)

        if msg.topic != self.topic:
            return
        
        json_msg = ""
        if len(msg.payload) >= len(SINGLE_PUBLISH_HEADER) and msg.payload[: len(SINGLE_PUBLISH_HEADER)] == SINGLE_PUBLISH_HEADER:
            msg.payload = msg.payload[len(SINGLE_PUBLISH_HEADER):]
            
        json_msg = json.loads(msg.payload, cls=UserDecoder)
        if self.session._debug:
            print(json_msg)
        try:
            sender_id = get_sender_id(json_msg)
            instr = get_instr(json_msg)
        except:
            print("WARNING: missing instr/sender id")

        if sender_id == self.session.user_id:
            if self.session._debug:
                print("instr ignored")
            return

        elif instr["type"] == "exist" and self.session.is_host:
            self.respond_to_exist(instr["reply"])

        # on edit
        elif instr["type"] in ("I", "D", "S", "M"):
            WORKBENCH.event_generate("RemoteChange", change=instr)

        # On new user signal only sent by host
        elif instr["type"] == "new_join":
            if instr["user"].id != self.session.user_id:
                self.session.add_user(instr["user"])

    def publish(self, msg=None, id_assignment=None, unique_code=None):
        send_msg = {
            "id": self.session.user_id,
            "instr": msg,
            "unique_code": unique_code,
            "id_assigned": id_assignment,
        }
        mqtt_client.Client.publish(
            self, self.topic, payload=json.dumps(send_msg, cls=UserEncoder)
        )

    def respond_to_exist(self,reply_url):
        MqttConnection.single_publish(
            self.topic + "/" + reply_url,
            payload="True",
            hostname=self.broker,
        )

    def addressed_msg(self, msg):
        if self.session._debug:
            print("in addressed")
        json_msg = json.loads(msg, cls=UserDecoder)

        instr = json_msg["instr"]
        if self.session.is_host and instr["type"] == "success":
            user = instr["user"]
            self.session.add_user_host(user)

    def Connect(self):
        mqtt_client.Client.connect(self, self.broker, self.port, 60)
        mqtt_client.Client.subscribe(self, self.topic, qos=self.qos)

        if self.session.is_host:
            mqtt_client.Client.subscribe(
                self, self.topic + "/" + str(self.session.user_id), qos=self.qos
            )

        self.loop_start()

    def Disconnect(self):
        self.unsubscribe(self.topic)
        self.unsubscribe(self.topic + "/" + str(self.session.user_id))
        self.loop_stop()
        self.disconnect()

    def get_sender(self, msg):
        pass


if __name__ == "__main__":
    import sys
    import pprint

    class Session_temp:
        def __init__(self, name="John Doe", _id=None, is_host=True):
            self.username = name
            self.user_id = _id or utils.get_new_id()
            self.is_host = is_host

        def get_docs(self):
            return {
                1: {"title": "doc1", "content": "Hello World 1"},
                2: {"title": "doc2", "content": "Hello World 2"},
                3: {"title": "doc3", "content": "Hello World 2"},
            }

        def get_active_users(self, in_json=True):
            return {1: "user1", 2: "user2", 3: "user3"}

    def test_handshake():
        temp_topic = "codelive_handshake_test/" + generate_topic()
        temp_broker = assign_broker()

        x = Session_temp()

        myConnection = MqttConnection(x, topic=temp_topic, broker_url = temp_broker)
        myConnection.Connect()
        myConnection.loop_start()

        while True:
            x = input("Press enter for handshake...")
            response = MqttConnection.handshake("Jane Doe", temp_topic, temp_broker)
            p = pprint.PrettyPrinter(4)
            p.pprint(response)

    test_topic = "test_topic"
    test_broker = "test.mosquitto.org"
    test_text = "Hello"
    test_timeout = 10

    def test_single_publish():
        MqttConnection.single_publish(test_topic, test_text, test_broker)

    def test_single_subscribe():
        payload = MqttConnection.single_subscribe(test_topic, test_broker, test_timeout)
        print(payload)

    if sys.argv[1] == "handshake":
        test_handshake()

    if sys.argv[1] == "s_pub":
        test_single_publish()

    if sys.argv[1] == "s_sub":
        test_single_subscribe()
