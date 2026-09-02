"""StructureLab_CFS package.

M6 provides generic immutable trace/result infrastructure, while member design
calculations, AISI applicability, EWM, DSM, and pyCUFSM remain absent.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("structurelab-cfs")
except PackageNotFoundError:  # Allows source-tree inspection before installation.
    __version__ = "0+unknown"

__all__ = ["__version__"]
