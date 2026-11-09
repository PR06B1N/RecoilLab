"""Moves the real cursor with SendInput. +Y is up, like the graph."""
import math
import sys

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_size_t)]

    class _INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("mi", _MOUSEINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

_MOVE = 0x0001
_LIMIT = 2**31 - 1


def plan_steps(dx, dy, rx=0.0, ry=0.0):
    """Cartesian delta (+Y up) -> whole screen pixels (+Y down), plus the leftover fraction."""
    tx, ty = dx + rx, -dy + ry
    ix, iy = math.floor(tx + 0.5), math.floor(ty + 0.5)
    return ix, iy, tx - ix, ty - iy


def send_move(ix, iy):
    if sys.platform != "win32":
        raise RuntimeError("Moving the mouse is only supported on Windows")
    inp = _INPUT(type=0, mi=_MOUSEINPUT(ix, iy, 0, _MOVE, 0, 0))
    if ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)) != 1:
        raise OSError("SendInput was blocked (target window may be running as admin)")


class MouseMover:
    def __init__(self, sender=None):
        self._send = sender or send_move
        self._rx = self._ry = 0.0

    def move(self, dx, dy):
        """Move by (dx, dy) and return the pixels actually sent."""
        ix, iy, rx, ry = plan_steps(dx, dy, self._rx, self._ry)
        if abs(ix) > _LIMIT or abs(iy) > _LIMIT:
            raise ValueError("movement too large")
        if ix or iy:
            self._send(ix, iy)
        self._rx, self._ry = rx, ry  # only keep the leftover once the send worked
        return ix, iy
