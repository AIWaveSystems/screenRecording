import mss
import numpy as np
import cv2
import time
from PyQt5.QtCore import QThread, pyqtSignal
import win32gui
import win32ui
import win32con
import win32api
from ..config.settings import VIDEO_FPS

def capture_cursor():
    """Captura la posición y la imagen del cursor."""
    try:
        cursor_info = win32gui.GetCursorInfo()
        hcursor = cursor_info[1]
        pos = win32api.GetCursorPos()
        
        # Crear DC y bitmap para el cursor
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, 32, 32)
        
        # Crear DC compatible para dibujar
        hdc_mem = hdc.CreateCompatibleDC()
        hdc_mem.SelectObject(hbmp)
        
        # Dibujar el cursor
        hdc_mem.DrawIcon((0, 0), hcursor)
        
        # Convertir a array de numpy
        bmp_bits = hbmp.GetBitmapBits(True)
        cursor_img = np.frombuffer(bmp_bits, dtype=np.uint8).reshape(32, 32, 4)
        
        # Limpiar
        win32gui.DeleteObject(hbmp.GetHandle())
        hdc_mem.DeleteDC()
        hdc.DeleteDC()
        
        return cursor_img, pos
    except Exception as e:
        print(f"Error al capturar cursor: {str(e)}")
        return None, None

class ScreenCaptureThread(QThread):
    update_image_signal = pyqtSignal(object)

    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.running = True
        self.last_frame = None

    def run(self):
        with mss.mss() as sct:
            last_time = time.time()
            target_time = 1.0 / VIDEO_FPS
            
            while self.running:
                try:
                    current_time = time.time()
                    elapsed = current_time - last_time
                    
                    if elapsed < target_time:
                        time.sleep(target_time - elapsed)
                    
                    # Capturar pantalla
                    screenshot = np.array(sct.grab({
                        'top': self.monitor['top'],
                        'left': self.monitor['left'],
                        'width': self.monitor['width'],
                        'height': self.monitor['height'],
                        'mon': self.monitor['mon']
                    }))
                    
                    # Capturar cursor
                    cursor_img, cursor_pos = capture_cursor()
                    
                    # Crear una copia para no modificar el original
                    frame = screenshot.copy()
                    
                    # Superponer el cursor si está disponible
                    if cursor_img is not None and cursor_pos is not None:
                        cursor_x = cursor_pos[0] - self.monitor['left']
                        cursor_y = cursor_pos[1] - self.monitor['top']
                        
                        if (0 <= cursor_x < self.monitor['width'] - 32 and 
                            0 <= cursor_y < self.monitor['height'] - 32):
                            
                            # Región donde se dibujará el cursor
                            roi = frame[cursor_y:cursor_y+32, cursor_x:cursor_x+32]
                            
                            # Aplicar el cursor usando la máscara alpha
                            alpha_mask = cursor_img[..., 3:] / 255.0
                            inv_alpha_mask = 1.0 - alpha_mask
                            
                            # Combinar el cursor con el fondo
                            for c in range(3):  # Para cada canal de color
                                roi[..., c] = (roi[..., c] * inv_alpha_mask[..., 0] + 
                                             cursor_img[..., c] * alpha_mask[..., 0])
                    
                    # Convertir de BGRA a BGR para OpenCV
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                    # Guardar el último frame
                    self.last_frame = frame_bgr
                    
                    # Emitir señal con el frame con cursor
                    self.update_image_signal.emit(frame)
                    
                    last_time = time.time()
                    
                except Exception as e:
                    print(f"Error en captura: {str(e)}")
                    time.sleep(target_time)

    def stop(self):
        self.running = False
        self.wait()  # Esperar a que termine el thread 