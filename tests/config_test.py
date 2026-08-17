"""Pruebas de la configuracion persistente: round-trip, corrupcion y migracion."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))

import json
import os
import shutil
import tempfile

from src.config import user_config

WORKDIR = tempfile.mkdtemp(prefix="srconfig_")
CONFIG = os.path.join(WORKDIR, "config.json")
STATE = os.path.join(WORKDIR, "state.json")

user_config.config_path = lambda: CONFIG
user_config.state_path = lambda: STATE

passed, failed = 0, 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ok   {name}")
    else:
        failed += 1
        print(f"  FALLA {name} {detail}")


def write(raw):
    with open(CONFIG, 'w', encoding='utf-8') as handle:
        handle.write(raw)


print("sin archivo -> valores por defecto")
if os.path.exists(CONFIG):
    os.remove(CONFIG)
config = user_config.load()
check("devuelve defaults", config == user_config.defaults())
check("no crea el archivo al leer", not os.path.exists(CONFIG))

print("\nround-trip")
config['audio']['mic_volume'] = 0.42
config['audio']['mic_muted'] = True
config['audio']['speaker_device'] = "Altavoces (Test)"
config['monitor']['index'] = 1
user_config.save(config)
loaded = user_config.load()
check("volumen persiste", loaded['audio']['mic_volume'] == 0.42)
check("mute persiste", loaded['audio']['mic_muted'] is True)
check("dispositivo persiste", loaded['audio']['speaker_device'] == "Altavoces (Test)")
check("monitor persiste", loaded['monitor']['index'] == 1)

print("\narchivo corrupto")
write("{ esto no es json ")
loaded = user_config.load()
check("no lanza y usa defaults", loaded['audio']['mic_volume'] == 1.0)
check("aparta un .bak", os.path.exists(CONFIG + '.bak'))

print("\ntipo equivocado en la raiz")
write('["una", "lista"]')
loaded = user_config.load()
check("lista rechazada", loaded == user_config.defaults())

print("\nvalores fuera de rango")
write(json.dumps({
    "schema_version": 1,
    "video": {"fps": 9999, "codec": "NO", "capture_cursor": "si"},
    "preview": {"fps": -3, "max_width": 99999},
    "audio": {"mic_volume": 50, "speaker_volume": "alto", "mic_muted": "true"},
    "monitor": {"index": -7},
    "output_dir": "",
}))
loaded = user_config.load()
base = user_config.defaults()
check("fps corregido", loaded['video']['fps'] == base['video']['fps'])
check("codec corregido", loaded['video']['codec'] == base['video']['codec'])
check("cursor corregido", loaded['video']['capture_cursor'] is True)
check("preview fps corregido", loaded['preview']['fps'] == base['preview']['fps'])
check("volumen corregido", loaded['audio']['mic_volume'] == 1.0)
check("volumen no numerico corregido", loaded['audio']['speaker_volume'] == 1.0)
check("mute no booleano corregido", loaded['audio']['mic_muted'] is False)
check("monitor corregido", loaded['monitor']['index'] == 0)
check("output_dir corregido", loaded['output_dir'] == base['output_dir'])

print("\nmigracion desde v0")
write(json.dumps({"audio": {"mic_volume": 0.7}}))
loaded = user_config.load()
check("schema actualizado", loaded['schema_version'] == user_config.SCHEMA_VERSION)
check("valor antiguo conservado", loaded['audio']['mic_volume'] == 0.7)
check("claves nuevas rellenadas", 'speaker_muted' in loaded['audio'])

print("\nclaves desconocidas de una version mas nueva")
write(json.dumps({"schema_version": 1, "futuro": {"algo": 1}}))
loaded = user_config.load()
check("clave desconocida conservada", loaded.get('futuro') == {"algo": 1})
user_config.save(loaded)
check("y sobrevive al guardado", user_config.load().get('futuro') == {"algo": 1})

print("\ndispositivo desactivado explicitamente")
write(json.dumps({"schema_version": 1, "audio": {"mic_device": None}}))
loaded = user_config.load()
check("None se conserva (no grabar)", loaded['audio']['mic_device'] is None)

print("\nestado de ventana")
user_config.save_state({"window": {"x": 10, "y": 20, "width": 800, "height": 600}})
check("estado persiste", user_config.load_state()['window']['width'] == 800)

print("\nescritura atomica")
before = set(os.listdir(WORKDIR))
user_config.save(user_config.defaults())
after = set(os.listdir(WORKDIR))
check("no deja temporales", not [f for f in after - before if f.endswith('.tmp')])

print("\npurge en modo consulta")
targets = user_config.purge_targets()
check("purge_targets no borra nada", os.path.exists(CONFIG))
check("devuelve tuplas (ruta, tamano)",
      all(isinstance(t, tuple) and len(t) == 2 for t in targets))

shutil.rmtree(WORKDIR, ignore_errors=True)
print(f"\n{passed} ok, {failed} fallos")
_sys.exit(1 if failed else 0)
