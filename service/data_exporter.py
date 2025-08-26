import sqlite3
import json
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timezone

DB_PATH = "database/events.db"

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

if __name__ == "__main__":
    export()
    print("Exported data to docs/")
