"""
Minimalist Animated Posture Avatar Component for SIERRA.
Sleek, high-tech, organic wireframe skeleton visualization.
Uses Tosca Ephemeral styling with dynamic bezier spine curves, pulsing joint nodes,
and expressive angular articulation (Zero emojis).
"""

import math
import time
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QRadialGradient, QPainterPath
from PyQt5.QtCore import Qt, QPointF, QTimer


class PostureAvatarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(210, 210)

        # Current display targets
        self.target_neck_angle = 0.0
        self.target_shoulder_angle = 0.0
        self.current_neck_angle = 0.0
        self.current_shoulder_angle = 0.0

        self.risk_category = "Aman"
        self.risk_score = 0.0
        self.is_detected = True

        # Phase timer for continuous organic idle/pulse animation
        self.phase = 0.0

        # Animation timer for smooth 60fps interpolation
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_step)
        self.anim_timer.start(16)  # ~60 FPS

    def update_posture(self, neck_angle: float, shoulder_angle: float,
                       risk_score: float, risk_category: str, is_detected: bool = True):
        self.target_neck_angle = neck_angle
        self.target_shoulder_angle = shoulder_angle
        self.risk_score = risk_score
        self.risk_category = risk_category
        self.is_detected = is_detected

    def _animate_step(self):
        # Damping interpolation
        self.current_neck_angle += (self.target_neck_angle - self.current_neck_angle) * 0.14
        self.current_shoulder_angle += (self.target_shoulder_angle - self.current_shoulder_angle) * 0.14
        self.phase += 0.06
        self.update()

    def _get_status_color(self) -> QColor:
        if not self.is_detected:
            return QColor(100, 116, 139)  # Slate gray
        if self.risk_category == "Aman":
            return QColor(20, 184, 166)   # Tosca / Teal 500
        elif self.risk_category == "Waspada":
            return QColor(245, 158, 11)   # Warm Amber
        else:
            return QColor(244, 63, 94)    # Rose Crimson

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        center_x = w / 2.0
        center_y = h / 2.0

        accent_color = self._get_status_color()

        # 1. Dark Ephemeral Radar Pod Background
        pod_gradient = QRadialGradient(QPointF(center_x, center_y), w * 0.6)
        pod_gradient.setColorAt(0.0, QColor(13, 22, 35, 230))
        pod_gradient.setColorAt(1.0, QColor(7, 12, 20, 245))
        painter.setBrush(QBrush(pod_gradient))
        painter.setPen(QPen(QColor(19, 78, 74, 90), 1.2))
        painter.drawRoundedRect(8, 8, int(w - 16), int(h - 16), 18, 18)

        # 2. Concentric Target Rings
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(20, 184, 166, 25), 1, Qt.DashLine))
        painter.drawEllipse(QPointF(center_x, center_y), w * 0.38, h * 0.38)
        painter.drawEllipse(QPointF(center_x, center_y), w * 0.22, h * 0.22)

        # Crosshairs
        painter.setPen(QPen(QColor(20, 184, 166, 30), 1))
        painter.drawLine(int(center_x), 16, int(center_x), int(h - 16))
        painter.drawLine(16, int(center_y), int(w - 16), int(center_y))

        if not self.is_detected:
            painter.setPen(QColor(148, 163, 184))
            painter.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
            painter.drawText(self.rect(), Qt.AlignCenter, "MENUNGGU SUBJEK...")
            return

        # 3. Kinematic Geometry Calculation
        # Shoulder anchors
        sh_base_y = center_y + 30
        sh_span = w * 0.29
        # Tilt calculation (increased multiplier for expressive feedback)
        sh_tilt = self.current_shoulder_angle * 1.5
        left_sh = QPointF(center_x - sh_span, sh_base_y + sh_tilt)
        right_sh = QPointF(center_x + sh_span, sh_base_y - sh_tilt)
        mid_sh = QPointF(center_x, sh_base_y)

        # Torso / Lower spine anchor
        torso_bottom = QPointF(center_x, sh_base_y + 40)

        # Head anchor with forward slouch drop & lateral deflection
        # When neck bends forward (high angle), head drops down significantly and pushes outward
        neck_len = h * 0.30
        head_drop = (self.current_neck_angle / 50.0) * 36.0
        head_sway = math.sin(self.phase * 0.5) * 1.2
        head_lateral = (self.current_shoulder_angle * 0.8) + head_sway
        head_pt = QPointF(center_x + head_lateral, (sh_base_y - neck_len) + head_drop)

        # 4. Draw Spine with Bezier Curve (Organic spinal curvature)
        spine_path = QPainterPath()
        spine_path.moveTo(torso_bottom)
        spine_path.lineTo(mid_sh)
        # Curve from mid-shoulder to head with ergonomic slouch inflection
        ctrl_pt = QPointF(center_x + (head_lateral * 0.5), (mid_sh.y() + head_pt.y()) / 2.0 + (head_drop * 0.3))
        spine_path.quadTo(ctrl_pt, head_pt)

        # Draw spine shadow glow
        painter.setPen(QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 60), 6, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(spine_path)

        # Draw spine core line
        painter.setPen(QPen(accent_color, 3.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(spine_path)

        # 5. Draw Shoulder Clavicle Bar
        painter.setPen(QPen(QColor(15, 118, 110, 80), 8, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(left_sh, right_sh)
        painter.setPen(QPen(accent_color, 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(left_sh, right_sh)

        # 6. Joint Articulation Nodes
        painter.setBrush(QBrush(QColor(240, 253, 250)))
        painter.setPen(QPen(accent_color, 2))
        painter.drawEllipse(left_sh, 4.5, 4.5)
        painter.drawEllipse(right_sh, 4.5, 4.5)
        painter.drawEllipse(mid_sh, 5, 5)
        painter.drawEllipse(torso_bottom, 3.5, 3.5)

        # 7. Head Cranium with Concentric Pulse Ring
        pulse_r = 17 + math.sin(self.phase * 2.0) * 2.5
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 100), 1.5))
        painter.drawEllipse(head_pt, pulse_r, pulse_r)

        # Head Solid Dome
        head_radius = 13.0
        head_glow = QRadialGradient(head_pt, head_radius * 1.8)
        head_glow.setColorAt(0.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 180))
        head_glow.setColorAt(1.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))
        painter.setBrush(QBrush(head_glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(head_pt, head_radius * 1.8, head_radius * 1.8)

        painter.setBrush(QBrush(QColor(10, 20, 30)))
        painter.setPen(QPen(accent_color, 2.5))
        painter.drawEllipse(head_pt, head_radius, head_radius)

        # Center Eye pupil dot
        painter.setBrush(QBrush(accent_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(head_pt, 3, 3)

        # 8. Bottom Angle Telemetry Strip (Precision Typography, Zero Emojis)
        painter.setPen(QColor(204, 251, 241))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        text_str = f"LEHER: {self.current_neck_angle:.1f}°   |   BAHU: {self.current_shoulder_angle:.1f}°"
        painter.drawText(0, int(h - 18), int(w), 16, Qt.AlignCenter, text_str)
