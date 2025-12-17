from enum import Enum

class GCPService(str, Enum):
    IAM = "iam"
    ORGANIZATIONS = "organizations"
    ORG_POLICIES = "org-policies"
    AUTH = "auth"
    BILLING = "billing"
    STORAGE = "storage"
    #BIGLAKE = "biglake"
    BIGQUERY = "bq"
    PUB_SUB = "pubsub"
    SQL = "sql"
    DATAFLOW = "dataflow"
    DATAPLEX = "dataplex"
    DATAPROC = "dataproc"
    COMPOSER = "composer"
    LOGGING = "logging"
    MONITORING = "monitoring"
    KMS = "kms"
    SECRETS = "secrets"
    AUTOMATION = "automation"
    DEBUG = "debug"

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

class UpdateMode(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    SINGLE = "single"
    PATCH = "patch"  # Process only unscraped entities from unprocessed.json files
