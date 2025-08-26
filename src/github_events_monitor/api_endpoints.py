"""
Deprecated: Endpoint classes are now defined in `api.py`. This module re-exports
them to avoid breaking imports in downstream code and tests.
"""

from .api import (
    ApiEndpoint,
    HealthEndpoint,
    CollectEndpoint,
    WebhookEndpoint,
    MetricsEventCountsEndpoint,
    MetricsPrIntervalEndpoint,
    MetricsRepositoryActivityEndpoint,
    MetricsTrendingEndpoint,
    VisualizationTrendingChartEndpoint,
    VisualizationPrTimelineEndpoint,
    McpCapabilitiesEndpoint,
    McpToolsEndpoint,
    McpResourcesEndpoint,
    McpPromptsEndpoint,
)

__all__ = [
    "ApiEndpoint",
    "HealthEndpoint",
    "CollectEndpoint",
    "WebhookEndpoint",
    "MetricsEventCountsEndpoint",
    "MetricsPrIntervalEndpoint",
    "MetricsRepositoryActivityEndpoint",
    "MetricsTrendingEndpoint",
    "VisualizationTrendingChartEndpoint",
    "VisualizationPrTimelineEndpoint",
    "McpCapabilitiesEndpoint",
    "McpToolsEndpoint",
    "McpResourcesEndpoint",
    "McpPromptsEndpoint",
]
