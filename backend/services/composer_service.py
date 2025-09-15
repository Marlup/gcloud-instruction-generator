
from google.cloud.orchestration.airflow import service_v1

from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService
from backend.infrastructure.configuration_manager import ConfigurationManager


__all__ = ["ComposerService"]

class ComposerService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Composer.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.COMPOSER

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.reset_client()
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
    
    def reset_client(self):
        self.client = service_v1.EnvironmentsClient(credentials=self.configuration.credentials)
