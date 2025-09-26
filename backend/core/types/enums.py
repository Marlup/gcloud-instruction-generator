from enum import Enum

class GCPService(str, Enum):
    IAM = "iam"
    ORGANIZATION = "organization"
    STORAGE = "storage"
    BIGLAKE = "biglake"
    BIGQUERY = "bigquery"
    PUB_SUB = "pub-sub"
    DATACATALOG = "datacatalog"
    DATAFLOW = "dataflow"
    DATAPLEX = "dataplex"
    DATAPROC = "dataproc"
    COMPOSER = "composer"
    LOG = "log"
    MONITOR = "monitor"
    SECURITY = "security"
    AUTOMATION = "automation"
    DEBUG_ERROR = "debug-error"

class IAMPurpose(str, Enum):
    ADMIN = "admin"                # Roles, cuentas de servicio
    CREDENTIALS = "credentials"    # Impersonation, tokens
    POLICIES = "policies"          # IAM v3, políticas condicionales
    RESOURCES = "resource-manager"          # Resource Manager

class GCPResource(str, Enum):
    # --- Core resources ---
    DATASET = "dataset"
    TABLE = "table"
    VIEW = "view"
    JOB = "job"
    BUCKET = "bucket"
    OBJECT = "object"
    IAM_POLICY = "iam-policy"
    TRANSFER_JOB = "transfer-job"
    OPERATION = "operation"
    LOG = "log"
    KMS_KEY = "kms-key"
    BIGLAKE_CATALOG = "biglake-catalog"
    BIGLAKE_TABLE = "biglake-table"
    PUBSUB_TOPIC = "pubsub-topic"
    PUBSUB_SUBSCRIPTION = "pubsub-subscription"

class ExportFileFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    YAML = "yaml"
    SHELL = "shell"
    TERRAFORM = "Terraform"


