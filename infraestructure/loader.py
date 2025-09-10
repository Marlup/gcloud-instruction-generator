import json
import os

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_actions(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    _, ext = os.path.splitext(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        if ext == ".json":
            data = json.load(f)
        elif ext in [".yml", ".yaml"]:
            if not HAS_YAML:
                raise ImportError("pyyaml no está instalado. Ejecuta: pip install pyyaml")
            data = yaml.safe_load(f)
        else:
            raise ValueError(f"Formato no soportado: {ext}")

    actions = {}
    for category, items in data.items():
        for action, details in items.items():
            actions[action] = {
                "cmd": details["cmd"],
                "params": {p: f"<{p}>" for p in details.get("params", [])}
            }

    return actions


def load_list(file_path: str, key: str) -> list:
    """Carga una lista (ej. regiones o storage_classes) desde JSON."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if key not in data:
        raise KeyError(f"El archivo {file_path} no contiene la clave esperada '{key}'")

    return data[key]
