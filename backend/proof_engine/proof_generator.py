"""Cryptographic proof generation module for render verification."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .exceptions import FileHashError, PresetNotFoundError

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8192


class ProofGenerator:
    """Generates cryptographic proofs for rendered outputs."""

    def __init__(self) -> None:
        """Initialize the ProofGenerator."""
        self._presets_cache: dict[str, dict[str, Any]] | None = None

    def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of a file, returning 64-char hex digest.

        Args:
            file_path: Path to the file to hash.

        Returns:
            64-character lowercase hexadecimal SHA-256 digest.

        Raises:
            FileNotFoundError: If the file does not exist.
            FileHashError: If there's an error reading the file.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            sha256 = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except PermissionError as e:
            logger.error(f"Permission denied reading file: {file_path}")
            raise FileHashError(f"Permission denied reading file: {file_path}") from e
        except IOError as e:
            logger.error(f"IO error reading file {file_path}: {e}")
            raise FileHashError(f"Error reading file: {file_path}") from e

    def compute_scene_hash(self, preset_config: dict[str, Any]) -> str:
        """Compute SHA-256 hash of preset config with deterministic JSON serialization.

        Args:
            preset_config: Dictionary containing preset configuration.

        Returns:
            64-character lowercase hexadecimal SHA-256 digest.
        """
        json_str = json.dumps(preset_config, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _load_preset_config(self, preset_name: str) -> dict[str, Any]:
        """Load preset configuration from presets.yaml.

        Args:
            preset_name: Name of the preset to load.

        Returns:
            Preset configuration dictionary.

        Raises:
            PresetNotFoundError: If the preset name is not found.
            FileHashError: If presets.yaml cannot be read.
        """
        presets_path = Path(__file__).parent.parent / "render_engine" / "presets.yaml"

        try:
            with open(presets_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError as e:
            logger.error(f"Presets file not found: {presets_path}")
            raise FileHashError(f"Presets file not found: {presets_path}") from e
        except yaml.YAMLError as e:
            logger.error(f"Error parsing presets.yaml: {e}")
            raise FileHashError(f"Error parsing presets.yaml: {e}") from e
        except IOError as e:
            logger.error(f"Error reading presets.yaml: {e}")
            raise FileHashError(f"Error reading presets.yaml: {e}") from e

        for preset in data.get("presets", []):
            if preset.get("name") == preset_name:
                return preset

        raise PresetNotFoundError(f"Unknown preset: {preset_name}")

    def generate_proof(
        self,
        job_id: str,
        asset_path: str,
        preset_name: str,
        output_path: str,
        aidp_job_id: str,
        blender_version: str = "3.6.5",
        render_duration: float = 0.0,
    ) -> dict[str, Any]:
        """Generate cryptographic proof structure for a completed render.

        Args:
            job_id: Unique identifier for the render job.
            asset_path: Path to the original .gltf asset file.
            preset_name: Name of the scene preset used.
            output_path: Path to the rendered PNG output.
            aidp_job_id: AIDP network job ID.
            blender_version: Version of Blender used for rendering.
            render_duration: Time taken to render in seconds.

        Returns:
            Dictionary containing the complete proof structure.

        Raises:
            FileNotFoundError: If asset or output file doesn't exist.
            FileHashError: If there's an error computing hashes.
            PresetNotFoundError: If preset name is invalid.
        """
        asset_hash = self.compute_file_hash(asset_path)
        preset_config = self._load_preset_config(preset_name)
        scene_params_hash = self.compute_scene_hash(preset_config)
        output_hash = self.compute_file_hash(output_path)
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        samples = preset_config.get("samples", 128)

        proof = {
            "assetHash": asset_hash,
            "sceneParamsHash": scene_params_hash,
            "outputHash": output_hash,
            "timestamp": timestamp,
            "aidpJobId": aidp_job_id,
            "metadata": {
                "presetName": preset_name,
                "resolution": "1024x1024",
                "samples": samples,
                "blenderVersion": blender_version,
                "renderDuration": render_duration,
            },
        }

        logger.info(f"Generated proof for job {job_id}")
        return proof

    def save_proof(self, job_id: str, proof: dict[str, Any]) -> str:
        """Save proof.json to output directory with pretty formatting.

        Args:
            job_id: Unique identifier for the render job.
            proof: Proof dictionary to save.

        Returns:
            Path to the saved proof.json file.

        Raises:
            IOError: If there's an error writing the file.
        """
        output_dir = Path("/tmp/outputs") / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        proof_path = output_dir / "proof.json"

        try:
            with open(proof_path, "w") as f:
                json.dump(proof, f, indent=2)
            logger.info(f"Saved proof to {proof_path}")
            return str(proof_path)
        except IOError as e:
            logger.error(f"Error saving proof to {proof_path}: {e}")
            raise
