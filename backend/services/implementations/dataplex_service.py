
from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService

from backend.infrastructure.configuration_manager import ConfigurationManager

__all__ = ["DataplexService"]

class DataplexService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Dataplex.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.DATAPLEX

    def __init__(self, configuration: ConfigurationManager, on_reset_client=False , on_concat_project_id: bool=False):
        self.configuration = configuration
        if on_reset_client:
            self.reset_client()
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)

    def reset_client(self):
        # Google logic removed
        pass
