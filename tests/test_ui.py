import sys
import unittest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Ensure QApplication exists for widget testing
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from ui.components.posture_avatar import PostureAvatarWidget
from ui.components.gauge_widget import CircularRiskGauge
from ui.overlay_window import DesktopOverlay


class TestUIComponents(unittest.TestCase):
    def test_posture_avatar_widget(self):
        widget = PostureAvatarWidget()
        self.assertIsNotNone(widget)
        widget.update_posture(15.0, 3.0, 20.0, "Aman", is_detected=True)
        self.assertEqual(widget.risk_category, "Aman")

    def test_circular_risk_gauge(self):
        gauge = CircularRiskGauge()
        self.assertIsNotNone(gauge)
        gauge.set_risk(75.0, "Bahaya")
        self.assertEqual(gauge.target_score, 75.0)
        self.assertEqual(gauge.category, "Bahaya")

    def test_desktop_overlay_attributes(self):
        overlay = DesktopOverlay()
        self.assertIsNotNone(overlay)
        # Verify non-intrusive flags
        flags = overlay.windowFlags()
        self.assertTrue(bool(flags & Qt.FramelessWindowHint))
        self.assertTrue(bool(flags & Qt.WindowStaysOnTopHint))
        overlay.update_risk(80.0, "Bahaya")
        self.assertGreater(overlay.target_opacity, 0.4)
        overlay.close()

    def test_user_guide_dialog(self):
        from ui.dashboard_window import UserGuideDialog
        dialog = UserGuideDialog()
        self.assertIsNotNone(dialog)
        self.assertIn("SIERRA", dialog.windowTitle())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
