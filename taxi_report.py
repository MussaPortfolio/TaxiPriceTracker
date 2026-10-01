"""Строит отчёт по taxi_prices.csv: средняя цена по часам и все замеры во времени.
Результат — taxi_report.html (открывается в любом браузере, сторонние библиотеки не нужны).

    python taxi_report.py           # построить отчёт и открыть его
    python taxi_report.py --watch   # пересобирать отчёт при каждом новом замере (Ctrl+C — выход)
"""
import csv
import sys
import time
import webbrowser
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CSV_PATH = Path(__file__).with_name("taxi_prices.csv")
HTML_PATH = Path(__file__).with_name("taxi_report.html")

W, H = 860, 300                      # размер графика
L, R, T, B = 50, 15, 15, 30          # отступы под оси


def load():
    """Замеры с ценой и число неудачных замеров (капча, цена не найдена и т. п.)."""
    with CSV_PATH.open(encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f, delimiter=";"))
    rows = [
        (datetime.strptime(r["время"], "%Y-%m-%d %H:%M"), int(r["цена_руб"]),
         r["повышенный_спрос"] == "да")
        for r in all_rows if r["цена_руб"]
    ]
    return rows, len(all_rows) - len(rows)


def y_axis(lo, hi):
    """Горизонтальные линии сетки и функция перевода цены в координату y."""
    step = 50
    lo, hi = lo // step * step, -(-hi // step) * step
    y = lambda p: T + (hi - p) / (hi - lo) * (H - T - B)
    grid = "".join(
        f'<line x1="{L}" x2="{W - R}" y1="{y(p):.1f}" y2="{y(p):.1f}" class="grid"/>'
        f'<text x="{L - 6}" y="{y(p) + 4:.1f}" class="lbl" text-anchor="end">{p}</text>'
        for p in range(lo, hi + 1, step)
    )
    return y, grid


def hourly_chart(rows):
    by_hour = defaultdict(list)
    for t, p, _ in rows:
        by_hour[t.hour].append(p)
    avg = {h: sum(v) / len(v) for h, v in by_hour.items()}
    y, svg = y_axis(min(min(v) for v in by_hour.values()), max(max(v) for v in by_hour.values()))
    cheap, dear = sorted(avg, key=avg.get)[:4], sorted(avg, key=avg.get)[-4:]
    slot = (W - L - R) / 24
    for h in range(24):
        x = L + h * slot
        svg += f'<text x="{x + slot / 2:.1f}" y="{H - 10}" class="lbl" text-anchor="middle">{h}</text>'
        if h not in avg:
            continue
        v = by_hour[h]
        cls = "cheap" if h in cheap else "dear" if h in dear else "bar"
        svg += (f'<rect x="{x + 3:.1f}" y="{y(avg[h]):.1f}" width="{slot - 6:.1f}" '
                f'height="{H - B - y(avg[h]):.1f}" class="{cls}">'
                f'<title>{h}:00 — в среднем {avg[h]:.0f} ₽ (от {min(v)} до {max(v)}, замеров: {len(v)})</title></rect>'
                f'<line x1="{x + slot / 2:.1f}" x2="{x + slot / 2:.1f}" y1="{y(max(v)):.1f}" '
                f'y2="{y(min(v)):.1f}" class="range"/>')
    return svg, avg


def timeline_chart(rows):
    t0, t1 = rows[0][0], rows[-1][0]
    span = max((t1 - t0).total_seconds(), 1)
    x = lambda t: L + (t - t0).total_seconds() / span * (W - L - R)
    y, svg = y_axis(min(p for _, p, _ in rows), max(p for _, p, _ in rows))
    pts = " ".join(f"{x(t):.1f},{y(p):.1f}" for t, p, _ in rows)
    svg += f'<polyline points="{pts}" class="line"/>'
    for t, p, surge in rows:
        svg += (f'<circle cx="{x(t):.1f}" cy="{y(p):.1f}" r="3.5" class="{"dear" if surge else "cheap"}">'
                f'<title>{t:%d.%m %H:%M} — {p} ₽{" (повышенный спрос)" if surge else ""}</title></circle>')
    # подписи времени: примерно 8 штук по оси
    for i in range(0, len(rows), max(1, len(rows) // 8)):
        t = rows[i][0]
        svg += f'<text x="{x(t):.1f}" y="{H - 10}" class="lbl" text-anchor="middle">{t:%d.%m %H:%M}</text>'
    return svg


def render(head_extra=""):
    """HTML-отчёт строкой или None, если замеров с ценой пока нет."""
    rows, failed = load() if CSV_PATH.exists() else ([], 0)
    rows.sort()
    if not rows:
        return None
    hourly, avg = hourly_chart(rows)
    best = sorted(avg, key=avg.get)[:3]
    worst = sorted(avg, key=avg.get)[-3:][::-1]
    fmt = lambda hs: ", ".join(f"{h}:00 (~{avg[h]:.0f} ₽)" for h in hs)
    surge = sum(s for *_, s in rows) / len(rows) * 100

    html = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Цены на такси</title>{head_extra}
<style>
:root {{ --bg:#fff; --fg:#1d1d1f; --muted:#6e6e73; --grid:#e5e5ea; --bar:#a1a1aa;
        --cheap:#16a34a; --dear:#dc2626; --line:#2563eb; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161618; --fg:#f2f2f7; --muted:#98989f;
        --grid:#2c2c30; --bar:#5a5a62; --cheap:#4ade80; --dear:#f87171; --line:#60a5fa; }} }}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
       font:15px/1.5 system-ui, sans-serif; }}
main {{ max-width:{W}px; margin:auto; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:28px 0 8px; }}
p {{ margin:4px 0; }} .muted {{ color:var(--muted); }}
svg {{ width:100%; height:auto; }}
.grid {{ stroke:var(--grid); }} .lbl {{ fill:var(--muted); font-size:11px; }}
.bar {{ fill:var(--bar); }} .cheap {{ fill:var(--cheap); }} .dear {{ fill:var(--dear); }}
.range {{ stroke:var(--fg); stroke-width:1.5; opacity:.5; }}
.line {{ fill:none; stroke:var(--line); stroke-width:1.5; }}
</style></head><body><main>
<h1>Когда дешевле ехать на такси</h1>
<p class="muted">{len(rows) + failed} замеров{f" (из них {failed} без цены — ошибка)" if failed else ""}, {rows[0][0]:%d.%m.%Y %H:%M} — {rows[-1][0]:%d.%m.%Y %H:%M}.
Повышенный спрос был в {surge:.0f}% замеров.</p>
<p><b style="color:var(--cheap)">Дешевле всего:</b> {fmt(best)}</p>
<p><b style="color:var(--dear)">Дороже всего:</b> {fmt(worst)}</p>

<h2>Средняя цена по часам</h2>
<p class="muted">Столбик — средняя цена, линия — от минимума до максимума.
Зелёные — 4 самых дешёвых часа, красные — 4 самых дорогих. Наведите курсор для деталей.</p>
<svg viewBox="0 0 {W} {H}">{hourly}</svg>

<h2>Все замеры</h2>
<p class="muted">Красные точки — повышенный спрос, зелёные — обычная цена.</p>
<svg viewBox="0 0 {W} {H}">{timeline_chart(rows)}</svg>
</main></body></html>"""
    return html


def build():
    """Пересобирает taxi_report.html. Возвращает False, если строить пока не из чего."""
    html = render()
    if html is None:
        return False
    HTML_PATH.write_text(html, encoding="utf-8")
    return True


def watch():
    """Пересобирает отчёт, как только taxi_prices.csv изменился."""
    print(f"Слежу за {CSV_PATH.name}, отчёт: {HTML_PATH}  (Ctrl+C — выход)")
    last = None
    while True:
        mtime = CSV_PATH.stat().st_mtime if CSV_PATH.exists() else None
        if mtime != last:
            last = mtime
            try:
                if build():
                    print(f"{datetime.now():%Y-%m-%d %H:%M}  отчёт обновлён")
            except Exception as e:
                print(f"{datetime.now():%Y-%m-%d %H:%M}  ошибка: {e}")
        time.sleep(30)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--watch" in sys.argv:
        return watch()
    if not build():
        print("В taxi_prices.csv пока нет замеров с ценой.")
        return
    print(f"Отчёт сохранён: {HTML_PATH}")
    if "--no-open" not in sys.argv:
        webbrowser.open(HTML_PATH.as_uri())


if __name__ == "__main__":
    main()
