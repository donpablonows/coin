"""
Ultra-optimized CUDA operations and GPU acceleration.
Provides maximum performance for cryptographic operations.
"""

import os
import torch
import numpy as np
from numba import cuda
from typing import Optional, Dict, Any

class CUDAManager:
    """High-performance CUDA resource manager."""
    
    def __init__(self, device_id: int = 0):
        self.available = torch.cuda.is_available()
        self.device = torch.device(f"cuda:{device_id}" if self.available else "cpu")
        self.enabled = False
        self.stream: Optional[cuda.Stream] = None
        self._original_settings: Dict[str, Any] = {}
    
    def setup(self) -> bool:
        """Initialize and optimize CUDA environment."""
        if not self.available:
            return False
        
        try:
            # Store original settings
            self._original_settings = {
                "memory_fraction": torch.cuda.get_device_properties(0).total_memory,
                "cache_size": os.environ.get("CUDA_CACHE_MAXSIZE"),
                "ptx_jit": os.environ.get("CUDA_FORCE_PTX_JIT")
            }
            
            # Configure CUDA device
            torch.cuda.set_device(self.device)
            torch.cuda.empty_cache()
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
            torch.backends.cudnn.deterministic = False
            
            # Optimize memory management
            torch.cuda.set_per_process_memory_fraction(0.95)
            
            # Enable tensor cores if available
            if torch.cuda.get_device_capability()[0] >= 7:
                torch.set_float32_matmul_precision('high')
            
            # Create CUDA stream for async operations
            self.stream = cuda.stream()
            
            # Set environment variables
            os.environ["CUDA_CACHE_MAXSIZE"] = str(2**30)  # 1GB cache
            os.environ["CUDA_FORCE_PTX_JIT"] = "1"
            
            self.enabled = True
            return True
            
        except Exception as e:
            print(f"CUDA setup failed: {e}")
            self.cleanup()
            return False
    
    def cleanup(self) -> None:
        """Clean up CUDA resources."""
        if not self.enabled:
            return
        
        try:
            # Synchronize and destroy stream
            if self.stream:
                self.stream.synchronize()
                del self.stream
            
            # Clear cache and reset device
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # Restore original settings
            for key, value in self._original_settings.items():
                if value is not None:
                    os.environ[key] = str(value)
                else:
                    os.environ.pop(key, None)
            
            self.enabled = False
            
        except Exception as e:
            print(f"CUDA cleanup failed: {e}")
    
    def __enter__(self) -> 'CUDAManager':
        """Context manager entry."""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()
    
    @property
    def device_name(self) -> str:
        """Get CUDA device name."""
        return torch.cuda.get_device_name(0) if self.available else "CPU"
    
    @property
    def memory_allocated(self) -> float:
        """Get allocated memory in GB."""
        if not self.available:
            return 0.0
        return torch.cuda.memory_allocated() / 1024**3
    
    @property
    def memory_cached(self) -> float:
        """Get cached memory in GB."""
        if not self.available:
            return 0.0
        return torch.cuda.memory_cached() / 1024**3
    
    @property
    def memory_summary(self) -> str:
        """Get detailed memory usage summary."""
        if not self.available:
            return "CUDA not available"
        return torch.cuda.memory_summary(device=self.device, abbreviated=True)
    
    def optimize_kernel_launch(
        self,
        data_size: int,
        threads_per_block: int = 256
    ) -> tuple[int, int]:
        """
        Calculate optimal kernel launch configuration.
        
        Args:
            data_size: Size of data to process
            threads_per_block: Number of threads per block
            
        Returns:
            Tuple of (grid_size, block_size)
        """
        if not self.available:
            return (1, 1)
        
        max_threads = torch.cuda.get_device_properties(0).max_threads_per_block
        threads_per_block = min(threads_per_block, max_threads)
        grid_size = (data_size + threads_per_block - 1) // threads_per_block
        
        return grid_size, threads_per_block
    
    def get_optimal_batch_size(self, data_size: int) -> int:
        """
        Calculate optimal batch size based on available memory.
        
        Args:
            data_size: Size of each data item in bytes
            
        Returns:
            Optimal batch size
        """
        if not self.available:
            return 1000
        
        total_memory = torch.cuda.get_device_properties(0).total_memory
        available_memory = total_memory - torch.cuda.memory_allocated()
        
        # Use 80% of available memory
        usable_memory = int(available_memory * 0.8)
        
        # Calculate batch size
        batch_size = usable_memory // data_size
        
        # Round to nearest power of 2 for better performance
        batch_size = 2 ** int(np.log2(batch_size))
        
        return max(1000, min(batch_size, 1_000_000)) 