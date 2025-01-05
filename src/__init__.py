"""
Coin (Crypto Optimization Interface Network)
Ultra-optimized Bitcoin address generator using CUDA and multi-threading.

This package provides high-performance cryptographic operations for Bitcoin
address generation, leveraging advanced parallel computing techniques and
hardware acceleration.
"""

__version__ = "1.0.0"
__author__ = "Coin Development Team"
__license__ = "MIT"
__copyright__ = "Copyright 2024 Coin Development Team"

import os
import sys
import platform
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("coin.log")
    ]
)

logger = logging.getLogger(__name__)

def get_system_info() -> Dict[str, Any]:
    """Get detailed system information."""
    return {
        'platform': platform.platform(),
        'python_version': sys.version,
        'processor': platform.processor(),
        'architecture': platform.architecture(),
        'cpu_count': os.cpu_count(),
        'cuda_available': _check_cuda_available()
    }

def _check_cuda_available() -> bool:
    """Check if CUDA is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

# Log system information
logger.info("Initializing Coin...")
for key, value in get_system_info().items():
    logger.info(f"{key}: {value}") 