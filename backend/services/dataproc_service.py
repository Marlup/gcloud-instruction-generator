from google.cloud import dataproc_v1

from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService

from backend.infrastructure.configuration_manager import ConfigurationManager

__all__ = ["DataprocService"]

class DataprocService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Dataproc.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.DATAPROC

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.reset_client()
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
    
    def reset_client(self):
        self.client = dataproc_v1.ClusterControllerClient(credentials=self.configuration.credentials)
