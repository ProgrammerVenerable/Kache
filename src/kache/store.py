from .mylist import DLL
from .node import Node
import json
import os
import tempfile
import threading
import traceback
import time
class Store:
    def __init__(self, capacity: int, cleanup_interval = 5, save_file = 'save.json'):
        self.capacity = capacity
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        self.kache: dict[str, Node] = {}
        self._linked_list = DLL()
        self._lock = threading.Lock()
        self.save_file = save_file 
        if self.save_file:
            self._load_snapshot()
        self._snapshot_trigger_event = threading.Event()
        self._snapshot_stop_event = threading.Event()
        self._snapshot_thread = threading.Thread(target=self._snapshot, daemon=True)

        self._cleanup_interval = cleanup_interval
        self._stop_event = threading.Event()

        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True) #so when the main program dies it dies too
        self._cleanup_thread.start()
        self._snapshot_thread.start()

    def parse(self, text_line: bytes) -> bytes:
        """Parses the raw incoming bytes and executes the command"""

        with self._lock:
            try:
                # strips the text of any unneccessary whitespaces
                decoded_line = text_line.decode().strip()
                if decoded_line == "":
                    return b"ERR empty command\n"

                # splits the the decoded line into parts e.g SET user:alice
                parts = decoded_line.split()
                # extrracts the command
                command = parts[0].upper()

                if command == "SET":
                    return self._setter(parts)

                if command == "GET":
                    return self._getter(parts)

                if command == "DEL":
                    return self._delete(parts)

                if command == "PUT":
                    return self._putter(parts)

                if command == "TTL":
                    return self._time_left(parts)

                if command == "EXPIRE":
                    return self._expire(parts)

                if command == "PERSIST":
                    return self._persist(parts)

                return b"ERR unknown command\n"

            except Exception as e:
                traceback.print_exc()
                return f"ERR parsing_error {str(e)}\n".encode()

    def _snapshot(self):
        """Saves a snapshot of hte dictionary to disk"""
        if not self.save_file:
            return
        while not self._snapshot_stop_event.is_set():

            # Wait for either a manual trigger or a timer
            self._snapshot_trigger_event.wait(300)
            # if manual, should always clear to prevent infinite writes
            self._snapshot_trigger_event.clear()


            data_to_save = []
            with self._lock:
                current_node = self._linked_list.head_sentinel.next

                while current_node != self._linked_list.tail_sentinel:
                    data_to_save.append({
                        "key": current_node.key,
                        "value": current_node.value,
                        "expires_at": current_node.expires_at
                    })

                    current_node = current_node.next

            # Perform file I/O outside the lock so cache operations aren't blocked
            try:
                save_dir = os.path.dirname(self.save_file) or '.'

                # Write to a temporary file first, then atomically replace the old save
                # This prevents a corrupted save.json if the server crashes mid-write
                with tempfile.NamedTemporaryFile('w', delete=False, dir=save_dir) as tmp:
                    json.dump(data_to_save, tmp)
                    temp_name = tmp.name

                os.replace(temp_name, self.save_file)

            except Exception:
                traceback.print_exc()
                # Clean up the orphan temp file if something failed before the replace
                if 'temp_name' in locals() and os.path.exists(temp_name):
                    os.remove(temp_name)

            if self._snapshot_stop_event.is_set():
                break

    def _load_snapshot(self):
        """Loads the snapshot from disk on startup."""

        # If save doesn't exist, it is the first run, so return
        if not self.save_file or not os.path.exists(self.save_file):
            return

        with self._lock:
            try:
                with open(self.save_file, 'r') as f:
                    saved_data = json.load(f)

                # We iterate backwards (from Least Recently Used to Most Recently Used).
                # If your standard DLL insertion puts new items at the 'head' (MRU),
                # inserting them in reverse order ensures the true MRU ends up at the head.

                for item in reversed(saved_data):
                    key = item["key"]
                    value = item["value"]
                    expires_at = item["expires_at"]

                    node = Node(key=key, value=value)
                    if expires_at is not None:
                        node.expires_at = expires_at
                        
                    # If a node expired while the server was offline remove/ignore it
                    if self.is_expired(node):
                        continue

                    self.kache[key] = node
                    self._linked_list.insert(node)

            except json.JSONDecodeError:
                print("ERR: save.json is corrupted. Starting with empty cache.")
            except Exception as e:
                traceback.print_exc()


    def _cleanup_worker(self):
        """Runs in the background and periodically triggers a cleanup sweep."""

        # Loop until the stop event is set
        while not self._stop_event.is_set():

            # Wait acts like time.sleep(), but can be interrupted instantly
            self._stop_event.wait(self._cleanup_interval)

            if not self._stop_event.is_set():
                self._sweep_expired_keys()

    def _sweep_expired_keys(self):
        """Iterates through the cache and removes expired keys thread-safely."""

        # By wrapping the iteration in with self._lock:, 
        # you guarantee that a user isn't halfway through a GET or SET operation 
        # while the cleaner is deleting nodes.
        with self._lock:
            # We must use list() to create a copy of the keys. 
            # Modifying a dictionary's size while iterating over it throws a RuntimeError.
            keys = list(self.kache.keys())

            for key in keys:
                node = self.kache[key]
                if self.is_expired(node):
                    self._evict_key(node.key)

    def shutdown(self):
        """Signals the background thread to stop and waits for it to finish."""
        self._stop_event.set()
        self._snapshot_stop_event.set() 
        self._snapshot_trigger_event.set() # <-- wakes wait() immediately instead of waiting up to 300s
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join()
        if self._snapshot_thread.is_alive():
            self._snapshot_thread.join()

    @staticmethod
    def is_expired(node: Node) -> bool:
        """Checks if a node has expired"""
        if node.expires_at is None:
            return False

        if time.time() >= node.expires_at:
            return True

        return False
    
    def _get_valid_node(self, key: str) -> Node | None:
            """Returns the node if it exists and is not expired, cleaning it up if it is."""
            if key not in self.kache:
                return None
                
            node = self.kache[key]
            if self.is_expired(node):
                self._evict_key(key)
                return None
                
            return node
    def _evict_key(self, key):
        node = self.kache[key]
        self._linked_list.remove(node)
        del self.kache[key]

    def _setter(self, parts: list[str]) -> bytes:
        """Creates a new entry in the dict and list"""
        if len(parts) != 3 and len(parts) != 5:
            return b"ERR syntax_error syntax: SET <key> <value> [OPTIONAL] EX <time_in_seconds>\n"

        # If it follows the optional syntax
        if len(parts) == 5:
            _, key, value, ex_flag, ttl_str = parts
            # Checks if the flag used is actually EX
            if ex_flag.upper() != "EX":
                return b"ERR syntax_error syntax: SET <key> <value> [OPTIONAL] EX <time_in_seconds>\n"
            # Then tries to convert it into a integer
            try:
                ttl = int(ttl_str)
            except ValueError:
                return b"ERR ttl must be an integer (seconds)\n"
            
            if ttl <= 0:
                return b"ERR ttl must be a positive integer\n"
            
        else:
            _, key, value = parts

        if self._get_valid_node(key) is not None:
            return b"ERR Key already in use\n"

        notify = ""
        if len(self.kache) == self.capacity:
            ev_key = self._linked_list.evict()
            del self.kache[ev_key]
            notify = f"MAX CAPACITY REACHED, LRU eviction applied '{ev_key}' REMOVED!\n"

        if len(parts) == 5:
            node = Node(key, value, ttl)
        else:
            node = Node(key, value)
        self.kache[key] = self._linked_list.insert(node)
        response = "OK\n" + notify
        return response.encode()

    def _getter(self, parts: list[str]) -> bytes:
        """"Gets the value from the given key"""
        if len(parts) != 2:
            return b"ERR syntax_error syntax: GET <key>\n"

        _, key = parts

        # For tests
        if key == "/all":
            return f"{self._linked_list}".encode()

        node = self._get_valid_node(key)
        if not node:
            return b"ERR key not found\n"

        node: Node = self._linked_list.touch(self.kache[key])
        value = node.value

        return f"{value}\n".encode()

    def _putter(self, parts: list[str]) -> bytes:
        """"Updates the value of a key"""
        if len(parts) != 3:
            return b"ERR syntax_error syntax: PUT <key> <value>\n"

        _, key, value = parts
        node = self._get_valid_node(key)
        if not node:
            return b"ERR key not found\n"
        
        self.kache[key] = self._linked_list.touch(self.kache[key], value)
        return b"OK\n"

    def _delete(self, parts: list[str]) -> bytes:
        """Deletes a key and its node"""
        if len(parts) != 2:
            return b"ERR syntax_error syntax: DEL <key>\n"

        _, key = parts
        if self._get_valid_node(key) is None:
            return b"ERR key not found\n"

        self._evict_key(key)
        return b"OK\n"

    def _time_left(self, parts: list[str]) -> bytes:
        """Shows how much time is left before a key expires"""
        if len(parts) != 2:
            return b"ERR syntax_error syntax: TTL <key>\n"

        _, key = parts
        node = self._get_valid_node(key)
        if node is None:
            return b"ERR key not found\n"

        if node.expires_at is None:
            return b"Node is permanent\n"

        remaining = remaining = int(node.expires_at - time.time())
        return f"{remaining:.0f} seconds\n".encode()

    def _expire(self, parts: list[str]) -> bytes:
        """Edits the expires_at field of any node"""
        if len(parts) != 3:
            return b"ERR syntax_error syntax: EXPIRE <key> <time_in_seconds>\n"

        _, key, ttl_str = parts
        node = self._get_valid_node(key)
        if not node:
            return b"ERR key not found\n"
   
        try:
            ttl = int(ttl_str)
        except ValueError:
            return b"ERR ttl must be an integer (seconds)\n"
            
        if ttl <= 0:
            return b"ERR ttl must be a positive integer\n"
        node: Node = self._linked_list.touch(self.kache[key])
        node.expires_at = time.time() + ttl
        return b"OK\n"

    def _persist(self, parts: list[str]) -> bytes:
        """Makes a node permanent with no expiry"""
        if len(parts) != 2:
            return b"ERR syntax_error syntax: PERSIST <key>\n"

        _, key = parts
        node = self._get_valid_node(key)
        if not node:
            return b"ERR key not found\n"
   
        if node.expires_at is None:
            return b"Node is already permanent\n"

        node: Node = self._linked_list.touch(self.kache[key])
        node.expires_at = None
        return b"OK\n"