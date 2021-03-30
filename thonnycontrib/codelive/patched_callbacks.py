import difflib
import tkinter as tk

from thonny import get_workbench
from thonny.tktextext import TweakableText
from thonnycontrib.codelive.utils import publish_delete, publish_insert


def patched_insert(text_widget, index, chars, *args):
    wb = get_workbench()
    if not text_widget.is_read_only():
        publish_insert(wb, text_widget, text_widget.index(tk.INSERT), index, chars)
    TweakableText.insert(text_widget, index, chars, *args)


def patched_delete(text_widget, index1, index2=None):
    wb = get_workbench()
    if not text_widget.is_read_only():
        publish_delete(wb, text_widget, text_widget.index(tk.INSERT), index1, index2)
    TweakableText.delete(text_widget, index1, index2)
