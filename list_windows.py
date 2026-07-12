"""
Допоміжний скрипт: виводить заголовки всіх видимих вікон, щоб знайти точну
назву вікна дзеркалення телефону для autoplay.py -> WINDOW_TITLE_KEYWORDS.

Запуск:  python list_windows.py

Відкрий вікно "Зв'язок зі смартфоном" (нехай воно буде видиме на екрані)
перед запуском, знайди його в списку і скопіюй точний або частину заголовка
у autoplay.py.
"""

import ctypes

user32 = ctypes.windll.user32


def main():
    titles = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if title:
            titles.append(title)
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)

    print(f"Знайдено {len(titles)} видимих вікон:\n")
    for t in titles:
        print(f"  - {t}")

    print("\nЗнайди серед них вікно дзеркалення телефону (наприклад, з чимось")
    print("схожим на 'Зв'язок зі смартфоном' або 'Phone Link') і додай слово")
    print("з нього (малими літерами) у список WINDOW_TITLE_KEYWORDS у autoplay.py")


if __name__ == "__main__":
    main()
