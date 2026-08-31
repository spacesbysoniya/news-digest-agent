import os
from observability import setup_logger

logger = setup_logger("SecretsManager")

class SecureSecretManager:
    """Manages sensitive API credentials securely utilizing GCP Secret Manager with local fallback."""
    @classmethod
    def get_secret(cls, secret_id: str, default: str = None) -> str:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "my-project")
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            logger.info(f"Successfully retrieved secret '{secret_id}' from GCP Secret Manager.")
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            val = os.getenv(secret_id, default)
            if val:
                logger.info(f"Retrieved secret '{secret_id}' from local environment fallback.")
            else:
                logger.warning(f"Secret '{secret_id}' not found in GCP or environment.")
            return val
