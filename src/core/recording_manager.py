"""Orquesta la grabación: vídeo a ritmo constante y pistas de audio en paralelo."""
import os
import threading
import time
from datetime import datetime

import cv2
import numpy as np

from ..config.settings import VIDEO_CODEC, VIDEO_FPS
from ..utils.video_utils import combine_audio_video, find_ffmpeg
from .audio_capture import (
    AudioError,
    InputTrack,
    LoopbackTrack,
    find_stereo_mix_device,
    loopback_backend_available,
)


class RecordingError(Exception):
    """Error que impide grabar y que debe mostrarse al usuario."""


class RecordingManager:
    """Gestiona una sesión de grabación completa."""

    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.is_recording = False
        self.is_paused = False
        self.frames_written = 0
        self._frame_provider = None
        self._video_writer = None
        self._video_thread = None
        self._video_size = None
        self._start_time = None
        self._stop_time = None
        self._pause_time = None
        self._total_paused = 0.0
        self._tracks = []
        self._paths = None

    def start(self, monitor, selected_speakers, selected_mics, frame_provider):
        """Arranca la grabación. Lanza RecordingError si algo falla."""
        if self.is_recording:
            raise RecordingError("Ya hay una grabación en curso.")

        date_folder = datetime.now().strftime("%Y-%m-%d")
        recording_dir = os.path.join(self.output_dir, date_folder)
        os.makedirs(recording_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%H-%M-%S")
        base = os.path.join(recording_dir, f"recording_{timestamp}")

        self._paths = {
            'video': f"{base}_temp.avi",
            'mic': None,
            'speakers': None,
            'final': f"{base}.avi",
            'offsets': {},
        }
        self._frame_provider = frame_provider
        self._video_size = (int(monitor['width']), int(monitor['height']))

        try:
            self._open_video()
            tracks = {}
            if selected_mics:
                self._paths['mic'] = f"{base}_mic.wav"
                tracks['mic'] = InputTrack(
                    'Micrófono', selected_mics[0]['id'], self._paths['mic']
                )
            if selected_speakers:
                self._paths['speakers'] = f"{base}_speakers.wav"
                tracks['speakers'] = self._build_system_track(
                    selected_speakers[0], self._paths['speakers']
                )
            for track in tracks.values():
                self._start_track(track)

            self._begin_video()
            for key, track in tracks.items():
                if track.started_at is not None:
                    self._paths['offsets'][key] = track.started_at - self._start_time
        except AudioError as exc:
            self._teardown()
            raise RecordingError(str(exc)) from exc
        except Exception:
            self._teardown()
            raise

        self.is_recording = True
        print(f"\n=== Grabando en {os.path.basename(base)} ===")

    @staticmethod
    def _build_system_track(speaker, path):
        """Loopback WASAPI si es posible; si no, una entrada tipo 'Mezcla estéreo'."""
        label = 'Audio del sistema'
        if loopback_backend_available():
            return LoopbackTrack(label, speaker.get('name'), path)

        fallback = find_stereo_mix_device()
        if fallback is not None:
            return InputTrack(label, fallback, path)

        raise AudioError(
            "No hay forma de capturar el audio del sistema.\n"
            "Instala el backend de loopback con: pip install soundcard"
        )

    def _start_track(self, track):
        track.start()
        self._tracks.append(track)

    def _open_video(self):
        width, height = self._video_size
        self._video_writer = cv2.VideoWriter(
            self._paths['video'],
            cv2.VideoWriter_fourcc(*VIDEO_CODEC),
            VIDEO_FPS,
            (width, height),
        )
        if not self._video_writer.isOpened():
            self._video_writer = None
            raise RecordingError(
                "No se pudo crear el archivo de vídeo. "
                f"¿Está disponible el códec {VIDEO_CODEC}?"
            )

    def _begin_video(self):
        """Arranca el reloj del vídeo cuando el audio ya está capturando."""
        self.frames_written = 0
        self._stop_time = None
        self._start_time = time.perf_counter()
        self._video_thread = threading.Thread(
            target=self._video_loop, name="video-writer", daemon=True
        )
        self._video_thread.start()

    def _video_loop(self):
        """Escribe a FPS constante contra el reloj real.

        El número de frames escritos se deriva del tiempo transcurrido, no de
        cuántos frames haya producido la captura. Así la duración del archivo
        coincide siempre con la duración real y el audio queda sincronizado,
        aunque la captura o el encoder se retrasen puntualmente.
        """
        width, height = self._video_size
        black = np.zeros((height, width, 3), dtype=np.uint8)
        frame_time = 1.0 / VIDEO_FPS

        try:
            while True:
                end = self._stop_time
                if end is not None:
                    now = end
                elif self.is_paused:
                    time.sleep(frame_time / 2)
                    continue
                else:
                    now = time.perf_counter()
                target = int((now - self._start_time - self._total_paused) * VIDEO_FPS)

                frame = self._frame_provider() if self._frame_provider else None
                frame = self._fit(frame, width, height) if frame is not None else black

                while self.frames_written < target:
                    self._video_writer.write(frame)
                    self.frames_written += 1

                if end is not None:
                    return
                time.sleep(frame_time / 2)
        except Exception as exc:
            print(f"[video-writer] error fatal: {exc}")
            self._stop_time = time.perf_counter()

    def pause(self):
        """Pausa la grabación."""
        if not self.is_recording or self.is_paused:
            return
        self.is_paused = True
        self._pause_time = time.perf_counter()
        for track in self._tracks:
            track.set_paused(True)
        print("=== Grabación pausada ===")

    def resume(self):
        """Reanuda la grabación."""
        if not self.is_recording or not self.is_paused:
            return
        if self._pause_time is not None:
            self._total_paused += time.perf_counter() - self._pause_time
            self._pause_time = None
        self.is_paused = False
        for track in self._tracks:
            track.set_paused(False)
        print("=== Grabación reanudada ===")

    def get_track_levels(self):
        """Devuelve dict con nivel RMS de cada pista activa."""
        return {track.label: track.get_level() for track in self._tracks}

    def get_track_volumes(self):
        """Devuelve dict con volumen de cada pista activa."""
        return {track.label: track.volume for track in self._tracks}

    def set_track_volume(self, label, volume):
        """Ajusta el volumen de una pista por su etiqueta."""
        for track in self._tracks:
            if track.label == label:
                track.volume = max(0.0, min(2.0, volume))
                return

    @staticmethod
    def _fit(frame, width, height):
        """Adapta el frame al tamaño del writer (cv2 descarta los que no encajan)."""
        if frame is None or frame.size == 0:
            return np.zeros((height, width, 3), dtype=np.uint8)
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.ndim == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        elif frame.ndim == 3 and frame.shape[2] != 3:
            return np.zeros((height, width, 3), dtype=np.uint8)
        if frame.shape[0] != height or frame.shape[1] != width:
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        return frame

    def stop(self):
        """Cierra streams y archivos. Rápido y síncrono; devuelve las rutas."""
        if not self.is_recording:
            return None

        self.is_recording = False
        self.is_paused = False
        self._pause_time = None
        self._total_paused = 0.0
        print("\n=== Deteniendo grabación ===")

        for track in self._tracks:
            track.stop()
        self._tracks.clear()

        self._stop_video()

        paths = self._paths
        self._paths = None
        self._frame_provider = None

        print(f"[ok] {self.frames_written} frames "
              f"({self.frames_written / VIDEO_FPS:.1f}s)")
        return paths

    def _stop_video(self):
        self._stop_time = time.perf_counter()
        if self._video_thread is not None:
            self._video_thread.join(timeout=15)
            self._video_thread = None
        if self._video_writer is not None:
            self._video_writer.release()
            self._video_writer = None

    def _teardown(self):
        """Limpieza tras un arranque fallido: no deja hilos ni archivos a medias."""
        for track in self._tracks:
            track.stop()
        self._tracks.clear()
        self._stop_video()
        if self._paths:
            for key in ('video', 'mic', 'speakers'):
                path = self._paths.get(key)
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        self._paths = None
        self.is_recording = False

    def finalize(self, paths):
        """Mezcla audio y vídeo. Bloqueante: llamar fuera del hilo de UI."""
        if not paths:
            return None

        offsets = paths.get('offsets') or {}
        audio_files = [
            (paths[key], offsets.get(key, 0.0)) for key in ('mic', 'speakers')
            if paths.get(key) and os.path.exists(paths[key])
        ]
        _, message = combine_audio_video(paths['video'], audio_files, paths['final'])
        print(message)
        return paths['final'] if os.path.exists(paths['final']) else paths['video']

    @staticmethod
    def ffmpeg_available():
        return find_ffmpeg() is not None

    def cleanup(self):
        """Libera todo por si la app se cierra en cualquier estado."""
        if self.is_recording:
            self.stop()
            return
        for track in self._tracks:
            track.stop()
        self._tracks.clear()
        self._stop_video()
