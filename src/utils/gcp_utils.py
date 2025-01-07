# gcp-ocr-exp/src/utils/gcp_utils.py
import os
import logging
from typing import Optional, Tuple
from google.cloud import storage
from google.cloud import vision
from google.oauth2 import service_account
from config.settings import GCP_CONFIG, LOGGING_CONFIG, VISION_CONSTANTS

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    filename=LOGGING_CONFIG['file_path']
)
logger = logging.getLogger(__name__)

class GCPClient:
    """GCP client wrapper for authentication and common operations"""

    def __init__(self):
        """Initialize GCP client with credentials"""
        try:
            self.credentials = self._get_credentials()
            self.storage_client = storage.Client(
                credentials=self.credentials,
                project=GCP_CONFIG['project_id']
            )
            self.vision_client = vision.ImageAnnotatorClient(
                credentials=self.credentials
            )
            logger.info("Successfully initialized GCP client")
        except Exception as e:
            logger.error(f"Failed to initialize GCP client: {str(e)}")
            raise

    def _get_credentials(self) -> service_account.Credentials:
        """Get GCP credentials from service account file"""
        try:
            credentials_path = GCP_CONFIG['credentials_path']
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Credentials file not found at: {credentials_path}"
                )

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            return credentials
        except Exception as e:
            logger.error(f"Failed to load credentials: {str(e)}")
            raise

    def upload_to_storage(
        self,
        local_file_path: str,
        destination_blob_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Upload a file to Google Cloud Storage

        Args:
            local_file_path: Path to the local file
            destination_blob_name: Name to give the file in GCS (optional)

        Returns:
            Tuple of (success status, public URL or error message)
        """
        try:
            # Get bucket
            bucket = self.storage_client.bucket(GCP_CONFIG['storage_bucket'])

            # Generate destination blob name if not provided
            if not destination_blob_name:
                file_name = os.path.basename(local_file_path)
                destination_blob_name = os.path.join(
                    GCP_CONFIG['bucket_prefix'],
                    file_name
                )

            # Create blob and upload file
            blob = bucket.blob(destination_blob_name)

            # Get file extension and mime type
            file_ext = os.path.splitext(local_file_path)[1].lower()
            content_type = VISION_CONSTANTS['supported_mime_types'].get(
                file_ext,
                'application/octet-stream'
            )

            # Upload with content type
            blob.upload_from_filename(
                local_file_path,
                content_type=content_type
            )

            logger.info(
                f"Successfully uploaded {local_file_path} to "
                f"gs://{GCP_CONFIG['storage_bucket']}/{destination_blob_name}"
            )

            return True, blob.public_url

        except Exception as e:
            error_msg = f"Failed to upload file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def delete_from_storage(self, blob_name: str) -> bool:
        """
        Delete a file from Google Cloud Storage

        Args:
            blob_name: Name of the blob to delete

        Returns:
            bool: Success status
        """
        try:
            bucket = self.storage_client.bucket(GCP_CONFIG['storage_bucket'])
            blob = bucket.blob(blob_name)
            blob.delete()

            logger.info(
                f"Successfully deleted gs://{GCP_CONFIG['storage_bucket']}/{blob_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to delete blob {blob_name}: {str(e)}")
            return False

    def list_files_in_bucket(
        self,
        prefix: Optional[str] = None
    ) -> Tuple[bool, list]:
        """
        List files in the configured GCS bucket

        Args:
            prefix: Optional prefix to filter files (default: configured prefix)

        Returns:
            Tuple of (success status, list of file names)
        """
        try:
            bucket = self.storage_client.bucket(GCP_CONFIG['storage_bucket'])
            prefix = prefix or GCP_CONFIG['bucket_prefix']

            blobs = bucket.list_blobs(prefix=prefix)
            file_list = [blob.name for blob in blobs]

            return True, file_list

        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            return False, []

    def get_signed_url(
        self,
        blob_name: str,
        expiration: int = 3600
    ) -> Tuple[bool, str]:
        """
        Generate a signed URL for a file in GCS

        Args:
            blob_name: Name of the blob
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Tuple of (success status, signed URL or error message)
        """
        try:
            bucket = self.storage_client.bucket(GCP_CONFIG['storage_bucket'])
            blob = bucket.blob(blob_name)

            url = blob.generate_signed_url(
                expiration=expiration,
                version="v4"
            )

            return True, url

        except Exception as e:
            error_msg = f"Failed to generate signed URL: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
