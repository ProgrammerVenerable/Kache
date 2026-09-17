import pytest
import concurrent.futures
import threading
from unittest.mock import MagicMock, call
import socket
import time

from kache.server import main
from kache.store import Store
from kache.server import handle_clients

# ==========================================
# 1. THREAD SAFETY TESTS
# ==========================================

def test_store_thread_safety():
    """
    Simulates 100 clients concurrently setting unique keys.
    If the threading.Lock() in Store is missing or broken, 
    the linked list will lose nodes and the dictionary size will be wrong.
    """
    store = Store(capacity=100)
    
    def worker(client_id):
        # Each thread attempts to set a unique key-value pair
        cmd = f"SET key_{client_id} {client_id}\n".encode()
        store.parse(cmd)
        
    # Spin up 100 threads simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        # map() executes the worker function for every number from 0 to 99
        executor.map(worker, range(100))
        
    # If the lock held, we should have exactly 100 items
    assert len(store.kache) == 100
    
    # Spot-check a random key to ensure it processed correctly
    assert store.parse(b"GET key_50") == b"50\n"

# ==========================================
# 2. NETWORK LAYER TESTS (MOCKING)
# ==========================================

def test_handle_clients_parsing():
    """
    Mocks a socket connection to test if the server correctly buffers, 
    splits commands by newline, and sends back the right responses.
    """
    store = Store(capacity=10)
    
    # 1. Create a fake socket
    mock_socket = MagicMock()
    
    # 2. Program the fake socket's behavior for .recv()
    # It will return the first string, then the second string, then an empty string.
    # (An empty string tells handle_clients that the connection closed).
    mock_socket.recv.side_effect = [
        b"SET name Ali",       # First packet (incomplete command)
        b"ce\nGET name\n",     # Second packet (completes SET, adds a GET)
        b""                    # Third packet (client disconnects)
    ]
    
    # 3. Run the function (we pass a dummy string for the address)
    handle_clients(mock_socket, "127.0.0.1", store)
    
    # 4. Assert that the server sent back the correct responses in the correct order
    expected_responses = [
        call(b"OK\n"),         # Response to SET
        call(b"Alice\n")       # Response to GET
    ]
    
    # assert_has_calls checks that sendall was called with exactly these arguments
    mock_socket.sendall.assert_has_calls(expected_responses, any_order=False)

# ==========================================
# 3. END-TO-END INTEGRATION TEST
# ==========================================

@pytest.fixture(scope="module")
def live_server():
    """
    Starts the actual server in a background thread before the tests run.
    The scope="module" means it spins up once for this entire test file,
    rather than restarting for every single test function.
    """
    # Start the server as a daemon thread so it automatically dies 
    # when pytest finishes running and exits.
    server_thread = threading.Thread(target=main, daemon=True)
    server_thread.start()
    
    # Give the operating system a fraction of a second to bind the socket to port 6767
    time.sleep(0.5) 
    
    # 'yield' hands control over to the test functions.
    yield 
    
    # Normally we would put teardown code here, but because the thread is a daemon,
    # Python will clean it up for us automatically when the test suite ends.

def test_full_client_server_interaction(live_server):
    """
    Connects to the live server using a real TCP socket, 
    sends raw bytes, and waits for the actual network responses.
    """
    HOST = 'localhost'
    PORT = 6767
    
    # Create a real client socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        
        # 1. Test SET
        client_socket.sendall(b"SET test_key 100\n")
        response = client_socket.recv(1024)
        assert response == b"OK\n"
        
        # 2. Test GET
        client_socket.sendall(b"GET test_key\n")
        response = client_socket.recv(1024)
        assert response == b"100\n"
        
        # 3. Test Unknown Command
        client_socket.sendall(b"PING\n")
        response = client_socket.recv(1024)
        assert response == b"ERR unknown command\n"
        
        # 4. Test multiple commands sent in a single burst (tests your buffer logic live)
        client_socket.sendall(b"SET multi 999\nGET multi\n")
        
        # First response from the buffer
        response1 = client_socket.recv(1024)
        assert response1 == b"OK\n"
        
        # Second response from the buffer
        response2 = client_socket.recv(1024)
        assert response2 == b"999\n"