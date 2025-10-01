"""Dashboard schema definitions for API responses."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ActivityType(str, Enum):
    """Activity type enumeration."""

    SEARCH = "search"
    WORKFLOW = "workflow"
    AGENT = "agent"
    DOCUMENT = "document"


class ActivityStatus(str, Enum):
    """Activity status enumeration."""

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    RUNNING = "running"


class TrendData(BaseModel):
    """Trend data for dashboard metrics."""

    value: float = Field(..., description="Percentage change value")
    period: str = Field(..., description="Time period for the trend (e.g., 'this month', 'this week')")
    direction: str = Field(..., description="Direction of change ('up', 'down')")


class DashboardStats(BaseModel):
    """Dashboard statistics schema."""

    total_documents: int = Field(..., description="Total number of documents in the system")
    total_searches: int = Field(..., description="Total number of searches performed")
    active_agents: int = Field(..., description="Number of currently active agents")
    completed_workflows: int = Field(..., description="Number of completed workflows")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate of operations")
    average_response_time: float = Field(..., ge=0.0, description="Average response time in seconds")

    # Trend data
    documents_trend: TrendData = Field(..., description="Documents trend data")
    searches_trend: TrendData = Field(..., description="Searches trend data")
    success_rate_trend: TrendData = Field(..., description="Success rate trend data")
    response_time_trend: TrendData = Field(..., description="Response time trend data")
    workflows_trend: TrendData = Field(..., description="Workflows trend data")

    model_config = ConfigDict(from_attributes=True)


class RecentActivity(BaseModel):
    """Recent activity item schema."""

    id: str = Field(..., description="Unique activity identifier")
    type: ActivityType = Field(..., description="Activity type")
    title: str = Field(..., description="Activity title")
    description: str = Field(..., description="Activity description")
    timestamp: datetime = Field(..., description="Activity timestamp")
    status: ActivityStatus = Field(..., description="Activity status")

    model_config = ConfigDict(from_attributes=True)


class QuickStat(BaseModel):
    """Quick statistics item schema."""

    metric: str = Field(..., description="Metric name")
    value: str = Field(..., description="Current value")
    change: str = Field(..., description="Change percentage")
    trend: str = Field(..., description="Trend direction ('up', 'down')")


class SystemHealth(BaseModel):
    """System health component schema."""

    component: str = Field(..., description="System component name")
    health_percentage: int = Field(..., ge=0, le=100, description="Health percentage")


class QuickStatistics(BaseModel):
    """Quick statistics schema."""

    documents_processed_today: QuickStat = Field(..., description="Documents processed today")
    search_queries: QuickStat = Field(..., description="Search queries count")
    agent_tasks_completed: QuickStat = Field(..., description="Agent tasks completed")
    average_processing_time: QuickStat = Field(..., description="Average processing time")
    error_rate: QuickStat = Field(..., description="Error rate")


class SystemHealthStatus(BaseModel):
    """System health status schema."""

    overall_status: str = Field(..., description="Overall system status")
    components: list[SystemHealth] = Field(..., description="Individual component health")


class DashboardOutput(BaseModel):
    """Dashboard combined output schema."""

    stats: DashboardStats
    recent_activity: list[RecentActivity]
    quick_statistics: QuickStatistics
    system_health: SystemHealthStatus

    model_config = ConfigDict(from_attributes=True)
