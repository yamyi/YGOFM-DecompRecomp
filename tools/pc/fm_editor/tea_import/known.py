"""The supported, read-only TeaTools detector set."""
from .decoders import InitialDeckDecoder, PhoenixBattleEffectsDecoder, RitualEngineDecoder
from .registry import TeaRegistry


def registry() -> TeaRegistry:
    known = TeaRegistry()
    for decoder in (PhoenixBattleEffectsDecoder(), RitualEngineDecoder(), InitialDeckDecoder()):
        known.register(decoder)
    return known
