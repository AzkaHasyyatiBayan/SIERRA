import math
import time
import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from .pose_detector import PoseDetector
from .fuzzy_engine import MamdaniFuzzyEngine
from .calibrator import BaselineCalibrator
from .game_detector import GameModeDetector
from .privacy_resource_manager import PrivacyResourceManager
from .ar_renderer import ARRenderer


class CameraWorker(QThread):
    # Signals for UI communication
    metrics_updated = pyqtSignal(dict)           # Live angles, risk score, category, coords
    calibration_updated = pyqtSignal(dict)       # Progress (0.0-1.0), is_done, baseline
    status_updated = pyqtSignal(str, bool)       # Message, is_error
    fps_updated = pyqtSignal(float)              # Calculated tracking FPS
    resource_metrics_updated = pyqtSignal(dict)  # RAM (MB), CPU (%), Frames Dropped
    frame_ready = pyqtSignal(object)             # QImage frame with AR HUD overlay

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.simulation_mode = False
        self.simulation_scenario = "auto"  # "auto" or "manual"

        # Manual mode state
        self.manual_mode = False
        self.manual_neck = 10.0
        self.manual_shoulder = 0.0
        self.manual_norm_x = 0.5
        self.manual_norm_y = 0.5

        # Core engines
        self.detector = PoseDetector()
        self.fuzzy_engine = MamdaniFuzzyEngine()
        self.calibrator = BaselineCalibrator(duration_seconds=10.0)
        self.game_detector = GameModeDetector()
        self.privacy_manager = PrivacyResourceManager(memory_cleanup_interval=120)

        # Posture state tracking
        self.posture_start_time = time.time()
        self.current_risk_category = "Aman"
        self.current_duration = 0.0

        # Game mode throttle control
        self.game_mode_enabled = True

    def set_camera_index(self, index: int):
        self.camera_index = index

    def set_manual_angles(self, neck: float, shoulder: float, norm_x: float = 0.5, norm_y: float = 0.5):
        """Called from mouse interaction on the camera label (manual mode only)."""
        if not self.manual_mode:
            return  # Ignore mouse input when not in manual mode

        self.manual_neck = float(neck)
        self.manual_shoulder = float(shoulder)
        self.manual_norm_x = float(norm_x)
        self.manual_norm_y = float(norm_y)

        # Adapt simulated duration based on posture severity for instant response
        now = time.time()
        if self.manual_neck >= 28.0 or abs(self.manual_shoulder) >= 9.0:
            self.posture_start_time = now - 65.0
        elif self.manual_neck >= 18.0 or abs(self.manual_shoulder) >= 4.0:
            self.posture_start_time = now - 24.0
        else:
            self.posture_start_time = now

    def set_simulation_mode(self, enabled: bool, scenario: str = "auto"):
        """Enables or disables simulation mode (no webcam needed)."""
        self.simulation_mode = enabled
        self.simulation_scenario = scenario
        self.manual_mode = (scenario == "manual")
        self.posture_start_time = time.time()

        # Reset manual defaults when switching
        if self.manual_mode:
            self.manual_neck = 10.0
            self.manual_shoulder = 0.0
            self.manual_norm_x = 0.5
            self.manual_norm_y = 0.5

        scenario_labels = {
            "auto": "Siklus Otomatis (Normal → Sedang → Bahaya)",
            "manual": "Manual Interaktif (Geser Kursor)"
        }
        label = scenario_labels.get(scenario, scenario)
        if enabled:
            self.status_updated.emit(f"Mode Simulasi: {label}", False)
        else:
            self.status_updated.emit("Beralih ke Kamera Fisik (Webcam)...", False)

    def set_baseline(self, neck: float, shoulder: float):
        self.calibrator.baseline_neck = neck
        self.calibrator.baseline_shoulder = shoulder
        self.calibrator.is_calibrated = True

    def start_calibration(self):
        self.calibrator.start_calibration()

    def stop_worker(self):
        self.running = False
        self.wait(1500)

    def _get_auto_simulation_angles(self, sim_elapsed: float):
        """
        Auto simulation: cycles through 3 distinct phases with smooth transitions.
        Total cycle = 24 seconds (8s each phase).
        Each phase smoothly transitions into the next.
        """
        cycle_duration = 24.0
        cycle_t = sim_elapsed % cycle_duration
        phase_duration = 8.0

        if cycle_t < phase_duration:
            # Phase 1: NORMAL posture (Aman)
            # Smooth ease: slight natural sway
            t = cycle_t / phase_duration
            neck = 5.0 + math.sin(t * math.pi) * 3.0
            shoulder = 1.0 + math.sin(t * math.pi * 2) * 1.0
            duration = 0.0
            label = "FASE: POSTUR NORMAL (Aman)"

        elif cycle_t < phase_duration * 2:
            # Phase 2: SLOUCHING / WARNING (Waspada)
            t = (cycle_t - phase_duration) / phase_duration
            # Gradually slouch forward
            neck = 8.0 + t * 14.0  # 8 -> 22
            shoulder = 2.0 + t * 4.0  # 2 -> 6
            duration = 15.0 + t * 15.0  # 15 -> 30
            label = "FASE: POSTUR SEDANG (Waspada)"

        else:
            # Phase 3: DANGER posture (Bahaya)
            t = (cycle_t - phase_duration * 2) / phase_duration
            # Heavily slouched, asymmetric
            neck = 28.0 + t * 12.0  # 28 -> 40
            shoulder = 6.0 + t * 5.0  # 6 -> 11
            duration = 50.0 + t * 20.0  # 50 -> 70
            label = "FASE: POSTUR BAHAYA (Berbahaya)"

        return neck, shoulder, duration, label

    def run(self):
        self.running = True

        # Attempt to open physical webcam if not explicitly in simulation mode
        if not self.simulation_mode:
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(self.camera_index)

            if not cap.isOpened():
                self.status_updated.emit(
                    "Webcam tidak terdeteksi. Otomatis beralih ke Mode Simulasi (Demo)...",
                    False
                )
                self.simulation_mode = True
                cap = None
            else:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                self.status_updated.emit("Kamera fisik aktif. Pelacakan AR ergonomi berjalan...", False)
        else:
            cap = None
            self.status_updated.emit("Mode Simulasi (Demo) aktif.", False)

        frame_count = 0
        fps_start = time.time()
        sim_start_time = time.time()
        current_fps = 30.0

        while self.running:
            loop_start = time.time()

            # =========================================================================
            # PATH A: SIMULATION / DEMO MODE (NO CAMERA NEEDED)
            # =========================================================================
            if self.simulation_mode or cap is None:
                sim_elapsed = time.time() - sim_start_time
                phase_label = ""

                if self.manual_mode:
                    # === MANUAL MODE: Angles come from mouse input ===
                    raw_neck = self.manual_neck
                    raw_shoulder = self.manual_shoulder
                    now = time.time()
                    self.current_duration = max(0.0, now - self.posture_start_time)
                    phase_label = ""
                else:
                    # === AUTO MODE: Pre-defined animated cycle ===
                    raw_neck, raw_shoulder, self.current_duration, phase_label = \
                        self._get_auto_simulation_angles(sim_elapsed)

                # Calibration handling in simulation
                if self.calibrator.is_calibrating:
                    is_done, prog, baseline = self.calibrator.process_frame(raw_neck, raw_shoulder)
                    self.calibration_updated.emit({
                        "is_calibrating": True,
                        "progress": prog,
                        "is_done": is_done,
                        "baseline": baseline
                    })
                    effective_neck, effective_shoulder = raw_neck, raw_shoulder
                else:
                    effective_neck, effective_shoulder = self.calibrator.get_effective_deviation(raw_neck, raw_shoulder)

                # Mamdani Fuzzy Evaluation
                risk_score, risk_cat = self.fuzzy_engine.evaluate(
                    neck_deg=effective_neck,
                    shoulder_deg=effective_shoulder,
                    duration_sec=self.current_duration
                )
                self.current_risk_category = risk_cat

                # Generate Synthetic Frame — NO mouse_norm_pos for auto mode
                synth_frame, synth_coords = ARRenderer.generate_synthetic_frame(
                    neck_angle=effective_neck,
                    shoulder_angle=effective_shoulder,
                    phase=sim_elapsed,
                    mouse_norm_pos=None,  # Arms always natural in synthetic
                    phase_label=phase_label
                )

                # Render High-Tech AR HUD over Synthetic Camera Frame
                ar_frame = ARRenderer.draw_ar_hud(
                    frame=synth_frame,
                    head_pt=synth_coords["head"],
                    shoulder_mid=synth_coords["shoulder_mid"],
                    left_sh=synth_coords["left_shoulder"],
                    right_sh=synth_coords["right_shoulder"],
                    neck_angle=effective_neck,
                    shoulder_angle=effective_shoulder,
                    risk_score=risk_score,
                    risk_cat=risk_cat,
                    fps=current_fps,
                    is_simulation=True,
                    extra_coords=synth_coords
                )

                # Convert to QImage for live AR view
                rgb_ar = cv2.cvtColor(ar_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_ar.shape
                q_img = QImage(rgb_ar.data, w, h, ch * w, QImage.Format_RGB888).copy()
                self.frame_ready.emit(q_img)

                # Emit metrics
                self.metrics_updated.emit({
                    "raw_neck": round(raw_neck, 1),
                    "raw_shoulder": round(raw_shoulder, 1),
                    "effective_neck": round(effective_neck, 1),
                    "effective_shoulder": round(effective_shoulder, 1),
                    "duration_sec": self.current_duration,
                    "risk_score": risk_score,
                    "risk_category": risk_cat,
                    "skeleton": synth_coords
                })

                self.privacy_manager.drop_frame()
                frame_count += 1
                if time.time() - fps_start >= 1.0:
                    current_fps = 30.0
                    self.fps_updated.emit(30.0)
                    self.resource_metrics_updated.emit(self.privacy_manager.get_resource_metrics())
                    fps_start = time.time()

                time.sleep(0.033)  # ~30 FPS
                continue

            # =========================================================================
            # PATH B: PHYSICAL WEBCAM TRACKING (WITH AR HUD & EPHEMERAL FRAME DROPPER)
            # =========================================================================
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            # Mirror the camera frame horizontally for better user experience
            frame = cv2.flip(frame, 1)

            frame_count += 1
            if time.time() - fps_start >= 1.0:
                current_fps = frame_count / (time.time() - fps_start)
                self.fps_updated.emit(round(current_fps, 1))
                self.resource_metrics_updated.emit(self.privacy_manager.get_resource_metrics())
                frame_count = 0
                fps_start = time.time()

            # Crop to 16:9 landscape to avoid distortion
            h_orig, w_orig = frame.shape[:2]
            target_h = int(w_orig * 9 / 16)
            if h_orig > target_h:
                y_offset = (h_orig - target_h) // 2
                proc_frame = frame[y_offset:y_offset+target_h, :]
            else:
                proc_frame = frame

            # Resize to standard 640x360
            proc_frame = cv2.resize(proc_frame, (640, 360), interpolation=cv2.INTER_LINEAR)
            rgb_frame = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)

            # === MediaPipe Inference ===
            landmarks = self.detector.extract_landmarks(rgb_frame)

            if landmarks is not None:
                angles = self.detector.calculate_angles(landmarks, 640, 360)
            else:
                angles = None

            if angles is not None:
                raw_neck = angles["neck_angle"]
                raw_shoulder = angles["shoulder_angle"]

                # Calibration check
                if self.calibrator.is_calibrating:
                    is_done, prog, baseline = self.calibrator.process_frame(raw_neck, raw_shoulder)
                    self.calibration_updated.emit({
                        "is_calibrating": True,
                        "progress": prog,
                        "is_done": is_done,
                        "baseline": baseline
                    })
                    effective_neck, effective_shoulder = raw_neck, raw_shoulder
                else:
                    effective_neck, effective_shoulder = self.calibrator.get_effective_deviation(raw_neck, raw_shoulder)

                # Duration tracking
                now = time.time()
                if effective_neck < 10.0 and effective_shoulder < 5.0:
                    self.current_duration = 0.0
                    self.posture_start_time = now
                else:
                    self.current_duration = now - self.posture_start_time

                # Mamdani Fuzzy Risk Evaluation
                risk_score, risk_cat = self.fuzzy_engine.evaluate(
                    neck_deg=effective_neck,
                    shoulder_deg=effective_shoulder,
                    duration_sec=self.current_duration
                )
                self.current_risk_category = risk_cat

                # Collect extra landmark coordinates for arm/torso drawing
                extra = {}
                for key in ["left_elbow", "right_elbow", "left_wrist", "right_wrist", "left_hip", "right_hip"]:
                    extra[key] = angles.get(key)

                # Draw AR HUD over the webcam frame
                ar_frame = ARRenderer.draw_ar_hud(
                    frame=proc_frame,
                    head_pt=angles["head_point"],
                    shoulder_mid=angles["shoulder_mid"],
                    left_sh=angles["left_shoulder"],
                    right_sh=angles["right_shoulder"],
                    neck_angle=effective_neck,
                    shoulder_angle=effective_shoulder,
                    risk_score=risk_score,
                    risk_cat=risk_cat,
                    fps=current_fps,
                    is_simulation=False,
                    extra_coords=extra
                )

                rgb_ar = cv2.cvtColor(ar_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_ar.shape
                q_img = QImage(rgb_ar.data, w, h, ch * w, QImage.Format_RGB888).copy()
                self.frame_ready.emit(q_img)

                # Emit metrics to UI
                self.metrics_updated.emit({
                    "raw_neck": raw_neck,
                    "raw_shoulder": raw_shoulder,
                    "effective_neck": effective_neck,
                    "effective_shoulder": effective_shoulder,
                    "duration_sec": self.current_duration,
                    "risk_score": risk_score,
                    "risk_category": risk_cat,
                    "skeleton": {
                        "head": angles["head_point"],
                        "shoulder_mid": angles["shoulder_mid"],
                        "left_shoulder": angles["left_shoulder"],
                        "right_shoulder": angles["right_shoulder"],
                        "nose": angles["nose"]
                    }
                })
            else:
                # No person detected in camera view
                cv2.putText(proc_frame, "MENUNGGU SUBJEK DI DEPAN KAMERA...", (30, 180),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184), 2, cv2.LINE_AA)
                rgb_ar = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_ar.shape
                q_img = QImage(rgb_ar.data, w, h, ch * w, QImage.Format_RGB888).copy()
                self.frame_ready.emit(q_img)

                self.metrics_updated.emit({
                    "raw_neck": 0.0,
                    "raw_shoulder": 0.0,
                    "effective_neck": 0.0,
                    "effective_shoulder": 0.0,
                    "duration_sec": 0.0,
                    "risk_score": 0.0,
                    "risk_category": "Tidak Terdeteksi",
                    "skeleton": None
                })

            # === EPHEMERAL FRAME DROPPER (Privacy by Design) ===
            # Instantly drop, zero out and destroy raw camera frames from memory
            self.privacy_manager.drop_frame(frame, proc_frame, rgb_frame)
            del frame
            del proc_frame
            del rgb_frame

            # === Dynamic Game-Mode Thread / Rate Throttling ===
            target_fps = 30.0
            if self.game_mode_enabled:
                is_game, _ = self.game_detector.is_fullscreen_or_game_running()
                if is_game:
                    target_fps = 15.0

            elapsed = time.time() - loop_start
            sleep_time = max(0.001, (1.0 / target_fps) - elapsed)
            time.sleep(sleep_time)

        if cap is not None:
            cap.release()
        self.status_updated.emit("Pemantauan dihentikan.", False)
