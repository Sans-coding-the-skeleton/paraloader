import threading
import queue
import time
from typing import Callable, Any, List
import logging


class ThreadPool:
    """
    A reusable thread pool implementation that manages worker threads
    and task distribution. This can be used in ANY project needing
    concurrent task execution.
    """

    def __init__(self, num_workers: int, name: str = "Worker"):
        self.num_workers = num_workers
        self.task_queue = queue.Queue()
        self.workers: List[threading.Thread] = []
        self.shutdown_flag = False
        self.name_prefix = name
        self.lock = threading.RLock()
        self.active_tasks = 0
        self.logger = logging.getLogger(__name__)

        # PRODUCER-CONSUMER PATTERN: Create worker threads
        self._start_workers()

    def _start_workers(self):
        """Start all worker threads - the consumers"""
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self.name_prefix}-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

    def _worker_loop(self):
        """Main loop for each worker thread - consumes tasks"""
        while not self.shutdown_flag:
            try:
                # BLOCKING GET - demonstrates waiting for work
                task, args, kwargs = self.task_queue.get(timeout=1)

                with self.lock:
                    self.active_tasks += 1

                try:
                    # Execute the actual task
                    task(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Task execution failed: {e}")
                finally:
                    with self.lock:
                        self.active_tasks -= 1
                    self.task_queue.task_done()

            except queue.Empty:
                # Timeout allows checking shutdown_flag
                continue

    def submit(self, task: Callable, *args, **kwargs):
        """Submit a task to the pool - the producer side"""
        if self.shutdown_flag:
            raise RuntimeError("ThreadPool is shutting down")

        # PUT task in queue - producer action
        self.task_queue.put((task, args, kwargs))

    def wait_completion(self, timeout: float = None):
        """Wait for all tasks to complete"""
        self.task_queue.join()

    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool"""
        self.shutdown_flag = True
        if wait:
            self.wait_completion()

# USAGE EXAMPLE in other projects:
# pool = ThreadPool(4)
# for data in large_dataset:
#     pool.submit(process_data, data)
# pool.wait_completion()