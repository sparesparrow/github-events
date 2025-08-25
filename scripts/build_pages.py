"""
Build a simple static HTML visualization page from a SQLite DB artifact.

Reads site/github_events.db (if present) and writes site/index.html.
Uses only Python standard library.
"""

import json
import sqlite3
from pathlib import Path


def load_event_counts(database_path: Path) -> dict:
    if not database_path.exists():
        return {}
    try:
        connection = sqlite3.connect(str(database_path))
        cursor = connection.cursor()
        cursor.execute(
            "SELECT event_type, COUNT(*) FROM events GROUP BY event_type"
        )
        result = {row[0]: int(row[1]) for row in cursor.fetchall()}
        connection.close()
        return result
    except Exception:
        return {}


def build_html(counts: dict) -> str:
    counts_json = json.dumps(counts)
    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        "  <meta charset='utf-8'/>\n"
        "  <title>GitHub Events Monitor</title>\n"
        "  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>\n"
        "  <style>body{font-family:system-ui,Segoe UI,Arial;margin:24px;} .wrap{max-width:1000px;margin:auto;} h1{margin-bottom:8px}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <div class=\"wrap\">\n"
        "    <h1>GitHub Events Monitor</h1>\n"
        "    <p>Static visualization built from CI artifact.</p>\n"
        "    <div id=\"chart\" style=\"width:100%;height:520px;\"></div>\n"
        "  </div>\n"
        "  <script>\n"
        f"    const counts = {counts_json};\n"
        "    const types = Object.keys(counts);\n"
        "    const values = types.map(t => counts[t]);\n"
        "    const data = [{type:'bar', x: types, y: values, marker:{color:'#3b82f6'}}];\n"
        "    const layout = {title:'Event Counts by Type', xaxis:{title:'Event Type'}, yaxis:{title:'Count'}};\n"
        "    Plotly.newPlot('chart', data, layout, {displaylogo:false});\n"
        "  </script>\n"
        "</body>\n"
        "</html>\n"
    )


def main() -> None:
    site_dir = Path("site")
    site_dir.mkdir(parents=True, exist_ok=True)
    db_path = site_dir / "github_events.db"
    html_path = site_dir / "index.html"

    counts = load_event_counts(db_path)
    html = build_html(counts)
    html_path.write_text(html)


if __name__ == "__main__":
    main()


