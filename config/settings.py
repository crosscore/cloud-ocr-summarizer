from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base utility class for configuration
class BaseConfig:
    """Base configuration class with common utilities for environment variable handling"""

    @staticmethod
    def get_env_bool(key: str, default: bool = False) -> bool:
        """Get boolean value from environment variable"""
        return os.getenv(key, str(default)).lower() == 'true'

    @staticmethod
    def get_env_int(key: str, default: int) -> int:
        """Get integer value from environment variable"""
        return int(os.getenv(key, str(default)))

    @staticmethod
    def get_env_float(key: str, default: float) -> float:
        """Get float value from environment variable"""
        return float(os.getenv(key, str(default)))

# Project root and directory configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def ensure_directories_exist():
    """Create necessary directories if they don't exist"""
    directories = [
        os.path.join(PROJECT_ROOT, 'data', 'input'),
        os.path.join(PROJECT_ROOT, 'data', 'output'),
        os.path.join(PROJECT_ROOT, 'data', 'output', 'vision'),
        os.path.join(PROJECT_ROOT, 'data', 'output', 'gemini'),
        os.path.join(PROJECT_ROOT, 'data', 'output', 'claude'),
        os.path.join(PROJECT_ROOT, 'logs'),
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Create directories on import
ensure_directories_exist()

# -----------------------------------------------------------------------------
# Core System Configurations
# -----------------------------------------------------------------------------

# Logging Configuration
LOGGING_CONFIG: Dict[str, Any] = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': os.path.join(PROJECT_ROOT, 'logs', 'app.log')
}

# Security Configuration
SECURITY_CONFIG: Dict[str, Any] = {
    'enable_audit_logs': BaseConfig.get_env_bool('ENABLE_AUDIT_LOGS', True),
    'data_retention_days': BaseConfig.get_env_int('DATA_RETENTION_DAYS', 30),
    'delete_after_processing': BaseConfig.get_env_bool('DELETE_AFTER_PROCESSING', True)
}

# File Processing Configuration
FILE_CONFIG: Dict[str, Any] = {
    'allowed_extensions': ['.pdf', '.png', '.jpg', '.jpeg'],
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'input_directory': os.path.join(PROJECT_ROOT, 'data', 'input'),
    'output_directory': os.path.join(PROJECT_ROOT, 'data', 'output'),
    'vision_output_directory': os.path.join(PROJECT_ROOT, 'data', 'output', 'vision'),
    'gemini_output_directory': os.path.join(PROJECT_ROOT, 'data', 'output', 'gemini'),
    'claude_output_directory': os.path.join(PROJECT_ROOT, 'data', 'output', 'claude'),
    'vision_output_filename_pattern': 'vision_results_{timestamp}.json',
    'gemini_output_filename_pattern': 'gemini_summary_{timestamp}.json',
    'claude_output_filename_pattern': 'claude_summary_{timestamp}.json',
    'timestamp_format': '%Y%m%d_%H%M%S',
}

# -----------------------------------------------------------------------------
# Vision API Configurations
# -----------------------------------------------------------------------------

# Vision API Constants
VISION_CONSTANTS = {
    'supported_mime_types': {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
    },
    'max_pages_per_request': 5,
    'default_language_hints': ['ja', 'en']
}

# Vision API Core Configuration
VISION_CONFIG: Dict[str, Any] = {
    'max_retries': BaseConfig.get_env_int('VISION_MAX_RETRIES', 3),
    'timeout': BaseConfig.get_env_int('VISION_TIMEOUT', 30),
    'confidence_threshold': BaseConfig.get_env_float('VISION_CONFIDENCE_THRESHOLD', 0.7),
    'supported_languages': ['ja', 'en'],
    'batch_size': BaseConfig.get_env_int('VISION_BATCH_SIZE', 10),
    'default_language_hints': VISION_CONSTANTS['default_language_hints']
}

# Vision API Output Configuration
VISION_OUTPUT_CONFIG: Dict[str, Any] = {
    'output_mode': os.getenv('VISION_OUTPUT_MODE', 'detailed'), # 'detailed' or 'simple'
    'include_confidence': BaseConfig.get_env_bool('VISION_INCLUDE_CONFIDENCE', True),
    'include_bounding_boxes': BaseConfig.get_env_bool('VISION_INCLUDE_BOUNDING_BOXES', True),
    'min_confidence_threshold': BaseConfig.get_env_float('VISION_MIN_CONFIDENCE', 0.0),
    'save_raw_response': BaseConfig.get_env_bool('VISION_SAVE_RAW_RESPONSE', True),
}

# -----------------------------------------------------------------------------
# Generative AI Configurations
# -----------------------------------------------------------------------------

# GCP Configuration for Gemini
GCP_CONFIG: Dict[str, Any] = {
    'project_id': os.getenv('GCP_PROJECT_ID', ''),
    'credentials_path': os.path.join(
        PROJECT_ROOT,
        'credentials',
        os.getenv('GCP_CREDENTIALS_FILE', 'gcp-service-account.json')
    ),
    'storage_bucket': os.getenv('GCP_STORAGE_BUCKET', ''),
    'bucket_prefix': os.getenv('GCP_BUCKET_PREFIX', 'medical_documents/'),
    'region': os.getenv('GCP_REGION', 'asia-northeast1'),
    'api_key': os.getenv('GEMINI_API_KEY', '')
}

# Gemini Configuration
GEMINI_CONFIG: Dict[str, Any] = {
    'model': 'gemini-pro',
    'temperature': BaseConfig.get_env_float('GEMINI_TEMPERATURE', 0.2),
    'max_output_tokens': BaseConfig.get_env_int('GEMINI_MAX_OUTPUT_TOKENS', 2048),
    'top_p': BaseConfig.get_env_float('GEMINI_TOP_P', 0.8),
    'top_k': BaseConfig.get_env_int('GEMINI_TOP_K', 40),
    'language_settings': {
        'ja': {
            'prompt_template': '以下の文書を要約してください：\n{text}\n\n要約：',
            'max_tokens_per_chunk': 1000
        },
        'en': {
            'prompt_template': 'Please summarize the following document:\n{text}\n\nSummary:',
            'max_tokens_per_chunk': 1000
        }
    }
}

# Claude Configuration
CLAUDE_CONFIG: Dict[str, Any] = {
    'model': 'anthropic.claude-3-5-sonnet-20240620-v1:0',  # Bedrock model ID
    'temperature': BaseConfig.get_env_float('CLAUDE_TEMPERATURE', 0.2),
    'max_output_tokens': BaseConfig.get_env_int('CLAUDE_MAX_OUTPUT_TOKENS', 2048),
    'top_p': BaseConfig.get_env_float('CLAUDE_TOP_P', 0.8),
    'top_k': BaseConfig.get_env_int('CLAUDE_TOP_K', 40),
    'region': os.getenv('AWS_REGION', 'us-east-1'),
    'language_settings': {
        'ja': {
            'prompt_template': '以下の文書を要約してください：\n{text}\n\n要約：',
            'max_tokens_per_chunk': 1000
        },
        'en': {
            'prompt_template': 'Please summarize the following document:\n{text}\n\nSummary:',
            'max_tokens_per_chunk': 1000
        }
    }
}
