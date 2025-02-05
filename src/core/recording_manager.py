from datetime import datetime
import os
import cv2
import sounddevice as sd
import wave
import numpy as np
from ..utils.async_utils import ProcessManager, AsyncWorker
from ..config.settings import (
    VIDEO_FPS,
    VIDEO_CODEC,
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHUNK_SIZE
)

class RecordingManager:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.process_manager = ProcessManager()
        self.is_recording = False
        self.current_recording = None
        self.video_writer = None
        self.audio_streams = {}
        self.wav_files = {}

    async def start_recording(self, monitor, selected_speakers, selected_mics):
        """Inicia la grabación."""
        if self.is_recording:
            return False

        try:
            print("\n=== Iniciando grabación ===")
            
            # Crear directorios y nombres de archivo
            date_folder = datetime.now().strftime("%Y-%m-%d")
            recording_dir = os.path.join(self.output_dir, date_folder)
            os.makedirs(recording_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%H-%M-%S")
            filename_base = os.path.join(recording_dir, f"recording_{timestamp}")
            
            print(f"Directorio de grabación: {recording_dir}")
            print(f"Nombre base del archivo: {os.path.basename(filename_base)}")
            
            # Inicializar grabación de video
            video_file = f"{filename_base}_temp.avi"
            print(f"\nCreando archivo de video: {os.path.basename(video_file)}")
            
            self.video_writer = cv2.VideoWriter(
                video_file,
                cv2.VideoWriter_fourcc(*VIDEO_CODEC),
                VIDEO_FPS,
                (monitor['width'], monitor['height'])
            )

            if not self.video_writer.isOpened():
                raise Exception("No se pudo crear el archivo de video")
            print("✓ Video writer inicializado correctamente")

            # Inicializar grabación de audio
            print("\nIniciando grabación de audio...")
            self.is_recording = True
            
            if selected_mics:
                print(f"\nIniciando grabación de micrófono: {selected_mics[0]['name']}")
                self._init_microphone(filename_base, selected_mics[0]['id'])
                print("✓ Grabación de micrófono iniciada")
                
            if selected_speakers:
                print(f"\nIniciando grabación de audio del sistema: {selected_speakers[0]['name']}")
                self._init_system_audio(filename_base, selected_speakers[0]['id'])
                print("✓ Grabación de audio del sistema iniciada")

            self.current_recording = {
                'video': video_file,
                'mic': f"{filename_base}_mic.wav" if selected_mics else None,
                'speakers': f"{filename_base}_speakers.wav" if selected_speakers else None,
                'final': f"{filename_base}.avi"
            }

            print("\n✓ Grabación iniciada correctamente")
            return True

        except Exception as e:
            print(f"\n✗ Error al iniciar grabación: {str(e)}")
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            return False

    def _init_microphone(self, filename_base, mic_id):
        """Inicializa la grabación del micrófono."""
        try:
            self.wav_files['mic'] = wave.open(f"{filename_base}_mic.wav", 'wb')
            self.wav_files['mic'].setnchannels(AUDIO_CHANNELS)
            self.wav_files['mic'].setsampwidth(2)
            self.wav_files['mic'].setframerate(AUDIO_SAMPLE_RATE)

            def mic_callback(indata, frames, time, status):
                if status:
                    print(f"Estado del micrófono: {status}")
                if self.is_recording and len(indata) > 0:
                    try:
                        data = (indata * 32767).astype(np.int16)
                        self.wav_files['mic'].writeframes(data.tobytes())
                    except Exception as e:
                        print(f"Error en callback de micrófono: {str(e)}")

            self.audio_streams['mic'] = sd.InputStream(
                device=mic_id,
                channels=AUDIO_CHANNELS,
                callback=mic_callback,
                samplerate=AUDIO_SAMPLE_RATE,
                blocksize=AUDIO_CHUNK_SIZE,
                dtype=np.float32
            )
            self.audio_streams['mic'].start()

        except Exception as e:
            print(f"Error al inicializar micrófono: {str(e)}")
            if 'mic' in self.wav_files:
                self.wav_files['mic'].close()
                del self.wav_files['mic']

    def _init_system_audio(self, filename_base, speaker_id):
        """Inicializa la grabación del audio del sistema."""
        try:
            self.wav_files['speakers'] = wave.open(f"{filename_base}_speakers.wav", 'wb')
            self.wav_files['speakers'].setnchannels(AUDIO_CHANNELS)
            self.wav_files['speakers'].setsampwidth(2)
            self.wav_files['speakers'].setframerate(AUDIO_SAMPLE_RATE)

            def speaker_callback(indata, frames, time, status):
                if status:
                    print(f"Estado del audio del sistema: {status}")
                if self.is_recording and len(indata) > 0:
                    try:
                        data = (indata * 32767).astype(np.int16)
                        self.wav_files['speakers'].writeframes(data.tobytes())
                    except Exception as e:
                        print(f"Error en callback de audio del sistema: {str(e)}")

            # Buscar dispositivo de loopback
            loopback_device = None
            for i, dev in enumerate(sd.query_devices()):
                if ('stereo mix' in dev['name'].lower() or 
                    'what u hear' in dev['name'].lower() or
                    'voicemeeter' in dev['name'].lower()):
                    loopback_device = i
                    break

            if loopback_device is None:
                loopback_device = speaker_id

            self.audio_streams['speakers'] = sd.InputStream(
                device=loopback_device,
                channels=AUDIO_CHANNELS,
                callback=speaker_callback,
                samplerate=AUDIO_SAMPLE_RATE,
                blocksize=AUDIO_CHUNK_SIZE,
                dtype=np.float32
            )
            self.audio_streams['speakers'].start()

        except Exception as e:
            print(f"Error al inicializar audio del sistema: {str(e)}")
            if 'speakers' in self.wav_files:
                self.wav_files['speakers'].close()
                del self.wav_files['speakers']

    async def stop_recording(self):
        """Detiene la grabación."""
        if not self.is_recording:
            return False

        try:
            print("\n=== Deteniendo grabación ===")
            self.is_recording = False

            # Detener streams de audio
            print("\nDeteniendo streams de audio...")
            for stream in self.audio_streams.values():
                stream.stop()
                stream.close()
            self.audio_streams.clear()
            print("✓ Streams de audio detenidos")

            # Cerrar archivos WAV
            print("\nCerrando archivos de audio...")
            for wav_file in self.wav_files.values():
                wav_file.close()
            self.wav_files.clear()
            print("✓ Archivos de audio cerrados")

            # Cerrar video writer
            print("\nCerrando archivo de video...")
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            print("✓ Archivo de video cerrado")

            # Verificar archivos
            print("\nVerificando archivos generados:")
            for key, path in self.current_recording.items():
                if path and os.path.exists(path):
                    size = os.path.getsize(path)
                    print(f"✓ {key}: {os.path.basename(path)} ({size} bytes)")
                elif path:
                    print(f"✗ {key}: Archivo no encontrado - {os.path.basename(path)}")

            # Combinar audio y video
            if self.current_recording:
                print("\nCombinando audio y video...")
                await self._combine_audio_video()

            print("\n✓ Grabación finalizada correctamente")
            return True

        except Exception as e:
            print(f"\n✗ Error al detener grabación: {str(e)}")
            return False

    async def _combine_audio_video(self):
        """Combina audio y video de manera asíncrona."""
        from ..utils.video_utils import combine_audio_video
        
        try:
            audio_files = []
            if self.current_recording['mic'] and os.path.exists(self.current_recording['mic']):
                audio_files.append(self.current_recording['mic'])
            if self.current_recording['speakers'] and os.path.exists(self.current_recording['speakers']):
                audio_files.append(self.current_recording['speakers'])

            # Ejecutar la combinación en un worker separado
            worker = AsyncWorker(
                combine_audio_video,
                self.current_recording['video'],
                audio_files,
                self.current_recording['final']
            )
            worker.start()
            worker.wait()  # Esperar a que termine

        except Exception as e:
            print(f"Error al combinar audio y video: {str(e)}")
            # En caso de error, mantener el video temporal
            if os.path.exists(self.current_recording['video']):
                os.rename(self.current_recording['video'], self.current_recording['final'])

    def write_frame(self, frame):
        """Escribe un frame al video si está grabando."""
        if self.is_recording and self.video_writer:
            try:
                # Asegurarse de que el frame esté en BGR
                if frame.shape[-1] == 4:  # Si es BGRA
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                self.video_writer.write(frame)
                return True
            except Exception as e:
                print(f"Error al escribir frame: {str(e)}")
                return False
        return False

    def cleanup(self):
        """Limpia todos los recursos."""
        self.process_manager.stop_all()
        if self.video_writer:
            self.video_writer.release()
        for stream in self.audio_streams.values():
            stream.stop()
            stream.close()
        for wav_file in self.wav_files.values():
            wav_file.close() 