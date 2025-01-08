# gcp-ocr-exp/src/generative/gcp/gemini.py
import google.generativeai as genai
import logging
from typing import Dict, Any, Optional, List
from ..base.llm_base import LLMBase
from config.settings import GEMINI_CONFIG, LOGGING_CONFIG, GCP_CONFIG

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format']
)
logger = logging.getLogger(__name__)

class GeminiProcessor(LLMBase):
    """
    Gemini model processor for text summarization
    """
    def __init__(self):
        """Initialize Gemini model with configurations"""
        try:
            # Configure Gemini with API key only
            genai.configure(api_key=GCP_CONFIG['api_key'])

            # Initialize model with generation config
            self.model = genai.GenerativeModel(
                model_name=GEMINI_CONFIG['model'],
                generation_config=genai.types.GenerationConfig(
                    temperature=GEMINI_CONFIG['temperature'],
                    top_p=GEMINI_CONFIG['top_p'],
                    top_k=GEMINI_CONFIG['top_k'],
                    max_output_tokens=GEMINI_CONFIG['max_output_tokens'],
                )
            )
            logger.info("Successfully initialized Gemini model")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise

    def get_summary(self, ocr_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate summary from OCR data

        Args:
            ocr_data: Dictionary containing OCR results

        Returns:
            Dictionary containing summaries and metadata
        """
        try:
            # Get primary language for prompt selection
            primary_lang = self._get_primary_language(ocr_data['metadata']['language_codes'])
            language_settings = GEMINI_CONFIG['language_settings'][primary_lang]

            summaries = []
            # Process each page
            for page in ocr_data['pages']:
                # Extract text from blocks
                page_text = ' '.join([block['text'] for block in page['blocks']])
                if page_text:
                    page_summary = self._generate_page_summary(
                        page_text,
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

    def _get_primary_language(self, language_codes: List[str]) -> str:
        """Determine primary language from detected languages"""
        if not language_codes:
            return 'en'  # Default to English
        # Use the first detected language
        primary_lang = language_codes[0]
        # If language not in settings, default to English
        return primary_lang if primary_lang in GEMINI_CONFIG['language_settings'] else 'en'

    def _generate_page_summary(
        self,
        text: str,
        page_number: int,
        language_settings: Dict[str, Any]
    ) -> Optional[str]:
        """Generate summary for a single page"""
        try:
            prompt = language_settings['prompt_template'].format(text=text)
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            return None

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
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            return None

        except Exception as e:
            logger.error(f"Error generating overall summary: {str(e)}")
            return None
