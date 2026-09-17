import argparse
import sys

from .server import main as run_server
from .client import main as run_client

def main():
    parser = argparse.ArgumentParser(description="Kache - A custom key-value store")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Server parser (defaults to 6767 port)
    server_parser = subparsers.add_parser("server", help="Start the Kache server")
    server_parser.add_argument("--host", type=str, default="", help="Host to bind to (default: all interfaces)")
    server_parser.add_argument("--port", type=int, default=6767, help="Port to listen on (default: 6767)")

    # Client parser
    client_parser = subparsers.add_parser("client", help="Connect to the Kache server")
    client_parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host to connect to (default: 127.0.0.1)")
    client_parser.add_argument("--port", type=int, default=6767, help="Server port to connect to (default: 6767)")

    args = parser.parse_args()

    if args.command == "server":
        run_server(host=args.host, port=args.port)
        
    elif args.command == "client":
        run_client(host=args.host, port=args.port)
        
    else:
        # Show help if `python -m kache` is typed
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()