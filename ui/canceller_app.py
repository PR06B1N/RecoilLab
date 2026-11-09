import json
import os
import queue
import customtkinter as ctk
from core.calculations import validate_number
from core.canceller import Canceller
from core.hotkeys import MODIFIER_KEYSYMS, HotkeyManager, event_to_hotkey, hotkey_label
from . import theme as t

MAX_RATE = 10000.0
CFG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "canceller_config.json")


def _label(parent, text, size=12, bold=False, color=t.TEXT):
    return ctk.CTkLabel(parent, text=text, text_color=color,
                        font=(t.FONT, size, "bold" if bold else "normal"))


class CancellerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("Recoil Canceller")
        self.geometry("420x330")
        self.resizable(False, False)
        self.configure(fg_color=t.BG)
        self.canceller = Canceller()
        self.canceller.rate = 142.5
        self.hotkey = {"mods": [], "vk": 0x77}  # F8 by default
        self.capturing = False
        self.hk_queue = queue.Queue()
        self.hotkeys = HotkeyManager(lambda: self.hk_queue.put(1))
        self._load_cfg()
        self._build()
        self.bind("<KeyPress>", self._on_key, add="+")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.canceller.start()
        except RuntimeError as e:
            self._say(str(e), False)
        if self.hotkey:
            self._register_hotkey(self.hotkey, save=False)
        self.after(25, self._poll)

    def _build(self):
        c = ctk.CTkFrame(self, fg_color=t.PANEL, border_width=1, border_color=t.BORDER, corner_radius=8)
        c.pack(fill="both", expand=True, padx=t.PAD, pady=t.PAD)
        c.grid_columnconfigure((0, 1), weight=1)
        _label(c, "Recoil Canceller", 18, True).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 0))
        _label(c, "Hold left mouse: cursor moves down at a constant rate", 11, color=t.MUTED).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))
        _label(c, "Rate (px/s, + = down)", 11, color=t.MUTED).grid(row=2, column=0, columnspan=2, sticky="w", padx=14)
        self.ent = ctk.CTkEntry(c, height=34, fg_color=t.BG, border_color=t.BORDER, text_color=t.TEXT,
                                font=(t.MONO, 14))
        self.ent.insert(0, f"{self.canceller.rate:g}")
        self.ent.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(2, 8))
        self.ent.bind("<KeyRelease>", lambda e: self._on_rate())
        self.sw = ctk.CTkSwitch(c, text="Enabled", progress_color=t.ACCENT, font=(t.FONT, 13),
                                command=lambda: self._set_enabled(bool(self.sw.get())))
        self.sw.grid(row=4, column=0, sticky="w", padx=14, pady=6)
        self.btn_hk = ctk.CTkButton(c, text="", command=self._begin_capture, height=32, corner_radius=6,
                                    fg_color=t.PANEL_ALT, hover_color=t.BORDER, border_width=1,
                                    border_color=t.BORDER, text_color=t.TEXT, font=(t.FONT, 12))
        self.btn_hk.grid(row=4, column=1, sticky="ew", padx=(6, 14), pady=6)
        self.btn_hk.bind("<Button-3>", lambda e: self._clear_hotkey())
        _label(c, "Toggle hotkey: click to set, right-click to clear", 10, color=t.MUTED).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=14)
        self.status = _label(c, "Off", 14, True)
        self.status.grid(row=6, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 0))
        self.msg = _label(c, "", 11, color=t.MUTED)
        self.msg.grid(row=7, column=0, columnspan=2, sticky="w", padx=14, pady=(2, 0))
        _label(c, "Paused while this window is focused.", 10, color=t.MUTED).grid(
            row=8, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 12))
        self._refresh_hk_button()

    def _say(self, text, ok=True):
        self.msg.configure(text=text, text_color=t.OK if ok else t.DANGER)

    def _on_rate(self):
        try:
            v = validate_number(self.ent.get(), "rate")
            if abs(v) > MAX_RATE:
                raise ValueError(f"rate must be within +/-{MAX_RATE:g} px/s")
        except ValueError as e:
            self._say(str(e), False)
            return False
        self.canceller.rate = v
        self._save_cfg()
        self._say(f"Rate set: {v:g} px/s")
        return True

    def _set_enabled(self, on):
        if on and not self._on_rate():
            on = False
        self.canceller.enabled = on
        self.sw.select() if on else self.sw.deselect()

    def _refresh_hk_button(self):
        if self.capturing:
            txt = "Press keys... (Esc)"
        elif self.hotkey:
            txt = "Hotkey: " + hotkey_label(self.hotkey["mods"], self.hotkey["vk"])
        else:
            txt = "Hotkey: none"
        self.btn_hk.configure(text=txt)

    def _register_hotkey(self, hk, save=True):
        try:
            ok = self.hotkeys.set(hk["mods"], hk["vk"])
            err = "" if ok else "Hotkey unavailable (already in use?)"
        except RuntimeError as e:
            ok, err = False, str(e)
        self.hotkey = hk if ok else None
        if ok and save:
            self._save_cfg()
        if not ok:
            self._say(err, False)
        self._refresh_hk_button()

    def _begin_capture(self):
        self.capturing = True
        self.focus_set()
        self._refresh_hk_button()
        self._say("Press the toggle hotkey (Esc cancels)")

    def _on_key(self, ev):
        if not self.capturing:
            return None
        if ev.keysym == "Escape":
            self.capturing = False
            self._refresh_hk_button()
            self._say("Cancelled")
        elif ev.keysym not in MODIFIER_KEYSYMS:
            hk = event_to_hotkey(ev.keysym, ev.state)
            if hk is None:
                self._say("Use an F-key, or Ctrl/Alt/Shift + letter/digit", False)
            else:
                self.capturing = False
                self._register_hotkey({"mods": hk[0], "vk": hk[1]})
        return "break"

    def _clear_hotkey(self):
        self.hotkeys.clear()
        self.hotkey = None
        self.capturing = False
        self._save_cfg()
        self._refresh_hk_button()
        self._say("Hotkey cleared")

    def _load_cfg(self):
        try:
            with open(CFG, encoding="utf-8") as f:
                d = json.load(f)
            r = validate_number(d.get("rate", 142.5), "rate")
            if abs(r) <= MAX_RATE:
                self.canceller.rate = r
            if "hotkey" in d:
                hk = d["hotkey"]
                if hk is None:
                    self.hotkey = None
                elif isinstance(hk.get("vk"), int) and isinstance(hk.get("mods"), list):
                    self.hotkey = {"mods": [m for m in hk["mods"] if m in ("ctrl", "alt", "shift")],
                                   "vk": hk["vk"]}
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    def _save_cfg(self):
        try:
            with open(CFG, "w", encoding="utf-8") as f:
                json.dump({"rate": self.canceller.rate, "hotkey": self.hotkey}, f)
        except OSError:
            pass

    def _poll(self):
        try:
            while True:
                self.hk_queue.get_nowait()
                self._set_enabled(not self.canceller.enabled)
        except queue.Empty:
            pass
        c = self.canceller
        c.paused = self.focus_displayof() is not None
        if c.last_error:
            self._say(f"Stopped: {c.last_error}", False)
            c.last_error = ""
        if bool(self.sw.get()) != c.enabled:  # the worker switches itself off if sending fails
            self.sw.select() if c.enabled else self.sw.deselect()
        if not c.enabled:
            txt, col = "Off", t.MUTED
        elif c.paused:
            txt, col = "On - paused (window focused)", t.WARN
        elif c.active:
            txt, col = "Compensating...", t.OK
        else:
            txt, col = "On - hold left mouse", t.ACCENT
        self.status.configure(text=txt, text_color=col)
        self.after(25, self._poll)

    def _on_close(self):
        self.canceller.stop()
        self.hotkeys.clear()
        self.destroy()
