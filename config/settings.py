# gcp-ocr-exp/config/settings.py
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create required directories
def ensure_directories_exist():
    """Create necessary directories if they don't exist"""
    directories = [
        os.path.join(PROJECT_ROOT, 'data', 'input'),
        os.path.join(PROJECT_ROOT, 'data', 'output'),
        os.path.join(PROJECT_ROOT, 'logs'),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Create directories
ensure_directories_exist()

# GCP Configuration
GCP_CONFIG: Dict[str, Any] = {
    'project_id': os.getenv('GCP_PROJECT_ID', ''),
    'credentials_path': os.path.join(
        PROJECT_ROOT,
        'credentials',
        os.getenv('GCP_CREDENTIALS_FILE', 'gcp-service-account.json')
    ),
    'storage_bucket': os.getenv('GCP_STORAGE_BUCKET', ''),
    'bucket_prefix': os.getenv('GCP_BUCKET_PREFIX', 'medical_documents/'),
    'region': os.getenv('GCP_REGION', 'asia-northeast1')
}

# Vision API Configuration
VISION_CONFIG: Dict[str, Any] = {
    'max_retries': int(os.getenv('VISION_MAX_RETRIES', '3')),
    'timeout': int(os.getenv('VISION_TIMEOUT', '30')),  # seconds
    'confidence_threshold': float(os.getenv('VISION_CONFIDENCE_THRESHOLD', '0.7')),
    'supported_languages': ['ja', 'en'],  # 日本語と英語をサポート
    'batch_size': int(os.getenv('VISION_BATCH_SIZE', '10'))  # OCR処理のバッチサイズ
}

# File Processing Configuration
FILE_CONFIG: Dict[str, Any] = {
    'allowed_extensions': ['.pdf', '.png', '.jpg', '.jpeg'],
    'max_file_size': 10 * 1024 * 1024,  # 10MB (GCP Vision APIの制限に合わせて調整)
    'input_directory': os.path.join(PROJECT_ROOT, 'data', 'input'),
    'output_directory': os.path.join(PROJECT_ROOT, 'data', 'output'),
    'temp_directory': os.path.join(PROJECT_ROOT, 'data', 'temp')  # 一時ファイル用
}

# Logging Configuration
LOGGING_CONFIG: Dict[str, Any] = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': os.path.join(PROJECT_ROOT, 'logs', 'app.log')
}

# Security Configuration
SECURITY_CONFIG: Dict[str, Any] = {
    'enable_audit_logs': os.getenv('ENABLE_AUDIT_LOGS', 'true').lower() == 'true',
    'data_retention_days': int(os.getenv('DATA_RETENTION_DAYS', '30')),
    'delete_after_processing': os.getenv('DELETE_AFTER_PROCESSING', 'true').lower() == 'true'
}

# Sample .env file template
ENV_TEMPLATE = '''
GCP_PROJECT_ID=your-project-id
GCP_CREDENTIALS_FILE=gcp-service-account.json
GCP_STORAGE_BUCKET=your-bucket-name
GCP_BUCKET_PREFIX=medical_documents/
GCP_REGION=asia-northeast1

VISION_MAX_RETRIES=3
VISION_TIMEOUT=30
VISION_CONFIDENCE_THRESHOLD=0.7
VISION_BATCH_SIZE=10

LOG_LEVEL=INFO
ENABLE_AUDIT_LOGS=true
DATA_RETENTION_DAYS=30
DELETE_AFTER_PROCESSING=true
'''

# Constants for Vision API
VISION_CONSTANTS = {
    'supported_mime_types': {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
    },
    'max_pages_per_request': 5,  # Vision APIの1リクエストあたりの最大ページ数
    'default_language_hints': ['ja', 'en']
}
