from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest

from core.google_logger import GoogleSheetLogger
from core.workspace_settings import load_workspace_settings


PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
SEARCH_CONSOLE_ENDPOINT = "https://searchconsole.googleapis.com/webmasters/v3"


def _workspace_value(key: str, *fallbacks: str) -> str:
    workspace_settings = load_workspace_settings()
    for candidate in (key, *fallbacks):
        value = os.getenv(candidate, "").strip()
        if value:
            return value
    for candidate in (key, *fallbacks):
        value = str(workspace_settings.get(candidate, "")).strip()
        if value:
            return value
    return ""


def _request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: Any = None) -> Any:
    data = None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("error", {}).get("message") or detail
        except json.JSONDecodeError:
            message = detail or exc.reason
        raise RuntimeError(message) from exc


def _score(category: dict[str, Any] | None) -> int | None:
    value = (category or {}).get("score")
    if isinstance(value, (int, float)):
        return round(value * 100)
    return None


def _audit_value(audits: dict[str, Any], key: str) -> dict[str, Any]:
    audit = audits.get(key) or {}
    return {
        "id": key,
        "title": audit.get("title", key),
        "display_value": audit.get("displayValue") or "",
        "score": audit.get("score"),
        "numeric_value": audit.get("numericValue"),
    }


def get_pagespeed_insights(url: str, *, strategy: str = "mobile", google_api_key: str | None = None) -> dict[str, Any]:
    api_key = (google_api_key or "").strip() or _workspace_value("AUTOMATION_GOOGLE_API_KEY", "GOOGLE_API_KEY")
    params = [
        ("url", url),
        ("strategy", strategy),
        ("category", "performance"),
        ("category", "accessibility"),
        ("category", "best-practices"),
        ("category", "seo"),
    ]
    if api_key:
        params.append(("key", api_key))
    payload = _request_json(f"{PAGESPEED_ENDPOINT}?{urllib.parse.urlencode(params)}")
    lighthouse = payload.get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    audits = lighthouse.get("audits") or {}
    loading = payload.get("loadingExperience") or {}
    origin_loading = payload.get("originLoadingExperience") or {}
    return {
        "url": payload.get("id") or url,
        "strategy": strategy,
        "fetched_at": payload.get("analysisUTCTimestamp") or "",
        "scores": {
            "performance": _score(categories.get("performance")),
            "accessibility": _score(categories.get("accessibility")),
            "best_practices": _score(categories.get("best-practices")),
            "seo": _score(categories.get("seo")),
        },
        "metrics": [
            _audit_value(audits, "first-contentful-paint"),
            _audit_value(audits, "largest-contentful-paint"),
            _audit_value(audits, "total-blocking-time"),
            _audit_value(audits, "cumulative-layout-shift"),
            _audit_value(audits, "speed-index"),
        ],
        "opportunities": [
            {
                "id": key,
                "title": audit.get("title", key),
                "display_value": audit.get("displayValue") or "",
                "description": audit.get("description") or "",
                "score": audit.get("score"),
            }
            for key, audit in audits.items()
            if isinstance(audit, dict)
            and audit.get("details", {}).get("type") == "opportunity"
            and audit.get("score") not in (None, 1)
        ][:8],
        "field_data": {
            "page": loading.get("overall_category") or "UNKNOWN",
            "origin": origin_loading.get("overall_category") or "UNKNOWN",
        },
    }


def _search_console_credentials():
    scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
    credentials = GoogleSheetLogger._load_credentials(scopes)
    credentials.refresh(GoogleAuthRequest())
    return credentials


def _candidate_site_urls(target_url: str, explicit_site_url: str | None = None) -> list[str]:
    if explicit_site_url:
        return [explicit_site_url]
    parsed = urllib.parse.urlparse(target_url)
    if not parsed.scheme or not parsed.netloc:
        return [target_url]
    origin = f"{parsed.scheme}://{parsed.netloc}/"
    domain = parsed.netloc[4:] if parsed.netloc.startswith("www.") else parsed.netloc
    return [target_url, origin, f"sc-domain:{domain}"]


def get_search_console_data(
    url: str,
    *,
    site_url: str | None = None,
    days: int = 28,
) -> dict[str, Any]:
    credentials = _search_console_credentials()
    headers = {"Authorization": f"Bearer {credentials.token}"}
    sites_payload = _request_json(f"{SEARCH_CONSOLE_ENDPOINT}/sites", headers=headers)
    available_sites = [item.get("siteUrl", "") for item in sites_payload.get("siteEntry", []) if item.get("siteUrl")]
    candidates = _candidate_site_urls(url, site_url)
    selected_site = next((candidate for candidate in candidates if candidate in available_sites), site_url or "")
    if not selected_site:
        return {
            "url": url,
            "site_url": "",
            "available_sites": available_sites,
            "summary": {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0},
            "rows": [],
            "queries": [],
            "pages": [],
            "countries": [],
            "devices": [],
            "message": "No matching Search Console property is accessible for this URL.",
        }

    end_date = date.today() - timedelta(days=2)
    start_date = end_date - timedelta(days=max(days, 1) - 1)

    def query(dimensions: list[str], row_limit: int = 25) -> list[dict[str, Any]]:
        encoded_site = urllib.parse.quote(selected_site, safe="")
        payload = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dimensions,
            "rowLimit": row_limit,
        }
        if dimensions != ["page"]:
            payload["dimensionFilterGroups"] = [
                {
                    "filters": [
                        {
                            "dimension": "page",
                            "operator": "equals",
                            "expression": url,
                        }
                    ]
                }
            ]
        result = _request_json(
            f"{SEARCH_CONSOLE_ENDPOINT}/sites/{encoded_site}/searchAnalytics/query",
            method="POST",
            headers=headers,
            payload=payload,
        )
        return result.get("rows", [])

    rows = query(["date"], 90)
    queries = query(["query"], 20)
    pages = query(["page"], 20)
    countries = query(["country"], 10)
    devices = query(["device"], 10)
    clicks = sum(float(row.get("clicks", 0) or 0) for row in rows)
    impressions = sum(float(row.get("impressions", 0) or 0) for row in rows)
    weighted_position = sum(float(row.get("position", 0) or 0) * float(row.get("impressions", 0) or 0) for row in rows)
    return {
        "url": url,
        "site_url": selected_site,
        "available_sites": available_sites,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": {
            "clicks": round(clicks),
            "impressions": round(impressions),
            "ctr": clicks / impressions if impressions else 0,
            "position": weighted_position / impressions if impressions else 0,
        },
        "rows": rows,
        "queries": queries,
        "pages": pages,
        "countries": countries,
        "devices": devices,
    }
