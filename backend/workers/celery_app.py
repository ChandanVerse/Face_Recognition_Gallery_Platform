"""
Celery application configuration - OPTIMIZED
"""
from celery import Celery
from backend.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    'face_recognition_workers',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['backend.workers.tasks']
)

celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task tracking and limits
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit (gives time for cleanup)

    # Worker optimization for GPU workload
    worker_prefetch_multiplier=2,  # Fetch 2 tasks at a time (concurrency of 2)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevents memory leaks)
    worker_pool_restarts=True,

    # Concurrency limit - Maximum 2 concurrent tasks per worker
    worker_concurrency=2,

    # Compression (reduce Redis memory usage)
    task_compression='gzip',
    result_compression='gzip',

    # Reliability
    task_acks_late=True,  # Acknowledge after task completion (safer)
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_acks_on_failure_or_timeout=True,  # Ack even on failure

    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=False,  # Don't persist results to disk
)

# Task routing with priorities
celery_app.conf.task_routes = {
    'backend.workers.tasks.process_photo': {'queue': 'photo_processing'},
    'backend.workers.tasks.create_user_profile': {'queue': 'profile_creation'},
    'backend.workers.tasks.scan_all_galleries_for_user': {'queue': 'photo_processing'},
}

# Queue priorities (higher number = higher priority)
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5

# Set priority for specific tasks
celery_app.conf.task_default_queue = 'default'
celery_app.conf.task_create_missing_queues = True