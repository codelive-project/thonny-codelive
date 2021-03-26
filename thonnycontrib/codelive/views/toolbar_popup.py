import tkinter


class ToolbarPopup(tkinter.Menu):
    def __init__(self, parent, groups: dict = None, *cnf, **key):
        super().__init__(parent, *cnf, **key)
        if groups != None:
            self.populate_menu(groups)

    def add_item(self, text, command, new_group=False):
        if new_group:
            self.add_separator()
        self.add_command(label=text, command=command)

    def populate_menu(self, groups: dict):
        """
        groups = group_number : list of {command_label, handler, enable (True or False})
        """
        sep_count = 0
        for group in sorted(groups):
            for item in groups[group]:
                if item["include_in_menu"]:
                    self.add_command(
                        label=item["command_label"],
                        command=item["handler"],
                        state=tkinter.NORMAL if item["enable"]() else tkinter.DISABLED,
                    )
            if sep_count < len(groups) - 1:
                self.add_separator()
                sep_count += 1
