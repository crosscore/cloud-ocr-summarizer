import json
import logging
from typing import Dict, Any, Optional, List
import boto3
from config.settings import CLAUDE_CONFIG, LOGGING_CONFIG
import random
import time

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

            # Get language settings
            language_settings = CLAUDE_CONFIG['language_settings'].get(
                primary_lang,
                CLAUDE_CONFIG['language_settings']['ja']
            )

            summaries = []
            # Process each page individually
            for page in pages:
                if page.get('text'):
                    page_summary = self._generate_page_summary(
                        page['text'],
                        page['page_number'],
                        language_settings
                    )
                    if page_summary:
                        summaries.append({
                            'page_number': page['page_number'],
                            'summary': page_summary
                        })

            # Generate overall summary if there are multiple pages
            overall_summary = None
            if len(summaries) > 1:
                combined_text = '\n'.join([s['summary'] for s in summaries])
                overall_summary = self._generate_overall_summary(
                    combined_text,
                    language_settings
                )

            return {
                'page_summaries': summaries,
                'overall_summary': overall_summary,
                'metadata': {
                    'total_pages': len(summaries),
                    'primary_language': primary_lang
                }
            }

        except Exception as e:
            logger.error(f"Error processing OCR data: {str(e)}")
            return None

    def _generate_page_summary(
        self,
        text: str,
        page_number: int,
        language_settings: Dict[str, Any]
    ) -> Optional[str]:
        """Generate summary for a single page with retry logic"""
        try:
            prompt = language_settings['prompt_template'].format(text=text)
            response = self._invoke_claude_with_retry(prompt)
            if response:
                return response.strip()
            return None

        except Exception as e:
            logger.error(f"Error generating summary for page {page_number}: {str(e)}")
            return None

    def _generate_overall_summary(
        self,
        combined_summaries: str,
        language_settings: Dict[str, Any]
    ) -> Optional[str]:
        """Generate overall summary from page summaries with retry logic"""
        try:
            prompt = language_settings['prompt_template'].format(text=combined_summaries)
            response = self._invoke_claude_with_retry(prompt)
            if response:
                return response.strip()
            return None

        except Exception as e:
            logger.error(f"Error generating overall summary: {str(e)}")
            return None

    def _invoke_claude_with_retry(self, prompt: str) -> Optional[str]:
        """Send request to Claude model with exponential backoff retry"""
        max_retries = 5
        base_delay = 1  # Initial delay in seconds
        max_delay = 32  # Maximum delay in seconds

        for attempt in range(max_retries):
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
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, 0.1 * delay)
                total_delay = delay + jitter

                if attempt < max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {total_delay:.2f} seconds..."
                    )
                    time.sleep(total_delay)
                else:
                    logger.error(
                        f"Failed all {max_retries} attempts to invoke Claude. "
                        f"Last error: {str(e)}"
                    )
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
