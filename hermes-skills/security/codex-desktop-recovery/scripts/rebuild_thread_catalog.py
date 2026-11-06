#!/usr/bin/env python3
"""
Rebuild Codex Desktop UI's local_thread_catalog from state_5.sqlite.

WHEN: Codex desktop App (ChatGPT.exe / Store build) sidebar session list is
empty/stale but real data exists in ~/.codex/sessions/ and state_5.sqlite.
Symptom: local_thread_catalog has only a few rows while threads table has many.

USAGE:
  1. Close the App first (PowerShell Stop-Process -Name 'ChatGPT','codex' -Force)
  2. python rebuild_thread_catalog.py          # backs up, rebuilds, verifies
  3. Relaunch the App (shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App)

Writes: sqlite/codex-dev.db (local_thread_catalog + local_thread_catalog_sync_state)
Backups: <file>.bak-YYYYMMDD alongside each modified db.
"""
import sqlite3
import shutil
import time
from pathlib import Path

CODEX_HOME = Path.home() / ".codex"
SRC = CODEX_HOME / "state_5.sqlite"
DST = CODEX_HOME / "sqlite" / "codex-dev.db"
BACKUP_SUFFIX = time.strftime("bak-%Y%m%d")


def backup(p: Path) -> None:
    if p.exists():
        shutil.copy2(p, p.with_name(f"{p.name}.{BACKUP_SUFFIX}"))


def main() -> None:
    if not SRC.exists() or not DST.exists():
        raise SystemExit(f"missing db: src={SRC} dst={DST}")

    backup(SRC)
    backup(DST)
    backup(CODEX_HOME / "session_index.jsonl")

    src = sqlite3.connect(SRC)
    dst = sqlite3.connect(DST, timeout=15)
    src.row_factory = sqlite3.Row

    # user-level, non-archived threads = what the UI sidebar should show
    rows = src.execute(
        """
        SELECT id, title, first_user_message, created_at, updated_at, cwd, source,
               model_provider, git_branch, thread_source
        FROM threads
        WHERE thread_source = 'user' AND archived = 0
        ORDER BY updated_at DESC
        """
    ).fetchall()
    print(f"candidate user threads: {len(rows)}")

    cur = dst.cursor()
    existing = {r[0] for r in cur.execute("SELECT thread_id FROM local_thread_catalog")}
    max_seq = cur.execute(
        "SELECT COALESCE(MAX(observation_sequence),0) FROM local_thread_catalog"
    ).fetchone()[0]
    sync_seq = cur.execute(
        "SELECT COALESCE(observation_sequence,0) FROM local_thread_catalog_sync_state"
    ).fetchone()[0]
    seq = max(max_seq, sync_seq) + 1
    print(f"existing catalog rows: {len(existing)} | next observation_sequence: {seq}")

    inserted = 0
    for r in rows:
        tid = r["id"]
        if tid in existing:
            continue
        title = (r["title"] or r["first_user_message"] or "").strip().replace("\n", " ")
        cur.execute(
            """
            INSERT INTO local_thread_catalog
            (host_id, thread_id, display_title, source_created_at, source_updated_at,
             cwd, source_kind, source_detail, model_provider, git_branch,
             observation_sequence, missing_candidate, thread_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?)
            """,
            (
                "local", tid, title[:200],
                float(r["created_at"]), float(r["updated_at"]),
                r["cwd"] or "", r["source"] or "vscode", None,
                r["model_provider"] or "openai", r["git_branch"],
                seq, r["thread_source"] or "user",
            ),
        )
        seq += 1
        inserted += 1

    cur.execute(
        """
        UPDATE local_thread_catalog_sync_state
        SET initial_build_complete = 1, observation_sequence = ?,
            last_full_reconciled_at = ?
        WHERE host_id = 'local'
        """,
        (seq - 1, int(time.time())),
    )
    if cur.rowcount == 0:
        cur.execute(
            """
            INSERT INTO local_thread_catalog_sync_state
            (host_id, watermark_updated_at, initial_build_complete,
             observation_sequence, last_full_reconciled_at)
            VALUES ('local', NULL, 1, ?, ?)
            """,
            (seq - 1, int(time.time())),
        )

    dst.commit()
    print(f"inserted: {inserted}")
    print("integrity:", cur.execute("PRAGMA integrity_check").fetchone()[0])
    print("catalog total:", cur.execute("SELECT COUNT(*) FROM local_thread_catalog").fetchone()[0])
    print("sync_state:", cur.execute("SELECT * FROM local_thread_catalog_sync_state").fetchone())
    dst.close()
    src.close()


if __name__ == "__main__":
    main()
