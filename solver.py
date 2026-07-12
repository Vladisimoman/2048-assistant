"""
Expectimax-солвер для 2048.

Хід гравця (UP/DOWN/LEFT/RIGHT) -- вузол "max" (обираємо найкращий).
Поява нової плитки (2 з ймов. 0.9, 4 з ймов. 0.1 на випадковій вільній
клітинці) -- вузол "chance" (усереднюємо по ймовірностях).

Евристики оцінки позиції:
- monotonicity: рядки/стовпці мають бути монотонними (зростання/спадання)
- smoothness: сусідні клітинки не повинні сильно відрізнятись
- free_cells: більше вільних клітинок -- краще
- max_in_corner: бонус, якщо найбільша плитка в кутку

Глибина пошуку адаптується до кількості вільних клітинок, а виконання ще й
обмежене часовим бюджетом (щоб підказка в оверлеї не гальмувала).
"""

import time
import math

MOVES = ["up", "down", "left", "right"]


def _compress_and_merge_line(line):
    """Застосовує рух вліво до одного рядка (list із 4 int, 0 = порожньо).
    Повертає (новий рядок, здобуті очки)."""
    vals = [v for v in line if v != 0]
    merged = []
    score = 0
    i = 0
    while i < len(vals):
        if i + 1 < len(vals) and vals[i] == vals[i + 1]:
            merged_val = vals[i] * 2
            merged.append(merged_val)
            score += merged_val
            i += 2
        else:
            merged.append(vals[i])
            i += 1
    merged += [0] * (4 - len(merged))
    return merged, score


def _rotate_board_for_move(board, move):
    """Зводимо будь-який напрямок руху до 'руху вліво' через транспонування/реверс."""
    if move == "left":
        return [row[:] for row in board]
    if move == "right":
        return [row[::-1] for row in board]
    if move == "up":
        return [list(row) for row in zip(*board)]
    if move == "down":
        return [list(row)[::-1] for row in zip(*board)]
    raise ValueError(move)


def _unrotate_board_after_move(board, move):
    if move == "left":
        return [row[:] for row in board]
    if move == "right":
        return [row[::-1] for row in board]
    if move == "up":
        return [list(row) for row in zip(*board)]
    if move == "down":
        rev = [row[::-1] for row in board]
        return [list(row) for row in zip(*rev)]
    raise ValueError(move)


def apply_move(board, move):
    """Повертає (новий_board, здобуті_очки, чи_щось_змінилось)."""
    rotated = _rotate_board_for_move(board, move)
    new_rotated = []
    total_score = 0
    for row in rotated:
        new_row, score = _compress_and_merge_line(row)
        new_rotated.append(new_row)
        total_score += score
    new_board = _unrotate_board_after_move(new_rotated, move)
    changed = new_board != board
    return new_board, total_score, changed


def empty_cells(board):
    return [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]


def _monotonicity(board):
    def line_mono(line):
        increasing = decreasing = 0
        for i in range(3):
            a, b = line[i], line[i + 1]
            if a > b:
                decreasing += math.log2(a + 1) - math.log2(b + 1) if b else math.log2(a + 1)
            elif b > a:
                increasing += math.log2(b + 1) - math.log2(a + 1) if a else math.log2(b + 1)
        return -min(increasing, decreasing)

    total = 0.0
    for r in range(4):
        total += line_mono(board[r])
    for c in range(4):
        total += line_mono([board[r][c] for r in range(4)])
    return total


def _smoothness(board):
    total = 0.0
    for r in range(4):
        for c in range(4):
            if board[r][c] == 0:
                continue
            val = math.log2(board[r][c])
            if c + 1 < 4 and board[r][c + 1] != 0:
                total -= abs(val - math.log2(board[r][c + 1]))
            if r + 1 < 4 and board[r + 1][c] != 0:
                total -= abs(val - math.log2(board[r + 1][c]))
    return total


def _max_in_corner_bonus(board):
    flat = [board[r][c] for r in range(4) for c in range(4)]
    max_val = max(flat)
    corners = [board[0][0], board[0][3], board[3][0], board[3][3]]
    return max_val if max_val in corners else 0


def evaluate(board):
    free = len(empty_cells(board))
    score = 0.0
    score += _monotonicity(board) * 1.0
    score += _smoothness(board) * 0.15
    score += math.log2(free + 1) * 2.7 if free else -10.0
    score += _max_in_corner_bonus(board) * 0.02
    return score


def _search_depth_for(free_count):
    if free_count >= 8:
        return 2
    if free_count >= 5:
        return 3
    if free_count >= 2:
        return 4
    return 5


def _expectimax(board, depth, is_player_turn, deadline):
    if time.time() > deadline or depth == 0:
        return evaluate(board)

    if is_player_turn:
        best = -math.inf
        any_move = False
        for move in MOVES:
            new_board, _, changed = apply_move(board, move)
            if not changed:
                continue
            any_move = True
            val = _expectimax(new_board, depth - 1, False, deadline)
            best = max(best, val)
        if not any_move:
            return evaluate(board)  # програш/глухий кут
        return best
    else:
        cells = empty_cells(board)
        if not cells:
            return evaluate(board)
        # Для швидкості, якщо клітинок багато -- семплюємо підмножину
        sample = cells if len(cells) <= 6 else cells[:6]
        total = 0.0
        weight_sum = 0.0
        for (r, c) in sample:
            for val, prob in ((2, 0.9), (4, 0.1)):
                b2 = [row[:] for row in board]
                b2[r][c] = val
                total += prob * _expectimax(b2, depth - 1, True, deadline)
                weight_sum += prob
        return total / weight_sum if weight_sum else evaluate(board)


def best_move(board, time_budget_sec=0.35):
    """Повертає ('up'|'down'|'left'|'right'|None, debug_scores_dict)."""
    free_count = len(empty_cells(board))
    depth = _search_depth_for(free_count)
    deadline = time.time() + time_budget_sec

    scores = {}
    for move in MOVES:
        new_board, _, changed = apply_move(board, move)
        if not changed:
            continue
        scores[move] = _expectimax(new_board, depth - 1, False, deadline)

    if not scores:
        return None, scores
    return max(scores, key=scores.get), scores
