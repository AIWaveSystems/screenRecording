import cv2
import numpy as np
import subprocess
import os
from ..config.settings import VIDEO_CODEC, VIDEO_QUALITY

class VideoProcessor:
    def __init__(self):
        self.video_writer = None
        self._temp_frames = []
        self._max_temp_frames = 30  # Buffer de 1 segundo a 30 FPS
        
    def init_writer(self, filename, width, height, fps):
        """Inicializa el escritor de video de manera optimizada."""
        try:
            self.video_writer = cv2.VideoWriter(
                filename,
                cv2.VideoWriter_fourcc(*VIDEO_CODEC),
                fps,
                (width, height)
            )
            return self.video_writer.isOpened()
        except Exception as e:
            print(f"Error al inicializar video writer: {str(e)}")
            return False
    
    def write_frame(self, frame):
        """Escribe un frame al video con buffering."""
        try:
            if len(self._temp_frames) >= self._max_temp_frames:
                # Escribir frames en lote
                for temp_frame in self._temp_frames:
                    self.video_writer.write(temp_frame)
                self._temp_frames.clear()
            
            self._temp_frames.append(frame)
            return True
        except Exception as e:
            print(f"Error al escribir frame: {str(e)}")
            return False
    
    def close(self):
        """Cierra el writer y limpia recursos."""
        try:
            # Escribir frames restantes
            for frame in self._temp_frames:
                self.video_writer.write(frame)
            self._temp_frames.clear()
            
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            return True
        except Exception as e:
            print(f"Error al cerrar video writer: {str(e)}")
            return False

def combine_audio_video(video_file, audio_files, output_file):
    """Combina video y audio de manera optimizada usando FFmpeg."""
    try:
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"No se encuentra el video: {video_file}")

        # Verificar archivos de audio válidos
        valid_audio_files = [
            f for f in audio_files 
            if os.path.exists(f) and os.path.getsize(f) > 44
        ]

        if not valid_audio_files:
            os.rename(video_file, output_file)
            return True

        # Construir comando FFmpeg optimizado
        cmd = ['ffmpeg', '-y', '-i', video_file]
        
        # Agregar inputs de audio
        for audio_file in valid_audio_files:
            cmd.extend(['-i', audio_file])

        # Configurar filtros y mapeo
        if len(valid_audio_files) > 1:
            filter_complex = ''.join([
                f'[{i+1}:a]volume=1[a{i}];' 
                for i in range(len(valid_audio_files))
            ])
            filter_complex += ''.join([
                f'[a{i}]' for i in range(len(valid_audio_files))
            ])
            filter_complex += f'amix=inputs={len(valid_audio_files)}:duration=longest[a]'
            
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '0:v', '-map', '[a]'
            ])
        else:
            cmd.extend(['-map', '0:v', '-map', '1:a'])

        # Configurar códecs y calidad
        cmd.extend([
            '-c:v', 'mpeg4',
            '-q:v', str(VIDEO_QUALITY),
            '-c:a', 'aac',
            '-b:a', '192k',  # Reducido de 320k para optimizar
            output_file
        ])

        # Ejecutar FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Limpiar archivos temporales
        os.remove(video_file)
        for audio_file in valid_audio_files:
            os.remove(audio_file)

        return True

    except Exception as e:
        print(f"Error al combinar audio y video: {str(e)}")
        if os.path.exists(video_file):
            os.rename(video_file, output_file)
        return False 