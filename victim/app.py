"""Deliberately vulnerable CTF target for the live demo: path traversal in /download. Read-only, localhost only."""

import http.server
import pathlib
import urllib.parse

ROOT = pathlib.Path(__file__).parent
FILES = ROOT / "public"
INDEX = b"""<html><body><h1>Acme Report Portal</h1>
<p>Quarterly reports: <a href="/download?file=q1.txt">q1.txt</a> <a href="/download?file=q2.txt">q2.txt</a></p>
<!-- TODO: move flag.txt out of the app directory before launch -->
</body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/":
            return self.reply(200, INDEX, "text/html")
        if url.path == "/download":
            name = urllib.parse.parse_qs(url.query).get("file", [""])[0]
            path = FILES / name  # the bug: no normalization, so ../flag.txt escapes public/
            if path.is_file():
                return self.reply(200, path.read_bytes(), "text/plain")
            return self.reply(404, b"not found", "text/plain")
        self.reply(404, b"not found", "text/plain")

    def reply(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
