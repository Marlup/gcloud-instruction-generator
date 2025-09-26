# backend/infrastructure/di_container.py

from functools import wraps
from typing import Dict, Type, Callable

from backend.services.base_service import BaseGCloudService
from backend.services.iam_service import IamService
from backend.services.org_service import OrganizationService
from backend.services.storage_service import StorageService
from backend.services.biglake_service import BiglakeService
from backend.services.bigquery_service import BigqueryService
from backend.services.pubsub_service import PubSubService
from backend.services.datacatalog_service import DataCatalogService
from backend.services.dataflow_service import DataflowService
from backend.services.dataplex_service import DataplexService
from backend.services.dataproc_service import DataprocService
from backend.services.composer_service import ComposerService
from backend.services.log_service import LogService
from backend.services.monitor_service import MonitorService
from backend.services.security_service import SecurityService
from backend.services.automation_service import AutomationService
from backend.services.debug_service import DebugErrorService

from backend.infrastructure.configuration_manager import ConfigurationManager


class DIContainer:
    """
    Dependency Injection Container.
    Mantiene un registro de servicios instanciados según el nombre del servicio.
    """

    def __init__(self, config: ConfigurationManager):
        self.config = config
        self._services: Dict[str, object] = {}

        # Mapa de servicios disponibles
        self._service_classes: Dict[str, Type] = {
            "iam": IamService,
            "organization": OrganizationService,
            "storage": StorageService,
            "biglake": BiglakeService,
            "bigquery": BigqueryService,
            "pub-sub": PubSubService,
            "datacatalog": DataCatalogService,
            "dataflow": DataflowService,
            "dataplex": DataplexService,
            "dataproc": DataprocService,
            "composer": ComposerService,
            "log": LogService,
            "monitor": MonitorService,
            "security": SecurityService,
            "automation": AutomationService,
            "debug-error": DebugErrorService,
        }

    def get(self, service_name: str) -> BaseGCloudService:
        """
        Devuelve la instancia del servicio solicitado, creándola si no existe aún.
        """
        if service_name not in self._service_classes:
            raise ValueError(f"Servicio no soportado: {service_name}")

        if service_name not in self._services:
            service_class = self._service_classes[service_name]
            self._services[service_name] = service_class(self.config)

        return self._services[service_name]

    def list_services(self) -> list[str]:
        """Devuelve los nombres de servicios registrados en el contenedor."""
        return list(self._service_classes.keys())

# --- Decorador para inyección automática ---
def inject(*service_names: str):
    """
    Decorador que inyecta servicios del contenedor en la función.
    Ejemplo:

        @inject("storage", "bigquery")
        def my_func(storage, bigquery):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            container: DIContainer = kwargs.pop("container")  # requiere container explícito
            for name in service_names:
                kwargs[name] = container.get(name)
            return func(*args, **kwargs)
        return wrapper
    return decorator