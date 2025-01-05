"""
Ultra-optimized process and thread management.
Provides maximum performance through intelligent resource allocation.
"""

import os
import signal
import threading
import multiprocessing as mp
from typing import List, Callable, Any, Optional, Dict, Union
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from queue import Queue, Empty
from threading import Event as ThreadEvent
import psutil
import numpy as np

class ProcessManager:
    """High-performance process manager with dynamic scaling."""
    
    def __init__(
        self,
        worker_function: Callable,
        num_workers: Optional[int] = None,
        thread_multiplier: int = 2048,
        daemon: bool = True,
        priority: int = psutil.HIGH_PRIORITY_CLASS
    ):
        self.worker_function = worker_function
        self.num_workers = num_workers or mp.cpu_count()
        self.thread_multiplier = thread_multiplier
        self.daemon = daemon
        self.priority = priority
        
        # Process management
        self.processes: List[mp.Process] = []
        self.stop_event = mp.Event()
        self.result_queue = mp.Queue()
        self.error_queue = mp.Queue()
        
        # Performance monitoring
        self._monitor_thread: Optional[threading.Thread] = None
        self._performance_stats: Dict[int, Dict[str, float]] = {}
        self._stats_lock = threading.Lock()
    
    def create_workers(self, *args, **kwargs) -> None:
        """Create optimized worker processes."""
        self.processes = [
            mp.Process(
                target=self._worker_wrapper,
                args=(i, *args),
                kwargs=kwargs,
                daemon=self.daemon
            )
            for i in range(self.num_workers)
        ]
    
    def _worker_wrapper(self, worker_id: int, *args, **kwargs) -> None:
        """Enhanced worker wrapper with performance optimization."""
        try:
            # Set process name and priority
            process = psutil.Process()
            process.name = f"Worker-{worker_id}"
            process.nice(10)  # Lower nice value = higher priority
            
            if os.name == 'nt':
                process.nice(self.priority)
            
            # Set CPU affinity
            cpu_id = worker_id % mp.cpu_count()
            process.cpu_affinity([cpu_id])
            
            # Initialize worker-specific RNG
            np.random.seed(os.getpid() + worker_id)
            
            # Run worker function
            result = self.worker_function(*args, **kwargs)
            
            # Send result if any
            if result is not None:
                self.result_queue.put((worker_id, result))
            
            # Update performance stats
            self._update_stats(worker_id, process)
            
        except Exception as e:
            # Send error to main process
            self.error_queue.put((worker_id, str(e)))
            # Signal other processes to stop
            self.stop_event.set()
    
    def _update_stats(self, worker_id: int, process: psutil.Process) -> None:
        """Update performance statistics for worker."""
        try:
            with self._stats_lock:
                self._performance_stats[worker_id] = {
                    'cpu_percent': process.cpu_percent(),
                    'memory_percent': process.memory_percent(),
                    'io_counters': process.io_counters()._asdict()
                }
        except Exception:
            pass
    
    def start_workers(self) -> None:
        """Start workers with performance monitoring."""
        # Start performance monitoring
        self._monitor_thread = threading.Thread(
            target=self._monitor_performance,
            daemon=True
        )
        self._monitor_thread.start()
        
        # Start workers
        for process in self.processes:
            process.start()
    
    def _monitor_performance(self) -> None:
        """Monitor worker performance and adjust resources."""
        while not self.stop_event.is_set():
            try:
                for worker_id, process in enumerate(self.processes):
                    if process.is_alive():
                        psutil_process = psutil.Process(process.pid)
                        self._update_stats(worker_id, psutil_process)
                        
                        # Optimize if process is underperforming
                        stats = self._performance_stats.get(worker_id, {})
                        if stats.get('cpu_percent', 0) < 50:
                            self._optimize_worker(psutil_process)
                
                threading.Event().wait(1.0)  # Check every second
                
            except Exception:
                continue
    
    def _optimize_worker(self, process: psutil.Process) -> None:
        """Optimize worker process performance."""
        try:
            # Increase priority if needed
            if process.nice() > 0:
                process.nice(max(process.nice() - 1, -20))
            
            # Optimize memory
            if os.name == 'nt':
                process.suspend()
                process.resume()
        except Exception:
            pass
    
    def stop_workers(self) -> None:
        """Stop workers gracefully."""
        self.stop_event.set()
        
        for process in self.processes:
            if process.is_alive():
                process.terminate()
        
        # Wait for processes to terminate
        for process in self.processes:
            process.join(timeout=1.0)
            
        # Force kill if necessary
        for process in self.processes:
            if process.is_alive():
                process.kill()
    
    def join_workers(self, timeout: Optional[float] = None) -> None:
        """Wait for workers with timeout."""
        for process in self.processes:
            try:
                process.join(timeout=timeout)
            except Exception:
                continue
    
    def check_errors(self) -> List[tuple]:
        """Check for worker errors."""
        errors = []
        try:
            while True:
                error = self.error_queue.get_nowait()
                errors.append(error)
        except Empty:
            pass
        return errors
    
    def get_results(self) -> List[tuple]:
        """Get worker results."""
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
        
        # Clean up queues
        for queue in [self.result_queue, self.error_queue]:
            while True:
                try:
                    queue.get_nowait()
                except Empty:
                    break
            queue.close()
            queue.join_thread()
        
        self.processes.clear()
        self._performance_stats.clear()

class ThreadManager:
    """High-performance thread pool manager."""
    
    def __init__(
        self,
        num_threads: Optional[int] = None,
        thread_name_prefix: str = "Worker",
        queue_size: int = 10000
    ):
        self.num_threads = num_threads or (mp.cpu_count() * 2)
        self.thread_name_prefix = thread_name_prefix
        self.queue_size = queue_size
        self.executor: Optional[ThreadPoolExecutor] = None
        self.stop_event = ThreadEvent()
        self.task_queue: Queue = Queue(maxsize=queue_size)
        self._futures: List[Future] = []
    
    def start(self) -> None:
        """Start optimized thread pool."""
        self.executor = ThreadPoolExecutor(
            max_workers=self.num_threads,
            thread_name_prefix=self.thread_name_prefix,
            initializer=self._thread_initializer
        )
    
    def _thread_initializer(self) -> None:
        """Initialize thread-specific settings."""
        thread = threading.current_thread()
        
        # Set thread priority
        if hasattr(thread, "priority"):
            thread.priority = threading.HIGHEST_PRIORITY
    
    def stop(self) -> None:
        """Stop thread pool gracefully."""
        if self.executor:
            self.stop_event.set()
            
            # Cancel pending futures
            for future in self._futures:
                if not future.done():
                    future.cancel()
            
            self.executor.shutdown(wait=True)
            self.executor = None
            self._futures.clear()
    
    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit task to thread pool."""
        if not self.executor:
            raise RuntimeError("Thread pool not started")
        
        future = self.executor.submit(fn, *args, **kwargs)
        self._futures.append(future)
        return future
    
    def map(
        self,
        fn: Callable,
        *iterables,
        timeout: Optional[float] = None,
        chunksize: Optional[int] = None
    ) -> List[Any]:
        """Map function over iterables in parallel."""
        if not self.executor:
            raise RuntimeError("Thread pool not started")
        
        # Optimize chunk size if not specified
        if chunksize is None:
            chunksize = max(1, len(next(iter(iterables))) // (self.num_threads * 4))
        
        return list(self.executor.map(fn, *iterables,
                                    timeout=timeout,
                                    chunksize=chunksize))
    
    def __enter__(self) -> 'ThreadManager':
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

def set_process_signals() -> None:
    """Set up optimized signal handlers."""
    def signal_handler(signum: int, frame: Any) -> None:
        # Clean up resources
        for process in psutil.Process().children(recursive=True):
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ignore broken pipe errors
    signal.signal(signal.SIGPIPE, signal.SIG_IGN) 