from typing import Any
import time
class Node:
    def __init__(self, key, value, ttl=None):
        self.key: Any = key
        self.value: Any = value
        self.prev: Node = None
        self.next: Node = None
        self.time_to_live = ttl
        self.expires_at = (time.time() + ttl) if ttl is not None else None
        

