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

    def __init__(self, configuration: ConfigurationManager, on_reset_client=False , on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
        if on_reset_client:
            self.reset_client()
    
    def reset_client(self):
        self.client = gcp_logging.Client(project=self.configuration.project,
                                         credentials=self.configuration.credentials)
