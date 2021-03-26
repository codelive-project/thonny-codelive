import os
import tkinter as tk
import webbrowser

from tkinter import messagebox
from tkinter import ttk

from thonnycontrib.codelive.views.session_status.user_list import UserList, UserListItem

SESSION_DIA_MIN_SIZE = {"width": 378, "height": 400}
BUG_ICON_PATH = os.path.join(os.path.dirname(__file__), "res", "bug-16.png")
BUG_REPORT_URL = "https://github.com/codelive-project/codelive/issues/new"


class SessionInfo(ttk.LabelFrame):
    def __init__(self, parent, session):
        ttk.LabelFrame.__init__(self, parent, width=100, text="Session Info")
        # labels
        frame = ttk.Frame(self)
        name_label = ttk.Label(frame, text="Your name: ")
        topic_label = ttk.Label(frame, text="Topic: ")
        broker_label = ttk.Label(frame, text="Broker: ")
        driver_label = ttk.Label(frame, text="Driver: ")

        # feilds
        connection_info = session.get_connection_info()

        self.session = session
        self.driver_name = tk.StringVar()
        _id, name = session.get_driver()
        self.driver_name.set(name + " (You)" if self.session.user_id == _id else name)

        name = ttk.Label(frame, text=session.username)
        topic = ttk.Label(frame, text=connection_info["topic"])
        broker = ttk.Label(frame, text=connection_info["broker"])
        driver = ttk.Label(frame, textvariable=self.driver_name)

        # position
        name_label.grid(row=0, column=0, sticky=tk.E)
        topic_label.grid(row=1, column=0, sticky=tk.E)
        broker_label.grid(row=2, column=0, sticky=tk.E)
        driver_label.grid(row=3, column=0, sticky=tk.E)

        name.grid(row=0, column=1, sticky=tk.W)
        topic.grid(row=1, column=1, sticky=tk.W)
        broker.grid(row=2, column=1, sticky=tk.W)
        driver.grid(row=3, column=1, sticky=tk.W)

        frame.pack(side=tk.TOP, fill=tk.X, expand=True, anchor=tk.CENTER)

    def update_driver(self, s=None):
        if s != None:
            self.driver_name.set(s)
        else:
            _id, name = self.session.get_driver()
            self.driver_name.set(
                name + " (You)" if self.session.user_id == _id else name
            )

    def update_driver_id(self, _id):
        name = (
            self.session.get_name(_id) + " (You)"
            if self.session.user_id == _id
            else self.session.get_name(_id)
        )
        self.driver_name.set(name)


class ActionList(ttk.Frame):
    def __init__(self, parent, session, dia):
        ttk.Frame.__init__(self, parent)

        self.dia = dia
        self.session = session
        self.request_control = ttk.Button(
            self, text="Request Control", command=self._request_callback
        )
        leave = ttk.Button(self, text="Leave Session", command=self._leave_callback)
        self.end = ttk.Button(self, text="End Session", command=self._end_callback)

        self.request_control.pack(
            side=tk.LEFT, padx=(5, 0)
        )  # grid(row = 0, column = 0, columnspan = 2, pady = (5, 2), padx = 10, sticky = tk.N + tk.E + tk.S + tk.W)
        self.end.pack(
            side=tk.RIGHT, padx=(0, 0)
        )  # grid(row = 1, column = 1, pady = (2, 10), padx = (2, 10), sticky = tk.N + tk.E + tk.S + tk.W)
        leave.pack(
            side=tk.RIGHT, padx=(0, 5)
        )  # .grid(row = 1, column = 0, pady = (2, 10), padx = (10, 2), sticky = tk.N + tk.E + tk.S + tk.W)

        self.request_control["state"] = tk.DISABLED if session.is_host else tk.NORMAL
        self.end["state"] = tk.NORMAL if session.is_host else tk.DISABLED

        # configure for resize
        # self.columnconfigure(0, weight = 1, minsize = 50)
        # self.columnconfigure(1, weight = 1, minsize = 50)
        # self.rowconfigure(0, weight = 1, minsize = 10)
        # self.rowconfigure(1, weight = 1, minsize = 10)

        self.retry_attempt = 0

    def driver(self, val=None):
        if val == None:
            return self.end["state"] == tk.NORMAL

        self.request_control["state"] = tk.DISABLED if val else tk.NORMAL
        self.end["state"] = tk.NORMAL if val else tk.DISABLED

    def toggle_driver(self):
        self.end["state"] = tk.DISABLED if self.end["state"] == tk.NORMAL else tk.NORMAL
        self.request_control["state"] = (
            tk.DISABLED if self.request_control["state"] == tk.NORMAL else tk.NORMAL
        )

    def _request_callback(self):
        status = self.session.request_control()

        if status == 0:
            # Success
            pass
        elif status == 1:
            # Rejected
            self.retry_attempt += 1
            ret = messagebox.askretrycancel(
                "Request rejected",
                "Your request was rejected. Do you want to request control again?",
            )
            if ret:
                if self.retry_attempt >= 5:
                    messagebox.showerror(
                        "Unable to Join",
                        "You cannot request control at the moment. Please try again later.",
                    )
                else:
                    self._request_callback()

        elif status == 2:
            #  out
            messagebox.showerror(
                "Request timed-out",
                "Your request has timed out. Please try again later.",
            )
        else:
            # general error
            messagebox.showerror("Error", "Unable to join. Please try again later.")

        # reset retry attempts after last attempt
        self.retry_attempt = 0

    def _leave_callback(self):
        ret = self.session.leave()

    def _end_callback(self):
        ret = self.session.end()


class SessionDialog(tk.Toplevel):
    def __init__(self, parent, session):
        tk.Toplevel.__init__(self)
        self.title("Current Session - Beta")
        frame = ttk.Frame(self)

        self.session = session
        self.session_info = SessionInfo(frame, session)
        sep1 = ttk.Separator(frame, orient=tk.HORIZONTAL)
        self.user_list = UserList(
            frame, session, text="Active Users", borderwidth=1, width=1000
        )
        sep2 = ttk.Separator(frame, orient=tk.HORIZONTAL)
        self.buttons = ActionList(frame, session, self)

        self.session_info.grid(
            row=0, column=0, sticky=tk.N + tk.E + tk.W, padx=10, pady=5
        )
        sep1.grid(row=1, column=0, sticky=tk.E + tk.W, padx=10)
        self.user_list.grid(
            row=2, column=0, sticky=tk.N + tk.E + tk.S + tk.W, padx=10, pady=(5, 5)
        )

        bug_frame = ttk.Frame(frame)
        bug_icon = tk.PhotoImage(file=BUG_ICON_PATH)
        bug = ttk.Button(
            bug_frame,
            text="Report Bug",
            image=bug_icon,
            compound=tk.LEFT,
            command=lambda: webbrowser.open(BUG_REPORT_URL),
        )
        bug.image = bug_icon
        bug.pack(side=tk.RIGHT)

        bug_frame.grid(row=3, column=0, sticky=tk.E + tk.W, padx=10, pady=(0, 5))
        sep2.grid(row=4, column=0, sticky=tk.E + tk.W, padx=10)
        self.buttons.grid(
            row=5, column=0, sticky=tk.S + tk.E + tk.W, padx=10, pady=(5, 10)
        )

        frame.pack(fill=tk.BOTH, expand=True)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.minsize(SESSION_DIA_MIN_SIZE["width"], SESSION_DIA_MIN_SIZE["height"])

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        self._initial_place(parent)

    def _initial_place(self, parent):
        parent_dim, parent_x, parent_y = parent.geometry().split("+")
        parent_w, parent_h = (int(l) for l in parent_dim.split("x"))

        parent_x = int(parent_x)
        parent_y = int(parent_y)

        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()

        w, h = SESSION_DIA_MIN_SIZE["width"], SESSION_DIA_MIN_SIZE["height"]
        _x = _y = None

        if screen_width < 10 + parent_x + parent_w + w:
            _x = screen_width - (w + 10)
        elif parent_x + parent_w < 0:
            _x = 10
        else:
            _x = 10 + parent_x + parent_w

        if screen_height < parent_y + h:
            _y = screen_height - (h + 10)
        elif parent_y < 0:
            _y = 10
        else:
            _y = parent_y

        self.geometry("%dx%d+%d+%d" % (w, h, _x, _y))

    def update_host(self, _id=None):
        self.session_info.update_driver_id(_id)
        self.user_list.update_driver(_id)
        self.buttons.driver(self.session.user_id == _id)

    def add_user(self, user):
        self.user_list.add_user(user)

    def remove_id(self, rm_id, new_host=None):
        self.user_list.remove_id(rm_id)
        if new_host != None:
            self.update_host(new_host)

    def on_closing(self):
        pass


if __name__ == "__main__":
    import sys
    import random
    import string

    colors = ["#75DBFF", "#50FF56", "#FF8D75", "#FF50AD", "#FF9B47"]

    class DummyUser:
        def __init__(self, _id, name=None, is_host=False):
            self.name = (
                name
                if name != None
                else str(_id)
                + " - John "
                + "".join(random.choice(string.ascii_uppercase) for i in range(10))
            )
            self.id = _id
            self.position = "1.1"
            self.color = random.choice(colors)
            self.last_alive = 0

            self.is_host = is_host
            self.is_idle = False
            self.cursor_colored = True

    class DummySession:
        def __init__(self, is_host=False):
            self.user_id = 0
            self._users = {i: DummyUser(i) for i in range(1, 10)}
            self._users[0] = DummyUser(0, "Me", is_host)
            self.username = "John Doe"
            self.is_host = is_host

            if self.is_host == False:
                self._users[random.randint(1, 9)].is_host = True

        def get_connection_info(self):
            return {
                "name": self.username,
                "broker": "test_broker",
                "topic": "test_topic",
            }

        def get_driver(self):
            if self.is_host:
                return 0, "You"

            else:
                for i in self._users:
                    if self._users[i].is_host == True:
                        return i, self._users[i].name

            return -1, "null"

        def get_users(self):
            return self._users

        def get_name(self, _id):
            return self._users[_id].name

    root = tk.Tk()
    dummyUser = DummyUser(
        random.randint(0, 9), len(sys.argv) > 2 and sys.argv[2] == "host"
    )
    dummySession = DummySession(len(sys.argv) > 2 and sys.argv[2] == "host")

    if sys.argv[1] == "dialog":
        frame = ttk.Frame(root)
        r = SessionDialog(root, dummySession)
        text = tk.Text(frame, width=10, height=1)

        def make_host():
            _id = int(text.get("0.0", tk.END).strip())
            if r == None:
                print("Start dialog first")
            else:
                r.update_host(_id)

        button_mh = ttk.Button(frame, text="Make", command=make_host)
        button_dest = ttk.Button(frame, text="Destroy", command=lambda: r.destroy())
        text.grid(row=0, column=0, padx=(10, 2.5), pady=10)
        button_mh.grid(row=0, column=1, padx=(2.5, 10), pady=(10, 0))
        button_dest.grid(row=1, column=1, padx=(2.5, 10), pady=(0, 10))
        frame.pack()

    elif sys.argv[1] == "info":
        frame = SessionInfo(root, dummySession)
        frame.pack(padx=50, pady=50)

    elif sys.argv[1] == "item":
        frame = UserListItem(root, dummyUser)
        frame.pack(fill=tk.BOTH, expand=True)

        def t():
            frame.toggle_driver()

        button = ttk.Button(root, text="Hey", command=t)
        button.pack()

    elif sys.argv[1] == "list":
        frame = UserList(root, dummySession)
        frame.pack(fill=tk.BOTH, expand=True)
        t_box = tk.Text(root)
        t_box.pack(fill=tk.X, expand=True)

        def add():
            global frame
            name = t_box.get("0.0", tk.END).strip()
            if len(name) > 0:
                usr = DummyUser(random.randint(100, 10000000), name)
                frame.add(usr)

        def remove():
            global frame
            try:
                index = int(t_box.get("0.0", tk.END).strip())
                frame.remove_id(index)
            except Exception as e:
                print(e)

        ttk.Button(root, text="Add", command=add).pack(fill=tk.X, expand=True)
        ttk.Button(root, text="Remove", command=remove).pack(fill=tk.X, expand=True)

    elif sys.argv[1] == "action":
        frame = ActionList(root, dummySession)
        frame.pack(fill=tk.X, expand=True)

    root.mainloop()
