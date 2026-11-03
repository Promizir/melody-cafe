"""Melody Cafe dashboard for localhost or Render; standard library only."""
import argparse
import io
import json
import os
import uuid
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock

from playlist import Playlist

ROOT = Path(__file__).resolve().parent


class Dashboard:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.playlist = Playlist()
        self.current = None
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                song = json.loads(line)
                node = self.playlist.addSong(song["title"], song["duration"])
                node.uid = song["id"]
        else:
            self.playlist.addSong("Sunrise", 210)
            self.playlist.addSong("Desert Rain", 185)
            self.playlist.addSong("Marina Lights", 240)
            self.save()

    def nodes(self, backward=False):
        node = self.playlist.tail if backward else self.playlist.head
        while node is not None:
            yield node
            node = node.prev if backward else node.next

    def save(self):
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            for node in self.nodes():
                if not hasattr(node, "uid"):
                    node.uid = uuid.uuid4().hex
                handle.write(json.dumps({"id": node.uid, "title": node.title,
                                         "duration": node.duration}) + "\n")
        os.replace(temporary, self.path)

    def find(self, uid):
        for node in self.nodes():
            if node.uid == uid:
                return node
        raise ValueError("That song is no longer in the playlist.")

    def state(self, backward=False):
        # Arrays are only API transport; the live playlist is the custom linked list.
        return {"songs": [{"id": n.uid, "title": n.title, "duration": n.duration}
                          for n in self.nodes(backward)],
                "current": self.current.uid if self.current else None}

    def action(self, data):
        action = data.get("action")
        if action in ("add", "insert"):
            title = data.get("title", "")
            duration = data.get("duration")
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > 30:
                raise ValueError("Enter a title between 1 and 30 characters.")
            title = title.strip()
            if type(duration) is not int or not 1 <= duration <= 86400:
                raise ValueError("Duration must be 1 to 86400 whole seconds.")
            if action == "add":
                self.playlist.addSong(title, duration)
            else:
                key = data.get("key", "")
                with redirect_stdout(io.StringIO()):
                    success = self.playlist.insertAfter(key, title, duration)
                if not success:
                    raise ValueError(f"Song not found: {key}")
            self.save()
            return f'Added "{title}".'
        if action == "remove":
            title = data.get("title")
            target = next((n for n in self.nodes() if n.title == title), None)
            if target is None:
                raise ValueError(f"Song not found: {title}")
            replacement = self.playlist.playNext(target)
            if self.current is target:
                self.current = None if replacement is target else replacement
            self.playlist.removeSong(title)
            self.save()
            return f'Removed "{title}".'
        if action == "select":
            self.current = self.find(data.get("id"))
        elif action == "next":
            self.current = self.playlist.playNext(self.current)
        elif action == "previous":
            self.current = (self.current.prev or self.playlist.tail) if self.current else self.playlist.tail
        else:
            raise ValueError("Unknown operation.")
        return f"Selected {self.current.title}." if self.current else "Your playlist is empty."


def make_handler(dashboard):
    lock = RLock()
    external_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
    hosted = os.environ.get("RENDER") == "true"

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def reply(self, status, body, kind="application/json; charset=utf-8"):
            if isinstance(body, dict):
                body = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def trusted(self):
            port = self.server.server_port
            origins = {f"127.0.0.1:{port}": f"http://127.0.0.1:{port}",
                       f"localhost:{port}": f"http://localhost:{port}"}
            if external_host:
                origins[external_host] = f"https://{external_host}"
            origin = self.headers.get("Origin")
            host = self.headers.get("Host")
            return host in origins and (origin is None or origin == origins[host])

        def do_GET(self):
            if self.path == "/healthz":
                return self.reply(200, {"status": "ok"})
            if not self.trusted():
                return self.reply(403, {"error": "Untrusted host or origin."})
            if self.path in ("/api/state", "/api/state?backward=1"):
                with lock:
                    state = dashboard.state("backward=1" in self.path)
                state["hosted"] = hosted
                state["persistent"] = os.environ.get("MELODY_PERSISTENT_STORAGE") == "true"
                return self.reply(200, state)
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/style.css": ("style.css", "text/css; charset=utf-8")}
            if self.path not in assets:
                return self.reply(404, {"error": "Not found."})
            filename, kind = assets[self.path]
            self.reply(200, (ROOT / "static" / filename).read_bytes(), kind)

        def do_POST(self):
            if not self.trusted():
                return self.reply(403, {"error": "Untrusted host or origin."})
            if self.path != "/api/action":
                return self.reply(404, {"error": "Not found."})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply(415, {"error": "Expected JSON."})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192:
                    raise ValueError("Invalid request size.")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected an object.")
                with lock:
                    message = dashboard.action(data)
                self.reply(200, {"message": message})
            except (ValueError, TypeError) as error:
                self.reply(400, {"error": str(error)})

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--host", default="0.0.0.0" if os.environ.get("RENDER") == "true" else "127.0.0.1")
    args = parser.parse_args()
    data_dir = Path(os.environ.get("MELODY_DATA_DIR", str(ROOT)))
    dashboard = Dashboard(data_dir / "songs.jsonl")
    server = ThreadingHTTPServer((args.host, args.port), make_handler(dashboard))
    url = os.environ.get("RENDER_EXTERNAL_URL", f"http://127.0.0.1:{args.port}")
    print(f"Melody Cafe is ready: {url}", flush=True)
    print("Keep this terminal open. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
