import socket
import threading
from .store import Store

HOST = ''
PORT = 6767

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
                print(f"Received from {addr}: {data!r}")
                conn.sendall(kache.parse(line))

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
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

if __name__ == "__main__":
    main()