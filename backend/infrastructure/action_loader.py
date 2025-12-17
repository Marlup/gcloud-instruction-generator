import os
import json
import logging
from typing import List, Dict

logging.getLogger(__name__)

class ActionLoader:

    def __init__(self, service_path: str):
        self.service_path = service_path
        self.actions = self._load_actions()

    def _load_actions(self) -> Dict[str, Dict[str, dict]]:
        """
        Carga todas las acciones desde la estructura:
        service-dir/resource-dir/category-json-file
        """
        actions: Dict[str, Dict[str, dict]] = {}


        logging.info(f"Starting loading actions {self.service_path}")
        for resource in os.listdir(self.service_path):
            resource_path = os.path.join(self.service_path, resource)
            if not os.path.isdir(resource_path):
                continue

            actions[resource] = self._load_resource(resource_path)

        return actions

    def _load_resource(self, resource_path: str) -> Dict[str, Dict[str, dict]]:
        """
        Carga todas las categorías dentro de un recurso.
        Soporta:
        1. Directorios de categoría (legacy): resource/category/action.json
        2. Archivos de categoría (current): resource/category.json
        """
        categories: Dict[str, Dict[str, dict]] = {}

        for entry in os.listdir(resource_path):
            entry_path = os.path.join(resource_path, entry)
            
            # Case 1: Directory (folder for category)
            if os.path.isdir(entry_path):
                categories[entry] = self._load_category(entry_path)
            
            # Case 2: JSON file (category file)
            elif entry.endswith(".json"):
                # category name is filename without extension
                category = os.path.splitext(entry)[0]
                try:
                    with open(entry_path, "r", encoding="utf-8") as f:
                        categories[category] = json.load(f)
                except Exception as e:
                    logging.error(f"Error loading category file {entry_path}: {e}")

        return categories

    def _load_category(self, category_path: str) -> Dict[str, dict]:
        """
        Carga todas las acciones de una categoría (archivos JSON).
        """
        actions: Dict[str, dict] = {}

        for filename in os.listdir(category_path):
            if not filename.endswith(".json"):
                continue
            file_path = os.path.join(category_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                action_data = json.load(f)
                actions.update(action_data)

        return actions

    def list_actions(self, on_categories: bool = True) -> List[str] | Dict[str, List[str]]:
        """
        Devuelve una lista de acciones soportadas por el servicio.

        - Si `on_categories=True`: 
          {
            "Recurso / Categoría": ["Acción1", "Acción2"]
          }

        - Si `on_categories=False`:
          ["Acción1", "Acción2", ...]
        """
        if on_categories:
            result: Dict[str, List[str]] = {}
            for resource, categories in self.actions.items():
                for category, actions in categories.items():
                    key = f"{resource} / {category}"
                    result[key] = list(actions.keys())
            return result
        else:
            result: List[str] = []
            for resource, categories in self.actions.items():
                for category, actions in categories.items():
                    result.extend(actions.keys())
            return result
