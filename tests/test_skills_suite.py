#!/usr/bin/env python3
"""
Comprehensive QC, Unit, Contract, CLI Runner & MCP E2E Test Suite
for haravan-ops-skills (88 Canonical Skills: 62 api-mcp + 26 browser-ui).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "mcp"))

import dry_run_report  # noqa: E402
import generate_registry  # noqa: E402
import haravan_mcp_server  # noqa: E402
import hrv_client  # noqa: E402
import hrv_ops  # noqa: E402
import validate_registry  # noqa: E402


class TestHaravanClientAndSafety(unittest.TestCase):
    def test_dry_run_blocks_mutations(self) -> None:
        client = hrv_client.HaravanClient(access_token="", dry_run=True)
        for verb in ("POST", "PUT", "PATCH", "DELETE"):
            res = client.request(verb, "com", "/products.json", payload={"product": {"title": "Test"}})
            self.assertTrue(res["dry_run"])
            self.assertTrue(res["blocked_mutation"])
            self.assertEqual(res["method"], verb)

    def test_pii_redaction_vn(self) -> None:
        self.assertEqual(hrv_client.redact_phone("0901234567"), "090****567")
        self.assertEqual(hrv_client.redact_phone("+84 901 234 567"), "849*****567")
        self.assertEqual(hrv_client.redact_email("nguyen.van.a@haravan.com"), "ng***@haravan.com")

    def test_webhook_hmac_verification(self) -> None:
        secret = "test_haravan_webhook_secret"
        body = b'{"id": 1001, "name": "#1001", "total_price": 500000}'
        sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
        self.assertTrue(hrv_client.verify_webhook_hmac(body, sig, secret))
        self.assertFalse(hrv_client.verify_webhook_hmac(body, "invalid_sig", secret))

    def test_dry_run_artifact_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = dry_run_report.write_dry_run_artifact(
                output_dir=tmp,
                skill_name="pricing-bulk-adjustment-proposal",
                store_domain="demo.myharavan.com",
                environment="staging",
                changes=[
                    {
                        "record_id": "v_1",
                        "field": "price",
                        "before": 100000,
                        "after": 110000,
                        "risk_note": "+10%",
                    }
                ],
            )
            self.assertTrue(Path(res["backup_json"]).exists())
            self.assertTrue(Path(res["preview_csv"]).exists())
            data = json.loads(Path(res["backup_json"]).read_text(encoding="utf-8"))
            self.assertEqual(data["total_records"], 1)
            self.assertTrue(data["dry_run"])


class TestRegistryAndContracts(unittest.TestCase):
    def test_validate_all_skills_passes(self) -> None:
        self.assertEqual(validate_registry.main(), 0)

    def test_registry_counts_and_layers(self) -> None:
        reg = json.loads(generate_registry.REGISTRY_PATH.read_text(encoding="utf-8"))
        reg_api = json.loads(generate_registry.REGISTRY_API_PATH.read_text(encoding="utf-8"))
        reg_ui = json.loads(generate_registry.REGISTRY_UI_PATH.read_text(encoding="utf-8"))
        self.assertEqual(reg["total_skills"], 88)
        self.assertEqual(reg_api["total_skills"], 62)
        self.assertEqual(reg_ui["total_skills"], 26)
        self.assertEqual(reg["summary"]["by_channel"]["api_mcp"], 62)
        self.assertEqual(reg["summary"]["by_channel"]["browser_ui"], 26)
        self.assertEqual(reg["summary"]["by_layer"]["L0"], 6)
        self.assertEqual(reg["summary"]["by_layer"]["L1"], 43)
        self.assertEqual(reg["summary"]["by_layer"]["L2"], 33)
        self.assertEqual(reg["summary"]["by_layer"]["L3"], 6)
        self.assertIn("Nguyễn Ngọc Tuấn", reg.get("author", ""))

    def test_all_browser_ui_skills_have_live_dom_snapshot(self) -> None:
        ui_files = sorted((ROOT / "skills/browser-ui").glob("*/*/SKILL.md"))
        self.assertEqual(len(ui_files), 26)
        for md in ui_files:
            txt = md.read_text(encoding="utf-8")
            self.assertIn("Live-DOM Verified Snapshot", txt, f"Missing Live-DOM snapshot in {md}")
            self.assertGreaterEqual(len(txt.splitlines()), 200, f"Too short: {md}")

    def test_sitemap_covers_17_settings_and_3_microfrontends(self) -> None:
        sitemap = (ROOT / "api/admin-ui-sitemap.yaml").read_text(encoding="utf-8")
        self.assertIn("total_items: 17", sitemap)
        for origin in ("https://web.haravan.app", "https://customers.haravan.app", "https://reports.haravan.app"):
            self.assertIn(origin, sitemap)
        self.assertIn("live_dom_verified_controls:", sitemap)

    def test_schedules_reference_valid_skills(self) -> None:
        reg = json.loads(generate_registry.REGISTRY_PATH.read_text(encoding="utf-8"))
        valid = {s["name"] for s in reg["skills"]}
        sched = (ROOT / "workflows/schedules.yaml").read_text(encoding="utf-8")
        names = re.findall(r"^\s*skill:\s*([a-z0-9-]+)\s*$", sched, re.M)
        self.assertEqual(len(names), 16)
        for name in names:
            self.assertIn(name, valid)

    def test_pure_haravan_zero_external_mentions(self) -> None:
        forbidden = re.compile(r"shopify|storehand|40rty|daino|dragonfruit|pikka|selofy|polaris|shopifyql", re.I)
        for md in list(ROOT.glob("*.md")) + list((ROOT / "skills").glob("*/*/*/SKILL.md")):
            txt = md.read_text(encoding="utf-8")
            self.assertIsNone(forbidden.search(txt), f"Unexpected external mention in {md}")

    def test_zero_broken_internal_markdown_links(self) -> None:
        for md in list(ROOT.glob("*.md")) + list((ROOT / "playbooks").glob("*.md")) + list((ROOT / "policies").glob("*.md")):
            txt = md.read_text(encoding="utf-8")
            for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", txt):
                href = m.group(1).strip()
                if href.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                target = (md.parent / href.split("#")[0]).resolve()
                self.assertTrue(target.exists(), f"Broken link in {md}: {href}")


class TestOpsCliAndMcpServer(unittest.TestCase):
    def test_hrv_ops_demo_commands(self) -> None:
        data = hrv_ops.demo_dataset()
        self.assertEqual(hrv_ops.cmd_probe(data)["status"], "OK")
        cat = hrv_ops.cmd_catalog_audit(data)
        self.assertIn("TRA-200G", cat["duplicate_skus"])
        self.assertEqual(len(hrv_ops.cmd_low_stock(data)["negative_stock_p0"]), 1)
        cod = hrv_ops.cmd_cod_risk(data)
        self.assertEqual(len(cod["flagged_orders"]), 1)
        self.assertEqual(cod["flagged_orders"][0]["customer_phone_redacted"], "090****567")
        self.assertEqual(len(hrv_ops.cmd_wismo(data)["stuck_orders"]), 1)
        rfm = hrv_ops.cmd_rfm(data)
        self.assertEqual(len(rfm["duplicate_phone_clusters"]), 1)
        self.assertGreaterEqual(len(hrv_ops.cmd_promo_audit(data)["issues"]), 2)
        self.assertEqual(len(hrv_ops.cmd_redirect_audit(data)["loops"]), 2)
        self.assertGreater(hrv_ops.cmd_health_check(data)["overall_score"], 0)
        self.assertGreater(hrv_ops.cmd_morning_briefing(data)["gross_revenue_vnd"], 0)

    def test_hrv_ops_subprocess_e2e(self) -> None:
        for cmd in ("probe", "health-check", "cod-risk", "morning-briefing"):
            r = subprocess.run([sys.executable, str(ROOT / "scripts/hrv_ops.py"), "--demo", cmd], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"CLI failed on {cmd}: {r.stderr}")
            parsed = json.loads(r.stdout)
            self.assertIn("skill", parsed)

    def test_price_dry_run_guardrail_and_artifact(self) -> None:
        data = hrv_ops.demo_dataset()
        with self.assertRaises(ValueError):
            hrv_ops.cmd_price_dry_run(data, pct=45.0, output_dir="/tmp")
        with tempfile.TemporaryDirectory() as tmp:
            res = hrv_ops.cmd_price_dry_run(data, pct=10.0, output_dir=tmp)
            self.assertTrue(res["dry_run"])
            self.assertTrue(res["separate_turn_confirmation_required"])
            self.assertTrue(Path(res["artifacts"]["backup_json"]).exists())

    def test_mcp_server_jsonrpc_and_stdio_e2e(self) -> None:
        init_resp = haravan_mcp_server.handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "haravan-ops-mcp")

        list_resp = haravan_mcp_server.handle_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = [t["name"] for t in list_resp["result"]["tools"]]
        self.assertEqual(len(tool_names), 6)

        mcp_in = (
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "haravan_list_skills", "arguments": {"execution_channel": "browser_ui"}}}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "haravan_health_check", "arguments": {"demo": True}}}) + "\n"
        )
        proc = subprocess.run([sys.executable, str(ROOT / "mcp/haravan_mcp_server.py")], input=mcp_in, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        resps = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(resps), 3)
        self.assertEqual(json.loads(resps[1]["result"]["content"][0]["text"])["total"], 26)
        self.assertGreater(json.loads(resps[2]["result"]["content"][0]["text"])["overall_score"], 0)


if __name__ == "__main__":
    unittest.main()
