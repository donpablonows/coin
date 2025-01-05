"""
CUDA optimizations and GPU acceleration
"""

import torch
import numpy as np
from numba import cuda

# Enable all CUDA optimizations
def enable_cuda_optimizations():
    """Enable all available CUDA optimizations."""
    for key in dir(torch.backends.cuda):
        if not key.startswith('_'):
            setattr(torch.backends.cuda, key, True)

@cuda.jit(fastmath=True, parallel=True)
def generate_random_cuda(seed, output):
    """Generate random numbers using CUDA."""
    thread = cuda.grid(1)
    if thread < output.shape[0]:
        output[thread] = cuda.random.xoroshiro128p_uniform_float32(seed, thread)

def setup_cuda_device():
    """Setup and configure CUDA device."""
    if not torch.cuda.is_available():
        return False
    
    # Set device to GPU
    torch.cuda.set_device(0)
    
    # Configure memory allocation
    torch.cuda.empty_cache()
    torch.backends.cuda.max_memory_allocated = 0
    torch.backends.cuda.max_memory_cached = 0
    
    # Set memory allocator
    if hasattr(torch.cuda, 'caching_allocator_alloc'):
        torch.cuda.caching_allocator_alloc()
    
    return True

def optimize_cuda_settings():
    """Optimize CUDA settings for maximum performance."""
    if not torch.cuda.is_available():
        return
    
    # Set CUDA flags
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.enabled = True
    
    # Configure memory management
    torch.cuda.set_per_process_memory_fraction(0.95)
    
    # Enable tensor cores if available
    if torch.cuda.get_device_capability()[0] >= 7:
        torch.set_float32_matmul_precision('high')

def cleanup_cuda():
    """Clean up CUDA resources."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

class CUDAManager:
    """Manage CUDA resources and optimization."""
    
    def __init__(self):
        self.available = torch.cuda.is_available()
        self.device = torch.device("cuda" if self.available else "cpu")
        self.enabled = False
    
    def setup(self):
        """Setup CUDA environment."""
        if not self.available:
            return False
        
        enable_cuda_optimizations()
        setup_cuda_device()
        optimize_cuda_settings()
        self.enabled = True
        return True
    
    def cleanup(self):
        """Clean up CUDA resources."""
        if self.enabled:
            cleanup_cuda()
    
    def __enter__(self):
        """Context manager entry."""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
    
    @property
    def device_name(self):
        """Get CUDA device name."""
        return torch.cuda.get_device_name(0) if self.available else "CPU"
    
    @property
    def memory_allocated(self):
        """Get allocated memory in GB."""
        if not self.available:
            return 0
        return torch.cuda.memory_allocated() / 1024**3
    
    @property
    def memory_cached(self):
        """Get cached memory in GB."""
        if not self.available:
            return 0
        return torch.cuda.memory_cached() / 1024**3 