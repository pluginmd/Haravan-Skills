#!/usr/bin/env python3
"""
Validate all Haravan SKILL.md files against the canonical safety contract,
official Haravan scope catalog, and registry.json consistency.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from generate_registry import (
    REGISTRY_API_PATH,
    REGISTRY_PATH,
    REGISTRY_UI_PATH,
    ROOT,
    SKILLS_DIR,
    parse_frontmatter,
)

VALID_SCOPES = {
    "com.read_shop",
    "com.write_shop",
    "com.read_products",
    "com.write_products",
    "com.read_orders",
    "com.write_orders",
    "com.read_customers",
    "com.write_customers",
    "com.read_inventories",
    "com.write_inventories",
    "com.read_discounts",
    "com.write_discounts",
    "com.read_contents",
    "com.write_contents",
    "com.write_script_tags",
    "web.read_themes",
    "web.write_themes",
    "web.read_contents",
    "web.write_contents",
    "web.read_script_tags",
    "web.write_script_tags",
    "wh_api",
    "offline_access",
}

REQUIRED_TOP_KEYS = {
    "name",
    "description",
    "version",
    "execution_channel",
    "requires_token",
    "domain",
    "layer",
    "wave",
    "mode",
    "risk",
    "haravan",
    "execution",
    "privacy",
    "rollback",
}


def validate_skill(skill_path: Path) -> List[str]:
    errors: List[str] = []
    rel = skill_path.relative_to(ROOT).as_posix()
    text = skill_path.read_text(encoding="utf-8")

    try:
        meta = parse_frontmatter(text)
    except Exception as exc:
        return [f"{rel}: frontmatter parse error: {exc}"]

    missing = REQUIRED_TOP_KEYS - set(meta.keys())
    if missing:
        errors.append(f"{rel}: missing required keys: {sorted(missing)}")
        return errors

    folder_name = skill_path.parent.name
    domain_folder = skill_path.parent.parent.name
    channel_folder = skill_path.parent.parent.parent.name
    if meta["name"] != folder_name:
        errors.append(f"{rel}: name '{meta['name']}' != folder '{folder_name}'")
    if meta["domain"] != domain_folder:
        errors.append(f"{rel}: domain '{meta['domain']}' != folder '{domain_folder}'")

    channel = meta["execution_channel"]
    req_token = meta["requires_token"]
    if channel_folder == "api-mcp":
        if channel != "api_mcp" or req_token is not True:
            errors.append(f"{rel}: skills/api-mcp must have execution_channel='api_mcp' and requires_token=true")
        if meta["haravan"].get("api_surface") == "admin_ui":
            errors.append(f"{rel}: skills/api-mcp cannot have api_surface='admin_ui'")
    elif channel_folder == "browser-ui":
        if channel != "browser_ui" or req_token is not False:
            errors.append(f"{rel}: skills/browser-ui must have execution_channel='browser_ui' and requires_token=false")
        if meta["haravan"].get("api_surface") != "admin_ui":
            errors.append(f"{rel}: skills/browser-ui must have api_surface='admin_ui'")
    else:
        errors.append(f"{rel}: unexpected channel folder '{channel_folder}' (expected 'api-mcp' or 'browser-ui')")

    layer = meta["layer"]
    mode = meta["mode"]
    risk = meta["risk"]
    hrv: Dict[str, Any] = meta["haravan"]
    exe: Dict[str, Any] = meta["execution"]
    priv: Dict[str, Any] = meta["privacy"]
    rb: Dict[str, Any] = meta["rollback"]

    if layer not in ("L0", "L1", "L2", "L3"):
        errors.append(f"{rel}: invalid layer '{layer}'")
    if mode not in ("reference", "read", "proposal", "write"):
        errors.append(f"{rel}: invalid mode '{mode}'")
    if risk not in ("low", "medium", "high", "critical"):
        errors.append(f"{rel}: invalid risk '{risk}'")

    # Scope validation (admin_ui skills may use empty API scopes)
    scopes = hrv.get("scopes", [])
    if hrv.get("api_surface") not in ("com", "web", "webhook", "cli", "admin_ui"):
        errors.append(f"{rel}: invalid api_surface '{hrv.get('api_surface')}'")
    for sc in scopes:
        if sc not in VALID_SCOPES:
            errors.append(f"{rel}: unknown Haravan scope '{sc}'")

    # L1 Read-only must NOT request write scopes
    if layer == "L1":
        if mode != "read":
            errors.append(f"{rel}: L1 skill must have mode='read'")
        write_scopes = [s for s in scopes if ".write_" in s]
        if write_scopes:
            errors.append(f"{rel}: L1 read-only skill must not request write scopes: {write_scopes}")

    # L2 Proposal safety rules
    if layer == "L2":
        if mode != "proposal":
            errors.append(f"{rel}: L2 skill must have mode='proposal'")
        if exe.get("dry_run") is not True:
            errors.append(f"{rel}: L2 skill MUST default dry_run=true")
        if exe.get("confirmation_required") is not True:
            errors.append(f"{rel}: L2 skill MUST require confirmation_required=true")
        if rb.get("backup_required") is not True:
            errors.append(f"{rel}: L2 skill MUST require backup_required=true")

    # L3 Critical write safety rules
    if layer == "L3":
        if mode != "write":
            errors.append(f"{rel}: L3 skill must have mode='write'")
        if exe.get("dry_run") is not True:
            errors.append(f"{rel}: L3 skill MUST default dry_run=true")
        if exe.get("confirmation_required") is not True:
            errors.append(f"{rel}: L3 skill MUST require confirmation_required=true")
        if exe.get("separate_turn") is not True:
            errors.append(f"{rel}: L3 skill MUST require separate_turn=true")
        if exe.get("idempotency_required") is not True:
            errors.append(f"{rel}: L3 skill MUST require idempotency_required=true")
        if exe.get("partial_failure_policy") != "stop":
            errors.append(f"{rel}: L3 skill MUST set partial_failure_policy='stop'")
        if int(exe.get("max_records", 999)) > 25:
            errors.append(f"{rel}: L3 skill max_records must be <= 25")

    # Privacy checks
    if priv.get("pii_level") in ("customer", "financial"):
        if priv.get("redact_output") is not True:
            errors.append(f"{rel}: PII skill must have redact_output=true")
        if priv.get("export_allowed") is not False:
            errors.append(f"{rel}: PII skill must default export_allowed=false")

    # Production-Grade content depth & structure quality gates
    required_sections = ["## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7.", "## 8."]
    for sec in required_sections:
        if sec not in text:
            errors.append(f"{rel}: missing required section heading '{sec}'")
    line_count = len(text.splitlines())
    min_lines = 200 if channel == "browser_ui" else 130
    if line_count < min_lines:
        errors.append(f"{rel}: skill too shallow ({line_count} lines < {min_lines} minimum)")
    if channel == "browser_ui" and "## 9." not in text:
        errors.append(f"{rel}: browser_ui skill missing required section heading '## 9.'")
    if "```json" not in text:
        errors.append(f"{rel}: missing concrete ```json payload/output schema block")
    if "| ---" not in text and "| :---" not in text and "|---" not in text:
        errors.append(f"{rel}: missing Markdown parameter/report table")

    return errors


def main() -> int:
    skill_files = sorted(SKILLS_DIR.glob("*/*/*/SKILL.md"))
    if not skill_files:
        print("ERROR: No SKILL.md files found under skills/{api-mcp,browser-ui}/", file=sys.stderr)
        return 1

    all_errors: List[str] = []
    seen_names = set()
    api_disk = 0
    ui_disk = 0
    for path in skill_files:
        errs = validate_skill(path)
        all_errors.extend(errs)
        name = path.parent.name
        if name in seen_names:
            all_errors.append(f"Duplicate skill name detected: {name}")
        seen_names.add(name)
        if path.parent.parent.parent.name == "api-mcp":
            api_disk += 1
        elif path.parent.parent.parent.name == "browser-ui":
            ui_disk += 1

    # Check all 3 registry JSON files sync
    for reg_path, expected in (
        (REGISTRY_PATH, len(skill_files)),
        (REGISTRY_API_PATH, api_disk),
        (REGISTRY_UI_PATH, ui_disk),
    ):
        if not reg_path.exists():
            all_errors.append(f"{reg_path.name} does not exist. Run scripts/generate_registry.py")
        else:
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
            if reg.get("total_skills") != expected:
                all_errors.append(
                    f"{reg_path.name} out of sync: total_skills={reg.get('total_skills')} vs disk={expected}"
                )

    if all_errors:
        print(f"VALIDATION FAILED ({len(all_errors)} errors):", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"VALIDATION PASSED: {len(skill_files)} skills verified with 0 errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
