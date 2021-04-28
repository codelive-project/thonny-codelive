import json
import uuid
import random
import paho.mqtt.client as mqtt_client
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.subscribe as mqtt_subscribe
import tkinter as tk

from thonny import get_workbench

from thonnycontrib.codelive.user import UserDecoder, UserEncoder
import thonnycontrib.codelive.mqtt_connection as mqttc


def get_sender_id(json_msg):
    return json_msg["id"]


def get_instr(json_msg):
    return json_msg["instr"]

SINGLE_PUBLISH_HEADER = b"CODELIVE_MSG:"


class MqttUserManagement(mqtt_client.Client):
    def __init__(
        self,
        session,
        broker_url,
        port,
        qos,
        delay,
        topic,
        on_message=None,
        on_publish=None,
        on_connect=None,
    ):
        mqtt_client.Client.__init__(self)
        self.session = session
        self.broker = broker_url
        self.port = port
        self.qos = qos
        self.delay = delay
        self.main_topic = topic
        self.users_topic = topic + "/" + "UserManagement"
        self.reply_topic = None
        self.my_id_topic = self.users_topic + "/" + str(self.session.user_id)
        self.exit_topic = self.users_topic + "/" + "UserExitHandling"


    def Connect(self):
        last_will_msg = {
            "id": self.session.user_id,
            "instr": {"type": "lastWillExit", "new_host": None},
        }
        mqtt_client.Client.will_set(self, self.users_topic, json.dumps(last_will_msg), 1, True)
        mqtt_client.Client.connect(self, self.broker, self.port, 60)
        mqtt_client.Client.subscribe(self, self.users_topic, qos=self.qos)
        mqtt_client.Client.subscribe(self, self.my_id_topic, qos=self.qos)

        self.loop_start()

    def Disconnect(self):
        self.unsubscribe([self.users_topic, self.my_id_topic])
        self.loop_stop()
        self.disconnect()

    def on_message(self, client, data, msg):
        json_msg = ""
        if len(msg.payload) >= len(SINGLE_PUBLISH_HEADER) and msg.payload[: len(SINGLE_PUBLISH_HEADER)] == SINGLE_PUBLISH_HEADER:
            msg.payload = msg.payload[len(SINGLE_PUBLISH_HEADER):]
        
        try:
            json_msg = json.loads(msg.payload,cls=UserDecoder)
        except Exception:
            return
        sender_id = get_sender_id(json_msg)

        if sender_id == self.session.user_id:
            return
        
        print(json_msg)
        if msg.topic == self.reply_topic:
            self.handle_reply(json_msg)
        elif msg.topic == self.my_id_topic:
            self.handle_addressed(json_msg)
        elif msg.topic == self.users_topic:
            self.handle_general(json_msg)

    @classmethod
    def handshake(cls, name, topic, broker):
        retries = 0

        while retries < 5:
            response = cls._handshake_helper(name, topic + "/" + "UserManagement", broker)
            if response == None:
                # show message
                resp = tk.messagebox.askyesno(
                    master=WORKBENCH,
                    title="Join Attempt Failed",
                    message="Failed to connect to session host. Do you want to try again?",
                )
                if resp == "no":
                    break
            else:
                return response
            retries += 1

        return None

    @classmethod
    def _handshake_helper(cls, name, topic, broker):

        my_id = random.randint(-1000, -1)
        reply_url = str(uuid.uuid4())

        greeting = {
            "id": my_id,
            "instr": {"type": "join", "name": name, "reply": reply_url},
        }

        mqttc.MqttConnection.single_publish(
            topic, payload=json.dumps(greeting), hostname=broker
        )
        payload = mqttc.MqttConnection.single_subscribe(
            topic + "/" + reply_url, hostname=broker, timeout=4
        )
        response = json.loads(payload, cls=UserDecoder)
        return response

    def respond_to_handshake(self, sender_id, reply_url, name):
        assigned_id = self.session.get_new_user_id()

        def get_unique_name(_name):
            name_list = [user.name for user in self.session.get_active_users(False)]
            if _name not in name_list:
                return _name

            else:
                return "%s (%d)" % (_name, assigned_id)

        message = {
            "id": self.session.user_id,
            "name": get_unique_name(name),
            "id_assigned": assigned_id,
            "docs": self.session.get_docs(),
            "users": self.session.get_active_users(False),
        }
        mqttc.MqttConnection.single_publish(
            self.users_topic + "/" + reply_url,
            payload=json.dumps(message, cls=UserEncoder),
            hostname=self.broker,
        )

    def handle_reply(self, json_msg):
        message = ""
        instr = get_instr(json_msg)
        print(json_msg)
        if instr["approved"]:
            if instr["type"] == "request_control":
                self.session.change_host(self.session.user_id)
            else:
                self.session.change_host(json_msg["id"])
            message = "Granted"
        else:
            message = "Denied"
        tk.messagebox.showinfo(
            parent=get_workbench(),
            title="Control Request",
            message="Control Request " + message,
        )
        mqtt_client.Client.unsubscribe(self, self.reply_topic)
        self.reply_topic = None

    def handle_addressed(self, json_msg):
        approve = False

        instr = get_instr(json_msg)
        if self.session.is_host and instr["type"] == "success":
            user = instr["user"]
            self.session.add_user_host(user)

        if instr["type"] == "request_control":
            approve = tk.messagebox.askokcancel(
                parent=get_workbench(),
                title="Control Request",
                message="Make " + instr["name"] + " host?",
            )  # add a timeout on this?
            self.respond_to_request(json_msg, approve)

        if instr["type"] == "request_give":
            approve = tk.messagebox.askokcancel(
                parent=get_workbench(),
                title="Control Request",
                message="Accept host-handoff from " + instr["name"] + "?",
            )  # add a timeout on this?
            self.respond_to_give(json_msg, approve)

        if approve:
            self.session.change_host(
                self.session.user_id
                if instr["type"] == "request_give"
                else json_msg["id"]
            )

    def handle_general(self, json_msg):
        instr = get_instr(json_msg)
        if instr["type"] == "join" and self.session.is_host:
            self.respond_to_handshake(get_sender_id(json_msg), instr["reply"], instr["name"])
        elif instr["type"] == "leave":
            self.session.remote_leave(json_msg)
        elif instr["type"] == "end":
            self.session.remote_end(json_msg)
        elif instr['type'] == "lastWillExit":
            self.last_will_exit(json_msg)

    def last_will_exit(self, json_msg):
        print(json_msg["id"], self.session.get_driver()[0])
        if json_msg["id"] == self.session.get_driver()[0]:
            new_host = self.session.nominate_host()
            json_msg['instr']['new_host'] = new_host
            print(json_msg)
        self.session.remote_leave(json_msg)


    def request_give(self, targetID):
        if targetID not in self.session._users or targetID == self.session.user_id:
            return 3
        if self.reply_topic:  # cleanup
            mqtt_client.Client.unsubscribe(self, self.reply_topic)
        self.reply_topic = self.users_topic + "/" + str(uuid.uuid4())
        request = {
            "id": self.session.user_id,
            "instr": {"type": "request_give", "name": self.session.username, "reply": self.reply_topic}
        }
        mqtt_client.Client.subscribe(self, self.reply_topic, qos=self.qos)
        mqttc.MqttConnection.single_publish(
            self.users_topic + "/" + str(targetID), json.dumps(request), self.broker
        )

    def respond_to_give(self, json_msg, approved):
        response = {
            "id": self.session.user_id,
            "instr": {"type": "request_give", "approved": approved}
        }
        instr = get_instr(json_msg)
        mqttc.MqttConnection.single_publish(
            instr["reply"], json.dumps(response), self.broker
        )

    def request_control(self):
        host_id, host_name = self.session.get_driver()
        if host_id in {-1, self.session.user_id}:
            return 3
        if self.reply_topic:  # cleanup
            mqtt_client.Client.unsubscribe(self, self.reply_topic)
        self.reply_topic = self.users_topic + "/" + str(uuid.uuid4())

        request = {
            "id": self.session.user_id,
            "instr": {"name": self.session.username, "type": "request_control", "reply": self.reply_topic}
        }

        mqtt_client.Client.subscribe(self, self.reply_topic, qos=self.qos)
        mqttc.MqttConnection.single_publish(
            self.users_topic + "/" + str(host_id), json.dumps(request), self.broker
        )

    def respond_to_request(self, json_msg, approved):
        response = {
            "id": self.session.user_id,
            "instr": {"type": "request_control", "approved": approved}
        }
        instr = get_instr(json_msg)
        mqttc.MqttConnection.single_publish(
            instr["reply"], payload=json.dumps(response), hostname=self.broker
        )

    def announce_leave(self):
        leave = {
            "id": self.session.user_id,
            "instr": {"type": "leave", "new_host": None}
        }

        if self.session.is_host:
            leave["instr"]["new_host"] = self.session.nominate_host()
        mqttc.MqttConnection.single_publish(
            self.users_topic, json.dumps(leave), self.broker
        )

    def announce_end(self):
        if not self.session.is_host:
            raise ValueError("Only hosts are allowed to end sessions")
        end = {
            "id": self.session.user_id,
            "instr": {"type": "end"}
        }
        mqttc.MqttConnection.single_publish(
            self.users_topic, json.dumps(end), self.broker
        )

    def announce_active(self): #FIX to new formatted json
        instr = dict()

        instr["type"] = "A"
        instr["id"] = self.session.user_id
        instr["is_host"] = self.session.is_host

        mqttc.MqttConnection.single_publish(self.users_topic, instr, self.broker)
        if self.session.is_host:
            self.announce_host()

    def announce_host(self):
        instr = "codelive-active"  # replace with a unique hash
        mqttc.MqttConnection.single_publish(self.users_topic, instr, self.broker)
