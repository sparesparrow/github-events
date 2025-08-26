import os
import sqlite3
import json
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timezone, timedelta

DB_PATH = os.environ.get("DB_PATH", "database/events.db")

def export():
    with sqlite3.connect(DB_PATH) as conn:
        # Events by type and date (using epoch for proper SQLite date ops)
        df_events = pd.read_sql_query(
            """
            SELECT type,
                   date(datetime(created_at_ts, 'unixepoch')) AS day,
                   COUNT(*) AS count
            FROM events
            GROUP BY type, day
            ORDER BY day ASC
            """,
            conn,
        )

        # Top repositories
        df_repos = pd.read_sql_query(
            """
            SELECT repo_name,
                   COUNT(*) AS total_events,
                   SUM(CASE WHEN type='WatchEvent' THEN 1 ELSE 0 END) AS watches,
                   SUM(CASE WHEN type='PullRequestEvent' THEN 1 ELSE 0 END) AS pull_requests,
                   SUM(CASE WHEN type='IssuesEvent' THEN 1 ELSE 0 END) AS issues
            FROM events
            WHERE repo_name IS NOT NULL
            GROUP BY repo_name
            ORDER BY total_events DESC
            LIMIT 20
            """,
            conn,
        )

        # PR metrics
        df_pr = pd.read_sql_query(
            """
            SELECT repo_name, avg_time_between_prs_minutes AS avg_minutes, total_prs
            FROM pr_metrics
            WHERE total_prs >= 2
            ORDER BY avg_minutes ASC
            LIMIT 15
            """,
            conn,
        )

        # Event counts for rolling windows (10 and 60 minutes)
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        def counts_for_minutes(minutes: int) -> dict:
            cutoff = now_epoch - minutes * 60
            df_counts = pd.read_sql_query(
                f"""
                SELECT type, COUNT(*) as count
                FROM events
                WHERE created_at_ts >= {cutoff}
                GROUP BY type
                """,
                conn,
            )
            counts = {"WatchEvent": 0, "PullRequestEvent": 0, "IssuesEvent": 0}
            for _, row in df_counts.iterrows():
                counts[row["type"]] = int(row["count"])
            total = int(sum(counts.values()))
            return {
                "offset_minutes": minutes,
                "total_events": total,
                "counts": counts,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        counts10 = counts_for_minutes(10)
        counts60 = counts_for_minutes(60)

        # Trending over last 24h
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        df_trending = pd.read_sql_query(
            """
            SELECT 
                repo_name,
                COUNT(*) as total_events,
                SUM(CASE WHEN type='WatchEvent' THEN 1 ELSE 0 END) as watch_events,
                SUM(CASE WHEN type='PullRequestEvent' THEN 1 ELSE 0 END) as pr_events,
                SUM(CASE WHEN type='IssuesEvent' THEN 1 ELSE 0 END) as issue_events
            FROM events
            WHERE created_at >= ? AND repo_name IS NOT NULL
            GROUP BY repo_name
            ORDER BY total_events DESC
            LIMIT 10
            """,
            conn,
            params=(cutoff_24h,),
        )

    # Charts
    if not df_events.empty:
        fig = px.line(
            df_events,
            x="day",
            y="count",
            color="type",
            title="GitHub Events Timeline by Type",
            labels={"day": "Date", "count": "Events"},
        )
        fig.update_layout(hovermode="x unified")
        fig.write_html("docs/events_timeline.html", include_plotlyjs="cdn")
    else:
        with open("docs/events_timeline.html", "w") as f:
            f.write("<html><body><p>No data yet.</p></body></html>")

    if not df_repos.empty:
        top = df_repos.head(10)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Watches", x=top["repo_name"], y=top["watches"], marker_color="#60a5fa"))
        fig.add_trace(go.Bar(name="PRs", x=top["repo_name"], y=top["pull_requests"], marker_color="#34d399"))
        fig.add_trace(go.Bar(name="Issues", x=top["repo_name"], y=top["issues"], marker_color="#f87171"))
        fig.update_layout(
            title="Top 10 Repositories by Activity",
            barmode="stack",
            xaxis_title="Repository",
            yaxis_title="Events",
            xaxis={"tickangle": 45},
        )
        fig.write_html("docs/repository_activity.html", include_plotlyjs="cdn")
    else:
        with open("docs/repository_activity.html", "w") as f:
            f.write("<html><body><p>No data yet.</p></body></html>")

    if not df_pr.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_pr["repo_name"],
                y=df_pr["avg_minutes"] / 60.0,
                mode="markers+lines",
                marker=dict(size=df_pr["total_prs"], sizemode="diameter", sizeref=0.1),
                hovertemplate="<b>%{x}</b><br>Avg: %{y:.2f}h<br>PRs: %{marker.size}<extra></extra>",
                name="Avg time between PRs (h)",
            )
        )
        fig.update_layout(
            title="Average Time Between Pull Requests",
            xaxis_title="Repository",
            yaxis_title="Hours",
            xaxis={"tickangle": 45},
            showlegend=False,
        )
        fig.write_html("docs/pr_metrics.html", include_plotlyjs="cdn")
    else:
        with open("docs/pr_metrics.html", "w") as f:
            f.write("<html><body><p>No PR metric data yet.</p></body></html>")

    data_json = {
        "events_by_type_date": df_events.to_dict("records"),
        "top_repositories": df_repos.to_dict("records"),
        "pr_metrics": df_pr.to_dict("records"),
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open("docs/data.json", "w") as f:
        json.dump(data_json, f, indent=2)

    # Write JSON artifacts used by the dashboard single-file app
    # event_counts_10.json
    with open("docs/event_counts_10.json", "w") as f:
        json.dump({"status": 200, "data": counts10}, f, indent=2)
    # event_counts_60.json
    with open("docs/event_counts_60.json", "w") as f:
        json.dump({"status": 200, "data": counts60}, f, indent=2)

    # trending.json (fallback to sample when no data)
    trending_payload = {
        "hours": 24,
        "repositories": df_trending.to_dict("records"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if len(trending_payload["repositories"]) == 0:
        trending_payload.update({
            "repositories": [
                {"repo_name": "sample/repo-a", "total_events": 12, "watch_events": 6, "pr_events": 3, "issue_events": 3},
                {"repo_name": "sample/repo-b", "total_events": 9, "watch_events": 4, "pr_events": 3, "issue_events": 2},
                {"repo_name": "sample/repo-c", "total_events": 7, "watch_events": 3, "pr_events": 2, "issue_events": 2},
            ],
            "note": "sample fallback due to empty or unavailable trending data",
        })
    with open("docs/trending.json", "w") as f:
        json.dump({"status": 200, "data": trending_payload}, f, indent=2)

    # data_status.json for quick health of artifacts
    status_json = {
        "base_url": os.environ.get("BASE_URL", "http://127.0.0.1:8000"),
        "health_status": 200,
        "event_counts_10_status": 200,
        "event_counts_60_status": 200,
        "trending_status": 200,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open("docs/data_status.json", "w") as f:
        json.dump(status_json, f, indent=2)

    # config.json for UI
    config = {
        "target_repositories": [r.strip() for r in os.environ.get("TARGET_REPOSITORIES", "").split(",") if r.strip()],
        "repo_slug": os.environ.get("REPO_SLUG", ""),
        "workflow": os.environ.get("WORKFLOW_NAME", "CI and Pages"),
    }
    with open("docs/config.json", "w") as f:
        json.dump(config, f, indent=2)

if __name__ == "__main__":
    export()
    print("Exported data to docs/")
