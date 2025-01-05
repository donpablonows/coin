"""
Ultra-optimized system performance tuning.
Maximizes hardware utilization through intelligent resource management.
"""

import os
import sys
import gc
import ctypes
import platform
import threading
from typing import Dict, Optional, List, Any
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor

class SystemOptimizer:
    """Advanced system optimization manager."""
    
    def __init__(
        self,
        thread_multiplier: int = 2048,
        memory_target: float = 0.9,  # Target 90% memory usage
        cpu_target: float = 0.95,    # Target 95% CPU usage
        gpu_memory_target: float = 0.8  # Target 80% GPU memory usage
    ):
        self.num_cpus = os.cpu_count() or 1
        self.thread_multiplier = thread_multiplier
        self.num_threads = self.num_cpus * self.thread_multiplier
        self.memory_target = memory_target
        self.cpu_target = cpu_target
        self.gpu_memory_target = gpu_memory_target
        
        self.process = psutil.Process()
        self._original_settings: Dict[str, Any] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def optimize_windows(self) -> None:
        """Apply advanced Windows optimizations."""
        if sys.platform != "win32":
            return
        
        try:
            # Import Windows-specific modules
            import win32api
            import win32con
            import win32process
            import win32security
            from ctypes import windll
            
            # Get process handle
            handle = win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS,
                False,
                os.getpid()
            )
            
            # Set process priority and boost
            win32process.SetPriorityClass(
                handle,
                win32process.HIGH_PRIORITY_CLASS
            )
            windll.kernel32.SetProcessPriorityBoost(handle, True)
            
            # Enable large pages support
            privilege = win32security.LookupPrivilegeValue(
                None,
                win32security.SE_LOCK_MEMORY_NAME
            )
            token = win32security.OpenProcessToken(
                handle,
                win32security.TOKEN_ALL_ACCESS
            )
            win32security.AdjustTokenPrivileges(
                token,
                False,
                [(privilege, win32security.SE_PRIVILEGE_ENABLED)]
            )
            
            # Optimize memory
            win32process.SetProcessWorkingSetSize(
                handle,
                -1,
                -1
            )
            
            # Set CPU affinity for all cores
            mask = (1 << self.num_cpus) - 1
            win32process.SetProcessAffinityMask(handle, mask)
            
        except ImportError:
            pass
    
    def optimize_linux(self) -> None:
        """Apply advanced Linux optimizations."""
        if sys.platform != "linux":
            return
        
        try:
            # Set maximum process priority
            os.nice(-20)
            
            # Configure CPU governor
            for cpu in range(self.num_cpus):
                governor_path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
                if os.path.exists(governor_path):
                    try:
                        with open(governor_path, "w") as f:
                            f.write("performance")
                    except PermissionError:
                        pass
            
            # Optimize kernel parameters
            kernel_params = {
                "kernel.sched_rt_runtime_us": -1,
                "kernel.sched_migration_cost_ns": 5000000,
                "kernel.sched_autogroup_enabled": 0,
                "vm.swappiness": 10,
                "vm.dirty_ratio": 60,
                "vm.dirty_background_ratio": 2
            }
            
            # Apply kernel parameters
            for param, value in kernel_params.items():
                try:
                    with open(f"/proc/sys/{param.replace('.', '/')}", "w") as f:
                        f.write(str(value))
                except (PermissionError, FileNotFoundError):
                    pass
            
        except Exception:
            pass
    
    def optimize_memory(self) -> None:
        """Apply advanced memory optimizations."""
        # Configure garbage collection
        gc.enable()
        gc.set_threshold(100000, 100000, 100000)
        
        # Pre-allocate memory pool
        self._allocate_memory_pool()
        
        # Set memory priority
        if sys.platform == "win32":
            try:
                import win32process
                win32process.SetProcessWorkingSetSize(
                    win32process.GetCurrentProcess(),
                    -1,
                    -1
                )
            except ImportError:
                pass
    
    def _allocate_memory_pool(self, pool_size_mb: int = 1024) -> None:
        """Pre-allocate memory pool for better performance."""
        try:
            # Allocate memory pool
            pool_size = pool_size_mb * 1024 * 1024
            self._memory_pool = np.zeros(pool_size, dtype=np.uint8)
            
            # Lock memory pages
            if sys.platform == "win32":
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel32.VirtualLock(
                    self._memory_pool.ctypes.data,
                    pool_size
                )
            else:
                import resource
                resource.plock(resource.LOCK_MLOCK)
                
        except Exception:
            self._memory_pool = None
    
    def set_environment_variables(self) -> None:
        """Set optimized environment variables."""
        # Store original settings
        self._original_settings = {
            key: os.environ.get(key) for key in [
                "PYTHONOPTIMIZE",
                "PYTHONMALLOC",
                "NUMBA_NUM_THREADS",
                "MKL_NUM_THREADS",
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "CUDA_CACHE_MAXSIZE",
                "CUDA_FORCE_PTX_JIT",
                "TF_XLA_FLAGS",
                "NUMBA_CACHE_DIR"
            ]
        }
        
        # Set optimized values
        env_vars = {
            "PYTHONOPTIMIZE": "2",
            "PYTHONMALLOC": "malloc",
            "NUMBA_NUM_THREADS": str(self.num_threads),
            "MKL_NUM_THREADS": str(self.num_threads),
            "OMP_NUM_THREADS": str(self.num_threads),
            "OPENBLAS_NUM_THREADS": str(self.num_threads),
            "CUDA_CACHE_MAXSIZE": str(2**30),  # 1GB cache
            "CUDA_FORCE_PTX_JIT": "1",
            "TF_XLA_FLAGS": "--tf_xla_auto_jit=2",
            "NUMBA_CACHE_DIR": os.path.join(os.getcwd(), ".cache")
        }
        
        os.environ.update(env_vars)
    
    def restore_environment_variables(self) -> None:
        """Restore original environment variables."""
        for key, value in self._original_settings.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    def start_monitoring(self) -> None:
        """Start performance monitoring thread."""
        self._monitor_thread = threading.Thread(
            target=self._monitor_performance,
            daemon=True
        )
        self._monitor_thread.start()
    
    def _monitor_performance(self) -> None:
        """Monitor and optimize system performance."""
        while not self._stop_event.is_set():
            try:
                # Monitor CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent < self.cpu_target * 100:
                    self._optimize_cpu_usage()
                
                # Monitor memory usage
                memory_percent = psutil.virtual_memory().percent
                if memory_percent < self.memory_target * 100:
                    self._optimize_memory_usage()
                
                # Monitor GPU if available
                self._optimize_gpu_usage()
                
            except Exception:
                pass
            
            threading.Event().wait(1.0)
    
    def _optimize_cpu_usage(self) -> None:
        """Optimize CPU usage."""
        try:
            # Set CPU affinity
            available_cpus = list(range(self.num_cpus))
            self.process.cpu_affinity(available_cpus)
            
            # Adjust process priority
            if self.process.nice() > -20:
                self.process.nice(max(self.process.nice() - 1, -20))
                
        except Exception:
            pass
    
    def _optimize_memory_usage(self) -> None:
        """Optimize memory usage."""
        try:
            # Trigger garbage collection
            gc.collect()
            
            # Compact memory if possible
            if sys.platform == "win32":
                ctypes.windll.psapi.EmptyWorkingSet(
                    ctypes.windll.kernel32.GetCurrentProcess()
                )
                
        except Exception:
            pass
    
    def _optimize_gpu_usage(self) -> None:
        """Optimize GPU usage if available."""
        try:
            import torch
            if torch.cuda.is_available():
                # Clear GPU cache
                torch.cuda.empty_cache()
                
                # Optimize memory allocation
                torch.cuda.memory.set_per_process_memory_fraction(
                    self.gpu_memory_target
                )
                
        except ImportError:
            pass
    
    def optimize(self) -> None:
        """Apply all optimizations."""
        self.optimize_memory()
        self.optimize_windows()
        self.optimize_linux()
        self.set_environment_variables()
        self.start_monitoring()
    
    def cleanup(self) -> None:
        """Clean up optimizations."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        
        self.restore_environment_variables()
        gc.collect()
        
        # Release memory pool
        if hasattr(self, '_memory_pool'):
            del self._memory_pool
    
    def __enter__(self) -> 'SystemOptimizer':
        """Context manager entry."""
        self.optimize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()
    
    @property
    def memory_usage(self) -> float:
        """Get current memory usage in GB."""
        return self.process.memory_info().rss / 1024**3
    
    @property
    def cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return self.process.cpu_percent()
    
    @property
    def system_info(self) -> Dict[str, Any]:
        """Get detailed system information."""
        return {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'cpu_count': self.num_cpus,
            'memory_total': psutil.virtual_memory().total / 1024**3,
            'memory_available': psutil.virtual_memory().available / 1024**3,
            'swap_total': psutil.swap_memory().total / 1024**3,
            'swap_free': psutil.swap_memory().free / 1024**3,
            'disk_usage': psutil.disk_usage('/').percent,
            'python_version': sys.version,
            'process_priority': self.process.nice()
        } 