from google.cloud import biglake_v1

from backend.services.base_service import BaseGCloudService

from backend.core.types.enums import GCPResource, GCPService
from backend.infrastructure.configuration_manager import ConfigurationManager

__all__ = ["BiglakeService"]

class BiglakeService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP BigLake.
    Puede manejar catálogos, tablas o catálogos Iceberg.
    """

    service_name = GCPService.BIGLAKE

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)

    def get_client(self, purpose: GCPResource = GCPResource.BIGLAKE_CATALOG):
        """
        Devuelve el cliente de BigLake correcto para el propósito:
        - purpose == "catalog": Catálogo estándar
        - purpose == "iceberg": Catálogo Iceberg
        """
        creds = self.configuration.client._credentials
        if purpose == "catalog":
            return biglake_v1.CatalogServiceClient(credentials=creds)
        elif purpose == "iceberg":
            return biglake_v1.IcebergCatalogServiceClient(credentials=creds)
        else:
            raise ValueError(f"Propósito no soportado para BigLake: {purpose}")

    # -----------------------------
    # Validaciones en vivo
    # -----------------------------
    def validate(self, resource: str, **kwargs) -> bool:
        # TODO: implementar validaciones reales contra BigLake
        return True

    # -----------------------------
    # Exportación IaC
    # -----------------------------
    def export(self, format: str, config: dict) -> str:
        # TODO: exportar a shell, terraform, yaml
        raise NotImplementedError

    def explain(self, action: str) -> str:
        return f"Explicación para {action} no disponible aún."

    def list_actions(self):
        return self.actions

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> str:
        return "Ejecutar comandos BigLake aún no implementado"
