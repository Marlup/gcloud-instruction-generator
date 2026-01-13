from abc import abstractmethod
from typing import Any, Dict, List
from backend.infrastructure.action_loader import ActionLoader

class BaseGCloudService():
    """
    Interfaz base para todos los servicios gcloud.
    Define los métodos mínimos que cada servicio debe implementar.
    """

    def __init__(self):
        self.actions: Dict = {}
        self.parameters: Dict = {}
        self.on_concat_project_id = False

    # Validaciones en vivo
    # -----------------------------
    @abstractmethod
    def validate(self, resource: str, **kwargs) -> bool:
        """
        Verifica si un recurso existe o es válido en GCP.
        - resource: nombre del recurso principal (bucket, dataset, topic, etc.)
        - kwargs: parámetros adicionales (ej. objeto dentro de bucket)
        """
        pass

    # -----------------------------
    # Generación de comandos
    # -----------------------------
    @abstractmethod
    def build_command(self, base_command: str, params: Dict[str, Any]) -> str:
        """
        Construye un comando a partir de una plantilla y parámetros.
        - template: str con placeholders {param}
        - params: dict con los valores a insertar
        """
        command_params = params.copy()
        if self.on_concat_project_id and "project" not in command_params:
            command_params["project"] = self.configuration.project

        command = base_command + "".format(**command_params)
        return command.format(**command_params)

    # -----------------------------
    # Exportación IaC
    # -----------------------------
    @abstractmethod
    def export(self, format: str, config: Dict[str, Any]) -> str:
        """
        Exporta una configuración a distintos formatos (shell, terraform, yaml).
        - format: "shell" | "terraform" | "yaml".
        - config: diccionario con la configuración del recurso.
        """
        pass

    # -----------------------------
    # Explicaciones educativas
    # -----------------------------
    @abstractmethod
    def explain(self, action: str) -> str:
        """
        Devuelve una explicación en texto del comando/acción.
        - action: nombre de la acción.
        """
        pass

    # -----------------------------
    # Listado de acciones soportadas
    # -----------------------------
    @abstractmethod
    def load_actions(service_path: str, on_save: bool=False) -> Dict[str, Dict[str, Dict[str, dict]]]:
        """
        Construye el diccionario de acciones desde:
        service_path/resource/category/*.json

        Devuelve:
        {
        "Recurso": {
            "Categoría": {
            "Acción": {"cmd": "...", "params": [...]}
            }
        }
        }
        """
        loader = ActionLoader(service_path)
        return loader.actions

    # -----------------------------
    # Comprobación de conectividad
    # -----------------------------
    @abstractmethod
    def ping(self) -> bool:
        """
        Devuelve true si el ping a Google Cloud Console fue exitoso.
        """
        pass

    # -----------------------------
    # Ejecución directa
    # -----------------------------
    @abstractmethod
    def execute(self, command: str) -> str:
        """
        Ejecuta un comando gcloud completo en el sistema.
        - command: string del comando ya construido.
        - return: salida stdout o stderr.
        """
        pass


    # -----------------------------
    # Ejecución directa
    # -----------------------------
    @abstractmethod
    def reset_client(self) -> str:
        """
        Initialize the client.
        """
        pass
    
    def get_action_def(self, resource: str, *args) -> Dict[str, Any]:
        """
        Devuelve la definición de una acción dado un path de claves.
        """
        try:
            node = self.actions[resource]
            for key in args:
                node = node[key]
            
            # If the node itself has 'action' key, that's what we want?
            # Or is 'node' the action def?
            # In our structure: { "action": { ... } }
            if "action" in node:
                return node["action"]
            return node
        except KeyError as e:
            # Fallback for old calls or debug
            raise ValueError(f"Acción no encontrada: {resource} > {args}") from e