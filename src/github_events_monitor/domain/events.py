from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class GitHubEvent:
    id: str
    event_type: str
    created_at: datetime
    repo_name: Optional[str]
    actor_login: Optional[str]
    payload: Dict[str, Any]
