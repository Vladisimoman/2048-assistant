# 2048 Assistant: real-time move advisor and autoplayer

A desktop tool that reads a live 2048 board from the screen, recognizes the 4×4 grid and shows the best next move in a small always-on-top overlay. It can also play on its own (F9) and logs every new tile (2 or 4) to a CSV file for analysis.

It was built for 2048 running on an Android phone mirrored to Windows through Phone Link, but it works with any 2048 board visible on screen, including browser versions.

## How it works

1. **Screen capture** (`mss`) grabs only the calibrated board region.
2. **Board recognition** (`board_reader.py`, `templates.py`): each cell is classified as empty or not, and digits are read with OpenCV template matching. Tesseract OCR is used only for the first few occurrences of each new value, after which the cell image becomes a template.
3. **Solver** (`solver.py`): Expectimax search. Player moves are "max" nodes; new tile spawns (2 with 90%, 4 with 10%) are "chance" nodes. Positions are scored on monotonicity, smoothness, free cells and keeping the largest tile in a corner. Search depth adapts to the number of free cells and is capped by a time budget so the overlay stays responsive.
4. **Overlay** (`overlay.py`): a small arrow shows the suggested move.
5. **Autoplay** (`autoplay.py`): sends arrow keys for browser versions, or simulates swipes with the mouse for the mirrored phone.

## Installation

### Python dependencies
```
pip install -r requirements.txt
```

### Tesseract OCR (separate program, not installed via pip)
1. Download the Windows installer: https://github.com/UB-Mannheim/tesseract/wiki
2. Install it (default: `C:\Program Files\Tesseract-OCR\`).
3. If needed, update `TESSERACT_CMD` in `config.py` to the actual path of `tesseract.exe`.

## Calibration (once, or whenever the window size or position changes)

1. Open the game so the board is clearly visible.
2. Run:
   ```
   python calibrate.py
   ```
3. Select exactly the 4×4 board with the mouse, from the outer edge of the top-left cell to the outer edge of the bottom-right cell. Do not include the score or buttons.
4. Press ENTER. The region is saved to `region_config.json`.

## Running

```
python main.py
```

A small black overlay with an arrow appears next to the board. It stays on top and can be dragged.

**Arrow colours:**
- 🟢 green: move calculated, ready to play
- 🔴 red: the board just changed, the next move is being calculated
- ⚪ grey / `?`: the board cannot be recognized

**Autoplay (F9):** press F9 (works globally) to let the program play; press F9 again to stop. The overlay shows `AUTO: ON` / `AUTO: off`.

- For browser versions that accept arrow keys (for example play2048.co), set `AUTOPLAY_INPUT_MODE = "keys"` in `config.py`.
- For the mirrored phone, the game only reacts to swipes, so autoplay simulates mouse swipes over the board using the low-level Windows API (`SetCursorPos` + `mouse_event`) and focuses the Phone Link window first. If your mirroring window has a different title, add it to `WINDOW_TITLE_KEYWORDS` in `autoplay.py`. Check a few moves before trusting a whole game to autoplay.

**Emergency stop:** move the mouse to the top-left corner of the screen (the built-in `pyautogui` failsafe). Stop the program with Ctrl+C in the console.

## Temporary occlusions

The program remembers the last successfully recognized value of each cell. If a cell suddenly becomes unreadable (a finger, the cursor, a cat's paw), it keeps the last known value instead of marking the board as unknown, and reads the real value again as soon as the cell is clear.

## Tile spawn statistics

After a few games:
```
python spawn_logger.py
```
This shows the share of 2s versus 4s and their distribution across the board. Raw data: `spawn_log.csv`.

## Troubleshooting

- **Empty cells detected as filled (or the opposite):** tune `EMPTY_WHITE_RATIO_THRESHOLD` in `board_reader.py` (a higher value is less sensitive to small light artifacts).
- **Digits misread:** make sure the calibrated region matches the board edges exactly and the game window is large enough; bigger cells read better.
- **"Board not clear" does not go away:** check `debug_cells/`, where unrecognized cells are saved (original and the image prepared for OCR).

## A note on "predicting" new tiles

In classic 2048 a new tile (2 with 90% probability, 4 with 10%) appears on a random free cell, chosen by the game's pseudo-random generator. It cannot be predicted from the outside without access to the generator's internal state. The spawn log lets you check the real distribution, while the solver deliberately uses Expectimax, which accounts for these probabilities directly.

## Tech

Python · OpenCV · Tesseract OCR (pytesseract) · mss · NumPy · pyautogui · keyboard
