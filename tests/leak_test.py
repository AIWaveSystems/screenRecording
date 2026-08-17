"""Comprueba que la captura de cursor no filtra handles GDI/User."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
import ctypes
import sys
import time

from PyQt5.QtWidgets import QApplication

from src.core.screen_capture import ScreenCaptureThread
from src.ui.main_window import get_screen_list

GR_GDIOBJECTS, GR_USEROBJECTS = 0, 1
ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
ctypes.windll.user32.GetGuiResources.argtypes = [ctypes.c_void_p, ctypes.c_uint]
ctypes.windll.user32.GetGuiResources.restype = ctypes.c_uint
proc = ctypes.windll.kernel32.GetCurrentProcess()


def counts():
    g = ctypes.windll.user32.GetGuiResources(proc, GR_GDIOBJECTS)
    u = ctypes.windll.user32.GetGuiResources(proc, GR_USEROBJECTS)
    return g, u


app = QApplication(sys.argv)
mon = get_screen_list()[0]['monitor']
cap = ScreenCaptureThread(mon)
cap.start()
time.sleep(2)
base = counts()
print("handles tras 2s :", base)
time.sleep(20)
after = counts()
cap.stop()
print("handles tras 22s:", after)
print(f"delta en ~600 frames -> GDI {after[0] - base[0]:+d}, USER {after[1] - base[1]:+d}")
print("RESULTADO:", "OK, sin fuga" if after[0] - base[0] < 20 else "FUGA DETECTADA")
