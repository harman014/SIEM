"""
AI-SIEM Frontend API
FastAPI backend that proxies Elasticsearch queries and serves the dashboard UI.
"""
import os
from datetime import datetime, timezone
from typing import Optional
import httpx
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

# ── Config ─────────────────────────────────────────────────────────────────────
ES_HOST = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
ES_PORT = int(os.getenv("ELASTICSEARCH_PORT", 9200))
ES_URL  = f"http://{ES_HOST}:{ES_PORT}"
ES_AUTH = (
    os.getenv("ELASTICSEARCH_USER", "elastic"),
    os.getenv("ELASTICSEARCH_PASSWORD", "change_me_elastic_password"),
)

app = FastAPI(title="AI-SIEM Dashboard API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Helpers ────────────────────────────────────────────────────────────────────
async def es_search(index: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{ES_URL}/{index}/_search",
            json=body,
            auth=ES_AUTH,
        )
        return r.json() if r.status_code == 200 else {"hits": {"hits": [], "total": {"value": 0}}}


async def es_count(index: str) -> int:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{ES_URL}/{index}/_count", auth=ES_AUTH)
        return r.json().get("count", 0) if r.status_code == 200 else 0


async def es_cluster_health() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{ES_URL}/_cluster/health", auth=ES_AUTH)
        return r.json() if r.status_code == 200 else {}


# ── Pages ──────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ── API Endpoints ──────────────────────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats():
    health   = await es_cluster_health()
    logs     = await es_count("siem-logs-*")
    threats  = await es_count("siem-threats*")
    anomalies= await es_count("siem-anomalies*")
    alerts   = await es_count("siem-alerts*")
    response_actions = await es_count("siem-response-actions-*")
    return {
        "cluster_status": health.get("status", "unknown"),
        "active_nodes": health.get("number_of_nodes", 0),
        "active_shards": health.get("active_shards", 0),
        "logs_indexed": logs,
        "threats_detected": threats,
        "anomalies_detected": anomalies,
        "alerts_fired": alerts,
        "ips_blocked": response_actions,
    }


@app.get("/api/threats")
async def get_threats(hours: int = 24, severity: Optional[str] = None, limit: int = 50):
    must = [{"range": {"@timestamp": {"gte": f"now-{hours}h"}}}]
    if severity:
        must.append({"match": {"severity": severity}})
    body = {
        "query": {"bool": {"must": must}},
        "sort": [{"@timestamp": {"order": "desc"}}],
        "size": limit,
    }
    data = await es_search("siem-threats*", body)
    return [h["_source"] for h in data["hits"]["hits"]]


@app.get("/api/anomalies")
async def get_anomalies(hours: int = 24, limit: int = 50):
    body = {
        "query": {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
        "sort": [{"anomaly_score": {"order": "asc"}}],
        "size": limit,
    }
    data = await es_search("siem-anomalies*", body)
    return [h["_source"] for h in data["hits"]["hits"]]


@app.get("/api/alerts")
async def get_alerts(hours: int = 24, limit: int = 50):
    body = {
        "query": {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
        "sort": [{"@timestamp": {"order": "desc"}}],
        "size": limit,
    }
    data = await es_search("siem-alerts*", body)
    return [h["_source"] for h in data["hits"]["hits"]]


@app.get("/api/blocked")
async def get_blocked(hours: int = 24, limit: int = 50):
    body = {
        "query": {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
        "sort": [{"@timestamp": {"order": "desc"}}],
        "size": limit,
    }
    data = await es_search("siem-response-actions-*", body)
    return [h["_source"] for h in data["hits"]["hits"]]


@app.get("/api/logs")
async def get_logs(
    hours: int = 1,
    limit: int = 100,
    q: Optional[str] = Query(None, description="Lucene query string"),
):
    must = [{"range": {"@timestamp": {"gte": f"now-{hours}h"}}}]
    if q:
        must.append({"query_string": {"query": q}})
    body = {
        "query": {"bool": {"must": must}},
        "sort": [{"@timestamp": {"order": "desc"}}],
        "size": limit,
    }
    data = await es_search("siem-logs-*", body)
    return [h["_source"] for h in data["hits"]["hits"]]


@app.get("/api/timeline")
async def get_timeline(hours: int = 24):
    """Events-over-time histogram (1h buckets)."""
    body = {
        "query": {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
        "aggs": {
            "over_time": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "1h",
                    "min_doc_count": 0,
                    "extended_bounds": {
                        "min": f"now-{hours}h",
                        "max": "now",
                    },
                }
            }
        },
        "size": 0,
    }
    data = await es_search("siem-logs-*", body)
    buckets = data.get("aggregations", {}).get("over_time", {}).get("buckets", [])
    return [{"time": b["key_as_string"], "count": b["doc_count"]} for b in buckets]


@app.get("/api/severity_breakdown")
async def get_severity_breakdown(hours: int = 24):
    """Threat count by severity."""
    body = {
        "query": {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
        "aggs": {
            "by_severity": {
                "terms": {"field": "severity.keyword", "size": 10}
            }
        },
        "size": 0,
    }
    data = await es_search("siem-threats*", body)
    buckets = data.get("aggregations", {}).get("by_severity", {}).get("buckets", [])
    return [{"severity": b["key"], "count": b["doc_count"]} for b in buckets]
