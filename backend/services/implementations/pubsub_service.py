

from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService


from backend.infrastructure.configuration_manager import ConfigurationManager

__all__ = ["PubSubService"]

class PubSubService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Pub/Sub.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.PUB_SUB

    def __init__(self, configuration: ConfigurationManager, on_reset_client=False , on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
        if on_reset_client:
            self.reset_client()
    
    def reset_client(self):
        # Google logic removed
        pass

    def validate(self, resource: str, **kwargs) -> bool:
        """
        Valida si un bucket u objeto existe en GCP.
        - resource: nombre del bucket (si no hay kwargs).
        - kwargs: si incluye "object", valida un objeto dentro del bucket.
        """

        return True

