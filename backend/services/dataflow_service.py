from googleapiclient.discovery import build

from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService

from backend.infrastructure.configuration_manager import ConfigurationManager

__all__ = ["DataflowService"]

# ⚠️ Aquí no hay cliente Python oficial al 100% → se usa REST API vía googleapiclient.
class DataflowService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Dataflow.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.DATAFLOW

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.reset_client()
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
    
    def reset_client(self):
        self.client = build("dataflow", "v1b3", credentials=self.configuration.credentials)

    def validate(self, template_path: str) -> bool:
        """
        dataflow_template_exists
        Verifica si una plantilla de Dataflow existe en GCS.
        template_path suele ser gs://bucket/path/template
        """
        try:
            bucket_name, prefix = template_path[5:].split("/", 1)
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(prefix)
            return blob.exists()
        except Exception:
            return False