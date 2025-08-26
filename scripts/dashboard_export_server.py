from fastmcp import FastMCP
from typing import Literal

mcp = FastMCP(name="GitHubEventsExport")

@mcp.tool(name="export_dashboard_html", description="Generate a self-contained dashboard HTML from REST metrics and save to docs/index.html")
def export_dashboard_html(
    base_url: str = "http://localhost:8000",
    hours: int = 24,
    limit: int = 5,
    output_path: str = "docs/index.html",
    include_plotlyjs: Literal["cdn","inline"] = "cdn",
) -> str:
    """
    Build a static HTML dashboard using metrics from the REST API and write it to docs/index.html.
    Returns the output path.
    """
    from src.github_events_monitor.dashboard_html import generate_dashboard_html
    return generate_dashboard_html(
        base_url=base_url,
        hours=hours,
        limit=limit,
        output_path=output_path,
        include_plotlyjs=include_plotlyjs,
    )

if __name__ == "__main__":
    mcp.run()
