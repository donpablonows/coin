"""Tests for cryptographic operations."""

import unittest
import pytest
from src.core.crypto import (
    generate_private_key,
    derive_public_key,
    generate_bitcoin_address
)

class TestCryptoOperations(unittest.TestCase):
    """Test suite for cryptographic operations."""
    
    def test_private_key_generation(self):
        """Test that private key generation produces valid keys."""
        private_key = generate_private_key()
        self.assertEqual(len(private_key), 32)  # 256 bits = 32 bytes
        
    def test_public_key_derivation(self):
        """Test public key derivation from private key."""
        private_key = generate_private_key()
        public_key = derive_public_key(private_key)
        self.assertEqual(len(public_key), 33)  # Compressed public key
        
    def test_address_generation(self):
        """Test Bitcoin address generation."""
        private_key = generate_private_key()
        address = generate_bitcoin_address(private_key)
        self.assertTrue(address.startswith('1'))  # Legacy address format
        self.assertEqual(len(address), 34)  # Standard Bitcoin address length

    @pytest.mark.cuda
    def test_cuda_acceleration(self):
        """Test CUDA-accelerated operations."""
        try:
            import numba.cuda
            self.assertTrue(numba.cuda.is_available())
        except ImportError:
            pytest.skip("CUDA not available") 