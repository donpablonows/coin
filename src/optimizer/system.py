"""
System optimization and performance tuning
"""

import os
import sys
import gc
import psutil
from multiprocessing import cpu_count
from typing import Dict, Optional

class SystemOptimizer:
    """Manage system-wide optimizations."""
    
    def __init__(self, thread_multiplier: int = 2048):
        self.num_cpus = cpu_count()
        self.thread_multiplier = thread_multiplier
        self.num_threads = self.num_cpus * self.thread_multiplier
        self.original_settings = {}
        self.process = psutil.Process()
    
    def optimize_windows(self) -> None:
        """Apply Windows-specific optimizations."""
        if sys.platform != "win32":
            return
        
        try:
            from ctypes import windll
            from win32api import OpenProcess, GetCurrentThread
            from win32process import (
                SetPriorityClass,
                SetProcessWorkingSetSize,
                SetThreadAffinityMask,
                ABOVE_NORMAL_PRIORITY_CLASS
            )
            from win32security import (
                OpenProcessToken,
                AdjustTokenPrivileges,
                LookupPrivilegeValue,
                SE_LOCK_MEMORY_NAME
            )
            
            # Set maximum thread and process priorities
            windll.kernel32.SetThreadPriority(-2, 31)
            windll.kernel32.SetProcessPriorityBoost(-1, 1)
            
            # Optimize process settings
            handle = OpenProcess(2035711, 1, os.getpid())
            SetPriorityClass(handle, ABOVE_NORMAL_PRIORITY_CLASS)
            SetProcessWorkingSetSize(handle, -1, -1)
            
            # Enable large pages support
            token = OpenProcessToken(handle, 983551)
            AdjustTokenPrivileges(token, 0, [
                (LookupPrivilegeValue(0, SE_LOCK_MEMORY_NAME), 2)
            ])
            
            # Set CPU affinity for maximum performance
            for i in range(self.num_cpus):
                self.process.cpu_affinity([i])
                SetThreadAffinityMask(GetCurrentThread(), 1 << i)
        
        except ImportError:
            pass  # Windows optimization modules not available
    
    def optimize_linux(self) -> None:
        """Apply Linux-specific optimizations."""
        if sys.platform != "linux":
            return
        
        try:
            # Set process niceness
            os.nice(-20)
            
            # Set CPU governor to performance
            for cpu in range(self.num_cpus):
                governor_path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
                if os.path.exists(governor_path):
                    try:
                        with open(governor_path, "w") as f:
                            f.write("performance")
                    except PermissionError:
                        pass
            
            # Disable CPU frequency scaling
            os.system("echo -1 > /proc/sys/kernel/sched_rt_runtime_us")
        
        except Exception:
            pass  # Linux optimization failed
    
    def optimize_memory(self) -> None:
        """Optimize memory management."""
        # Configure garbage collection
        gc.enable()
        gc.set_threshold(9**9, 9**9, 9**9)
        
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
    
    def set_environment_variables(self) -> None:
        """Set optimized environment variables."""
        env_vars = {
            "PYTHONOPTIMIZE": "2",
            "PYTHONMALLOC": "malloc",
            "NUMBA_NUM_THREADS": str(self.num_threads),
            "MKL_NUM_THREADS": str(self.num_threads),
            "OMP_NUM_THREADS": str(self.num_threads),
            "OPENBLAS_NUM_THREADS": str(self.num_threads),
            "CUDA_CACHE_MAXSIZE": "9" * 9,
            "CUDA_FORCE_PTX_JIT": "1",
            "TF_XLA_FLAGS": "--tf_xla_auto_jit=2",
            "NUMBA_CACHE_DIR": ".cache"
        }
        
        # Store original values
        self.original_settings = {
            key: os.environ.get(key) for key in env_vars
        }
        
        # Set new values
        os.environ.update(env_vars)
    
    def restore_environment_variables(self) -> None:
        """Restore original environment variables."""
        for key, value in self.original_settings.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    def optimize(self) -> None:
        """Apply all optimizations."""
        self.optimize_memory()
        self.optimize_windows()
        self.optimize_linux()
        self.set_environment_variables()
    
    def cleanup(self) -> None:
        """Clean up optimizations."""
        self.restore_environment_variables()
        gc.collect()
    
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