from __future__ import annotations

import socket
import threading
import time
import webbrowser
import uvicorn
import importlib
import sys
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000


def wait_for_server(host: str, port: int, timeout: float = 20.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def open_browser_when_ready():
    if wait_for_server(HOST, PORT, timeout=25):
        webbrowser.open(f"http://{HOST}:{PORT}")


def prepare_import_path():
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base_dir = Path(__file__).resolve().parent

    app_dir = base_dir / "app"

    for path in [base_dir, app_dir]:
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def main():
    prepare_import_path()

    module = importlib.import_module("main")
    fastapi_app = module.app

    t = threading.Thread(target=open_browser_when_ready, daemon=True)
    t.start()

    config = uvicorn.Config(
        fastapi_app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
