import json
import logging
from typing import Dict, Any, Optional
import boto3
from config.settings import CLAUDE_CONFIG, LOGGING_CONFIG

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format']
)
logger = logging.getLogger(__name__)

class ClaudeProcessor:
    """
    Claude model processor for text summarization using AWS Bedrock
    """
    def __init__(self):
        """Initialize Claude model with configurations"""
        try:
            # Initialize Bedrock client
            self.bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=CLAUDE_CONFIG.get('region', 'us-east-1')
            )
            logger.info("Successfully initialized Bedrock client")

        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise

    def _invoke_claude(self, prompt: str) -> Optional[str]:
        """Send request to Claude model and get response"""
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

    def process_ocr_data(self, ocr_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate summary from OCR data

        Args:
            ocr_data: Dictionary containing OCR results

        Returns:
            Dictionary containing summaries and metadata
        """
        try:
            # Extract pages from the correct location in JSON structure
            if not ocr_data.get('responses'):
                logger.error("OCR data missing 'responses' key")
                return None

            pages = ocr_data['responses'][0].get('pages', [])
            if not pages:
                logger.error("No pages found in OCR data")
                return None

            # Get primary language from the first page
            primary_lang = self._get_primary_language_from_pages(pages)

            # Get language settings
            language_settings = CLAUDE_CONFIG['language_settings'].get(
                primary_lang,
                CLAUDE_CONFIG['language_settings']['en']  # Default to English settings
            )

            summaries = []
            # Process each page
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
            logger.error(f"Error generating summary: {str(e)}")
            return None

    def _get_primary_language_from_pages(self, pages: list[Dict[str, Any]]) -> str:
        """Determine primary language from pages"""
        try:
            for page in pages:
                if page.get('detected_languages'):
                    # Sort languages by confidence and get the highest confidence language
                    languages = sorted(
                        page['detected_languages'],
                        key=lambda x: x.get('confidence', 0),
                        reverse=True
                    )
                    if languages:
                        return languages[0]['language_code']

            logger.warning("No language detected in pages. Defaulting to English.")
            return 'en'
        except Exception as e:
            logger.warning(f"Error detecting language: {str(e)}. Defaulting to English.")
            return 'en'

    def _generate_page_summary(
        self,
        text: str,
        page_number: int,
        language_settings: Dict[str, Any]
    ) -> Optional[str]:
        """Generate summary for a single page"""
        try:
            prompt = language_settings['prompt_template'].format(text=text)
            return self._invoke_claude(prompt)

        except Exception as e:
            logger.error(f"Error generating summary for page {page_number}: {str(e)}")
            return None

    def _generate_overall_summary(
        self,
        combined_summaries: str,
        language_settings: Dict[str, Any]
    ) -> Optional[str]:
        """Generate overall summary from page summaries"""
        try:
            prompt = language_settings['prompt_template'].format(text=combined_summaries)
            return self._invoke_claude(prompt)

        except Exception as e:
            logger.error(f"Error generating overall summary: {str(e)}")
            return None
