# backend/infrastructure/di_container.py

from functools import wraps
from typing import Dict, Type, Callable

from backend.services.base_service import BaseGCloudService
from backend.services.implementations.auth_service import AuthService
from backend.services.implementations.kms_service import KmsService
from backend.services.implementations.billing_service import BillingService
from backend.services.implementations.iam_service import IamService
from backend.services.implementations.org_service import OrganizationsService
from backend.services.implementations.org_policies_service import OrgPoliciesService
from backend.services.implementations.storage_service import StorageService
from backend.services.implementations.sql_service import SqlService
from backend.services.implementations.bigquery_service import BigqueryService
from backend.services.implementations.pubsub_service import PubSubService
from backend.services.implementations.dataflow_service import DataflowService
from backend.services.implementations.dataplex_service import DataplexService
from backend.services.implementations.dataproc_service import DataprocService
from backend.services.implementations.composer_service import ComposerService
from backend.services.implementations.log_service import LogService
from backend.services.implementations.monitor_service import MonitoringService
from backend.services.implementations.secrets_service import SecretsService
from backend.services.implementations.automation_service import AutomationService
from backend.services.implementations.debug_service import DebugService

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
            "auth": AuthService,
            "billing": BillingService,
            "organizations": OrganizationsService,
            "org-policies": OrgPoliciesService,
            "storage": StorageService,
            "sql": SqlService,
            #"biglake": BiglakeService,
            "bq": BigqueryService,
            "pubsub": PubSubService,
            "dataflow": DataflowService,
            "dataplex": DataplexService,
            "dataproc": DataprocService,
            "composer": ComposerService,
            "logging": LogService,
            "monitoring": MonitoringService,
            "kms": KmsService,
            "secrets": SecretsService,
            "automation": AutomationService,
            "debug": DebugService,
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