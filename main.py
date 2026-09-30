import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Ensure local imports work correctly regardless of invocation path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.dashboard_window import DashboardWindow


def main():
    # Enable Modern High-DPI Scaling for Crisp Gaming Displays
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("SIERRA")
    app.setOrganizationName("Universitas Siliwangi")

    window = DashboardWindow()
    window.setWindowState(Qt.WindowMaximized)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
