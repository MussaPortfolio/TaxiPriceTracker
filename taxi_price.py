"""Раз в 20 минут берёт цену Яндекс Такси (эконом) со страницы маршрута
в Яндекс Картах и дописывает её в taxi_prices.csv.

Маршрут задаётся при запуске координатами "широта,долгота" начала и конца:

    python taxi_price.py 55.752023,37.617499 55.749633,37.537434
    python taxi_price.py 55.752023,37.617499 55.749633,37.537434 --once

Без координат скрипт спросит их сам. Остановить: Ctrl+C.
"""
import csv
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import taxi_report

INTERVAL_MIN = 20

URL = "https://yandex.ru/maps/?mode=routes&rtext={start}~{end}&rtt=taxi"
COORD_RE = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}
CSV_PATH = Path(__file__).with_name("taxi_prices.csv")
FIELDS = ["время", "цена_руб", "подача_мин", "в_пути_мин", "повышенный_спрос", "ошибка"]


def parse_point(text):
    """"55.75, 37.61" -> "55.75,37.61"; None, если это не координаты."""
    m = COORD_RE.match(text)
    if not m or abs(float(m[1])) > 90 or abs(float(m[2])) > 180:
        return None
    return f"{m[1]},{m[2]}"


def ask_point(prompt):
    while True:
        point = parse_point(input(prompt))
        if point:
            return point
        print("  нужны координаты вида 55.752023,37.617499 "
              "(в Яндекс Картах: правый клик по месту → «Что здесь?»)")


def get_route():
    """Маршрут из аргументов командной строки, а если их нет — спрашиваем."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        points = [parse_point(a) for a in args]
        if len(points) != 2 or None in points:
            sys.exit("Укажите две точки: python taxi_price.py 55.752023,37.617499 55.749633,37.537434")
        return points
    return ask_point("Откуда (широта,долгота): "), ask_point("Куда (широта,долгота): ")


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        final_url = r.geturl()
        html = r.read().decode("utf-8", "ignore")
    if "showcaptcha" in final_url:
        raise RuntimeError("Яндекс показал капчу")
    m = re.search(r'"taxiInfo":(\{.*?\})', html)
    if not m:
        raise RuntimeError("цена не найдена на странице")
    info = json.loads(m.group(1))
    price = int(re.sub(r"\D", "", info["priceText"]))
    return {
        "цена_руб": price,
        "подача_мин": info.get("waitingTime", ""),
        "в_пути_мин": round(info["time"] / 60) if info.get("time") else "",
        "повышенный_спрос": "да" if info.get("isSurge") else "нет",
    }


def save(row):
    new = not CSV_PATH.exists()
    # utf-8-sig и ";" — чтобы файл сразу нормально открывался в Excel
    with CSV_PATH.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, FIELDS, delimiter=";")
        if new:
            w.writeheader()
        w.writerow(row)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    once = "--once" in sys.argv  # для Планировщика заданий: один замер и выход
    start, end = get_route()
    url = URL.format(start=start, end=end)
    print(f"Маршрут: {start} → {end}, замер каждые {INTERVAL_MIN} мин")
    while True:
        row = {"время": datetime.now().strftime("%Y-%m-%d %H:%M")}
        try:
            row.update(fetch(url))
            print(f"{row['время']}  {row['цена_руб']} ₽  подача {row['подача_мин']} мин"
                  f"{'  (повышенный спрос)' if row['повышенный_спрос'] == 'да' else ''}")
        except Exception as e:
            row["ошибка"] = str(e)
            print(f"{row['время']}  ошибка: {e}")
        save(row)
        try:
            taxi_report.build()  # отчёт taxi_report.html обновляется после каждого замера
        except Exception as e:
            print(f"не удалось обновить отчёт: {e}")
        if once:
            break
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
