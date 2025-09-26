import os
import json
from typing import Dict

def load_actions_from_fs(service_path: str, on_save: bool=False) -> Dict[str, Dict[str, Dict[str, dict]]]:
    """
    Construye el diccionario de acciones desde:
    service_path/resource/category/*.json

    Devuelve:
    {
      "Recurso": {
        "Categoría": {
          "Acción": {"cmd": "...", "params": [...]}
        }
      }
    }
    """
    actions: Dict[str, Dict[str, Dict[str, dict]]] = {}

    print("Cargando acciones desde:", service_path)
    for resource in os.listdir(service_path):
        resource_path = os.path.join(service_path, resource)
        if not os.path.isdir(resource_path):
            continue

        actions[resource] = {}

        for category in os.listdir(resource_path):
            category_path = os.path.join(resource_path, category)
            if not os.path.isdir(category_path):
                continue

            actions[resource][category] = {}

            for filename in os.listdir(category_path):
                print("filename:", filename)
                if not filename.endswith(".json"):
                    continue

                #action_name = os.path.splitext(filename)[0].replace("_", " ").capitalize()
                file_path = os.path.join(category_path, filename)

                with open(file_path, "r", encoding="utf-8") as f:
                    action_data = json.load(f)


                print(f"Cargando acción: {resource} / {category} desde {file_path}")

                # asumimos que el JSON ya viene con {"cmd": ..., "params": [...]}
                actions[resource][category].update(action_data)

    if on_save:
        with open(os.path.join(service_path, "actions.json"), "w", encoding="utf-8") as f:
            json.dump(actions, f, indent=2, ensure_ascii=False)
    return actions


def main():
    actions = load_actions_from_fs("plugins/storage", on_save=True)

if __name__ == "__main__":
    main()