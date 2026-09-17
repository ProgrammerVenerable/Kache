import pytest
from kache.mylist import DLL
from kache.node import Node

def test_dll_initialization():
    dll = DLL()

    # If the head_sen points to the tail
    assert dll.head_sentinel.next == dll.tail_sentinel

    # likewise if the tail points to the head
    assert dll.tail_sentinel.prev == dll.head_sentinel
    assert str(dll) == "Empty List"

def test_dll_insert():
    """If nodes can be succesfully inserted into the list"""
    dll = DLL()

    node = Node("name", "sam")

    dll.insert(node)

    # if the head_sen points to the newly added node
    assert dll.head_sentinel.next == node
    # if the node pints back to the head
    assert node.prev == dll.head_sentinel

    # does the node point to the tail
    assert node.next == dll.tail_sentinel

    # does the tail point to the new node
    assert dll.tail_sentinel.prev == node

def test_dll_multipe_insert():
    """Insert logic with multiple nodes"""
    dll = DLL()

    n1 = Node("name", "sam")
    n2 = Node("age", 19)
    n3 = Node("bench", "170")
    n4 = Node("favourite manhwa", "Absolute Regression")

    dll.insert(n1)
    dll.insert(n2)
    dll.insert(n3)
    dll.insert(n4)

    # does the head point to the most recent node, n4
    assert dll.head_sentinel.next == n4
    # does n4 point back to the head
    assert n4.prev == dll.head_sentinel

    # does it point to its adjacent node n3
    assert n4.next == n3
    # does the tail point to the least recently accessed node, n1, which is also the first
    assert dll.tail_sentinel.prev == n1
    # does n1 point back to the tail
    assert n1.next == dll.tail_sentinel

    # Do all the element look like the expected iterable form
    assert list(dll) == [
        ("favourite manhwa", "Absolute Regression"),
        ("bench", "170"),
        ("age", 19),
        ("name", "sam")
    ]
def test_remove_only_node():
    """Removes only one node to verify HEAD ⇄ TAIL"""
    dll = DLL()
    node = Node("A", 1)

    dll.insert(node)
    dll.remove(node)

    assert dll.head_sentinel.next == dll.tail_sentinel
    assert dll.tail_sentinel.prev == dll.head_sentinel
    assert str(dll) == "Empty List"

def test_dll_remove():
    """Tests if remove works"""
    dll = DLL()
    
    n1 = Node("name", "sam")
    n2 = Node("age", 19)
    n3 = Node("bench", "170")
    n4 = Node("favourite manhwa", "Absolute Regression")
    
    dll.insert(n1)
    dll.insert(n2)
    dll.insert(n3)
    dll.insert(n4)
    dll.remove(n2)

    assert list(dll) == [
        ("favourite manhwa", "Absolute Regression"),
        ("bench", "170"),
        ("name", "sam")
    ]

def test_dll_multiple_removes():
    """Tests if list follows remove logic with multiple values removed"""
    dll = DLL()

    n1 = Node("name", "sam")
    n2 = Node("age", 19)
    n3 = Node("bench", "170")
    n4 = Node("favourite manhwa", "Absolute Regression")
    
    dll.insert(n1)
    dll.insert(n2)
    dll.insert(n3)
    dll.insert(n4)
    dll.remove(n1)
    dll.remove(n4)

    assert dll.head_sentinel.next == n3
    assert n3.prev == dll.head_sentinel

    assert n3.next == n2
    assert dll.tail_sentinel.prev == n2
    assert n2.next == dll.tail_sentinel

    assert list(dll) == [
        ("bench", "170"),
        ("age", 19)
    ]

def test_remove_head_node():
    dll = DLL()

    n1 = Node("A", 1)
    n2 = Node("B", 2)
    n3 = Node("C", 3)

    dll.insert(n1)
    dll.insert(n2)
    dll.insert(n3)

    dll.remove(n3)

    assert dll.head_sentinel.next == n2
    assert n2.prev == dll.head_sentinel
    assert list(dll) == [
        ("B", 2),
        ("A", 1)
    ]

def test_dll_touch():
    """Checks if accessing a node will change it to most 
    recently accessed/or the node after the head"""

    dll = DLL()

    n1 = Node("name", "sam")
    n2 = Node("age", 19)
    n3 = Node("bench", "170")
    n4 = Node("favourite manhwa", "Absolute Regression")

    dll.insert(n1)
    dll.insert(n2)
    dll.insert(n3)
    dll.insert(n4)

    # Currently the most recent node is n4
    assert dll.head_sentinel.next == n4

    
    dll.touch(n1)

    # does n1 become the most recently accessed node after touch
    assert dll.head_sentinel.next == n1

    # will the form change to name(n1), being at the top
    assert list(dll) == [
            ("name", "sam"),
            ("favourite manhwa", "Absolute Regression"),
            ("bench", "170"),
            ("age", 19)
        ]

    dll.touch(n3)

    # will it work for another node
    assert dll.head_sentinel.next == n3

    assert list(dll) == [
            ("bench", "170"),
            ("name", "sam"),
            ("favourite manhwa", "Absolute Regression"),
            ("age", 19)
        ]
def test_touch_head():
    """Checks if nothing unexpexted happens why you touch the MRU"""
    dll = DLL()

    n1 = Node("A", 1)
    n2 = Node("B", 2)

    dll.insert(n1)
    dll.insert(n2)

    dll.touch(n2)

    assert list(dll) == [
        ("B", 2),
        ("A", 1)
    ]

    assert dll.head_sentinel.next == n2
    assert dll.tail_sentinel.prev == n1

def test_touch_tail():
    dll = DLL()

    n1 = Node("A", 1)
    n2 = Node("B", 2)
    n3 = Node("C", 3)

    dll.insert(n1)
    dll.insert(n2)
    dll.insert(n3)

    assert dll.tail_sentinel.prev == n1

    dll.touch(n1)

    assert dll.head_sentinel.next == n1
    assert dll.tail_sentinel.prev == n2

    assert list(dll) == [
        ("A", 1),
        ("C", 3),
        ("B", 2)
    ]

def test_touch_updates_value():
    """Tests if using touch with value updates the nodes value"""
    dll = DLL()

    node = Node("name", "Samuel")

    dll.insert(node)

    # value is now Samuel
    assert node.value == "Samuel"

    # accesses name and updates it with a new vlaue
    dll.touch(node, "John")

    # value should now be John, instead of Samuel
    assert node.value == "John"

    assert list(dll) == [
        ("name", "John")
    ]

def test_evict_removes_lru_node():
    """Tests if evict removes the least recently 
    accessed node/the node at the tail"""
    dll = DLL()

    node_a = Node("A", 1)
    node_b = Node("B", 2)
    node_c = Node("C", 3)

    dll.insert(node_a)
    dll.insert(node_b)
    dll.insert(node_c)

    # node_a is the current least recently accessed node
    assert dll.tail_sentinel.prev == node_a

    evicted_key = dll.evict()

    # is A the one removed
    assert evicted_key == "A"
    assert list(dll) == [
        ("C", 3),
        ("B", 2),
    ]

def test_lru_behavior():
    dll = DLL()

    node_a = Node("A", 1)
    node_b = Node("B", 2)
    node_c = Node("C", 3)

    dll.insert(node_a)
    dll.insert(node_b)
    dll.insert(node_c)

    # Making b MRA(Most Recently Accessed) node
    dll.touch(node_b)

    assert list(dll) == [
        ("B", 2),
        ("C", 3),
        ("A", 1),
    ]

    # evict LRA, should be A
    evicted = dll.evict()

    # is it really A
    assert evicted == "A"

    assert list(dll) == [
        ("B", 2),
        ("C", 3),
    ]