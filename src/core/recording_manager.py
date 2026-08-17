"""Orquesta la grabación: vídeo escrito desde el hilo de UI y audio en paralelo."""
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
    """Gestiona una sesión de grabación completa.

    El vídeo se escribe desde write_frame(), invocado por el timer de la UI.
    Así no hay daemon thread de vídeo y un crash en OpenCV se ve con
    traceback completo en vez de matar el proceso silenciosamente.
    """

    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.is_recording = False
        self.is_paused = False
        self.frames_written = 0
        self._video_writer = None
        self._video_size = None
        self._tracks = []
        self._paths = None

    def start(self, monitor, selected_speakers, selected_mics):
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
        self._video_size = (int(monitor['width']), int(monitor['height']))
        self.frames_written = 0

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

            start_time = time.perf_counter()
            for track in tracks.values():
                track.start()
                self._tracks.append(track)

            offsets = {}
            for key, track in tracks.items():
                if track.started_at is not None:
                    offsets[key] = track.started_at - start_time
            self._paths['offsets'] = offsets

        except AudioError as exc:
            self._teardown()
            raise RecordingError(str(exc)) from exc
        except Exception:
            self._teardown()
            raise

        self.is_recording = True
        self.is_paused = False
        print(f"\n=== Grabando en {os.path.basename(base)} ===")

    @staticmethod
    def _build_system_track(speaker, path):
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

    def _open_video(self):
        width, height = self._video_size
        path = self._paths['video']
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        for codec in [VIDEO_CODEC, 'MJPG', 'mp4v']:
            self._video_writer = cv2.VideoWriter(
                path, cv2.VideoWriter_fourcc(*codec), VIDEO_FPS, (width, height),
            )
            if self._video_writer.isOpened():
                print(f"[video-writer] códec: {codec}")
                return
            self._video_writer.release()
            self._video_writer = None
        raise RecordingError("No se encontró un códec de vídeo funcional.")

    def write_frame(self, frame):
        """Escribe un frame al vídeo. Se llama desde el timer de la UI."""
        if not self.is_recording or self.is_paused:
            return
        if self._video_writer is None:
            return
        try:
            width, height = self._video_size
            if frame is None or frame.size == 0:
                frame = np.zeros((height, width, 3), dtype=np.uint8)
            else:
                if frame.ndim == 3 and frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height),
                                       interpolation=cv2.INTER_AREA)
            self._video_writer.write(frame)
            self.frames_written += 1
        except Exception as exc:
            print(f"[video-writer] error escribiendo frame: {exc}")

    def pause(self):
        if not self.is_recording or self.is_paused:
            return
        self.is_paused = True
        for track in self._tracks:
            track.set_paused(True)
        print("=== Grabación pausada ===")

    def resume(self):
        if not self.is_recording or not self.is_paused:
            return
        self.is_paused = False
        for track in self._tracks:
            track.set_paused(False)
        print("=== Grabación reanudada ===")

    def get_track_levels(self):
        return {track.label: track.get_level() for track in self._tracks}

    def set_track_volume(self, label, volume):
        for track in self._tracks:
            if track.label == label:
                track.volume = max(0.0, min(2.0, volume))
                return

    def stop(self):
        """Cierra streams y archivos. Devuelve las rutas."""
        if not self.is_recording:
            return None

        self.is_recording = False
        self.is_paused = False
        print("\n=== Deteniendo grabación ===")

        for track in self._tracks:
            try:
                track.stop()
            except Exception as exc:
                print(f"[stop] error deteniendo pista: {exc}")
        self._tracks.clear()

        if self._video_writer is not None:
            try:
                self._video_writer.release()
            except Exception as exc:
                print(f"[stop] error liberando writer: {exc}")
            self._video_writer = None

        paths = self._paths
        self._paths = None

        print(f"[ok] {self.frames_written} frames "
              f"({self.frames_written / VIDEO_FPS:.1f}s)")
        return paths

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

    def _teardown(self):
        for track in self._tracks:
            try:
                track.stop()
            except Exception:
                pass
        self._tracks.clear()
        if self._video_writer is not None:
            try:
                self._video_writer.release()
            except Exception:
                pass
            self._video_writer = None
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

    def cleanup(self):
        if self.is_recording:
            self.stop()
        for track in self._tracks:
            try:
                track.stop()
            except Exception:
                pass
        self._tracks.clear()
        if self._video_writer is not None:
            try:
                self._video_writer.release()
            except Exception:
                pass
            self._video_writer = None
