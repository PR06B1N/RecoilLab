import json
import os
import queue
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from core.hotkeys import MODIFIER_KEYSYMS, HotkeyManager, event_to_hotkey, hotkey_label
from core.mouse import MouseMover
from core.movement import MovementEngine
from . import theme as t
from .visualizer import Visualizer


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=t.PANEL, border_width=1, border_color=t.BORDER,
                        corner_radius=8, **kw)


def label(parent, text, size=12, bold=False, color=t.TEXT, mono=False):
    return ctk.CTkLabel(parent, text=text, text_color=color,
                        font=(t.MONO if mono else t.FONT, size, "bold" if bold else "normal"))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("RecoilLab")
        self.geometry("1280x840")
        self.minsize(1000, 720)
        self.configure(fg_color=t.BG)
        self.engine = MovementEngine()
        self.preview_pt = None
        self.decimals = 4
        self.auto_fit = True
        self.show_grid = True
        self.show_trail = True
        self.mode = "cartesian"
        self.mover = MouseMover()
        self.move_mouse = True
        self.hotkey = None
        self.capturing = False
        self.hk_queue = queue.Queue()
        self.hotkeys = HotkeyManager(lambda: self.hk_queue.put(1))
        self._load_cfg()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color=t.BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self._build_main()
        self._build_settings()
        self.show_page("Dashboard")
        self.refresh(fit=True)
        self.bind("<KeyPress>", self._on_key, add="+")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.hotkey:
            self._register_hotkey(self.hotkey, save=False)
        self.after(25, self._poll)

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=t.PANEL, width=190, corner_radius=0,
                          border_width=1, border_color=t.BORDER)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        label(sb, "RecoilLab", 20, True).pack(anchor="w", padx=16, pady=(20, 2))
        label(sb, "Displacement simulator", 11, color=t.MUTED).pack(anchor="w", padx=16, pady=(0, 20))
        self.nav = {}
        for name in ("Dashboard", "Movement Controller", "Settings"):
            b = ctk.CTkButton(sb, text=name, anchor="w", height=36, corner_radius=6,
                              fg_color="transparent", hover_color=t.PANEL_ALT, text_color=t.TEXT,
                              font=(t.FONT, 13), command=lambda n=name: self.show_page(n))
            b.pack(fill="x", padx=10, pady=2)
            self.nav[name] = b

    def _build_main(self):
        m = self.main = ctk.CTkFrame(self.content, fg_color=t.BG, corner_radius=0)
        m.grid(row=0, column=0, sticky="nsew", padx=t.PAD, pady=t.PAD)
        m.grid_columnconfigure(0, weight=0, minsize=340)
        m.grid_columnconfigure(1, weight=1)
        m.grid_rowconfigure(1, weight=1)

        stats = ctk.CTkFrame(m, fg_color=t.BG)
        stats.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, t.PAD))
        self.stat = {}
        for i, (k, title) in enumerate((("x", "X"), ("y", "Y"), ("dist", "Total displacement"),
                                        ("ang", "Angle"))):
            stats.grid_columnconfigure(i, weight=1, uniform="s")
            c = card(stats)
            c.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else t.PAD // 2, 0))
            label(c, title, 11, color=t.MUTED).pack(anchor="w", padx=12, pady=(8, 0))
            v = label(c, "0", 20, True, mono=True)
            v.pack(anchor="w", padx=12, pady=(0, 8))
            self.stat[k] = v

        left = ctk.CTkFrame(m, fg_color=t.BG)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, t.PAD))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self._build_controls(left)
        self._build_history(left)

        self.graph_card = card(m)
        self.graph_card.grid(row=1, column=1, sticky="nsew")
        self.graph_card.grid_rowconfigure(0, weight=1)
        self.graph_card.grid_columnconfigure(0, weight=1)
        self.viz = Visualizer(self.graph_card)
        self.viz.widget.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        bar = ctk.CTkFrame(self.graph_card, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        label(bar, "Scroll: zoom  |  Drag: pan", 11, color=t.MUTED).pack(side="left")
        self._btn(bar, "Fit view", lambda: self.refresh(fit=True), secondary=True, w=90).pack(side="right")

    def _btn(self, parent, text, cmd, secondary=False, danger=False, w=None):
        fg = t.DANGER if danger else (t.PANEL_ALT if secondary else t.ACCENT)
        hv = "#c4453e" if danger else (t.BORDER if secondary else t.ACCENT_HOVER)
        kw = {"width": w} if w else {}
        return ctk.CTkButton(parent, text=text, command=cmd, fg_color=fg, hover_color=hv,
                             text_color=t.TEXT, height=32, corner_radius=6,
                             border_width=1 if secondary else 0, border_color=t.BORDER,
                             font=(t.FONT, 12), **kw)

    def _build_controls(self, parent):
        c = card(parent)
        c.grid(row=0, column=0, sticky="ew", pady=(0, t.PAD))
        c.grid_columnconfigure((0, 1), weight=1)
        label(c, "Movement", 14, True).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))
        self.mode_var = ctk.StringVar(value="Cartesian")
        ctk.CTkSegmentedButton(c, values=["Cartesian", "Polar"], variable=self.mode_var,
                               command=self._on_mode, fg_color=t.PANEL_ALT,
                               selected_color=t.ACCENT, selected_hover_color=t.ACCENT_HOVER,
                               unselected_color=t.PANEL_ALT, unselected_hover_color=t.BORDER,
                               font=(t.FONT, 12)).grid(row=1, column=0, columnspan=2, sticky="ew", padx=12)
        self.lbl_a = label(c, "X displacement", 11, color=t.MUTED)
        self.lbl_b = label(c, "Y displacement", 11, color=t.MUTED)
        self.lbl_a.grid(row=2, column=0, sticky="w", padx=12, pady=(10, 0))
        self.lbl_b.grid(row=2, column=1, sticky="w", padx=6, pady=(10, 0))
        self.ent_a = self._entry(c)
        self.ent_b = self._entry(c)
        self.ent_a.grid(row=3, column=0, sticky="ew", padx=(12, 6))
        self.ent_b.grid(row=3, column=1, sticky="ew", padx=(6, 12))
        self.conv = label(c, "", 11, color=t.MUTED, mono=True)
        self.conv.grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 0))
        self.msg = label(c, "", 11, color=t.MUTED)
        self.msg.grid(row=5, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 0))
        self._btn(c, "Apply", self.on_apply).grid(row=6, column=0, sticky="ew", padx=(12, 6), pady=(8, 6))
        self._btn(c, "Preview", self.on_preview, secondary=True).grid(row=6, column=1, sticky="ew", padx=(6, 12), pady=(8, 6))
        self._btn(c, "Undo", self.on_undo, secondary=True).grid(row=7, column=0, sticky="ew", padx=(12, 6), pady=(0, 6))
        self._btn(c, "Reset position", self.on_reset, secondary=True).grid(row=7, column=1, sticky="ew", padx=(6, 12), pady=(0, 6))
        self._btn(c, "Clear history", self.on_clear, danger=True).grid(row=8, column=0, sticky="ew", padx=(12, 6), pady=(0, 6))
        self._btn(c, "Export CSV", self.on_export, secondary=True).grid(row=8, column=1, sticky="ew", padx=(6, 12), pady=(0, 6))
        self.sw_mouse = ctk.CTkSwitch(c, text="Move mouse", progress_color=t.ACCENT,
                                      font=(t.FONT, 12), command=self._on_toggle_mouse)
        if self.move_mouse:
            self.sw_mouse.select()
        self.sw_mouse.grid(row=9, column=0, sticky="w", padx=12, pady=(0, 4))
        self.btn_hk = self._btn(c, "", self._begin_capture, secondary=True)
        self.btn_hk.grid(row=9, column=1, sticky="ew", padx=(6, 12), pady=(0, 4))
        self.btn_hk.bind("<Button-3>", lambda ev: self._clear_hotkey())
        label(c, "Click hotkey to set  |  right-click to clear", 10, color=t.MUTED).grid(
            row=10, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))
        self._refresh_hk_button()
        for e in (self.ent_a, self.ent_b):
            e.bind("<Return>", lambda ev: self.on_apply())
            e.bind("<KeyRelease>", lambda ev: self._update_conv())
        self.controls_card = c

    def _entry(self, parent):
        return ctk.CTkEntry(parent, height=32, fg_color=t.BG, border_color=t.BORDER,
                            text_color=t.TEXT, font=(t.MONO, 13), placeholder_text="0")

    def _build_history(self, parent):
        c = card(parent)
        c.grid(row=1, column=0, sticky="nsew")
        c.grid_rowconfigure(1, weight=1)
        c.grid_columnconfigure(0, weight=1)
        label(c, "Movement history", 14, True).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.hist = tk.Text(c, bg=t.BG, fg=t.TEXT, font=(t.MONO, 10), relief="flat", bd=0,
                            highlightthickness=0, wrap="none", state="disabled", height=8)
        self.hist.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        sb = ctk.CTkScrollbar(c, command=self.hist.yview)
        sb.grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=(0, 10))
        self.hist.configure(yscrollcommand=sb.set)

    def _build_settings(self):
        s = self.settings = ctk.CTkFrame(self.content, fg_color=t.BG, corner_radius=0)
        s.grid(row=0, column=0, sticky="nsew", padx=t.PAD, pady=t.PAD)
        c = card(s)
        c.pack(anchor="nw", fill="x", padx=0, pady=0)
        label(c, "Settings", 16, True).pack(anchor="w", padx=16, pady=(14, 8))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(anchor="w", padx=16, pady=6)
        label(row, "Display decimals", 12).pack(side="left", padx=(0, 12))
        self.dec_var = ctk.StringVar(value=str(self.decimals))
        ctk.CTkOptionMenu(row, values=[str(i) for i in range(0, 11)], variable=self.dec_var,
                          command=self._on_decimals, width=80, fg_color=t.PANEL_ALT,
                          button_color=t.BORDER, button_hover_color=t.ACCENT).pack(side="left")
        for text, attr in (("Show grid", "show_grid"), ("Show trajectory", "show_trail"),
                           ("Auto-fit view after movement", "auto_fit")):
            sw = ctk.CTkSwitch(c, text=text, progress_color=t.ACCENT, font=(t.FONT, 12),
                               command=lambda a=attr: self._on_switch(a))
            sw.select()
            sw.pack(anchor="w", padx=16, pady=6)
            setattr(self, "sw_" + attr, sw)
        label(c, "Internal precision is never rounded; decimals affect display only.", 11,
              color=t.MUTED).pack(anchor="w", padx=16, pady=(6, 14))

    def show_page(self, name):
        for n, b in self.nav.items():
            b.configure(fg_color=t.PANEL_ALT if n == name else "transparent")
        if name == "Settings":
            self.main.grid_remove()
            self.settings.grid()
            return
        self.settings.grid_remove()
        self.main.grid()
        if name == "Movement Controller":
            self.graph_card.grid_remove()
            self.main.grid_columnconfigure(0, weight=1)
            self.main.grid_columnconfigure(1, weight=0, minsize=0)
        else:
            self.graph_card.grid()
            self.main.grid_columnconfigure(0, weight=0, minsize=340)
            self.main.grid_columnconfigure(1, weight=1)
            self.refresh()

    def _on_decimals(self, v):
        self.decimals = int(v)
        self.refresh()
        self._update_conv()

    def _on_switch(self, attr):
        setattr(self, attr, bool(getattr(self, "sw_" + attr).get()))
        self.refresh()

    def f(self, v):
        s = f"{v:.{self.decimals}f}"
        return s[1:] if s.startswith("-") and float(s) == 0 else s

    def _on_mode(self, v):
        self.mode = v.lower()
        if self.mode == "cartesian":
            self.lbl_a.configure(text="X displacement"); self.lbl_b.configure(text="Y displacement")
        else:
            self.lbl_a.configure(text="Distance r"); self.lbl_b.configure(text="Angle θ (degrees)")
        self.preview_pt = None
        self._update_conv()
        self.refresh()

    def _inputs(self):
        return self.ent_a.get(), self.ent_b.get()

    def _update_conv(self):
        if self.mode != "polar":
            self.conv.configure(text="")
            return
        try:
            dx, dy = self.engine.resolve("polar", *self._inputs())
            self.conv.configure(text=f"→ X = {self.f(dx)}, Y = {self.f(dy)}", text_color=t.MUTED)
        except ValueError:
            self.conv.configure(text="→ X = ?, Y = ?", text_color=t.MUTED)

    def _say(self, text, ok=True):
        self.msg.configure(text=text, text_color=t.OK if ok else t.DANGER)

    def on_apply(self):
        try:
            p = self.engine.preview(self.mode, *self._inputs())
        except ValueError as e:
            self._say(str(e), False)
            return
        note = ""
        if self.move_mouse:  # cursor first, so a failed move doesn't touch the history
            try:
                ix, iy = self.mover.move(p["dx"], p["dy"])
            except (RuntimeError, OSError, ValueError) as e:
                self._say(f"Mouse move failed: {e}", False)
                return
            note = f"  |  cursor {ix:+d}, {-iy:+d} px"
        self.engine.apply(self.mode, *self._inputs())
        self.preview_pt = None
        self._say(f"Moved by ({self.f(p['dx'])}, {self.f(p['dy'])}){note}")
        self.refresh(fit=self.auto_fit)

    def on_preview(self):
        try:
            p = self.engine.preview(self.mode, *self._inputs())
        except ValueError as e:
            self._say(str(e), False)
            return
        self.preview_pt = (p["x"], p["y"])
        self._say(f"Preview → ({self.f(p['x'])}, {self.f(p['y'])}), "
                  f"r={self.f(p['distance'])}, θ={self.f(p['angle'])}°")
        self.refresh()

    def on_undo(self):
        self.preview_pt = None
        self._say("Undone" if self.engine.undo() else "Nothing to undo", True)
        self.refresh(fit=self.auto_fit)

    def on_reset(self):
        self.preview_pt = None
        self.engine.reset()
        self._say("Position reset to origin")
        self.refresh(fit=self.auto_fit)

    def on_clear(self):
        self.preview_pt = None
        self.engine.clear_history()
        self._say("History cleared; position reset")
        self.refresh(fit=True)

    def on_export(self):
        if not self.engine.history:
            self._say("No history to export", False)
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="recoillab_history.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            self.engine.export_csv(path)
            self._say(f"Exported {len(self.engine.history)} rows")
        except OSError as e:
            self._say(f"Export failed: {e.strerror or e}", False)

    CFG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

    def _load_cfg(self):
        try:
            with open(self.CFG, encoding="utf-8") as f:
                d = json.load(f)
            self.move_mouse = bool(d.get("move_mouse", True))
            hk = d.get("hotkey")
            if isinstance(hk, dict) and isinstance(hk.get("vk"), int) and isinstance(hk.get("mods"), list):
                self.hotkey = {"mods": [m for m in hk["mods"] if m in ("ctrl", "alt", "shift")],
                               "vk": hk["vk"]}
        except (OSError, ValueError, AttributeError):
            pass

    def _save_cfg(self):
        try:
            with open(self.CFG, "w", encoding="utf-8") as f:
                json.dump({"move_mouse": self.move_mouse, "hotkey": self.hotkey}, f)
        except OSError:
            pass

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
        if ok:
            self.hotkey = hk
            if save:
                self._save_cfg()
            self._say("Apply hotkey: " + hotkey_label(hk["mods"], hk["vk"]))
        else:
            self.hotkey = None
            self._say(err, False)
        self._refresh_hk_button()
        return ok

    def _begin_capture(self):
        self.capturing = True
        self.focus_set()
        self._refresh_hk_button()
        self._say("Press the hotkey (Esc cancels)")

    def _on_key(self, ev):
        if not self.capturing:
            return None
        if ev.keysym == "Escape":
            self.capturing = False
            self._refresh_hk_button()
            self._say("Cancelled")
        elif ev.keysym in MODIFIER_KEYSYMS:
            pass
        else:
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

    def _on_toggle_mouse(self):
        self.move_mouse = bool(self.sw_mouse.get())
        self._save_cfg()

    def _poll(self):
        try:
            while True:
                self.hk_queue.get_nowait()
                self.on_apply()
        except queue.Empty:
            pass
        self.after(25, self._poll)

    def _on_close(self):
        self.hotkeys.clear()
        self.destroy()

    def refresh(self, fit=False):
        e = self.engine
        self.stat["x"].configure(text=self.f(e.x))
        self.stat["y"].configure(text=self.f(e.y))
        self.stat["dist"].configure(text=self.f(e.distance))
        self.stat["ang"].configure(text=self.f(e.angle) + "°")
        self.hist.configure(state="normal")
        self.hist.delete("1.0", "end")
        hdr = f"{'#':>3} {'mode':<9} {'dx':>10} {'dy':>10} {'x':>10} {'y':>10}\n"
        self.hist.insert("end", hdr)
        for i, h in enumerate(e.history, 1):
            self.hist.insert("end", f"{i:>3} {h['mode']:<9} {self.f(h['dx']):>10} {self.f(h['dy']):>10} "
                                    f"{self.f(h['x']):>10} {self.f(h['y']):>10}\n")
        self.hist.see("end")
        self.hist.configure(state="disabled")
        if self.graph_card.winfo_manager():
            self.viz.draw(e.path(), self.preview_pt, fit=fit, grid=self.show_grid, trail=self.show_trail)
