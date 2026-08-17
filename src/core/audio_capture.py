"""Pistas de audio: micrófono y audio del sistema (loopback WASAPI).

Ambas capturas usan PortAudio con callbacks que solo encolan; el disco se toca
desde un hilo aparte para que el hilo de audio en tiempo real nunca se bloquee.
"""
import queue
import threading
import time
import wave

import numpy as np
import sounddevice as sd

from ..config.settings import (
    AUDIO_CHUNK_SIZE,
    AUDIO_MAX_CHANNELS,
    AUDIO_QUEUE_MAX,
    AUDIO_SAMPLE_RATE,
)

_SILENCE_GAP_SECONDS = 0.2


class AudioError(Exception):
    """Fallo de audio que debe mostrarse al usuario en lugar de silenciarse."""


def loopback_backend_available():
    try:
        import pyaudiowpatch
        return True
    except Exception:
        return False


def find_loopback_device(speaker_name=None):
    """Índice y datos del dispositivo de loopback de la salida indicada.

    Windows expone cada salida como un dispositivo de entrada '[Loopback]'.
    Se busca el que corresponde al altavoz elegido y, si no aparece, el
    predeterminado del sistema.
    """
    import pyaudiowpatch as pa

    audio = pa.PyAudio()
    try:
        candidates = list(audio.get_loopback_device_info_generator())
        if not candidates:
            raise AudioError(
                "Windows no expone ningún dispositivo de loopback para grabar "
                "el audio del sistema."
            )

        if speaker_name:
            needle = speaker_name[:28].lower()
            for device in candidates:
                if device['name'].lower().startswith(needle):
                    return dict(device)

        try:
            return dict(audio.get_default_wasapi_loopback())
        except Exception:
            return dict(candidates[0])
    finally:
        audio.terminate()


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
        self._muted = False
        self._channels = 1
        self._samplerate = AUDIO_SAMPLE_RATE
        self.volume = 1.0
        self.boost = 1.0
        self.level = 0.0
        self._level_lock = threading.Lock()

    @property
    def gain(self):
        """Ganancia total: el volumen elegido más el refuerzo fijo de la pista."""
        return self.volume * self.boost

    @property
    def is_paused(self):
        return self._paused

    def set_paused(self, paused):
        self._paused = paused

    @property
    def is_muted(self):
        return self._muted

    def set_muted(self, muted):
        self._muted = bool(muted)

    def get_level(self):
        with self._level_lock:
            return self.level

    def _update_level(self, block):
        rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
        with self._level_lock:
            self.level = min(1.0, rms * 3.0)

    def _open_wav(self, channels, samplerate):
        self._channels = channels
        self._samplerate = int(samplerate)
        self._wav = wave.open(self.path, 'wb')
        self._wav.setnchannels(channels)
        self._wav.setsampwidth(2)
        self._wav.setframerate(self._samplerate)
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

    def _write_block(self, block):
        self._update_level(block)
        if self._paused:
            return 0
        if self._muted:
            block = np.zeros_like(block)
            self._wav.writeframes(block.astype(np.int16).tobytes())
        else:
            data = np.clip(block * self.gain, -1.0, 1.0)
            self._wav.writeframes((data * 32767).astype(np.int16).tobytes())
        return len(block)

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
                self._write_block(block)
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

    WASAPI no entrega nada mientras no suena audio, así que el escritor rellena
    los huecos con silencio contra el reloj real; de lo contrario el WAV sería
    más corto que el vídeo y todo quedaría desincronizado.
    """

    def __init__(self, label, speaker_name, path):
        super().__init__(label, path)
        self._speaker_name = speaker_name
        self._audio = None
        self._stream = None
        self._frames_written = 0

    def start(self):
        if not loopback_backend_available():
            raise AudioError(
                "Falta el paquete 'pyaudiowpatch', necesario para grabar el "
                "audio del sistema.\nInstálalo con: pip install PyAudioWPatch"
            )

        import pyaudiowpatch as pa

        device = find_loopback_device(self._speaker_name)
        channels = max(1, min(AUDIO_MAX_CHANNELS, int(device['maxInputChannels'])))
        rate = int(device['defaultSampleRate'])

        self._open_wav(channels, rate)
        self._frames_written = 0

        def callback(in_data, frame_count, time_info, status):
            if self._running and in_data:
                block = np.frombuffer(in_data, dtype=np.float32)
                if block.size:
                    self._submit(block.reshape(-1, channels).copy())
            return (None, pa.paContinue)

        try:
            self._audio = pa.PyAudio()
            self._stream = self._audio.open(
                format=pa.paFloat32,
                channels=channels,
                rate=rate,
                input=True,
                frames_per_buffer=AUDIO_CHUNK_SIZE,
                input_device_index=device['index'],
                stream_callback=callback,
            )
            self.started_at = time.perf_counter()
        except Exception as exc:
            self._running = False
            self._close_wav()
            self._release()
            raise AudioError(
                f"No se pudo abrir el loopback de '{device['name']}': {exc}"
            ) from exc

        print(f"[ok] {self.label}: {device['name']} ({channels} ch, {rate} Hz)")

    def _write_block(self, block):
        written = super()._write_block(block)
        self._frames_written += written
        return written

    def _drain(self):
        """Escribe lo que llega y rellena con silencio los tramos sin sonido."""
        while True:
            try:
                block = self._queue.get(timeout=0.1)
            except queue.Empty:
                block = None
                if not self._running:
                    self._pad_to_clock()
                    return
            if block is None:
                self._pad_to_clock()
                continue
            try:
                self._write_block(block)
            except Exception as exc:
                print(f"[{self.label}] error al escribir audio: {exc}")
                return

    def _pad_to_clock(self):
        if self._wav is None or self.started_at is None or self._paused:
            return
        elapsed = time.perf_counter() - self.started_at
        missing = int(elapsed * self._samplerate) - self._frames_written
        if missing < int(_SILENCE_GAP_SECONDS * self._samplerate):
            return
        try:
            silence = np.zeros((missing, self._channels), dtype=np.int16)
            self._wav.writeframes(silence.tobytes())
            self._frames_written += missing
            with self._level_lock:
                self.level = 0.0
        except Exception as exc:
            print(f"[{self.label}] error al rellenar silencio: {exc}")

    def _release(self):
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as exc:
                print(f"[{self.label}] error al cerrar el loopback: {exc}")
            self._stream = None
        if self._audio is not None:
            try:
                self._audio.terminate()
            except Exception:
                pass
            self._audio = None

    def stop(self):
        self._running = False
        self._release()
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
    """Mide niveles de audio en vivo sin grabar nada."""

    def __init__(self):
        self._streams = {}
        self._loopback = None
        self._levels = {}
        self._lock = threading.Lock()

    def start(self, mic_device_id=None, speaker_device_id=None):
        self.stop()
        if mic_device_id is not None:
            self._add_input_stream('mic', mic_device_id)
        if speaker_device_id is not None:
            self._add_loopback_stream('speakers', speaker_device_id)

    def _set_level(self, label, samples):
        rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        with self._lock:
            self._levels[label] = min(1.0, rms * 3.0)

    def _add_input_stream(self, label, device_id):
        try:
            info = sd.query_devices(device_id)
            channels = max(1, min(AUDIO_MAX_CHANNELS,
                                  int(info.get('max_input_channels', 1))))

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
                self._set_level(_label, indata)

            stream = sd.InputStream(
                device=device_id, channels=channels, samplerate=rate,
                blocksize=AUDIO_CHUNK_SIZE, dtype='float32', callback=callback,
            )
            stream.start()
            with self._lock:
                self._streams[label] = stream
                self._levels[label] = 0.0
        except Exception as exc:
            print(f"[LiveMonitor] no se pudo abrir el micrófono: {exc}")

    def _add_loopback_stream(self, label, speaker_device_id):
        if not loopback_backend_available():
            return

        try:
            import pyaudiowpatch as pa

            speaker_name = sd.query_devices(speaker_device_id)['name']
            device = find_loopback_device(speaker_name)
            channels = max(1, min(AUDIO_MAX_CHANNELS,
                                  int(device['maxInputChannels'])))

            def callback(in_data, frame_count, time_info, status, _label=label):
                if in_data:
                    block = np.frombuffer(in_data, dtype=np.float32)
                    if block.size:
                        self._set_level(_label, block)
                return (None, pa.paContinue)

            audio = pa.PyAudio()
            stream = audio.open(
                format=pa.paFloat32,
                channels=channels,
                rate=int(device['defaultSampleRate']),
                input=True,
                frames_per_buffer=AUDIO_CHUNK_SIZE,
                input_device_index=device['index'],
                stream_callback=callback,
            )
            self._loopback = (audio, stream)
            with self._lock:
                self._levels[label] = 0.0
        except Exception as exc:
            print(f"[LiveMonitor] no se pudo abrir el loopback: {exc}")

    def stop(self):
        if self._loopback is not None:
            audio, stream = self._loopback
            self._loopback = None
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
            try:
                audio.terminate()
            except Exception:
                pass

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
