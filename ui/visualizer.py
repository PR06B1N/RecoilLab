"""Cartesian graph in Tk. Scroll to zoom, drag to pan."""
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from . import theme as t


class Visualizer:
    def __init__(self, parent):
        self.fig = Figure(facecolor=t.PANEL, tight_layout=True)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.widget = self.canvas.get_tk_widget()
        self.widget.configure(bg=t.PANEL, highlightthickness=0)
        self._pan = None
        self._half = 10.0
        self._center = (0.0, 0.0)
        c = self.canvas
        c.mpl_connect("scroll_event", self._on_scroll)
        c.mpl_connect("button_press_event", self._on_press)
        c.mpl_connect("button_release_event", lambda e: setattr(self, "_pan", None))
        c.mpl_connect("motion_notify_event", self._on_move)
        c.mpl_connect("resize_event", lambda e: self._apply_limits(draw=False))
        self.draw([(0.0, 0.0)], None, fit=True)

    def draw(self, path, preview, fit=False, grid=True, trail=True):
        ax = self.ax
        ax.clear()
        ax.set_facecolor(t.BG)
        for s in ax.spines.values():
            s.set_color(t.BORDER)
        ax.tick_params(colors=t.MUTED, labelsize=8)
        ax.grid(grid, color=t.GRID, linewidth=0.6)
        ax.axhline(0, color=t.AXES, linewidth=1.2, zorder=1)
        ax.axvline(0, color=t.AXES, linewidth=1.2, zorder=1)
        ax.set_xlabel("X (+right)", color=t.MUTED, fontsize=8)
        ax.set_ylabel("Y (+up)", color=t.MUTED, fontsize=8)
        if trail and len(path) > 1:
            xs, ys = zip(*path)
            ax.plot(xs, ys, color=t.TRAIL, linewidth=1.6, marker="o", markersize=3, zorder=3)
        cur = path[-1]
        if preview is not None:
            ax.plot([cur[0], preview[0]], [cur[1], preview[1]], color=t.PREVIEW,
                    linestyle="--", linewidth=1.4, marker="x", markersize=6, zorder=4)
        ax.plot([0], [0], "o", color=t.TEXT, markersize=6, zorder=5, label="Origin")
        ax.plot([cur[0]], [cur[1]], "o", color=t.OK, markersize=8, zorder=6, label="Current")
        leg = ax.legend(loc="upper right", fontsize=8, facecolor=t.PANEL, edgecolor=t.BORDER)
        for txt in leg.get_texts():
            txt.set_color(t.TEXT)
        if fit:
            self._fit(path, preview)
        self._apply_limits()

    def _fit(self, path, preview):
        pts = list(path) + ([preview] if preview is not None else [])
        xs = [p[0] for p in pts] + [0.0]
        ys = [p[1] for p in pts] + [0.0]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 * 1.2
        self._center = (cx, cy)
        self._half = max(half, 1e-6) if half > 0 else 10.0

    def _apply_limits(self, draw=True):
        """Keep the same scale on both axes."""
        w = max(self.widget.winfo_width(), 1)
        h = max(self.widget.winfo_height(), 1)
        aspect = w / h
        cx, cy = self._center
        hy = self._half
        hx = hy * aspect
        self.ax.set_xlim(cx - hx, cx + hx)
        self.ax.set_ylim(cy - hy, cy + hy)
        if draw:
            self.canvas.draw_idle()

    def _on_scroll(self, e):
        if e.inaxes is None or e.xdata is None:
            return
        f = 0.8 if e.button == "up" else 1.25
        new = min(max(self._half * f, 1e-6), 1e12)
        f = new / self._half
        cx, cy = self._center
        # zoom around the cursor
        self._center = (e.xdata - (e.xdata - cx) * f, e.ydata - (e.ydata - cy) * f)
        self._half = new
        self._apply_limits()

    def _on_press(self, e):
        if e.button == 1 and e.inaxes is not None:
            self._pan = (e.x, e.y, self._center)

    def _on_move(self, e):
        if self._pan is None or e.x is None:
            return
        x0, y0, (cx, cy) = self._pan
        h = max(self.widget.winfo_height(), 1)
        upp = 2 * self._half / h
        self._center = (cx - (e.x - x0) * upp, cy - (e.y - y0) * upp)
        self._apply_limits()
