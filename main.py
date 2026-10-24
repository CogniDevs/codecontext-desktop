import os
import sys
import socket
import argparse
import threading
import time
import urllib.request
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from backend.router import api_router
from backend.services import watcher_service

app = FastAPI(title="CodeContext Core API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

base_dir = os.path.dirname(os.path.abspath(__file__))
dist_candidates = [
    os.path.join(base_dir, "dist_ui"),
    os.path.join(base_dir, "frontend", "dist", "codecontext-web", "browser"),
    os.path.join(base_dir, "frontend", "dist", "browser"),
    os.path.join(base_dir, "frontend", "dist"),
    os.path.join(base_dir, "dist", "browser"),
    os.path.join(base_dir, "dist"),
]

static_dir = next((d for d in dist_candidates if os.path.exists(d)), None)
if static_dir:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


def is_port_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(host: str, preferred_port: int) -> int:
    if is_port_available(host, preferred_port):
        return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def is_server_ready(url: str, timeout: float = 0.3) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="CodeContext Desktop & Web Engine")
    parser.add_argument("--server-only", "-s", action="store_true", help="Run HTTP server only without desktop window")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable WebView developer tools")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    args = parser.parse_args()

    effective_port = args.port
    if not args.server_only:
        effective_port = find_available_port(args.host, args.port)

    config = uvicorn.Config(app, host=args.host, port=effective_port, log_level="warning")
    server = uvicorn.Server(config)

    if args.server_only:
        try:
            server.run()
        finally:
            watcher_service.stop_watching()
            os._exit(0)
        return

    try:
        import webview
    except ImportError:
        try:
            server.run()
        finally:
            watcher_service.stop_watching()
            os._exit(0)
        return

    server_thread = threading.Thread(
        target=server.run,
        daemon=True
    )
    server_thread.start()

    target_url = f"http://{args.host}:{effective_port}"
    if static_dir is None and is_server_ready("http://127.0.0.1:4200"):
        target_url = "http://127.0.0.1:4200"
    else:
        status_url = f"http://{args.host}:{effective_port}/api/status"
        for _ in range(50):
            if is_server_ready(status_url, timeout=0.1):
                break
            time.sleep(0.05)

    def on_window_closed():
        watcher_service.stop_watching()
        server.should_exit = True

    window = webview.create_window(
        title="CodeContext",
        url=target_url,
        width=1400,
        height=850,
        min_size=(1000, 650)
    )
    window.events.closed += on_window_closed

    try:
        webview.start(debug=args.debug)
    finally:
        watcher_service.stop_watching()
        server.should_exit = True
        time.sleep(0.1)
        os._exit(0)


if __name__ == "__main__":
    main()