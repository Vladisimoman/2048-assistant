"""
Порівнює попередній та новий стан поля, знаходить клітинку(и), де з'явилась
нова плитка (2 або 4), і дописує запис у CSV для подальшого аналізу
(розподіл значень, розподіл по позиціях тощо).
"""

import csv
import os
import time

from config import SPAWN_LOG_PATH


def _ensure_header():
    if not os.path.exists(SPAWN_LOG_PATH):
        with open(SPAWN_LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "row", "col", "value", "free_cells_before"])


def log_new_tiles(prev_board, new_board, prev_move):
    """Викликати ПІСЛЯ ходу: знаходить клітинки, які були 0 у prev_board
    (в позиції ПІСЛЯ симуляції ходу) і стали ненульовими у new_board."""
    _ensure_header()
    free_before = sum(1 for r in range(4) for c in range(4) if prev_board[r][c] == 0)

    rows = []
    for r in range(4):
        for c in range(4):
            if prev_board[r][c] == 0 and new_board[r][c] not in (0, -1):
                rows.append((r, c, new_board[r][c]))

    if not rows:
        return  # нічого нового не з'явилось (або не вдалось однозначно визначити)

    with open(SPAWN_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r, c, val in rows:
            writer.writerow([time.time(), r, c, val, free_before])


def summarize():
    """Швидка статистика: частка 2 проти 4, розподіл по клітинках."""
    if not os.path.exists(SPAWN_LOG_PATH):
        print("Лог поки порожній.")
        return

    counts = {2: 0, 4: 0}
    cell_counts = {}
    with open(SPAWN_LOG_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = int(row["value"])
            if val in counts:
                counts[val] += 1
            key = (row["row"], row["col"])
            cell_counts[key] = cell_counts.get(key, 0) + 1

    total = counts[2] + counts[4]
    if total == 0:
        print("Даних ще недостатньо.")
        return

    print(f"Всього зафіксовано появ: {total}")
    print(f"  2: {counts[2]} ({counts[2] / total:.1%})")
    print(f"  4: {counts[4]} ({counts[4] / total:.1%})")
    print("Розподіл по клітинках (row,col -> кількість):")
    for key, cnt in sorted(cell_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {key}: {cnt}")


if __name__ == "__main__":
    summarize()
