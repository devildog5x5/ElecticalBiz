"""PowerFlow launcher — standalone desktop or web server mode."""

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from database import init_db
from seed import seed_if_empty

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
APP_DIR = Path(__file__).parent
ICON_ICO = APP_DIR / "static" / "img" / "icon.ico"
ICON_PNG = APP_DIR / "static" / "img" / "icon.png"


def app_icon_path():
    if ICON_ICO.exists():
        return str(ICON_ICO)
    if ICON_PNG.exists():
        return str(ICON_PNG)
    return None


def wait_for_server(host, port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def run_server(host, port, debug=False):
    from app import app

    app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)


def run_web(host=DEFAULT_HOST, port=DEFAULT_PORT, debug=False, open_browser=False):
    init_db()
    seed_if_empty()

    url = f"http://{host}:{port}"
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print(f"PowerFlow web server running at {url}")
    print(f"API docs: {url}/api/docs")
    print("Press Ctrl+C to stop.")
    run_server(host, port, debug=debug)


def run_standalone(host=DEFAULT_HOST, port=DEFAULT_PORT, width=1280, height=860):
    init_db()
    seed_if_empty()

    server = threading.Thread(
        target=run_server,
        args=(host, port),
        kwargs={"debug": False},
        daemon=True,
    )
    server.start()

    url = f"http://{host}:{port}"
    if not wait_for_server(host, port):
        print(f"Error: server did not start on {url}", file=sys.stderr)
        sys.exit(1)

    try:
        import webview
    except ImportError:
        print("Standalone mode requires pywebview. Install with: pip install pywebview")
        print(f"Opening in your browser instead: {url}")
        webbrowser.open(url)
        try:
            server.join()
        except KeyboardInterrupt:
            pass
        return

    window = webview.create_window(
        "PowerFlow — Electrical Business Manager",
        url,
        width=width,
        height=height,
        min_size=(900, 600),
        text_select=True,
    )
    webview.start(debug=False, icon=app_icon_path())


def main():
    parser = argparse.ArgumentParser(
        description="PowerFlow Electrical Business Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                  Standalone desktop app (default)
  python main.py --web            Web server on port 5000
  python main.py --web --browser  Web server and open browser
  python main.py --standalone     Desktop app explicitly
        """,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--web",
        action="store_true",
        help="Run as web server (access via browser)",
    )
    mode.add_argument(
        "--standalone",
        action="store_true",
        help="Run as standalone desktop app (default)",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Bind host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    parser.add_argument("--browser", action="store_true", help="Open browser (web mode only)")
    parser.add_argument("--debug", action="store_true", help="Flask debug mode (web mode only)")
    parser.add_argument("--width", type=int, default=1280, help="Window width (standalone mode)")
    parser.add_argument("--height", type=int, default=860, help="Window height (standalone mode)")
    args = parser.parse_args()

    if args.web:
        run_web(host=args.host, port=args.port, debug=args.debug, open_browser=args.browser)
    else:
        run_standalone(host=args.host, port=args.port, width=args.width, height=args.height)


if __name__ == "__main__":
    main()
