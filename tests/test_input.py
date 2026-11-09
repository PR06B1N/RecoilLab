import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.mouse import MouseMover, plan_steps
from core.hotkeys import event_to_hotkey, hotkey_label


class TestMouse(unittest.TestCase):
    def test_plan_y_inverted_and_rounding(self):
        self.assertEqual(plan_steps(5, -3)[:2], (5, 3))
        self.assertEqual(plan_steps(-2, 4)[:2], (-2, -4))

    def test_subpixel_carry(self):
        calls = []
        m = MouseMover(sender=lambda x, y: calls.append((x, y)))
        m.move(0.4, 0); self.assertEqual(calls, [])
        m.move(0.4, 0); self.assertEqual(calls, [(1, 0)])
        total = sum(c[0] for c in calls)
        for _ in range(10): m.move(0.1, 0)
        self.assertEqual(total + sum(c[0] for c in calls[1:]), 1 + 1)

    def test_failed_send_keeps_carry(self):
        def boom(x, y): raise OSError("x")
        m = MouseMover(sender=boom)
        with self.assertRaises(OSError): m.move(3, 0)
        self.assertEqual(m._rx, 0.0)

    def test_non_windows_raises(self):
        if sys.platform == "win32": self.skipTest("windows")
        with self.assertRaises(RuntimeError): MouseMover().move(1, 1)


class TestHotkeys(unittest.TestCase):
    def test_fkey_plain(self):
        self.assertEqual(event_to_hotkey("F6", 0), ([], 0x75))

    def test_modifiers(self):
        self.assertEqual(event_to_hotkey("a", 0x4 | 0x1), (["ctrl", "shift"], ord("A")))
        self.assertEqual(event_to_hotkey("1", 0x20000), (["alt"], ord("1")))

    def test_rejects_plain_letter_and_unknown(self):
        self.assertIsNone(event_to_hotkey("a", 0))
        self.assertIsNone(event_to_hotkey("Delete", 0))
        self.assertIsNone(event_to_hotkey("F25", 0))

    def test_label(self):
        self.assertEqual(hotkey_label([], 0x75), "F6")
        self.assertEqual(hotkey_label(["ctrl", "alt"], ord("Q")), "Ctrl+Alt+Q")


if __name__ == "__main__":
    unittest.main()
