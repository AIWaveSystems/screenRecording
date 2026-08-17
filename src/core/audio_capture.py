"""Pistas de audio: micrófono (sounddevice) y audio del sistema (loopback WASAPI).

En ambos casos la captura solo encola bloques; el disco se toca desde un hilo
aparte para que el hilo de audio en tiempo real nunca se bloquee.
"""
import queue
import threading
import time
import wave
import warnings

import numpy as np
import sounddevice as sd

warnings.filterwarnings("ignore", message=".*data discontinuity.*")

try:
    from soundcard.mediafoundation import SoundcardRuntimeWarning
    warnings.filterwarnings("ignore", category=SoundcardRuntimeWarning)
except ImportError:
    pass

from ..config.settings import (
    AUDIO_CHUNK_SIZE,
    AUDIO_MAX_CHANNELS,
    AUDIO_QUEUE_MAX,
    AUDIO_SAMPLE_RATE,
)


class AudioError(Exception):
    """Fallo de audio que debe mostrarse al usuario en lugar de silenciarse."""


def loopback_backend_available():
    try:
        import soundcard
        return True
    except Exception:
        return False


class BaseTrack:
    """Cola + escritor WAV compartidos por todas las pistas."""

    def __init__(self, label, path):
        self.label = label
        self.path = path
        self.dropped_blocks = 0
        self.started_at = None
        self._queue = queue.Queue(maxsize=AUDIO_QUEUE_MAX)
        self._wav = None
        self._writer = None
        self._running = False
        self._paused = False
        self.volume = 1.0
        self.level = 0.0
        self._level_lock = threading.Lock()

    @property
    def is_paused(self):
        return self._paused

    def set_paused(self, paused):
        self._paused = paused

    def get_level(self):
        with self._level_lock:
            return self.level

    def _update_level(self, block):
        rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
        with self._level_lock:
            self.level = min(1.0, rms * 3.0)

    def _open_wav(self, channels, samplerate):
        self._wav = wave.open(self.path, 'wb')
        self._wav.setnchannels(channels)
        self._wav.setsampwidth(2)
        self._wav.setframerate(int(samplerate))
        self._running = True
        self._writer = threading.Thread(
            target=self._drain, name=f"audio-{self.label}", daemon=True
        )
        self._writer.start()

    def _submit(self, block):
        try:
            self._queue.put_nowait(block)
        except queue.Full:
            self.dropped_blocks += 1

    def _drain(self):
        while True:
            try:
                block = self._queue.get(timeout=0.2)
            except queue.Empty:
                if not self._running:
                    return
                continue
            if block is None:
                return
            try:
                self._update_level(block)
                if self._paused:
                    continue
                scaled = block * self.volume
                data = np.clip(scaled, -1.0, 1.0)
                self._wav.writeframes((data * 32767).astype(np.int16).tobytes())
            except Exception as exc:
                print(f"[{self.label}] error al escribir audio: {exc}")
                return

    def _close_wav(self):
        if self._writer is not None:
            self._queue.put(None)
            self._writer.join(timeout=5)
            self._writer = None
        if self._wav is not None:
            self._wav.close()
            self._wav = None
        with self._level_lock:
            self.level = 0.0
        if self.dropped_blocks:
            print(f"[{self.label}] {self.dropped_blocks} bloques descartados")

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class InputTrack(BaseTrack):
    """Captura de un dispositivo de entrada (micrófono, mezcla estéreo...)."""

    def __init__(self, label, device_id, path):
        super().__init__(label, path)
        self._device_id = device_id
        self._stream = None

    def _negotiate(self):
        """Canales y sample rate que el hardware acepta de verdad."""
        info = sd.query_devices(self._device_id)
        available = int(info['max_input_channels'])
        if available < 1:
            raise AudioError(f"'{info['name']}' no tiene canales de entrada.")

        channels = max(1, min(AUDIO_MAX_CHANNELS, available))

        for rate in (AUDIO_SAMPLE_RATE, int(info['default_samplerate'])):
            try:
                sd.check_input_settings(
                    device=self._device_id,
                    channels=channels,
                    samplerate=rate,
                    dtype='float32',
                )
                return channels, rate, info['name']
            except Exception:
                continue

        raise AudioError(
            f"'{info['name']}' no admite grabación con {channels} canal(es) "
            f"a {AUDIO_SAMPLE_RATE} Hz ni a {int(info['default_samplerate'])} Hz."
        )

    def start(self):
        channels, rate, name = self._negotiate()
        self._open_wav(channels, rate)

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[{self.label}] estado del stream: {status}")
            if self._running:
                self._submit(indata.copy())

        try:
            self._stream = sd.InputStream(
                device=self._device_id,
                channels=channels,
                samplerate=rate,
                blocksize=AUDIO_CHUNK_SIZE,
                dtype='float32',
                callback=callback,
            )
            self._stream.start()
            self.started_at = time.perf_counter()
        except Exception as exc:
            self._running = False
            self._close_wav()
            raise AudioError(f"No se pudo abrir '{name}': {exc}") from exc

        print(f"[ok] {self.label}: {name} ({channels} ch, {rate} Hz)")

    def stop(self):
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                print(f"[{self.label}] error al cerrar el stream: {exc}")
            self._stream = None
        self._close_wav()


class LoopbackTrack(BaseTrack):
    """Audio del sistema por loopback WASAPI, sin necesidad de 'Mezcla estéreo'.

    soundcard expone una API de lectura (pull) en vez de callbacks, así que la
    captura vive en su propio hilo.
    """

    def __init__(self, label, speaker_name, path):
        super().__init__(label, path)
        self._speaker_name = speaker_name
        self._thread = None
        self._ready = threading.Event()
        self._error = None

    def _resolve_microphone(self):
        import soundcard as sc

        speaker = None
        if self._speaker_name:
            needle = self._speaker_name[:28].lower()
            for candidate in sc.all_speakers():
                name = candidate.name.lower()
                if name.startswith(needle) or needle.startswith(name[:28]):
                    speaker = candidate
                    break
        if speaker is None:
            speaker = sc.default_speaker()
        if speaker is None:
            raise AudioError("No se encontró ningún dispositivo de salida.")

        mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        if mic is None:
            raise AudioError(
                f"'{speaker.name}' no admite captura por loopback."
            )
        return mic, speaker.name

    def start(self):
        try:
            import soundcard
        except ImportError as exc:
            raise AudioError(
                "Falta el paquete 'soundcard', necesario para grabar el audio "
                "del sistema.\nInstálalo con: pip install soundcard"
            ) from exc

        mic, name = self._resolve_microphone()
        channels = max(1, min(AUDIO_MAX_CHANNELS, mic.channels or AUDIO_MAX_CHANNELS))
        self._open_wav(channels, AUDIO_SAMPLE_RATE)

        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(mic, channels),
            name=f"loopback-{self.label}",
            daemon=True,
        )
        self._thread.start()

        if not self._ready.wait(timeout=5):
            self.stop()
            raise AudioError(f"'{name}' no respondió al abrir el loopback.")
        if self._error is not None:
            error = self._error
            self.stop()
            raise AudioError(f"No se pudo capturar el audio de '{name}': {error}")

        print(f"[ok] {self.label}: {name} (loopback, {channels} ch, "
              f"{AUDIO_SAMPLE_RATE} Hz)")

    def _capture_loop(self, mic, channels):
        try:
            with mic.recorder(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=channels,
                blocksize=AUDIO_CHUNK_SIZE,
            ) as recorder:
                self.started_at = time.perf_counter()
                self._ready.set()
                while self._running:
                    self._submit(recorder.record(numframes=AUDIO_CHUNK_SIZE))
        except Exception as exc:
            self._error = exc
            self._ready.set()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._close_wav()


def find_stereo_mix_device():
    """Índice de una entrada tipo 'Mezcla estéreo', o None si no hay ninguna."""
    for i, dev in enumerate(sd.query_devices()):
        name = dev['name'].lower()
        if dev['max_input_channels'] > 0 and (
            'stereo mix' in name
            or 'mezcla est' in name
            or 'what u hear' in name
            or 'voicemeeter' in name
            or 'cable output' in name
        ):
            return i
    return None


class LiveAudioMonitor:
    """Monitorea niveles de audio en vivo sin grabar.

    Para micrófono usa sounddevice InputStream (dispositivo de entrada).
    Para parlante usa soundcard loopback WASAPI (captura la salida del sistema).
    """

    def __init__(self):
        self._streams = {}
        self._threads = {}
        self._levels = {}
        self._running = {}
        self._lock = threading.Lock()

    def start(self, mic_device_id=None, speaker_device_id=None):
        self.stop()
        if mic_device_id is not None:
            self._add_input_stream('mic', mic_device_id)
        if speaker_device_id is not None:
            self._add_loopback_stream('speakers', speaker_device_id)

    def _add_input_stream(self, label, device_id):
        try:
            info = sd.query_devices(device_id)
            channels = max(1, min(AUDIO_MAX_CHANNELS, int(info.get('max_input_channels', 1))))
            if channels < 1:
                return

            for rate in (AUDIO_SAMPLE_RATE, int(info.get('default_samplerate', 48000))):
                try:
                    sd.check_input_settings(
                        device=device_id, channels=channels,
                        samplerate=rate, dtype='float32',
                    )
                    break
                except Exception:
                    continue
            else:
                return

            def callback(indata, frames, time_info, status, _label=label):
                rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))
                level = min(1.0, rms * 3.0)
                with self._lock:
                    self._levels[_label] = level

            stream = sd.InputStream(
                device=device_id, channels=channels, samplerate=rate,
                blocksize=AUDIO_CHUNK_SIZE, dtype='float32', callback=callback,
            )
            stream.start()
            with self._lock:
                self._streams[label] = stream
                self._levels[label] = 0.0
        except Exception as exc:
            print(f"[LiveMonitor] no se pudo abrir micrófono: {exc}")

    def _add_loopback_stream(self, label, speaker_device_id):
        try:
            import soundcard as sc
        except ImportError:
            print("[LiveMonitor] soundcard no instalado, no se puede monitorear parlante")
            return

        try:
            speaker_info = sd.query_devices(speaker_device_id)
            speaker_name = speaker_info['name']

            speaker = None
            needle = speaker_name[:28].lower()
            for candidate in sc.all_speakers():
                name = candidate.name.lower()
                if name.startswith(needle) or needle.startswith(name[:28]):
                    speaker = candidate
                    break
            if speaker is None:
                speaker = sc.default_speaker()
            if speaker is None:
                return

            mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
            if mic is None:
                print(f"[LiveMonitor] '{speaker.name}' no admite loopback")
                return

            channels = max(1, min(AUDIO_MAX_CHANNELS, mic.channels or AUDIO_MAX_CHANNELS))

            with self._lock:
                self._running[label] = True

            def _capture():
                try:
                    with mic.recorder(
                        samplerate=AUDIO_SAMPLE_RATE,
                        channels=channels,
                        blocksize=AUDIO_CHUNK_SIZE,
                    ) as recorder:
                        while self._running.get(label, False):
                            data = recorder.record(numframes=AUDIO_CHUNK_SIZE)
                            rms = float(np.sqrt(np.mean(data.astype(np.float64) ** 2)))
                            level = min(1.0, rms * 3.0)
                            with self._lock:
                                self._levels[label] = level
                except Exception as exc:
                    print(f"[LiveMonitor] error loopback '{label}': {exc}")

            t = threading.Thread(target=_capture, name=f"live-monitor-{label}", daemon=True)
            t.start()
            with self._lock:
                self._threads[label] = t
                self._levels[label] = 0.0
        except Exception as exc:
            print(f"[LiveMonitor] no se pudo abrir parlante: {exc}")

    def stop(self):
        with self._lock:
            for label in list(self._running):
                self._running[label] = False
        for t in self._threads.values():
            t.join(timeout=2)
        self._threads.clear()

        with self._lock:
            for stream in self._streams.values():
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
            self._streams.clear()
            self._levels.clear()

    def get_levels(self):
        with self._lock:
            return dict(self._levels)
