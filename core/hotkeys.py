"""Global hotkey via RegisterHotKey, plus Tk key parsing."""
import sys
import threading

MODIFIER_KEYSYMS = {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
                    "Meta_L", "Meta_R", "Super_L", "Super_R", "Caps_Lock", "Num_Lock"}
_TK_MODS = (("ctrl", 0x4), ("alt", 0x20000), ("shift", 0x1))  # Tk modifier bits (Windows)
_WIN_MODS = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4}
_MOD_NOREPEAT = 0x4000


def event_to_hotkey(keysym, state):
    """Turn a Tk key event into (mods, vk), or None if we can't use it.
    Plain keys must be F1-F24; letters/digits need Ctrl/Alt/Shift."""
    mods = [n for n, b in _TK_MODS if state & b]
    vk, standalone = None, False
    if len(keysym) > 1 and keysym[0] == "F" and keysym[1:].isdigit() and 1 <= int(keysym[1:]) <= 24:
        vk, standalone = 0x70 + int(keysym[1:]) - 1, True
    elif len(keysym) == 1 and keysym.isascii() and keysym.isalnum():
        vk = ord(keysym.upper())
    if vk is None or (not mods and not standalone):
        return None
    return mods, vk


def hotkey_label(mods, vk):
    parts = [m.capitalize() for m in ("ctrl", "alt", "shift") if m in mods]
    parts.append(f"F{vk - 0x6F}" if 0x70 <= vk <= 0x87 else chr(vk))
    return "+".join(parts)


class HotkeyManager:
    """Holds one global hotkey. The callback runs on a background thread, so keep it tiny."""

    def __init__(self, callback):
        self._cb = callback
        self._thread = None
        self._tid = None

    def set(self, mods, vk):
        """Register the hotkey (replacing any old one). False if Windows refuses."""
        self.clear()
        if sys.platform != "win32":
            raise RuntimeError("Global hotkeys are only supported on Windows")
        import ctypes
        from ctypes import wintypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        flags = _MOD_NOREPEAT
        for m in mods:
            flags |= _WIN_MODS[m]
        ready, res = threading.Event(), {}

        def run():
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # makes sure this thread has a message queue
            res["tid"] = kernel32.GetCurrentThreadId()
            res["ok"] = bool(user32.RegisterHotKey(None, 1, flags, vk))
            ready.set()
            if not res["ok"]:
                return
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    self._cb()
            user32.UnregisterHotKey(None, 1)

        th = threading.Thread(target=run, daemon=True)
        th.start()
        ready.wait(2)
        if not res.get("ok"):
            return False
        self._thread, self._tid = th, res["tid"]
        return True

    def clear(self):
        if self._thread is not None:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._tid, 0x0012, 0, 0)  # WM_QUIT
            self._thread.join(1)
            self._thread = self._tid = None
