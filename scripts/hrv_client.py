#!/usr/bin/env python3
"""
Haravan Omni & Web REST API Client with built-in operational guardrails:
- Leaky-bucket rate limiter (80 bucket, 4 req/s leak, safe default 2.5 req/s)
- Exponential backoff for HTTP 429 and 5xx
- Dry-run enforcement for all mutating HTTP verbs (POST/PUT/PATCH/DELETE)
- Webhook HMAC-SHA256 signature verification (X-Haravan-Hmacsha256)
- Vietnam PII redaction helpers (phone, email)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

BASE_URLS = {
    "com": "https://apis.haravan.com/com",
    "web": "https://apis.haravan.com/web",
    "webhook": "https://webhook.haravan.com/api",
}

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def redact_phone(phone: Optional[str]) -> str:
    """Mask Vietnam phone numbers: 0901234567 -> 090****567."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) < 6:
        return "***"
    return f"{digits[:3]}{'*' * (len(digits) - 6)}{digits[-3:]}"


def redact_email(email: Optional[str]) -> str:
    """Mask email local part: nguyen.a@gmail.com -> ng***@gmail.com."""
    if not email or "@" not in str(email):
        return ""
    local, domain = str(email).split("@", 1)
    prefix = local[:2] if len(local) >= 2 else local[:1]
    return f"{prefix}***@{domain}"


def verify_webhook_hmac(raw_body: bytes, header_hmac: str, secret: str) -> bool:
    """Verify Haravan X-Haravan-Hmacsha256 header using constant-time comparison."""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, header_hmac.strip())


@dataclass
class LeakyBucketLimiter:
    """Client-side leaky bucket matching Haravan limits (80 cap, 4 req/s leak)."""

    capacity: float = 80.0
    leak_rate: float = 2.5  # Safe operational rate (< 4 req/s official limit)
    water: float = 0.0
    last_ts: float = field(default_factory=time.monotonic)

    def acquire(self, cost: float = 1.0) -> float:
        now = time.monotonic()
        elapsed = max(0.0, now - self.last_ts)
        self.water = max(0.0, self.water - elapsed * self.leak_rate)
        self.last_ts = now

        slept = 0.0
        if self.water + cost > self.capacity - 10.0:  # Keep 10-req burst reserve
            overflow = (self.water + cost) - (self.capacity - 10.0)
            wait_sec = overflow / self.leak_rate
            time.sleep(wait_sec)
            slept = wait_sec
            self.last_ts = time.monotonic()
            self.water = max(0.0, self.water - wait_sec * self.leak_rate)

        self.water += cost
        return slept


class HaravanClient:
    """Safe Haravan REST API client for operational AI skills."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        dry_run: bool = True,
        max_retries: int = 5,
        timeout: int = 30,
    ) -> None:
        self.access_token = access_token or os.environ.get("HARAVAN_ACCESS_TOKEN", "")
        self.dry_run = dry_run
        self.max_retries = max_retries
        self.timeout = timeout
        self.limiter = LeakyBucketLimiter()

    def request(
        self,
        method: str,
        surface: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        method = method.upper()
        if surface not in BASE_URLS:
            raise ValueError(f"Unsupported Haravan API surface: {surface}")

        base = BASE_URLS[surface].rstrip("/")
        clean_path = "/" + path.lstrip("/")
        url = f"{base}{clean_path}"
        if params:
            query = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}, doseq=True
            )
            if query:
                url = f"{url}?{query}"

        if method in MUTATING_METHODS and self.dry_run:
            return {
                "dry_run": True,
                "blocked_mutation": True,
                "method": method,
                "url": url,
                "payload_preview": payload,
            }

        if not self.access_token:
            raise RuntimeError(
                "Missing HARAVAN_ACCESS_TOKEN. Export it via environment variable; never hardcode."
            )

        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            self.limiter.acquire()
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                status = exc.code
                err_body = exc.read().decode("utf-8", errors="replace")
                if status in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(min(backoff, 30.0))
                    backoff *= 2.0
                    continue
                raise RuntimeError(
                    f"Haravan API error {status} on {method} {url}: {err_body[:500]}"
                ) from exc

        raise RuntimeError(f"Exhausted retries on {method} {url}")

    def paginate(
        self,
        surface: str,
        path: str,
        resource_key: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        max_pages: int = 50,
    ) -> List[Dict[str, Any]]:
        """Paginate through a Haravan GET collection endpoint safely."""
        results: List[Dict[str, Any]] = []
        base_params = dict(params or {})
        base_params["limit"] = min(limit, 250)

        for page in range(1, max_pages + 1):
            base_params["page"] = page
            data = self.request("GET", surface, path, params=base_params)
            items = data.get(resource_key, [])
            if not items:
                break
            results.extend(items)
            if len(items) < base_params["limit"]:
                break
        return results


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "client": "HaravanClient",
                "surfaces": BASE_URLS,
                "default_dry_run": True,
                "sample_phone_redact": redact_phone("0901234567"),
                "sample_email_redact": redact_email("merchant.vn@haravan.com"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
