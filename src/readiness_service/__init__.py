"""Self-Hosted Platform Readiness Service."""

from readiness_service.engine import analyze_snapshot
from readiness_service.models import AnalysisResult, PlatformSnapshot

__all__ = ["AnalysisResult", "PlatformSnapshot", "analyze_snapshot"]
__version__ = "0.1.0"
