"""
HyperQuantum Bitcoin Address Generator - Main Entry Point
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .core.cuda import CUDAManager
from .core.crypto import process_batch, generate_private_keys, create_wif
from .database.manager import DatabaseManager
from .optimizer.system import SystemOptimizer
from .optimizer.process import ProcessManager, ThreadManager, set_process_signals

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HyperQuantum:
    """Main application class."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        database_url: Optional[str] = None
    ):
        self.config = config or {
            "suffix_len": 8,
            "thread_multiplier": 2048,
            "batch_size": 2**31,
            "buffer_size": 4096
        }
        
        self.database_url = database_url
        self.stop_requested = False
        
        # Initialize managers
        self.cuda = CUDAManager()
        self.system = SystemOptimizer(
            thread_multiplier=self.config["thread_multiplier"]
        )
        self.database = DatabaseManager(
            database_url=self.database_url
        )
        self.process_manager: Optional[ProcessManager] = None
    
    def setup(self) -> bool:
        """Initialize all components."""
        try:
            # Setup CUDA
            logger.info("Setting up CUDA...")
            self.cuda.setup()
            logger.info(f"Using device: {self.cuda.device_name}")
            
            # Optimize system
            logger.info("Optimizing system...")
            self.system.optimize()
            
            # Setup database
            logger.info("Setting up database...")
            if not self.database.setup(self.config["suffix_len"]):
                logger.error("Failed to setup database")
                return False
            
            logger.info(f"Loaded {self.database.size:,} addresses")
            return True
        
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def process_addresses(self, addresses: set, config: dict) -> None:
        """Process addresses in worker process."""
        try:
            with ThreadManager() as thread_manager:
                while not self.stop_requested:
                    # Generate private keys
                    private_keys = generate_private_keys(self.config["batch_size"])
                    
                    # Process in parallel
                    futures = [
                        thread_manager.submit(
                            process_batch,
                            batch,
                            addresses,
                            config["suffix_len"]
                        )
                        for batch in np.array_split(
                            private_keys,
                            thread_manager.num_threads
                        )
                    ]
                    
                    # Save results
                    for future in futures:
                        for i in range(0, len(future.result()), 3):
                            result = future.result()
                            self.save_result(
                                private_key=result[i],
                                public_key=result[i+1],
                                address=result[i+2]
                            )
        
        except Exception as e:
            logger.error(f"Worker process failed: {e}")
            self.stop_requested = True
    
    def save_result(
        self,
        private_key: bytes,
        public_key: bytes,
        address: bytes
    ) -> None:
        """Save found address to file."""
        try:
            with open("found.txt", "ab", buffering=self.config["buffer_size"]) as f:
                f.write(
                    f"\nPrivate Key (HEX): {private_key.hex()}\n"
                    f"Private Key (WIF): {create_wif(private_key)}\n"
                    f"Public Key: {public_key.hex()}\n"
                    f"Address: {address}\n"
                    f"{'-' * 50}\n".encode()
                )
        except IOError as e:
            logger.error(f"Failed to save result: {e}")
    
    def run(self) -> None:
        """Run the address generator."""
        try:
            # Setup signal handlers
            set_process_signals()
            
            # Initialize process manager
            self.process_manager = ProcessManager(
                worker_function=self.process_addresses,
                thread_multiplier=self.config["thread_multiplier"]
            )
            
            # Create and start workers
            self.process_manager.create_workers(
                self.database.addresses,
                self.config
            )
            self.process_manager.start_workers()
            
            # Monitor progress
            while not self.stop_requested:
                # Check for errors
                errors = self.process_manager.check_errors()
                if errors:
                    for worker_id, error in errors:
                        logger.error(f"Worker {worker_id} failed: {error}")
                    break
                
                # Update statistics
                logger.info(
                    f"Memory: {self.system.memory_usage:.2f} GB, "
                    f"CPU: {self.system.cpu_usage}%, "
                    f"GPU: {self.cuda.memory_allocated:.2f} GB"
                )
        
        except KeyboardInterrupt:
            logger.info("Stopping...")
        
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_requested = True
        
        if self.process_manager:
            self.process_manager.cleanup()
        
        self.cuda.cleanup()
        self.system.cleanup()
        self.database.cleanup()
        
        logger.info("Cleanup complete")

def main() -> int:
    """Main entry point."""
    try:
        app = HyperQuantum()
        if app.setup():
            app.run()
            return 0
        return 1
    
    except Exception as e:
        logger.error(f"Application failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 