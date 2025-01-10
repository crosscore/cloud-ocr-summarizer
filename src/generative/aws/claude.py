import json
import logging
from typing import Dict, Any, Optional, List
import boto3
from config.settings import CLAUDE_CONFIG, LOGGING_CONFIG

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format']
)
logger = logging.getLogger(__name__)

class ClaudeProcessor:
    """Claude processor for generating document summaries"""

    def __init__(self):
        """Initialize Claude model with configurations"""
        try:
            session = boto3.Session(
                profile_name='AdministratorAccess-207567758619',
                region_name=CLAUDE_CONFIG.get('region', 'us-east-1')
            )
            self.bedrock_client = session.client('bedrock-runtime')
            logger.info("Successfully initialized Bedrock client")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise

    def process_ocr_data(self, ocr_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process OCR data and generate summaries"""
        try:
            if not ocr_data.get('responses'):
                logger.error("OCR data missing 'responses' key")
                return None

            pages = ocr_data['responses'][0].get('pages', [])
            if not pages:
                logger.error("No pages found in OCR data")
                return None

            # Get primary language from the first page
            primary_lang = self._get_primary_language(pages[0])

            # Generate summaries for all pages
            return self._generate_summaries(pages, primary_lang)

        except Exception as e:
            logger.error(f"Error processing OCR data: {str(e)}")
            return None

    def _get_primary_language(self, page: Dict[str, Any]) -> str:
        """Get primary language from page data"""
        try:
            if page.get('detected_languages'):
                # Get the highest confidence language
                langs = sorted(
                    page['detected_languages'],
                    key=lambda x: x.get('confidence', 0),
                    reverse=True
                )
                if langs:
                    return langs[0]['language_code']
            return 'ja'  # デフォルト言語として日本語を使用

        except Exception as e:
            logger.warning(f"Error detecting language: {str(e)}. Defaulting to Japanese.")
            return 'ja'

    def _generate_summaries(
        self,
        pages: List[Dict[str, Any]],
        primary_lang: str
    ) -> Optional[Dict[str, Any]]:
        """Generate summaries for all pages in a single request"""
        try:
            # Prepare combined text with page markers
            combined_text = "\n\n".join([
                f"===== ページ {page['page_number']} =====\n{page['text']}"
                for page in pages
            ])

            # Get language settings
            language_settings = CLAUDE_CONFIG['language_settings'].get(
                primary_lang,
                CLAUDE_CONFIG['language_settings']['ja']  # デフォルトは日本語設定を使用
            )

            # Create prompt using template
            prompt = language_settings['prompt_template'].format(
                text=f"""以下の文書の各ページの要約と全体の要約を生成してください。
各ページは「===== ページ X =====」で区切られています。

{combined_text}

以下のJSON形式で出力してください：
{{
    "page_summaries": [
        {{"page_number": ページ番号, "summary": "ページの要約"}}
    ],
    "overall_summary": "全体要約"
}}"""
            )

            # Send request to Claude
            response = self._invoke_claude(prompt)
            if not response:
                return None

            try:
                # Parse the response as JSON
                result = json.loads(response)
                return {
                    'page_summaries': result['page_summaries'],
                    'overall_summary': result['overall_summary'],
                    'metadata': {
                        'total_pages': len(pages),
                        'primary_language': primary_lang
                    }
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Claude response as JSON: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Error generating summaries: {str(e)}")
            return None

    def _invoke_claude(self, prompt: str) -> Optional[str]:
        """Send request to Claude model with basic error handling"""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": CLAUDE_CONFIG['max_output_tokens'],
                "temperature": CLAUDE_CONFIG['temperature'],
                "top_p": CLAUDE_CONFIG['top_p'],
                "top_k": CLAUDE_CONFIG['top_k'],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            response = self.bedrock_client.invoke_model(
                modelId=CLAUDE_CONFIG['model'],
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except Exception as e:
            logger.error(f"Error invoking Claude model: {str(e)}")
            return None
