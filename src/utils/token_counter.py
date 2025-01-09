import json
from typing import Dict, Any
import logging
from config.settings import LOGGING_CONFIG

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    filename=LOGGING_CONFIG['file_path']
)
logger = logging.getLogger(__name__)

class TokenCounter:
    """Utility class for counting tokens in JSON files"""

    @staticmethod
    def count_json_tokens(file_path: str) -> int:
        """
        Counts the number of tokens in a JSON file

        Args:
            file_path: Path to the JSON file

        Returns:
            int: Total number of tokens
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return TokenCounter._count_structure(data)
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            return 0

    @staticmethod
    def count_json_file(file_path: str) -> dict:
        """
        Counts tokens in a JSON file and provides detailed statistics

        Args:
            file_path: Path to the JSON file

        Returns:
            dict: Dictionary containing token statistics
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return {
                'total_tokens': TokenCounter._count_structure(data),
                'structure_stats': TokenCounter._analyze_structure(data)
            }

        except Exception as e:
            logger.error(f"Error processing JSON file: {str(e)}")
            return {'error': str(e)}

    @staticmethod
    def _count_structure(obj: Any, depth: int = 0) -> int:
        """Recursively counts tokens in a data structure"""
        if depth > 100:  # 再帰の深さ制限
            logger.warning("Maximum recursion depth exceeded")
            return 0

        try:
            if obj is None:
                return 1
            elif isinstance(obj, (bool, int, float)):
                return 1
            elif isinstance(obj, str):
                return len(obj.split())
            elif isinstance(obj, dict):
                return sum(1 + TokenCounter._count_structure(v, depth + 1) for k, v in obj.items())
            elif isinstance(obj, (list, tuple)):
                return sum(TokenCounter._count_structure(item, depth + 1) for item in obj)
            else:
                return 1

        except Exception as e:
            logger.error(f"Error in _count_structure: {str(e)}")
            return 0

    @staticmethod
    def _analyze_structure(data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes the structure of Vision API JSON data"""
        stats = {
            'pages': 0,
            'blocks': 0,
            'paragraphs': 0,
            'words': 0,
            'average_confidence': 0.0,
            'languages': set()
        }

        try:
            if 'responses' in data:
                confidences = []

                for response in data['responses']:
                    for page in response.get('pages', []):
                        stats['pages'] += 1

                        for lang_info in page.get('detected_languages', []):
                            stats['languages'].add(lang_info.get('language_code'))

                        if 'confidence' in page:
                            confidences.append(page['confidence'])

                        for block in page.get('blocks', []):
                            stats['blocks'] += 1

                            for paragraph in block.get('paragraphs', []):
                                stats['paragraphs'] += 1

                                for word in paragraph.get('words', []):
                                    stats['words'] += 1

                if confidences:
                    stats['average_confidence'] = sum(confidences) / len(confidences)

                stats['languages'] = list(stats['languages'])

            return stats

        except Exception as e:
            logger.error(f"Error in structure analysis: {str(e)}")
            return stats
