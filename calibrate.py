"""
Одноразове калібрування: робимо знімок усього екрана і просимо тебе
виділити мишкою РІВНО ігрове поле 4x4 (від зовнішнього краю верхньої-лівої
клітинки до зовнішнього краю нижньої-правої клітинки, без рахунку/кнопок).

Запуск:  python calibrate.py
Керування у вікні вибору: затиснути ЛКМ і виділити прямокутник, ENTER для
підтвердження, C щоб почати заново.
"""

import cv2
import numpy as np
import mss

from config import save_region


def main():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # головний монітор; зміни індекс, якщо в тебе кілька
        shot = np.array(sct.grab(monitor))

    img_bgr = cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)

    print("Виділи прямокутником ігрове поле 4x4 (без заголовка 'Рахунок/Рекорд').")
    print("ENTER або SPACE — підтвердити, C — скасувати виділення, ESC — скасувати все.")

    r = cv2.selectROI("Виділи ігрове поле 2048 (ENTER = ок)", img_bgr, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, w, h = r
    if w == 0 or h == 0:
        print("Виділення не зроблено, вихід без збереження.")
        return

    save_region((int(x), int(y), int(w), int(h)))
    print(f"Збережено область: x={x}, y={y}, w={w}, h={h}")
    print("Готово! Тепер можна запускати: python main.py")


if __name__ == "__main__":
    main()
