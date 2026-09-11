from .node import Node
from typing import Optional, Any
class DLL:
    def __init__(self):
        self.head_sentinel: Node = Node(None, None)
        self.tail_sentinel: Node = Node(None, None)
        self.head_sentinel.next = self.tail_sentinel
        self.tail_sentinel.prev = self.head_sentinel
    
    def insert(self, node):
        """"Inserting a node holding key, value pairs in the list"""
        # nN.next points to what hs is pointing at
        node.next = self.head_sentinel.next
        # nN.prev points to hs, which completes the loop nN ⇌ hs
        node.prev = self.head_sentinel
        # setting the prev node ref of the node hs is pointing at
        # id hs is pointing at ts the ts.prev should point to nN
        self.head_sentinel.next.prev = node
        # setting what hs is pointing at
        self.head_sentinel.next = node
        return node

    def remove(self, node):
        """"Removing a node from the list, used for normal deletion and eviction"""
        # The node (behind current/the prev node of current) 
        # thats pointing at current should now point to what current is pointing at( the node in front of current)
        # prev ⇌ current ⇌ next
        node.prev.next = node.next
        # the node in front of current (next) should point at the node behind current
        node.next.prev = node.prev
        return True

    def touch(self, node: Node = None, value: Optional[Any] = None):
        """"Reposition a node at the head, when accessed by GET/PUT operations"""
        if value is not None:
            node.value = value

        self.remove(node)
        self.insert(node)
        return node

    def evict(self):
        """"Removing the Least Recently Used node, when max size is reached"""
        LRU_node = self.tail_sentinel.prev
        self.remove(LRU_node)
        return LRU_node.key

    def __iter__(self):
        current = self.head_sentinel.next
        while current != self.tail_sentinel:
            yield current.key, current.value
            current = current.next

    def __str__(self):
        elements = [f"({key} -> {val})" for key, val in self]
        return f"{elements}" if elements else "Empty List"