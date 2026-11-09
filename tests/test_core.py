import math, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import calculations as c
from core.movement import MovementEngine


class TestCalc(unittest.TestCase):
    def test_polar_quadrants(self):
        self.assertEqual(c.polar_to_cartesian(5, 0), (5.0, 0.0))
        self.assertEqual(c.polar_to_cartesian(5, 90), (0.0, 5.0))
        self.assertEqual(c.polar_to_cartesian(5, 180), (-5.0, 0.0))
        self.assertEqual(c.polar_to_cartesian(5, 270), (0.0, -5.0))

    def test_negative_and_large_angles(self):
        self.assertEqual(c.polar_to_cartesian(5, -90), (0.0, -5.0))
        self.assertEqual(c.polar_to_cartesian(5, 450), (0.0, 5.0))
        x, y = c.polar_to_cartesian(2, -45)
        self.assertAlmostEqual(x, math.sqrt(2)); self.assertAlmostEqual(y, -math.sqrt(2))
        x, y = c.polar_to_cartesian(2, 765)
        self.assertAlmostEqual(x, math.sqrt(2)); self.assertAlmostEqual(y, math.sqrt(2))

    def test_distance_angle(self):
        self.assertAlmostEqual(c.distance(3, 4), 5)
        self.assertAlmostEqual(c.angle_deg(1, 1), 45)
        self.assertAlmostEqual(c.angle_deg(0, -1), 270)
        self.assertEqual(c.angle_deg(0, 0), 0.0)

    def test_validation(self):
        for bad in ["", "abc", None, float("nan"), float("inf"), "-inf", "nan", True]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                c.validate_number(bad)
        self.assertEqual(c.validate_number(" -2.5 "), -2.5)


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.e = MovementEngine()

    def test_cartesian_cumulative(self):
        self.e.apply("cartesian", 5, -3)
        self.assertEqual(self.e.position, (5.0, -3.0))
        self.e.apply("cartesian", -2, 1)
        self.assertEqual(self.e.position, (3.0, -2.0))

    def test_polar_apply(self):
        self.e.apply("polar", 10, 90)
        self.e.apply("polar", 10, 0)
        self.assertEqual(self.e.position, (10.0, 10.0))
        self.assertAlmostEqual(self.e.angle, 45)

    def test_decimal_precision(self):
        for _ in range(3):
            self.e.apply("cartesian", "0.1", "0.2")
        self.assertAlmostEqual(self.e.x, 0.3, places=12)
        self.assertAlmostEqual(self.e.y, 0.6, places=12)

    def test_undo_exact(self):
        self.e.apply("cartesian", 0.1, 0.2)
        before = self.e.position
        self.e.apply("polar", 7, 33)
        self.assertTrue(self.e.undo())
        self.assertEqual(self.e.position, before)
        self.assertTrue(self.e.undo())
        self.assertEqual(self.e.position, (0.0, 0.0))
        self.assertFalse(self.e.undo())

    def test_reset_and_undo_reset(self):
        self.e.apply("cartesian", 4, 4)
        self.e.reset()
        self.assertEqual(self.e.position, (0.0, 0.0))
        self.assertEqual(len(self.e.history), 2)
        self.e.undo()
        self.assertEqual(self.e.position, (4.0, 4.0))

    def test_clear_history(self):
        self.e.apply("cartesian", 1, 1)
        self.e.clear_history()
        self.assertEqual(self.e.history, [])
        self.assertEqual(self.e.position, (0.0, 0.0))

    def test_invalid_does_not_change_state(self):
        self.e.apply("cartesian", 1, 2)
        for args in [("cartesian", "x", 1), ("cartesian", float("nan"), 0),
                     ("cartesian", float("inf"), 0), ("polar", 1, float("inf")),
                     ("polar", "", 5), ("bogus", 1, 1), ("cartesian", 1e308, 0)]:
            if args[1:] == (1e308, 0):
                self.e.apply("cartesian", 1e308, 0)
                with self.assertRaises(ValueError):
                    self.e.apply("cartesian", 1e308 * 1.5 if False else 1.7e308, 0)
                self.e.undo()
                continue
            with self.assertRaises(ValueError, msg=str(args)):
                self.e.apply(*args)
        self.assertEqual(self.e.position, (1.0, 2.0))
        self.assertEqual(len(self.e.history), 1)

    def test_preview_no_change(self):
        p = self.e.preview("polar", 5, 90)
        self.assertEqual((p["x"], p["y"]), (0.0, 5.0))
        self.assertEqual(self.e.position, (0.0, 0.0))
        self.assertEqual(self.e.history, [])

    def test_history_consistency(self):
        self.e.apply("cartesian", 1, 2)
        self.e.apply("polar", 3, 180)
        self.e.reset()
        self.e.apply("cartesian", -1, -1)
        px = py = 0.0
        for h in self.e.history:
            px += h["dx"]; py += h["dy"]
            self.assertAlmostEqual(px, h["x"]); self.assertAlmostEqual(py, h["y"])
        self.assertEqual((self.e.history[-1]["x"], self.e.history[-1]["y"]), self.e.position)
        self.assertEqual(len(self.e.path()), len(self.e.history) + 1)

    def test_csv_export(self):
        self.e.apply("cartesian", 5, -3)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "h.csv")
            self.e.export_csv(p)
            with open(p) as f:
                lines = f.read().strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(lines[1].startswith("1,cartesian,5,-3,5.0,-3.0"))
            with self.assertRaises(OSError):
                self.e.export_csv(os.path.join(d, "no", "such", "h.csv"))


if __name__ == "__main__":
    unittest.main()
