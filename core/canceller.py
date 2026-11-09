"""Linear compensation while the left button is held."""
import sys
import threading
import time

from .mouse import MouseMover

_MAX_DT = 0.1  # seconds; stops a stalled thread from causing a jump


def lbutton_down():
    if sys.platform != "win32":
        raise RuntimeError("Recoil Canceller is only supported on Windows")
    import ctypes
    return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)


class Canceller:
    """rate is px/s (positive = down). Movement is rate x elapsed time,
    so ticks can jitter without changing the speed."""

    def __init__(self, sender=None):
        self.rate = 0.0
        self.enabled = False
        self.paused = False
        self.active = False
        self.last_error = ""
        self._sender = sender
        self._mover = None
        self._last = None
        self._stop = threading.Event()
        self._thread = None

    def tick(self, now, down):
        """One step; returns the pixels sent."""
        self.active = bool(self.enabled and down and not self.paused)
        if not self.active:
            self._mover = self._last = None
            return (0, 0)
        if self._mover is None:  # just pressed, start timing
            self._mover, self._last = MouseMover(self._sender), now
            return (0, 0)
        dt = min(max(now - self._last, 0.0), _MAX_DT)
        self._last = now
        return self._mover.move(0.0, -self.rate * dt)  # -Y is down

    def start(self):
        if self._thread is not None:
            return
        if sys.platform != "win32":
            raise RuntimeError("Recoil Canceller is only supported on Windows")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(1)
            self._thread = None

    def _run(self):
        import ctypes
        winmm = ctypes.windll.winmm
        winmm.timeBeginPeriod(1)
        try:
            while not self._stop.is_set():
                try:
                    self.tick(time.perf_counter(), lbutton_down())
                except (OSError, ValueError) as e:
                    self.last_error = str(e)
                    self.enabled = False
                time.sleep(0.001)
        finally:
            winmm.timeEndPeriod(1)
