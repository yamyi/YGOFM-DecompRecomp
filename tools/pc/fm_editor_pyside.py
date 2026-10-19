"""PyInstaller entry point for the package-relative PySide6 FM Editor."""

import sys



def main():
    # Release verification is shared with the classic build.  Keep the Qt
    # window as the normal packaged entry point, but route the noninteractive
    # smoke test through the command-line handler so it writes its report
    # rather than opening a window and waiting for a user.
    if len(sys.argv) > 1 and sys.argv[1] == "self-test":
        from fm_editor.cli import main as command
        return command()
    from fm_editor.pyside_app import main as window
    return window()


if __name__ == "__main__":
    raise SystemExit(main())
