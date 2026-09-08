class Store:
    def __init__(self):
        self.kache: dict = {}

    def parse(self, text_line: bytes) -> bytes:
        """Parses the raw incoming bytes and executes the command"""

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

            return b"ERR unknown command\n"

        except Exception as e:
            return f"ERR parsing_error {str(e)}\n".encode()

    def _setter(self, parts: list[str]) -> bytes:
        if len(parts) != 3:
            return b"ERR syntax_error syntax: SET <key> <value>\n"

        _, key, value = parts
        self.kache[key] = value
        return b"OK\n"

    def _getter(self, parts: list[str]) -> bytes:
        if len(parts) != 2:
            return b"ERR syntax_error syntax: GET <key>\n"

        _, key = parts
        if key not in self.kache:
            return b"ERR key not found\n"

        return f"{self.kache[key]}\n".encode()

    def _delete(self, parts: list[str]) -> bytes:
        if len(parts) != 2:
            return b"ERR syntax_error syntax: DEL <key>\n"

        _, key = parts
        if key not in self.kache:
            return b"key not found\n"

        del self.kache[key]
        return b"OK\n"