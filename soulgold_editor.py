#!/usr/bin/env python3
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    if "--web" in sys.argv or "-w" in sys.argv:
        import soulgold_web_server
        port = 8080
        for i, a in enumerate(sys.argv):
            if a in ("-p", "--port") and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    pass
        soulgold_web_server.start_server(port=port, open_browser=True)
        return

    has_cli_flags = any(arg.startswith("-") and arg not in ("-g", "--gui") for arg in sys.argv[1:])
    is_gui_explicit = "-g" in sys.argv or "--gui" in sys.argv
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    if is_gui_explicit or (not has_cli_flags and has_display):
        import soulgold_editor_gui
        save_arg = None
        for a in sys.argv[1:]:
            if not a.startswith("-"):
                save_arg = a
                break
        soulgold_editor_gui.main(save_arg)
    else:
        import soulgold_editor_cli
        soulgold_editor_cli.main()

if __name__ == "__main__":
    main()
