"""Native Visio scene, semantic edit, bridge, and package-audit infrastructure."""

from .edits import SemanticEditError, apply_edits
from .models import EditRequest, Scene, semantic_sha256
from .package import audit_vsdx, diff_audits

__all__ = [
    "EditRequest",
    "Scene",
    "SemanticEditError",
    "apply_edits",
    "audit_vsdx",
    "diff_audits",
    "semantic_sha256",
]
