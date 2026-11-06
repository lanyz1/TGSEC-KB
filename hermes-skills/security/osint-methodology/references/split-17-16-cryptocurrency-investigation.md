## 16. Cryptocurrency Investigation

### 16.1 Transaction Analysis

- Track flows between wallets; identify clusters of related addresses; monitor large transfers.

Tools: Cielo (multi-chain), TRM (graphs), Arkham (multichain + entity labels), MetaSleuth (visual), Range (CCTP), Socketscan (EVM bridge), Pulsy (bridge aggregator), Chainalysis Horizon 2.0 (paid), Elliptic Lens.

### 16.2 Layer 2 / Rollup Analysis

- **zkSync Era / Polygon zkEVM** — ZK proofs hide L2 details; only L1 bridge events visible.
- **Arbitrum / Optimism** — batched/compressed; L2 state from L1 calldata.
- **StarkNet** — Cairo VM; different address derivation.
- **Base / Blast / Scroll** — OP Stack or ZK.
- **Privacy protocols on L2** — Aztec (programmable privacy), Railgun (shielded pools), Privacy Pools (Tornado Cash successor).

**Methodology:** start with L1 bridge events; use L2 explorers for in-rollup activity; for privacy protocols focus on timing analysis and clustering.

### 16.3 Cautions

- Bridges introduce mint/burn semantics; avoid 1:1 flow assumptions.
- MEV/aggregator paths create false "direct" trails.
- L2 finality: optimistic rollups have 7-day challenge periods.

### 16.4 Wallet / Exchange / NFT Profiling

Same patterns: age + activity + connections + balance over time + linked accounts. NFTs add ownership history + metadata + connected wallets.

---

