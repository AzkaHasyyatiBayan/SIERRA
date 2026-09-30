import sys
import ctypes
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QBrush, QPen, QFont


class DesktopOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Configurable settings
        self.max_opacity = 0.65       # Max dimming opacity (0.0 - 1.0)
        self.dimming_color_hex = "#0f172a"  # Dark navy vignette
        self.show_hud_pill = True

        # Current animation state
        self.current_opacity = 0.0
        self.target_opacity = 0.0
        self.risk_category = "Aman"
        self.risk_score = 0.0

        # Setup frameless transparent always-on-top window
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )

        # Fill primary monitor screen
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Setup Windows Click-Through
        self._enable_click_through()

        # Animation timer (Smooth fade in / fade out at 60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._step_fade)
        self.anim_timer.start(16)

    def _enable_click_through(self):
        """Enforces true click-through on Windows so game input is never intercepted."""
        if sys.platform.startswith("win"):
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                GWL_EXSTYLE = -20
                WS_EX_TRANSPARENT = 0x00000020
                WS_EX_LAYERED = 0x00080000

                style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
            except Exception as e:
                print(f"[Overlay] Click-through warning: {e}")

    def update_risk(self, risk_score: float, risk_category: str):
        self.risk_score = risk_score
        self.risk_category = risk_category

        # Determine target opacity based on risk
        if risk_category == "Aman" or risk_score < 30.0:
            self.target_opacity = 0.0
        elif risk_category == "Waspada":
            # Subtle dimming (40% of max opacity)
            self.target_opacity = self.max_opacity * 0.40
        else:  # Bahaya
            # Full dimming
            self.target_opacity = self.max_opacity

    def configure_intervention(self, max_opacity: float, color_hex: str):
        """Customizable intervention settings from dashboard."""
        self.max_opacity = max(0.1, min(0.95, max_opacity))
        self.dimming_color_hex = color_hex
        self.update()

    def _step_fade(self):
        """Smoothly interpolates opacity."""
        diff = self.target_opacity - self.current_opacity
        if abs(diff) > 0.005:
            # Smooth ease-in-out factor
            self.current_opacity += diff * 0.08
            self.update()
        elif self.current_opacity != self.target_opacity:
            self.current_opacity = self.target_opacity
            self.update()

    def paintEvent(self, event):
        # If completely transparent, no need to paint
        if self.current_opacity <= 0.001 and not self.show_hud_pill:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        center = QPointF(w / 2.0, h / 2.0)
        radius = max(w, h) * 0.72

        # 1. Adaptive Radial Edge Dimming (Vignette)
        if self.current_opacity > 0.001:
            base_color = QColor(self.dimming_color_hex)
            alpha_int = int(self.current_opacity * 255)

            gradient = QRadialGradient(center, radius)
            # Center of the screen remains completely crystal-clear transparent (0 alpha)
            gradient.setColorAt(0.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
            gradient.setColorAt(0.50, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
            gradient.setColorAt(0.75, QColor(base_color.red(), base_color.green(), base_color.blue(), int(alpha_int * 0.4)))
            gradient.setColorAt(1.0, QColor(base_color.red(), base_color.green(), base_color.blue(), alpha_int))

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

            # Additional subtle warning border glow when in Bahaya
            if self.risk_category == "Bahaya" and self.current_opacity > 0.2:
                edge_glow_alpha = int(self.current_opacity * 140)
                pen = QPen(QColor(239, 68, 68, edge_glow_alpha), 8)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(self.rect())

        # 2. Subtle Discreet Status Pill (Top-Right Screen Corner)
        if self.show_hud_pill and self.risk_category in ["Waspada", "Bahaya"]:
            pill_w = 160
            pill_h = 32
            pill_x = w - pill_w - 24
            pill_y = 20

            # Glass background
            painter.setBrush(QBrush(QColor(15, 23, 42, int(min(220, self.current_opacity * 280 + 80)))))
            pill_color = QColor(245, 158, 11) if self.risk_category == "Waspada" else QColor(239, 68, 68)
            painter.setPen(QPen(pill_color, 1.5))
            painter.drawRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), 16, 16)

            # Warning icon dot
            painter.setBrush(QBrush(pill_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(pill_x + 18, pill_y + 16), 5, 5)

            # Text
            painter.setPen(QColor(248, 250, 252))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            hud_text = f"SIERRA: {self.risk_category.upper()}"
            painter.drawText(QRectF(pill_x + 30, pill_y, pill_w - 35, pill_h), Qt.AlignVCenter | Qt.AlignLeft, hud_text)
