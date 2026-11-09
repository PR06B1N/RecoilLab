import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.canceller import Canceller


def run(c, seconds, dt, down=True, t0=0.0):
    sent, t = [], t0
    for _ in range(int(round(seconds / dt)) + 1):
        r = c.tick(t, down)
        if r != (0, 0):
            sent.append(r)
        t += dt
    return sent


def make(rate=142.5):
    c = Canceller(sender=lambda x, y: None)
    c.rate, c.enabled = rate, True
    return c


class TestCanceller(unittest.TestCase):
    def test_linear_rate_one_second(self):
        c = make(); sent = run(c, 1.0, 0.001)
        self.assertAlmostEqual(sum(s[1] for s in sent), 142.5, delta=1)
        self.assertTrue(all(s == (0, 1) for s in sent))  # smooth: 1 px at a time, straight down

    def test_linear_over_time_with_jitter(self):
        c = make(); sent = run(c, 2.0, 0.016)
        self.assertAlmostEqual(sum(s[1] for s in sent), 142.5 * 2.0, delta=3)

    def test_disabled_or_released_sends_nothing(self):
        c = make(); c.enabled = False
        self.assertEqual(run(c, 1.0, 0.001), [])
        c = make()
        self.assertEqual(run(c, 1.0, 0.001, down=False), [])

    def test_paused_sends_nothing(self):
        c = make(); c.paused = True
        self.assertEqual(run(c, 1.0, 0.001), [])

    def test_clock_restarts_each_press(self):
        c = make()
        run(c, 0.5, 0.001)
        c.tick(0.6, False)
        self.assertEqual(c.tick(10.0, True), (0, 0))  # new press: no jump from stale time
        self.assertEqual(c.tick(10.001, True), (0, 0))

    def test_dt_cap(self):
        c = make(1000.0)
        c.tick(0.0, True)
        self.assertLessEqual(c.tick(5.0, True)[1], 100)  # capped at 0.1 s

    def test_negative_rate_moves_up(self):
        c = make(-100.0); sent = run(c, 0.5, 0.001)
        self.assertTrue(all(s[1] == -1 for s in sent))

    def test_zero_rate(self):
        self.assertEqual(run(make(0.0), 1.0, 0.001), [])


class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tempfile
            import ui.canceller_app as m
            m.CFG = os.path.join(tempfile.mkdtemp(), 'cfg.json')  # don't touch the real config
            CancellerApp = m.CancellerApp
            cls.app = CancellerApp(); cls.app.update()
        except Exception:
            cls.app = None

    @classmethod
    def tearDownClass(cls):
        if cls.app: cls.app.destroy()

    def setUp(self):
        if not self.app: self.skipTest("no display")

    def entry(self, v):
        self.app.ent.delete(0, "end"); self.app.ent.insert(0, v)

    def test_rate_validation(self):
        self.entry("200"); self.assertTrue(self.app._on_rate()); self.assertEqual(self.app.canceller.rate, 200.0)
        for bad in ("abc", "", "nan", "inf", "99999"):
            self.entry(bad); self.assertFalse(self.app._on_rate(), bad)
            self.assertEqual(self.app.canceller.rate, 200.0)

    def test_cannot_enable_with_invalid_rate(self):
        self.entry("oops"); self.app._set_enabled(True)
        self.assertFalse(self.app.canceller.enabled)
        self.entry("142.5"); self.app._set_enabled(True)
        self.assertTrue(self.app.canceller.enabled)
        self.app._set_enabled(False)


if __name__ == "__main__":
    unittest.main()
