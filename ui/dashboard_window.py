import sys
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QSlider, QFrame, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QMessageBox, QComboBox, QCheckBox, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QBrush, QPen, QPixmap

class InteractiveCameraLabel(QLabel):
    mouse_moved = pyqtSignal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_angles(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_angles(event.pos())

    def _update_angles(self, pos: QPoint):
        w = float(self.width())
        h = float(self.height())
        if w == 0 or h == 0:
            return
        # map x from 0..w to -40..40 (shoulder tilt) for easier movement
        shoulder = ((pos.x() / w) - 0.5) * -80.0
        # map y from 0..h to -10..70 (neck flexion)
        neck = (pos.y() / h) * 80.0 - 10.0
        self.mouse_moved.emit(neck, shoulder, pos.x() / w, pos.y() / h)

from .components.gauge_widget import CircularRiskGauge
from .overlay_window import DesktopOverlay
from core.camera_worker import CameraWorker
from database.db_manager import DatabaseManager
from assets.icons import get_svg_icon


class UserGuideDialog(QDialog):
    """Clean, modern user guide modal dialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Panduan Penggunaan — SIERRA")
        self.resize(700, 560)
        self.setMinimumSize(620, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #060b13;
                color: #e2e8f0;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #e2e8f0;
            }
            QFrame.guide-step {
                background-color: #0d1726;
                border: 1px solid #134e4a;
                border-radius: 12px;
                padding: 14px;
            }
            QPushButton {
                background-color: #0f766e;
                color: #ffffff;
                border: 1px solid #14b8a6;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0d9488;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_icon("info", "#14b8a6", 28).pixmap(28, 28))
        title_lbl = QLabel("PANDUAN PENGGUNAAN SISTEM SIERRA")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_lbl.setStyleSheet("color: #2dd4bf; letter-spacing: 0.5px;")
        title_box.addWidget(icon_lbl)
        title_box.addWidget(title_lbl)
        title_box.addStretch()
        layout.addLayout(title_box)

        sub_lbl = QLabel(
            "Sistem Intervensi Ergonomi Real-Time untuk menjaga postur tubuh selama gaming "
            "tanpa menghalangi kursor mouse atau mengganggu konsentrasi permainan."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 6px;")
        layout.addWidget(sub_lbl)

        # Scroll Area for steps
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(12)
        c_layout.setContentsMargins(0, 0, 0, 0)

        steps = [
            ("Langkah 1: Kalibrasi Postur Ideal",
             "Saat duduk tegak dan nyaman di kursi gaming Anda, klik tombol 'Kalibrasi Baseline (10 Detik)' "
             "pada tab Live Monitor. Sistem akan merekam anatomi unik dan tinggi kursi Anda sehingga tidak ada false alarm."),
            
            ("Langkah 2: Menjalankan Game Favorit",
             "Buka game Anda dalam mode Fullscreen atau Borderless Windowed. Jendela Desktop Overlay SIERRA akan "
             "melayang transparan di atas game dengan teknologi True Click-Through, sehingga kursor mouse Anda bebas 100%."),
            
            ("Langkah 3: Intervensi Visual Halus (Adaptive Dimming)",
             "Jika Anda menunduk atau membungkuk terlalu lama, bagian sudut/tepi monitor akan meredup perlahan "
             "(vignette dimming) untuk mengingatkan Anda memperbaiki postur secara bawah sadar tanpa menutup tampilan tengah game."),
            
            ("Langkah 4: Pemulihan Otomatis",
             "Begitu Anda menegakkan kembali leher dan bahu, layar monitor akan langsung cerah dan jernih kembali secara otomatis."),
             
            ("Mode Simulasi (Demo Tanpa Kamera)",
             "Jika Anda ingin menguji atau mendemonstrasikan sistem tanpa webcam fisik, cukup pilih opsi 'Mode Simulasi' "
             "pada dropdown Sumber Data di pojok kanan atas dashboard.")
        ]

        for num_title, desc in steps:
            card = QFrame()
            card.setProperty("class", "guide-step")
            c_v = QVBoxLayout(card)
            c_v.setContentsMargins(14, 10, 14, 10)
            
            t = QLabel(num_title)
            t.setFont(QFont("Segoe UI", 11, QFont.Bold))
            t.setStyleSheet("color: #5eead4;")
            
            d = QLabel(desc)
            d.setWordWrap(True)
            d.setStyleSheet("color: #cbd5e1; font-size: 11.5px; line-height: 1.4;")
            
            c_v.addWidget(t)
            c_v.addWidget(d)
            c_layout.addWidget(card)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Close button
        btn_close = QPushButton("Tutup Panduan")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIERRA — Sistem Intervensi Ergonomi Real-Time")
        self.resize(1040, 720)
        self.setMinimumSize(960, 650)

        # Database and state
        self.db = DatabaseManager()
        self.session_id = None
        self.session_start_time = None
        self.safe_seconds = 0
        self.warning_seconds = 0
        self.danger_seconds = 0
        self.total_seconds = 0
        self.neck_sum = 0.0
        self.shoulder_sum = 0.0
        self.sample_count = 0

        # Overlay window
        self.overlay = DesktopOverlay()
        settings = self.db.get_settings()
        self.overlay.configure_intervention(
            settings.get("max_dimming_opacity", 0.65),
            settings.get("dimming_color", "#070c14")
        )
        self.overlay.show()

        # Camera worker thread
        self.worker = CameraWorker(camera_index=0)
        neck_base, shoulder_base = self.db.get_calibration()
        self.worker.set_baseline(neck_base, shoulder_base)

        # Connect worker signals
        self.worker.metrics_updated.connect(self._on_metrics_updated)
        self.worker.calibration_updated.connect(self._on_calibration_updated)
        self.worker.status_updated.connect(self._on_status_updated)
        self.worker.fps_updated.connect(self._on_fps_updated)
        self.worker.resource_metrics_updated.connect(self._on_resource_metrics_updated)
        self.worker.frame_ready.connect(self._on_frame_ready)

        # Session update timer (every 1 second)
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self._on_session_tick)

        # Setup Styles & UI Layout
        self._apply_theme()
        self._init_ui()

        # Start Camera and Auto-start initial session
        self.worker.start()
        self._start_new_session()

    def _apply_theme(self):
        """Applies elegant Dark Tosca / Ephemeral styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #060b13;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #134e4a;
                border-radius: 14px;
                background-color: #0d1726;
                padding: 12px;
            }
            QTabBar::tab {
                background: #0a111c;
                color: #94a3b8;
                padding: 10px 14px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid #112238;
                border-bottom: none;
                min-height: 20px;
            }
            QTabBar::tab:selected {
                background: #0d1726;
                color: #2dd4bf;
                border: 1px solid #134e4a;
                border-bottom: 2px solid #14b8a6;
            }
            QFrame.card {
                background-color: #0b1320;
                border: 1px solid #134e4a;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton {
                background-color: #0f2338;
                color: #f8fafc;
                border: 1px solid #1e3a5f;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 12.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #153350;
                border-color: #14b8a6;
                color: #2dd4bf;
            }
            QPushButton.primary {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f766e, stop:1 #0d9488);
                border: 1px solid #14b8a6;
                color: #ffffff;
            }
            QPushButton.primary:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #115e59, stop:1 #0f766e);
            }
            QProgressBar {
                border: 1px solid #134e4a;
                border-radius: 6px;
                text-align: center;
                background-color: #070d18;
                color: #f8fafc;
                font-size: 11px;
                font-weight: bold;
                height: 14px;
            }
            QProgressBar::chunk {
                background-color: #14b8a6;
                border-radius: 5px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #0f2338;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #14b8a6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2dd4bf;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QComboBox {
                background-color: #0b1526;
                color: #f8fafc;
                border: 1px solid #14b8a6;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #070e1a;
                color: #e2e8f0;
                selection-background-color: #0f766e;
                selection-color: #ffffff;
                border: 1px solid #14b8a6;
                border-radius: 6px;
                outline: none;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #11283d;
                color: #2dd4bf;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #0b1526;
                border: 1px solid #14b8a6;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #14b8a6;
            }
            QTableWidget {
                background-color: #070d18;
                border: 1px solid #134e4a;
                gridline-color: #0f2338;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #0f2338;
                color: #2dd4bf;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableCornerButton::section {
                background-color: #0f2338;
                border: none;
            }
            QScrollBar:vertical {
                background: #060b13;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #0f2338;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #060b13;
                height: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #0f2338;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QMessageBox {
                background-color: #060b13;
            }
            QMessageBox QLabel {
                color: #e2e8f0;
            }
            QMessageBox QPushButton {
                background-color: #0f766e;
                color: #ffffff;
                border: 1px solid #14b8a6;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QMessageBox QPushButton:hover {
                background-color: #0d9488;
            }
        """)

    def _init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # Header Bar
        header = self._create_header()
        main_layout.addWidget(header)

        # Tab Navigation
        tabs = QTabWidget()
        tabs.addTab(self._create_monitor_tab(), "Live Monitor & Intervensi")
        tabs.addTab(self._create_analytics_tab(), "Analitik Sesi Lokal")
        tabs.addTab(self._create_settings_tab(), "Pengaturan & Privasi")
        main_layout.addWidget(tabs)

        # Footer Status Bar
        footer = self._create_footer()
        main_layout.addWidget(footer)

        self.setCentralWidget(main_widget)

    def _create_header(self) -> QWidget:
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(4, 2, 4, 6)
        h_layout.setSpacing(14)

        # App Logo & Title
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("SIERRA")
        title.setFont(QFont("Segoe UI", 19, QFont.Bold))
        title.setStyleSheet("color: #2dd4bf; letter-spacing: 1.5px;")

        subtitle = QLabel("Sistem Intervensi Ergonomi Real-Time & Risiko Aktivitas")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #94a3b8;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        h_layout.addLayout(title_box)

        h_layout.addStretch()

        # Guide Button
        btn_guide = QPushButton("Panduan")
        btn_guide.setIcon(get_svg_icon("info", "#2dd4bf", 18))
        btn_guide.clicked.connect(self._open_guide)
        h_layout.addWidget(btn_guide)

        # Data Source Mode Selection (Webcam vs Simulation)
        mode_box = QHBoxLayout()
        mode_box.setSpacing(8)
        mode_lbl = QLabel("Sumber Data:")
        mode_lbl.setStyleSheet("color: #94a3b8; font-size: 11.5px; font-weight: bold;")

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Kamera Fisik (Webcam)",
            "Simulasi Otomatis (Berganti Otomatis)",
            "Simulasi Manual (Geser Kursor)"
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_source_mode_changed)

        mode_box.addWidget(mode_lbl)
        mode_box.addWidget(self.mode_combo)
        h_layout.addLayout(mode_box)

        # Privacy Badge (Vector Shield, No Emoji)
        privacy_badge = QFrame()
        privacy_badge.setStyleSheet("""
            background-color: #064e3b;
            border: 1px solid #059669;
            border-radius: 16px;
            padding: 4px 12px;
        """)
        pb_layout = QHBoxLayout(privacy_badge)
        pb_layout.setContentsMargins(6, 4, 8, 4)
        pb_layout.setSpacing(6)

        shield_icon = QLabel()
        shield_icon.setPixmap(get_svg_icon("shield", "#6ee7b7", 16).pixmap(16, 16))
        pb_text = QLabel("Zero-Retention Active")
        pb_text.setStyleSheet("color: #6ee7b7; font-size: 11px; font-weight: bold; border: none; background: transparent;")

        pb_layout.addWidget(shield_icon)
        pb_layout.addWidget(pb_text)
        h_layout.addWidget(privacy_badge)

        return header

    def _open_guide(self):
        dlg = UserGuideDialog(self)
        dlg.exec_()

    def _on_source_mode_changed(self, idx: int):
        if idx == 0:
            self.worker.set_simulation_mode(False)
        elif idx == 1:
            self.worker.set_simulation_mode(True, "auto")
        elif idx == 2:
            self.worker.set_simulation_mode(True, "manual")

    def _create_monitor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(8, 8, 8, 8)

        # Left Column: Posture Avatar & Kinematics
        left_card = QFrame()
        left_card.setProperty("class", "card")
        l_layout = QVBoxLayout(left_card)
        l_layout.setSpacing(12)

        l_title = QLabel("KAMERA REAL-TIME (AR HUD)")
        l_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        l_title.setStyleSheet("color: #2dd4bf; letter-spacing: 0.5px;")
        l_layout.addWidget(l_title)

        self.camera_feed_label = InteractiveCameraLabel()
        self.camera_feed_label.setAlignment(Qt.AlignCenter)
        self.camera_feed_label.setScaledContents(False)
        self.camera_feed_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_feed_label.setMinimumSize(480, 270)
        self.camera_feed_label.setStyleSheet("background-color: #070d18; border: 1px solid #134e4a; border-radius: 8px;")
        self.camera_feed_label.mouse_moved.connect(self.worker.set_manual_angles)
        l_layout.addWidget(self.camera_feed_label, alignment=Qt.AlignCenter)

        # Kinematic metrics row
        metrics_box = QHBoxLayout()
        metrics_box.setSpacing(12)

        self.lbl_neck = QLabel("Deviasi Leher: 0.0°")
        self.lbl_neck.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lbl_neck.setStyleSheet("color: #f0fdfa; background: #070d18; border: 1px solid #134e4a; border-radius: 8px; padding: 6px 12px;")

        self.lbl_shoulder = QLabel("Deviasi Bahu: 0.0°")
        self.lbl_shoulder.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lbl_shoulder.setStyleSheet("color: #f0fdfa; background: #070d18; border: 1px solid #134e4a; border-radius: 8px; padding: 6px 12px;")

        metrics_box.addWidget(self.lbl_neck)
        metrics_box.addWidget(self.lbl_shoulder)
        l_layout.addLayout(metrics_box)

        # Calibration Box
        calib_box = QVBoxLayout()
        calib_box.setSpacing(6)

        self.calib_status_lbl = QLabel("Baseline Terkalibrasi: Leher 10.0°, Bahu 0.0°")
        self.calib_status_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        calib_box.addWidget(self.calib_status_lbl)

        self.calib_btn = QPushButton("Kalibrasi Baseline (10 Detik)")
        self.calib_btn.setIcon(get_svg_icon("target", "#ffffff", 18))
        self.calib_btn.setProperty("class", "primary")
        self.calib_btn.clicked.connect(self._trigger_calibration)
        calib_box.addWidget(self.calib_btn)

        self.calib_progress = QProgressBar()
        self.calib_progress.setValue(0)
        self.calib_progress.setVisible(False)
        calib_box.addWidget(self.calib_progress)

        l_layout.addLayout(calib_box)
        layout.addWidget(left_card, 6)

        # Right Column: Risk Gauge, Duration, Intervention Controls
        right_card = QFrame()
        right_card.setProperty("class", "card")
        r_layout = QVBoxLayout(right_card)
        r_layout.setSpacing(12)

        r_title = QLabel("EVALUASI RISIKO FUZZY (MAMDANI)")
        r_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        r_title.setStyleSheet("color: #2dd4bf; letter-spacing: 0.5px;")
        r_layout.addWidget(r_title)

        # Circular Gauge in center
        self.gauge_widget = CircularRiskGauge()
        r_layout.addWidget(self.gauge_widget, alignment=Qt.AlignCenter)

        # Posture Duration & Status Card
        self.lbl_duration = QLabel("Postur Tubuh Ergonomis")
        self.lbl_duration.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lbl_duration.setAlignment(Qt.AlignCenter)
        self.lbl_duration.setStyleSheet("color: #34d399; background: #070d18; border: 1px solid #134e4a; border-radius: 8px; padding: 6px;")
        r_layout.addWidget(self.lbl_duration)

        # Session Metrics Grid
        sess_box = QHBoxLayout()
        sess_box.setSpacing(10)
        self.lbl_safe_time = QLabel("Aman: 0m 0s")
        self.lbl_safe_time.setAlignment(Qt.AlignCenter)
        self.lbl_safe_time.setStyleSheet("color: #14b8a6; font-weight: bold; background: #07171d; border-radius: 6px; padding: 6px;")

        self.lbl_warn_time = QLabel("Waspada: 0m 0s")
        self.lbl_warn_time.setAlignment(Qt.AlignCenter)
        self.lbl_warn_time.setStyleSheet("color: #f59e0b; font-weight: bold; background: #1c1508; border-radius: 6px; padding: 6px;")

        self.lbl_danger_time = QLabel("Bahaya: 0m 0s")
        self.lbl_danger_time.setAlignment(Qt.AlignCenter)
        self.lbl_danger_time.setStyleSheet("color: #f43f5e; font-weight: bold; background: #1c0b11; border-radius: 6px; padding: 6px;")

        sess_box.addWidget(self.lbl_safe_time)
        sess_box.addWidget(self.lbl_warn_time)
        sess_box.addWidget(self.lbl_danger_time)
        r_layout.addLayout(sess_box)

        # Overlay Controls
        r_layout.addSpacing(4)
        overlay_btn_box = QHBoxLayout()
        overlay_btn_box.setSpacing(10)

        self.overlay_toggle_btn = QPushButton("Sembunyikan Overlay")
        self.overlay_toggle_btn.setIcon(get_svg_icon("eye_off", "#cbd5e1", 16))
        self.overlay_toggle_btn.clicked.connect(self._toggle_overlay)
        overlay_btn_box.addWidget(self.overlay_toggle_btn)

        self.btn_reset_session = QPushButton("Sesi Baru")
        self.btn_reset_session.setIcon(get_svg_icon("refresh", "#cbd5e1", 16))
        self.btn_reset_session.clicked.connect(self._start_new_session)
        overlay_btn_box.addWidget(self.btn_reset_session)
        r_layout.addLayout(overlay_btn_box)

        layout.addWidget(right_card, 4)
        return tab

    def _create_analytics_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 8, 8, 8)

        # Top Aggregate Cards
        stat_cards = QHBoxLayout()
        stat_cards.setSpacing(12)
        self.lbl_agg_sessions = self._make_stat_card("Total Sesi", "0")
        self.lbl_agg_duration = self._make_stat_card("Total Waktu", "0 Menit")
        self.lbl_agg_score = self._make_stat_card("Rata-rata Skor", "100.0%")
        self.lbl_agg_danger = self._make_stat_card("Waktu Bahaya", "0 Menit")

        stat_cards.addWidget(self.lbl_agg_sessions)
        stat_cards.addWidget(self.lbl_agg_duration)
        stat_cards.addWidget(self.lbl_agg_score)
        stat_cards.addWidget(self.lbl_agg_danger)
        layout.addLayout(stat_cards)

        # Table of Recent Sessions
        table_lbl = QLabel("Riwayat Sesi Gaming Terakhir (Tersimpan Lokal)")
        table_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        table_lbl.setStyleSheet("color: #2dd4bf;")
        layout.addWidget(table_lbl)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Waktu Mulai", "Durasi", "Skor Postur", "Aman", "Waspada", "Bahaya"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)
        
        btn_hapus = QPushButton("Hapus Sesi Terpilih")
        btn_hapus.setProperty("class", "primary")
        btn_hapus.clicked.connect(self._delete_selected_session)
        layout.addWidget(btn_hapus, alignment=Qt.AlignRight)

        self._refresh_analytics()
        return tab

    def _make_stat_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        
        val_lbl = QLabel(value)
        val_lbl.setObjectName("val")
        val_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        val_lbl.setStyleSheet("color: #2dd4bf;")

        v.addWidget(t_lbl)
        v.addWidget(val_lbl)
        return card

    def _create_settings_tab(self) -> QWidget:
        main_tab = QWidget()
        h_layout = QHBoxLayout(main_tab)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        tab = QWidget()
        tab.setMaximumWidth(800)
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignTop)

        h_layout.addWidget(tab)
        h_layout.addStretch()

        # Section: Overlay Settings
        ov_card = QFrame()
        ov_card.setProperty("class", "card")
        ov_layout = QVBoxLayout(ov_card)
        ov_layout.setSpacing(10)

        ov_title = QLabel("Kustomisasi Intervensi Visual (Adaptive Edge Dimming)")
        ov_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        ov_title.setStyleSheet("color: #2dd4bf;")
        ov_layout.addWidget(ov_title)

        # Slider Max Opacity
        self.lbl_slider_val = QLabel(f"Opasitas Maksimal Peredupan: {int(self.overlay.max_opacity * 100)}%")
        self.lbl_slider_val.setStyleSheet("color: #cbd5e1;")
        ov_layout.addWidget(self.lbl_slider_val)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 95)
        self.opacity_slider.setValue(int(self.overlay.max_opacity * 100))
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        ov_layout.addWidget(self.opacity_slider)

        # Dimming Color Scheme Selector
        color_row = QHBoxLayout()
        color_lbl = QLabel("Skema Warna Dimming:")
        color_lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.color_combo = QComboBox()
        self.color_combo.addItems([
            "Dark Obsidian (#070c14)",
            "Stealth Charcoal (#18181b)",
            "Crimson Vignette (#450a0a)"
        ])
        self.color_combo.currentIndexChanged.connect(self._on_color_changed)
        color_row.addWidget(color_lbl)
        color_row.addWidget(self.color_combo)
        ov_layout.addLayout(color_row)

        layout.addWidget(ov_card)

        # Section: Game-Mode Auto Detection
        gm_card = QFrame()
        gm_card.setProperty("class", "card")
        gm_layout = QVBoxLayout(gm_card)
        gm_layout.setSpacing(6)

        self.cb_game_mode = QCheckBox("Aktifkan Game-Mode Auto-Detect (Hemat CPU saat Fullscreen Game)")
        self.cb_game_mode.setChecked(True)
        self.cb_game_mode.toggled.connect(self._on_game_mode_toggled)
        self.cb_game_mode.setStyleSheet("font-weight: bold; color: #f0fdfa;")
        gm_layout.addWidget(self.cb_game_mode)

        gm_desc = QLabel(
            "Secara otomatis mendeteksi ketika game AAA atau aplikasi layar penuh berjalan, "
            "lalu menyesuaikan alokasi thread pelacakan agar performa GPU/FPS game tetap maksimal."
        )
        gm_desc.setWordWrap(True)
        gm_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        gm_layout.addWidget(gm_desc)

        layout.addWidget(gm_card)

        # Section: Privacy & Resource Optimization (Azka Hasyyati Bayan)
        pr_card = QFrame()
        pr_card.setProperty("class", "card")
        pr_layout = QVBoxLayout(pr_card)
        pr_layout.setSpacing(10)

        pr_title = QLabel("Keamanan Privasi & Efisiensi Sumber Daya (Privacy by Design)")
        pr_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        pr_title.setStyleSheet("color: #2dd4bf;")
        pr_layout.addWidget(pr_title)

        pr_grid = QHBoxLayout()
        self.lbl_card_ram = QLabel("RAM: 0.0 MB")
        self.lbl_card_ram.setStyleSheet("color: #f8fafc; font-weight: bold; background: #070d18; border-radius: 4px; border: 1px solid #1e293b; padding: 4px 10px;")
        self.lbl_card_cpu = QLabel("CPU: 0.0%")
        self.lbl_card_cpu.setStyleSheet("color: #f8fafc; font-weight: bold; background: #070d18; border-radius: 4px; border: 1px solid #1e293b; padding: 4px 10px;")
        self.lbl_card_dropped = QLabel("Frame Dihapus: 0")
        self.lbl_card_dropped.setStyleSheet("color: #5eead4; font-weight: bold; background: #070d18; border-radius: 4px; border: 1px solid #1e293b; padding: 4px 10px;")

        pr_grid.addWidget(self.lbl_card_ram)
        pr_grid.addWidget(self.lbl_card_cpu)
        pr_grid.addWidget(self.lbl_card_dropped)
        pr_grid.addStretch()
        pr_layout.addLayout(pr_grid)

        pr_desc = QLabel(
            "• Algoritma Ephemeral Frame Dropper: Frame video mentah segera dihapus dari RAM begitu koordinat diekstrak.\n"
            "• 0 Byte Media Disimpan: Tidak ada video/foto yang direkam, disimpan ke disk, atau dikirim ke internet.\n"
            "• Eksekusi CPU-Only: Backend GPU dinonaktifkan pada CV agar 100% daya GPU dialokasikan untuk game.\n"
            "• Prioritas Gamer-Friendly: Windows process priority diatur ke Below Normal agar game tidak pernah lag."
        )
        pr_desc.setStyleSheet("color: #99f6e4; font-size: 11px; line-height: 1.6;")
        pr_layout.addWidget(pr_desc)

        pr_btn_layout = QHBoxLayout()
        btn_force_gc = QPushButton("Bersihkan Cache RAM Manual (Force GC)")
        btn_force_gc.setIcon(get_svg_icon("clean", "#ffffff", 16))
        btn_force_gc.clicked.connect(self._manual_clean_memory)
        pr_btn_layout.addWidget(btn_force_gc)
        pr_btn_layout.addStretch()
        pr_layout.addLayout(pr_btn_layout)

        layout.addWidget(pr_card)

        layout.addStretch()
        return main_tab

    def _create_footer(self) -> QWidget:
        footer = QWidget()
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(4, 4, 4, 2)

        self.lbl_status = QLabel("Status: Inisialisasi SIERRA...")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")

        self.lbl_ram_telemetry = QLabel("RAM: 0 MB")
        self.lbl_ram_telemetry.setStyleSheet("color: #2dd4bf; font-size: 11px; font-weight: bold;")

        self.lbl_cpu_telemetry = QLabel("CPU: 0%")
        self.lbl_cpu_telemetry.setStyleSheet("color: #2dd4bf; font-size: 11px; font-weight: bold;")

        self.lbl_fps = QLabel("FPS: 0.0")
        self.lbl_fps.setStyleSheet("color: #2dd4bf; font-weight: bold; font-size: 11px;")

        f_layout.addWidget(self.lbl_status)
        f_layout.addStretch()
        f_layout.addWidget(self.lbl_ram_telemetry)
        f_layout.addSpacing(14)
        f_layout.addWidget(self.lbl_cpu_telemetry)
        f_layout.addSpacing(14)
        f_layout.addWidget(self.lbl_fps)

        return footer

    def _on_resource_metrics_updated(self, metrics: dict):
        ram = metrics.get("ram_mb", 0.0)
        cpu = metrics.get("cpu_percent", 0.0)
        dropped = metrics.get("frames_dropped", 0)

        self.lbl_ram_telemetry.setText(f"RAM: {ram:.1f} MB")
        self.lbl_cpu_telemetry.setText(f"CPU: {cpu:.1f}%")

        if hasattr(self, "lbl_card_ram"):
            self.lbl_card_ram.setText(f"RAM: {ram:.1f} MB (Ringan)")
            self.lbl_card_cpu.setText(f"CPU: {cpu:.1f}% (CPU-Only)")
            self.lbl_card_dropped.setText(f"Frame Dihapus: {dropped:,} frame")

    def _manual_clean_memory(self):
        self.worker.privacy_manager.clean_memory()
        QMessageBox.information(
            self, "Pembersihan Memori",
            "Garbage Collection berhasil dijalankan.\nCache RAM telah dibersihkan dan dikompaksi."
        )

    # --- Callbacks & Signal Handlers ---
    def _on_metrics_updated(self, data: dict):
        is_detected = data.get("skeleton") is not None
        eff_neck = data.get("effective_neck", 0.0)
        eff_sh = data.get("effective_shoulder", 0.0)
        risk_score = data.get("risk_score", 0.0)
        risk_cat = data.get("risk_category", "Aman")
        duration = data.get("duration_sec", 0.0)

        # Update Gauge
        self.gauge_widget.set_risk(risk_score, risk_cat)

        # Update Labels
        self.lbl_neck.setText(f"Deviasi Leher: {eff_neck:.1f}°")
        self.lbl_shoulder.setText(f"Deviasi Bahu: {eff_sh:.1f}°")

        if duration > 1.0 and risk_cat in ["Waspada", "Bahaya"]:
            self.lbl_duration.setText(f"Durasi Posisi Berisiko: {int(duration)} detik")
            self.lbl_duration.setStyleSheet("color: #f43f5e; font-weight: bold; background: #1c0b11; border: 1px solid #e11d48; border-radius: 8px; padding: 6px;")
        else:
            self.lbl_duration.setText("Postur Tubuh Ergonomis")
            self.lbl_duration.setStyleSheet("color: #34d399; font-weight: bold; background: #070d18; border: 1px solid #134e4a; border-radius: 8px; padding: 6px;")

        # Update Overlay Dimming
        self.overlay.update_risk(risk_score, risk_cat)

        # Accumulate metrics for session
        if is_detected:
            self.neck_sum += eff_neck
            self.shoulder_sum += eff_sh
            self.sample_count += 1

            if risk_cat == "Aman":
                self.safe_seconds += 1
            elif risk_cat == "Waspada":
                self.warning_seconds += 1
            else:
                self.danger_seconds += 1

    def _on_frame_ready(self, q_img):
        pixmap = QPixmap.fromImage(q_img)
        if not pixmap.isNull():
            self.camera_feed_label.setPixmap(pixmap.scaled(self.camera_feed_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _delete_selected_session(self):
        row = self.history_table.currentRow()
        if row >= 0:
            item = self.history_table.item(row, 0)
            if item:
                session_id = item.data(Qt.UserRole)
                reply = QMessageBox.question(self, "Hapus Sesi", "Apakah Anda yakin ingin menghapus sesi ini dari riwayat?", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.db.delete_session(session_id)
                    self._refresh_analytics()

    def _on_calibration_updated(self, calib_data: dict):
        prog = calib_data.get("progress", 0.0)
        is_done = calib_data.get("is_done", False)
        baseline = calib_data.get("baseline")

        self.calib_progress.setValue(int(prog * 100))

        if is_done:
            self.calib_progress.setVisible(False)
            self.calib_btn.setEnabled(True)
            self.calib_btn.setText("Kalibrasi Baseline (10 Detik)")

            if baseline:
                neck_b, sh_b = baseline
                self.db.save_calibration(neck_b, sh_b)
                self.calib_status_lbl.setText(f"Baseline Disimpan: Leher {neck_b:.1f}°, Bahu {sh_b:.1f}°")
                QMessageBox.information(
                    self, "Kalibrasi Berhasil",
                    f"Postur ideal Anda telah dipelajari!\n\nBaseline Leher: {neck_b:.1f}°\nBaseline Bahu: {sh_b:.1f}°\n\nSistem kini terkalibrasi khusus untuk tubuh dan meja gaming Anda."
                )
            else:
                self.calib_status_lbl.setText("Kalibrasi Gagal: Kerangka tidak terdeteksi secara konsisten.")

    def _trigger_calibration(self):
        self.calib_btn.setEnabled(False)
        self.calib_btn.setText("Mengukur postur ideal... (10 Detik)")
        self.calib_progress.setValue(0)
        self.calib_progress.setVisible(True)
        self.calib_status_lbl.setText("Harap duduk tegak dan nyaman menghadap layar...")
        self.worker.start_calibration()

    def _on_session_tick(self):
        if self.session_id is not None:
            self.total_seconds += 1
            avg_n = self.neck_sum / max(1, self.sample_count)
            avg_s = self.shoulder_sum / max(1, self.sample_count)

            # Update live indicators
            self.lbl_safe_time.setText(f"Aman: {self.safe_seconds // 60}m {self.safe_seconds % 60}s")
            self.lbl_warn_time.setText(f"Waspada: {self.warning_seconds // 60}m {self.warning_seconds % 60}s")
            self.lbl_danger_time.setText(f"Bahaya: {self.danger_seconds // 60}m {self.danger_seconds % 60}s")

            # Persist to database periodically (every 5 seconds)
            if self.total_seconds % 5 == 0:
                self.db.update_session(
                    self.session_id, self.total_seconds,
                    self.safe_seconds, self.warning_seconds, self.danger_seconds,
                    avg_n, avg_s
                )

    def _start_new_session(self):
        if self.session_id is not None:
            avg_n = self.neck_sum / max(1, self.sample_count)
            avg_s = self.shoulder_sum / max(1, self.sample_count)
            self.db.update_session(
                self.session_id, self.total_seconds,
                self.safe_seconds, self.warning_seconds, self.danger_seconds,
                avg_n, avg_s
            )

        self.session_id = self.db.start_session()
        self.session_start_time = datetime.now()
        self.safe_seconds = 0
        self.warning_seconds = 0
        self.danger_seconds = 0
        self.total_seconds = 0
        self.neck_sum = 0.0
        self.shoulder_sum = 0.0
        self.sample_count = 0

        if not self.session_timer.isActive():
            self.session_timer.start(1000)

        self._refresh_analytics()

    def _refresh_analytics(self):
        stats = self.db.get_aggregate_stats()
        self.lbl_agg_sessions.findChild(QLabel, "val").setText(str(stats.get("total_sessions", 0)))
        dur_min = stats.get("total_duration", 0) // 60
        self.lbl_agg_duration.findChild(QLabel, "val").setText(f"{dur_min} Menit")
        score = stats.get("overall_avg_score", 100.0)
        self.lbl_agg_score.findChild(QLabel, "val").setText(f"{score:.1f}%")
        danger_min = stats.get("total_danger", 0) // 60
        self.lbl_agg_danger.findChild(QLabel, "val").setText(f"{danger_min} Menit")

        # History table
        sessions = self.db.get_recent_sessions(limit=15)
        self.history_table.setRowCount(len(sessions))
        for row, s in enumerate(sessions):
            start = s.get("start_time", "").replace("T", " ")[:16]
            dur = f"{s.get('duration_seconds', 0) // 60}m {s.get('duration_seconds', 0) % 60}s"
            score_txt = f"{s.get('posture_score', 100.0):.1f}%"
            safe_txt = f"{s.get('safe_duration_seconds', 0)}s"
            warn_txt = f"{s.get('warning_duration_seconds', 0)}s"
            danger_txt = f"{s.get('danger_duration_seconds', 0)}s"

            item = QTableWidgetItem(start)
            item.setData(Qt.UserRole, s.get("id"))
            self.history_table.setItem(row, 0, item)
            self.history_table.setItem(row, 1, QTableWidgetItem(dur))
            self.history_table.setItem(row, 2, QTableWidgetItem(score_txt))
            self.history_table.setItem(row, 3, QTableWidgetItem(safe_txt))
            self.history_table.setItem(row, 4, QTableWidgetItem(warn_txt))
            self.history_table.setItem(row, 5, QTableWidgetItem(danger_txt))

    def _toggle_overlay(self):
        if self.overlay.isVisible():
            self.overlay.hide()
            self.overlay_toggle_btn.setText("Tampilkan Overlay")
            self.overlay_toggle_btn.setIcon(get_svg_icon("eye", "#cbd5e1", 16))
        else:
            self.overlay.show()
            self.overlay_toggle_btn.setText("Sembunyikan Overlay")
            self.overlay_toggle_btn.setIcon(get_svg_icon("eye_off", "#cbd5e1", 16))

    def _on_opacity_slider_changed(self, val: int):
        opacity = val / 100.0
        self.lbl_slider_val.setText(f"Opasitas Maksimal Peredupan: {val}%")
        self.overlay.configure_intervention(opacity, self.overlay.dimming_color_hex)
        self.db.update_settings(opacity, self.overlay.dimming_color_hex, self.worker.game_mode_enabled)

    def _on_color_changed(self, idx: int):
        colors = ["#070c14", "#18181b", "#450a0a"]
        selected = colors[min(idx, len(colors) - 1)]
        self.overlay.configure_intervention(self.overlay.max_opacity, selected)
        self.db.update_settings(self.overlay.max_opacity, selected, self.worker.game_mode_enabled)

    def _on_game_mode_toggled(self, checked: bool):
        self.worker.game_mode_enabled = checked
        self.db.update_settings(self.overlay.max_opacity, self.overlay.dimming_color_hex, checked)

    def _on_status_updated(self, msg: str, is_err: bool):
        self.lbl_status.setText(f"Status: {msg}")
        if is_err:
            self.lbl_status.setStyleSheet("color: #f43f5e; font-size: 11px;")
        else:
            self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")

    def _on_fps_updated(self, fps: float):
        self.lbl_fps.setText(f"FPS: {fps:.1f}")

    def closeEvent(self, event):
        # Stop worker gracefully
        if self.worker.isRunning():
            self.worker.stop_worker()
        # Close overlay
        self.overlay.close()
        # Save last session state
        if self.session_id is not None:
            avg_n = self.neck_sum / max(1, self.sample_count)
            avg_s = self.shoulder_sum / max(1, self.sample_count)
            self.db.update_session(
                self.session_id, self.total_seconds,
                self.safe_seconds, self.warning_seconds, self.danger_seconds,
                avg_n, avg_s
            )
        event.accept()
