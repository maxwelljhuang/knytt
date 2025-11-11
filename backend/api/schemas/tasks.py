"""
Pydantic schemas for Celery task monitoring.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field


class TaskProgressInfo(BaseModel):
    """Task progress information."""

    percent: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage (0-100)")
    current: Optional[int] = Field(None, description="Current item being processed")
    total: Optional[int] = Field(None, description="Total items to process")
    message: Optional[str] = Field(None, description="Human-readable progress message")


class TaskExecutionResponse(BaseModel):
    """Task execution details response."""

    id: UUID = Field(..., description="Internal database ID")
    task_id: str = Field(..., description="Celery task ID (UUID)")
    task_name: str = Field(..., description="Task function name")
    task_type: str = Field(..., description="Task category (embedding, ingestion, maintenance)")

    # Status
    status: str = Field(
        ...,
        description="Task status (PENDING, STARTED, PROGRESS, SUCCESS, FAILURE, REVOKED, RETRY)",
    )
    progress: Optional[TaskProgressInfo] = Field(None, description="Task progress information")

    # Metadata
    args: Optional[List[Any]] = Field(None, description="Task positional arguments")
    kwargs: Optional[Dict[str, Any]] = Field(None, description="Task keyword arguments")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional task metadata")

    # Execution details
    worker_name: Optional[str] = Field(None, description="Worker that executed the task")
    queue_name: Optional[str] = Field(None, description="Queue the task was sent to")
    retries: int = Field(..., description="Number of retry attempts")
    max_retries: Optional[int] = Field(None, description="Maximum number of retries allowed")

    # Timing
    created_at: datetime = Field(..., description="When task was created/dispatched")
    started_at: Optional[datetime] = Field(None, description="When task started executing")
    completed_at: Optional[datetime] = Field(None, description="When task finished")
    duration_seconds: Optional[float] = Field(None, description="Task duration in seconds")

    # Results and errors
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if task failed")
    traceback: Optional[str] = Field(None, description="Full error traceback")

    # User association
    user_id: Optional[UUID] = Field(None, description="User who triggered the task")

    # Computed fields
    is_finished: bool = Field(..., description="Whether task has finished")
    is_active: bool = Field(..., description="Whether task is currently active")

    class Config:
        from_attributes = True


class TaskExecutionListResponse(BaseModel):
    """Paginated list of task executions."""

    tasks: List[TaskExecutionResponse] = Field(..., description="List of task executions")
    total: int = Field(..., description="Total number of tasks matching filters")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of tasks per page")
    has_more: bool = Field(..., description="Whether there are more tasks available")


class TaskStatsResponse(BaseModel):
    """Aggregated task statistics."""

    total_tasks: int = Field(..., description="Total number of tasks")
    pending: int = Field(..., description="Number of pending tasks")
    started: int = Field(..., description="Number of started tasks")
    in_progress: int = Field(..., description="Number of tasks in progress")
    success: int = Field(..., description="Number of successful tasks")
    failure: int = Field(..., description="Number of failed tasks")
    revoked: int = Field(..., description="Number of revoked tasks")
    retry: int = Field(..., description="Number of tasks retrying")

    # By task type
    by_type: Dict[str, int] = Field(..., description="Task counts by type")

    # Timing
    avg_duration_seconds: Optional[float] = Field(
        None, description="Average task duration in seconds"
    )
    total_duration_seconds: Optional[float] = Field(None, description="Total duration of all tasks")

    # Recent activity
    tasks_last_hour: int = Field(..., description="Tasks started in the last hour")
    tasks_last_24h: int = Field(..., description="Tasks started in the last 24 hours")
    tasks_last_week: int = Field(..., description="Tasks started in the last week")


class CeleryWorkerInfo(BaseModel):
    """Celery worker information."""

    hostname: str = Field(..., description="Worker hostname")
    active: bool = Field(..., description="Whether worker is active")
    concurrency: int = Field(..., description="Worker concurrency level")
    pool: str = Field(..., description="Worker pool type (prefork, gevent, etc.)")
    max_tasks_per_child: Optional[int] = Field(None, description="Max tasks per child process")

    # Current state
    active_tasks: int = Field(..., description="Number of currently active tasks")
    reserved_tasks: int = Field(..., description="Number of reserved tasks")

    # Stats (if available)
    total_processed: Optional[int] = Field(None, description="Total tasks processed by worker")


class CeleryQueueInfo(BaseModel):
    """Celery queue information."""

    name: str = Field(..., description="Queue name")
    messages: int = Field(..., description="Number of messages in queue")
    consumers: int = Field(..., description="Number of active consumers")


class CeleryHealthResponse(BaseModel):
    """Celery infrastructure health status."""

    broker_connected: bool = Field(..., description="Whether broker is connected")
    broker_url: str = Field(..., description="Broker URL (masked)")
    result_backend_connected: bool = Field(..., description="Whether result backend is connected")

    # Workers
    active_workers: int = Field(..., description="Number of active workers")
    workers: List[CeleryWorkerInfo] = Field(..., description="List of workers")

    # Queues
    queues: List[CeleryQueueInfo] = Field(..., description="List of queues")

    # Overall health
    healthy: bool = Field(..., description="Whether Celery infrastructure is healthy")
    issues: List[str] = Field(default_factory=list, description="List of health issues")


class TaskDispatchRequest(BaseModel):
    """Request to dispatch a task."""

    task_name: str = Field(..., description="Task function name to dispatch")
    args: Optional[List[Any]] = Field(default_factory=list, description="Positional arguments")
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Keyword arguments")
    queue: Optional[str] = Field(None, description="Queue to send task to")
    countdown: Optional[int] = Field(None, description="Delay in seconds before execution")
    eta: Optional[datetime] = Field(None, description="Specific datetime to execute")
    user_id: Optional[UUID] = Field(None, description="User triggering the task")


class TaskDispatchResponse(BaseModel):
    """Response after dispatching a task."""

    task_id: str = Field(..., description="Celery task ID")
    task_name: str = Field(..., description="Task function name")
    status: str = Field(..., description="Initial task status")
    message: str = Field(..., description="Human-readable message")
    db_id: Optional[UUID] = Field(None, description="Database record ID")


class TaskCancelRequest(BaseModel):
    """Request to cancel a task."""

    task_id: str = Field(..., description="Celery task ID to cancel")
    terminate: bool = Field(False, description="Whether to forcefully terminate the task")


class TaskCancelResponse(BaseModel):
    """Response after canceling a task."""

    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Task status after cancel")
    message: str = Field(..., description="Human-readable message")


class TaskRetryRequest(BaseModel):
    """Request to retry a failed task."""

    task_id: str = Field(..., description="Celery task ID to retry")
    countdown: Optional[int] = Field(None, description="Delay in seconds before retry")


class TaskRetryResponse(BaseModel):
    """Response after retrying a task."""

    new_task_id: str = Field(..., description="New Celery task ID")
    original_task_id: str = Field(..., description="Original task ID")
    status: str = Field(..., description="New task status")
    message: str = Field(..., description="Human-readable message")
