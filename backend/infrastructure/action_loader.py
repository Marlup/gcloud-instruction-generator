from typing import List, Dict
import os
import json

class ActionLoader:

    def __init__(self, service_path: str):
        self.service_path = service_path
        self.actions = self._load_actions()

    def _load_actions(self) -> Dict[str, Dict[str, Dict[str, dict]]]:
        """
        Carga todas las acciones desde la estructura:
        service-dir/resource-dir/category-dir/*.json
        """
        actions: Dict[str, Dict[str, Dict[str, dict]]] = {}

        for resource in os.listdir(self.service_path):
            resource_path = os.path.join(self.service_path, resource)
            if not os.path.isdir(resource_path):
                continue

            actions[resource] = self._load_resource(resource_path)

        return actions

    def _load_resource(self, resource_path: str) -> Dict[str, Dict[str, dict]]:
        """
        Carga todas las categorías dentro de un recurso.
        """
        categories: Dict[str, Dict[str, dict]] = {}

        for category in os.listdir(resource_path):
            category_path = os.path.join(resource_path, category)
            if not os.path.isdir(category_path):
                continue

            categories[category] = self._load_category(category_path)

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
