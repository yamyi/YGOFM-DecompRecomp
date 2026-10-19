"""Registry for independent TeaTools decoders."""
from __future__ import annotations

from .analyzer import AnalysisContext, TeaAnalyzer, TeaDecoder
from .results import AnalysisResult


class TeaRegistry:
    """A deliberately small registry; importers choose when to run it."""

    def __init__(self):
        self._decoders: list[TeaDecoder] = []

    @property
    def decoders(self) -> tuple[TeaDecoder, ...]:
        return tuple(self._decoders)

    def register(self, decoder: TeaDecoder) -> TeaDecoder:
        if any(current.id == decoder.id for current in self._decoders):
            raise ValueError(f"TeaTools decoder {decoder.id!r} is already registered")
        self._decoders.append(decoder)
        return decoder

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        return TeaAnalyzer(self._decoders).analyze(context)
