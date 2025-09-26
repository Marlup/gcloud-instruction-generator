from google.cloud import logging as gcp_logging

from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import GCPService

from backend.infrastructure.configuration_manager import ConfigurationManager

__all__ = ["AutomationService"]

class AutomationService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP AutomationService .
    Basada en BaseGCloudService.
    """

    service_name = GCPService.AUTOMATION

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.reset_client()
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
    
    def reset_client(self):
        self.client = gcp_logging.Client(project=self.configuration.project,
                                         credentials=self.configuration.credentials)
