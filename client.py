import copy
import json
import os
import queue
import random
import re
import sys
import threading
import time
import tkinter as tk
import types

from thonny import get_workbench
from thonny.tktextext import EnhancedText

import thonny.plugins.codelive.patched_callbacks as pc
import thonny.plugins.codelive.mqtt_connection as cmqtt
import thonny.plugins.codelive.utils as utils
import thonny.plugins.codelive.user_management as userManMqtt

from thonny.plugins.codelive.user import User, UserEncoder, UserDecoder
from thonny.plugins.codelive.views.session_status.dialog import SessionDialog
from thonny.ui_utils import select_sequence

MSGLEN = 2048

WORKBENCH = get_workbench()
DEBUG = False

class Session:

    def __init__(self,
                 is_host,
                 _id = -1,
                 name = None,
                 topic = None,
                 broker = None,
                 shared_editors = None,
                 users = None,
                 debug = DEBUG):
        self._debug = debug
        self._users = users if users else dict()
        self.username = name if name != None else ("Host" if is_host else "Client")
        self.user_id = _id
        if _id == -1:
            if is_host == True:
                self.user_id = 0
            else:
                raise ValueError("Please provide id")
        self._bind_hashes = {}

        # UI handles
        self._editor_notebook = WORKBENCH.get_editor_notebook()
        self._shared_editors = {"id_first": dict(), "ed_first": dict(), "txt_first": dict()} \
                                    if shared_editors == None \
                                    else self._enumerate_s_ed(shared_editors)

        # Network handles
        self._connection = cmqtt.MqttConnection(self, broker_url=broker, topic = topic)
        self._network_lock = threading.Lock()

        # client privilage flags
        self.is_host = is_host

        self.user_man = \
            userManMqtt.MqttUserManagement(self._connection.session,
                                           self._connection.broker,
                                           self._connection.port,
                                           self._connection.qos,
                                           self._connection.delay,
                                           self._connection.topic)

        # service threads
        # self._cursor_blink_thread = threading.Thread(target=self._cursor_blink, daemon=True)
        
        # bindings
        self.bind_all(debug)

        self.initialized = False
        
        self._default_insert = None
        self._defualt_delete = None
        
        self.replace_insert_delete()
        self._add_self(is_host)

        if is_host:
            self.enable_editing()
        else:
            self.disable_editing()
        
        self.dialog = SessionDialog(WORKBENCH, self)

    @classmethod
    def create_session(cls, name, topic, broker = None, shared_editors = None, debug = False):
        return Session(name = name,
                       topic = topic,
                       broker = broker or cmqtt.get_default_broker(),
                       shared_editors = shared_editors,
                       is_host = True)

    @classmethod
    def join_session(cls, name, topic, broker, debug = False):
        current_state = cmqtt.MqttConnection.handshake(name, topic, broker)
        if debug:
           print(current_state)
        shared_editors = utils.intiialize_documents(current_state["docs"])
        users = {user.id : user for user in current_state["users"]}

        return Session(is_host= False,
                       _id = current_state["id_assigned"],
                       name = current_state["name"],
                       topic = topic,
                       broker = broker,
                       users = users,
                       shared_editors = shared_editors)
    
    def bind_event(self, widget, seq, handler, override = True, debug = False):
        if debug:
            print("Binding Widget: %s to seq: %s..." % (str(widget), str(seq)))
        binding = None
        if widget == get_workbench():
            widget.bind(seq, handler, override)
            binding = {"handler": handler, 
                       "seq": seq}
            if "workbench" in self._bind_hashes:
                self._bind_hashes["workbench"].append(binding)
            else:
                self._bind_hashes["workbench"] = [binding]
        else:
            binding = {"id": widget.bind(seq, handler, override), 
                       "seq": seq}
            if widget in self._bind_hashes:
                self._bind_hashes[widget].append(binding)
            else:
                self._bind_hashes[widget] = [binding]

        if debug:
            print("  Done.")

    def bind_locals(self, debug = False):
        '''
        Bind keypress binds the events from components with callbacks. The function keys 
        associated with the bindings are returned as values of a dictionary whose keys are string of
        the event sequence and the widget's name separated by a "|"

        If the event is bound to a widget, the name of the widget is "editor_<the editor's assigned id>". 
        '''
        for widget in self._shared_editors["txt_first"]:
            self.bind_event(widget, "<KeyPress>", self.broadcast_keypress, True, debug)
        
        self.bind_event(get_workbench(), "LocalInsert", self.broadcast_insert, True, debug)
        self.bind_event(get_workbench(), "LocalDelete", self.broadcast_delete, True, debug)

    def bind_cursor_callbacks(self, debug = False):
        seqs = [
            "<KeyRelease-Left>",
            "<KeyRelease-Right>",
            "<KeyRelease-Up>",
            "<KeyRelease-Down>",
            "<KeyRelease-Return>",
            "<ButtonRelease-1>",
        ]
        if debug:
            print("Binding Special keys...")
        for text_widget in self._shared_editors["txt_first"]:
            for seq in seqs:
                self.bind_event(text_widget, seq, self.boradcast_cursor_motion, True, debug)
        if debug:
            print("Done")

    def bind_special_keys(self, debug = False):
        seqs = [
            "<KeyRelease-Meta_L>",
            "<KeyRelease-Super_L>",
            "<KeyRelease-Control_L>",
            "<KeyRelease-Alt_L>",
            select_sequence("<Control-s>", "<Command-s>"),
            select_sequence("<Control-x>", "<Command-x>"),
            select_sequence("<Control-z>", "<Command-z>"),
            select_sequence("<Control-v>", "<Command-v>"),
            select_sequence("<Control-Shift-z>", "<Command-Shift-z>"),
        ]

        for text_widget in self._shared_editors["txt_first"]:
            for seq in seqs:
                self.bind_event(text_widget, seq, self.handle_special_keys, True, debug)

    def bind_all(self, debug = False):
        if debug:
            print("Binding All events")
        self.bind_event(WORKBENCH, "RemoteChange", self.apply_remote_changes, True, debug)
        self.bind_event(WORKBENCH, "MakeDriver", self.request_give, True, debug)
        self.bind_locals(debug)
        self.bind_cursor_callbacks(debug)
        self.bind_special_keys(debug)
        if debug:
            print("Done")

    def unbind_all(self, debug = False):
        if debug:
            print("Unbinding all events...")
        def unbind_workbench():
            wb = get_workbench()
            for binding in self._bind_hashes["workbench"]:
                if debug:
                    print("\t > Unbinding:", binding["seq"], end = "... ")
                wb.unbind(binding["seq"], binding["handler"])
                if debug:
                    print("Done")

            del self._bind_hashes["workbench"]
    
        def unbind_others(widget):
            for binding in self._bind_hashes[widget]:
                if debug:
                    print("\t > Unbinding:", binding["seq"], end = "... ")
                widget.unbind(binding["seq"], binding["id"])
                if debug:
                    print("Done")

            del self._bind_hashes[widget]

        for widget in list(self._bind_hashes.keys()):
            if debug:
                print("   Unbinding widget:", widget)
            if widget == "workbench":
                unbind_workbench()
            else:
                unbind_others(widget)
            if debug:
                print("\t Done")
        if debug:
            print("Done")
    
    def _add_self(self, is_host):
        current_doc = min(self._shared_editors["id_first"])
        me = User(self.user_id, self.username, current_doc, is_host= is_host)
        self._users[self.user_id] = me

        # if not host notify host that you joined
        if not is_host:
            success_message = {
                "id": self.user_id,
                "instr": {
                    "type": "success",
                    "user": me
                }
            }
            cmqtt.MqttConnection.single_publish(self._connection.topic + "/" + str(self.get_driver()[0]),
                                                json.dumps(success_message, cls = UserEncoder),
                                                hostname= self._connection.broker)

    def add_user(self, user):
        self._users[user.id] = user
        self.dialog.add_user(user)
    
    def add_user_host(self, user):
        self.add_user(user)
        msg = {
            "type": "new_join",
            "user": user
        }

        self.send(msg)

    def request_control(self):
        '''
        Requests control from the host

        On success, returns 0
        On rejection, returns 1
        On timeout, returns 2
        In a general error, returns 3, and error object
        '''
        self.user_man.request_control()
        return 0

    def request_give(self, event):
        self.user_man.request_give(event.user)
        return 0

    def leave(self):
        '''
        Attempts to leave the session

        On success, returns 0
        On failure, returns 1
        '''
        pass

    def end(self):
        '''
        Attempts to end the session (only available to acting hosts)

        On success, returns 0;
        On failure, returns 1
        '''
        if not self.is_host:
            return 1
        
        pass

    def _enumerate_s_ed(self, shared_editors):
        id_f = {i : editor for (i , editor) in enumerate(shared_editors)}
        ed_f = {editor: i for (i, editor) in id_f.items()}
        tex_f = {editor.get_text_widget() : editor for editor in ed_f}
        return {
            "id_first": id_f,
            "ed_first": ed_f,
            "txt_first": tex_f
        }

    def editor_from_id(self, _id):
        return self._shared_editors["id_first"][_id]
    
    def text_widget_from_id(self, _id):
        return self.editor_from_id(_id).get_text_widget()

    def id_from_editor(self, editor):
        return self._shared_editors["ed_first"][editor]

    def editor_from_text(self, widget):
        return self._shared_editors["txt_first"][widget]
    
    def e_id_from_text(self, widget):
        return self.id_from_editor(self.editor_from_text(widget))

    def get_new_doc_id(self):
        if self._shared_editors == None:
            return 0
        else:
            existing = sorted(self._shared_editors["id_first"].keys())
            for i in range(len(existing)):
                if i != existing[i]:
                    return i
            return len(existing)
    
    def get_new_user_id(self):
        if self._users == None:
            return 0
        else:
            existing = sorted(self._users.keys())
            for i in range(len(existing)):
                if i != existing[i]:
                    return i
            return len(existing)

    def get_docs(self):
        json_form = dict()
        for editor in self._shared_editors["ed_first"]:
            content = editor.get_text_widget().get("0.0", tk.END)
            # remove needles \n at the end of file
            if len(content) >= 1:
                content = content[: -1]

            temp = {"title": editor.get_title(),
                    "content": content}
            json_form[self.id_from_editor(editor)] = temp
        
        return json_form
    
    def get_active_users(self, in_json = False):
        if in_json == False:
            return list(self._users.values())
        
        return json.dumps((self._users.values()), cls = UserEncoder)

    def replace_insert_delete(self):
        defn_saved = False

        for widget in self._shared_editors["txt_first"]:
            if not defn_saved:
                self._default_insert = widget.insert
                self._default_delete = widget.delete
                defn_saved = True
            
            widget.insert = types.MethodType(pc.patched_insert, widget)
            widget.delete = types.MethodType(pc.patched_delete, widget)
    
    def _cursor_blink(self):
        '''
        Runs of a daemon thread to show a remote user's pseudo-cursor...
        '''
        while True:
            time.sleep(0.5)
            text_widget = self._editor_notebook.get_current_editor().get_text_widget()

            for i in text_widget.tag_names():
                if i != str(self.user_id) and i in self._users:
                    if self._users[i].cursor_colored:
                        text_widget.tag_config(i, background="white")
                        self._users[i].cursor_colored = False
                    else:
                        text_widget.tag_config(i, background=self._users[i].color)
                        self._users[i].cursor_colored = True

    def send(self, msg = None):
        self._connection.publish(msg)

    def boradcast_cursor_motion(self, event):
        if event.widget.is_read_only():
            return

        editor_id = self.e_id_from_text(event.widget)
        instr = {
            "type": "M",
            "user": self.user_id,
            "user_pos": event.widget.index(tk.INSERT),
            "doc": editor_id
        }
        self.send(instr)
    
    def handle_special_keys(self, event):
        SYNC_DELAY_MS = 1000
        text_widget = event.widget
        
        if text_widget.is_read_only():
            return
        
        _id = self.e_id_from_text(event.widget)
        
        WORKBENCH.after(SYNC_DELAY_MS, self.sync_docs, _id)

    def broadcast_insert(self, event):
        editor = WORKBENCH.get_editor_notebook().get_current_editor()
        editor_id = self.id_from_editor(editor)
        instr = utils.get_latent_instr(event, editor_id, True, user_id = self.user_id)

        if instr == None:
            return

        if self._debug:
            print("*****************\nSending: %s\n*****************" % repr(instr))
        self.send(instr)

    def broadcast_delete(self, event):
        editor = WORKBENCH.get_editor_notebook().get_current_editor()
        editor_id = self.id_from_editor(editor)
        instr = utils.get_latent_instr(event, editor_id, False, user_id = self.user_id)

        if instr == None:
            return
        
        if self._debug:
            print("*****************\nSending: %s\n*****************" % repr(instr))
        
        self.send(instr)

    def broadcast_keypress(self, event):
        text_widget = event.widget
        
        if text_widget.is_read_only():
            text_widget.bell()
            return
        
        sel_start = text_widget.index(tk.INSERT)
        editor_id = self.e_id_from_text(event.widget)

        # if text was selected, delete the selection before inserting
        if text_widget.tag_ranges("sel"):
            sel_start = text_widget.index("sel.first")
            sel_end = text_widget.index("sel.last")

            del_instr = utils.del_selection_instr(sel_start, sel_end, editor_id, self.user_id, self._debug)
            if self._debug:
                print("Deleting selection")
            self.send(del_instr)
        
        instr = utils.get_direct_instr(event, editor_id, self.user_id, 
                                sel_start, False)
        
        if instr == None:
            return

        if self._debug:
            print("in broadcast: -%s-" % instr)

        self.send(instr)

    def enable_editing(self):
        for text_widget in self._shared_editors["txt_first"]:
            text_widget.set_read_only(False)

    def disable_editing(self):
        for text_widget in self._shared_editors["txt_first"]:
            text_widget.set_read_only(True)

    def get_connection_info(self):
        return {"name" : self.username,
                "broker" : self._connection.broker,
                "topic" : self._connection.topic}
    
    def get_driver(self):
        if self.is_host:
            return self.user_id, self._users[self.user_id].name
        
        else:
            for i in self._users:
                if self._users[i].is_host == True:
                    return i, self._users[i].name
        
        return -1, "null"
    
    def sync_docs(self, _id):
        text_widget = self.text_widget_from_id(_id)
        instr = utils.get_sync_instr(text_widget, _id, self.user_id,
                                     text_widget.index(tk.INSERT), self._debug)
        
        if instr == None:
            return

        if self._debug:
            print("in broadcast: -%s-" % instr)

        self.send(instr)

    def change_host(self, user_id = None):
        if user_id == self.user_id:
            self.be_host()
        elif self.is_host:
            self.be_copilot(user_id)
        elif user_id != None:
            self.other_host(user_id)
        else:
            print("Err: ", user_id, "is not a valid input")

    def be_host(self):
        _id, _ = self.get_driver()

        self.enable_editing()

        self._users[_id].is_host = False 
        self.is_host = self._users[self.user_id].is_host = True

        self.dialog.update_host(self.user_id)

    def be_copilot(self, new_host_id = None):
        self.disable_editing()

        if new_host_id != None:
            self._users[new_host_id].is_host = True 
        self.is_host = self._users[self.user_id].is_host = False

        self.dialog.update_host(new_host_id)

    def other_host(self, new_host_id):
        _id, _ = self.get_driver()

        if _id == new_host_id:
            return

        self._users[_id].is_host = False 
        self._users[new_host_id].is_host = True

        self.dialog.update_host(new_host_id)

    def get_name(self, _id):
        print(self._users[_id].name)
        return self._users[_id].name

    def get_users(self):
        return self._users
    
    def apply_remote_changes(self, event):
        '''
        WARNING: We don't expect the host (driver) to be getting ANY remote changes. So, we only expect 
        apply_remote_changes to be used in "client" users. So, the function makes the editor
        read only immediately after apply changes.
        '''
        msg = event.change
    
        if self._debug:
            print("command: %s" % msg)
        
        widget = self.text_widget_from_id(msg["doc"])

        if msg["type"] == "I":
            pos = msg["pos"]
            new_text = msg["text"]

            widget.set_read_only(False)
            tk.Text.insert(widget, pos, new_text)
            widget.see(msg["user_pos"])
            widget.set_read_only(True)
        
        elif msg["type"] == "D":
            widget.set_read_only(False)
            if "end" in msg:
                tk.Text.delete(widget, msg["start"], msg["end"])
            else:
                tk.Text.delete(widget, msg["start"])
            widget.set_read_only(True)
        
        elif msg["type"] == "S":
            widget.set_read_only(False)
            tk.Text.delete(widget, "0.0", tk.END)
            tk.Text.insert(widget, "0.0", msg["text"])
            widget.see(msg["user_pos"])
            widget.set_read_only(True)

        elif msg["type"] == "M":
            # user_id = msg["user"]
            # doc_id = msg["doc"]
            # pos = msg["user_pos"]

            # self._users[user_id].position(doc_id, pos)
            pass

    def update_remote_cursor(self, user_id, index, is_keypress = False):
        color = self._users[user_id].color
        text_widget = self._editor_notebook.get_current_editor().get_text_widget()
        
        text_widget.mark_set(user_id, index)

        if user_id in text_widget.tag_names():
            text_widget.tag_delete(user_id)
        
        col = int(index[index.find(".") + 1 : ])
        if col != 0:
            real_index = index[: index.find(".") + 1] + \
                         str(col if is_keypress else col - 1)
            text_widget.tag_add(user_id, real_index)
            text_widget.tag_configure(user_id, background=color)

    def start_session(self):
        self._connection.Connect()
        self._connection.loop_start()
        self.user_man.Connect()
        self.user_man.loop_start()

if __name__ == "__main__":

    class DummyEditor:
        def __init__(self):
            pass

    class SessionTester:
        
        def get_docs(self):
            sess = Session()
            # test empty
            print(sess.get_docs())
            
        def _populate_editors(self, session):
            pass

    sTest = SessionTester()
    sTest.get_docs()