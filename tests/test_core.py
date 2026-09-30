import os
import time
import unittest
import numpy as np

from core.fuzzy_engine import MamdaniFuzzyEngine
from core.calibrator import BaselineCalibrator
from database.db_manager import DatabaseManager


class TestMamdaniFuzzyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MamdaniFuzzyEngine()

    def test_ideal_posture_is_safe(self):
        """Test ideal posture produces risk category 'Aman' with low score."""
        score, category = self.engine.evaluate(neck_deg=5.0, shoulder_deg=1.0, duration_sec=5.0)
        self.assertEqual(category, "Aman")
        self.assertLess(score, 30.0)

    def test_moderate_flexion_is_warning(self):
        """Test moderate neck flexion after moderate duration triggers 'Waspada'."""
        score, category = self.engine.evaluate(neck_deg=18.0, shoulder_deg=2.0, duration_sec=25.0)
        self.assertIn(category, ["Waspada", "Bahaya"])
        self.assertGreater(score, 25.0)

    def test_severe_posture_is_danger(self):
        """Test sharp forward head tilt for prolonged duration triggers 'Bahaya'."""
        score, category = self.engine.evaluate(neck_deg=35.0, shoulder_deg=8.0, duration_sec=60.0)
        self.assertEqual(category, "Bahaya")
        self.assertGreaterEqual(score, 60.0)

    def test_centroid_defuzzification_bounds(self):
        """Test that defuzzification output is strictly bounded [0, 100]."""
        for n in [0.0, 15.0, 30.0, 50.0]:
            for s in [0.0, 10.0, 25.0]:
                for d in [0.0, 20.0, 60.0, 120.0]:
                    score, cat = self.engine.evaluate(n, s, d)
                    self.assertGreaterEqual(score, 0.0)
                    self.assertLessEqual(score, 100.0)
                    self.assertIn(cat, ["Aman", "Waspada", "Bahaya"])


class TestBaselineCalibrator(unittest.TestCase):
    def test_calibration_and_deviation(self):
        calibrator = BaselineCalibrator(duration_seconds=0.05, min_samples=5)
        calibrator.start_calibration()

        # Feed samples of typical sitting neck posture (~14 deg)
        is_done = False
        for _ in range(25):
            done, prog, baseline = calibrator.process_frame(raw_neck=14.0, raw_shoulder=1.0)
            if done:
                is_done = True
                break
            time.sleep(0.005)

        self.assertTrue(is_done)
        self.assertTrue(calibrator.is_calibrated)
        self.assertAlmostEqual(calibrator.baseline_neck, 14.0, places=1)
        self.assertAlmostEqual(calibrator.baseline_shoulder, 1.0, places=1)

        # When sitting at baseline, effective deviation should be ~0
        dev_n, dev_s = calibrator.get_effective_deviation(raw_neck=14.0, raw_shoulder=1.0)
        self.assertAlmostEqual(dev_n, 0.0, places=1)
        self.assertAlmostEqual(dev_s, 0.0, places=1)

        # When slouching forward to 28 deg, effective deviation is 14 deg - 1.5 deg leniency = 12.5 deg
        dev_n_slouch, _ = calibrator.get_effective_deviation(raw_neck=28.0, raw_shoulder=1.0)
        self.assertAlmostEqual(dev_n_slouch, 12.5, places=1)


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_sierra.db"
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass
        self.db = DatabaseManager(self.test_db)

    def tearDown(self):
        del self.db
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass

    def test_session_lifecycle(self):
        sess_id = self.db.start_session()
        self.assertIsNotNone(sess_id)

        # Update session metrics
        self.db.update_session(
            session_id=sess_id,
            duration_sec=120,
            safe_sec=100,
            warning_sec=15,
            danger_sec=5,
            avg_neck=12.5,
            avg_shoulder=2.1
        )

        sessions = self.db.get_recent_sessions(limit=5)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["duration_seconds"], 120)
        self.assertGreater(sessions[0]["posture_score"], 80.0)

        stats = self.db.get_aggregate_stats()
        self.assertEqual(stats["total_sessions"], 1)
        self.assertEqual(stats["total_duration"], 120)

    def test_calibration_storage(self):
        self.db.save_calibration(13.5, 1.2)
        n, s = self.db.get_calibration()
        self.assertAlmostEqual(n, 13.5, places=1)
        self.assertAlmostEqual(s, 1.2, places=1)


class TestPrivacyResourceManager(unittest.TestCase):
    def test_ephemeral_frame_dropping_and_metrics(self):
        from core.privacy_resource_manager import PrivacyResourceManager
        mgr = PrivacyResourceManager(memory_cleanup_interval=5)
        
        # Test dropping dummy frame
        dummy = np.zeros((240, 320, 3), dtype=np.uint8)
        mgr.drop_frame(dummy)
        
        metrics = mgr.get_resource_metrics()
        self.assertEqual(metrics["frames_dropped"], 1)
        self.assertGreater(metrics["ram_mb"], 0.0)
        self.assertTrue(metrics["cpu_only"])
        self.assertIn("Zero-Retention", metrics["privacy_status"])
        
        # Test explicit clean memory
        mgr.clean_memory()


if __name__ == "__main__":
    unittest.main()
