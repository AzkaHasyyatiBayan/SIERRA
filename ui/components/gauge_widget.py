"""
Animated Circular Risk Gauge Widget for SIERRA.
Classy, modern circular telemetry meter with smooth gradient sweep,
precision typography, and dynamic glow (Zero emojis).
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QRadialGradient
from PyQt5.QtCore import Qt, QRectF, QTimer, QPointF


class CircularRiskGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)

        self.target_score = 0.0
        self.current_score = 0.0
        self.category = "Aman"

        # Smooth 60fps animation
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_step)
        self.anim_timer.start(16)

    def set_risk(self, score: float, category: str):
        self.target_score = max(0.0, min(100.0, score))
        self.category = category

    def _animate_step(self):
        diff = self.target_score - self.current_score
        if abs(diff) > 0.08:
            self.current_score += diff * 0.14
            self.update()

    def _get_color(self) -> QColor:
        if self.current_score < 30.0:
            return QColor(20, 184, 166)  # Tosca / Teal 500
        elif self.current_score < 65.0:
            return QColor(245, 158, 11)  # Warm Amber
        else:
            return QColor(244, 63, 94)   # Rose Crimson

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        dim = min(w, h) - 32
        rect = QRectF((w - dim) / 2.0, (h - dim) / 2.0, dim, dim)
        center = QPointF(w / 2.0, h / 2.0)

        # 1. Dark Gauge Pod Background
        pod_gradient = QRadialGradient(center, dim * 0.65)
        pod_gradient.setColorAt(0.0, QColor(13, 22, 35, 230))
        pod_gradient.setColorAt(1.0, QColor(7, 12, 20, 245))
        painter.setBrush(QBrush(pod_gradient))
        painter.setPen(QPen(QColor(19, 78, 74, 90), 1.2))
        painter.drawRoundedRect(8, 8, int(w - 16), int(h - 16), 18, 18)

        # 2. Track Base Arc (240-degree sweep from 150 deg)
        start_angle = 150 * 16
        span_angle = -240 * 16

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(30, 41, 59, 140), 14, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, start_angle, span_angle)

        # 3. Active Risk Arc
        active_color = self._get_color()
        active_span = int((-240 * (self.current_score / 100.0)) * 16)

        # Subtle Arc Glow
        painter.setPen(QPen(QColor(active_color.red(), active_color.green(), active_color.blue(), 50), 22, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, start_angle, active_span)

        # Core Arc Line
        painter.setPen(QPen(active_color, 12, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, start_angle, active_span)

        # 4. Center Numerical Score
        painter.setPen(QColor(240, 253, 250))
        painter.setFont(QFont("Segoe UI", 26, QFont.Bold))
        score_str = f"{int(round(self.current_score))}"
        painter.drawText(QRectF(0, h * 0.28, w, 40), Qt.AlignCenter, score_str)

        # Metric Label
        painter.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        painter.setPen(QColor(148, 163, 184))
        painter.drawText(QRectF(0, h * 0.48, w, 18), Qt.AlignCenter, "SKOR RISIKO")

        # Category Badge Strip
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.setPen(active_color)
        cat_text = self.category.upper()
        painter.drawText(QRectF(0, h * 0.62, w, 22), Qt.AlignCenter, cat_text)
