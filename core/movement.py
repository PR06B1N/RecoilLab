"""Tracks position and history, with exact undo. No UI code."""
import csv
import math
from . import calculations as calc


class MovementEngine:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.history = []  # one dict per move: dx, dy, resulting x/y, mode, inputs

    @property
    def position(self):
        return (self.x, self.y)

    @property
    def distance(self):
        return calc.distance(self.x, self.y)

    @property
    def angle(self):
        return calc.angle_deg(self.x, self.y)

    def path(self):
        return [(0.0, 0.0)] + [(h["x"], h["y"]) for h in self.history]

    def resolve(self, mode, a, b):
        """Validate and return (dx, dy) for cartesian (x, y) or polar (r, theta)."""
        if mode == "cartesian":
            return calc.validate_number(a, "X"), calc.validate_number(b, "Y")
        if mode == "polar":
            return calc.polar_to_cartesian(a, b)
        raise ValueError(f"unknown mode: {mode}")

    def preview(self, mode, a, b):
        dx, dy = self.resolve(mode, a, b)
        nx, ny = self.x + dx, self.y + dy
        if not (math.isfinite(nx) and math.isfinite(ny)):
            raise ValueError("result overflows")
        return {"dx": dx, "dy": dy, "x": nx, "y": ny,
                "distance": calc.distance(nx, ny), "angle": calc.angle_deg(nx, ny)}

    def apply(self, mode, a, b):
        p = self.preview(mode, a, b)
        self.x, self.y = p["x"], p["y"]
        self.history.append({"dx": p["dx"], "dy": p["dy"], "x": p["x"], "y": p["y"],
                             "mode": mode, "inputs": (str(a), str(b))})
        return p

    def undo(self):
        if not self.history:
            return False
        self.history.pop()
        if self.history:
            self.x, self.y = self.history[-1]["x"], self.history[-1]["y"]
        else:
            self.x, self.y = 0.0, 0.0
        return True

    def reset(self):
        """Go back to the origin. Logged as a move so undo works."""
        if self.x == 0.0 and self.y == 0.0:
            return
        self.history.append({"dx": -self.x, "dy": -self.y, "x": 0.0, "y": 0.0,
                             "mode": "reset", "inputs": ("", "")})
        self.x = self.y = 0.0

    def clear_history(self):
        """Wipe history and go back to the origin."""
        self.history.clear()
        self.x = self.y = 0.0

    def export_csv(self, path):
        """Write history to CSV; OSError is left for the caller."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["step", "mode", "input_a", "input_b", "dx", "dy", "x", "y",
                        "distance", "angle_deg"])
            for i, h in enumerate(self.history, 1):
                w.writerow([i, h["mode"], h["inputs"][0], h["inputs"][1],
                            repr(h["dx"]), repr(h["dy"]), repr(h["x"]), repr(h["y"]),
                            repr(calc.distance(h["x"], h["y"])),
                            repr(calc.angle_deg(h["x"], h["y"]))])
