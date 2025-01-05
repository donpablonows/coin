"""
Database management and operations
"""

import os
import gzip
import mmap
import requests
from pathlib import Path
from typing import Set, Optional
from tqdm import tqdm

class DatabaseManager:
    """Manage Bitcoin address database operations."""
    
    def __init__(
        self,
        database_url: str = "http://addresses.loyce.club/blockchair_bitcoin_addresses_and_balance_LATEST.tsv.gz",
        database_dir: str = "d",
        database_file: str = "a",
        chunk_size: int = 9**7,
        timeout: int = 60
    ):
        self.database_url = database_url
        self.database_dir = Path(database_dir)
        self.database_file = self.database_dir / database_file
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.addresses: Set[str] = set()
    
    def ensure_database_dir(self) -> None:
        """Create database directory if it doesn't exist."""
        self.database_dir.mkdir(exist_ok=True)
    
    def download_database(self) -> Optional[Path]:
        """Download the compressed database file."""
        self.ensure_database_dir()
        gz_file = self.database_file.with_suffix(".gz")
        
        if gz_file.exists():
            return gz_file
        
        try:
            response = requests.get(
                self.database_url,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            
            with tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc="Downloading database"
            ) as progress_bar:
                with open(gz_file, "wb", buffering=self.chunk_size) as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            progress_bar.update(len(chunk))
            
            return gz_file
        
        except (requests.RequestException, IOError) as e:
            print(f"Failed to download database: {e}")
            if gz_file.exists():
                gz_file.unlink()
            return None
    
    def extract_database(self, gz_file: Path) -> bool:
        """Extract the compressed database file."""
        try:
            with tqdm(
                desc="Extracting database",
                unit='B',
                unit_scale=True
            ) as progress_bar:
                with gzip.open(gz_file, 'rb') as gz_input:
                    with open(self.database_file, 'wb', buffering=self.chunk_size) as output:
                        while True:
                            chunk = gz_input.read(self.chunk_size)
                            if not chunk:
                                break
                            output.write(chunk)
                            progress_bar.update(len(chunk))
            
            # Remove compressed file after successful extraction
            gz_file.unlink()
            return True
        
        except IOError as e:
            print(f"Failed to extract database: {e}")
            return False
    
    def load_addresses(self, suffix_length: int = 8) -> bool:
        """Load addresses from database file."""
        if not self.database_file.exists():
            return False
        
        try:
            with open(self.database_file, "rb") as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                
                with tqdm(
                    desc="Loading addresses",
                    unit=' addresses',
                    unit_scale=True
                ) as progress_bar:
                    for line in iter(mm.readline, b""):
                        if line.startswith(b"1"):
                            addr = line.strip().decode()[-suffix_length:]
                            self.addresses.add(addr)
                            progress_bar.update(1)
                
                mm.close()
            return True
        
        except IOError as e:
            print(f"Failed to load addresses: {e}")
            return False
    
    def setup(self, suffix_length: int = 8) -> bool:
        """Complete database setup process."""
        # Check if database exists
        if not self.database_file.exists():
            # Download and extract if needed
            gz_file = self.download_database()
            if not gz_file or not self.extract_database(gz_file):
                return False
        
        # Load addresses
        return self.load_addresses(suffix_length)
    
    def cleanup(self) -> None:
        """Clean up database resources."""
        self.addresses.clear()
    
    def __enter__(self) -> 'DatabaseManager':
        """Context manager entry."""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()
    
    @property
    def size(self) -> int:
        """Get number of loaded addresses."""
        return len(self.addresses)
    
    @property
    def database_size(self) -> int:
        """Get database file size in bytes."""
        return self.database_file.stat().st_size if self.database_file.exists() else 0 