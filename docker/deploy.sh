#!/usr/bin/env bash
set -euo pipefail

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

if [ ! -f database/events.db ]; then
  sqlite3 database/events.db < database/schema.sql
fi

python service/data_exporter.py

SERVICE_FILE="/etc/systemd/system/github-events.service"
sudo tee "$SERVICE_FILE" >/dev/null <<SYS
[Unit]
Description=GitHub Events Monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
Environment=PYTHONUNBUFFERED=1
ExecStart=$(pwd)/venv/bin/python service/github_monitor.py
Restart=always
RestartSec=10
User=$USER

[Install]
WantedBy=multi-user.target
SYS

sudo systemctl daemon-reload
sudo systemctl enable github-events
sudo systemctl restart github-events

echo "Service started. To view logs: journalctl -u github-events -f"
