import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any
import requests
import plotly.graph_objects as go
import os

def _fetch_json(url: str) -> Any:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

def _parse_trending(trending_json: Any) -> Tuple[List[str], List[int]]:
    """
    Attempt to parse common shapes:
      - [{"repo":"owner/name","count":123}, ...]
      - [{"repository":"owner/name","events":123}, ...]
      - {"items":[...]}
    """
    data = trending_json
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    labels, values = [], []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("repo") or item.get("repository") or item.get("name") or ""
            cnt = item.get("count")
            if cnt is None:
                cnt = item.get("events")
            try:
                cnt = int(cnt)
            except Exception:
                cnt = 0
            if name:
                labels.append(name)
                values.append(cnt)
    return labels, values

def _parse_counts(json_obj: Any) -> Dict[str, int]:
    """
    Expecting {"WatchEvent": n, "PullRequestEvent": m, "IssuesEvent": k}
    but tolerate {"data": {...}} or list of pairs.
    """
    if isinstance(json_obj, dict):
        inner = json_obj.get("data")
        if isinstance(inner, dict):
            return {str(k): int(v) for k, v in inner.items() if isinstance(v, (int, float))}
        return {str(k): int(v) for k, v in json_obj.items() if isinstance(v, (int, float))}
    if isinstance(json_obj, list):
        out: Dict[str, int] = {}
        for item in json_obj:
            if isinstance(item, dict):
                k = item.get("type") or item.get("name")
                v = item.get("count") or item.get("value")
                if k is not None and v is not None:
                    try:
                        out[str(k)] = int(v)
                    except Exception:
                        pass
        return out
    return {}

def generate_dashboard_html(
    base_url: str = "http://localhost:8000",
    hours: int = 24,
    limit: int = 5,
    output_path: str = "docs/index.html",
    include_plotlyjs: str = "cdn"  # "cdn" or "inline"
) -> str:
    # Fetch inputs
    health = _fetch_json(f"{base_url}/health")
    trending = _fetch_json(f"{base_url}/metrics/trending?hours={hours}&limit={limit}")
    ec10 = _fetch_json(f"{base_url}/metrics/event-counts?offset_minutes=10")
    ec60 = _fetch_json(f"{base_url}/metrics/event-counts?offset_minutes=60")

    # Parse
    trending_labels, trending_values = _parse_trending(trending)
    counts10 = _parse_counts(ec10)
    counts60 = _parse_counts(ec60)
    event_types = sorted(set(counts10.keys()) | set(counts60.keys()))
    y10 = [counts10.get(t, 0) for t in event_types]
    y60 = [counts60.get(t, 0) for t in event_types]

    # Build charts
    trend_fig = go.Figure(data=[go.Bar(x=trending_labels, y=trending_values, marker_color="#1f77b4")])
    trend_fig.update_layout(title=f"Trending Repositories (last {hours}h)", xaxis_title="Repository", yaxis_title="Events", template="plotly_white")

    counts_fig = go.Figure(data=[
        go.Bar(name="10 min", x=event_types, y=y10, marker_color="#2ca02c"),
        go.Bar(name="60 min", x=event_types, y=y60, marker_color="#ff7f0e"),
    ])
    counts_fig.update_layout(barmode="group", title="Event Counts (last 10 vs 60 minutes)", xaxis_title="Event Type", yaxis_title="Events", template="plotly_white", legend=dict(orientation="h"))

    # Inline vs CDN script
    trend_html = trend_fig.to_html(full_html=False, include_plotlyjs=(include_plotlyjs == "inline"))
    counts_html = counts_fig.to_html(full_html=False, include_plotlyjs=False)

    # Health snapshot
    status = ""
    try:
        status = health.get("data", {}).get("status", "")
    except Exception:
        status = ""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")

    # Build HTML skeleton
    head_scripts = ""
    if include_plotlyjs == "cdn":
        head_scripts = "<script src=\"https://cdn.plot.ly/plotly-2.32.0.min.js\"></script>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>GitHub Events Monitor — Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  {head_scripts}
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 0; }}
    .muted {{ color: #666; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 24px; }}
    @media (min-width: 960px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
    .card {{ border: 1px solid #eee; border-radius: 12px; padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
    .status {{ display: flex; gap: 8px; align-items: center; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; background: #2ecc71; display: inline-block; }}
    pre {{ background: #f9f9f9; padding: 12px; border-radius: 8px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>GitHub Events Monitor — Dashboard</h1>
  <p class="status"><span class="dot"></span> Status: {status or "unknown"} · Updated: {ts}</p>

  <div class="grid">
    <div class="card">
      <h2>Trending Repositories</h2>
      {trend_html}
    </div>
    <div class="card">
      <h2>Event Counts</h2>
      {counts_html}
    </div>
  </div>

  <div class="card" style="margin-top:24px">
    <h3>Debug</h3>
    <pre>{json.dumps({ "health": health, "trending_sample": trending_labels[:5] }, indent=2)}</pre>
  </div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
