# gcp-ocr-exp/src/processors/vision_processor.py
import os
import json
import logging
from typing import List, Dict, Any
from google.cloud import vision
from google.protobuf.json_format import MessageToDict
from datetime import datetime
from config.settings import (
    VISION_CONFIG, FILE_CONFIG, LOGGING_CONFIG,
    VISION_CONSTANTS, VISION_OUTPUT_CONFIG
)
from src.utils.gcp_utils import GCPClient

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    filename=LOGGING_CONFIG['file_path']
)
logger = logging.getLogger(__name__)

class VisionProcessor:
    """Class for processing documents using Google Cloud Vision API"""

    def __init__(self):
        """Initializes the VisionProcessor with necessary configurations"""
        self.vision_config = VISION_CONFIG
        self.file_config = FILE_CONFIG
        self.output_config = VISION_OUTPUT_CONFIG
        self.gcp_client = GCPClient()
        self.vision_client = self.gcp_client.vision_client

    def process_document(self, file_path: str) -> str:
        """
        Processes a document using the Vision API

        Args:
            file_path: Path to the document

        Returns:
            str: Path to the saved JSON file containing OCR results
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Check if file size is within limits
            file_size = os.path.getsize(file_path)
            if file_size > self.file_config['max_file_size']:
                raise ValueError(
                    f"File size exceeds the maximum limit of "
                    f"{self.file_config['max_file_size']} bytes"
                )

            # Upload file to GCS
            logger.info(f"Uploading {file_path} to GCS...")
            success, gcs_uri = self.gcp_client.upload_to_storage(file_path)
            if not success:
                raise Exception(f"Failed to upload file to GCS: {gcs_uri}")

            # Prepare OCR request
            logger.info("Preparing OCR request...")

            input_config = vision.InputConfig(
                mime_type=self._get_mime_type(file_path),
                gcs_source=vision.GcsSource(uri=gcs_uri)
            )

            features = [
                vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
            ]

            # Process all pages
            pages = [i for i in range(1, VISION_CONSTANTS['max_pages_per_request'] + 1)]

            request = vision.BatchAnnotateFilesRequest(
                requests=[
                    vision.AnnotateFileRequest(
                        input_config=input_config,
                        features=features,
                        pages=pages
                    )
                ]
            )

            # Perform OCR
            logger.info("Performing OCR...")
            response = self.vision_client.batch_annotate_files(request)

            # Debug log
            if self.output_config['debug_mode']:
                logger.info(f"Raw response type: {type(response)}")

            # Save results
            logger.info("Saving OCR results...")
            output_path = self._save_results(response, file_path)

            # Delete file from GCS if configured
            if self.output_config.get('delete_after_processing', True):
                logger.info(f"Deleting {gcs_uri} from GCS...")
                self.gcp_client.delete_from_storage(gcs_uri)

            return output_path

        except Exception as e:
            logger.error(f"Error processing document with Vision API: {str(e)}")
            return ""

    def _get_mime_type(self, file_path: str) -> str:
        """Gets the MIME type of a file based on its extension"""
        file_ext = os.path.splitext(file_path)[1].lower()
        return VISION_CONSTANTS['supported_mime_types'].get(
            file_ext,
            'application/octet-stream'
        )

    def _save_results(self, response, input_file: str) -> str:
        """
        Saves OCR results to a JSON file based on configuration

        Args:
            response: Vision API response
            input_file: Original input file path

        Returns:
            str: Path to the saved JSON file
        """
        try:
            timestamp = datetime.datetime.now().strftime(FILE_CONFIG['timestamp_format'])
            output_filename = FILE_CONFIG['vision_output_filename_pattern'].format(timestamp=timestamp)
            output_path = os.path.join(FILE_CONFIG['vision_output_directory'], output_filename)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Process response according to selected mode
            result_dict = {
                'simple': self._process_simple_output,
                'detailed': self._process_detailed_output,
            }.get(self.output_config['output_mode'], self._process_simple_output)(response)

            # Save processed results
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)

            # Save raw response if configured
            if self.output_config['save_raw_response']:
                raw_output_path = output_path.replace('.json', '_raw.json')
                raw_dict = MessageToDict(response, preserving_proto_field_name=True)
                with open(raw_output_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_dict, f, ensure_ascii=False, indent=2)
                logger.info(f"Raw response saved to: {raw_output_path}")

            logger.info(f"OCR results saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to save OCR results: {str(e)}")
            return ""

    def _process_simple_output(self, response) -> Dict[str, Any]:
        """Process response in simple mode"""
        response_dict = {
            'files': []
        }

        for file_response in response.responses:
            file_data = {
                'total_pages': file_response.total_pages,
                'pages': []
            }

            if hasattr(file_response, 'responses') and file_response.responses:
                for page_response in file_response.responses:
                    if not hasattr(page_response, 'full_text_annotation'):
                        continue

                    text_annotation = page_response.full_text_annotation
                    page_data = {
                        'page_number': len(file_data['pages']) + 1,
                        'text': text_annotation.text
                    }

                    # Add language detection if available
                    if (hasattr(text_annotation.pages[0], 'property') and
                        hasattr(text_annotation.pages[0].property, 'detected_languages')):
                        page_data['detected_languages'] = [
                            {
                                'language_code': lang.language_code,
                                'confidence': lang.confidence
                            }
                            for lang in text_annotation.pages[0].property.detected_languages
                        ]

                    file_data['pages'].append(page_data)

            response_dict['files'].append(file_data)

        return response_dict

    def _process_detailed_output(self, response) -> Dict[str, Any]:
        """Process response in detailed mode"""
        response_dict = {
            'files': []
        }

        for file_response in response.responses:
            file_data = {
                'total_pages': file_response.total_pages,
                'pages': []
            }

            if hasattr(file_response, 'responses') and file_response.responses:
                for page_response in file_response.responses:
                    if not hasattr(page_response, 'full_text_annotation'):
                        continue

                    text_annotation = page_response.full_text_annotation
                    page_data = {
                        'page_number': len(file_data['pages']) + 1,
                        'text': text_annotation.text,
                        'width': text_annotation.pages[0].width,
                        'height': text_annotation.pages[0].height,
                        'blocks': []
                    }

                    # Add language detection
                    if (hasattr(text_annotation.pages[0], 'property') and
                        hasattr(text_annotation.pages[0].property, 'detected_languages')):
                        page_data['detected_languages'] = [
                            {
                                'language_code': lang.language_code,
                                'confidence': lang.confidence
                            }
                            for lang in text_annotation.pages[0].property.detected_languages
                        ]

                    # Process blocks if requested
                    if self.output_config['include_bounding_boxes']:
                        for block in text_annotation.pages[0].blocks:
                            if (block.confidence <
                                self.output_config['min_confidence_threshold']):
                                continue

                            block_data = {
                                'bounding_box': {
                                    'vertices': [
                                        {'x': vertex.x, 'y': vertex.y}
                                        for vertex in block.bounding_box.normalized_vertices
                                    ]
                                }
                            }

                            if self.output_config['include_confidence']:
                                block_data['confidence'] = block.confidence

                            if self.output_config['include_word_level']:
                                block_data['text'] = ''
                                block_data['words'] = []

                                for paragraph in block.paragraphs:
                                    for word in paragraph.words:
                                        word_text = ''.join(
                                            symbol.text for symbol in word.symbols
                                        )
                                        block_data['text'] += word_text + ' '

                                        if word.confidence >= self.output_config['min_confidence_threshold']:
                                            word_data = {'text': word_text}
                                            if self.output_config['include_confidence']:
                                                word_data['confidence'] = word.confidence
                                            block_data['words'].append(word_data)

                            page_data['blocks'].append(block_data)

                    file_data['pages'].append(page_data)

            response_dict['files'].append(file_data)

        return response_dict

    def _process_full_output(self, response) -> Dict[str, Any]:
        """Process response in full mode - preserve complete API response structure"""
        try:
            full_dict = MessageToDict(response, preserving_proto_field_name=True)

            if isinstance(full_dict, dict) and 'responses' in full_dict:
                return full_dict
            return {'responses': [full_dict]}

        except Exception as e:
            logger.error(f"Error in full output processing: {str(e)}")
            return {'error': str(e)}

    # Utility methods for custom output processing
    def _extract_languages(self, response) -> List[Dict[str, Any]]:
        """Extract language information from response"""
        languages = []
        try:
            if (hasattr(response, 'full_text_annotation') and
                hasattr(response.full_text_annotation.pages[0], 'property')):
                for lang in response.full_text_annotation.pages[0].property.detected_languages:
                    languages.append({
                        'language_code': lang.language_code,
                        'confidence': lang.confidence
                    })
        except Exception as e:
            logger.debug(f"Error extracting languages: {str(e)}")
        return languages

    def _extract_confidence(self, response) -> float:
        """Extract confidence score from response"""
        try:
            if hasattr(response, 'full_text_annotation'):
                return response.full_text_annotation.pages[0].confidence
        except Exception as e:
            logger.debug(f"Error extracting confidence: {str(e)}")
        return 0.0

    def _extract_blocks(self, response) -> List[Dict[str, Any]]:
        """Extract block information from response"""
        blocks = []
        try:
            if hasattr(response, 'full_text_annotation'):
                for block in response.full_text_annotation.pages[0].blocks:
                    block_data = {
                        'confidence': block.confidence,
                        'bounding_box': {
                            'vertices': [
                                {'x': vertex.x, 'y': vertex.y}
                                for vertex in block.bounding_box.normalized_vertices
                            ]
                        },
                        'text': ''
                    }

                    # Extract text from block
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = ''.join(symbol.text for symbol in word.symbols)
                            block_data['text'] += word_text + ' '

                    block_data['text'] = block_data['text'].strip()
                    blocks.append(block_data)
        except Exception as e:
            logger.debug(f"Error extracting blocks: {str(e)}")
        return blocks

    def _extract_words(self, response) -> List[Dict[str, Any]]:
        """Extract word-level information from response"""
        words = []
        try:
            if hasattr(response, 'full_text_annotation'):
                for block in response.full_text_annotation.pages[0].blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_data = {
                                'text': ''.join(symbol.text for symbol in word.symbols),
                                'confidence': word.confidence,
                                'bounding_box': {
                                    'vertices': [
                                        {'x': vertex.x, 'y': vertex.y}
                                        for vertex in word.bounding_box.normalized_vertices
                                    ]
                                }
                            }
                            words.append(word_data)
        except Exception as e:
            logger.debug(f"Error extracting words: {str(e)}")
        return words

    def _add_page_dimensions(self, page_data: Dict[str, Any],
                            text_annotation: Any,
                            desired_fields: set) -> None:
        """Add page dimension information to page data"""
        try:
            if 'width' in desired_fields:
                page_data['width'] = text_annotation.pages[0].width
            if 'height' in desired_fields:
                page_data['height'] = text_annotation.pages[0].height
        except Exception as e:
            logger.debug(f"Error adding page dimensions: {str(e)}")

    def _extract_breaks(self, response) -> List[Dict[str, Any]]:
        """Extract break information from response"""
        breaks = []
        try:
            if hasattr(response, 'full_text_annotation'):
                for block in response.full_text_annotation.pages[0].blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            for symbol in word.symbols:
                                if (hasattr(symbol, 'property') and
                                    hasattr(symbol.property, 'detected_break')):
                                    breaks.append({
                                        'text': symbol.text,
                                        'break_type': symbol.property.detected_break.type_,
                                        'position': {
                                            'x': symbol.bounding_box.normalized_vertices[0].x,
                                            'y': symbol.bounding_box.normalized_vertices[0].y
                                        }
                                    })
        except Exception as e:
            logger.debug(f"Error extracting breaks: {str(e)}")
        return breaks
