#!/usr/bin/env python3
"""
Haravan Operational CLI Runner (hrv_ops.py)
Executes core Wave 1 (Read-Only) and Wave 2 (Dry-Run Proposal) Haravan skills
against a live Haravan store (via HARAVAN_ACCESS_TOKEN) or offline (--demo).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from dry_run_report import write_dry_run_artifact  # noqa: E402
from hrv_client import HaravanClient, redact_phone  # noqa: E402

FINANCIAL_DISCLAIMER = (
    "Operational Estimate / Reconciliation Aid — không thay thế sổ cái kế toán hoặc tờ khai thuế chính thức."
)


def normalize_vn_phone(phone: Optional[str]) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if digits.startswith("84") and len(digits) >= 10:
        return "0" + digits[2:]
    return digits


def demo_dataset() -> Dict[str, Any]:
    """Realistic Vietnam Haravan Omni store dataset for offline testing (--demo)."""
    now = dt.datetime.now(dt.timezone.utc)
    iso = lambda delta_h: (now - dt.timedelta(hours=delta_h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "shop": {
            "name": "Demo VN Store",
            "domain": "demo-vn.myharavan.com",
            "currency": "VND",
            "timezone": "Asia/Ho_Chi_Minh",
            "email": "ops@demo-vn.vn",
        },
        "locations": [
            {"id": 101, "name": "Kho Trung Tam HCM", "active": True},
            {"id": 102, "name": "Cua Hang POS Q1", "active": True},
        ],
        "products": [
            {
                "id": 1001,
                "title": "Tra Thao Moc Thanh Nhiet 200g",
                "body_html": "<p>" + ("Mo ta chi tiet san pham thao moc tu nhien " * 6) + "</p>",
                "vendor": "HerbVN",
                "product_type": "Tra",
                "tags": "bestseller, thao-moc",
                "published_at": iso(720),
                "images": [{"id": 1, "alt": "Tra thao moc thanh nhiet 200g"}],
                "variants": [
                    {"id": 5001, "sku": "TRA-200G", "barcode": "8930001001", "price": 185000, "compare_at_price": 220000, "grams": 250}
                ],
            },
            {
                "id": 1002,
                "title": "Tinh Dau Sa Chanh 50ml",
                "body_html": "<p>Ngan</p>",
                "vendor": "HerbVN",
                "product_type": "Tinh Dau",
                "tags": "",
                "published_at": iso(400),
                "images": [],
                "variants": [
                    {"id": 5002, "sku": "TRA-200G", "barcode": "", "price": 149000, "compare_at_price": 140000, "grams": 0}
                ],
            },
            {
                "id": 1003,
                "title": "Mat Ong Rung Nguyen Chat 500ml",
                "body_html": "<p>" + ("Mat ong rung tu nhien khai thac Tay Nguyen " * 5) + "</p>",
                "vendor": "HerbVN",
                "product_type": "Mat Ong",
                "tags": "vip, qua-tang",
                "published_at": iso(200),
                "images": [{"id": 2, "alt": ""}],
                "variants": [
                    {"id": 5003, "sku": "MO-500ML", "barcode": "8930001003", "price": 320000, "compare_at_price": None, "grams": 650}
                ],
            },
        ],
        "inventory_locations": [
            {"location_id": 101, "variant_id": 5001, "sku": "TRA-200G", "qty_onhand": 4, "qty_commited": 1, "qty_available": 3},
            {"location_id": 102, "variant_id": 5001, "sku": "TRA-200G", "qty_onhand": 25, "qty_commited": 0, "qty_available": 25},
            {"location_id": 101, "variant_id": 5002, "sku": "TD-50ML", "qty_onhand": -2, "qty_commited": 0, "qty_available": -2},
            {"location_id": 101, "variant_id": 5003, "sku": "MO-500ML", "qty_onhand": 60, "qty_commited": 2, "qty_available": 58},
        ],
        "orders": [
            {
                "id": 9001,
                "name": "#109001",
                "created_at": iso(6),
                "source_name": "web",
                "gateway": "COD",
                "financial_status": "pending",
                "fulfillment_status": "unshipped",
                "cancelled_at": None,
                "total_price": 3250000,
                "customer": {"id": 701, "phone": "0901234567", "orders_count": 1, "cancelled_orders_count": 2},
                "shipping_address": {"address1": "123 Le Loi", "ward": "", "district": "Q1", "province": "Ho Chi Minh"},
            },
            {
                "id": 9002,
                "name": "#109002",
                "created_at": iso(72),
                "source_name": "shopee",
                "gateway": "Prepaid",
                "financial_status": "paid",
                "fulfillment_status": "unshipped",
                "cancelled_at": None,
                "total_price": 505000,
                "customer": {"id": 702, "phone": "+84901234567", "orders_count": 4, "cancelled_orders_count": 0},
                "shipping_address": {"address1": "45 Nguyen Hue", "ward": "Ben Nghe", "district": "Q1", "province": "Ho Chi Minh"},
            },
            {
                "id": 9003,
                "name": "#109003",
                "created_at": iso(18),
                "source_name": "pos",
                "gateway": "Cash",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "cancelled_at": None,
                "total_price": 640000,
                "customer": {"id": 703, "phone": "0987654321", "orders_count": 5, "cancelled_orders_count": 0},
                "shipping_address": {"address1": "POS", "ward": "Ben Nghe", "district": "Q1", "province": "Ho Chi Minh"},
            },
        ],
        "customers": [
            {"id": 701, "phone": "0901234567", "orders_count": 1, "total_spent": 3250000},
            {"id": 702, "phone": "+84 901 234 567", "orders_count": 4, "total_spent": 4800000},
            {"id": 703, "phone": "0987654321", "orders_count": 5, "total_spent": 9200000},
        ],
        "promotions": [
            {"id": 301, "title": "SALE-TET-CU", "status": "enabled", "value": 55, "value_type": "percentage", "ends_at": iso(240)},
            {"id": 302, "title": "FREESHIP-VIP", "status": "enabled", "value": 30000, "value_type": "fixed_amount", "ends_at": None},
        ],
        "redirects": [
            {"id": 401, "path": "/old-a", "target": "/old-b"},
            {"id": 402, "path": "/old-b", "target": "/old-a"},
            {"id": 403, "path": "/promo", "target": "/collections/sale"},
        ],
        "themes": [{"id": 801, "name": "Haravan Twenty Live", "role": "main"}],
    }


def load_data(client: Optional[HaravanClient], demo: bool, resources: List[str]) -> Dict[str, Any]:
    if demo:
        return demo_dataset()
    assert client is not None
    data: Dict[str, Any] = {}
    if "shop" in resources:
        data["shop"] = client.request("GET", "com", "/shop.json").get("shop", {})
    if "locations" in resources:
        data["locations"] = client.request("GET", "com", "/locations.json").get("locations", [])
    if "products" in resources:
        data["products"] = client.paginate("com", "/products.json", "products", limit=50, max_pages=10)
    if "inventory_locations" in resources:
        data["inventory_locations"] = client.paginate("com", "/inventory_locations.json", "inventory_locations", limit=50, max_pages=10)
    if "orders" in resources:
        data["orders"] = client.paginate("com", "/orders.json", "orders", limit=50, max_pages=10)
    if "customers" in resources:
        data["customers"] = client.paginate("com", "/customers.json", "customers", limit=50, max_pages=10)
    if "promotions" in resources:
        data["promotions"] = client.request("GET", "com", "/promotions.json").get("promotions", [])
    if "redirects" in resources:
        data["redirects"] = client.paginate("web", "/redirects.json", "redirects", limit=50, max_pages=10)
    if "themes" in resources:
        data["themes"] = client.request("GET", "web", "/themes.json").get("themes", [])
    return data


def cmd_probe(data: Dict[str, Any]) -> Dict[str, Any]:
    shop = data["shop"]
    return {
        "skill": "haravan-auth-setup",
        "status": "OK",
        "shop": {
            "name": shop.get("name"),
            "domain": shop.get("domain"),
            "currency": shop.get("currency"),
            "timezone": shop.get("timezone"),
        },
        "locations_count": len(data.get("locations", [])),
    }


def cmd_catalog_audit(data: Dict[str, Any]) -> Dict[str, Any]:
    products = data["products"]
    sku_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    missing_images, missing_alt, missing_grams, bad_compare_at = [], [], [], []
    scores: List[int] = []

    for p in products:
        score = 0
        imgs = p.get("images") or []
        if imgs:
            score += 20
            if any(not (im.get("alt") or "").strip() for im in imgs):
                missing_alt.append(p["id"])
        else:
            missing_images.append(p["id"])
        if len(re.sub(r"<[^>]+>", "", p.get("body_html") or "")) >= 150:
            score += 15
        if p.get("vendor") and p.get("product_type"):
            score += 10
        if (p.get("tags") or "").strip():
            score += 10

        variants = p.get("variants") or []
        if variants and all((v.get("sku") or "").strip() for v in variants):
            score += 20
        if variants and all(int(v.get("grams") or 0) > 0 for v in variants):
            score += 15
        else:
            missing_grams.append(p["id"])
        if variants and all((v.get("barcode") or "").strip() for v in variants):
            score += 10

        for v in variants:
            sku = (v.get("sku") or "").strip().upper()
            if sku:
                sku_map[sku].append({"product_id": p["id"], "variant_id": v["id"], "title": p["title"]})
            price = float(v.get("price") or 0)
            cmp_p = float(v.get("compare_at_price") or 0)
            if cmp_p > 0 and cmp_p <= price:
                bad_compare_at.append({"variant_id": v["id"], "price": price, "compare_at_price": cmp_p})
        scores.append(score)

    dup_skus = {k: v for k, v in sku_map.items() if len(v) > 1}
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    return {
        "skill": "catalog-data-completeness-audit",
        "products_scanned": len(products),
        "avg_quality_score": avg_score,
        "duplicate_skus": dup_skus,
        "missing_images_ids": missing_images,
        "missing_alt_text_ids": missing_alt,
        "missing_grams_ids": missing_grams,
        "invalid_compare_at_price": bad_compare_at,
    }


def cmd_low_stock(data: Dict[str, Any], threshold: int = 10) -> Dict[str, Any]:
    rows = data["inventory_locations"]
    negative = [r for r in rows if int(r.get("qty_available", 0)) < 0]
    low = [r for r in rows if 0 <= int(r.get("qty_available", 0)) <= threshold]
    return {
        "skill": "inventory-low-stock-watchdog",
        "threshold": threshold,
        "negative_stock_p0": negative,
        "low_stock_p1": low,
        "total_records_checked": len(rows),
    }


def cmd_cod_risk(data: Dict[str, Any], high_value_vnd: int = 2000000) -> Dict[str, Any]:
    flagged = []
    for o in data["orders"]:
        if o.get("cancelled_at") or o.get("fulfillment_status") == "fulfilled":
            continue
        is_cod = "cod" in (o.get("gateway") or "").lower() or o.get("financial_status") == "pending"
        if not is_cod:
            continue
        score = 0
        signals = []
        total = float(o.get("total_price") or 0)
        if total >= high_value_vnd:
            score += 30
            signals.append("HIGH_VALUE_COD")
        addr = o.get("shipping_address") or {}
        if not (addr.get("ward") or "").strip():
            score += 25
            signals.append("MISSING_VN_WARD")
        cust = o.get("customer") or {}
        if int(cust.get("cancelled_orders_count") or 0) >= 2:
            score += 40
            signals.append("PRIOR_CANCELLATIONS")
        if score >= 30:
            flagged.append(
                {
                    "order_id": o["id"],
                    "order_name": o.get("name"),
                    "total_price_vnd": total,
                    "risk_score": score,
                    "risk_tier": "HIGH_CALL_VERIFY" if score >= 60 else "MEDIUM_ZNS_VERIFY",
                    "signals": signals,
                    "customer_phone_redacted": redact_phone(cust.get("phone")),
                }
            )
    return {
        "skill": "order-risk-cod-boom-signals",
        "note": "Signals only — NEVER auto-cancel orders without CS verification.",
        "flagged_orders": flagged,
    }


def cmd_wismo(data: Dict[str, Any], stuck_hours: int = 48) -> Dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc)
    stuck = []
    for o in data["orders"]:
        if o.get("cancelled_at") or o.get("fulfillment_status") == "fulfilled":
            continue
        created = dt.datetime.strptime(o["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        age_h = round((now - created).total_seconds() / 3600.0, 1)
        if age_h >= stuck_hours:
            stuck.append({"order_id": o["id"], "order_name": o.get("name"), "source": o.get("source_name"), "age_hours": age_h})
    return {"skill": "fulfillment-status-digest-wismo", "stuck_threshold_hours": stuck_hours, "stuck_orders": stuck}


def cmd_rfm(data: Dict[str, Any]) -> Dict[str, Any]:
    phone_groups: Dict[str, List[int]] = defaultdict(list)
    tiers = Counter()
    for c in data["customers"]:
        p = normalize_vn_phone(c.get("phone"))
        if p:
            phone_groups[p].append(c["id"])
        spent = float(c.get("total_spent") or 0)
        orders_cnt = int(c.get("orders_count") or 0)
        if spent >= 5000000 and orders_cnt >= 3:
            tiers["Champions_VIP"] += 1
        elif orders_cnt >= 2:
            tiers["Loyal_Repeat"] += 1
        else:
            tiers["New_OneTime"] += 1

    duplicates = [
        {"phone_redacted": redact_phone(p), "customer_ids": ids}
        for p, ids in phone_groups.items()
        if len(ids) > 1
    ]
    return {
        "skill": "customer-rfm-segmentation",
        "customers_analyzed": len(data["customers"]),
        "segment_distribution": dict(tiers),
        "duplicate_phone_clusters": duplicates,
        "pii_export_allowed": False,
    }


def cmd_promo_audit(data: Dict[str, Any]) -> Dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc)
    issues = []
    for pr in data["promotions"]:
        ends = pr.get("ends_at")
        if ends:
            end_dt = dt.datetime.strptime(ends, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
            if end_dt < now and pr.get("status") == "enabled":
                issues.append({"promotion_id": pr["id"], "title": pr["title"], "issue": "EXPIRED_STILL_ENABLED"})
        else:
            issues.append({"promotion_id": pr["id"], "title": pr["title"], "issue": "NO_END_DATE"})
        if pr.get("value_type") == "percentage" and float(pr.get("value") or 0) > 40:
            issues.append({"promotion_id": pr["id"], "title": pr["title"], "issue": f"HIGH_DISCOUNT_{pr['value']}%"})
    return {"skill": "marketing-promotion-hygiene-audit", "promotions_checked": len(data["promotions"]), "issues": issues}


def cmd_redirect_audit(data: Dict[str, Any]) -> Dict[str, Any]:
    mapping = {r["path"]: r["target"] for r in data["redirects"]}
    loops, chains = [], []
    for src, tgt in mapping.items():
        if tgt in mapping:
            if mapping[tgt] == src:
                loops.append([src, tgt, src])
            else:
                chains.append([src, tgt, mapping[tgt]])
    return {"skill": "store-redirect-audit", "total_redirects": len(mapping), "loops": loops, "chains": chains}


def cmd_morning_briefing(data: Dict[str, Any]) -> Dict[str, Any]:
    by_channel: Dict[str, float] = defaultdict(float)
    active_orders = [o for o in data["orders"] if not o.get("cancelled_at")]
    for o in active_orders:
        by_channel[o.get("source_name") or "unknown"] += float(o.get("total_price") or 0)
    return {
        "skill": "ops-daily-morning-briefing",
        "disclaimer": FINANCIAL_DISCLAIMER,
        "orders_count": len(active_orders),
        "gross_revenue_vnd": sum(by_channel.values()),
        "revenue_by_channel_vnd": dict(by_channel),
        "cod_risk_alerts": len(cmd_cod_risk(data)["flagged_orders"]),
        "low_stock_alerts": len(cmd_low_stock(data)["negative_stock_p0"]) + len(cmd_low_stock(data)["low_stock_p1"]),
        "stuck_fulfillments": len(cmd_wismo(data)["stuck_orders"]),
    }


def cmd_health_check(data: Dict[str, Any]) -> Dict[str, Any]:
    cat = cmd_catalog_audit(data)
    inv = cmd_low_stock(data)
    promo = cmd_promo_audit(data)
    cod = cmd_cod_risk(data)
    inv_score = max(0, 100 - len(inv["negative_stock_p0"]) * 30 - len(inv["low_stock_p1"]) * 10)
    promo_score = max(0, 100 - len(promo["issues"]) * 15)
    theme_score = 100 if any(t.get("role") == "main" for t in data.get("themes", [])) else 0
    overall = round((cat["avg_quality_score"] + inv_score + promo_score + theme_score) / 4.0, 1)
    return {
        "skill": "store-health-check",
        "overall_score": overall,
        "pillars": {
            "catalog": cat["avg_quality_score"],
            "inventory": inv_score,
            "promotions": promo_score,
            "storefront_theme": theme_score,
        },
        "priority_alerts": {
            "duplicate_skus": len(cat["duplicate_skus"]),
            "negative_stock": len(inv["negative_stock_p0"]),
            "cod_risk_orders": len(cod["flagged_orders"]),
            "promotion_issues": len(promo["issues"]),
        },
    }


def cmd_price_dry_run(data: Dict[str, Any], pct: float, output_dir: str) -> Dict[str, Any]:
    if abs(pct) > 30.0:
        raise ValueError(f"Blocked by guardrail: {pct}% exceeds ±30% max_change_pct_guard.")
    changes = []
    for p in data["products"]:
        for v in p.get("variants", []):
            old_p = float(v.get("price") or 0)
            new_p = round((old_p * (1.0 + pct / 100.0)) / 1000.0) * 1000
            if new_p <= 0:
                continue
            changes.append(
                {
                    "record_id": f"variant_{v['id']}",
                    "field": "price",
                    "before": int(old_p),
                    "after": int(new_p),
                    "risk_note": f"{pct:+.1f}% rounded to 1,000 VND",
                }
            )
    artifacts = write_dry_run_artifact(
        output_dir=output_dir,
        skill_name="pricing-bulk-adjustment-proposal",
        store_domain=data["shop"].get("domain", "unknown"),
        environment="staging",
        changes=changes,
        rollback_supported=True,
    )
    return {
        "skill": "pricing-bulk-adjustment-proposal",
        "dry_run": True,
        "separate_turn_confirmation_required": True,
        "total_variants": len(changes),
        "artifacts": artifacts,
        "preview": changes[:10],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Haravan Operational Skills CLI Runner")
    parser.add_argument("--demo", action="store_true", help="Run offline with realistic VN Haravan demo dataset")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("probe", "health-check", "catalog-audit", "low-stock", "cod-risk", "wismo", "rfm", "promo-audit", "redirect-audit", "morning-briefing"):
        sub.add_parser(name)
    p_price = sub.add_parser("price-dry-run")
    p_price.add_argument("--pct", type=float, required=True, help="Percentage price change (guarded within ±30%%)")
    p_price.add_argument("--out", default="artifacts", help="Directory for backup JSON & preview CSV")

    args = parser.parse_args(argv)
    client = None if args.demo else HaravanClient(dry_run=True)

    need_map = {
        "probe": ["shop", "locations"],
        "health-check": ["shop", "products", "inventory_locations", "orders", "promotions", "themes"],
        "catalog-audit": ["products"],
        "low-stock": ["inventory_locations"],
        "cod-risk": ["orders"],
        "wismo": ["orders"],
        "rfm": ["customers"],
        "promo-audit": ["promotions"],
        "redirect-audit": ["redirects"],
        "morning-briefing": ["orders", "inventory_locations"],
        "price-dry-run": ["shop", "products"],
    }
    data = load_data(client, args.demo, need_map[args.command])

    handlers = {
        "probe": lambda: cmd_probe(data),
        "health-check": lambda: cmd_health_check(data),
        "catalog-audit": lambda: cmd_catalog_audit(data),
        "low-stock": lambda: cmd_low_stock(data),
        "cod-risk": lambda: cmd_cod_risk(data),
        "wismo": lambda: cmd_wismo(data),
        "rfm": lambda: cmd_rfm(data),
        "promo-audit": lambda: cmd_promo_audit(data),
        "redirect-audit": lambda: cmd_redirect_audit(data),
        "morning-briefing": lambda: cmd_morning_briefing(data),
        "price-dry-run": lambda: cmd_price_dry_run(data, args.pct, args.out),
    }
    result = handlers[args.command]()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
