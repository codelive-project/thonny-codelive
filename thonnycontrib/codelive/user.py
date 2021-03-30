from datetime import datetime
from threading import Lock

import json
import random

from thonnycontrib.codelive.res.default_values import COLORS


def get_color(used_colors=None):
    if used_colors == None:
        return random.choice(COLORS)

    else:
        if len(used_colors) == len(COLORS):
            raise ValueError(
                "Unable to assign a new color: len(used_colors) == len(COLORS)"
            )

        for i in range(len(COLORS)):
            color = random.choice(COLORS)
            if color not in used_colors:
                return color

        raise ValueError("Unable to assign a new color: attempt timed out")


class User:
    def __init__(
        self, _id, name, doc_id, color=get_color(), is_host=False, position="0.0"
    ):
        self.name = name
        self.id = _id
        self.color = color

        self.is_host = is_host

        self.doc_id = doc_id
        self.position = position

        self.last_alive = 0
        self.is_idle = False
        self.cursor_colored = True

        self._lock = Lock()

    def host(self, val=None):
        if val:
            with self._lock:
                self.is_host = val
        else:
            with self._lock:
                return self.is_host

    def set_alive(self):
        with self._lock:
            self.last_live = 0
            self.is_idle = False

    def age(self):
        with self._lock:
            self.last_alive += 1

            if self.last_alive > 5:
                self.is_idle = True
                return True
            else:
                return False

    def __str__(self):
        return str(
            {
                "name": self.name,
                "id": self.id,
                "doc_id": self.doc_id,
                "position": self.position,
                "color": self.color,
                "is_host": self.is_host,
            }
        )

    def position(self, doc_id=None, position=None):
        if position and doc_id:
            if doc_id:
                with self._lock:
                    self.doc_id = doc_id

            if position:
                with self._lock:
                    self.position = position
        else:
            with self._lock:
                return self.doc_id, self.position


class UserEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, User):
            return {
                "_type": "User",
                "value": {
                    "name": o.name,
                    "id": o.id,
                    "doc_id": o.doc_id,
                    "position": o.position,
                    "color": o.color,
                    "is_host": o.is_host,
                },
            }

        else:
            return super().default(o)


class UserDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if "_type" not in obj:
            return obj
        type = obj["_type"]
        if type == "User":
            data = obj["value"]
            return User(
                _id=data["id"],
                name=data["name"],
                doc_id=data["doc_id"],
                color=data["color"],
                is_host=data["is_host"],
            )
        return obj
