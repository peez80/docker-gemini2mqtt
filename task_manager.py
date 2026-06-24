import time
import threading
import concurrent.futures
import logging
from typing import Callable

logger = logging.getLogger(__name__)

QUEUE_STATUS_INTERVAL = 30  # seconds

class TaskManager:
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self._tasks_lock = threading.Lock()
        self._pending_count: int = 0
        self._active_tasks: dict[int, float] = {}
        self._task_id_counter: int = 0
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent)
        
        self._stop_event = threading.Event()
        self._status_thread = threading.Thread(
            target=self._queue_status_loop,
            daemon=True,
            name="queue-status"
        )
        self._status_thread.start()

    def submit_task(self, func: Callable, *args, **kwargs) -> None:
        with self._tasks_lock:
            task_id = self._task_id_counter
            self._task_id_counter += 1
            self._pending_count += 1
            
        def _worker():
            with self._tasks_lock:
                self._pending_count -= 1
                self._active_tasks[task_id] = time.monotonic()
                
            try:
                func(*args, **kwargs)
            finally:
                with self._tasks_lock:
                    self._active_tasks.pop(task_id, None)

        self._executor.submit(_worker)

    def _queue_status_loop(self) -> None:
        was_busy = False
        while not self._stop_event.is_set():
            if self._stop_event.wait(QUEUE_STATUS_INTERVAL):
                break
            
            now = time.monotonic()
            with self._tasks_lock:
                active_durations = [round(now - t) for t in self._active_tasks.values()]
                pending = self._pending_count

            is_busy = bool(active_durations) or pending > 0
            if is_busy:
                durations_str = ", ".join(f"{d}s" for d in active_durations)
                logger.info(
                    "Queue status: %d active (%s), %d queued",
                    len(active_durations), durations_str, pending,
                )
                was_busy = True
            elif was_busy:
                logger.info("Queue status: 0 active, 0 queued (queue empty)")
                was_busy = False

    def shutdown(self) -> None:
        self._stop_event.set()
        self._executor.shutdown(wait=False)
