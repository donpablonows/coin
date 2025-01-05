"""
High-performance database management for Bitcoin addresses.
Uses memory mapping and optimized data structures for maximum efficiency.
"""

import os
import gzip
import mmap
import shutil
import threading
from pathlib import Path
from typing import Set, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from tqdm import tqdm
import requests

class DatabaseManager:
    """Optimized Bitcoin address database manager."""
    
    def __init__(
        self,
        database_url: str = "http://addresses.loyce.club/blockchair_bitcoin_addresses_and_balance_LATEST.tsv.gz",
        database_dir: str = "database",
        database_file: str = "addresses.db",
        chunk_size: int = 2**20,  # 1MB chunks
        timeout: int = 60,
        max_workers: Optional[int] = None
    ):
        self.database_url = database_url
        self.database_dir = Path(database_dir)
        self.database_file = self.database_dir / database_file
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) * 2)
        
        # Use NumPy array for faster lookups
        self.addresses = np.array([], dtype=np.str_)
        self._mmap: Optional[mmap.mmap] = None
        self._lock = threading.RLock()
        self._executor: Optional[ThreadPoolExecutor] = None
    
    def ensure_database_dir(self) -> None:
        """Create database directory if it doesn't exist."""
        self.database_dir.mkdir(parents=True, exist_ok=True)
    
    def download_database(self) -> Optional[Path]:
        """Download database with parallel processing and resume capability."""
        self.ensure_database_dir()
        gz_file = self.database_file.with_suffix(".gz")
        
        if gz_file.exists():
            return gz_file
        
        try:
            # Get file size
            response = requests.head(self.database_url, timeout=self.timeout)
            total_size = int(response.headers.get("content-length", 0))
            
            # Calculate chunk ranges for parallel download
            chunk_starts = range(0, total_size, self.chunk_size)
            chunk_ends = [min(start + self.chunk_size - 1, total_size) 
                         for start in chunk_starts]
            
            # Download chunks in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for start, end in zip(chunk_starts, chunk_ends):
                    futures.append(executor.submit(
                        self._download_chunk,
                        start, end, gz_file
                    ))
                
                # Show progress
                with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                    for future in futures:
                        chunk_size = future.result()
                        if chunk_size is None:
                            return None
                        pbar.update(chunk_size)
            
            return gz_file
            
        except Exception as e:
            print(f"Download failed: {e}")
            if gz_file.exists():
                gz_file.unlink()
            return None
    
    def _download_chunk(
        self,
        start: int,
        end: int,
        gz_file: Path
    ) -> Optional[int]:
        """Download a specific chunk of the database."""
        headers = {"Range": f"bytes={start}-{end}"}
        try:
            response = requests.get(
                self.database_url,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            chunk = response.content
            with self._lock:
                with open(gz_file, "ab") as f:
                    f.seek(start)
                    f.write(chunk)
            
            return len(chunk)
            
        except Exception as e:
            print(f"Chunk download failed: {e}")
            return None
    
    def extract_database(self, gz_file: Path) -> bool:
        """Extract database with parallel processing."""
        try:
            # Create temporary directory for chunks
            temp_dir = self.database_dir / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Extract chunks in parallel
            with gzip.open(gz_file, 'rb') as gz_input:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = []
                    chunk_num = 0
                    
                    while True:
                        chunk = gz_input.read(self.chunk_size)
                        if not chunk:
                            break
                        
                        chunk_file = temp_dir / f"chunk_{chunk_num}"
                        futures.append(executor.submit(
                            self._write_chunk,
                            chunk_file,
                            chunk
                        ))
                        chunk_num += 1
                    
                    # Show progress
                    with tqdm(total=chunk_num, desc="Extracting") as pbar:
                        for future in futures:
                            if not future.result():
                                return False
                            pbar.update(1)
            
            # Combine chunks
            with open(self.database_file, 'wb') as output:
                for i in range(chunk_num):
                    chunk_file = temp_dir / f"chunk_{i}"
                    shutil.copyfileobj(open(chunk_file, 'rb'), output)
                    chunk_file.unlink()
            
            # Cleanup
            temp_dir.rmdir()
            gz_file.unlink()
            return True
            
        except Exception as e:
            print(f"Extraction failed: {e}")
            return False
    
    def _write_chunk(self, chunk_file: Path, data: bytes) -> bool:
        """Write a chunk to temporary file."""
        try:
            with open(chunk_file, 'wb') as f:
                f.write(data)
            return True
        except Exception:
            return False
    
    def load_addresses(self, suffix_length: int = 8) -> bool:
        """Load addresses using memory mapping and parallel processing."""
        if not self.database_file.exists():
            return False
        
        try:
            # Memory map the file
            with open(self.database_file, "rb") as f:
                self._mmap = mmap.mmap(
                    f.fileno(), 0,
                    access=mmap.ACCESS_READ
                )
            
            # Process file in parallel
            addresses = set()
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                
                # Split file into chunks
                chunk_size = self._mmap.size() // self.max_workers
                for i in range(self.max_workers):
                    start = i * chunk_size
                    end = start + chunk_size if i < self.max_workers - 1 else self._mmap.size()
                    futures.append(executor.submit(
                        self._process_chunk,
                        start, end, suffix_length
                    ))
                
                # Show progress
                total_size = self._mmap.size()
                with tqdm(total=total_size, desc="Loading addresses") as pbar:
                    for future in futures:
                        chunk_addresses, processed_size = future.result()
                        addresses.update(chunk_addresses)
                        pbar.update(processed_size)
            
            # Convert to NumPy array for faster lookups
            self.addresses = np.array(list(addresses), dtype=np.str_)
            return True
            
        except Exception as e:
            print(f"Loading failed: {e}")
            return False
    
    def _process_chunk(
        self,
        start: int,
        end: int,
        suffix_length: int
    ) -> tuple[set, int]:
        """Process a chunk of the database file."""
        addresses = set()
        current_pos = start
        
        # Find start of next line
        if start > 0:
            self._mmap.seek(start - 1)
            while current_pos < end:
                if self._mmap.read(1) == b'\n':
                    break
                current_pos += 1
        
        # Process lines
        self._mmap.seek(current_pos)
        while current_pos < end:
            line = self._mmap.readline()
            if not line:
                break
            
            current_pos = self._mmap.tell()
            if line.startswith(b"1"):
                addr = line.strip().decode()[-suffix_length:]
                addresses.add(addr)
        
        return addresses, current_pos - start
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        self.addresses = np.array([], dtype=np.str_)
    
    def __enter__(self) -> 'DatabaseManager':
        """Context manager entry."""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()
    
    def setup(self) -> bool:
        """Complete database setup."""
        if not self.database_file.exists():
            gz_file = self.download_database()
            if not gz_file or not self.extract_database(gz_file):
                return False
        return self.load_addresses()
    
    @property
    def size(self) -> int:
        """Get number of loaded addresses."""
        return len(self.addresses)
    
    @property
    def database_size(self) -> int:
        """Get database file size in bytes."""
        return self.database_file.stat().st_size if self.database_file.exists() else 0
    
    def address_exists(self, address: str) -> bool:
        """Check if address exists using optimized NumPy search."""
        return address in self.addresses  # NumPy uses optimized search 