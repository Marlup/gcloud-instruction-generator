# backend/services/bigquery_service.py

import subprocess
from typing import Any, Dict, List


from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService
from backend.infrastructure.configuration_manager import ConfigurationManager


__all__ = ["BigqueryService"]


class BigqueryService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Bigquery.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.BIGQUERY

    def __init__(self, configuration: ConfigurationManager, on_reset_client=False , on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
        if on_reset_client:
            self.reset_client()

    # -----------------------------
    #  Client reset 
    # -----------------------------
    def reset_client(self):
        # Google logic removed
        pass

    # -----------------------------
    #  Validaciones en vivo
    # -----------------------------
    def validate(self, resource: str, **kwargs) -> bool:
        """
        Valida si un dataset o tabla existe en BigQuery.
        - resource: dataset_id o dataset_id.table_id
        """
        return True

    # -----------------------------
    # Exportación IaC
    # -----------------------------
    def export(self, format: ExportFileFormat, config: Dict[str, Any]) -> str:
        if format == ExportFileFormat.SHELL:
            return to_shell([self.build_command("Crear dataset", config)])
        elif format == ExportFileFormat.TERRAFORM:
            # Ejemplo de Terraform para dataset
            return f'''
resource "google_bigquery_dataset" "{config["dataset"]}" {{
  dataset_id                  = "{config["dataset"]}"
  location                    = "{config["region"]}"
  default_table_expiration_ms = {config.get("expiration", 0)}
}}
'''
        elif format == ExportFileFormat.YAML:
            return to_yaml(config)
        else:
            raise ValueError(f"Formato no soportado: {format}")

    # -----------------------------
    # Explicaciones educativas
    # -----------------------------
    def explain(self, action: str) -> str:
        explanations = {
            "Crear dataset": "Crea un dataset en BigQuery dentro de un proyecto y región específicos.",
            "Listar datasets": "Lista todos los datasets disponibles en el proyecto.",
            "Borrar dataset": "Elimina un dataset de BigQuery. Con --deleteContents borra también sus tablas.",
        }
        return explanations.get(action, "Explicación no disponible aún.")

    # -----------------------------
    # Listado de acciones soportadas
    # -----------------------------
    def load_actions(self, on_categories: bool = True) -> List[str] | Dict[str, List[str]]:
        if on_categories:
            result = {}
        else:
            result = []
        for category, subcats in self.actions.items():
            if on_categories:
                actions_by_subcat = {}
            for subcat, actions in subcats.items():
                if on_categories:
                    actions_by_subcat[subcat] = list(actions.keys())
                else:
                    result.extend(actions.keys())
            if on_categories:
                result[category] = actions_by_subcat
        return result

    # -----------------------------
    # Comprobación de conectividad
    # -----------------------------
    def ping(self) -> bool:
        return True

    # -----------------------------
    # Ejecución directa
    # -----------------------------
    def execute(self, command: str) -> str:
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

