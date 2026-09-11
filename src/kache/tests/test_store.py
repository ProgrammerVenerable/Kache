import pytest
from ..store import Store

@pytest.fixture
def store():
    """Returns a fresh store with a capacity of 3 before every test"""
    return Store(3)

def test_store_initialization(store: Store):
    """Ensures the store starts with the correct capacity and an empty dictionary."""
    assert store.capacity == 3
    assert len(store.kache) == 0

def test_parse_bad_cmds(store: Store):
    """Validates that malformed commands return the correct ERR strings."""
    # Should catch empty commands
    assert store.parse(b" \n") == b"ERR empty command\n"

    # Should catch unknown commands
    assert store.parse(b"do my homework") == b"ERR unknown command\n"
    
    # Should catch syntax errors (missing or extra arguments)
    assert store.parse(b"set car") == b"ERR syntax_error syntax: SET <key> <value>\n"
    assert store.parse(b"set car toyoya model corolla") == b"ERR syntax_error syntax: SET <key> <value>\n"
    
    # Should catch missing keys
    assert store.parse(b"get name") == b"ERR key not found\n"

def test_parse_set_cmds(store: Store):
    """Tests if SET returns OK, rejects duplicates, and saves the value."""
    assert store.parse(b"set name sam") == b"OK\n"
    assert store.parse(b"set name joe") == b"ERR Key already in use\n"
    assert store.parse(b"get name") == b"sam\n"

def test_parse_get_cmds(store: Store):
    """Tests if GET correctly retrieves existing values."""
    store.parse(b"set name Samuel")
    store.parse(b"set job Backend_Dev")
    store.parse(b"set salary 3,000,000")

    assert store.parse(b"get name") == b"Samuel\n"
    assert store.parse(b"get job") == b"Backend_Dev\n"
    assert store.parse(b"get salary") == b"3,000,000\n"

def test_parse_put_cmds(store: Store):
    """Tests if PUT updates an existing key and successfully overwrites the value."""
    store.parse(b"set name Samuel")
    store.parse(b"set job Backend_Dev")
    store.parse(b"set salary 3,000,000")

    assert store.parse(b"put salary 5,000,000") == b"OK\n"
    
    # Ensure the value was actually updated
    assert store.parse(b"get salary") == b"5,000,000\n"

def test_parse_del_cmds(store: Store):
    """Tests if DEL removes a key from the dictionary and linked list."""
    store.parse(b"set name Samuel")
    assert store.parse(b"del name") == b"OK\n"
    
    # Ensure the key is completely gone
    assert store.parse(b"get name") == b"ERR key not found\n"
    assert "name" not in store.kache

# ==========================================
# LRU EVICTION LOGIC TESTS
# ==========================================

def test_lru_straight_eviction(store: Store):
    """Tests that the oldest inserted item is evicted when capacity is exceeded."""
    # Fill to capacity (3)
    store.parse(b"SET A 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")
    
    # Add a 4th item. Expect the "OK" plus the eviction notification.
    response = store.parse(b"SET D 4")
    assert response == b"OK\nMAX CAPACITY REACHED, LRU eviction applied 'A' REMOVED!\n"
    
    # Verify A is gone, but B, C, and D remain
    assert "A" not in store.kache
    assert store.parse(b"GET B") == b"2\n"
    assert store.parse(b"GET C") == b"3\n"
    assert store.parse(b"GET D") == b"4\n"
    
    # Verify the cache size never exceeded capacity
    assert len(store.kache) == 3

def test_lru_get_prevents_eviction(store: Store):
    """Tests that using GET on an older item prevents it from being evicted."""
    store.parse(b"SET A 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")
    
    # Touch A (the oldest). This makes B the new Least Recently Used.
    store.parse(b"GET A") 
    
    # Add a 4th item, which should now evict B, not A.
    response = store.parse(b"SET D 4")
    assert response == b"OK\nMAX CAPACITY REACHED, LRU eviction applied 'B' REMOVED!\n"
    
    # Verify B is gone, but A survived
    assert "B" not in store.kache
    assert store.parse(b"GET A") == b"1\n"
    assert store.parse(b"GET C") == b"3\n"
    assert store.parse(b"GET D") == b"4\n"

def test_lru_put_prevents_eviction(store: Store):
    """Tests that using PUT on an older item also prevents it from being evicted."""
    store.parse(b"SET A 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")
    
    # Update A. This makes B the new Least Recently Used.
    store.parse(b"PUT A 99") 
    
    # Add a 4th item, which should evict B.
    response = store.parse(b"SET D 4")
    assert response == b"OK\nMAX CAPACITY REACHED, LRU eviction applied 'B' REMOVED!\n"
    
    # Verify B is gone, and A survived with its NEW value
    assert "B" not in store.kache
    assert store.parse(b"GET A") == b"99\n"
    assert store.parse(b"GET C") == b"3\n"