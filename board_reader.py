"""
Захоплення області екрана та розпізнавання стану поля 2048 (матриця 4x4).

Логіка на клітинку:
1. Вирізаємо клітинку з невеликим внутрішнім відступом (щоб уникнути країв
   плитки/сітки).
2. Шукаємо БІЛІ пікселі цифри за кольором (HSV: висока яскравість V,
   низька насиченість S) -- це працює однаково для будь-якого кольору фону
   плитки (синій, помаранчевий, фіолетовий), на відміну від порогу за
   загальною яскравістю, який плутається на яскравих плитках.
3. Якщо білих пікселів майже немає -- клітинка порожня.
4. Інакше -- готуємо чорний текст на білому тлі (як любить Tesseract) і
   пробуємо кілька режимів розпізнавання.
"""

import os
import time

import numpy as np
import cv2
import mss
import pytesseract

from config import TESSERACT_CMD

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

GRID_SIZE = 4

# Внутрішній відступ клітинки (частка від розміру клітинки з кожного боку).
# Якщо великі двозначні числа (16/32/64/128...) обрізаються -- зменш це значення.
CELL_PADDING_RATIO = 0.10

# Поріг частки "білих" пікселів у клітинці, нижче якого вважаємо клітинку порожньою.
EMPTY_WHITE_RATIO_THRESHOLD = 0.015

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug_cells")
DEBUG_SAVE_UNKNOWN = True  # зберігати картинки клітинок, які не вдалось розпізнати


def grab_region(region):
    x, y, w, h = region
    with mss.mss() as sct:
        shot = np.array(sct.grab({"left": x, "top": y, "width": w, "height": h}))
    return cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)


def _split_cells(img_bgr):
    h, w = img_bgr.shape[:2]
    cell_h, cell_w = h / GRID_SIZE, w / GRID_SIZE
    cells = []
    for row in range(GRID_SIZE):
        row_cells = []
        for col in range(GRID_SIZE):
            y0 = int(row * cell_h)
            y1 = int((row + 1) * cell_h)
            x0 = int(col * cell_w)
            x1 = int((col + 1) * cell_w)
            pad_y = int((y1 - y0) * CELL_PADDING_RATIO)
            pad_x = int((x1 - x0) * CELL_PADDING_RATIO)
            cell = img_bgr[y0 + pad_y:y1 - pad_y, x0 + pad_x:x1 - pad_x]
            row_cells.append(cell)
        cells.append(row_cells)
    return cells


def _extract_white_text_mask(cell_bgr):
    """Виділяє білі пікселі цифри за кольором, незалежно від кольору фону
    плитки. Додатково прибирає дрібні шумові фрагменти (лапи/шерсть кота,
    відблиски), які інколи залазять у клітинку -- цифра зазвичай суцільна й
    відносно велика, а шум -- дрібний і роз'єднаний.
    Повертає (clean_mask, clean_ratio, raw_mask, raw_ratio)."""
    hsv = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    raw_mask = ((v > 170) & (s < 90)).astype(np.uint8) * 255
    raw_ratio = float(np.mean(raw_mask == 255))

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(raw_mask, connectivity=8)
    total_area = raw_mask.shape[0] * raw_mask.shape[1]
    min_component_area = total_area * 0.02  # менше 2% площі клітинки -- вважаємо шумом

    clean_mask = np.zeros_like(raw_mask)
    for label_id in range(1, num_labels):  # 0 -- фон
        area = stats[label_id, cv2.CC_STAT_AREA]
        if area >= min_component_area:
            clean_mask[labels == label_id] = 255

    clean_ratio = float(np.mean(clean_mask == 255))
    return clean_mask, clean_ratio, raw_mask, raw_ratio


def _prep_for_ocr(mask):
    """mask: 255 = піксель цифри, 0 = фон.
    Готує чорний текст на білому тлі -- формат, який Tesseract читає найкраще."""
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)  # трохи потовщуємо штрихи

    big = cv2.resize(mask, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, big = cv2.threshold(big, 127, 255, cv2.THRESH_BINARY)

    inverted = cv2.bitwise_not(big)  # чорний текст на білому
    bordered = cv2.copyMakeBorder(
        inverted, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
    )
    return bordered


def _ocr_digits(img):
    """Пробує кілька режимів Tesseract, повертає перший непустий результат цифр."""
    configs = [
        "--psm 8 -c tessedit_char_whitelist=0123456789",   # окреме слово
        "--psm 10 -c tessedit_char_whitelist=0123456789",  # один символ
        "--psm 7 -c tessedit_char_whitelist=0123456789",   # один рядок
    ]
    for config in configs:
        text = pytesseract.image_to_string(img, config=config).strip()
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            return digits
    return ""


def _save_debug(cell_bgr, ocr_img, row, col, reason):
    if not DEBUG_SAVE_UNKNOWN:
        return
    os.makedirs(DEBUG_DIR, exist_ok=True)
    ts = int(time.time() * 1000)
    base = os.path.join(DEBUG_DIR, f"{ts}_r{row}c{col}_{reason}")
    cv2.imwrite(base + "_orig.png", cell_bgr)
    if ocr_img is not None:
        cv2.imwrite(base + "_ocrimg.png", ocr_img)


def _read_cell_value(cell_bgr, row=-1, col=-1, fallback_value=None):
    clean_mask, clean_ratio, raw_mask, raw_ratio = _extract_white_text_mask(cell_bgr)

    if raw_ratio < EMPTY_WHITE_RATIO_THRESHOLD:
        return 0  # порожня клітинка

    # Спочатку пробуємо очищену від шуму маску (найкраща якість).
    digits = ""
    if clean_ratio >= EMPTY_WHITE_RATIO_THRESHOLD:
        ocr_img = _prep_for_ocr(clean_mask)
        digits = _ocr_digits(ocr_img)

    # Якщо фільтр шуму прибрав забагато (наприклад, цифра сама по собі
    # дрібна через неточну обрізку клітинки) -- пробуємо ще раз на сирій,
    # нефільтрованій масці.
    if not digits:
        ocr_img = _prep_for_ocr(raw_mask)
        digits = _ocr_digits(ocr_img)

    if not digits:
        _save_debug(cell_bgr, ocr_img, row, col, "unknown")
        # Не вдалось розпізнати -- ймовірно, щось тимчасово закриває цифру
        # (лапка кота, курсор миші тощо) або кадр невдало обрізаний.
        # Якщо знаємо попереднє значення цієї клітинки -- використовуємо
        # його замість того, щоб позначати "невідомо".
        if fallback_value:
            return fallback_value
        return -1  # заповнена, попереднього значення немає -- справді невідомо

    return int(digits)


def read_board(region, previous_values=None):
    """Повертає 4x4 список int: 0 = порожньо, -1 = не вдалось розпізнати.

    previous_values: опційна 4x4 матриця останніх ВІДОМИХ (не -1) значень
    кожної клітинки -- використовується як fallback при тимчасовій оклюзії.
    """
    img = grab_region(region)
    cells = _split_cells(img)
    board = []
    for r in range(GRID_SIZE):
        row_vals = []
        for c in range(GRID_SIZE):
            fallback = previous_values[r][c] if previous_values else None
            val = _read_cell_value(cells[r][c], r, c, fallback_value=fallback)
            row_vals.append(val)
        board.append(row_vals)
    return board
