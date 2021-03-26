import sys
import random
import string

from ..session_status import *
import tkinter as tk


class DummyUser:
    def __init__(self):
        self.name = "John " + "".join(
            random.choice(string.ascii_uppercase) for i in range(10)
        )
        self.id = random.randint(0, 100)
        self.position = "1.1"
        self.color = color
        self.last_alive = 0

        self.is_host = False
        self.is_idle = False
        self.cursor_colored = True


class DummySession:
    def __init__(self, is_host=False):
        self._users = {i: DummyUser() for i in range(0, 10)}
        self.username = "John Doe"
        self.is_host = is_host

        if self.is_host == False:
            self._users[random.randint(0, 9)].is_host = True

    def get_connection_info(self):
        return {"name": self.username, "broker": "test_broker", "topic": "test_topic"}

    def get_driver(self):
        if self.is_host:
            return "You"

        else:
            for user in self._users:
                if user.is_host == True:
                    return user.name

        return "null"


root = tk.Tk()
dummySession = DummySession()

if sys.argv[1] == "dialog":
    dummySession.is_host = len(sys.argv) > 2 and sys.argv[2] == "host"

    def t():
        r = SessionDialog(root, dummySession)

    button = ttk.Button(root, text="Hey", command=t)
    button.pack()

elif sys.argv[1] == "info":
    frame = SessionInfo(root, dummySession)
    frame.pack()

elif sys.argv[1] == "user":
    frame = UserList(root, dummySession)
    frame.pack()

elif sys.argv[1] == "action":
    dummySession.is_host = len(sys.argv) > 2 and sys.argv[2] == "host"
    frame = ActionList(root, dummySession)
    frame.pack()

root.mainloop()
