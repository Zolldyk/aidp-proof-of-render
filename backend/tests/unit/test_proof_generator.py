"""Unit tests for ProofGenerator class."""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from proof_engine import FileHashError, PresetNotFoundError, ProofGenerator


@pytest.fixture
def generator() -> ProofGenerator:
    """Create a ProofGenerator instance."""
    return ProofGenerator()


@pytest.fixture
def temp_file() -> str:
    """Create a temporary file with known content."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
        f.write(b"test content for hashing")
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def temp_asset_file() -> str:
    """Create a temporary asset file simulating a .gltf."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".gltf") as f:
        f.write('{"asset": {"version": "2.0"}, "scenes": []}')
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def temp_output_file() -> str:
    """Create a temporary output file simulating a rendered PNG."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".png") as f:
        # Write fake PNG header + content
        f.write(b"\x89PNG\r\n\x1a\n" + os.urandom(1024))
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


class TestComputeFileHash:
    """Tests for compute_file_hash method."""

    def test_compute_file_hash_identical_files_same_hash(
        self, generator: ProofGenerator
    ) -> None:
        """Identical files produce identical hashes."""
        content = b"identical content for testing hash consistency"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f2:
            f2.write(content)
            path2 = f2.name

        try:
            hash1 = generator.compute_file_hash(path1)
            hash2 = generator.compute_file_hash(path2)
            assert hash1 == hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_compute_file_hash_same_file_twice_same_hash(
        self, generator: ProofGenerator, temp_file: str
    ) -> None:
        """Hashing the same file twice produces identical hashes."""
        hash1 = generator.compute_file_hash(temp_file)
        hash2 = generator.compute_file_hash(temp_file)
        assert hash1 == hash2

    def test_compute_file_hash_different_files_different_hash(
        self, generator: ProofGenerator
    ) -> None:
        """Different files produce different hashes."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f1:
            f1.write(b"content A")
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f2:
            f2.write(b"content B")
            path2 = f2.name

        try:
            hash1 = generator.compute_file_hash(path1)
            hash2 = generator.compute_file_hash(path2)
            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_compute_file_hash_format_is_64_char_hex(
        self, generator: ProofGenerator, temp_file: str
    ) -> None:
        """Hash is 64-character lowercase hexadecimal string."""
        file_hash = generator.compute_file_hash(temp_file)
        assert len(file_hash) == 64
        assert re.match(r"^[a-f0-9]{64}$", file_hash) is not None

    def test_compute_file_hash_missing_file_raises_error(
        self, generator: ProofGenerator
    ) -> None:
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            generator.compute_file_hash("/nonexistent/path/file.bin")

    def test_compute_file_hash_empty_file(self, generator: ProofGenerator) -> None:
        """Empty file produces valid hash."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            temp_path = f.name

        try:
            file_hash = generator.compute_file_hash(temp_path)
            assert len(file_hash) == 64
            # SHA-256 of empty file is known
            assert (
                file_hash
                == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )
        finally:
            os.unlink(temp_path)


class TestComputeSceneHash:
    """Tests for compute_scene_hash method."""

    def test_compute_scene_hash_deterministic(self, generator: ProofGenerator) -> None:
        """Same config dictionary always produces same hash."""
        config = {"samples": 128, "resolution": "1024x1024", "preset": "studio"}

        hash1 = generator.compute_scene_hash(config)
        hash2 = generator.compute_scene_hash(config)
        hash3 = generator.compute_scene_hash(config)

        assert hash1 == hash2 == hash3

    def test_compute_scene_hash_key_order_independence(
        self, generator: ProofGenerator
    ) -> None:
        """Different key insertion order produces same hash."""
        config1 = {"a": 1, "b": 2, "c": 3}
        config2 = {"c": 3, "a": 1, "b": 2}
        config3 = {"b": 2, "c": 3, "a": 1}

        hash1 = generator.compute_scene_hash(config1)
        hash2 = generator.compute_scene_hash(config2)
        hash3 = generator.compute_scene_hash(config3)

        assert hash1 == hash2 == hash3

    def test_compute_scene_hash_nested_dict_deterministic(
        self, generator: ProofGenerator
    ) -> None:
        """Nested dictionaries are also deterministic."""
        config = {
            "camera": {"position": {"x": 7, "y": -7, "z": 5}},
            "lights": [{"type": "AREA", "energy": 1000}],
            "samples": 128,
        }

        hash1 = generator.compute_scene_hash(config)
        hash2 = generator.compute_scene_hash(config)

        assert hash1 == hash2

    def test_compute_scene_hash_format_is_64_char_hex(
        self, generator: ProofGenerator
    ) -> None:
        """Scene hash is 64-character lowercase hexadecimal string."""
        config = {"test": "value"}
        scene_hash = generator.compute_scene_hash(config)

        assert len(scene_hash) == 64
        assert re.match(r"^[a-f0-9]{64}$", scene_hash) is not None


class TestLoadPresetConfig:
    """Tests for _load_preset_config method."""

    def test_load_preset_config_studio(self, generator: ProofGenerator) -> None:
        """Studio preset loads successfully."""
        config = generator._load_preset_config("studio")
        assert config["name"] == "studio"
        assert config["samples"] == 128
        assert "lights" in config

    def test_load_preset_config_sunset(self, generator: ProofGenerator) -> None:
        """Sunset preset loads successfully."""
        config = generator._load_preset_config("sunset")
        assert config["name"] == "sunset"
        assert config["samples"] == 128

    def test_load_preset_config_dramatic(self, generator: ProofGenerator) -> None:
        """Dramatic preset loads successfully."""
        config = generator._load_preset_config("dramatic")
        assert config["name"] == "dramatic"
        assert config["samples"] == 128

    def test_load_preset_config_invalid_raises_error(
        self, generator: ProofGenerator
    ) -> None:
        """Invalid preset name raises PresetNotFoundError."""
        with pytest.raises(PresetNotFoundError):
            generator._load_preset_config("nonexistent")


class TestGenerateProof:
    """Tests for generate_proof method."""

    def test_generate_proof_returns_complete_structure(
        self,
        generator: ProofGenerator,
        temp_asset_file: str,
        temp_output_file: str,
    ) -> None:
        """Generated proof contains all required fields."""
        proof = generator.generate_proof(
            job_id="test-job-123",
            asset_path=temp_asset_file,
            preset_name="studio",
            output_path=temp_output_file,
            aidp_job_id="aidp-456",
        )

        assert "assetHash" in proof
        assert "sceneParamsHash" in proof
        assert "outputHash" in proof
        assert "timestamp" in proof
        assert "aidpJobId" in proof
        assert "metadata" in proof

    def test_generate_proof_metadata_contains_required_fields(
        self,
        generator: ProofGenerator,
        temp_asset_file: str,
        temp_output_file: str,
    ) -> None:
        """Proof metadata contains all required fields."""
        proof = generator.generate_proof(
            job_id="test-job-123",
            asset_path=temp_asset_file,
            preset_name="studio",
            output_path=temp_output_file,
            aidp_job_id="aidp-456",
            blender_version="3.6.5",
            render_duration=25.5,
        )

        metadata = proof["metadata"]
        assert metadata["presetName"] == "studio"
        assert metadata["resolution"] == "1024x1024"
        assert metadata["samples"] == 128
        assert metadata["blenderVersion"] == "3.6.5"
        assert metadata["renderDuration"] == 25.5

    def test_generate_proof_timestamp_is_iso8601(
        self,
        generator: ProofGenerator,
        temp_asset_file: str,
        temp_output_file: str,
    ) -> None:
        """Proof timestamp is valid ISO8601 format."""
        proof = generator.generate_proof(
            job_id="test-job-123",
            asset_path=temp_asset_file,
            preset_name="studio",
            output_path=temp_output_file,
            aidp_job_id="aidp-456",
        )

        timestamp = proof["timestamp"]
        assert timestamp.endswith("Z")
        # Parse without the Z suffix
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_generate_proof_hashes_are_valid_format(
        self,
        generator: ProofGenerator,
        temp_asset_file: str,
        temp_output_file: str,
    ) -> None:
        """All hashes in proof are 64-char hex strings."""
        proof = generator.generate_proof(
            job_id="test-job-123",
            asset_path=temp_asset_file,
            preset_name="studio",
            output_path=temp_output_file,
            aidp_job_id="aidp-456",
        )

        for hash_field in ["assetHash", "sceneParamsHash", "outputHash"]:
            assert len(proof[hash_field]) == 64
            assert re.match(r"^[a-f0-9]{64}$", proof[hash_field]) is not None

    @pytest.mark.parametrize("preset_name", ["studio", "sunset", "dramatic"])
    def test_generate_proof_with_all_presets(
        self,
        generator: ProofGenerator,
        temp_asset_file: str,
        temp_output_file: str,
        preset_name: str,
    ) -> None:
        """All presets generate valid proofs."""
        proof = generator.generate_proof(
            job_id=f"test-{preset_name}",
            asset_path=temp_asset_file,
            preset_name=preset_name,
            output_path=temp_output_file,
            aidp_job_id=f"aidp-{preset_name}",
        )

        assert proof["metadata"]["presetName"] == preset_name
        assert proof["metadata"]["samples"] == 128

    def test_generate_proof_invalid_preset_raises_error(
        self,
        generator: ProofGenerator,
        temp_asset_file: str,
        temp_output_file: str,
    ) -> None:
        """Invalid preset name raises PresetNotFoundError."""
        with pytest.raises(PresetNotFoundError):
            generator.generate_proof(
                job_id="test-job",
                asset_path=temp_asset_file,
                preset_name="nonexistent",
                output_path=temp_output_file,
                aidp_job_id="aidp-123",
            )

    def test_generate_proof_missing_asset_raises_error(
        self,
        generator: ProofGenerator,
        temp_output_file: str,
    ) -> None:
        """Missing asset file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            generator.generate_proof(
                job_id="test-job",
                asset_path="/nonexistent/asset.gltf",
                preset_name="studio",
                output_path=temp_output_file,
                aidp_job_id="aidp-123",
            )

    def test_generate_proof_missing_output_raises_error(
        self,
        generator: ProofGenerator,
        temp_asset_file: str,
    ) -> None:
        """Missing output file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            generator.generate_proof(
                job_id="test-job",
                asset_path=temp_asset_file,
                preset_name="studio",
                output_path="/nonexistent/render.png",
                aidp_job_id="aidp-123",
            )


class TestSaveProof:
    """Tests for save_proof method."""

    def test_save_proof_creates_directory(self, generator: ProofGenerator) -> None:
        """save_proof creates directory if it doesn't exist."""
        job_id = f"test-{os.urandom(4).hex()}"
        proof = {"test": "data"}
        output_dir = Path("/tmp/outputs") / job_id

        try:
            proof_path = generator.save_proof(job_id, proof)
            assert Path(proof_path).exists()
            assert output_dir.exists()
        finally:
            if output_dir.exists():
                for f in output_dir.iterdir():
                    f.unlink()
                output_dir.rmdir()

    def test_save_proof_file_is_valid_json(self, generator: ProofGenerator) -> None:
        """Saved proof.json is valid JSON with correct content."""
        job_id = f"test-{os.urandom(4).hex()}"
        proof = {"assetHash": "abc123", "metadata": {"samples": 128}}
        output_dir = Path("/tmp/outputs") / job_id

        try:
            proof_path = generator.save_proof(job_id, proof)
            with open(proof_path, "r") as f:
                loaded = json.load(f)
            assert loaded == proof
        finally:
            if output_dir.exists():
                for f in output_dir.iterdir():
                    f.unlink()
                output_dir.rmdir()

    def test_save_proof_uses_pretty_formatting(
        self, generator: ProofGenerator
    ) -> None:
        """Saved proof.json uses indent=2 formatting."""
        job_id = f"test-{os.urandom(4).hex()}"
        proof = {"key": "value"}
        output_dir = Path("/tmp/outputs") / job_id

        try:
            proof_path = generator.save_proof(job_id, proof)
            with open(proof_path, "r") as f:
                content = f.read()
            # Pretty-printed JSON should have newlines and indentation
            assert "\n" in content
            assert "  " in content
        finally:
            if output_dir.exists():
                for f in output_dir.iterdir():
                    f.unlink()
                output_dir.rmdir()

    def test_save_proof_returns_correct_path(self, generator: ProofGenerator) -> None:
        """save_proof returns the correct file path."""
        job_id = f"test-{os.urandom(4).hex()}"
        proof = {"test": "data"}
        output_dir = Path("/tmp/outputs") / job_id

        try:
            proof_path = generator.save_proof(job_id, proof)
            expected = str(output_dir / "proof.json")
            assert proof_path == expected
        finally:
            if output_dir.exists():
                for f in output_dir.iterdir():
                    f.unlink()
                output_dir.rmdir()
