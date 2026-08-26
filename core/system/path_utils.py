import os
from typing import Optional

def normalize_path_cross_platform(p: Optional[str]) -> str:
    """Normalizes a filesystem path for cross-platform comparison.
    
    Handles:
    - Case sensitivity (Windows vs POSIX) via os.path.normcase
    - Slash direction consistency
    - Absolute and real path resolution (symlinks / NTFS junctions)
    - UNC network paths (\\\\server\\share)
    """
    if not p or not isinstance(p, str):
        return ""
    
    p_clean = p.strip()
    if not p_clean:
        return ""

    try:
        abs_p = os.path.abspath(os.path.realpath(p_clean))
    except (ValueError, OSError):
        abs_p = os.path.abspath(p_clean)

    norm = os.path.normcase(os.path.normpath(abs_p))
    if os.name == 'nt':
        norm = norm.replace("/", "\\")
    return norm

def paths_are_equivalent(p1: Optional[str], p2: Optional[str]) -> bool:
    """Checks if two paths point to the exact same directory or file."""
    norm1 = normalize_path_cross_platform(p1)
    norm2 = normalize_path_cross_platform(p2)
    if not norm1 or not norm2:
        return False
    return norm1 == norm2

def is_subpath_or_equal(child_path: Optional[str], parent_path: Optional[str]) -> bool:
    """Checks if child_path is equal to or located within parent_path.
    
    Supports:
    - Exact match
    - Subdirectories (e.g., C:\\bot\\src inside C:\\bot)
    - UNC network shares
    - Case-insensitive comparison on Windows
    """
    norm_child = normalize_path_cross_platform(child_path)
    norm_parent = normalize_path_cross_platform(parent_path)

    if not norm_child or not norm_parent:
        return False

    if norm_child == norm_parent:
        return True

    sep = "\\" if os.name == 'nt' else "/"
    return norm_child.startswith(norm_parent + sep)

__all__ = [
    "normalize_path_cross_platform",
    "paths_are_equivalent",
    "is_subpath_or_equal"
]
