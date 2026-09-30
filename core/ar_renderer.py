import math
import cv2
import numpy as np
from typing import Dict, Tuple, Optional, Any


def get_risk_bgr_color(category: str) -> Tuple[int, int, int]:
    """Returns BGR color tuple for OpenCV drawing."""
    if category == "Aman":
        return (166, 184, 20)   # Tosca / Teal (BGR)
    elif category == "Waspada":
        return (11, 158, 245)   # Amber (BGR)
    else:
        return (94, 63, 244)    # Rose Crimson (BGR)


class ARRenderer:
    @staticmethod
    def draw_ar_hud(
        frame: np.ndarray,
        head_pt: Tuple[float, float],
        shoulder_mid: Tuple[float, float],
        left_sh: Tuple[float, float],
        right_sh: Tuple[float, float],
        neck_angle: float,
        shoulder_angle: float,
        risk_score: float,
        risk_cat: str,
        fps: float,
        is_simulation: bool = False,
        extra_coords: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """Draws high-tech cyber ergonomics AR overlay onto image frame."""
        h, w = frame.shape[:2]
        canvas = frame.copy()
        accent_bgr = get_risk_bgr_color(risk_cat)

        # Convert normalized coords [0-1] to pixel space
        def to_px(pt):
            return int(pt[0] * w), int(pt[1] * h)

        px_head = to_px(head_pt)
        px_mid_sh = to_px(shoulder_mid)
        px_l_sh = to_px(left_sh)
        px_r_sh = to_px(right_sh)

        # 1. Semi-transparent HUD overlay pass
        hud_layer = canvas.copy()
        # Top banner
        cv2.rectangle(hud_layer, (0, 0), (w, 36), (8, 14, 24), -1)
        # Bottom banner
        cv2.rectangle(hud_layer, (0, h - 38), (w, h), (8, 14, 24), -1)
        cv2.addWeighted(hud_layer, 0.75, canvas, 0.25, 0, canvas)

        # 2. Draw Bones & Connecting Segments
        # Shoulder Clavicle Line
        cv2.line(canvas, px_l_sh, px_r_sh, accent_bgr, 3, cv2.LINE_AA)
        # Cervical Neck Spine Line
        cv2.line(canvas, px_mid_sh, px_head, accent_bgr, 3, cv2.LINE_AA)

        # 3. Draw Joint Nodes with Glowing Halos
        for pt in [px_l_sh, px_r_sh, px_mid_sh]:
            cv2.circle(canvas, pt, 7, (240, 253, 250), -1, cv2.LINE_AA)
            cv2.circle(canvas, pt, 9, accent_bgr, 2, cv2.LINE_AA)

        # 3.5 Draw Arms and Torso if available
        if extra_coords:
            def cpx(key):
                if key in extra_coords and extra_coords[key] is not None:
                    return to_px(extra_coords[key])
                return None

            p_lelbow = cpx("left_elbow")
            p_relbow = cpx("right_elbow")
            p_lwrist = cpx("left_wrist")
            p_rwrist = cpx("right_wrist")
            p_lhip = cpx("left_hip")
            p_rhip = cpx("right_hip")

            # Draw lines
            if p_lelbow:
                cv2.line(canvas, px_l_sh, p_lelbow, accent_bgr, 2, cv2.LINE_AA)
                cv2.circle(canvas, p_lelbow, 6, (240, 253, 250), -1, cv2.LINE_AA)
                if p_lwrist:
                    cv2.line(canvas, p_lelbow, p_lwrist, accent_bgr, 2, cv2.LINE_AA)
                    cv2.circle(canvas, p_lwrist, 5, (200, 220, 240), -1, cv2.LINE_AA)
            if p_relbow:
                cv2.line(canvas, px_r_sh, p_relbow, accent_bgr, 2, cv2.LINE_AA)
                cv2.circle(canvas, p_relbow, 6, (240, 253, 250), -1, cv2.LINE_AA)
                if p_rwrist:
                    cv2.line(canvas, p_relbow, p_rwrist, accent_bgr, 2, cv2.LINE_AA)
                    cv2.circle(canvas, p_rwrist, 5, (200, 220, 240), -1, cv2.LINE_AA)
            if p_lhip and p_rhip:
                cv2.line(canvas, px_l_sh, p_lhip, accent_bgr, 2, cv2.LINE_AA)
                cv2.line(canvas, px_r_sh, p_rhip, accent_bgr, 2, cv2.LINE_AA)
                cv2.line(canvas, p_lhip, p_rhip, accent_bgr, 2, cv2.LINE_AA)
                cv2.circle(canvas, p_lhip, 6, (240, 253, 250), -1, cv2.LINE_AA)
                cv2.circle(canvas, p_rhip, 6, (240, 253, 250), -1, cv2.LINE_AA)

        # Head Cranium Target Ring
        cv2.circle(canvas, px_head, 18, accent_bgr, 2, cv2.LINE_AA)
        cv2.circle(canvas, px_head, 24, (accent_bgr[0]//2, accent_bgr[1]//2, accent_bgr[2]//2), 1, cv2.LINE_AA)
        cv2.circle(canvas, px_head, 4, (240, 253, 250), -1, cv2.LINE_AA)

        # 4. Angle Telemetry Tags directly over joints
        # Neck Angle Tag
        tag_neck = f"LEHER: {neck_angle:.1f} DEG"
        cv2.putText(canvas, tag_neck, (px_head[0] + 28, max(45, px_head[1] - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 253, 250), 1, cv2.LINE_AA)

        # Shoulder Tilt Tag
        tag_sh = f"BAHU: {shoulder_angle:.1f} DEG"
        cv2.putText(canvas, tag_sh, (px_r_sh[0] + 10, min(h - 45, px_r_sh[1] + 16)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 220, 240), 1, cv2.LINE_AA)

        # 5. Top Bar Information
        mode_str = "SIMULASI SINTETIS" if is_simulation else "KAMERA FISIK"
        cv2.putText(canvas, f"SIERRA AR SCANNER [{mode_str}]", (14, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (20, 184, 166), 1, cv2.LINE_AA)

        cv2.putText(canvas, f"FPS: {fps:.1f}", (w - 95, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 220, 240), 1, cv2.LINE_AA)

        # 6. Bottom Status Banner
        cv2.putText(canvas, f"STATUS: {risk_cat.upper()} (SKOR: {int(risk_score)})", (14, h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, accent_bgr, 1, cv2.LINE_AA)

        cv2.putText(canvas, "PRIVACY: ZERO-RETENTION", (w - 220, h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 180, 160), 1, cv2.LINE_AA)

        return canvas

    @staticmethod
    def generate_synthetic_frame(
        neck_angle: float,
        shoulder_angle: float,
        phase: float = 0.0,
        mouse_norm_pos: Optional[Tuple[float, float]] = None,
        w: int = 640,
        h: int = 360,
        phase_label: str = ""
    ) -> Tuple[np.ndarray, Dict[str, Tuple[float, float]]]:
        """
        Generates a synthetic camera image depicting a seated gamer in a dark ambient room.
        The skeleton dynamically adapts to neck_angle and shoulder_angle.
        If mouse_norm_pos is provided, the head+neck track the mouse (manual mode).
        """
        # Create dark ambient workstation background
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Background subtle gradient
        for y in range(h):
            ratio = y / float(h)
            frame[y, :] = (int(14 + ratio * 8), int(20 + ratio * 10), int(30 + ratio * 12))

        # Ambient monitor glow on desk
        cv2.ellipse(frame, (w // 2, h - 30), (w // 3, 40), 0, 0, 360, (30, 45, 60), -1)

        # Gaming chair silhouette
        chair_color = (25, 32, 45)
        chair_back_top = 70
        chair_pts = np.array([
            [w // 2 - 75, chair_back_top],
            [w // 2 + 75, chair_back_top],
            [w // 2 + 85, h - 40],
            [w // 2 - 85, h - 40]
        ], np.int32)
        cv2.fillPoly(frame, [chair_pts], chair_color)
        cv2.polylines(frame, [chair_pts], True, (40, 55, 75), 2)

        # Calculate gamer body kinematics
        sh_center_x = w / 2.0
        sh_y = float(h * 0.58)
        sh_span = float(w * 0.22)

        # Shoulder tilt
        sh_tilt_px = (shoulder_angle / 25.0) * 22.0
        l_sh = (sh_center_x - sh_span, sh_y + sh_tilt_px)
        r_sh = (sh_center_x + sh_span, sh_y - sh_tilt_px)
        mid_sh = (sh_center_x, sh_y)

        # Head flexion calculation
        neck_len = float(h * 0.26)
        slouch_drop = (neck_angle / 50.0) * 40.0
        lateral_offset = (shoulder_angle / 25.0) * 18.0 + math.sin(phase * 0.5) * 1.5
        head_x = sh_center_x + lateral_offset
        head_y = (sh_y - neck_len) + slouch_drop

        # Draw Person Silhouette (Torso & Shoulders)
        body_color = (38, 48, 65)
        torso_pts = np.array([
            [int(l_sh[0]), int(l_sh[1])],
            [int(r_sh[0]), int(r_sh[1])],
            [int(sh_center_x + 60), h - 10],
            [int(sh_center_x - 60), h - 10]
        ], np.int32)
        cv2.fillPoly(frame, [torso_pts], body_color)

        # Neck column
        cv2.line(frame, (int(mid_sh[0]), int(mid_sh[1])), (int(head_x), int(head_y)), (45, 55, 75), 24)

        # Head dome
        head_radius = 28
        cv2.circle(frame, (int(head_x), int(head_y)), head_radius, (48, 60, 80), -1)

        # Headset headband & earcups
        cv2.ellipse(frame, (int(head_x), int(head_y) - 6), (head_radius + 4, head_radius + 2), 0, 180, 360, (20, 184, 166), 4)
        cv2.circle(frame, (int(head_x) - head_radius - 2, int(head_y)), 9, (20, 184, 166), -1)
        cv2.circle(frame, (int(head_x) + head_radius + 2, int(head_y)), 9, (20, 184, 166), -1)

        # Draw Arms (resting naturally for both modes)
        arm_color = (40, 50, 65)
        # Left arm: shoulder -> elbow -> wrist (resting on desk)
        l_elbow = (int(l_sh[0] - 35), int(l_sh[1] + 50))
        l_wrist = (int(l_sh[0] - 20), int(h - 45))
        cv2.line(frame, (int(l_sh[0]), int(l_sh[1])), l_elbow, arm_color, 16)
        cv2.line(frame, l_elbow, l_wrist, arm_color, 14)

        # Right arm
        r_elbow = (int(r_sh[0] + 35), int(r_sh[1] + 50))
        r_wrist = (int(r_sh[0] + 20), int(h - 45))
        cv2.line(frame, (int(r_sh[0]), int(r_sh[1])), r_elbow, arm_color, 16)
        cv2.line(frame, r_elbow, r_wrist, arm_color, 14)

        # Hip points (bottom of torso)
        l_hip = (int(sh_center_x - 55), h - 15)
        r_hip = (int(sh_center_x + 55), h - 15)

        # Phase label overlay (for auto simulation)
        if phase_label:
            label_color = get_risk_bgr_color(
                "Aman" if "Normal" in phase_label else
                "Waspada" if "Sedang" in phase_label else "Bahaya"
            )
            cv2.putText(frame, phase_label, (14, h - 48),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, label_color, 2, cv2.LINE_AA)

        coords = {
            "head": (head_x / w, head_y / h),
            "shoulder_mid": (mid_sh[0] / w, mid_sh[1] / h),
            "left_shoulder": (l_sh[0] / w, l_sh[1] / h),
            "right_shoulder": (r_sh[0] / w, r_sh[1] / h),
            "nose": (head_x / w, (head_y + 2) / h),
            "left_elbow": (l_elbow[0] / w, l_elbow[1] / h),
            "right_elbow": (r_elbow[0] / w, r_elbow[1] / h),
            "left_wrist": (l_wrist[0] / w, l_wrist[1] / h),
            "right_wrist": (r_wrist[0] / w, r_wrist[1] / h),
            "left_hip": (l_hip[0] / w, l_hip[1] / h),
            "right_hip": (r_hip[0] / w, r_hip[1] / h),
        }

        return frame, coords
