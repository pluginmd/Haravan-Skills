#!/usr/bin/env python3
"""
Haravan Safe Operational MCP Server (JSON-RPC 2.0 over stdio, zero external dependencies).
Exposes Read-Only (L1) and Dry-Run Proposal (L2) tools backed by hrv_ops.py & registry.json.
Never performs unapproved mutations or exposes secrets.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import hrv_ops  # noqa: E402
from hrv_client import HaravanClient  # noqa: E402

SERVER_INFO = {"name": "haravan-ops-mcp", "version": "1.0.0"}

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "haravan_list_skills",
        "description": "List canonical Haravan operational skills from registry.json (filter by execution_channel: api_mcp | browser_ui, domain, or layer).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_channel": {"type": "string", "enum": ["api_mcp", "browser_ui"]},
                "domain": {"type": "string"},
                "layer": {"type": "string", "enum": ["L0", "L1", "L2", "L3"]},
            },
        },
    },
    {
        "name": "haravan_health_check",
        "description": "Run Read-Only Haravan Store Health Check across catalog, inventory, promotions, and theme.",
        "inputSchema": {"type": "object", "properties": {"demo": {"type": "boolean", "default": False}}},
    },
    {
        "name": "haravan_catalog_audit",
        "description": "Audit Haravan product completeness, duplicate SKUs, missing images/alt text, and missing grams.",
        "inputSchema": {"type": "object", "properties": {"demo": {"type": "boolean", "default": False}}},
    },
    {
        "name": "haravan_low_stock",
        "description": "Detect negative stock and low-stock SKUs across Haravan locations.",
        "inputSchema": {
            "type": "object",
            "properties": {"threshold": {"type": "integer", "default": 10}, "demo": {"type": "boolean", "default": False}},
        },
    },
    {
        "name": "haravan_cod_risk",
        "description": "Score Vietnam COD boom-risk signals on unfulfilled Haravan orders (read-only, PII redacted).",
        "inputSchema": {
            "type": "object",
            "properties": {"high_value_vnd": {"type": "integer", "default": 2000000}, "demo": {"type": "boolean", "default": False}},
        },
    },
    {
        "name": "haravan_morning_briefing",
        "description": "Generate Haravan Daily Morning Control-Tower Briefing (orders, omnichannel revenue, alerts).",
        "inputSchema": {"type": "object", "properties": {"demo": {"type": "boolean", "default": False}}},
    },
]


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "haravan_list_skills":
        reg = json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))
        skills = reg.get("skills", [])
        if arguments.get("execution_channel"):
            skills = [s for s in skills if s.get("execution_channel") == arguments["execution_channel"]]
        if arguments.get("domain"):
            skills = [s for s in skills if s.get("domain") == arguments["domain"]]
        if arguments.get("layer"):
            skills = [s for s in skills if s.get("layer") == arguments["layer"]]
        return {
            "total": len(skills),
            "skills": [
                {
                    "name": s["name"],
                    "execution_channel": s["execution_channel"],
                    "requires_token": s["requires_token"],
                    "domain": s["domain"],
                    "layer": s["layer"],
                    "mode": s["mode"],
                    "path": s["path"],
                }
                for s in skills
            ],
        }

    use_demo = bool(arguments.get("demo")) or not os.environ.get("HARAVAN_ACCESS_TOKEN")
    client = None if use_demo else HaravanClient(dry_run=True)

    if name == "haravan_health_check":
        data = hrv_ops.load_data(client, use_demo, ["shop", "products", "inventory_locations", "orders", "promotions", "themes"])
        return hrv_ops.cmd_health_check(data)
    if name == "haravan_catalog_audit":
        data = hrv_ops.load_data(client, use_demo, ["products"])
        return hrv_ops.cmd_catalog_audit(data)
    if name == "haravan_low_stock":
        data = hrv_ops.load_data(client, use_demo, ["inventory_locations"])
        return hrv_ops.cmd_low_stock(data, threshold=int(arguments.get("threshold", 10)))
    if name == "haravan_cod_risk":
        data = hrv_ops.load_data(client, use_demo, ["orders"])
        return hrv_ops.cmd_cod_risk(data, high_value_vnd=int(arguments.get("high_value_vnd", 2000000)))
    if name == "haravan_morning_briefing":
        data = hrv_ops.load_data(client, use_demo, ["orders", "inventory_locations"])
        return hrv_ops.cmd_morning_briefing(data)

    raise ValueError(f"Unknown MCP tool: {name}")


def handle_rpc(request: Dict[str, Any]) -> Dict[str, Any] | None:
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params") or {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": SERVER_INFO,
                "capabilities": {"tools": {}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        try:
            output = handle_tool_call(params.get("name", ""), params.get("arguments") or {})
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False, indent=2)}]},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> None:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_rpc(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
