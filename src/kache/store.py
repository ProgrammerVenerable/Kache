from .mylist import DLL
from .node import Node
import threading
class Store:
    def __init__(self, capacity: int):
        self.capacity = capacity
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        self.kache: dict[str, Node] = {}
        self._linked_list = DLL()
        self._lock = threading.Lock()

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

                return b"ERR unknown command\n"

            except Exception as e:
                return f"ERR parsing_error {str(e)}\n".encode()

    def _setter(self, parts: list[str]) -> bytes:
        """Creates a new entry in the dict and list"""
        if len(parts) != 3:
            return b"ERR syntax_error syntax: SET <key> <value>\n"
        _, key, value = parts
        if key in self.kache:
            return b"ERR Key already in use\n"

        notify = ""
        if len(self.kache) == self.capacity:
            ev_key = self._linked_list.evict()
            del self.kache[ev_key]
            notify = f"MAX CAPACITY REACHED, LRU eviction applied '{ev_key}' REMOVED!\n"
        
        self.kache[key] = self._linked_list.insert(Node(key, value))
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

        if key not in self.kache:
            return b"ERR key not found\n"

        node: Node = self._linked_list.touch(self.kache[key])
        value = node.value

        return f"{value}\n".encode()

    def _putter(self, parts: list[str]) -> bytes:
        """"Updates the value of a key"""
        if len(parts) != 3:
            return b"ERR syntax_error syntax: PUT <key> <value>\n"

        _, key, value = parts
        if key not in self.kache:
            return b"ERR key not found\n"
        
        self.kache[key] = self._linked_list.touch(self.kache[key], value)
        return b"OK\n"

    def _delete(self, parts: list[str]) -> bytes:
        """Deletes a key and its node"""
        if len(parts) != 2:
            return b"ERR syntax_error syntax: DEL <key>\n"

        _, key = parts
        if key not in self.kache:
            return b"ERR key not found\n"

        self._linked_list.remove(self.kache[key])
        del self.kache[key]
        return b"OK\n"