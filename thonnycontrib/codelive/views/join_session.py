import tkinter as tk
from tkinter import ttk

from thonnycontrib.codelive.mqtt_connection import topic_exists

from thonnycontrib.codelive.views.hinttext import HintText
from thonnycontrib.codelive.views.textspin import TextSpin
from thonnycontrib.codelive.mqtt_connection import BROKER_URLS

BG = "#EEEEE4"
JOIN_DIA_MIN_SIZE = {"width": 470, "height": 220}


class JoinSessionDialog(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent, bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.cancel_callback)
        self.title("Join Live Session - Beta")
        self.data = dict()

        frame = ttk.Frame(self)

        intro = ttk.Label(
            frame,
            text="Please Provide information needed to join an existing CodeLive Session.",
        )

        form_frame = ttk.Frame(frame)

        name_label = ttk.Label(form_frame, text="Your alias")
        self.name_input = HintText(form_frame)

        topic_label = ttk.Label(form_frame, text="Session Topic")
        self.topic_input = HintText(form_frame)

        broker_label = ttk.Label(form_frame, text="MQTT Broker")
        broker_frame = ttk.Frame(form_frame)
        (
            self.broker_input,
            self.default_broker_val,
            self.default_broker_check,
        ) = self._make_broker_entry(broker_frame)

        name_label.grid(row=0, column=0, sticky=tk.W + tk.E + tk.N, pady=5)
        self.name_input.grid(
            row=0, column=1, sticky=tk.W + tk.E + tk.N, padx=10, pady=5
        )

        topic_label.grid(row=1, column=0, sticky=tk.E + tk.W + tk.N, pady=5)
        self.topic_input.grid(
            row=1, column=1, sticky=tk.E + tk.W + tk.N, padx=10, pady=5
        )

        broker_label.grid(row=2, column=0, sticky=tk.W + tk.E + tk.N, pady=5)
        broker_frame.grid(row=2, column=1, sticky=tk.E + tk.W + tk.N, padx=10, pady=5)

        form_frame.columnconfigure(0, weight=0)
        form_frame.columnconfigure(1, weight=4)

        button_frame = ttk.Frame(frame)

        start_button = tk.Button(
            button_frame, text="Join!", command=self.join_callback, fg="green", width=10
        )

        cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_callback,
            fg="red",
            width=10,
        )

        start_button.pack(side=tk.RIGHT, padx=5)
        cancel_button.pack(side=tk.LEFT, padx=5)

        intro.pack(
            side=tk.TOP, fill=tk.X, expand=True, padx=10, pady=5, anchor=tk.CENTER
        )
        form_frame.pack(side=tk.TOP, fill=tk.X, expand=True, padx=10, pady=5)
        button_frame.pack(side=tk.BOTTOM, padx=10, pady=5)

        frame.pack(fill=tk.BOTH, expand=True)

        self.center(parent.winfo_geometry())
        self.minsize(JOIN_DIA_MIN_SIZE["width"], JOIN_DIA_MIN_SIZE["height"])
        self.maxsize(JOIN_DIA_MIN_SIZE["width"], JOIN_DIA_MIN_SIZE["height"])

    def center(self, parent_geo):
        parent_dim, parent_x, parent_y = parent_geo.split("+")
        parent_w, parent_h = [int(l) for l in parent_dim.split("x")]

        parent_x = int(parent_x)
        parent_y = int(parent_y)

        w = JOIN_DIA_MIN_SIZE["width"]
        h = JOIN_DIA_MIN_SIZE["height"]

        x = parent_x + (parent_w - w) / 2
        y = parent_y + (parent_h - h) / 2

        self.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _make_broker_entry(self, parent):
        _input = TextSpin(parent, BROKER_URLS, mode="option")
        val = tk.IntVar()
        val.set(1)
        check = ttk.Checkbutton(
            parent,
            text="Built-In",
            command=self._broker_check_cb,
            variable=val,
            onvalue=1,
            offvalue=0,
        )

        _input.grid(row=0, column=0, columnspan=2, sticky=tk.N + tk.S + tk.E + tk.W)
        check.grid(row=1, column=0, columnspan=1, sticky=tk.S + tk.W)
        parent.columnconfigure(0, weight=1)

        return _input, val, check

    def _broker_check_cb(self):
        is_text = self.default_broker_val.get() == 0
        self.broker_input.mode("text" if is_text else "option")

    def join_callback(self):
        name = self.name_input.val()
        topic = self.topic_input.val()
        broker = self.broker_input.val()

        if self.valid_name(name) and self.valid_connection(topic, broker):
            self.data["name"] = name
            self.data["topic"] = topic
            self.data["broker"] = broker

            self.destroy()

    def cancel_callback(self):
        if tk.messagebox.askokcancel(
            parent=self,
            title="Cancel Session",
            message="Are you sure you want to cancel joining the CodeLive session?",
        ):
            self.data = None
            self.destroy()

    def valid_name(self, s):
        if len(s) < 8:
            tk.messagebox.showerror(
                parent=self,
                title="Error",
                message="Please provide a name at least 8 characters long.",
            )
            return False
        return True

    def valid_connection(self, topic, broker):
        if len(topic) < 12:
            tk.messagebox.showerror(
                parent=self,
                title="Error",
                message="Please provide a unique topic with more than 12 characters.",
            )
            return False

        if len(broker) < 12:
            tk.messagebox.showerror(
                parent=self, title="Error", message="Please provide a valid broker."
            )
            return False

        # TODO: replace with topic_exists(s) when topic_exists's logic is complete
        if False:  # topic_exists(topic, broker):
            tk.messagebox.showerror(
                parent=self,
                title="Error",
                message="The topic doesn't exist. Make sure your topic is spelled correctly.",
            )
            return False
        return True


if __name__ == "__main__":

    root = tk.Tk()

    def start_top():
        top = JoinSessionDialog(root)
        root.wait_window(top)

    button = tk.Button(root, text="Test", command=start_top)
    button.pack(padx=20, pady=20)
    root.mainloop()
