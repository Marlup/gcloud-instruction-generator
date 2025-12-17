from typing import Any, Dict
import subprocess

from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPService
from backend.infrastructure.configuration_manager import ConfigurationManager
from backend.infrastructure.action_loader import ActionLoader

__all__ = ["KmsService"]

class KmsService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Kms.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.KMS

    def __init__(self, configuration: ConfigurationManager, on_reset_client=False , on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        if on_reset_client:
            self.reset_client()
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)

    #  Client reset 
    # -----------------------------
    def reset_client(self):
        #self.client = kms.Client(
        #    project=self.configuration.project,
        #    credentials=self.configuration.credentials
        #)
        return

    # -----------------------------
    # 1. Validaciones en vivo
    # -----------------------------
    def validate(self, **kwargs) -> bool:
        """
        Valida si un bucket u objeto existe en GCP.
        - resource: nombre del bucket (si no hay kwargs).
        - kwargs: si incluye "object", valida un objeto dentro del bucket.
        """

        return True

    # -----------------------------
    # 3. Exportación IaC
    # -----------------------------
    def export(self, format: ExportFileFormat, config: Dict[str, Any]) -> str:
        if format == ExportFileFormat.SHELL:
            return to_shell([self.build_command("", config)])
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
        return ""
    
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
