
# 1. Uso de MagicMock para simular credenciales:

# fake_credentials = MagicMock(name="FakeCredentials")
# cm._credentials = fake_credentials

# 2. Los tests siguen comprobando tipos reales (storage.Client, bigquery.Client, etc.).
# - Si las librerías están instaladas, los objetos se crean con el mock sin error.
# - No se hace conexión a GCP porque nunca se usan métodos que hagan requests.

# 3. Con este enfoque podemos ejecutar tests sin depender de claves reales ni de conexión a Google Cloud.

import pytest
from unittest.mock import MagicMock

from backend.infrastructure.configuration_manager import ConfigurationManager
from backend.core.types.enums import GCPService

from google.cloud import storage as gcs
from google.cloud import bigquery
from google.cloud.orchestration.airflow import v1 as composer_v1
from google.cloud import datacatalog
from googleapiclient.discovery import Resource
from google.cloud import dataplex_v1
from google.cloud import dataproc_v1
from google.cloud import iam_v1
from google.cloud import logging as gcp_logging
from google.cloud import biglake_v1
from google.cloud import pubsub_v1


@pytest.fixture
def config_manager():
    # Configuración simulada
    config = {"project_id": "fake-project"}
    cm = ConfigurationManager(config, on_connect=False)

    # Mock de credenciales (se comporta como objeto Credentials válido)
    fake_credentials = MagicMock(name="FakeCredentials")
    cm._credentials = fake_credentials
    return cm


def test_storage_client(config_manager):
    client = config_manager.get_client(GCPService.STORAGE)
    assert isinstance(client, gcs.Client)


def test_bigquery_client(config_manager):
    client = config_manager.get_client(GCPService.BIGQUERY)
    assert isinstance(client, bigquery.Client)


def test_composer_client(config_manager):
    client = config_manager.get_client(GCPService.COMPOSER)
    assert isinstance(client, composer_v1.EnvironmentsClient)


def test_datacatalog_client(config_manager):
    client = config_manager.get_client(GCPService.DATACATALOG)
    assert isinstance(client, datacatalog.DataCatalogClient)


def test_dataflow_client(config_manager):
    client = config_manager.get_client(GCPService.DATAFLOW)
    assert isinstance(client, Resource)  # googleapiclient.discovery.build devuelve Resource


def test_dataplex_client(config_manager):
    client = config_manager.get_client(GCPService.DATAPLEX)
    assert isinstance(client, dataplex_v1.DataplexServiceClient)


def test_dataproc_client(config_manager):
    client = config_manager.get_client(GCPService.DATAPROC)
    assert isinstance(client, dataproc_v1.ClusterControllerClient)


def test_iam_org_client(config_manager):
    client = config_manager.get_client(GCPService.IAM_ORG)
    assert isinstance(client, iam_v1.IAMClient)


def test_logging_client(config_manager):
    client = config_manager.get_client(GCPService.LOGGING_MONITOR)
    assert isinstance(client, gcp_logging.Client)


def test_biglake_client(config_manager):
    client = config_manager.get_client(GCPService.BIGLAKE)
    assert isinstance(client, biglake_v1.MetastoreServiceClient)


def test_pubsub_client(config_manager):
    clients = config_manager.get_client(GCPService.PUB_SUB)
    assert isinstance(clients, dict)
    assert isinstance(clients["publisher"], pubsub_v1.PublisherClient)
    assert isinstance(clients["subscriber"], pubsub_v1.SubscriberClient)
