import plotly.graph_objects as go
import plotly.io as pio

# Create figure
fig = go.Figure()

# Define system positions and properties
systems = {
    "GitHub Events MCP Server": {"x": 5, "y": 5, "color": "#1FB8CD", "type": "central"},
    "GitHub Events API": {"x": 1, "y": 8, "color": "#808080", "type": "external"},
    "MCP Client Apps": {"x": 9, "y": 8, "color": "#5D878F", "type": "client"},
    "PostgreSQL Database": {"x": 9, "y": 2, "color": "#2E8B57", "type": "database"},
    "End Users": {"x": 12, "y": 8, "color": "#D2BA4C", "type": "user"}
}

# Add system boxes as rectangles
for name, props in systems.items():
    # Abbreviate long names for display
    display_name = name
    if name == "GitHub Events MCP Server":
        display_name = "GitHub Events<br>MCP Server"
    elif name == "GitHub Events API":
        display_name = "GitHub Events<br>API"
    elif name == "MCP Client Apps":
        display_name = "MCP Client<br>Apps"
    elif name == "PostgreSQL Database":
        display_name = "PostgreSQL<br>Database"
    
    # Add rectangle shape
    fig.add_shape(
        type="rect",
        x0=props["x"]-1.2, y0=props["y"]-0.8,
        x1=props["x"]+1.2, y1=props["y"]+0.8,
        fillcolor=props["color"],
        line=dict(color="white", width=2),
        opacity=0.8
    )
    
    # Add text annotation
    fig.add_annotation(
        x=props["x"], y=props["y"],
        text=f"<b>{display_name}</b>",
        showarrow=False,
        font=dict(color="white", size=12),
        align="center"
    )

# Define connections with abbreviated labels
connections = [
    {"from": "GitHub Events API", "to": "GitHub Events MCP Server", "label": "HTTPS Polling"},
    {"from": "MCP Client Apps", "to": "GitHub Events MCP Server", "label": "JSON-RPC/MCP"},
    {"from": "GitHub Events MCP Server", "to": "PostgreSQL Database", "label": "SQL Queries"},
    {"from": "End Users", "to": "MCP Client Apps", "label": "User Interface"}
]

# Add connection arrows
for conn in connections:
    from_sys = systems[conn["from"]]
    to_sys = systems[conn["to"]]
    
    # Calculate arrow positions
    from_x, from_y = from_sys["x"], from_sys["y"]
    to_x, to_y = to_sys["x"], to_sys["y"]
    
    # Adjust start/end points to box edges
    if from_x < to_x:
        from_x += 1.2
        to_x -= 1.2
    else:
        from_x -= 1.2
        to_x += 1.2
        
    if from_y < to_y:
        from_y += 0.8
        to_y -= 0.8
    elif from_y > to_y:
        from_y -= 0.8
        to_y += 0.8
    
    # Add arrow
    fig.add_annotation(
        x=to_x, y=to_y,
        ax=from_x, ay=from_y,
        xref="x", yref="y",
        axref="x", ayref="y",
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor="#333333",
        showarrow=True
    )
    
    # Add connection label
    mid_x = (from_x + to_x) / 2
    mid_y = (from_y + to_y) / 2
    
    # Abbreviate labels to fit 15 char limit
    label = conn["label"]
    if label == "JSON-RPC/MCP":
        label = "JSON-RPC/MCP"
    elif label == "User Interface":
        label = "UI"
    
    fig.add_annotation(
        x=mid_x, y=mid_y + 0.3,
        text=f"<i>{label}</i>",
        showarrow=False,
        font=dict(color="#666666", size=10),
        bgcolor="white",
        bordercolor="#cccccc",
        borderwidth=1
    )

# Configure layout
fig.update_layout(
    title="GitHub Events MCP System Context",
    showlegend=False,
    xaxis=dict(
        range=[-1, 14],
        showgrid=False,
        showticklabels=False,
        zeroline=False
    ),
    yaxis=dict(
        range=[0, 10],
        showgrid=False,
        showticklabels=False,
        zeroline=False
    ),
    plot_bgcolor="white",
    paper_bgcolor="white"
)

# Remove axes
fig.update_xaxes(visible=False)
fig.update_yaxes(visible=False)

# Save the chart
fig.write_image("github_events_mcp_context_diagram.png")