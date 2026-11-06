## 4. Source Hygiene & Citations

For every artifact you capture, record: **URL + UTC timestamp + SHA-256 hash +command-line version + run_id**.

- Hash all downloaded files with SHA-256.
- Screenshot in PNG (lossless, smaller than full-page WARC for evidence packs).
- Capture raw HTTP requests/responses, capped at 2 KiB body to keep evidence packs small.
- Use JSONL (NDJSON) logs, one line per event, with a `run_id` so the entire engagement is replayable.
- Separate evidence read-only from working copies; never edit captured artifacts.

When citing a source in your output, prefer durable references (CVE, vendor advisory, ATT&CK technique ID, RFC) over ephemeral ones (a Twitter post, a forum thread). If the only source is ephemeral, archive it (archive.today, Wayback SavePageNow) before citing.

---

