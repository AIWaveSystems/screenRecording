"""Mezcla del vídeo temporal con las pistas de audio mediante FFmpeg."""
import glob
import os
import shutil
import subprocess
import sys

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

_COMMON_FFMPEG_PATHS = (
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    os.path.join(os.path.expanduser('~'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
)


def find_ffmpeg():
    """Ruta a ffmpeg: PATH, binario de imageio-ffmpeg o ubicaciones habituales.

    imageio-ffmpeg trae un ffmpeg estático, así que la app funciona recién
    instalada sin obligar al usuario a configurar el PATH a mano.
    """
    found = shutil.which('ffmpeg')
    if found:
        return found
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    for folder in (getattr(sys, '_MEIPASS', None),
                   os.path.dirname(sys.executable)):
        if not folder:
            continue
        matches = sorted(glob.glob(os.path.join(folder, 'ffmpeg*.exe')))
        if matches:
            return matches[0]
    for path in _COMMON_FFMPEG_PATHS:
        if os.path.exists(path):
            return path
    return None


def _rename_fallback(video_file, output_file, reason):
    """Conserva el vídeo sin audio cuando la mezcla no es posible."""
    try:
        if os.path.exists(output_file):
            os.remove(output_file)
        os.replace(video_file, output_file)
        return False, f"{reason} Se guardó el vídeo sin audio: {output_file}"
    except OSError as exc:
        return False, f"{reason} Además falló al renombrar el temporal: {exc}"


def combine_audio_video(video_file, audio_files, output_file):
    """Mezcla las pistas de audio en el vídeo. Devuelve (ok, mensaje).

    `audio_files` son pares (ruta, desfase en segundos respecto al inicio del
    vídeo); ese desfase se compensa para que la sincronía sea exacta. El vídeo
    se copia tal cual (`-c:v copy`): no se recodifica, así que la operación
    tarda segundos en lugar de tanto como la propia grabación.
    """
    if not os.path.exists(video_file):
        return False, f"No se encuentra el vídeo temporal: {video_file}"

    valid_audio = [
        (path, offset) for path, offset in audio_files
        if os.path.exists(path) and os.path.getsize(path) > 44
    ]

    if not valid_audio:
        return _rename_fallback(video_file, output_file, "No hay audio que mezclar.")

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        return _rename_fallback(
            video_file, output_file,
            "FFmpeg no está instalado o no está en el PATH.",
        )

    cmd = [ffmpeg, '-y', '-i', video_file]
    for path, offset in valid_audio:
        if offset > 0.005:
            cmd.extend(['-itsoffset', f"{offset:.3f}"])
        elif offset < -0.005:
            cmd.extend(['-ss', f"{-offset:.3f}"])
        cmd.extend(['-i', path])

    if len(valid_audio) > 1:
        inputs = ''.join(f'[{i + 1}:a]' for i in range(len(valid_audio)))
        cmd.extend([
            '-filter_complex',
            f'{inputs}amix=inputs={len(valid_audio)}:duration=longest:normalize=0[a]',
            '-map', '0:v', '-map', '[a]',
        ])
    else:
        cmd.extend(['-map', '0:v', '-map', '1:a'])

    cmd.extend([
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        output_file,
    ])

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=_CREATE_NO_WINDOW,
        )
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or '').strip().splitlines()[-3:]
        return _rename_fallback(
            video_file, output_file,
            "FFmpeg falló: " + ' | '.join(tail),
        )
    except OSError as exc:
        return _rename_fallback(video_file, output_file, f"No se pudo ejecutar FFmpeg: {exc}")

    for temp in [video_file, *(path for path, _ in valid_audio)]:
        try:
            os.remove(temp)
        except OSError as exc:
            print(f"No se pudo borrar el temporal {temp}: {exc}")

    return True, f"[ok] Grabación guardada en {output_file}"
