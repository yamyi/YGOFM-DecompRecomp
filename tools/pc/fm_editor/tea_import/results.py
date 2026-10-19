"""Typed, non-mutating results from TeaTools binary analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any


class DetectionStatus(str, Enum):
    RECOGNIZED = "recognized"
    VARIANT = "variant"
    AMBIGUOUS = "ambiguous"
    ABSENT = "absent"
    INVALID = "invalid"


class Compatibility(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    NEEDS_ENGINE = "needs_engine"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Diagnostic:
    message: str
    severity: str = "info"
    detector: str = ""


@dataclass(frozen=True)
class DetectionResult:
    patch_id: str
    status: DetectionStatus
    version: str = ""
    details: str = ""
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def is_recognized(self) -> bool:
        return self.status is DetectionStatus.RECOGNIZED


@dataclass(frozen=True)
class FeatureResult:
    feature_id: str
    category: str
    detection: DetectionResult
    compatibility: Compatibility
    data: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass
class AnalysisResult:
    detections: list[DetectionResult] = field(default_factory=list)
    features: list[FeatureResult] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    coverage: Any = None
    changed_ranges: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    unknown_ranges: dict[str, list[tuple[int, int]]] = field(default_factory=dict)

    def add(self, detection: DetectionResult, feature: FeatureResult | None = None) -> None:
        self.detections.append(detection)
        self.diagnostics.extend(detection.diagnostics)
        if feature is not None:
            self.features.append(feature)

    def coverage_summary(self) -> dict[str, dict[str, int]]:
        """Per-source counts for a report without double-counting ownership."""
        sources = set(self.changed_ranges) | set(self.unknown_ranges)
        return {
            source: {
                "changed": sum(end - start for start, end in self.changed_ranges.get(source, ())),
                "explained": sum(end - start for start, end in self.changed_ranges.get(source, ()))
                - sum(end - start for start, end in self.unknown_ranges.get(source, ())),
                "unknown": sum(end - start for start, end in self.unknown_ranges.get(source, ())),
            }
            for source in sorted(sources)
        }

    def report(self) -> str:
        """A deterministic human-readable report suitable for a sidecar file."""
        lines = ["TeaTools analysis", "=================", "", "Detected patches:"]
        features = {feature.feature_id: feature for feature in self.features}
        if not self.detections:
            lines.append("  None")
        for detection in self.detections:
            title = detection.patch_id.replace("_", " ").title()
            lines.append(f"  {title}")
            lines.append(f"    Detection: {detection.status.value.title()}"
                         + (f" ({detection.version})" if detection.version else ""))
            if detection.details:
                lines.append(f"    Evidence: {detection.details}")
            feature = features.get(detection.patch_id)
            if feature is not None:
                lines.append(f"    PC compatibility: {feature.compatibility.value}")
                if feature.data:
                    lines.append("    Decoded: " + json.dumps(feature.data, sort_keys=True, separators=(",", ":")))
                for warning in feature.warnings:
                    lines.append(f"    Warning: {warning}")
        if self.diagnostics:
            lines.extend(("", "Diagnostics:"))
            lines.extend(f"  [{item.severity}] {item.message}" for item in self.diagnostics)
        lines.extend(("", "Coverage:"))
        summary = self.coverage_summary()
        if not summary:
            lines.append("  No comparable binary sources.")
        for source, values in summary.items():
            lines.append(f"  {source}: {values['changed']} changed bytes; {values['explained']} explained; "
                         f"{values['unknown']} unrecognized")
        return "\n".join(lines) + "\n"

    def as_dict(self) -> dict[str, Any]:
        """Stable JSON-ready diagnostics; this is not a runtime mod schema."""
        claims = getattr(self.coverage, "claims", ())
        return {
            "detections": [{
                "id": item.patch_id, "status": item.status.value, "version": item.version,
                "details": item.details,
                "diagnostics": [{"message": note.message, "severity": note.severity, "detector": note.detector}
                                for note in item.diagnostics],
            } for item in self.detections],
            "features": [{
                "id": item.feature_id, "category": item.category,
                "detection": item.detection.status.value,
                "compatibility": item.compatibility.value, "data": item.data,
                "warnings": list(item.warnings),
            } for item in self.features],
            "diagnostics": [{"message": item.message, "severity": item.severity, "detector": item.detector}
                            for item in self.diagnostics],
            "coverage": self.coverage_summary(),
            # Ranges retain the decoder's provenance.  Consumers can inspect
            # which changed bytes were decoded without mistaking them for
            # project data that the importer has converted.
            "claims": [{"source": item.source, "start": item.start, "end": item.end,
                        "owner": item.owner, "purpose": item.purpose, "status": item.status}
                       for item in claims],
            "changed_ranges": {source: [{"start": start, "end": end} for start, end in ranges]
                               for source, ranges in sorted(self.changed_ranges.items())},
            "unknown_ranges": {source: [{"start": start, "end": end} for start, end in ranges]
                               for source, ranges in sorted(self.unknown_ranges.items())},
        }
