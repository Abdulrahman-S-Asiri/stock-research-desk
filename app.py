"""Personal stock research desk. Serves only on the local loopback interface."""
import argparse
import json
import logging
import threading
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from analytics import analyze
from provider import DataError, connect, load_prices, validate_request

ROOT = Path(__file__).resolve().parent
DATA_LOCK = threading.Lock()
STATIC = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/style.css": ("style.css", "text/css"), "/favicon.svg": ("favicon.svg", "image/svg+xml")}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Never log symbols, queries, or Norgate rows.
        pass

    def reply(self, status, body, content_type="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origins = {f"http://{h}" for h in hosts}
        if self.headers.get("Host") not in hosts or (self.headers.get("Origin") and self.headers["Origin"] not in origins):
            return self.reply(403, {"error": "This app is available only from its local address."})
        url = urlsplit(self.path)
        if url.path in STATIC:
            name, content_type = STATIC[url.path]
            return self.reply(200, (ROOT / "static" / name).read_bytes(), content_type)
        if url.path == "/api/status":
            try:
                with DATA_LOCK:
                    sdk = connect()
                    has_us = "US Equities" in sdk.databases()
                return self.reply(200, {"connected": has_us, "today": date.today().isoformat(), "message": "Norgate connected" if has_us else "US equities are unavailable"})
            except DataError as exc:
                return self.reply(200, {"connected": False, "today": date.today().isoformat(), "message": str(exc)})
            except Exception:
                return self.reply(200, {"connected": False, "today": date.today().isoformat(), "message": "Norgate is unavailable. Check Norgate Data Updater and retry."})
        if url.path != "/api/analyze":
            return self.reply(404, {"error": "Page not found."})
        try:
            query = parse_qs(url.query, max_num_fields=8)
            if set(query) != {"symbols", "benchmark", "start", "end"} or any(len(v) != 1 for v in query.values()):
                raise DataError("Supply symbols, benchmark, start date, and end date once each.")
            symbols, benchmark, start, end = validate_request(**{k: v[0] for k, v in query.items()})
            with DATA_LOCK:
                prices, warnings = load_prices(symbols, start, end)
            result = analyze(prices, benchmark)
            result["warnings"].extend(warnings)
            result.update({"source": "Norgate Data", "adjustment": "Total return (splits and dividends)",
                           "requested_start": start.isoformat(), "requested_end": end.isoformat(),
                           "retrieved_at": datetime.now(timezone.utc).isoformat(),
                           "evidence_level": "Historical comparison — not a strategy backtest"})
            self.reply(200, result)
        except (DataError, ValueError) as exc:
            self.reply(400, {"error": str(exc)})
        except Exception as exc:
            logging.error("Data request failed (%s)", type(exc).__name__)
            self.reply(503, {"error": "Norgate could not complete this request. Check the updater and retry."})


def main():
    parser = argparse.ArgumentParser(description="Local Norgate stock research dashboard")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Stock Research Desk: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
