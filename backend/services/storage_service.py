from typing import Any, Dict, List
import subprocess
from google.api_core.exceptions import NotFound
from google.cloud import storage

from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService
from backend.infrastructure.configuration_manager import ConfigurationManager
from backend.infrastructure.action_loader import ActionLoader

__all__ = ["StorageService"]

class StorageService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Storage.
    Basada en BaseGCloudService.
    """

    service_name = "storage"

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.reset_client()
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)

        # ✅ ActionLoader
        service_path = f"plugins/{self.service_name}"  # ej. actions/storage/
        loader = ActionLoader(service_path)
        self.actions = loader.actions
        self.parameters = configuration.load_parameters(self.service_name)

    #  Client reset 
    # -----------------------------
    def reset_client(self):
        self.client = storage.Client(
            project=self.configuration.project,
            credentials=self.configuration.credentials
        )

    # -----------------------------
    # 1. Validaciones en vivo
    # -----------------------------
    def validate(self, resource: str, **kwargs) -> bool:
        """
        Valida si un bucket u objeto existe en GCP.
        - resource: nombre del bucket (si no hay kwargs).
        - kwargs: si incluye "object", valida un objeto dentro del bucket.
        """

        if GCPResource.OBJECT in kwargs:
            print("Validando objeto:", kwargs[GCPResource.OBJECT], "en bucket:", resource)
            object_name = kwargs[GCPResource.OBJECT]
            return self.object_exists(resource, object_name)
        else:
            try:
                print("Validando bucket:", resource)
                return self.bucket_exists(resource)
            except NotFound:
                return False

    # -----------------------------
    # 3. Exportación IaC
    # -----------------------------
    def export(self, format: ExportFileFormat, config: Dict[str, Any]) -> str:
        if format == ExportFileFormat.SHELL:
            return to_shell([self.build_command("Crear bucket", config)])
        elif format == ExportFileFormat.TERRAFORM:
            return to_terraform(config)
        elif format == ExportFileFormat.YAML:
            return to_yaml(config)
        else:
            raise ValueError(f"Formato no soportado: {format}")

    # -----------------------------
    # 4. Explicaciones educativas
    # -----------------------------
    def explain(self, action: str) -> str:
        """
        Devuelve una breve explicación del comando/acción.
        En esta fase inicial lo resolvemos con hardcodeo mínimo.
        """
        explanations = {
            "Crear bucket": "Crea un bucket de almacenamiento en la región indicada con una clase de almacenamiento por defecto.",
            "Listar buckets": "Muestra todos los buckets disponibles en el proyecto actual.",
            "Borrar bucket": "Elimina un bucket y todos sus objetos si se usa la opción --force."
        }
        return explanations.get(action, "Explicación no disponible aún.")
    
    def ping(self) -> bool:
        return self.configuration.ping()

    def execute(self, command: str) -> str:
        """
        Ejecuta un comando gcloud real en el sistema.
        Devuelve la salida o el error.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"❌ Error:\n{result.stderr.strip()}"
        except Exception as e:
            return f"⚠️ Excepción ejecutando comando: {e}"

    # ========== 🪣 Storage ==========
    def bucket_exists(self, bucket_name: str) -> bool:
        return self.client.lookup_bucket(bucket_name) is not None

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        bucket = self.client.bucket(bucket_name)
        if not bucket.exists():
            return False
        return bucket.blob(object_name).exists()