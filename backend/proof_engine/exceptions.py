"""Custom exceptions for proof generation module."""


class ProofGenerationError(Exception):
    """Base exception for proof generation errors."""

    pass


class FileHashError(ProofGenerationError):
    """Error computing file hash."""

    pass


class PresetNotFoundError(ProofGenerationError):
    """Requested preset not found in presets.yaml."""

    pass
