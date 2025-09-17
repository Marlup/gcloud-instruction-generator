import os
import json
from typing import Dict
import logging

from backend.services.base_service import BaseGCloudService

# Google Credential base class
from google.oauth2.service_account import Credentials

from backend.constants import (
    ACTIONS_FILENAME,
    GCP_CREDENTIALS_FILENAME,
    PARAMETERS_FILENAME
)

class ConfigurationManager():
    
    def __init__(self, config: Dict = {}, plugins_path: str = "plugins", on_connect: bool = True):
        self.config = config
        self.plugins_path = plugins_path
        self._credentials = None

        
        # Cloud connection
        if on_connect:
            self.load_credentials()

        # Services
        self.services_names = []
        self.get_services()

    # -------- Properties --------
    @property
    def project(self) -> str:
        return self.config.get("project_id", "")

    @property
    def credentials(self) -> Credentials:
        return self._credentials

    # -------- Connection --------
    def ping(self) -> bool:
        try:
            self._client.project  # fuerza acceso
            return True
        except Exception:
            return False

    # -------- Loading methods --------
    
    # configuration
    def load_configuration(self, path: str):
        with open(path, "r") as f:
            for param in f.readlines():
                k, v = param.split("=")
                self.config[k] = v
        return self

    # actions
    def load_actions(self, service_name: str):
        actions_path = os.path.join(self.plugins_path, service_name, ACTIONS_FILENAME)
        with open(actions_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # parameters
    def load_parameters(self, service_name: str):
        parameters_path = os.path.join(self.plugins_path, service_name, PARAMETERS_FILENAME)
        with open(parameters_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
        # -------- Load credentials --------
    def load_credentials(self):
        try:
            return self._load_credentials()
        except Exception as e:
            logging.warning("ConfigurationManager - load_credentials", f"Exception: {e}")
    
    def _load_credentials(self):
        creds = Credentials.from_service_account_file(
            os.path.join("config", GCP_CREDENTIALS_FILENAME)
        )
        self._credentials = creds
        return self
    
    def get_services(self):
        paths = [os.path.join(self.plugins_path, d) for d in os.listdir(self.plugins_path)]
        self.services_names = list(
            filter(
                lambda p: os.path.isdir(p) and "common" not in p, paths)
                )