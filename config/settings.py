from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create required directories
def ensure_directories_exist():
    """Create necessary directories if they don't exist"""
    directories = [
        os.path.join(PROJECT_ROOT, 'data', 'input'),
        os.path.join(PROJECT_ROOT, 'data', 'output'),
        os.path.join(PROJECT_ROOT, 'data', 'output', 'vision'),
        os.path.join(PROJECT_ROOT, 'data', 'output', 'gemini'),
        os.path.join(PROJECT_ROOT, 'logs'),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Create directories
ensure_directories_exist()

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
    'region': os.getenv('GCP_REGION', 'asia-northeast1'),
    'api_key': os.getenv('GEMINI_API_KEY', '')
}

# GEMINI_CONFIG
GEMINI_CONFIG: Dict[str, Any] = {
    'model': 'gemini-pro',
    'temperature': float(os.getenv('GEMINI_TEMPERATURE', '0.2')),
    'max_output_tokens': int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '2048')),
    'top_p': float(os.getenv('GEMINI_TOP_P', '0.8')),
    'top_k': int(os.getenv('GEMINI_TOP_K', '40')),
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

# Vision API Configuration
VISION_CONFIG: Dict[str, Any] = {
    'max_retries': int(os.getenv('VISION_MAX_RETRIES', '3')),
    'timeout': int(os.getenv('VISION_TIMEOUT', '30')),
    'confidence_threshold': float(os.getenv('VISION_CONFIDENCE_THRESHOLD', '0.7')),
    'supported_languages': ['ja', 'en'],
    'batch_size': int(os.getenv('VISION_BATCH_SIZE', '10')),
    'default_language_hints': VISION_CONSTANTS['default_language_hints']
}

# Vision API Output Configuration
VISION_OUTPUT_CONFIG: Dict[str, Any] = {
    'output_mode': os.getenv('VISION_OUTPUT_MODE', 'detailed'),  # 'simple' or 'detailed'
    'include_confidence': os.getenv('VISION_INCLUDE_CONFIDENCE', 'true').lower() == 'true',
    'include_bounding_boxes': os.getenv('VISION_INCLUDE_BOUNDING_BOXES', 'true').lower() == 'true',
    'min_confidence_threshold': float(os.getenv('VISION_MIN_CONFIDENCE', '0.0')),
    # for DEBUG
    'save_raw_response': os.getenv('VISION_SAVE_RAW_RESPONSE', 'true').lower() == 'true',
}

# AWS Claude Configuration
CLAUDE_CONFIG: Dict[str, Any] = {
    'model': 'anthropic.claude-3-sonnet-20240229-v1:0',  # Bedrock model ID
    'temperature': float(os.getenv('CLAUDE_TEMPERATURE', '0.2')),
    'max_output_tokens': int(os.getenv('CLAUDE_MAX_OUTPUT_TOKENS', '2048')),
    'top_p': float(os.getenv('CLAUDE_TOP_P', '0.8')),
    'top_k': int(os.getenv('CLAUDE_TOP_K', '40')),
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
