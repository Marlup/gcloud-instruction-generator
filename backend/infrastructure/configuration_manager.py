import os
import json
from typing import Dict, Any, Optional

from google.cloud import storage as gcs
from google.oauth2.service_account import Credentials
from google.api_core.exceptions import GoogleAPIError

from backend.constants import GCP_CREDENTIALS_FILENAME

class ConfigurationManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None, plugins_path: str = "plugins", on_connect: bool = True):
        self.config: Dict[str, Any] = config or {}
        self.plugins_path = plugins_path
        self._client: Optional[gcs.Client] = None
        self._credentials: Optional[Credentials] = None

        if on_connect:
            try:
                self.connect()
            except Exception as e:
                print(f"⚠️ Advertencia: No se pudo conectar a GCP: {e}")

    # -------- Properties --------
    @property
    def project(self) -> str:
        return self.config.get("project_id", "")

    @property
    def credentials(self) -> Optional[Credentials]:
        return self._credentials

    @property
    def client(self) -> Optional[gcs.Client]:
        return self._client

    # -------- Connection --------
    def connect(self):
        cred_path = os.path.join("config", GCP_CREDENTIALS_FILENAME)
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"❌ No se encontró el archivo de credenciales: {cred_path}")

        self._credentials = Credentials.from_service_account_file(cred_path)
        self._client = gcs.Client(project=self.project, credentials=self._credentials)
        return self._client

    def ping(self) -> bool:
        try:
            if not self._client:
                self.connect()
            list(self._client.list_buckets(page_size=1))
            return True
        except GoogleAPIError:
            return False

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
    def load_actions(self, service_name: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Carga TODAS las acciones de un servicio:
        plugins/service/resource/category/*.json
        """
        service_path = os.path.join(self.plugins_path, service_name)
        if not os.path.isdir(service_path):
            raise FileNotFoundError(f"❌ No existe carpeta de servicio: {service_path}")

        actions: Dict[str, Dict[str, Dict[str, Any]]] = {}

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
                    if not filename.endswith(".json"):
                        continue
                    file_path = os.path.join(category_path, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        action_data = json.load(f)

                    # We assume format: {"Action name": {"cmd": "...", "params": [...]}}
                    actions[resource][category].update(action_data)

        return actions

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
