import sys
import ctypes
from ctypes import wintypes
from typing import Tuple


class GameModeDetector:
    def __init__(self):
        self.is_windows = sys.platform.startswith("win")
        if self.is_windows:
            self.user32 = ctypes.windll.user32

    def is_fullscreen_or_game_running(self) -> Tuple[bool, str]:
        """
        Detects if current foreground window is running in fullscreen (standard for games)
        or if a dedicated game process is active.
        Returns:
            (is_active: bool, window_title: str)
        """
        if not self.is_windows:
            return False, ""

        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return False, ""

            # Check window title
            length = self.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value

            # Skip common shell windows
            if title in ["", "Program Manager", "Task Switching", "Cortana", "Start"]:
                return False, ""

            # Check window dimensions vs screen dimensions
            rect = wintypes.RECT()
            self.user32.GetWindowRect(hwnd, ctypes.byref(rect))

            screen_w = self.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_h = self.user32.GetSystemMetrics(1)  # SM_CYSCREEN

            win_w = rect.right - rect.left
            win_h = rect.bottom - rect.top

            # If foreground window spans the entire screen resolution, it's fullscreen / borderless game
            if win_w >= screen_w and win_h >= screen_h and rect.left <= 0 and rect.top <= 0:
                return True, title

            return False, title
        except Exception:
            return False, ""
