"""
Core provenance tracking utilities.

Provides git state capture, system info, and manifest generation
for scientific reproducibility across herbarium digitization tools.

These utilities are used by both extraction pipelines and review workflows
to ensure full audit trails and reproducibility.
"""

import hashlib
import json
import logging
import subprocess
from datetime import UTC, datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def capture_git_provenance(repo_root: Path | None = None) -> dict:
    """Capture comprehensive git repository state.

    Returns dict with git_commit, git_branch, git_dirty flags.
    Fails gracefully if git is unavailable.

    Args:
        repo_root: Path to repository root. Auto-detected if None.

    Returns:
        {
            "git_commit": "a1b2c3d4e5f6...",
            "git_commit_short": "a1b2c3d",
            "git_branch": "main",
            "git_dirty": false
        }
    """
    git_info = {}

    if repo_root is None:
        # Try to find repo root from current file location
        repo_root = Path(__file__).parent.parent.parent.parent

    try:
        # Capture commit hash (primary identifier)
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            git_info["git_commit"] = commit
            git_info["git_commit_short"] = commit[:7]

        # Capture branch (context)
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch != "HEAD":  # Not in detached HEAD state
                git_info["git_branch"] = branch

        # Flag uncommitted changes (critical for reproducibility!)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode == 0:
            git_info["git_dirty"] = bool(result.stdout.strip())
            if git_info["git_dirty"]:
                logger.warning(
                    "Processing with uncommitted changes! Consider committing for reproducibility."
                )

    except (subprocess.SubprocessError, FileNotFoundError):
        logger.debug("Git information not available")
        git_info["git_commit"] = "unknown"
        git_info["git_commit_short"] = "unknown"

    return git_info


def capture_system_info() -> dict:
    """Capture system environment information for reproducibility."""
    import platform
    import sys

    return {
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "hostname": platform.node(),
    }


def get_code_version(repo_root: Path | None = None) -> str:
    """Get current git commit hash for version tracking."""
    return capture_git_provenance(repo_root).get("git_commit_short", "unknown")


def get_content_hash(content: str) -> str:
    """Get SHA256 hash of content (e.g., prompt text) for version tracking."""
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def create_manifest(
    version: str,
    git_info: dict | None = None,
    system_info: dict | None = None,
    custom_metadata: dict | None = None,
) -> dict:
    """Create standardized manifest with provenance metadata.

    Args:
        version: Semantic version string (e.g., "1.0.0")
        git_info: Git provenance from capture_git_provenance() (auto-captured if None)
        system_info: System info from capture_system_info() (auto-captured if None)
        custom_metadata: Additional domain-specific metadata

    Returns:
        Standardized manifest dict

    Example:
        >>> manifest = create_manifest(
        ...     version="1.0.0",
        ...     custom_metadata={"specimen_count": 2885, "export_type": "DwC"}
        ... )
    """
    if git_info is None:
        git_info = capture_git_provenance()
    if system_info is None:
        system_info = capture_system_info()

    manifest = {
        "provenance": {
            "version": version,
            "timestamp": datetime.now(UTC).isoformat(),
            **git_info,
        },
        "system": system_info,
    }

    if custom_metadata:
        manifest.update(custom_metadata)

    return manifest


def save_manifest(manifest: dict, output_path: Path) -> None:
    """Save manifest to JSON file.

    Args:
        manifest: Manifest dict from create_manifest()
        output_path: Path to write manifest.json
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest written to {output_path}")


def validate_reproducibility(manifest_path: Path) -> tuple[bool, list[str]]:
    """Validate that current environment matches manifest provenance.

    Checks if current git state matches manifest for reproducibility.

    Args:
        manifest_path: Path to manifest.json

    Returns:
        (is_valid, warnings) tuple
    """
    import sys

    warnings = []

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        return False, [f"Could not load manifest: {e}"]

    # Check git commit
    current_git = capture_git_provenance()
    manifest_commit = manifest.get("provenance", {}).get("git_commit")

    if manifest_commit and manifest_commit != "unknown":
        if current_git.get("git_commit") != manifest_commit:
            warnings.append(
                f"Git commit mismatch: "
                f"current={current_git.get('git_commit', 'unknown')[:7]}, "
                f"manifest={manifest_commit[:7]}"
            )

    # Check dirty flag
    if current_git.get("git_dirty"):
        warnings.append("Uncommitted changes present in current working tree")

    manifest_dirty = manifest.get("provenance", {}).get("git_dirty")
    if manifest_dirty:
        warnings.append("Original export had uncommitted changes (git_dirty=true)")

    # Check Python version
    current_python = sys.version.split()[0]
    manifest_python = manifest.get("system", {}).get("python_version")
    if manifest_python and manifest_python != current_python:
        warnings.append(
            f"Python version mismatch: current={current_python}, manifest={manifest_python}"
        )

    is_valid = len(warnings) == 0
    return is_valid, warnings


def track_provenance(version: str):
    """Decorator to automatically track provenance for processing functions.

    Captures git and system info at function entry, attaches to function object.

    Args:
        version: Semantic version string

    Example:
        @track_provenance(version="1.0.0")
        def process_specimens(input_dir: Path, output_dir: Path):
            # Git info captured automatically at function entry
            # Accessible via function.git_info attribute
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Capture provenance at entry
            git_info = capture_git_provenance()
            system_info = capture_system_info()

            # Attach to function for access
            func.git_info = git_info
            func.system_info = system_info

            # Execute function
            result = func(*args, **kwargs)

            return result

        return wrapper

    return decorator


__all__ = [
    "capture_git_provenance",
    "capture_system_info",
    "get_code_version",
    "get_content_hash",
    "create_manifest",
    "save_manifest",
    "validate_reproducibility",
    "track_provenance",
]
