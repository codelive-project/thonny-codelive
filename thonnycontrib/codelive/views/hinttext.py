import tkinter as tk
from tkinter import ttk


class HintText(ttk.Frame):
    def __init__(self, master=None, **kw):
        super().__init__(master=master, **kw)

        self.text = tk.Text(self, height=1, width=50)
        self.hint_str = tk.StringVar(self)
        self.hint_label = ttk.Label(self, textvariable=self.hint_str)

        self.text.pack(side=tk.TOP, fill=tk.X, expand=True)
        # self.hint_label(side = tk.TOP, fill = tk.X, expand = True)

    def hint(self, s=None):
        if s == None:
            return self.hint_str.get()
        else:
            self.hint_str.set(s)
            self.hint_visible(True)

    def hint_visible(self, val=None):
        if val != None:
            if val:
                self.hint_label.pack(side=tk.TOP, fill=tk.X, expand=True)
            else:
                self.hint_label.pack_forget()

    def val(self, s=None):
        if s == None:
            return self.text.get("0.0", tk.END).strip()

        state = self.text["state"]
        self.text["state"] = tk.NORMAL

        self.text.delete("0.0", tk.END)
        self.text.insert("0.0", s)

        self.text["state"] = state

    def state(self, state=None, both=True):
        if state == None:
            return self.text["state"]

        self.text["state"] = state
        self.text.configure(background="white" if state == tk.NORMAL else "#EEEEEE")
        if both:
            self.hint_visible(state == tk.NORMAL)
