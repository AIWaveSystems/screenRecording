"""Orquesta la grabación: vídeo a ritmo constante y audio en pistas paralelas."""
import os
import time
from datetime import datetime

import cv2
import numpy as np

from ..config.settings import MIC_BOOST, VIDEO_CODEC, VIDEO_FPS
from ..utils.video_utils import combine_audio_video, find_ffmpeg
from .audio_capture import (
    AudioError,
    InputTrack,
    LoopbackTrack,
    find_stereo_mix_device,
    loopback_backend_available,
)

MIC = 'mic'
SPEAKERS = 'speakers'
TRACK_LABELS = {MIC: 'Micrófono', SPEAKERS: 'Audio del sistema'}

_MAX_CATCHUP_SECONDS = 5


class RecordingError(Exception):
    """Error que impide grabar y que debe mostrarse al usuario."""


class RecordingManager:
    """Gestiona una sesión de grabación completa.

    write_frame() se llama desde el timer de la UI, pero el número de frames
    que escribe lo decide el reloj real, no la frecuencia con que se le llame.
    Así la duración del archivo coincide con la duración de la grabación
    aunque el preview corra a menos FPS o la UI se retrase.
    """

    def __init__(self, output_dir, fps=VIDEO_FPS, codec=VIDEO_CODEC,
                 mic_boost=MIC_BOOST):
        self.output_dir = output_dir
        self.fps = fps
        self.codec = codec
        self.mic_boost = mic_boost
        self.is_recording = False
        self.is_paused = False
        self.frames_written = 0
        self.dropped_frames = 0
        self._video_writer = None
        self._video_size = None
        self._start_time = None
        self._pause_time = None
        self._total_paused = 0.0
        self._tracks = {}
        self._paths = None

    def start(self, monitor, selected_speakers, selected_mics,
              volumes=None, muted=None):
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
        self.dropped_frames = 0
        volumes = volumes or {}
        muted = muted or {}

        try:
            self._open_video()

            pending = {}
            if selected_mics:
                self._paths[MIC] = f"{base}_mic.wav"
                pending[MIC] = InputTrack(
                    TRACK_LABELS[MIC], selected_mics[0]['id'], self._paths[MIC]
                )
            if selected_speakers:
                self._paths[SPEAKERS] = f"{base}_speakers.wav"
                pending[SPEAKERS] = self._build_system_track(
                    selected_speakers[0], self._paths[SPEAKERS]
                )

            for key, track in pending.items():
                track.volume = volumes.get(key, 1.0)
                track.boost = self.mic_boost if key == MIC else 1.0
                track.set_muted(muted.get(key, False))
                track.start()
                self._tracks[key] = track

            self._total_paused = 0.0
            self._pause_time = None
            self._start_time = time.perf_counter()

            self._paths['offsets'] = {
                key: track.started_at - self._start_time
                for key, track in self._tracks.items()
                if track.started_at is not None
            }
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
        label = TRACK_LABELS[SPEAKERS]
        if loopback_backend_available():
            return LoopbackTrack(label, speaker.get('name'), path)
        fallback = find_stereo_mix_device()
        if fallback is not None:
            return InputTrack(label, fallback, path)
        raise AudioError(
            "No hay forma de capturar el audio del sistema.\n"
            "Instala el backend de loopback con: pip install PyAudioWPatch"
        )

    def _open_video(self):
        width, height = self._video_size
        path = self._paths['video']
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

        for codec in (self.codec, 'MJPG', 'mp4v'):
            writer = cv2.VideoWriter(
                path, cv2.VideoWriter_fourcc(*codec), self.fps, (width, height),
            )
            if writer.isOpened():
                self._video_writer = writer
                if codec != self.codec:
                    print(f"[video-writer] {self.codec} no disponible, se usa {codec}")
                return
            writer.release()
        raise RecordingError("No se encontró un códec de vídeo funcional.")

    def write_frame(self, frame):
        """Escribe los frames que exija el reloj, duplicando el último si hace falta."""
        if not self.is_recording or self.is_paused or self._video_writer is None:
            return
        if self._start_time is None:
            return

        elapsed = time.perf_counter() - self._start_time - self._total_paused
        target = int(elapsed * self.fps)
        if target <= self.frames_written:
            return

        try:
            prepared = self._fit(frame)
            limit = self.frames_written + int(_MAX_CATCHUP_SECONDS * self.fps)
            while self.frames_written < min(target, limit):
                self._video_writer.write(prepared)
                self.frames_written += 1
            if target > limit:
                self.dropped_frames += target - limit
                self.frames_written = target
        except Exception as exc:
            print(f"[video-writer] error escribiendo frame: {exc}")

    def _fit(self, frame):
        width, height = self._video_size
        if frame is None or getattr(frame, 'size', 0) == 0:
            return np.zeros((height, width, 3), dtype=np.uint8)
        if frame.ndim == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        if frame.shape[:2] != (height, width):
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        return frame

    def pause(self):
        if not self.is_recording or self.is_paused:
            return
        self.is_paused = True
        self._pause_time = time.perf_counter()
        for track in self._tracks.values():
            track.set_paused(True)
        print("=== Grabación pausada ===")

    def resume(self):
        if not self.is_recording or not self.is_paused:
            return
        if self._pause_time is not None:
            self._total_paused += time.perf_counter() - self._pause_time
            self._pause_time = None
        self.is_paused = False
        for track in self._tracks.values():
            track.set_paused(False)
        print("=== Grabación reanudada ===")

    def get_levels(self):
        """Nivel RMS por pista, con las claves MIC y SPEAKERS."""
        return {key: track.get_level() for key, track in self._tracks.items()}

    def set_volume(self, key, volume):
        track = self._tracks.get(key)
        if track is not None:
            track.volume = max(0.0, min(2.0, volume))

    def set_muted(self, key, muted):
        track = self._tracks.get(key)
        if track is not None:
            track.set_muted(muted)

    def set_mic_boost(self, boost):
        """Refuerzo fijo del micrófono, aplicable también en caliente."""
        self.mic_boost = max(1.0, min(3.0, boost))
        track = self._tracks.get(MIC)
        if track is not None:
            track.boost = self.mic_boost

    def elapsed_seconds(self):
        if not self.is_recording or self._start_time is None:
            return 0.0
        paused = self._total_paused
        if self.is_paused and self._pause_time is not None:
            paused += time.perf_counter() - self._pause_time
        return max(0.0, time.perf_counter() - self._start_time - paused)

    def stop(self):
        """Cierra streams y archivos. Devuelve las rutas."""
        if not self.is_recording:
            return None

        if self.is_paused:
            self.resume()

        self._flush_video_tail()
        self.is_recording = False
        print("\n=== Deteniendo grabación ===")

        for track in self._tracks.values():
            try:
                track.stop()
            except Exception as exc:
                print(f"[stop] error deteniendo pista: {exc}")
        self._tracks.clear()

        self._release_writer()

        paths = self._paths
        self._paths = None
        self._start_time = None

        print(f"[ok] {self.frames_written} frames "
              f"({self.frames_written / self.fps:.1f}s)")
        if self.dropped_frames:
            print(f"[aviso] {self.dropped_frames} frames perdidos por retrasos")
        return paths

    def _flush_video_tail(self):
        """Completa los frames del último tramo para no cortar el final."""
        if self._video_writer is None or self._start_time is None:
            return
        elapsed = time.perf_counter() - self._start_time - self._total_paused
        target = int(elapsed * self.fps)
        if target <= self.frames_written:
            return
        try:
            width, height = self._video_size
            blank = np.zeros((height, width, 3), dtype=np.uint8)
            limit = self.frames_written + int(_MAX_CATCHUP_SECONDS * self.fps)
            while self.frames_written < min(target, limit):
                self._video_writer.write(blank)
                self.frames_written += 1
        except Exception as exc:
            print(f"[video-writer] error al cerrar el tramo final: {exc}")

    def _release_writer(self):
        if self._video_writer is not None:
            try:
                self._video_writer.release()
            except Exception as exc:
                print(f"[stop] error liberando writer: {exc}")
            self._video_writer = None

    def finalize(self, paths):
        """Mezcla audio y vídeo. Bloqueante: llamar fuera del hilo de UI."""
        if not paths:
            return None
        offsets = paths.get('offsets') or {}
        audio_files = [
            (paths[key], offsets.get(key, 0.0)) for key in (MIC, SPEAKERS)
            if paths.get(key) and os.path.exists(paths[key])
        ]
        _, message = combine_audio_video(paths['video'], audio_files, paths['final'])
        print(message)
        return paths['final'] if os.path.exists(paths['final']) else paths['video']

    @staticmethod
    def ffmpeg_available():
        return find_ffmpeg() is not None

    def _teardown(self):
        for track in self._tracks.values():
            try:
                track.stop()
            except Exception:
                pass
        self._tracks.clear()
        self._release_writer()
        if self._paths:
            for key in ('video', MIC, SPEAKERS):
                path = self._paths.get(key)
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        self._paths = None
        self.is_recording = False
        self.is_paused = False
        self._start_time = None

    def cleanup(self):
        if self.is_recording:
            self.stop()
            return
        for track in self._tracks.values():
            try:
                track.stop()
            except Exception:
                pass
        self._tracks.clear()
        self._release_writer()
