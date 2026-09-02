"""Development-time discovery and fingerprint validation for standard sources."""

from hashlib import sha256
from pathlib import Path, PurePosixPath

from cfs_design.core.exceptions import StandardSourceError

from .sources import STANDARD_SOURCE_REGISTRY, StandardSourceRegistry


_PRIMARY_DIRECTORY = PurePosixPath("references/standards/AISI_S100-24")


def select_primary_standard_path(
    repository_relative_pdf_paths: tuple[str, ...],
) -> str:
    """Require exactly one PDF below the authoritative S100-24 directory."""

    candidates = tuple(
        path
        for path in repository_relative_pdf_paths
        if PurePosixPath(path).parent == _PRIMARY_DIRECTORY
    )
    if not candidates:
        raise StandardSourceError(
            "No S100-24 primary PDF was found under "
            "references/standards/AISI_S100-24"
        )
    if len(candidates) != 1:
        listed = ", ".join(sorted(candidates))
        raise StandardSourceError(
            f"Ambiguous S100-24 primary source; found {len(candidates)} PDFs: "
            f"{listed}"
        )
    return candidates[0]


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_standard_sources(
    repository_root: str | Path,
) -> StandardSourceRegistry:
    """Discover all local PDFs and verify them against the M7 source registry."""

    root = Path(repository_root).resolve()
    standards_root = root / "references" / "standards"
    if not standards_root.is_dir():
        raise StandardSourceError(
            f"Standards directory does not exist: {standards_root}"
        )
    observed_paths = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in standards_root.rglob("*.pdf")
            if path.is_file()
        )
    )
    primary_path = select_primary_standard_path(observed_paths)
    if primary_path != STANDARD_SOURCE_REGISTRY.primary.repository_relative_path:
        raise StandardSourceError(
            "The discovered S100-24 PDF is not the registered primary source: "
            f"{primary_path}"
        )

    registered_paths = {
        item.repository_relative_path for item in STANDARD_SOURCE_REGISTRY.documents
    }
    observed_set = set(observed_paths)
    missing = sorted(registered_paths - observed_set)
    unexpected = sorted(observed_set - registered_paths)
    if missing:
        raise StandardSourceError(
            "Registered standard documents are missing: " + ", ".join(missing)
        )
    if unexpected:
        raise StandardSourceError(
            "Unregistered standard PDFs require an explicit authority role: "
            + ", ".join(unexpected)
        )

    for document in STANDARD_SOURCE_REGISTRY.documents:
        actual = _file_sha256(root / document.repository_relative_path)
        if actual != document.sha256:
            raise StandardSourceError(
                f"SHA-256 mismatch for {document.source_id}: expected "
                f"{document.sha256}, observed {actual}"
            )
    return STANDARD_SOURCE_REGISTRY


__all__ = ["select_primary_standard_path", "validate_standard_sources"]
