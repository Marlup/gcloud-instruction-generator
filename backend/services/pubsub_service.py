from google.cloud import pubsub_v1
from google.api_core.exceptions import NotFound

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

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.reset_client()
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)
    
    def reset_client(self):
        self.publisher_client = pubsub_v1.PublisherClient(credentials=self.configuration.credentials)
        self.subscriber_client = pubsub_v1.SubscriberClient(credentials=self.configuration.credentials)

    def validate(self, resource: str, **kwargs) -> bool:
        """
        Valida si un bucket u objeto existe en GCP.
        - resource: nombre del bucket (si no hay kwargs).
        - kwargs: si incluye "object", valida un objeto dentro del bucket.
        """

        if GCPResource.PUBSUB_TOPIC in kwargs:
            print("Validando topic:", kwargs[GCPResource.PUBSUB_TOPIC])
            topic_name = kwargs[GCPResource.PUBSUB_TOPIC]
            return self.topic_exists(topic_name, project_id=self.configuration.project)
        else:
            print("Validando PUBSUB-:", resource)
            subscription_name = kwargs[GCPResource.PUBSUB_SUBSCRIPTION]
            return self.subscription_exists(
                topic_name, 
                project_id=self.configuration.project, 
                subscription_name=subscription_name
                )

    def topic_exists(self, topic_name: str, project_id: str) -> bool:
        full_name = f"projects/{project_id}/topics/{topic_name}"
        try:
            return self.publisher_client \
                       .get_topic(request={"topic": full_name}) is not None
        except NotFound:
            return False

    def subscription_exists(self, subscription_name: str, project_id: str) -> bool:
        full_name = f"projects/{project_id}/subscriptions/{subscription_name}"
        try:
            return self.subscriber_client \
                       .get_subscription(request={"subscription": full_name}) is not None
        except NotFound:
            return False