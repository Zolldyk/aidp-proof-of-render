"""Pydantic models for cryptographic proof data."""

from pydantic import BaseModel, Field


class ProofMetadata(BaseModel):
    """Metadata about the render process."""

    preset_name: str = Field(..., alias="presetName")
    resolution: str
    samples: int
    blender_version: str = Field(..., alias="blenderVersion")
    render_duration: float = Field(..., alias="renderDuration")

    model_config = {"populate_by_name": True}


class ProofData(BaseModel):
    """Cryptographic proof structure for render verification."""

    asset_hash: str = Field(..., alias="assetHash")
    scene_params_hash: str = Field(..., alias="sceneParamsHash")
    output_hash: str = Field(..., alias="outputHash")
    timestamp: str
    aidp_job_id: str = Field(..., alias="aidpJobId")
    metadata: ProofMetadata

    model_config = {"populate_by_name": True}
