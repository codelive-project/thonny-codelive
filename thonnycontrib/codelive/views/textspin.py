import tkinter as tk
from tkinter import ttk

from thonny.misc_utils import running_on_mac_os


class TextSpin(ttk.Frame):
    def __init__(self, master, spin_options, mode="text", **kw):
        super().__init__(master=master, **kw)
        self.frame = ttk.Frame(self, width=50)

        if len(spin_options) == 0:
            raise ValueError("spin_options must be a non empty list")
        self.options = spin_options
        self.option_val = tk.StringVar(self)
        self.option_val.set(self.options[0])
        self.hint_str = tk.StringVar(self)

        self.text = tk.Text(self.frame, height=1, width=50)
        """
        tk.Option used because thonny themes hide the option to change the value of the default list
        """
        if running_on_mac_os():
            self.option_box = tk.OptionMenu(self.frame, self.option_val, *spin_options)
        else:
            self.option_box = ttk.OptionMenu(self.frame, self.option_val, *spin_options)

        self.hint_label = ttk.Label(self, textvariable=self.hint_str)

        self.frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        if mode == "text":
            self.text.pack(side=tk.TOP, fill=tk.X, expand=True)
        else:
            self.option_box.pack(side=tk.TOP, fill=tk.X, expand=True)

    def mode(self, mode=None):
        if mode == None:
            return self._mode

        if mode == "text":
            if self.option_box.winfo_ismapped():
                self.option_box.pack_forget()

            if not self.text.winfo_ismapped():
                self.text.pack(side=tk.TOP, fill=tk.X, expand=True)
            else:
                print("Warning: already on 'text' mode")

        elif mode == "option":
            if self.text.winfo_ismapped():
                self.text.pack_forget()

            if not self.option_box.winfo_ismapped():
                self.option_box.pack(side=tk.TOP, fill=tk.X, expand=True)
            else:
                print("Warning: already on 'option' mode")

        else:
            raise ValueError(
                "option '%s' (%d) is not viable. Possible modes are 'text' or 'option'"
                % (str(mode), str(type(mode)))
            )

    def val(self, s=None, mode=None, is_mapped=True):

        self.frame_state()
        self.frame_state(tk.NORMAL)

        if s == None:
            # if mode is None, dict containing value for both will be returned
            if mode == None:
                if self.text.winfo_ismapped():
                    return self.text.get("0.0", tk.END).strip()
                else:
                    return self.option_val.get()

            else:
                if mode == "text":
                    return self.text.get("0.0", tk.END).strip()
                elif mode == "option":
                    return self.option_val.get()
                else:
                    raise ValueError(
                        "option '%s' (%d) is not viable. Possible modes are 'text' or 'option'"
                        % (str(mode), str(type(mode)))
                    )

            return

        # if mode is non, text is assumed
        if mode == None or mode == "text":
            self.text.delete("0.0", tk.END)
            self.text.insert("0.0", s)

            if is_mapped:
                self.mode("text")
        else:
            if s not in self.options:
                raise ValueError(
                    "'%s' is not an option. s should be a str in" % s
                    + str(self.options)
                )
            self.option_val.set(s)

            if is_mapped:
                self.mode("option")

        self.frame_state(state)

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

    def state(self, state=None, both=True):
        if state == None:
            return self.frame_state()

        self.frame_state(state)
        if both:
            self.hint_visible(state == tk.NORMAL and len(self.hint_str.get()) > 0)

    def frame_state(self, state=None):
        if state == None:
            return self.frame.winfo_children()[0]["state"]

        for child in self.frame.winfo_children():
            child["state"] = state
