# Vast.ai Billing & Instance Lifecycle (verified from official docs, 2026-08)

Sources: docs.vast.ai/guides/reference/faq/billing, faq/instances, faq/rental-types
(URLs are /guides/reference/faq/* — bare /faq/* paths 404)

## Billing
- Prepaid credit model: add credit via credit card (Stripe; Vast never sees card numbers) or crypto (BitPay, Crypto.com). NO PayPal.
- **Balance hits zero/negative → instances are stopped automatically, but NOT destroyed.**
- Stopped instances are still charged STORAGE costs (per GB) — destroy instances when done using them.
- Credit card is auto-charged periodically to pay off any negative balance.
- Auto-billing: set a balance threshold; recommended ≈ daily/weekly spend, with an email alert at ~75% of that.
- Billing frequency: balances update every few seconds (per-second billing).
- Three charge components: active rental (GPU, only while active/connected) + storage (every second the instance exists, ANY state incl. stopped/loading) + bandwidth (per byte, any state). Offline instances: no rental/storage charges.

## Instance lifecycle (data persistence)
- **Stopped**: data persists, storage charges continue.
- **Destroyed**: all data permanently deleted.
- **Lifetime expired** (offer's max rental duration, locked at rent time): instance stops, data remains UNTIL destroyed — official guidance: "Always assume your instance will be lost once the lifetime expires." Back up important data before.
- **Interruptible** (bid-based): can be stopped by higher bids; may wait long to resume; checkpoint work.

## Rental types
- **On-Demand**: fixed host price, runs as long as you want, cannot be interrupted. Default for serving.
- **Reserved**: pre-payment discount, up to 50%, convert from an existing on-demand instance.
- **Interruptible**: you set a bid; 50-80% cheaper; can be killed by higher bids.

## Renting steps (UI-verified)
1. Register: vast.ai top-right "Login" (Google OAuth easiest). NOTE: `/console/login` URL is a 404 — always enter from the homepage.
2. Add credit in Billing BEFORE renting (prepaid).
3. Search page `cloud.vast.ai/create/` — browsable WITHOUT login: filter GPU type (combobox → type text → checkbox) + #GPUs (1X/2X/4X/8X buttons) + reliability.
4. RENT → configure:
   - Template: SSH mode with pytorch/vllm/cuda image (not Jupyter for long-running services).
   - **Container Size: FIXED after creation — set generously (≥ weights + deps + headroom; default 16GB is never enough).** Storage billed per GB.
   - SSH key: Vast can auto-generate and download a private key; or paste your own pubkey.
   - On-Demand (not Interruptible) for reliability.
5. Start: 1-5 min to "Running" (large images longer). SSH: `ssh -p <port> root@<ip>` (+ `-i key.pem` for Vast-managed key).
6. Auto-start script for SSH instances: put commands in `/root/onstart.sh` (runs on container startup).

## Good machine signals
- "verified" badge, reliability ≥ 98%, high Max CUDA version (12.x), NVMe disk, CPU cores + RAM ≥ weight size, max duration long enough for the job.
