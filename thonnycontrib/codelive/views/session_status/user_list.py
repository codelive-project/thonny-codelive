import tkinter as tk
from tkinter import ttk

from thonny import get_workbench
from thonnycontrib.codelive.views.session_status.scrollable_frame import ScrollableFrame


class UserListItem(tk.Frame):
    def __init__(self, parent, user, is_self, is_host):
        tk.Frame.__init__(
            self, parent, highlightbackground="#E9E9E9", highlightthickness=1
        )
        self.user_id = user.id
        self.color = user.color
        self.username = user.name + " (You)" if is_self else user.name
        self.is_driver = user.is_host

        self.label_str = tk.StringVar()
        self.label_str.set(self.username)

        icon = self.create_icon()
        self.name_label = tk.Label(self, textvariable=self.label_str, anchor="w")
        self.make_driver_button = tk.Button(
            self, text="Give Control", width=10, command=self.make_driver
        )

        icon.pack(side=tk.LEFT, padx=10)
        self.name_label.pack(side=tk.LEFT, fill=tk.X)
        self.make_driver_button.pack(side=tk.RIGHT, padx=10)

        if self.is_driver:
            self.driver(self.is_driver)
        self.enable_button(is_host and not self.is_driver)

    def make_driver(self):
        if __name__ != "__main__":
            get_workbench().event_generate("MakeDriver", user=self.user_id)

    def create_icon(self):
        def create_circle(canvas, x, y, r, **kwargs):
            return canvas.create_oval(x - r, y - r, x + r, y + r, **kwargs)

        icon = tk.Canvas(self, width=30, height=30)
        create_circle(icon, 17, 17, 10, fill=self.color, outline="")
        return icon

    def driver(self, val=None):
        if val == None:
            return self.is_driver
        else:
            self.label_str.set(self.username + " [Driver]" if val else self.username)
            self.name_label.configure(fg="green" if val else "black")
            self.is_driver = val

    def enable_button(self, val=True):
        self.make_driver_button["state"] = tk.NORMAL if val else tk.DISABLED

    def toggle_driver(self):
        self.driver(not self.is_driver)


class UserList(ttk.LabelFrame):
    def __init__(self, parent, session, **kw):
        ttk.LabelFrame.__init__(self, parent, **kw)

        self.scrollable_frame = ScrollableFrame(self, width=200)
        self.users = session.get_users()
        self.session = session
        self.widgets = dict()
        self.driver = session.get_driver()

        self.populate_list()
        self.scrollable_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5
        )

    def populate_list(self):
        for i in self.users:
            self.add_user(self.users[i])

    def add_user(self, user):
        line = UserListItem(
            self.scrollable_frame.get_frame(),
            user,
            self.session.user_id == user.id,
            self.session.is_host,
        )
        self.scrollable_frame.append(line)
        self.widgets[user.id] = line

    def remove_user(self, user):
        self.remove_id(user.id)

    def remove_id(self, _id):
        if _id == self.driver:
            return
        self.scrollable_frame.remove_widget(self.widgets[_id])

    def update_driver(self, _id):
        is_host = self.session.user_id == _id

        for line in self.widgets.values():
            if line.is_driver:
                line.driver(False)
            if line.user_id == _id:
                line.driver(True)

            line.enable_button(line.user_id != _id if is_host else False)

    def get_driver(self):
        return self.driver

    def set_driver(self, user):
        # set new driver
        self.set_driver_id(user.id)

    def set_driver_id(self, _id):
        self.widgets[_id].toggle_driver()
        self.driver = _id
        # remove current driver
        if self.driver >= 0:
            self.widgets[self.driver].toggle_driver()
