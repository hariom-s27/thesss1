# P-B7 — Operational SQLite State Layer

**Status:** HISTORICALLY ESTABLISHED  
**Primary Documentation:** [`arpipe/STATE.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-0.1.0/arpipe/STATE.md)  
**Implementation Modules:** `arpipe/state.py`, `arpipe/store.py`, `arpipe/tests/test_state.py`

---

## 1. Architectural Role
Provides an opt-in operational queuing system built on SQLite to enable safe concurrent worker processing without external brokers or race conditions.

---

## 2. Key Technical Features
1. **SQLite Database Engine:**
   - Database: `root/state.sqlite3`
   - Journal Mode: Write-Ahead Logging (`WAL`)
   - Synchronous: `NORMAL`
   - Busy Timeout: 30,000 ms on every connection.
2. **Atomic Claim Leasing:**
   - Claims are acquired via `BEGIN IMMEDIATE` transactions using `UPDATE ... RETURNING`.
   - Deterministic ordering by SHA-256 prevents lock contention.
   - Concurrent workers cannot receive the same live claim.
3. **Lease Fencing & Heartbeats:**
   - Claims expire after 1 hour (`claimed_at < unixepoch() - 3600`).
   - Workers update `db.heartbeat(claim)` periodically.
   - Workers whose lease expired receive `LostClaim` on commit attempt.
4. **Immediate Poison Cutoff:**
   - The attempt counter increments on each reservation.
   - On the 5th reservation (`MAX_ATTEMPTS = 4`), the row transitions immediately to `poison` and is never handed out to workers.
   - Poison rows remain permanently visible for diagnostic audit and are never auto-retried.

---

## 3. Production Boundaries
`state.py` is an opt-in infrastructure layer. Its presence did not modify legacy CLI execution paths or existing manifest processing.

