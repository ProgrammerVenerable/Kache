import socket
import threading
from .store import Store

def handle_clients(conn: socket.socket, addr, kache: Store):
    print(f"Connected by {addr}")
    buffer = b""
    with conn:
        while True:
            data = conn.recv(1024)
            if not data: 
                print(f"Connection with {addr} closed")
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                print(f"Received from {addr}: {line!r}")
                conn.sendall(kache.parse(line))

def main(host='', port=6767):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        kache = Store(10)
        try:
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(
                    target=handle_clients, args=(conn, addr, kache), daemon=True
                )

                thread.start()
        except KeyboardInterrupt:
            print("\nShutting down server...")

        finally:
            # This block ALWAYS runs before the program exits,
            # even if an unexpected exception crashed the 'while' loop!
            print("Cleaning up cache background threads...")
            kache.shutdown()
            print("Shutdown complete. Goodbye!")

if __name__ == "__main__":
    main()