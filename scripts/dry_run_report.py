#!/usr/bin/env python3
"""
Generate standardized Dry-Run Preview & Pre-Write Backup Artifacts (JSON + CSV)
for Haravan L2 Proposal and L3 Critical Write skills.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List


def write_dry_run_artifact(
    output_dir: str | Path,
    skill_name: str,
    store_domain: str,
    environment: str,
    changes: List[Dict[str, Any]],
    rollback_supported: bool = True,
) -> Dict[str, str]:
    """
    Write both a JSON backup/proposal artifact and a CSV diff preview.
    Each item in `changes` should contain: record_id, field, before, after, risk_note.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"hrv-{skill_name}-{ts}"

    json_path = out / f"{run_id}.backup.json"
    csv_path = out / f"{run_id}.preview.csv"

    payload = {
        "run_id": run_id,
        "generated_at_utc": ts,
        "skill_name": skill_name,
        "store_domain": store_domain,
        "environment": environment,
        "dry_run": True,
        "rollback_supported": rollback_supported,
        "total_records": len(changes),
        "changes": changes,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fieldnames = ["record_id", "field", "before", "after", "risk_note"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in changes:
            writer.writerow(row)

    return {
        "run_id": run_id,
        "backup_json": str(json_path),
        "preview_csv": str(csv_path),
    }


if __name__ == "__main__":
    sample = [
        {
            "record_id": "variant_1001",
            "field": "price",
            "before": 250000,
            "after": 275000,
            "risk_note": "+10% price adjustment",
        }
    ]
    print(json.dumps({"helper": "write_dry_run_artifact", "sample_row": sample[0]}, indent=2))
