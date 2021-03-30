import tkinter as tk
from tkinter import ttk

from thonny import get_workbench
from thonnycontrib.codelive.mqtt_connection import generate_topic, topic_exists

from thonnycontrib.codelive.views.hinttext import HintText
from thonnycontrib.codelive.views.textspin import TextSpin
from thonnycontrib.codelive.mqtt_connection import BROKER_URLS

# For testing only!!!!!
if __name__ == "__main__":

    class DummyEditor:
        def __init__(self, title="untitled", filename=None):
            self.title = title
            self.filename = filename

        def get_title(self):
            return self.title

        def get_filename(self):
            return self.filename


class EditorSelector(ttk.Frame):
    def __init__(self, parent, active_editors):
        ttk.Frame.__init__(self, parent)
        self.active_editors = active_editors

        label = ttk.Label(self, text="Please choose the editors you want to share")

        container, self.editor_list = self.get_list()

        label.pack(side=tk.TOP)
        container.pack(side=tk.BOTTOM)

    def on_select_all(self):
        # on uncheck
        if self.check_state.get() == 0:
            self.editor_list.selection_clear(0, self.editor_list.size() - 1)
            self.check_label.set("Select All")
        # on check
        else:
            self.editor_list.selection_set(0, self.editor_list.size() - 1)
            self.check_label.set("Unselect All")

    def get_list(self):
        container = ttk.Frame(self)
        sub_container = ttk.Frame(container)

        scrollbar = tk.Scrollbar(sub_container)
        list_widget = tk.Listbox(
            sub_container,
            yscrollcommand=scrollbar.set,
            height=7,
            width=60,
            selectmode=tk.MULTIPLE,
        )
        scrollbar.configure(command=list_widget.yview)

        self.check_state = tk.IntVar()
        self.check_label = tk.StringVar()
        self.check_label.set("Select All")

        self.select_all_check = ttk.Checkbutton(
            container,
            command=self.on_select_all,
            textvariable=self.check_label,
            variable=self.check_state,
            onvalue=1,
            offvalue=0,
        )

        for item in self.active_editors:
            editor = self.active_editors[item]
            title = editor.get_title()
            filename = editor.get_filename() or "Unsaved"

            if len(filename) + len(title) + 3 > 50:
                filename = "..." + filename[len(filename) - (len(title) + 6) :]

            label = " %s (%s) " % (title, editor.get_filename() or "Unsaved")
            list_widget.insert(tk.END, label)

        list_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        sub_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.select_all_check.pack(side=tk.LEFT)

        return container, list_widget

    def get_shared_editors(self):
        return (self.active_editors[index] for index in self.editor_list.curselection())

    def none_selected(self):
        return len(self.editor_list.curselection()) == 0


class CreateSessionDialog(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.protocol("WM_DELETE_WINDOW", self.cancel_callback)
        self.title("Create Live Session - Beta")

        frame = ttk.Frame(self)

        self.data = dict()

        # Connection info
        Intro = ttk.Label(
            frame,
            text="Please provide information needed to start your new CodeLive Session.",
        )

        form_frame = ttk.Frame(frame, width=50)

        name_label = ttk.Label(form_frame, text="Your alias")
        self.name_input = HintText(form_frame)

        session_topic_label = ttk.Label(form_frame, text="Session Topic")
        self.topic_input = HintText(form_frame)

        broker_label = ttk.Label(form_frame, text="MQTT Broker")
        self.broker_input = TextSpin(form_frame, BROKER_URLS, mode="option")

        self.auto_gen_topic_state = tk.IntVar()
        self.auto_generate_check = ttk.Checkbutton(
            form_frame,
            text="Auto-generate",
            command=self.auto_gen_callback,
            variable=self.auto_gen_topic_state,
            onvalue=1,
            offvalue=0,
        )

        self.default_broker_val = tk.IntVar()
        self.default_broker_val.set(1)
        self.default_broker_check = ttk.Checkbutton(
            form_frame,
            text="Built-In",
            command=self.default_broker_callback,
            variable=self.default_broker_val,
            onvalue=1,
            offvalue=0,
        )

        name_label.grid(row=0, column=0, sticky=tk.E)
        self.name_input.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)

        session_topic_label.grid(row=1, column=0, sticky=tk.E)
        self.topic_input.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        self.auto_generate_check.grid(row=1, column=3, sticky=tk.W)

        broker_label.grid(row=2, column=0, sticky=tk.E)
        self.broker_input.grid(row=2, column=1, sticky=tk.W + tk.E, padx=10, pady=5)
        self.default_broker_check.grid(row=2, column=3, sticky=tk.W)

        sep1 = ttk.Separator(frame, orient=tk.HORIZONTAL)
        # Shared editors frame
        self.editor_selector = EditorSelector(frame, self.get_active_editors(parent))

        sep2 = ttk.Separator(frame, orient=tk.HORIZONTAL)
        # Bottom Button Frame
        button_frame = ttk.Frame(frame)

        start_button = tk.Button(
            button_frame,
            text="Start!",
            command=self.start_callback,
            fg="green",
            width=10,
        )

        cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_callback,
            fg="red",
            width=10,
        )

        start_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        cancel_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        Intro.pack(expand=True, padx=10, pady=5)
        form_frame.pack(side=tk.TOP, expand=False, padx=10, pady=5)

        sep1.pack(side=tk.TOP, fill=tk.X, expand=True, padx=20)

        self.editor_selector.pack(side=tk.TOP, fill=tk.BOTH)

        sep2.pack(side=tk.TOP, fill=tk.X, expand=True, padx=20)

        button_frame.pack(side=tk.BOTTOM, padx=10, pady=5)

        frame.pack(fill=tk.BOTH, expand=True)

        self.center(parent.winfo_geometry())

    def center(self, parent_geo):
        parent_dim, parent_x, parent_y = parent_geo.split("+")
        parent_w, parent_h = [int(l) for l in parent_dim.split("x")]

        parent_x = int(parent_x)
        parent_y = int(parent_y)

        w = 650
        h = 350

        x = parent_x + (parent_w - w) / 2
        y = parent_y + (parent_h - h) / 2

        self.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def get_active_editors(self, parent):
        editors = dict()

        # for testing only
        if __name__ == "__main__":
            editors = {
                0: DummyEditor(),
                1: DummyEditor("Hello"),
                2: DummyEditor(filename="hello path"),
                3: DummyEditor("Hello", "Hello's path"),
            }

        else:
            editors = {
                index: editor
                for (index, editor) in enumerate(
                    parent.get_editor_notebook().winfo_children()
                )
            }

        return editors

    def start_callback(self):
        name = self.name_input.val()
        topic = self.topic_input.val()
        broker = self.broker_input.val()

        if (
            self.valid_name(name)
            and self.valid_connection(topic, broker)
            and self.valid_selection()
        ):
            self.data["name"] = name
            self.data["topic"] = topic
            self.data["broker"] = broker
            self.data["shared_editors"] = self.editor_selector.get_shared_editors()

            self.destroy()

    def cancel_callback(self):
        if tk.messagebox.askokcancel(
            parent=self,
            title="Cancel Session",
            message="Are you sure you want to cancel hosting a CodeLive session?",
        ):
            self.data = None
            self.destroy()

    def default_broker_callback(self):
        is_text = self.default_broker_val.get() == 0
        self.broker_input.mode("text" if is_text else "option")

    def auto_gen_callback(self):
        # on uncheck
        if self.auto_gen_topic_state.get() == 0:
            self.topic_input.state(tk.NORMAL)
        # on check
        else:
            self.topic_input.val(generate_topic())
            self.topic_input.state(tk.DISABLED)

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

    def valid_selection(self):
        if self.editor_selector.none_selected():
            tk.messagebox.showerror(
                parent=self,
                title="Error",
                message="Please select at least one editor that would be shared during your session.",
            )
            return False
        return True


if __name__ == "__main__":
    root = tk.Tk()

    def start_top():
        top = CreateSessionDialog(root)
        root.wait_window(top)

    button = tk.Button(root, text="Test", command=start_top)
    button.pack(padx=20, pady=20)
    root.mainloop()
