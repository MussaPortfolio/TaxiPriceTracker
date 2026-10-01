"""Живой график цен: локальный веб-сервер, страница сама обновляется при новых замерах.

    python taxi_live.py            # http://localhost:8000
    python taxi_live.py 8080       # другой порт

Сбору цен (taxi_price.py) не мешает: только читает taxi_prices.csv.
Остановить: Ctrl+C.
"""
import importlib
import sys
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import taxi_report

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

# Раз в 30 секунд страница спрашивает /version и перезагружается, если появился
# новый замер или изменился код отчёта
LIVE_JS = """
<script>
let v = null;
setInterval(async () => {
  try {
    const now = await (await fetch('/version', {cache: 'no-store'})).text();
    if (v !== null && now !== v) location.reload();
    v = now;
  } catch (e) {}
}, 30000);
</script>"""

EMPTY = ("<!doctype html><meta charset='utf-8'><meta http-equiv='refresh' content='30'>"
         "<p style='font-family:system-ui'>Замеров с ценой пока нет — страница обновится сама.</p>")


REPORT_PY = taxi_report.__file__
_report_mtime = Path(REPORT_PY).stat().st_mtime


def fresh_report():
    """taxi_report с последними правками кода — без перезапуска сервера."""
    global _report_mtime
    mtime = Path(REPORT_PY).stat().st_mtime
    if mtime != _report_mtime:
        _report_mtime = mtime
        importlib.reload(taxi_report)
    return taxi_report


def csv_version():
    """Меняется и при новом замере, и при правке кода отчёта — тогда страница перезагрузится."""
    p = taxi_report.CSV_PATH
    data = p.stat().st_mtime if p.exists() else 0
    return f"{data}-{Path(REPORT_PY).stat().st_mtime}"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/version":
            body, ctype = csv_version(), "text/plain"
        elif self.path == "/":
            try:
                body = fresh_report().render(LIVE_JS) or EMPTY
            except Exception as e:  # например, CSV дописывается прямо сейчас
                body = f"<meta http-equiv='refresh' content='5'><p>Ошибка: {e}</p>"
            ctype = "text/html"
        else:
            self.send_error(404)
            return
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # не засорять консоль запросами раз в 30 секунд
        pass


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    url = f"http://localhost:{PORT}"
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Живой график: {url}  (Ctrl+C — остановить)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
