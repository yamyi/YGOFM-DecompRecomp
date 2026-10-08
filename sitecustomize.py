"""Load FM Editor compatibility pages without editing tracked launcher files."""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys

_TARGETS = {"tools.pc.fm_editor.qt.window", "fm_editor.qt.window"}


class _WindowLoader(importlib.abc.Loader):
    def __init__(self, loader, package):
        self._loader = loader
        self._package = package

    def create_module(self, spec):
        create = getattr(self._loader, "create_module", None)
        return create(spec) if create else None

    def exec_module(self, module):
        self._loader.exec_module(module)
        for module_name in ("rituals_compat", "import_compat", "duelists_compat", "stars_compat"):
            compat = __import__(f"{self._package}.qt.{module_name}", fromlist=("install",))
            compat.install()


class _WindowFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in _TARGETS:
            return None
        # Call PathFinder directly so this finder does not call itself.
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is not None and spec.loader is not None and not isinstance(spec.loader, _WindowLoader):
            spec.loader = _WindowLoader(spec.loader, fullname.rsplit(".qt.window", 1)[0])
        return spec


sys.meta_path.insert(0, _WindowFinder())
