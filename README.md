# Kache

A Redis-inspired in-memory cache server built from raw TCP sockets — no frameworks.

Implemented:
- **LRU (Least Recently Used)** eviction
- **TTL (Time to Live)** expiry
- **Crash-safe snapshotting** to disk

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/ProgrammerVenerable/Kache
cd kache
```

### 2. Install dependencies

This project uses **uv** for dependency management.

If you already have uv installed:

```bash
uv sync
```

This creates the project's virtual environment and installs the dependencies specified by the project configuration and lock file.

### 3. Run the server and client

In one terminal, start the server:

```bash
uv run python -m kache server
```

In another terminal, connect a client:

```bash
uv run python -m kache client
```

## Commands

| Command | Syntax | Description |
|---|---|---|
| `SET` | `SET <key> <value> [EX <seconds>]` | Store a key, optionally with a TTL |
| `GET` | `GET <key>` | Retrieve a value |
| `PUT` | `PUT <key> <value>` | Update the value of an existing key |
| `DEL` | `DEL <key>` | Delete a key |
| `TTL` | `TTL <key>` | Show remaining time before expiry |
| `EXPIRE` | `EXPIRE <key> <seconds>` | Set or update a key's expiry |
| `PERSIST` | `PERSIST <key>` | Remove a key's expiry, making it permanent |

### Examples

**SET** — store a key and value:
```text
> SET name Samuel
OK
```

Optionally attach an expiry, in seconds:
```text
> SET age 19 EX 60
OK
```

**GET** — retrieve a value:
```text
> GET name
Samuel
```

**PUT** — update an existing key's value:
```text
> PUT name John
OK
```

**DEL** — remove a key:
```text
> DEL name
OK
```

**TTL** — check remaining time before expiry:
```text
> TTL age
60 seconds
```
Returns `Node is permanent` if no expiry was set.

**EXPIRE** — set or update a key's expiry:
```text
> EXPIRE age 120
OK
```

**PERSIST** — remove a key's expiry, making it permanent:
```text
> PERSIST age
OK
```

## Design Decisions

**1. Dict + doubly linked list for LRU.**
The store pairs a `dict` (for O(1) key lookup) with a doubly linked list (for O(1) reordering and eviction). A plain dict alone can't tell you which key was least recently used without an O(n) scan; the linked list keeps the "most recent" and "least recent" ends in constant reach, so `SET`, `GET`, and eviction all stay O(1).

**2. TTL via a lazy check plus a background sweep.**
Each node stores an `expires_at` timestamp. Reads check it lazily (`_get_valid_node` evicts an expired key the moment something tries to access it), but a lazy check alone means an expired key that nobody touches sits in memory forever. To close that gap, a background thread periodically sweeps the whole cache and evicts anything expired, whether or not a client ever asked for it.

**3. A single lock guarding all mutating operations.**
Every command that reads or mutates the store runs under one `threading.Lock`. This keeps the implementation simple and rules out race conditions between concurrent clients and the background threads (cleanup and snapshotting), at the cost of serializing all operations. Under many concurrent clients, this lock is the throughput ceiling; a more scalable design would shard the keyspace across multiple locks or move to a single-threaded event loop (asyncio) instead of one thread per client.

**4. Atomic snapshotting for crash-safe persistence.**
A background thread periodically writes the entire cache to `save.json`, and reloads it on startup. To avoid ever leaving a half-written, corrupted snapshot on disk (e.g. if the process dies mid-write), the snapshot is first written to a temporary file and then moved into place with `os.replace`, which is atomic on POSIX systems, the on-disk file is always either the old complete snapshot or the new complete one, never something in between.

**5. Two separate events to coordinate the snapshot thread's shutdown.**
The background snapshot thread originally used a single `threading.Event` for both "time to take a snapshot" and "time to shut down." That conflated two different signals: clearing the event to acknowledge a snapshot also erased the shutdown signal, so `shutdown()` could hang indefinitely waiting on a thread that never noticed it was told to stop. The fix was to give the thread two independent events, one purely for the periodic/manual snapshot trigger, one purely for shutdown. Thus acknowledging one can never accidentally cancel the other.

## Known Limitations

- **Snapshotting can lose recent writes on a hard crash.** Snapshots are taken periodically (every 5 minutes) and on graceful shutdown. A `Ctrl+C` or clean `shutdown()` call always flushes state to disk first, but a hard failure, `kill -9`, a segfault, a power loss, loses anything written since the last snapshot. A full append-only log (AOF-style), logging every mutating command as it happens, would close this gap at the cost of a disk write per command.
- **The client assumes one `recv()` call returns one full response.** This holds for the short, fast replies this protocol currently sends, but it isn't a guarantee TCP makes in general. A response could arrive split across multiple reads, or multiple responses could arrive coalesced into one. A length-prefixed or delimiter-based framing scheme would make this robust regardless of message size.
- **One global lock serializes all store operations.** Simple and correct, but it means concurrent clients are never actually processed in parallel at the store level.  Under heavy concurrent load, this lock is the bottleneck.

## Running Tests

```bash
uv run pytest
```

Tests cover the store's core logic: LRU eviction, TTL expiry (including the background sweep), and the persistence round-trip (snapshot, then reload).

## Roadmap

Things I'd build next if I kept extending this project:
- **Append-only log (AOF)** for durability between snapshots, closing the crash-recovery gap above
- **Pub/sub** (`PUBLISH` / `SUBSCRIBE`) to let clients broadcast messages to each other through the server
- **Benchmarking** — a small script measuring throughput/latency under concurrent load, to put real numbers behind the design trade-offs above
- **Deployment** as a systemd service on a small VPS
