"""The Qt FM Editor.

The window itself is `qt/window.py` and a page's own code is a module beside
it (`qt/packs.py`, `qt/map.py`, ...), as the Tk editor is split into
`tabs.py`, `packs_tab.py` and the rest. This module is the name the rest of
the editor and the tests know them by.
"""
from __future__ import annotations

from .qt.compat import install as _install_compat
from .qt.cards_compat import install as _install_cards_compat
from .qt.fusions_compat import install as _install_fusions_compat
from .qt.rituals_compat import install as _install_rituals_compat
from .qt.import_compat import install as _install_import_compat
from .qt.duelists_compat import install as _install_duelists_compat
from .qt.stars_compat import install as _install_stars_compat

_install_compat()

from .qt.common import *          # noqa: F401,F403
from .qt.common import (_qimage, _line_count, _pairs_text, _parse_pairs, _whole,
                        _card_image)      # noqa: F401
from .qt.window import ModernEditor, main      # noqa: F401
from .qt.ui_assets_compat import install as _install_ui_assets_compat

_install_cards_compat()
_install_fusions_compat()
_install_rituals_compat()
_install_import_compat()
_install_duelists_compat()
_install_stars_compat()
_install_ui_assets_compat()

if __name__ == "__main__":
    raise SystemExit(main())
