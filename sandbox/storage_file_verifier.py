import json
from collections import defaultdict

def validar_storage(file_path="storage.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=== Validación de storage.json ===")
    print(f"Total de categorías: {len(data)}\n")

    for categoria, subcats in data.items():
        print(f"📦 Categoría: {categoria}")
        print(f"  Subcategorías: {len(subcats)}")

        total_acciones_cat = 0
        for subcat, acciones in subcats.items():
            num_acciones = len(acciones)
            total_acciones_cat += num_acciones
            print(f"    - {subcat}: {num_acciones} acciones")

        print(f"  Total acciones en '{categoria}': {total_acciones_cat}\n")

if __name__ == "__main__":
    validar_storage("actions/storage copy 2.json")
