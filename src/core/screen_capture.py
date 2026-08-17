"""Captura de pantalla en un hilo dedicado, con cursor y sin fugas de handles GDI."""
import time

import cv2
import mss
import numpy as np
import win32api
import win32con
import win32gui
import win32ui
from PyQt5.QtCore import QThread

from ..config.settings import CAPTURE_CURSOR, VIDEO_FPS

CURSOR_SHOWING = 0x00000001


class CursorRenderer:
    """Dibuja el cursor del sistema sobre un frame.

    El handle del cursor solo cambia cuando cambia su forma, así que el bitmap
    se cachea: por frame únicamente se consultan posición y handle, que son
    llamadas baratas. Todos los recursos GDI se liberan siempre.
    """

    def __init__(self):
        self._cache = {}
        self._width = win32api.GetSystemMetrics(win32con.SM_CXCURSOR)
        self._height = win32api.GetSystemMetrics(win32con.SM_CYCURSOR)

    def _render_on(self, hcursor, background):
        """Dibuja el cursor sobre un fondo sólido y devuelve el resultado BGR."""
        hdc_screen = win32gui.GetDC(0)
        hdc = None
        hdc_mem = None
        hbmp = None
        try:
            hdc = win32ui.CreateDCFromHandle(hdc_screen)
            hdc_mem = hdc.CreateCompatibleDC()
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, self._width, self._height)
            hdc_mem.SelectObject(hbmp)
            hdc_mem.FillSolidRect((0, 0, self._width, self._height), background)
            hdc_mem.DrawIcon((0, 0), hcursor)
            bits = hbmp.GetBitmapBits(True)
            arr = np.frombuffer(bits, dtype=np.uint8).reshape(
                self._height, self._width, 4
            )
            return arr[..., :3].astype(np.float32)
        finally:
            if hbmp is not None:
                win32gui.DeleteObject(hbmp.GetHandle())
            if hdc_mem is not None:
                hdc_mem.DeleteDC()
            if hdc is not None:
                hdc.DeleteDC()
            win32gui.ReleaseDC(0, hdc_screen)

    def _build(self, hcursor):
        """Extrae color y alfa del cursor dibujándolo sobre negro y sobre blanco.

        DrawIcon pierde el canal alfa, así que se recupera comparando ambos
        renders: alpha = 1 - (blanco - negro) / 255.
        """
        on_black = self._render_on(hcursor, 0x000000)
        on_white = self._render_on(hcursor, 0xFFFFFF)

        alpha = 1.0 - np.clip((on_white - on_black) / 255.0, 0.0, 1.0)
        alpha = alpha.mean(axis=2, keepdims=True)

        safe_alpha = np.where(alpha > 0.01, alpha, 1.0)
        color = np.clip(on_black / safe_alpha, 0, 255)

        info = win32gui.GetIconInfo(hcursor)
        hotspot = (info[1], info[2])
        for handle in (info[3], info[4]):
            if handle:
                win32gui.DeleteObject(handle)

        return color, alpha, hotspot

    def _get(self, hcursor):
        entry = self._cache.get(hcursor)
        if entry is None:
            entry = self._build(hcursor)
            if len(self._cache) > 32:
                self._cache.clear()
            self._cache[hcursor] = entry
        return entry

    def draw(self, frame_bgr, monitor):
        """Superpone el cursor sobre el frame (BGR) si está dentro del monitor."""
        try:
            flags, hcursor, _ = win32gui.GetCursorInfo()
            if not (flags & CURSOR_SHOWING) or not hcursor:
                return

            color, alpha, hotspot = self._get(hcursor)
            pos_x, pos_y = win32api.GetCursorPos()

            x = pos_x - monitor['left'] - hotspot[0]
            y = pos_y - monitor['top'] - hotspot[1]

            frame_h, frame_w = frame_bgr.shape[:2]

            src_x0 = max(0, -x)
            src_y0 = max(0, -y)
            dst_x0 = max(0, x)
            dst_y0 = max(0, y)
            width = min(self._width - src_x0, frame_w - dst_x0)
            height = min(self._height - src_y0, frame_h - dst_y0)
            if width <= 0 or height <= 0:
                return

            src_color = color[src_y0:src_y0 + height, src_x0:src_x0 + width]
            src_alpha = alpha[src_y0:src_y0 + height, src_x0:src_x0 + width]
            roi = frame_bgr[dst_y0:dst_y0 + height, dst_x0:dst_x0 + width]

            blended = roi.astype(np.float32) * (1.0 - src_alpha) + src_color * src_alpha
            roi[:] = blended.astype(np.uint8)
        except Exception as exc:
            print(f"Error al dibujar el cursor: {exc}")


class ScreenCaptureThread(QThread):
    """Captura frames de un monitor a un ritmo constante.

    Publica el último frame en `latest_frame`; ni el preview ni el grabador
    escriben desde aquí, solo leen. Así la captura no depende del hilo de UI.
    """

    def __init__(self, monitor, fps=VIDEO_FPS, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.fps = fps
        self._running = True
        self._latest_frame = None
        self._cursor = CursorRenderer() if CAPTURE_CURSOR else None

    @property
    def latest_frame(self):
        """Último frame capturado en BGR, o None. Solo lectura desde otros hilos."""
        return self._latest_frame

    def run(self):
        region = {
            'top': self.monitor['top'],
            'left': self.monitor['left'],
            'width': self.monitor['width'],
            'height': self.monitor['height'],
            'mon': self.monitor.get('mon', 1),
        }
        frame_time = 1.0 / self.fps

        with mss.mss() as sct:
            next_frame_at = time.perf_counter()
            while self._running:
                try:
                    shot = sct.grab(region)
                    frame = cv2.cvtColor(np.asarray(shot), cv2.COLOR_BGRA2BGR)

                    if self._cursor is not None:
                        self._cursor.draw(frame, self.monitor)

                    self._latest_frame = frame

                    next_frame_at += frame_time
                    delay = next_frame_at - time.perf_counter()
                    if delay > 0:
                        time.sleep(delay)
                    else:
                        next_frame_at = time.perf_counter()
                except Exception as exc:
                    print(f"Error en captura: {exc}")
                    time.sleep(frame_time)

    def stop(self):
        self._running = False
        self.wait(3000)
        self._latest_frame = None
