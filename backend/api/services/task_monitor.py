"""
Celery Task Monitoring Service.

Provides comprehensive monitoring and management of Celery tasks.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from celery.result import AsyncResult
from celery import Celery

from backend.db.models import TaskExecution, User
from backend.api.schemas.tasks import (
    TaskExecutionResponse,
    TaskExecutionListResponse,
    TaskStatsResponse,
    TaskProgressInfo,
    CeleryWorkerInfo,
    CeleryQueueInfo,
    CeleryHealthResponse,
    TaskDispatchResponse,
    TaskCancelResponse,
    TaskRetryResponse,
)

logger = logging.getLogger(__name__)


class CeleryTaskMonitor:
    """
    Service for monitoring and managing Celery tasks.

    Provides:
    - Task execution tracking and persistence
    - Real-time task status queries
    - Task statistics and analytics
    - Worker and queue health monitoring
    - Task dispatch, cancel, and retry operations
    """

    def __init__(self, celery_app: Celery):
        """Initialize task monitor with Celery app instance."""
        self.celery_app = celery_app

    async def track_task(
        self,
        db: AsyncSession,
        task_id: str,
        task_name: str,
        task_type: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskExecution:
        """
        Create a task execution record for tracking.

        Args:
            db: Database session
            task_id: Celery task ID
            task_name: Task function name
            task_type: Task category (embedding, ingestion, maintenance)
            args: Task positional arguments
            kwargs: Task keyword arguments
            user_id: User who triggered the task
            metadata: Additional task metadata

        Returns:
            Created TaskExecution instance
        """
        task_exec = TaskExecution(
            task_id=task_id,
            task_name=task_name,
            task_type=task_type,
            args=args,
            kwargs=kwargs,
            user_id=user_id,
            metadata=metadata or {},
            status="PENDING",
        )

        db.add(task_exec)
        await db.commit()
        await db.refresh(task_exec)

        logger.info(f"Created task tracking record: {task_id} ({task_name})")
        return task_exec

    async def update_task_status(
        self,
        db: AsyncSession,
        task_id: str,
        status: str,
        progress_percent: Optional[int] = None,
        progress_current: Optional[int] = None,
        progress_total: Optional[int] = None,
        progress_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        traceback: Optional[str] = None,
        worker_name: Optional[str] = None,
    ) -> Optional[TaskExecution]:
        """
        Update task execution status.

        Args:
            db: Database session
            task_id: Celery task ID
            status: New status
            progress_percent: Progress percentage (0-100)
            progress_current: Current item being processed
            progress_total: Total items to process
            progress_message: Human-readable progress message
            result: Task result data
            error: Error message if failed
            traceback: Error traceback
            worker_name: Worker executing the task

        Returns:
            Updated TaskExecution instance or None if not found
        """
        stmt = select(TaskExecution).where(TaskExecution.task_id == task_id)
        result_obj = await db.execute(stmt)
        task_exec = result_obj.scalar_one_or_none()

        if not task_exec:
            logger.warning(f"Task execution not found for task_id: {task_id}")
            return None

        # Update status
        task_exec.status = status

        # Update progress
        if progress_percent is not None:
            task_exec.progress_percent = progress_percent
        if progress_current is not None:
            task_exec.progress_current = progress_current
        if progress_total is not None:
            task_exec.progress_total = progress_total
        if progress_message is not None:
            task_exec.progress_message = progress_message

        # Update timing
        now = datetime.utcnow()
        if status == "STARTED" and not task_exec.started_at:
            task_exec.started_at = now
        if status in ("SUCCESS", "FAILURE", "REVOKED") and not task_exec.completed_at:
            task_exec.completed_at = now

        # Update results/errors
        if result is not None:
            task_exec.result = result
        if error is not None:
            task_exec.error = error
        if traceback is not None:
            task_exec.traceback = traceback

        # Update worker info
        if worker_name is not None:
            task_exec.worker_name = worker_name

        await db.commit()
        await db.refresh(task_exec)

        logger.info(f"Updated task {task_id} status to {status}")
        return task_exec

    async def get_task(
        self,
        db: AsyncSession,
        task_id: str,
        include_celery_state: bool = True,
    ) -> Optional[TaskExecutionResponse]:
        """
        Get task execution details.

        Args:
            db: Database session
            task_id: Celery task ID
            include_celery_state: Whether to fetch live state from Celery

        Returns:
            TaskExecutionResponse or None if not found
        """
        stmt = select(TaskExecution).where(TaskExecution.task_id == task_id)
        result = await db.execute(stmt)
        task_exec = result.scalar_one_or_none()

        if not task_exec:
            # If not in DB but include_celery_state, try fetching from Celery
            if include_celery_state:
                async_result = AsyncResult(task_id, app=self.celery_app)
                if async_result.state != "PENDING" or async_result.result is not None:
                    # Create minimal response from Celery state
                    return self._celery_result_to_response(task_id, async_result)
            return None

        return self._task_exec_to_response(task_exec)

    async def list_tasks(
        self,
        db: AsyncSession,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> TaskExecutionListResponse:
        """
        List task executions with filtering and pagination.

        Args:
            db: Database session
            task_type: Filter by task type
            status: Filter by status
            user_id: Filter by user
            from_date: Filter tasks created after this date
            to_date: Filter tasks created before this date
            page: Page number (1-indexed)
            page_size: Number of tasks per page

        Returns:
            Paginated list of task executions
        """
        # Build filters
        filters = []
        if task_type:
            filters.append(TaskExecution.task_type == task_type)
        if status:
            filters.append(TaskExecution.status == status)
        if user_id:
            filters.append(TaskExecution.user_id == user_id)
        if from_date:
            filters.append(TaskExecution.created_at >= from_date)
        if to_date:
            filters.append(TaskExecution.created_at <= to_date)

        # Count total
        count_stmt = select(func.count(TaskExecution.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch page
        stmt = select(TaskExecution)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(TaskExecution.created_at.desc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        result = await db.execute(stmt)
        task_execs = result.scalars().all()

        tasks = [self._task_exec_to_response(task_exec) for task_exec in task_execs]

        return TaskExecutionListResponse(
            tasks=tasks,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    async def get_task_stats(
        self,
        db: AsyncSession,
        task_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
    ) -> TaskStatsResponse:
        """
        Get aggregated task statistics.

        Args:
            db: Database session
            task_type: Filter by task type
            from_date: Only include tasks created after this date

        Returns:
            Aggregated task statistics
        """
        filters = []
        if task_type:
            filters.append(TaskExecution.task_type == task_type)
        if from_date:
            filters.append(TaskExecution.created_at >= from_date)

        base_query = select(TaskExecution)
        if filters:
            base_query = base_query.where(and_(*filters))

        # Count by status
        status_counts = {}
        for status_val in [
            "PENDING",
            "STARTED",
            "PROGRESS",
            "SUCCESS",
            "FAILURE",
            "REVOKED",
            "RETRY",
        ]:
            stmt = select(func.count(TaskExecution.id)).where(TaskExecution.status == status_val)
            if filters:
                stmt = stmt.where(and_(*filters))
            result = await db.execute(stmt)
            status_counts[status_val.lower()] = result.scalar_one()

        # Count by type
        type_stmt = select(TaskExecution.task_type, func.count(TaskExecution.id)).group_by(
            TaskExecution.task_type
        )
        if filters:
            type_stmt = type_stmt.where(and_(*filters))
        type_result = await db.execute(type_stmt)
        by_type = {row[0]: row[1] for row in type_result}

        # Calculate durations
        duration_stmt = select(
            func.avg(func.extract("epoch", TaskExecution.completed_at - TaskExecution.started_at)),
            func.sum(func.extract("epoch", TaskExecution.completed_at - TaskExecution.started_at)),
        ).where(
            and_(
                TaskExecution.started_at.isnot(None),
                TaskExecution.completed_at.isnot(None),
            )
        )
        if filters:
            duration_stmt = duration_stmt.where(and_(*filters))
        duration_result = await db.execute(duration_stmt)
        avg_duration, total_duration = duration_result.one()

        # Count recent tasks
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        one_week_ago = now - timedelta(weeks=1)

        tasks_last_hour_stmt = select(func.count(TaskExecution.id)).where(
            TaskExecution.created_at >= one_hour_ago
        )
        if filters:
            tasks_last_hour_stmt = tasks_last_hour_stmt.where(and_(*filters))
        tasks_last_hour_result = await db.execute(tasks_last_hour_stmt)
        tasks_last_hour = tasks_last_hour_result.scalar_one()

        tasks_last_24h_stmt = select(func.count(TaskExecution.id)).where(
            TaskExecution.created_at >= one_day_ago
        )
        if filters:
            tasks_last_24h_stmt = tasks_last_24h_stmt.where(and_(*filters))
        tasks_last_24h_result = await db.execute(tasks_last_24h_stmt)
        tasks_last_24h = tasks_last_24h_result.scalar_one()

        tasks_last_week_stmt = select(func.count(TaskExecution.id)).where(
            TaskExecution.created_at >= one_week_ago
        )
        if filters:
            tasks_last_week_stmt = tasks_last_week_stmt.where(and_(*filters))
        tasks_last_week_result = await db.execute(tasks_last_week_stmt)
        tasks_last_week = tasks_last_week_result.scalar_one()

        total_tasks = sum(status_counts.values())

        return TaskStatsResponse(
            total_tasks=total_tasks,
            pending=status_counts.get("pending", 0),
            started=status_counts.get("started", 0),
            in_progress=status_counts.get("progress", 0),
            success=status_counts.get("success", 0),
            failure=status_counts.get("failure", 0),
            revoked=status_counts.get("revoked", 0),
            retry=status_counts.get("retry", 0),
            by_type=by_type,
            avg_duration_seconds=float(avg_duration) if avg_duration else None,
            total_duration_seconds=float(total_duration) if total_duration else None,
            tasks_last_hour=tasks_last_hour,
            tasks_last_24h=tasks_last_24h,
            tasks_last_week=tasks_last_week,
        )

    async def get_celery_health(self) -> CeleryHealthResponse:
        """
        Get Celery infrastructure health status.

        Returns:
            Health status of workers, queues, and broker
        """
        issues = []
        workers = []
        queues = []

        # Check broker connection
        try:
            inspect = self.celery_app.control.inspect()
            broker_connected = True
        except Exception as e:
            logger.error(f"Failed to connect to Celery broker: {e}")
            broker_connected = False
            issues.append(f"Broker connection failed: {str(e)}")

        # Get worker stats
        if broker_connected:
            try:
                stats = inspect.stats()
                active_tasks = inspect.active()
                reserved_tasks = inspect.reserved()

                if stats:
                    for worker_name, worker_stats in stats.items():
                        active_count = len(active_tasks.get(worker_name, [])) if active_tasks else 0
                        reserved_count = (
                            len(reserved_tasks.get(worker_name, [])) if reserved_tasks else 0
                        )

                        workers.append(
                            CeleryWorkerInfo(
                                hostname=worker_name,
                                active=True,
                                concurrency=worker_stats.get("pool", {}).get("max-concurrency", 1),
                                pool=worker_stats.get("pool", {}).get("implementation", "unknown"),
                                max_tasks_per_child=worker_stats.get("pool", {}).get(
                                    "max-tasks-per-child"
                                ),
                                active_tasks=active_count,
                                reserved_tasks=reserved_count,
                                total_processed=worker_stats.get("total", {})
                                .get("tasks", {})
                                .get("total"),
                            )
                        )
                else:
                    issues.append("No active Celery workers found")
            except Exception as e:
                logger.error(f"Failed to get worker stats: {e}")
                issues.append(f"Worker stats retrieval failed: {str(e)}")

        # Check result backend
        result_backend_connected = False
        try:
            # Try to access result backend
            test_result = AsyncResult("test-task-id", app=self.celery_app)
            result_backend_connected = True
        except Exception as e:
            logger.error(f"Failed to connect to result backend: {e}")
            issues.append(f"Result backend connection failed: {str(e)}")

        # Overall health
        healthy = broker_connected and result_backend_connected and len(workers) > 0

        # Mask sensitive broker URL
        broker_url = str(self.celery_app.conf.broker_url)
        if "@" in broker_url:
            broker_url = broker_url.split("@")[-1]

        return CeleryHealthResponse(
            broker_connected=broker_connected,
            broker_url=broker_url,
            result_backend_connected=result_backend_connected,
            active_workers=len(workers),
            workers=workers,
            queues=queues,
            healthy=healthy,
            issues=issues,
        )

    async def cancel_task(
        self,
        db: AsyncSession,
        task_id: str,
        terminate: bool = False,
    ) -> TaskCancelResponse:
        """
        Cancel a running task.

        Args:
            db: Database session
            task_id: Celery task ID
            terminate: Whether to forcefully terminate the task

        Returns:
            Task cancel response
        """
        async_result = AsyncResult(task_id, app=self.celery_app)

        if terminate:
            async_result.revoke(terminate=True, signal="SIGKILL")
            message = "Task terminated forcefully"
        else:
            async_result.revoke()
            message = "Task revoked gracefully"

        # Update database record
        await self.update_task_status(
            db,
            task_id,
            status="REVOKED",
            error=message,
        )

        return TaskCancelResponse(
            task_id=task_id,
            status="REVOKED",
            message=message,
        )

    def _task_exec_to_response(self, task_exec: TaskExecution) -> TaskExecutionResponse:
        """Convert TaskExecution ORM model to Pydantic response."""
        progress = None
        if any(
            [
                task_exec.progress_percent is not None,
                task_exec.progress_current is not None,
                task_exec.progress_total is not None,
                task_exec.progress_message is not None,
            ]
        ):
            progress = TaskProgressInfo(
                percent=task_exec.progress_percent,
                current=task_exec.progress_current,
                total=task_exec.progress_total,
                message=task_exec.progress_message,
            )

        return TaskExecutionResponse(
            id=task_exec.id,
            task_id=task_exec.task_id,
            task_name=task_exec.task_name,
            task_type=task_exec.task_type,
            status=task_exec.status,
            progress=progress,
            args=task_exec.args,
            kwargs=task_exec.kwargs,
            metadata=task_exec.metadata,
            worker_name=task_exec.worker_name,
            queue_name=task_exec.queue_name,
            retries=task_exec.retries,
            max_retries=task_exec.max_retries,
            created_at=task_exec.created_at,
            started_at=task_exec.started_at,
            completed_at=task_exec.completed_at,
            duration_seconds=task_exec.duration_seconds,
            result=task_exec.result,
            error=task_exec.error,
            traceback=task_exec.traceback,
            user_id=task_exec.user_id,
            is_finished=task_exec.is_finished,
            is_active=task_exec.is_active,
        )

    def _celery_result_to_response(
        self, task_id: str, async_result: AsyncResult
    ) -> TaskExecutionResponse:
        """Create minimal TaskExecutionResponse from Celery AsyncResult."""
        return TaskExecutionResponse(
            id=UUID("00000000-0000-0000-0000-000000000000"),  # Dummy ID
            task_id=task_id,
            task_name="unknown",
            task_type="unknown",
            status=async_result.state,
            progress=None,
            args=None,
            kwargs=None,
            metadata={},
            worker_name=None,
            queue_name=None,
            retries=0,
            max_retries=None,
            created_at=datetime.utcnow(),
            started_at=None,
            completed_at=None,
            duration_seconds=None,
            result=async_result.result if async_result.successful() else None,
            error=str(async_result.result) if async_result.failed() else None,
            traceback=async_result.traceback if async_result.failed() else None,
            user_id=None,
            is_finished=async_result.ready(),
            is_active=async_result.state in ("STARTED", "PROGRESS"),
        )
