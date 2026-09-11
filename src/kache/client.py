import socket

HOST = 'localhost'
PORT = 6767

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Connected to {HOST}:{PORT}. Type a message and press Enter.")
        print(f"Type 'quit' or press ctrl + c to exit.\n")

        try:
            while True:
                message = input("> ")
                if message.lower() == "quit":
                    print("Closing connection...")
                    break
                s.sendall((message + "\n").encode())
                data = s.recv(1024)
                if not data:
                    print("Server closed the connection")
                    break
                print(f"\t{repr(data)}")
        except KeyboardInterrupt:
            print("Closing connection...")

if __name__ == "__main__":
    main()