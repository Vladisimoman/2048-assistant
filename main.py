"""
Запуск: python main.py

Перед першим запуском обов'язково виконай: python calibrate.py

Керування:
- F9 -- увімкнути/вимкнути автогру (програма сама натискає стрілки)
- Ctrl+C у консолі -- зупинити програму
"""

import time
import sys

from config import load_region, POLL_INTERVAL_SEC, STABLE_READS_REQUIRED
from board_reader import read_board
from solver import best_move, apply_move
from spawn_logger import log_new_tiles
from overlay import Overlay
from autoplay import AutoPlayer


def board_has_unknown(board):
    return any(cell == -1 for row in board for cell in row)


def empty_last_known():
    return [[0] * 4 for _ in range(4)]


def merge_known(last_known, board):
    """Оновлює last_known по кожній клітинці, де вдалось отримати реальне значення."""
    for r in range(4):
        for c in range(4):
            if board[r][c] != -1:
                last_known[r][c] = board[r][c]


def main():
    region = load_region()
    if region is None:
        print("Область гри ще не відкалібрована.")
        print("Спочатку запусти: python calibrate.py")
        sys.exit(1)

    x, y, w, h = region
    overlay = Overlay(x + w + 15, y)

    autoplayer = AutoPlayer(region)
    overlay.set_auto_state(autoplayer.enabled)
    last_auto_state = autoplayer.enabled

    last_stable_board = None
    last_seen_board = None
    stable_count = 0
    predicted_next_board = None  # для логування появи нових плиток
    last_known = empty_last_known()  # останнє відоме значення кожної клітинки (для оклюзій)
    unknown_streak = 0
    UNKNOWN_STREAK_TO_WARN = 4

    print("Старт. Ctrl+C у консолі -- зупинити. F9 -- перемкнути автогру.")
    print(f"Область поля: {region}")

    try:
        while True:
            # Стан автогри міняється у ФОНОВОМУ потоці (обробка гарячої
            # клавіші keyboard). Tkinter не можна чіпати з іншого потоку,
            # тому оновлюємо індикатор тут, у головному циклі.
            if autoplayer.enabled != last_auto_state:
                overlay.set_auto_state(autoplayer.enabled)
                last_auto_state = autoplayer.enabled

            board = read_board(region, previous_values=last_known)
            merge_known(last_known, board)

            if board_has_unknown(board):
                unknown_streak += 1
                if unknown_streak >= UNKNOWN_STREAK_TO_WARN:
                    overlay.set_unknown()
                    overlay.update()
                time.sleep(POLL_INTERVAL_SEC * 0.5)
                continue
            unknown_streak = 0

            if last_seen_board is not None and board == last_seen_board:
                stable_count += 1
            else:
                stable_count = 1
                # Поле щойно змінилось (хтось/щось зробило хід) -- показуємо
                # "рахую" одразу, ще до того як порахуємо новий хід.
                if last_stable_board is not None:
                    overlay.set_calculating()
                    overlay.update()
            last_seen_board = board

            if stable_count >= STABLE_READS_REQUIRED and board != last_stable_board:
                if predicted_next_board is not None:
                    log_new_tiles(predicted_next_board, board, None)

                move, scores = best_move(board)
                free = sum(r.count(0) for r in board)

                if move is None:
                    overlay.set_move(None, "гра закінчена?")
                    predicted_next_board = None
                else:
                    overlay.set_move(move, f"вільних: {free}")
                    simulated, _, _ = apply_move(board, move)
                    predicted_next_board = simulated

                    if autoplayer.enabled:
                        # невелика пауза перед натисканням -- даємо анімації
                        # попереднього ходу точно завершитись
                        time.sleep(0.05)
                        autoplayer.send_move(move)

                last_stable_board = board

            overlay.update()
            time.sleep(POLL_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("Зупинено користувачем.")


if __name__ == "__main__":
    main()
