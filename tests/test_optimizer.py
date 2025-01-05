"""Tests for system optimization operations."""

import unittest
import pytest
import psutil
import os
from src.optimizer.system import SystemOptimizer
from src.optimizer.process import ProcessManager

class TestSystemOptimization(unittest.TestCase):
    """Test suite for system optimization."""
    
    def setUp(self):
        """Set up test environment."""
        self.sys_optimizer = SystemOptimizer()
        self.proc_manager = ProcessManager()
        
    def test_cpu_affinity(self):
        """Test CPU affinity optimization."""
        original_affinity = psutil.Process().cpu_affinity()
        self.sys_optimizer.optimize_cpu_affinity()
        new_affinity = psutil.Process().cpu_affinity()
        self.assertGreaterEqual(len(new_affinity), len(original_affinity))
        
    @pytest.mark.cuda
    def test_gpu_optimization(self):
        """Test GPU optimization settings."""
        try:
            import numba.cuda
            self.sys_optimizer.optimize_gpu_settings()
            self.assertTrue(os.environ.get('CUDA_VISIBLE_DEVICES'))
        except ImportError:
            pytest.skip("CUDA not available")
            
    def test_thread_management(self):
        """Test thread management."""
        num_threads = self.proc_manager.get_optimal_thread_count()
        self.assertGreater(num_threads, 0)
        self.assertLessEqual(num_threads, os.cpu_count() * 2)
        
    def test_memory_limits(self):
        """Test memory limit settings."""
        mem_limit = "16GB"
        self.sys_optimizer.set_memory_limit(mem_limit)
        current_limit = self.sys_optimizer.get_memory_limit()
        self.assertEqual(current_limit, mem_limit) 