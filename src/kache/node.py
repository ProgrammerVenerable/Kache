from typing import Any
class Node:
    def __init__(self, key, value):
        self.key: Any = key
        self.value: Any = value
        self.prev: Node = None
        self.next: Node = None