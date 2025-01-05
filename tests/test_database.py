"""Tests for database operations."""

import unittest
import tempfile
import os
from src.database.manager import DatabaseManager

class TestDatabaseOperations(unittest.TestCase):
    """Test suite for database operations."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_manager = DatabaseManager(self.temp_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        self.db_manager.close()
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)
        
    def test_database_initialization(self):
        """Test database initialization."""
        self.assertTrue(os.path.exists(self.db_manager.db_path))
        
    def test_address_storage(self):
        """Test storing and retrieving addresses."""
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        self.db_manager.store_address(test_address)
        self.assertTrue(self.db_manager.address_exists(test_address))
        
    def test_memory_mapping(self):
        """Test memory-mapped file operations."""
        large_dataset = ["1" + "A" * 32 for _ in range(1000)]
        self.db_manager.store_bulk_addresses(large_dataset)
        self.assertTrue(all(self.db_manager.address_exists(addr) 
                          for addr in large_dataset[:10])) 