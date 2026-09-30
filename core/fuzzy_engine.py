"""
Mamdani Fuzzy Inference System (FIS) for SIERRA Ergonomics Risk Evaluation.
Based on Capstone Project specification.

Inputs:
  1. neck_angle (deg): Deviation of neck from ideal calibrated baseline.
     Terms: 'Ideal' [0, 0, 15], 'Cukup Menunduk' [10, 18, 26], 'Menunduk Tajam' [22, 35, 60]
  2. shoulder_angle (deg): Asymmetry/tilt of shoulder line.
     Terms: 'Simetris' [0, 0, 6], 'Miring Sedang' [4, 9, 14], 'Miring Berat' [11, 20, 40]
  3. duration (sec): Continuous duration in current posture.
     Terms: 'Singkat' [0, 0, 15], 'Sedang' [10, 25, 45], 'Lama' [35, 60, 120]

Output:
  risk_score: 0 to 100
  Terms:
    'Aman' (Safe): [0, 0, 35]
    'Waspada' (Warning): [25, 45, 65]
    'Bahaya' (Danger): [55, 80, 100]

Defuzzification: Center of Gravity (Centroid)
"""

import numpy as np
from typing import Dict, Tuple


def trimf(x: np.ndarray, params: list) -> np.ndarray:
    """Triangular membership function."""
    a, b, c = params
    y = np.zeros_like(x, dtype=float)
    if a != b:
        idx1 = np.logical_and(a <= x, x <= b)
        y[idx1] = (x[idx1] - a) / (b - a)
    else:
        y[x <= b] = 1.0

    if b != c:
        idx2 = np.logical_and(b <= x, x <= c)
        y[idx2] = (c - x[idx2]) / (c - b)
    else:
        y[x >= b] = 1.0

    y[x == b] = 1.0
    return np.clip(y, 0.0, 1.0)


def trapmf(x: np.ndarray, params: list) -> np.ndarray:
    """Trapezoidal membership function."""
    a, b, c, d = params
    y = np.zeros_like(x, dtype=float)
    # Left slope
    if a != b:
        idx1 = np.logical_and(a <= x, x < b)
        y[idx1] = (x[idx1] - a) / (b - a)
    else:
        y[x < b] = 1.0
    # Top plate
    idx2 = np.logical_and(b <= x, x <= c)
    y[idx2] = 1.0
    # Right slope
    if c != d:
        idx3 = np.logical_and(c < x, x <= d)
        y[idx3] = (d - x[idx3]) / (d - c)
    else:
        y[x > c] = 1.0

    return np.clip(y, 0.0, 1.0)


class MamdaniFuzzyEngine:
    def __init__(self):
        # Universe of Discourse
        self.u_neck = np.linspace(0, 60, 601)
        self.u_shoulder = np.linspace(0, 40, 401)
        self.u_duration = np.linspace(0, 120, 1201)
        self.u_risk = np.linspace(0, 100, 1001)

        # Output Membership Functions
        self.mf_risk_aman = trapmf(self.u_risk, [0, 0, 20, 35])
        self.mf_risk_waspada = trimf(self.u_risk, [25, 45, 65])
        self.mf_risk_bahaya = trapmf(self.u_risk, [55, 75, 100, 100])

    def fuzzify_neck(self, val: float) -> Dict[str, float]:
        val = np.clip(val, 0, 60)
        return {
            "ideal": float(trapmf(np.array([val]), [0, 0, 6, 12])[0]),
            "cukup": float(trimf(np.array([val]), [10, 16, 24])[0]),
            "tajam": float(trapmf(np.array([val]), [20, 26, 60, 60])[0]),
        }

    def fuzzify_shoulder(self, val: float) -> Dict[str, float]:
        val = np.clip(val, 0, 40)
        return {
            "simetris": float(trapmf(np.array([val]), [0, 0, 3, 6])[0]),
            "sedang": float(trimf(np.array([val]), [4, 9, 14])[0]),
            "berat": float(trapmf(np.array([val]), [11, 18, 40, 40])[0]),
        }

    def fuzzify_duration(self, val: float) -> Dict[str, float]:
        val = np.clip(val, 0, 120)
        return {
            "singkat": float(trapmf(np.array([val]), [0, 0, 10, 18])[0]),
            "sedang": float(trimf(np.array([val]), [12, 28, 45])[0]),
            "lama": float(trapmf(np.array([val]), [35, 55, 120, 120])[0]),
        }

    def evaluate(self, neck_deg: float, shoulder_deg: float, duration_sec: float) -> Tuple[float, str]:
        """
        Evaluates risk score via Mamdani FIS.
        Returns:
            (risk_score: float [0-100], risk_category: str ['Aman', 'Waspada', 'Bahaya'])
        """
        n_mf = self.fuzzify_neck(neck_deg)
        s_mf = self.fuzzify_shoulder(shoulder_deg)
        d_mf = self.fuzzify_duration(duration_sec)

        # Rule Base Mamdani (9 Comprehensive Clinical Rules)
        # R1: IF neck Ideal AND shoulder Simetris THEN Aman
        r1 = min(n_mf["ideal"], s_mf["simetris"])

        # R2: IF neck Ideal AND shoulder Sedang AND duration Singkat THEN Aman
        r2 = min(n_mf["ideal"], s_mf["sedang"], d_mf["singkat"])

        # R3: IF neck Ideal AND shoulder Sedang AND duration Lama THEN Waspada
        r3 = min(n_mf["ideal"], s_mf["sedang"], d_mf["lama"])

        # R4: IF neck Cukup AND duration Singkat THEN Aman
        r4 = min(n_mf["cukup"], d_mf["singkat"])

        # R5: IF neck Cukup AND duration Sedang THEN Waspada
        r5 = min(n_mf["cukup"], d_mf["sedang"])

        # R6: IF neck Cukup AND duration Lama THEN Bahaya
        r6 = min(n_mf["cukup"], d_mf["lama"])

        # R7: IF neck Tajam AND duration Singkat THEN Waspada
        r7 = min(n_mf["tajam"], d_mf["singkat"])

        # R8: IF neck Tajam AND (duration Sedang OR duration Lama) THEN Bahaya
        r8 = min(n_mf["tajam"], max(d_mf["sedang"], d_mf["lama"]))

        # R9: IF shoulder Berat AND (duration Sedang OR duration Lama) THEN Bahaya
        r9 = min(s_mf["berat"], max(d_mf["sedang"], d_mf["lama"]))

        # Output Aggregation (Mamdani MAX)
        rule_aman = max(r1, r2, r4)
        rule_waspada = max(r3, r5, r7)
        rule_bahaya = max(r6, r8, r9)

        # Aggregate fuzzy output clipping
        agg_risk = np.maximum(
            np.minimum(rule_aman, self.mf_risk_aman),
            np.maximum(
                np.minimum(rule_waspada, self.mf_risk_waspada),
                np.minimum(rule_bahaya, self.mf_risk_bahaya)
            )
        )

        # Defuzzification: Center of Gravity (Centroid)
        sum_agg = np.sum(agg_risk)
        if sum_agg == 0:
            crisp_score = 0.0
        else:
            crisp_score = float(np.sum(agg_risk * self.u_risk) / sum_agg)

        # Determine category
        if crisp_score < 30.0:
            category = "Aman"
        elif crisp_score < 65.0:
            category = "Waspada"
        else:
            category = "Bahaya"

        return round(crisp_score, 1), category
