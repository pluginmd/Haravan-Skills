#!/usr/bin/env python3
"""
Generate canonical registry.json by scanning skills/*/*/SKILL.md frontmatter.
Zero external dependencies (uses a lightweight YAML subset parser for frontmatter).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
REGISTRY_PATH = ROOT / "registry.json"
REGISTRY_API_PATH = ROOT / "registry-api-mcp.json"
REGISTRY_UI_PATH = ROOT / "registry-browser-ui.json"


def _parse_scalar(val: str) -> Any:
    v = val.strip()
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v in ("null", "None", "~", ""):
        return None
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in inner.split(",")]
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def parse_frontmatter(md_text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter enclosed by --- markers (supports nested dicts and lists)."""
    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing opening YAML frontmatter delimiter '---'")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("Missing closing YAML frontmatter delimiter '---'")

    fm_lines = lines[1:end_idx]
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, root)]

    idx = 0
    while idx < len(fm_lines):
        raw = fm_lines[idx]
        idx += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if stripped.startswith("- "):
            item_val = _parse_scalar(stripped[2:])
            if isinstance(parent, list):
                parent.append(item_val)
            else:
                raise ValueError(f"List item without list container: {raw}")
            continue

        if ":" not in stripped:
            continue
        key, rest = stripped.split(":", 1)
        key = key.strip()
        rest = rest.strip()

        if rest != "":
            parent[key] = _parse_scalar(rest)
        else:
            # Look ahead to determine whether nested block is a list or dict
            next_is_list = False
            for j in range(idx, len(fm_lines)):
                nxt = fm_lines[j]
                if not nxt.strip() or nxt.lstrip().startswith("#"):
                    continue
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt_indent > indent and nxt.strip().startswith("- "):
                    next_is_list = True
                break
            container: Any = [] if next_is_list else {}
            parent[key] = container
            stack.append((indent, container))

    return root


def collect_skills() -> List[Dict[str, Any]]:
    skills: List[Dict[str, Any]] = []
    for skill_md in sorted(SKILLS_DIR.glob("*/*/*/SKILL.md")):
        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        rel_path = skill_md.relative_to(ROOT).as_posix()
        meta["path"] = rel_path
        skills.append(meta)
    return skills


def _summarize(skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_channel = Counter(s.get("execution_channel", "unknown") for s in skills)
    by_domain = Counter(s.get("domain", "unknown") for s in skills)
    by_layer = Counter(s.get("layer", "unknown") for s in skills)
    by_wave = Counter(f"wave_{s.get('wave', 'unknown')}" for s in skills)
    by_mode = Counter(s.get("mode", "unknown") for s in skills)
    return {
        "by_channel": dict(sorted(by_channel.items())),
        "by_domain": dict(sorted(by_domain.items())),
        "by_layer": dict(sorted(by_layer.items())),
        "by_wave": dict(sorted(by_wave.items())),
        "by_mode": dict(sorted(by_mode.items())),
    }


def build_registry(skills: List[Dict[str, Any]] | None = None, track: str = "all") -> Dict[str, Any]:
    items = collect_skills() if skills is None else skills
    return {
        "schema_version": "1.1.0",
        "author": "Nguyễn Ngọc Tuấn, Founder Transform Group",
        "platform": "haravan.com",
        "track": track,
        "total_skills": len(items),
        "summary": _summarize(items),
        "skills": items,
    }


def main() -> None:
    all_skills = collect_skills()
    api_skills = [s for s in all_skills if s.get("execution_channel") == "api_mcp"]
    ui_skills = [s for s in all_skills if s.get("execution_channel") == "browser_ui"]

    reg_all = build_registry(all_skills, track="all")
    reg_api = build_registry(api_skills, track="api_mcp")
    reg_ui = build_registry(ui_skills, track="browser_ui")

    REGISTRY_PATH.write_text(json.dumps(reg_all, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REGISTRY_API_PATH.write_text(json.dumps(reg_api, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REGISTRY_UI_PATH.write_text(json.dumps(reg_ui, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        f"Generated registries: total={reg_all['total_skills']} "
        f"(api_mcp={reg_api['total_skills']}, browser_ui={reg_ui['total_skills']})."
    )
    print(json.dumps(reg_all["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
