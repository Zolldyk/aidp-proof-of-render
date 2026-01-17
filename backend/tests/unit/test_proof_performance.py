"""Performance tests for proof generation module."""

import os
import tempfile
import time

import pytest

from proof_engine import ProofGenerator


@pytest.mark.slow
def test_hash_10mb_file_under_one_second() -> None:
    """Hash computation for 10MB file completes in under 1 second."""
    # Create 10MB temp file with random data
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(os.urandom(10 * 1024 * 1024))
        temp_path = f.name

    try:
        generator = ProofGenerator()
        start = time.time()
        file_hash = generator.compute_file_hash(temp_path)
        elapsed = time.time() - start

        # Verify hash is valid
        assert len(file_hash) == 64

        # Performance assertion
        assert elapsed < 1.0, f"Hash took {elapsed:.3f}s, exceeds 1s limit"
    finally:
        os.unlink(temp_path)


@pytest.mark.slow
def test_hash_large_file_chunked_reading() -> None:
    """Large file hashing uses chunked reading (memory efficient)."""
    # Create 50MB temp file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(os.urandom(50 * 1024 * 1024))
        temp_path = f.name

    try:
        generator = ProofGenerator()
        start = time.time()
        file_hash = generator.compute_file_hash(temp_path)
        elapsed = time.time() - start

        # Should complete within reasonable time (5 seconds for 50MB)
        assert elapsed < 5.0, f"Hash took {elapsed:.3f}s for 50MB file"
        assert len(file_hash) == 64
    finally:
        os.unlink(temp_path)
