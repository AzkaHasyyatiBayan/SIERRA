import os
import math
import urllib.request
import numpy as np
from typing import Dict, Optional, Tuple, Any

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
MODEL_FILENAME = "pose_landmarker_lite.task"


class PoseDetector:
    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.mode = None  # "tasks" or "solutions"
        self.landmarker = None
        self.solutions_pose = None
        self._init_detector()

    def _get_model_path(self) -> str:
        # Search relative to current file or working directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        candidates = [
            os.path.join(project_root, MODEL_FILENAME),
            os.path.join(current_dir, MODEL_FILENAME),
            os.path.join(os.getcwd(), MODEL_FILENAME)
        ]
        for p in candidates:
            if os.path.exists(p):
                return p

        # If not found, download to project root
        target_path = os.path.join(project_root, MODEL_FILENAME)
        try:
            print(f"[PoseDetector] Downloading {MODEL_FILENAME}...")
            urllib.request.urlretrieve(MODEL_URL, target_path)
            return target_path
        except Exception as e:
            print(f"[PoseDetector] Failed to download model: {e}")
            return target_path

    def _init_detector(self):
        import mediapipe as mp

        # 1. Try modern MediaPipe Tasks API (MediaPipe 1.0+)
        try:
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.core import base_options

            model_path = self._get_model_path()
            if os.path.exists(model_path):
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options.BaseOptions(model_asset_path=model_path),
                    running_mode=vision.RunningMode.IMAGE,
                    min_pose_detection_confidence=self.min_detection_confidence,
                    min_tracking_confidence=self.min_tracking_confidence,
                    output_segmentation_masks=False
                )
                self.landmarker = vision.PoseLandmarker.create_from_options(options)
                self.mode = "tasks"
                return
        except Exception as e:
            print(f"[PoseDetector] Tasks API init skipped: {e}")

        # 2. Fallback to legacy mp.solutions.pose
        try:
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "pose"):
                self.mp_pose = mp.solutions.pose
                self.solutions_pose = self.mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=0,
                    smooth_landmarks=True,
                    enable_segmentation=False,
                    min_detection_confidence=self.min_detection_confidence,
                    min_tracking_confidence=self.min_tracking_confidence
                )
                self.mode = "solutions"
                return
        except Exception as e:
            print(f"[PoseDetector] Solutions API init failed: {e}")

        print("[PoseDetector] Warning: Neither Tasks nor Solutions Pose could be initialized.")

    def extract_landmarks(self, rgb_frame: np.ndarray) -> Optional[Any]:
        """Runs MediaPipe inference on RGB frame."""
        if self.mode is None:
            self._init_detector()

        if self.mode == "tasks" and self.landmarker is not None:
            import mediapipe as mp
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = self.landmarker.detect(mp_image)
            if result and result.pose_landmarks and len(result.pose_landmarks) > 0:
                # Returns the first detected person's 33 landmarks
                return result.pose_landmarks[0]
            return None

        elif self.mode == "solutions" and self.solutions_pose is not None:
            results = self.solutions_pose.process(rgb_frame)
            if results and results.pose_landmarks:
                return results.pose_landmarks.landmark
            return None

        return None

    def calculate_angles(self, landmarks, frame_w: int = 640, frame_h: int = 480) -> Optional[Dict[str, Any]]:
        """
        Calculates Neck Angle and Shoulder Angle from extracted landmarks.
        Landmark indices:
            0: nose
            7: left ear, 8: right ear
            11: left shoulder, 12: right shoulder
        """
        if landmarks is None or len(landmarks) < 13:
            return None

        # Check visibility / presence of essential landmarks
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        nose = landmarks[0]

        # Landmark attribute handling (both Tasks and Solutions have .x, .y, .z, .visibility)
        def get_vis(pt):
            return getattr(pt, "visibility", 1.0) if getattr(pt, "visibility", None) is not None else 1.0

        if get_vis(left_shoulder) < 0.35 and get_vis(right_shoulder) < 0.35:
            return None

        l_ear = np.array([landmarks[7].x, landmarks[7].y, landmarks[7].z])
        r_ear = np.array([landmarks[8].x, landmarks[8].y, landmarks[8].z])
        l_sh = np.array([left_shoulder.x, left_shoulder.y, left_shoulder.z])
        r_sh = np.array([right_shoulder.x, right_shoulder.y, right_shoulder.z])
        nose_pt = np.array([nose.x, nose.y, nose.z])

        # Head centroid (prefer ears midpoint, fallback to nose)
        if get_vis(landmarks[7]) > 0.35 and get_vis(landmarks[8]) > 0.35:
            head_pt = (l_ear + r_ear) / 2.0
        else:
            head_pt = nose_pt

        # Shoulder midpoint
        shoulder_mid = (l_sh + r_sh) / 2.0

        # --- 1. Neck Flexion Angle (Kemiringan Leher) ---
        vec_neck = head_pt - shoulder_mid
        dx = vec_neck[0]
        dy = -vec_neck[1]  # Inverted Y for image space
        dz = vec_neck[2]   # Z depth

        # Forward head posture detection via vertical displacement
        # When head drops (dy gets smaller), the angle increases
        # Also consider lateral tilt
        angle_lateral = math.degrees(math.atan2(abs(dx), max(0.001, dy))) * 0.85
        
        # Forward posture: z-depth is unreliable from frontal cam, 
        # so primarily use vertical head drop relative to shoulders
        # The less vertical distance between head and shoulders, the more slouched
        vertical_ratio = max(0.0, 1.0 - (dy / 0.25)) * 15.0  # Head drop component
        vertical_ratio = max(0.0, min(40.0, vertical_ratio))
        
        # Z-based forward lean (secondary, less weight)
        forward_z = max(0.0, -dz)
        angle_sagittal = math.degrees(math.atan2(forward_z, max(0.001, dy))) * 0.5
        
        neck_angle = math.sqrt(angle_lateral**2 + vertical_ratio**2 + angle_sagittal**2)
        neck_angle = max(0.0, min(80.0, neck_angle))

        # --- 2. Shoulder Tilt / Asymmetry (Kemiringan Bahu) ---
        d_sh_x = r_sh[0] - l_sh[0]
        d_sh_y = r_sh[1] - l_sh[1]
        shoulder_angle = abs(math.degrees(math.atan2(d_sh_y, abs(d_sh_x))))
        shoulder_angle = max(0.0, min(45.0, shoulder_angle))

        def get_pt(idx):
            pt = landmarks[idx]
            return (pt.x, pt.y) if get_vis(pt) > 0.2 else None

        return {
            "neck_angle": round(neck_angle, 1),
            "shoulder_angle": round(shoulder_angle, 1),
            "head_point": (head_pt[0], head_pt[1]),
            "shoulder_mid": (shoulder_mid[0], shoulder_mid[1]),
            "left_shoulder": (l_sh[0], l_sh[1]),
            "right_shoulder": (r_sh[0], r_sh[1]),
            "nose": (nose_pt[0], nose_pt[1]),
            "left_elbow": get_pt(13),
            "right_elbow": get_pt(14),
            "left_wrist": get_pt(15),
            "right_wrist": get_pt(16),
            "left_hip": get_pt(23),
            "right_hip": get_pt(24),
        }
