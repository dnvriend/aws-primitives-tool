# TODO - KVStore Future Implementation

## Phase 1 Complete ✅
- [x] Table management (create-table, drop-table)
- [x] Basic key-value operations (set, get)

## Phase 2 Complete ✅
- [x] `delete` - Delete a key
- [x] `exists` - Check if key exists
- [x] `list` - List keys by prefix

## Phase 3 Complete ✅
- [x] `inc` - Atomic increment
- [x] `dec` - Atomic decrement
- [x] `get-counter` - Read counter value

## Phase 4 - Lock Operations
- [ ] `lock-acquire` - Acquire distributed lock (with wait + exponential backoff)
- [ ] `lock-release` - Release lock
- [ ] `lock-check` - Check lock status
- [ ] `lock-extend` - Extend lock TTL

## Phase 5 - Queue Operations
- [ ] `queue-push` - Push to queue (FIFO)
- [ ] `queue-pop` - Pop from queue
- [ ] `queue-peek` - Peek at queue items
- [ ] `queue-size` - Count queue items
- [ ] `queue-ack` - Acknowledge processed item

## Phase 6 - Leader Election Operations
- [ ] `leader-elect` - Attempt to become leader
- [ ] `leader-heartbeat` - Extend leadership
- [ ] `leader-check` - Check current leader
- [ ] `leader-resign` - Step down as leader

## Phase 7 - Set Operations
- [ ] `sadd` - Add member to set
- [ ] `srem` - Remove member from set
- [ ] `sismember` - Check if member exists
- [ ] `smembers` - List all members
- [ ] `scard` - Count members

## Phase 8 - List Operations
- [ ] `lpush` - Prepend to list
- [ ] `rpush` - Append to list
- [ ] `lpop` - Remove and return first item
- [ ] `rpop` - Remove and return last item
- [ ] `lrange` - Get range of items

## Phase 9 - Transaction Operations
- [ ] `transaction` - Execute multiple operations atomically (with --file flag)

## Future Enhancements
- [ ] Add priority queues (queue-push with --priority)
- [ ] Add batch operations (batch-get, batch-set)
- [x] Add conditional updates (--if-value for delete) ✅ Implemented in Phase 2
- [ ] Add query operations (query by type, TTL, etc.)
- [ ] Add integration tests with moto
- [ ] Add CLI tests with Click runner
- [ ] Add performance benchmarks

## Documentation TODOs
- [ ] Add comprehensive README examples for each operation
- [ ] Add CLAUDE.md architecture documentation
- [ ] Add usage patterns documentation
- [ ] Add cost optimization guide
