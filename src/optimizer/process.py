"""
Process and thread management for optimal performance
"""

import os
import signal
import threading
from typing import List, Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process, Queue, Event, cpu_count
from queue import Empty
from threading import Event as ThreadEvent

class ProcessManager:
    """Manage worker processes and threads."""
    
    def __init__(
        self,
        worker_function: Callable,
        num_workers: Optional[int] = None,
        thread_multiplier: int = 2048,
        daemon: bool = True
    ):
        self.worker_function = worker_function
        self.num_workers = num_workers or cpu_count()
        self.thread_multiplier = thread_multiplier
        self.daemon = daemon
        self.processes: List[Process] = []
        self.stop_event = Event()
        self.result_queue = Queue()
        self.error_queue = Queue()
    
    def create_workers(self, *args, **kwargs) -> None:
        """Create worker processes."""
        self.processes = [
            Process(
                target=self._worker_wrapper,
                args=(i, *args),
                kwargs=kwargs,
                daemon=self.daemon
            )
            for i in range(self.num_workers)
        ]
    
    def _worker_wrapper(self, worker_id: int, *args, **kwargs) -> None:
        """Wrapper for worker function with error handling."""
        try:
            # Set process name for better monitoring
            if hasattr(os, 'getpid'):
                threading.current_thread().name = f"Worker-{worker_id}"
            
            # Run worker function
            result = self.worker_function(*args, **kwargs)
            
            # Send result if any
            if result is not None:
                self.result_queue.put((worker_id, result))
        
        except Exception as e:
            # Send error to main process
            self.error_queue.put((worker_id, str(e)))
            # Signal other processes to stop
            self.stop_event.set()
    
    def start_workers(self) -> None:
        """Start all worker processes."""
        for process in self.processes:
            process.start()
    
    def stop_workers(self) -> None:
        """Stop all worker processes."""
        self.stop_event.set()
        for process in self.processes:
            if process.is_alive():
                process.terminate()
    
    def join_workers(self, timeout: Optional[float] = None) -> None:
        """Wait for all worker processes to complete."""
        for process in self.processes:
            process.join(timeout)
    
    def check_errors(self) -> List[tuple]:
        """Check for any errors from workers."""
        errors = []
        try:
            while True:
                error = self.error_queue.get_nowait()
                errors.append(error)
        except Empty:
            pass
        return errors
    
    def get_results(self) -> List[tuple]:
        """Get results from workers."""
        results = []
        try:
            while True:
                result = self.result_queue.get_nowait()
                results.append(result)
        except Empty:
            pass
        return results
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_workers()
        self.result_queue.close()
        self.error_queue.close()
        self.processes.clear()

class ThreadManager:
    """Manage thread pool for parallel processing."""
    
    def __init__(
        self,
        num_threads: Optional[int] = None,
        thread_name_prefix: str = "Worker"
    ):
        self.num_threads = num_threads or (cpu_count() * 2)
        self.thread_name_prefix = thread_name_prefix
        self.executor: Optional[ThreadPoolExecutor] = None
        self.stop_event = ThreadEvent()
    
    def start(self) -> None:
        """Start thread pool."""
        self.executor = ThreadPoolExecutor(
            max_workers=self.num_threads,
            thread_name_prefix=self.thread_name_prefix
        )
    
    def stop(self) -> None:
        """Stop thread pool."""
        if self.executor:
            self.stop_event.set()
            self.executor.shutdown(wait=True)
            self.executor = None
    
    def submit(self, fn: Callable, *args, **kwargs) -> Any:
        """Submit task to thread pool."""
        if not self.executor:
            raise RuntimeError("Thread pool not started")
        return self.executor.submit(fn, *args, **kwargs)
    
    def map(self, fn: Callable, *iterables, timeout: Optional[float] = None) -> List[Any]:
        """Map function over iterables in parallel."""
        if not self.executor:
            raise RuntimeError("Thread pool not started")
        return list(self.executor.map(fn, *iterables, timeout=timeout))
    
    def __enter__(self) -> 'ThreadManager':
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

def set_process_signals() -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        # Perform cleanup
        pass
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ignore broken pipe errors
    signal.signal(signal.SIGPIPE, signal.SIG_IGN) 