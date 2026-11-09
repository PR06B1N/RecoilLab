"""Drives the real window, so it needs a display (xvfb works)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from ui.dashboard import App
    from core.mouse import MouseMover
    HAVE_UI = True
except Exception:
    HAVE_UI = False


@unittest.skipUnless(HAVE_UI, "UI deps unavailable")
class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def setUp(self):
        self.app.move_mouse = False
        self.app.mover = MouseMover(sender=lambda x, y: None)
        self.app.on_clear()
        self.app.mode_var.set("Cartesian"); self.app._on_mode("Cartesian")

    def fill(self, a, b):
        for e, v in ((self.app.ent_a, a), (self.app.ent_b, b)):
            e.delete(0, "end"); e.insert(0, v)

    def test_apply_cartesian(self):
        self.fill("5", "-3"); self.app.on_apply(); self.app.update()
        self.assertEqual(self.app.engine.position, (5.0, -3.0))
        self.assertEqual(self.app.stat["x".lower()].cget("text"), "5.0000")

    def test_polar_and_conversion_display(self):
        self.app.mode_var.set("Polar"); self.app._on_mode("Polar")
        self.fill("10", "90"); self.app._update_conv()
        self.assertIn("X = 0.0000", self.app.conv.cget("text"))
        self.app.on_apply()
        self.assertEqual(self.app.engine.position, (0.0, 10.0))

    def test_invalid_input_rejected(self):
        self.fill("abc", "1"); self.app.on_apply()
        self.assertEqual(self.app.engine.history, [])
        self.fill("nan", "1"); self.app.on_apply()
        self.assertEqual(self.app.engine.position, (0.0, 0.0))

    def test_preview_does_not_move(self):
        self.fill("2", "2"); self.app.on_preview(); self.app.update()
        self.assertEqual(self.app.engine.position, (0.0, 0.0))
        self.assertEqual(self.app.preview_pt, (2.0, 2.0))

    def test_undo_reset_clear(self):
        self.fill("1", "1"); self.app.on_apply(); self.app.on_apply()
        self.app.on_undo(); self.assertEqual(self.app.engine.position, (1.0, 1.0))
        self.app.on_reset(); self.assertEqual(self.app.engine.position, (0.0, 0.0))
        self.app.on_clear(); self.assertEqual(self.app.engine.history, [])

    def test_apply_moves_mouse_with_y_inverted(self):
        sent = []
        self.app.mover = MouseMover(sender=lambda x, y: sent.append((x, y)))
        self.app.move_mouse = True
        self.fill("5", "-3"); self.app.on_apply()
        self.assertEqual(sent, [(5, 3)])  # Cartesian -Y (down) = +screen Y
        self.assertEqual(self.app.engine.position, (5.0, -3.0))

    def test_mouse_failure_leaves_state_unchanged(self):
        def boom(x, y): raise OSError("blocked")
        self.app.mover = MouseMover(sender=boom)
        self.app.move_mouse = True
        self.fill("5", "5"); self.app.on_apply()
        self.assertEqual(self.app.engine.position, (0.0, 0.0))
        self.assertEqual(self.app.engine.history, [])

    def test_hotkey_queue_triggers_apply(self):
        self.fill("2", "0"); self.app.hk_queue.put(1)
        self.app.update(); self.app.after(60, lambda: None); self.app.update()
        import time; time.sleep(0.1); self.app.update()
        self.assertEqual(self.app.engine.position, (2.0, 0.0))

    def test_pages_and_graph(self):
        for p in ("Movement Controller", "Settings", "Dashboard"):
            self.app.show_page(p); self.app.update()
        self.assertEqual(len(self.app.viz.ax.get_lines()) >= 3, True)


if __name__ == "__main__":
    unittest.main()
