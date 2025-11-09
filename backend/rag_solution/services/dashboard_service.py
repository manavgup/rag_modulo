"""
Dashboard service module for providing analytics and recent activity data.

This module provides the DashboardService class which handles all operations
related to dashboard statistics and recent activity tracking.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.models.collection import Collection
from rag_solution.models.conversation import ConversationMessage, ConversationSession
from rag_solution.models.file import File
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.schemas.dashboard_schema import (
    ActivityStatus,
    ActivityType,
    DashboardStats,
    QuickStat,
    QuickStatistics,
    RecentActivity,
    SystemHealth,
    SystemHealthStatus,
    TrendData,
)

logger = get_logger(__name__)


class DashboardService:
    """Service for managing dashboard data including statistics and recent activity."""

    def __init__(self, db: Session) -> None:
        """Initialize the dashboard service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_dashboard_stats(self) -> DashboardStats:
        """Get comprehensive dashboard statistics.

        Returns:
            DashboardStats: Current system statistics
        """
        try:
            # Get total documents count
            total_documents = self.db.query(func.count(File.id)).scalar() or 0

            # Get total searches/conversations count
            total_searches = self.db.query(func.count(ConversationSession.id)).scalar() or 0

            # Count active pipelines as "active agents"
            active_agents = self.db.query(func.count(PipelineConfig.id)).scalar() or 0

            # Count archived conversations as completed workflows
            completed_workflows = (
                self.db.query(func.count(ConversationSession.id)).filter(ConversationSession.is_archived).scalar() or 0
            )

            # Calculate success rate (conversations with messages vs total)
            conversations_with_messages = (
                self.db.query(func.count(func.distinct(ConversationMessage.conversation_id))).scalar() or 0
            )

            success_rate = conversations_with_messages / total_searches if total_searches > 0 else 1.0

            # Calculate average response time (mock calculation)
            # In a real implementation, you'd track actual response times
            average_response_time = 1.5  # Mock value in seconds

            # Calculate trends (comparing current vs previous periods)
            trends = self._calculate_trends()

            return DashboardStats(
                total_documents=total_documents,
                total_searches=total_searches,
                active_agents=active_agents,
                completed_workflows=completed_workflows,
                success_rate=min(success_rate, 1.0),  # Cap at 1.0
                average_response_time=average_response_time,
                documents_trend=trends["documents"],
                searches_trend=trends["searches"],
                success_rate_trend=trends["success_rate"],
                response_time_trend=trends["response_time"],
                workflows_trend=trends["workflows"],
            )

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error getting dashboard stats: %s", str(e))
            # Return default stats on error
            default_trends = self._get_default_trends()
            return DashboardStats(
                total_documents=0,
                total_searches=0,
                active_agents=0,
                completed_workflows=0,
                success_rate=0.0,
                average_response_time=0.0,
                documents_trend=default_trends["documents"],
                searches_trend=default_trends["searches"],
                success_rate_trend=default_trends["success_rate"],
                response_time_trend=default_trends["response_time"],
                workflows_trend=default_trends["workflows"],
            )

    def get_recent_activity(self, limit: int = 10) -> list[RecentActivity]:
        """Get recent system activity.

        Args:
            limit: Maximum number of activities to return

        Returns:
            list[RecentActivity]: List of recent activities
        """
        try:
            activities = []
            cutoff_time = datetime.now(UTC) - timedelta(hours=24)

            # Recent document uploads
            recent_files = (
                self.db.query(File)
                .filter(File.created_at >= cutoff_time)
                .order_by(File.created_at.desc())
                .limit(limit // 4)
                .all()
            )

            for file in recent_files:
                activities.append(
                    RecentActivity(
                        id=f"file_{file.id}",
                        type=ActivityType.DOCUMENT,
                        title="Document Upload",
                        description=f"Document '{file.filename}' uploaded to collection",
                        timestamp=file.created_at,
                        status=ActivityStatus.SUCCESS,
                    )
                )

            # Recent collections
            recent_collections = (
                self.db.query(Collection)
                .filter(Collection.created_at >= cutoff_time)
                .order_by(Collection.created_at.desc())
                .limit(limit // 4)
                .all()
            )

            for collection in recent_collections:
                activities.append(
                    RecentActivity(
                        id=f"collection_{collection.id}",
                        type=ActivityType.WORKFLOW,
                        title="Collection Created",
                        description=f"New collection '{collection.name}' created",
                        timestamp=collection.created_at,
                        status=ActivityStatus.SUCCESS,
                    )
                )

            # Recent conversations/searches
            recent_conversations = (
                self.db.query(ConversationSession)
                .filter(ConversationSession.created_at >= cutoff_time)
                .order_by(ConversationSession.created_at.desc())
                .limit(limit // 2)
                .all()
            )

            for conv in recent_conversations:
                status: ActivityStatus = ActivityStatus.SUCCESS if conv.is_archived else ActivityStatus.RUNNING
                activities.append(
                    RecentActivity(
                        id=f"search_{conv.id}",
                        type=ActivityType.SEARCH,
                        title="Document Search",
                        description="Search session started in collection",
                        timestamp=conv.created_at,
                        status=status,
                    )
                )

            # Sort all activities by timestamp (most recent first)
            activities.sort(key=lambda x: x.timestamp, reverse=True)

            # Return limited results
            return activities[:limit]

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error getting recent activity: %s", str(e))
            # Return mock data on error
            return [
                RecentActivity(
                    id="mock_1",
                    type=ActivityType.SEARCH,
                    title="System Activity",
                    description="Recent system activity",
                    timestamp=datetime.now(UTC),
                    status=ActivityStatus.SUCCESS,
                )
            ]

    def _calculate_trends(self) -> dict[str, TrendData]:  # pylint: disable=too-many-locals
        """Calculate trend data for dashboard metrics.

        Returns:
            dict[str, TrendData]: Dictionary of trend data for each metric
        """
        try:
            now = datetime.now(UTC)

            # Calculate documents trend (this month vs last month)
            current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

            current_documents = (
                self.db.query(func.count(File.id)).filter(File.created_at >= current_month_start).scalar() or 0
            )

            last_month_documents = (
                self.db.query(func.count(File.id))
                .filter(File.created_at >= last_month_start, File.created_at < current_month_start)
                .scalar()
                or 0
            )

            documents_change = self._calculate_percentage_change(current_documents, last_month_documents)

            # Calculate searches trend (this week vs last week)
            current_week_start = now - timedelta(days=now.weekday())
            current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            last_week_start = current_week_start - timedelta(days=7)

            current_searches = (
                self.db.query(func.count(ConversationSession.id))
                .filter(ConversationSession.created_at >= current_week_start)
                .scalar()
                or 0
            )

            last_week_searches = (
                self.db.query(func.count(ConversationSession.id))
                .filter(
                    ConversationSession.created_at >= last_week_start,
                    ConversationSession.created_at < current_week_start,
                )
                .scalar()
                or 0
            )

            searches_change = self._calculate_percentage_change(current_searches, last_week_searches)

            # Calculate success rate trend (this week vs last week)
            current_success_rate = self._calculate_success_rate(current_week_start, now)
            last_success_rate = self._calculate_success_rate(last_week_start, current_week_start)
            success_rate_change = self._calculate_percentage_change(current_success_rate, last_success_rate)

            # Calculate response time trend (mock data for now)
            response_time_change = -15.0  # Mock: 15% faster

            # Calculate workflows trend (this week vs last week)
            current_workflows = (
                self.db.query(func.count(ConversationSession.id))
                .filter(ConversationSession.created_at >= current_week_start, ConversationSession.is_archived)
                .scalar()
                or 0
            )

            last_week_workflows = (
                self.db.query(func.count(ConversationSession.id))
                .filter(
                    ConversationSession.created_at >= last_week_start,
                    ConversationSession.created_at < current_week_start,
                    ConversationSession.is_archived,
                )
                .scalar()
                or 0
            )

            workflows_change = self._calculate_percentage_change(current_workflows, last_week_workflows)

            return {
                "documents": TrendData(
                    value=abs(documents_change),
                    period="this month",
                    direction="up" if documents_change >= 0 else "down",
                ),
                "searches": TrendData(
                    value=abs(searches_change), period="this week", direction="up" if searches_change >= 0 else "down"
                ),
                "success_rate": TrendData(
                    value=abs(success_rate_change),
                    period="improvement",
                    direction="up" if success_rate_change >= 0 else "down",
                ),
                "response_time": TrendData(
                    value=abs(response_time_change),
                    period="faster",
                    direction="down",  # Faster is better, so down is positive
                ),
                "workflows": TrendData(
                    value=abs(workflows_change), period="this week", direction="up" if workflows_change >= 0 else "down"
                ),
            }

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error calculating trends: %s", str(e))
            return self._get_default_trends()

    def _calculate_percentage_change(self, current: float, previous: float) -> float:
        """Calculate percentage change between current and previous values.

        Args:
            current: Current value
            previous: Previous value

        Returns:
            float: Percentage change
        """
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100.0

    def _calculate_success_rate(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate success rate for a given time period.

        Args:
            start_time: Start of the period
            end_time: End of the period

        Returns:
            float: Success rate (0.0 to 1.0)
        """
        try:
            total_conversations = (
                self.db.query(func.count(ConversationSession.id))
                .filter(ConversationSession.created_at >= start_time, ConversationSession.created_at < end_time)
                .scalar()
                or 0
            )

            conversations_with_messages = (
                self.db.query(func.count(func.distinct(ConversationMessage.conversation_id)))
                .join(ConversationSession, ConversationMessage.conversation_id == ConversationSession.id)
                .filter(ConversationSession.created_at >= start_time, ConversationSession.created_at < end_time)
                .scalar()
                or 0
            )

            return conversations_with_messages / total_conversations if total_conversations > 0 else 1.0

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error calculating success rate: %s", str(e))
            return 1.0

    def _get_default_trends(self) -> dict[str, TrendData]:
        """Get default trend data for error cases.

        Returns:
            dict[str, TrendData]: Default trend data
        """
        return {
            "documents": TrendData(value=12.0, period="this month", direction="up"),
            "searches": TrendData(value=8.0, period="this week", direction="up"),
            "success_rate": TrendData(value=2.1, period="improvement", direction="up"),
            "response_time": TrendData(value=15.0, period="faster", direction="down"),
            "workflows": TrendData(value=5.0, period="this week", direction="up"),
        }

    def get_quick_statistics(self) -> QuickStatistics:
        """Get quick statistics for the dashboard.

        Returns:
            QuickStatistics: Quick statistics data
        """
        try:
            now = datetime.now(UTC)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Documents processed today
            documents_today = self.db.query(func.count(File.id)).filter(File.created_at >= today_start).scalar() or 0

            # Search queries (total)
            total_queries = self.db.query(func.count(ConversationSession.id)).scalar() or 0

            # Agent tasks completed (archived conversations)
            tasks_completed = (
                self.db.query(func.count(ConversationSession.id)).filter(ConversationSession.is_archived).scalar() or 0
            )

            # Average processing time (mock)
            avg_processing_time = 2.3

            # Error rate (mock calculation)
            error_rate = 0.2

            return QuickStatistics(
                documents_processed_today=QuickStat(
                    metric="Documents Processed Today", value=str(documents_today), change="+12%", trend="up"
                ),
                search_queries=QuickStat(metric="Search Queries", value=f"{total_queries:,}", change="+8%", trend="up"),
                agent_tasks_completed=QuickStat(
                    metric="Agent Tasks Completed", value=str(tasks_completed), change="+15%", trend="up"
                ),
                average_processing_time=QuickStat(
                    metric="Average Processing Time", value=f"{avg_processing_time}s", change="-5%", trend="down"
                ),
                error_rate=QuickStat(metric="Error Rate", value=f"{error_rate}%", change="-0.1%", trend="down"),
            )

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error getting quick statistics: %s", str(e))
            # Return default quick statistics
            return QuickStatistics(
                documents_processed_today=QuickStat(
                    metric="Documents Processed Today", value="0", change="+0%", trend="up"
                ),
                search_queries=QuickStat(metric="Search Queries", value="0", change="+0%", trend="up"),
                agent_tasks_completed=QuickStat(metric="Agent Tasks Completed", value="0", change="+0%", trend="up"),
                average_processing_time=QuickStat(
                    metric="Average Processing Time", value="0.0s", change="+0%", trend="up"
                ),
                error_rate=QuickStat(metric="Error Rate", value="0.0%", change="+0%", trend="up"),
            )

    def get_system_health(self) -> SystemHealthStatus:
        """Get system health status.

        Returns:
            SystemHealthStatus: System health data
        """
        try:
            # Mock system health data - in a real implementation,
            # you'd check actual system metrics
            components = [
                SystemHealth(component="API Health", health_percentage=100),
                SystemHealth(component="Database", health_percentage=95),
                SystemHealth(component="Storage", health_percentage=78),
                SystemHealth(component="Memory", health_percentage=65),
            ]

            # Calculate overall status based on component health
            avg_health = sum(comp.health_percentage for comp in components) / len(components)
            overall_status = "All Systems Operational" if avg_health >= 90 else "Degraded Performance"

            return SystemHealthStatus(overall_status=overall_status, components=components)

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Error getting system health: %s", str(e))
            return SystemHealthStatus(
                overall_status="Unknown",
                components=[
                    SystemHealth(component="API Health", health_percentage=0),
                    SystemHealth(component="Database", health_percentage=0),
                    SystemHealth(component="Storage", health_percentage=0),
                    SystemHealth(component="Memory", health_percentage=0),
                ],
            )
