"""PySide-only asynchronous recovery writer.

The original editor keeps its Job-based ``recovery.Writer``.  The Qt window
writes an immutable history snapshot after its event loop is idle, so it needs
a small adapter without changing the shared recovery module.
"""
from __future__ import annotations

import threading


def install():
    """Install the Qt writer once, after the original recovery module loads."""
    from .. import recovery as recovery_module

    if getattr(getattr(recovery_module, "Writer", None), "_pyside_recovery_compat", False):
        return

    class Writer:
        _pyside_recovery_compat = True

        def __init__(self, recovery):
            self.recovery = recovery
            self._thread = None
            self._lock = threading.Lock()
            self.error = None

        def busy(self):
            return self._thread is not None and self._thread.is_alive()

        def write(self, project, snapshot=None):
            if self.busy():
                return False
            frozen = snapshot or recovery_module.Snapshot(project)
            retail, source = project.retail, project.source_dir
            self.error = None

            def run():
                try:
                    clone = frozen.restore(retail, source)
                    self.recovery.write(clone, snapshot=frozen)
                except Exception as problem:  # read on the Qt thread
                    self.error = problem

            self._thread = threading.Thread(target=run, name="FM Editor Qt recovery", daemon=True)
            self._thread.start()
            return True

    recovery_module.Writer = Writer
