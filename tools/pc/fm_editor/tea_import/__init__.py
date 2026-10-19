"""Pure-Python analysis primitives for TeaTools-aware game imports.

This package intentionally analyses binaries without touching a Project or
importing Qt. Conversion belongs to the existing importer once a recovered
feature has a verified PC runtime equivalent.
"""
from .analyzer import AnalysisContext, TeaAnalyzer
from .api import analyze, context_for
from .binary import BinaryReader
from .coverage import CoverageClaim, CoverageLedger
from .registry import TeaRegistry
from .known import registry as known_registry
from .results import AnalysisResult, Compatibility, DetectionResult, DetectionStatus, Diagnostic, FeatureResult
from .signatures import PatchSignature, SignatureDecoder, SignatureProbe

__all__ = (
    "AnalysisContext", "AnalysisResult", "BinaryReader", "Compatibility", "CoverageClaim", "analyze",
    "CoverageLedger", "DetectionResult", "DetectionStatus", "Diagnostic", "FeatureResult",
    "PatchSignature", "SignatureDecoder", "SignatureProbe", "TeaAnalyzer", "TeaRegistry", "context_for", "known_registry",
)
