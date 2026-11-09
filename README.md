# RecoilLab

Windows 11 desktop toolkit in Python with two apps.

- **RecoilLab** - Cartesian/polar mouse displacement simulator with a live graph, undo, history and CSV export. Apply can move the real cursor, with a global hotkey.
- **Recoil Canceller** - while enabled and the left mouse button is held, moves the cursor down at a constant rate (default 142.5 px/s), smoothly and linearly.

## Requirements

- Windows 10/11
- Python 3.10+ (added to PATH)
- `customtkinter`, `matplotlib` (installed from `requirements.txt`)

## Run

Double-click:

- `Run.bat` - RecoilLab
- `Recoil Canceller.bat` - Recoil Canceller

Or manually:

```
pip install -r requirements.txt
python main.py
python recoil_canceller.py
```

## RecoilLab usage

1. Pick Cartesian (X right +, Y up +) or Polar (distance, angle in degrees).
2. Preview shows where a move would land. Apply commits it.
3. Undo, Reset position, Clear history, Export CSV.
4. "Move mouse" switch: Apply also moves the real cursor.
5. Click the Hotkey button and press an F-key (or Ctrl/Alt/Shift + letter/digit) to set a global Apply hotkey. Right-click to clear.
6. Graph: scroll to zoom, drag to pan, Fit view to recentre.

## Recoil Canceller usage

1. Enter the rate in px/s (+ = down, - = up, max 10000).
2. Turn on the Enabled switch, or press the toggle hotkey (default F8).
3. Hold left mouse to compensate. It pauses while its own window is focused.

## Tests

```
python -m unittest discover -s tests -v
```

UI tests need a display and are skipped if none is available.

## Project layout

```
main.py               RecoilLab entry point
recoil_canceller.py   Recoil Canceller entry point
core/                 math, movement, mouse, hotkeys, canceller logic
ui/                   dashboard, graph, canceller window, theme
tests/                unittest suite
```

## Limitations

- Windows only for mouse and hotkey features.
- Input into windows running as administrator is blocked unless the app is also run as admin.
- Windows "Enhance pointer precision" scales cursor movement; turn it off for exact pixel distances.
- Mouse movement is whole pixels; fractional pixels are carried over.
- Many online games treat input automation as cheating and may ban accounts. Use at your own risk.
- Settings are saved to `config.json` and `canceller_config.json` next to the scripts.
