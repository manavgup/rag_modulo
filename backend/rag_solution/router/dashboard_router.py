"""Dashboard router for API endpoints related to dashboard statistics and recent activity."""

from core.logging_utils import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.dashboard_schema import (
    DashboardStats,
    QuickStatistics,
    RecentActivity,
    SystemHealthStatus,
)
from rag_solution.services.dashboard_service import DashboardService

logger = get_logger("router.dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)) -> DashboardStats:
    """
    Get comprehensive dashboard statistics.

    Returns:
        DashboardStats: Current system statistics including document counts,
                       search counts, active agents, and success rates.
    """
    try:
        dashboard_service = DashboardService(db)
        stats = dashboard_service.get_dashboard_stats()
        logger.info("Dashboard stats retrieved successfully")
        return stats

    except Exception as e:
        logger.error("Error retrieving dashboard stats: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard statistics") from e


@router.get("/activity", response_model=list[RecentActivity])
async def get_recent_activity(limit: int = 10, db: Session = Depends(get_db)) -> list[RecentActivity]:
    """
    Get recent system activity.

    Args:
        limit: Maximum number of activities to return (default: 10)

    Returns:
        list[RecentActivity]: List of recent activities including searches,
                              document uploads, and workflow completions.
    """
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

        dashboard_service = DashboardService(db)
        activities = dashboard_service.get_recent_activity(limit=limit)
        logger.info("Retrieved {len(activities)} recent activities")
        return activities

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving recent activity: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve recent activity") from e


@router.get("/quick-stats", response_model=QuickStatistics)
async def get_quick_statistics(db: Session = Depends(get_db)) -> QuickStatistics:
    """
    Get quick statistics for the dashboard.

    Returns:
        QuickStatistics: Quick statistics including daily metrics and performance data.
    """
    try:
        dashboard_service = DashboardService(db)
        quick_stats = dashboard_service.get_quick_statistics()
        logger.info("Quick statistics retrieved successfully")
        return quick_stats

    except Exception as e:
        logger.error("Error retrieving quick statistics: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve quick statistics") from e


@router.get("/system-health", response_model=SystemHealthStatus)
async def get_system_health(db: Session = Depends(get_db)) -> SystemHealthStatus:
    """
    Get system health status.

    Returns:
        SystemHealthStatus: System health data including component health percentages.
    """
    try:
        dashboard_service = DashboardService(db)
        system_health = dashboard_service.get_system_health()
        logger.info("System health retrieved successfully")
        return system_health

    except Exception as e:
        logger.error("Error retrieving system health: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve system health") from e
