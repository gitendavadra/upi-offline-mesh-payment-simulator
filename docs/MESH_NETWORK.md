# Peer-to-Peer Mesh Network Architecture

### 1. Mesh Topology & Routing Mechanism
The simulation models epidemic gossip routing over low-power wireless links (simulating Bluetooth Low Energy GATT / Wi-Fi Direct).

#### Simulated Device Roles:
- **`phone-alice` (Sender)**: Initiates offline payment packets.
- **`phone-stranger1`, `phone-stranger2`, `phone-stranger3` (Relay Nodes)**: Intermediate peers in the physical propagation path.
- **`phone-bridge` (Gateway Node)**: Moves into range of cellular 4G/Wi-Fi and uploads buffered packets to `/api/bridge/ingest`.

---

### 2. Hop Limits & Loop Prevention
1. **Time-To-Live (TTL)**: Set to 5 hops upon creation. Decremented by 1 at each peer-to-peer transmission. When TTL reaches 0, forwarding ceases.
2. **Buffer Deduplication**: Devices check incoming `packetId` against locally buffered packets; duplicates are rejected to prevent broadcast storms and infinite routing loops.
3. **Simulated Packet Loss**: Models real-world RF interference and signal attenuation with configurable loss probability (0% to 50%).
