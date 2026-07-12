"""
Конфігурація 2048-Assistant.
Тут зберігаються шляхи та параметри, які можна підлаштувати під себе.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "region_config.json")

# Шлях до tesseract.exe (потрібно встановити окремо на Windows, див. README.md)
# Приклад: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Скільки разів на секунду опитувати екран
POLL_INTERVAL_SEC = 0.4

# Скільки послідовних однакових зчитувань поля вважати "стабільним"
# (щоб не ловити кадр посеред анімації зсуву плиток)
STABLE_READS_REQUIRED = 2

# Файл, куди пишеться статистика появи нових плиток
SPAWN_LOG_PATH = os.path.join(os.path.dirname(__file__), "spawn_log.csv")


def load_region():
    """Повертає (x, y, w, h) області ігрового поля 4x4 або None, якщо ще не калібровано."""
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return tuple(data["region"])


def save_region(region):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"region": list(region)}, f)
