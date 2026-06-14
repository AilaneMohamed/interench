from __future__ import annotations

import socket
import threading
import time
import webbrowser
import uvicorn


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


def main():
    from app.main import app as fastapi_app

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
