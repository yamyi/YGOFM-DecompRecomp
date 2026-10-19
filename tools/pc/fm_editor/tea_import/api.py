"""Public entry point for analysis before an importer mutates a Project."""
from __future__ import annotations

from .analyzer import AnalysisContext
from .binary import BinaryReader
from .registry import TeaRegistry
from .results import AnalysisResult


SLUS_SOURCE = "SLUS_014.11"
WA_SOURCE = "DATA/WA_MRG.MRG"


def context_for(retail_files, modified_files) -> AnalysisContext:
    """Build an analysis context from the existing :class:`disc.GameFiles` API."""
    return AnalysisContext(
        retail={
            SLUS_SOURCE: BinaryReader(retail_files.slus, SLUS_SOURCE),
            WA_SOURCE: BinaryReader(retail_files.wa, WA_SOURCE),
        },
        modified={
            SLUS_SOURCE: BinaryReader(modified_files.slus, SLUS_SOURCE),
            WA_SOURCE: BinaryReader(modified_files.wa, WA_SOURCE),
        },
    )


def analyze(retail_files, modified_files, registry: TeaRegistry | None = None) -> AnalysisResult:
    """Analyze game files without importing, converting, or modifying editor state."""
    context = context_for(retail_files, modified_files)
    if registry is None:
        from .known import registry as known_registry
        registry = known_registry()
    result = registry.analyze(context)
    for source, modified in context.modified.items():
        retail = context.retail.get(source)
        if retail is None:
            continue
        changed = modified.diff_ranges(retail)
        result.changed_ranges[source] = changed
        result.unknown_ranges[source] = context.coverage.uncovered(source, changed)
    return result
