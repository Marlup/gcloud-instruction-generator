import os
import json
from typing import Dict, Any, Optional

from backend.constants import GCP_CREDENTIALS_FILENAME
from backend.infrastructure.action_loader import ActionLoader

class ConfigurationManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None, plugins_path: str = "data/plugins"):
        self.config: Dict[str, Any] = config or {}
        self.plugins_path = plugins_path

    # -------- Properties --------
    @property
    def project(self) -> str:
        return self.config.get("project_id", "")

    # -------- Configuración --------
    def load_configuration(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ No se encontró configuración: {path}")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    self.config[k.strip()] = v.strip()
        return self

    # -------- Actions --------
    def load_actions(self, service_name: str) -> Dict[str, Any]:
        """
        Carga TODAS las acciones de un servicio usando ActionLoader.
        Soporta formato plano (actions.json) y legado.
        """
        service_path = os.path.join(self.plugins_path, service_name)
        if not os.path.isdir(service_path):
            print(f"❌ No existe carpeta de servicio: {service_path}")
            return {}

        loader = ActionLoader(service_path)
        return loader.actions

    # -------- Parámetros --------
    def load_parameters(self, service_name: str) -> dict:
        params_dir = "params"
        params = {}
        if not os.path.isdir(params_dir):
            return params

        for filename in os.listdir(params_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(params_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            params.update(data)
        return params
