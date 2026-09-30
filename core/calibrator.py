import time
import numpy as np
from typing import List, Optional, Tuple, Callable


class BaselineCalibrator:
    def __init__(self, duration_seconds: float = 10.0, min_samples: int = 15):
        self.duration_seconds = duration_seconds
        self.min_samples = min_samples
        self.is_calibrating = False
        self.start_time: Optional[float] = None
        self.neck_samples: List[float] = []
        self.shoulder_samples: List[float] = []
        
        # Saved baseline
        self.baseline_neck: float = 0.0
        self.baseline_shoulder: float = 0.0
        self.is_calibrated: bool = False

    def start_calibration(self):
        """Starts a fresh 10-second calibration sequence."""
        self.neck_samples.clear()
        self.shoulder_samples.clear()
        self.start_time = time.time()
        self.is_calibrating = True

    def cancel_calibration(self):
        self.is_calibrating = False
        self.start_time = None
        self.neck_samples.clear()
        self.shoulder_samples.clear()

    def process_frame(self, raw_neck: float, raw_shoulder: float) -> Tuple[bool, float, Optional[Tuple[float, float]]]:
        """
        Feeds a detected frame into calibration.
        Returns:
            (is_done: bool, progress: float [0.0 - 1.0], result: Optional[(baseline_neck, baseline_shoulder)])
        """
        if not self.is_calibrating or self.start_time is None:
            return False, 0.0, None

        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.duration_seconds)

        # Store sample
        self.neck_samples.append(raw_neck)
        self.shoulder_samples.append(raw_shoulder)

        if elapsed >= self.duration_seconds:
            self.is_calibrating = False
            if len(self.neck_samples) >= self.min_samples:
                # Remove top and bottom 10% outliers
                neck_arr = np.array(self.neck_samples)
                shoulder_arr = np.array(self.shoulder_samples)

                p10_n, p90_n = np.percentile(neck_arr, [10, 90])
                p10_s, p90_s = np.percentile(shoulder_arr, [10, 90])

                filtered_neck = neck_arr[(neck_arr >= p10_n) & (neck_arr <= p90_n)]
                filtered_shoulder = shoulder_arr[(shoulder_arr >= p10_s) & (shoulder_arr <= p90_s)]

                self.baseline_neck = float(np.mean(filtered_neck)) if len(filtered_neck) > 0 else float(np.mean(neck_arr))
                self.baseline_shoulder = float(np.mean(filtered_shoulder)) if len(filtered_shoulder) > 0 else float(np.mean(shoulder_arr))
                self.is_calibrated = True

                return True, 1.0, (self.baseline_neck, self.baseline_shoulder)
            else:
                # Not enough frames detected
                return True, 1.0, None

        return False, progress, None

    def get_effective_deviation(self, raw_neck: float, raw_shoulder: float) -> Tuple[float, float]:
        """
        Calculates deviation relative to personalized baseline.
        Uses a small leniency buffer so perfectly normal posture
        doesn't trigger false positives, while still being sensitive
        enough to detect actual slouching.
        """
        if not self.is_calibrated:
            return raw_neck, raw_shoulder

        # Neck flexion forward deviation (penalize if worse than baseline)
        # Small 1.5° buffer to absorb natural micro-movement noise
        neck_dev = max(0.0, raw_neck - self.baseline_neck - 1.5)
        
        # Shoulder tilt deviation from baseline
        # Small 1.0° buffer
        shoulder_dev = max(0.0, abs(raw_shoulder - self.baseline_shoulder) - 1.0)

        return neck_dev, shoulder_dev
