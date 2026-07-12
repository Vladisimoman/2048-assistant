"""
Автогра: за замовчуванням вимкнена. Натискання F9 (глобально, навіть якщо
фокус на вікні "Зв'язок зі смартфоном") перемикає режим.

Гра реагує лише на СВАЙПИ (дотики), а не на клавіші-стрілки, тому автогра
симулює свайп мишкою прямо по області ігрового поля на екрані.

Використовує низькорівневий Windows API (ctypes: SetCursorPos + mouse_event)
замість pyautogui/SendInput -- деякі сучасні (UWP) застосунки типу
"Зв'язок зі смартфоном" по-різному обробляють ці два джерела синтетичного
вводу, і mouse_event інколи спрацьовує там, де SendInput ігнорується.
Перед кожним свайпом програма також намагається явно перевести фокус на
вікно застосунку дзеркалення.
"""

import ctypes
import ctypes.wintypes
import time

import keyboard

user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

TOGGLE_HOTKEY = "f9"

SWIPE_DURATION_SEC = 0.15
SWIPE_STEPS = 16
SWIPE_MARGIN_RATIO = 0.18
PRE_MOVE_PAUSE_SEC = 0.06
POST_MOVE_PAUSE_SEC = 0.06

# Ключові слова в заголовку вікна дзеркалення телефону -- підлаштуй, якщо
# в тебе інша назва застосунку/мова системи.
WINDOW_TITLE_KEYWORDS = [
    "зв'язок зі смартфоном",
    "зв'язок із смартфоном",
    "phone link",
    "your phone",
    "ваш телефон",
    "A24 користувача Fedunyshyn",
]

FAILSAFE_CORNER = 5  # якщо курсор опиниться менш ніж за 5px від (0,0) -- аварійна зупинка


def _set_cursor_pos(x, y):
    user32.SetCursorPos(int(x), int(y))


def _get_cursor_pos():
    pt = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _mouse_down():
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)


def _mouse_up():
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def _find_window_by_keywords(keywords):
    found = {"hwnd": None}

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.lower()
        for kw in keywords:
            if kw in title:
                found["hwnd"] = hwnd
                return False
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)
    return found["hwnd"]


def _focus_window(hwnd):
    if not hwnd:
        return False
    try:
        user32.ShowWindow(hwnd, 5)  # SW_SHOW
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


class AutoPlayer:
    def __init__(self, region):
        """region: (x, y, w, h) -- область ігрового поля на екрані (з калібрування)."""
        self.enabled = False
        self.region = region
        self._target_hwnd = None
        keyboard.add_hotkey(TOGGLE_HOTKEY, self._toggle)

    def _toggle(self):
        self.enabled = not self.enabled
        state = "УВІМКНЕНО" if self.enabled else "вимкнено"
        print(f"[Автогра] {state} ({TOGGLE_HOTKEY.upper()} щоб перемкнути знову)")
        if self.enabled and self._target_hwnd is None:
            self._target_hwnd = _find_window_by_keywords(WINDOW_TITLE_KEYWORDS)
            if self._target_hwnd is None:
                print("[Автогра] Увага: не знайшов вікно дзеркалення телефону за "
                      "заголовком. Свайп все одно спробує спрацювати за координатами, "
                      "але без явного фокусування вікна.")

    def _swipe_points(self, move):
        x, y, w, h = self.region
        cx, cy = x + w / 2, y + h / 2
        mx, my = w * SWIPE_MARGIN_RATIO, h * SWIPE_MARGIN_RATIO

        if move == "up":
            return (cx, y + h - my), (cx, y + my)
        if move == "down":
            return (cx, y + my), (cx, y + h - my)
        if move == "left":
            return (x + w - mx, cy), (x + mx, cy)
        if move == "right":
            return (x + mx, cy), (x + w - mx, cy)
        raise ValueError(f"Невідомий хід: {move}")

    def _failsafe_triggered(self):
        x, y = _get_cursor_pos()
        return x <= FAILSAFE_CORNER and y <= FAILSAFE_CORNER

    def send_move(self, move):
        try:
            start, end = self._swipe_points(move)
        except ValueError:
            return

        if self._target_hwnd is None:
            self._target_hwnd = _find_window_by_keywords(WINDOW_TITLE_KEYWORDS)
        _focus_window(self._target_hwnd)
        time.sleep(0.03)  # дати вікну час прийняти фокус

        if self._failsafe_triggered():
            return

        sx, sy = start
        ex, ey = end

        _set_cursor_pos(sx, sy)
        time.sleep(0.02)
        _mouse_down()
        time.sleep(PRE_MOVE_PAUSE_SEC)

        for i in range(1, SWIPE_STEPS + 1):
            if self._failsafe_triggered():
                _mouse_up()
                return
            nx = sx + (ex - sx) * i / SWIPE_STEPS
            ny = sy + (ey - sy) * i / SWIPE_STEPS
            _set_cursor_pos(nx, ny)
            time.sleep(SWIPE_DURATION_SEC / SWIPE_STEPS)

        time.sleep(POST_MOVE_PAUSE_SEC)
        _mouse_up()
