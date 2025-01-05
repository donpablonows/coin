"""
Core cryptographic operations for Bitcoin address generation
"""

import numpy as np
from numba import jit, vectorize, prange
import hashlib
from fastecdsa.keys import get_public_key
from fastecdsa.curve import secp256k1

# Base58 encoding map
BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_MAP = {c: i for i, c in enumerate(BASE58_CHARS)}
BASE58_ARRAY = np.array([BASE58_MAP[c] for c in BASE58_CHARS], dtype=np.uint8)

@vectorize(["uint8[:](uint32)"], target="parallel", cache=True, fastmath=True)
def generate_random_bytes():
    """Generate random bytes using vectorized operations."""
    return np.random.bytes(32)

@jit(nopython=True, parallel=True, fastmath=True, cache=True)
def generate_private_keys(size):
    """Generate multiple private keys in parallel."""
    return np.array([generate_random_bytes() for _ in prange(size)])

@jit(nopython=True, fastmath=True, cache=True, inline="always")
def hash160(data):
    """Compute RIPEMD160(SHA256(data))."""
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()

@jit(nopython=True, fastmath=True, cache=True, inline="always")
def base58_encode(data):
    """Encode data in base58 format."""
    num = int.from_bytes(data, "big")
    result = np.empty(40, dtype=np.uint8)
    idx = 0
    while num:
        num, mod = divmod(num, 58)
        result[idx] = BASE58_ARRAY[mod]
        idx += 1
    return bytes(result[:idx][::-1])

@jit(nopython=True, fastmath=True, cache=True, inline="always")
def get_public_key_bytes(private_key):
    """Convert private key to public key bytes."""
    key = get_public_key(int.from_bytes(private_key, "big"), secp256k1)
    return b"\x04" + key.x.to_bytes(32, "big") + key.y.to_bytes(32, "big")

@jit(nopython=True, parallel=True, fastmath=True, cache=True)
def process_batch(batch, addresses, suffix_len):
    """Process a batch of private keys to find matching addresses."""
    results = []
    for i in prange(len(batch)):
        priv = batch[i]
        pub = get_public_key_bytes(priv)
        addr = base58_encode(b"\x00" + hash160(pub))
        if addr[-suffix_len:] in addresses:
            results.extend([priv, pub, addr])
    return results

def double_sha256(data):
    """Compute double SHA256 hash."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def create_wif(private_key):
    """Create Wallet Import Format from private key."""
    extended = b'\x80' + private_key
    with_checksum = extended + double_sha256(extended)[:4]
    return base58_encode(with_checksum) 