"""Tests for CUDA operations and optimizations."""

import unittest
import pytest
import torch
import numpy as np
from src.core.cuda import CUDAManager

class TestCUDAOperations(unittest.TestCase):
    """Test suite for CUDA operations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.cuda = CUDAManager()
        cls.cuda.setup()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        cls.cuda.cleanup()
    
    def test_cuda_availability(self):
        """Test CUDA availability detection."""
        self.assertEqual(
            self.cuda.available,
            torch.cuda.is_available()
        )
    
    @pytest.mark.skipif(not torch.cuda.is_available(),
                       reason="CUDA not available")
    def test_memory_management(self):
        """Test CUDA memory management."""
        # Allocate test tensor
        test_size = 1000000
        tensor = torch.zeros(test_size, device=self.cuda.device)
        
        # Check memory allocation
        self.assertGreater(self.cuda.memory_allocated, 0)
        
        # Clean up
        del tensor
        torch.cuda.empty_cache()
        
        # Check memory deallocation
        self.assertEqual(self.cuda.memory_allocated, 0)
    
    @pytest.mark.skipif(not torch.cuda.is_available(),
                       reason="CUDA not available")
    def test_kernel_launch_config(self):
        """Test kernel launch configuration optimization."""
        data_size = 1000000
        grid_size, block_size = self.cuda.optimize_kernel_launch(data_size)
        
        # Check grid size calculation
        self.assertEqual(
            grid_size,
            (data_size + block_size - 1) // block_size
        )
        
        # Check block size constraints
        max_threads = torch.cuda.get_device_properties(0).max_threads_per_block
        self.assertLessEqual(block_size, max_threads)
    
    @pytest.mark.skipif(not torch.cuda.is_available(),
                       reason="CUDA not available")
    def test_batch_size_optimization(self):
        """Test batch size optimization."""
        data_size = 1000  # bytes per item
        batch_size = self.cuda.get_optimal_batch_size(data_size)
        
        # Check batch size constraints
        self.assertGreaterEqual(batch_size, 1000)
        self.assertLessEqual(batch_size, 1_000_000)
        
        # Check if batch size is power of 2
        self.assertEqual(batch_size & (batch_size - 1), 0)
    
    @pytest.mark.skipif(not torch.cuda.is_available(),
                       reason="CUDA not available")
    def test_async_operations(self):
        """Test asynchronous CUDA operations."""
        test_size = 1000000
        
        # Create test data
        host_array = np.random.rand(test_size).astype(np.float32)
        device_array = torch.from_numpy(host_array).cuda()
        
        # Create events for timing
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        
        # Time asynchronous operation
        start.record()
        result = torch.sqrt(device_array)
        end.record()
        
        # Wait for operation to complete
        end.synchronize()
        
        # Check timing
        self.assertGreater(start.elapsed_time(end), 0)
        
        # Verify results
        np.testing.assert_array_almost_equal(
            result.cpu().numpy(),
            np.sqrt(host_array)
        )
    
    @pytest.mark.skipif(not torch.cuda.is_available(),
                       reason="CUDA not available")
    def test_memory_transfer(self):
        """Test optimized memory transfer."""
        test_size = 1000000
        
        # Create pinned memory
        host_array = torch.zeros(test_size, pin_memory=True)
        
        # Time transfer to device
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        
        start.record()
        device_array = host_array.cuda(non_blocking=True)
        end.record()
        end.synchronize()
        
        # Check transfer completed
        self.assertTrue(device_array.is_cuda)
        self.assertGreater(start.elapsed_time(end), 0) 