from random import randint
import math
from sortedcontainers import SortedList, SortedDict


class Character:
    def __init__(self, val, pos, author):
        self._val = val
        self._pos = pos
        self._author = author

    def author(self):
        return self._pos[-1]

    def __str__(self):
        # return (str(self._val) + "; " + str(self._pos)) # good for testing
        return str(self._val)

    # comparison to aid SortedList()
    def __lt__(self, other):
        if self._pos == None or other._pos == None:
            raise Exception("Can not compare uninitialized variables:", self, other)
        # author Id serves as tie breaker
        return (self._pos + [self._author]) < (other._pos + [other._author])


class CRDT_DOC:
    def __init__(self, file_path=None, siteID=0, id_bound=10, base_range=4):
        self.siteID = siteID
        self._id_strategy = {}
        self._id_boundary = 10
        self._base_range = base_range
        self.empty_start = Character("", [0], self.siteID)
        self.empty_end = Character("", [2 ** self._base_range - 1], self.siteID)

        self._chars = self._from_file(file_path) if file_path else self.from_scratch()

    def __str__(self):
        return str([str(c) for c in self._chars])

    def from_scratch(self):
        doc = SortedList()
        doc.add(self.empty_start)
        doc.add(self.empty_end)
        return doc

    def get_size(self):
        return len(self._chars)

    # generate doc fom file
    def _from_file(self, file_path):
        doc = SortedList()
        with open(file_path) as file:
            whole_file = file.read()
            doc.add(self.empty_start)
            doc.add(self.empty_end)
            for char in whole_file:
                self.insert(
                    char,
                    empty_start._pos,
                )
        return doc

    # placeholder for inserting in thonny
    def insert_local(self, val, prev_char, succ_char):
        pass

    def delete_by_id(self, id):
        self._chars = [x for x in self._chars if x._pos != id]

    def insert(self, val, prev_char=None, succ_char=None):
        new_char = None

        # if val is only character in doc
        if prev_char == None and succ_char == None:
            new_id = self.generatePosBetween(self.empty_start._pos, self.empty_end._pos)
            new_char = Character(val, new_id, self.siteID)

        # if val is first character in doc
        elif prev_char == None:
            new_id = self.generatePosBetween(self.empty_start._pos, succ_char._pos)
            new_char = Character(val, new_id, self.siteID)

        # if val is last character in doc
        elif succ_char == None:
            new_id = self.generatePosBetween(prev_char._pos, self.empty_end._pos)
            new_char = Character(val, new_id, self.siteID)

        else:
            new_id = self.generatePosBetween(prev_char._pos, succ_char._pos)
            new_char = Character(val, new_id, self.siteID)

        self._chars.add(new_char)
        return new_char

    # generates and Id between two positions
    def generatePosBetween(self, pos1, pos2, depth=0, newPos=[], is_root=True):
        # get id at tree depth or set 0
        id1 = pos1[depth] if len(pos1) >= (depth + 1) else 0
        id2 = pos2[depth] if len(pos2) >= (depth + 1) else 0

        alloc_strategy = self.get_strategy(depth)

        # new needs to be reset after multiple passes
        if is_root:
            newPos = []

        # if id's are not adjacent
        if (id2 - id1) > 1:
            newDigit = self.generatePosInLevel(id1, id2, depth)
            newPos.append(newDigit)
            return newPos

        # adjacent ids
        else:
            # check next depth
            if len(pos1) >= (depth + 1) or len(pos2) >= (depth + 1):
                newPos.append(id1)
                return self.generatePosBetween(pos1, pos2, depth + 1, newPos, False)

            # if Ids are at max depth, new level is created
            else:
                newPos.append(id1)
                new_digit = self.generatePosInLevel(id1, id2, depth + 1)
                newPos.append(new_digit)
                return newPos

    def generatePosInLevel(self, id1, id2, depth):
        strategy = self.get_strategy(depth)
        interval = id2 - id1 - 1
        step = min(self._id_boundary, interval)
        new_id = None

        if step == 0 or step == -1:
            new_id = randint(3, (self._base_range - 1))

        elif strategy == "+" and step > 0:
            new_id = id2
            # loop prevents duplicate IDs
            while id2 == new_id:
                new_id = id1 + randint(0, step) + 1

        elif strategy == "-" and step > 0:
            new_id = id1
            while id1 == new_id or id2 == new_id:
                new_id = id2 - randint(0, step)
        else:
            raise Exception("new level failure")

        return new_id

    def get_strategy(self, depth):
        if depth not in self._id_strategy:
            self._id_strategy[depth] = "+" if randint(0, 2) == 0 else "-"
        return self._id_strategy[depth]


if __name__ == "__main__":
    # For unit tests
    pass


# Unique id allocation - incomplete - based on LSEQ paper
if __name__ == "__main__":
    print("testing insert ...", end=" ")
    doc = CRDT_DOC()

    # empty condition
    assert doc.get_size() == 2
    print("0", end=" ")

    # insert basic
    char1 = doc.insert("a")
    assert doc.get_size() == 3
    assert doc._chars[1]._val == "a"
    print("1", end=" ")

    # insert end
    char2 = doc.insert("b", char1, None)
    assert doc._chars[2]._val == "b"
    print("2", end=" ")

    # insert middle
    char3 = doc.insert("x", char1, char2)
    assert doc._chars[2]._val == "x"
    print("3", end=" ")

    # insert begining (and new level)
    char4 = doc.insert("y", None, char1)
    assert doc._chars[1]._val == "y"

    char5 = doc.insert("q", None, char4)
    assert doc._chars[1]._val == "q"

    char6 = doc.insert("3", None, char5)
    assert doc._chars[1]._val == "3"
    print("4", end=" ")

    # insert end (and new level)
    char7 = doc.insert("2", char2, None)
    assert doc._chars[doc.get_size() - 2]._val == "2"

    char8 = doc.insert("1", char7, None)
    assert doc._chars[doc.get_size() - 2]._val == "1"

    char9 = doc.insert("-", char8, None)
    assert doc._chars[doc.get_size() - 2]._val == "-"
    print("5")

    print("testing delete... ", end=" ")

    # empty case
    assert doc.get_size() == 11
    doc.delete_by_id([99, 99, 99])
    assert doc.get_size() == 11
    print("0", end=" ")

    # delete from begining
    doc.delete_by_id(char1._pos)
    assert doc.get_size() == 10
    assert doc._chars[1]._val == "3"
    print("1", end=" ")

    # delete from end
    doc.delete_by_id(char9._pos)
    assert doc.get_size() == 9
    assert doc._chars[doc.get_size() - 2]._val == "1"
    print("2", end=" ")

    # delete middle
    doc.delete_by_id(char4._pos)
    assert doc.get_size() == 8
    assert doc._chars[3]._val == "x"

    print(doc)
