import pytest
from ..store import Store
import time

@pytest.fixture
def store():
    """Returns a fresh store with a capacity of 3 before every test 
    with a fast cleanup interval for testing.
    Crucially, ensures the background thread is shut down after each test."""
    s = Store(capacity=3, cleanup_interval=0.1)
    yield s
    s.shutdown()

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
    assert store.parse(b"set car") == b"ERR syntax_error syntax: SET <key> <value> [OPTIONAL] EX <time_in_seconds>\n"
    assert store.parse(b"set car toyoya model corolla") == b"ERR syntax_error syntax: SET <key> <value> [OPTIONAL] EX <time_in_seconds>\n"
    
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


def test_put_updates_lru_order(store):
    store.parse(b"SET A 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")

    store.parse(b"PUT A 99")

    assert list(store._linked_list) == [
        ("A", "99"),
        ("C", "3"),
        ("B", "2")
    ]

def test_get_updates_lru_order(store):
    store.parse(b"SET A 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")

    store.parse(b"GET A")

    assert list(store._linked_list) == [
        ("A", "1"),
        ("C", "3"),
        ("B", "2")
    ]

def test_dict_and_dll_stay_in_sync(store):
    store.parse(b"SET A 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")

    assert set(store.kache.keys()) == {
        key for key, value in store._linked_list
    }

    store.parse(b"DEL B")

    assert set(store.kache.keys()) == {
        key for key, value in store._linked_list
    }

    store.parse(b"SET D 4")

    assert set(store.kache.keys()) == {
        key for key, value in store._linked_list
    }

def test_put_preserves_ttl(store):
    store.parse(b"SET A 1 EX 2")

    original_expiry = store.kache["A"].expires_at

    time.sleep(0.1)

    store.parse(b"PUT A 999")

    assert store.kache["A"].expires_at == original_expiry

# ==========================================
# TTL & EXPIRATION TESTS
# ==========================================

def test_ttl_parsing_errors(store: Store):
    """Ensures bad TTL syntax is caught by the parser."""
    # Bad EX flag
    assert store.parse(b"SET A 1 IN 5") == b"ERR syntax_error syntax: SET <key> <value> [OPTIONAL] EX <time_in_seconds>\n"
    
    # Non-integer TTL
    assert store.parse(b"SET A 1 EX five") == b"ERR ttl must be an integer (seconds)\n"
    
    # Negative or Zero TTL
    assert store.parse(b"SET A 1 EX 0") == b"ERR ttl must be a positive integer\n"
    assert store.parse(b"EXPIRE A -5") == b"ERR key not found\n" # Because A isn't set yet

def test_lazy_expiration(store: Store):
    """Tests if GET correctly identifies an expired key and deletes it."""
    store.parse(b"SET A 1 EX 1")
    
    # Immediately accessible
    assert store.parse(b"GET A") == b"1\n"
    
    # Wait for the TTL to expire
    time.sleep(1.1)
    
    # GET should now trigger the lazy deletion and return not found
    assert store.parse(b"GET A") == b"ERR key not found\n"
    assert "A" not in store.kache

def test_ttl_command(store: Store):
    """Tests the TTL command for both temporary and permanent keys."""
    store.parse(b"SET temp 99 EX 5")
    store.parse(b"SET perm 100")
    
    # Check temporary key (should be 5 seconds)
    ttl_response = store.parse(b"TTL temp")
    assert ttl_response == b"5 seconds\n" or ttl_response == b"4 seconds\n"
    
    # Check permanent key
    assert store.parse(b"TTL perm") == b"Node is permanent\n"

def test_expire_and_persist_commands(store: Store):
    """Tests modifying the lifespan of an existing key."""
    store.parse(b"SET mykey val")
    
    # 1. Apply a TTL to a permanent key
    assert store.parse(b"EXPIRE mykey 1") == b"OK\n"
    
    # Verify it was applied
    ttl_res = store.parse(b"TTL mykey")
    assert b"seconds" in ttl_res
    
    # 2. Make it permanent again before it dies
    assert store.parse(b"PERSIST mykey") == b"OK\n"
    assert store.parse(b"TTL mykey") == b"Node is permanent\n"
    
    # 3. Wait 1.1 seconds. Since it is persistent, it should survive.
    time.sleep(1.1)
    assert store.parse(b"GET mykey") == b"val\n"

def test_background_sweeper(store: Store):
    """
    Tests active expiration. Proves the background thread deletes 
    expired keys even if the client never calls GET.
    """
    store.parse(b"SET ghost boo EX 1")
    
    # Prove it's in the underlying dictionary
    assert "ghost" in store.kache
    
    # Sleep long enough for the key to expire AND the background 
    # thread to wake up (cleanup_interval is 0.1s in our fixture)
    time.sleep(1.2)
    
    # Checks the dictionary directly. We are NOT calling store.parse("GET ghost"),
    # which proves the background thread did the cleanup, not lazy deletion!
    assert "ghost" not in store.kache

def test_expire_resets_existing_ttl(store):
    store.parse(b"SET A 1 EX 10")

    old_expiry = store.kache["A"].expires_at

    time.sleep(0.1)

    store.parse(b"EXPIRE A 30")

    new_expiry = store.kache["A"].expires_at

    assert new_expiry > old_expiry

def test_expired_key_cannot_be_put(store):
    store.parse(b"SET A 1 EX 1")

    time.sleep(1.1)

    assert store.parse(b"PUT A 2") == b"ERR key not found\n"
    assert "A" not in store.kache

def test_expired_key_cannot_be_deleted(store):
    store.parse(b"SET A 1 EX 1")

    time.sleep(1.1)

    assert store.parse(b"DEL A") == b"ERR key not found\n"
    assert "A" not in store.kache

def test_expired_key_does_not_consume_capacity(store):
    store.parse(b"SET A 1 EX 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")

    time.sleep(1.1)

    store.parse(b"SET D 4")

    assert "A" not in store.kache
    assert "B" in store.kache
    assert "C" in store.kache
    assert "D" in store.kache

def test_invalid_capacity():
    with pytest.raises(ValueError):
        Store(0)

    with pytest.raises(ValueError):
        Store(-1)

def test_persist_permanent_key(store):
    store.parse(b"SET A 1")

    assert store.parse(b"PERSIST A") == b"Node is already permanent\n"

def test_expire_invalid_ttl(store):
    store.parse(b"SET A 1")

    assert store.parse(b"EXPIRE A 0") == (
        b"ERR ttl must be a positive integer\n"
    )

    assert store.parse(b"EXPIRE A -5") == (
        b"ERR ttl must be a positive integer\n"
    )

    assert store.parse(b"EXPIRE A five") == (
        b"ERR ttl must be an integer (seconds)\n"
    )

def assert_store_consistent(store):
    dll_keys = [key for key, _ in store._linked_list]

    assert set(dll_keys) == set(store.kache.keys())
    assert len(dll_keys) == len(set(dll_keys))
    assert len(store.kache) <= store.capacity

    for key in dll_keys:
        assert store.kache[key].key == key

def test_cache_consistency(store):
    store.parse(b"SET A 1")
    store.parse(b"SET B 2")
    store.parse(b"SET C 3")

    assert_store_consistent(store)

    store.parse(b"GET A")
    assert_store_consistent(store)

    store.parse(b"PUT B 20")
    assert_store_consistent(store)

    store.parse(b"DEL C")
    assert_store_consistent(store)

    store.parse(b"SET D 4")
    assert_store_consistent(store)

def test_unicode_values(store):
    assert store.parse("SET greeting こんにちは".encode()) == b"OK\n"
    assert store.parse("GET greeting".encode()) == "こんにちは\n".encode()

def test_unicode_key(store):
    assert store.parse("SET prénom Samuel".encode()) == b"OK\n"
    assert store.parse("GET prénom".encode()) == "Samuel\n".encode()