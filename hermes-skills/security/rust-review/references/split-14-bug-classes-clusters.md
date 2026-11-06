## Bug classes / clusters

Authoritative: `prompts/clusters/manifest.json`. 37 bug classes live in `always`-gated clusters (so the cluster always runs); of those, 35 always fire and 2 — `adversarial-trait` (TRAITADV) and `closure-panic` (CLOSUREPANIC) in `logic-correctness` — additionally carry `requires: has_unsafe`, so they only fire when `has_unsafe=true`. 69 bug classes across all clusters when every conditional gate is enabled. The `memory-safety` cluster is gated on `has_unsafe` (all its bug classes require `unsafe`); PATHJOIN and TOCTOU are gated behind `has_fs_io` via `input-os-safety`, and PACKEDREF lives in the conditional `layout-safety` cluster (`has_packed_repr`); PTREXPOSE stays always-on via the `info-disclosure` cluster. `unsafe-boundary` and `concurrency-locking` are fully consolidated (their sub-prompts are not re-read at runtime).

---
