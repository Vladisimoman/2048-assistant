"""
Маленьке завжди-зверху віконце зі стрілкою рекомендованого ходу.

Кольори:
- зелений  -- хід порахований, можна тиснути (або автогра щойно натиснула)
- червоний -- щойно виявлено новий стан поля, рахується наступний хід
- сірий    -- не бачу поле чітко

Внизу невеликий напис показує стан автогри (F9 щоб перемкнути).
"""

import tkinter as tk

ARROWS = {"up": "↑", "down": "↓", "left": "←", "right": "→"}

COLOR_READY = "#39ff88"
COLOR_CALCULATING = "#ff4d4d"
COLOR_UNKNOWN = "#888888"


class Overlay:
    def __init__(self, x, y):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # без рамки/заголовка
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)
        self.root.configure(bg="black")

        size = 100
        self.root.geometry(f"{size}x{size}+{x}+{y}")

        self.label = tk.Label(
            self.root,
            text="…",
            font=("Segoe UI", 40, "bold"),
            fg=COLOR_UNKNOWN,
            bg="black",
        )
        self.label.pack(expand=True, fill="both", pady=(6, 0))

        self.info = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 8),
            fg="#aaaaaa",
            bg="black",
        )
        self.info.place(relx=0.5, rely=0.80, anchor="s")

        self.auto_label = tk.Label(
            self.root,
            text="AUTO: off (F9)",
            font=("Segoe UI", 8, "bold"),
            fg="#666666",
            bg="black",
        )
        self.auto_label.place(relx=0.5, rely=0.98, anchor="s")

        # дозволяє перетягнути вікно мишкою, якщо заважає
        self.label.bind("<Button-1>", self._start_move)
        self.label.bind("<B1-Motion>", self._on_move)

    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_move(self, event):
        x = self.root.winfo_pointerx() - self._drag_x
        y = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def set_calculating(self):
        """Хід щойно застосовано (кимось), рахуємо наступний -- показуємо червоне."""
        self.label.config(fg=COLOR_CALCULATING)
        self.info.config(text="рахую...")

    def set_unknown(self, text="не бачу поле чітко"):
        self.label.config(text="?", fg=COLOR_UNKNOWN)
        self.info.config(text=text)

    def set_move(self, move, extra_text=""):
        if move is None:
            self.label.config(text="✕", fg=COLOR_UNKNOWN)
            self.info.config(text=extra_text or "немає ходів")
            return
        self.label.config(text=ARROWS.get(move, "?"), fg=COLOR_READY)
        self.info.config(text=extra_text)

    def set_auto_state(self, enabled):
        if enabled:
            self.auto_label.config(text="AUTO: ON (F9)", fg="#39ff88")
        else:
            self.auto_label.config(text="AUTO: off (F9)", fg="#666666")

    def update(self):
        self.root.update_idletasks()
        self.root.update()
