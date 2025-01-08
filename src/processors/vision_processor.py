# gcp-ocr-exp/src/processors/vision_processor.py
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
from google.cloud import vision
from google.protobuf.json_format import MessageToDict
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
            print(response)

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
        Saves OCR results including raw response
        """
        try:
            timestamp = datetime.now().strftime(FILE_CONFIG['timestamp_format'])
            output_filename = FILE_CONFIG['vision_output_filename_pattern'].format(timestamp=timestamp)
            output_path = os.path.join(FILE_CONFIG['vision_output_directory'], output_filename)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 通常の処理用の出力の保存
            result_dict = {
                'simple': self._process_simple_output,
                'detailed': self._process_detailed_output,
            }.get(self.output_config['output_mode'], self._process_simple_output)(response)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)

            # Raw responseの保存
            if self.output_config.get('save_raw_response', True):
                raw_output_path = output_path.replace('.json', '_raw.txt')

                # Protobufレスポンスを文字列として保存
                with open(raw_output_path, 'w', encoding='utf-8') as f:
                    f.write(str(response))

                logger.info(f"Raw response saved to: {raw_output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to save OCR results: {str(e)}")
            return ""

    def _process_simple_output(self, response) -> Dict[str, Any]:
        """Process response in simple mode"""
        response_dict = {
            'responses': []
        }

        try:
            for file_response in response.responses:
                file_data = {
                    'pages': []
                }

                for page_response in file_response.responses:
                    if hasattr(page_response, 'full_text_annotation'):
                        text_annotation = page_response.full_text_annotation
                        page_data = {
                            'page_number': len(file_data['pages']) + 1,
                            'text': text_annotation.text if text_annotation else '',
                            'confidence': text_annotation.pages[0].confidence if text_annotation and text_annotation.pages else 0.0
                        }

                        # Add language detection if available
                        if (text_annotation and
                            text_annotation.pages and
                            hasattr(text_annotation.pages[0], 'property') and
                            hasattr(text_annotation.pages[0].property, 'detected_languages')):
                            page_data['detected_languages'] = [
                                {
                                    'language_code': lang.language_code,
                                    'confidence': lang.confidence
                                }
                                for lang in text_annotation.pages[0].property.detected_languages
                            ]

                        file_data['pages'].append(page_data)

                response_dict['responses'].append(file_data)

        except Exception as e:
            logger.error(f"Error in simple output processing: {str(e)}")

        return response_dict

    def _process_detailed_output(self, response) -> Dict[str, Any]:
        """Process response in detailed mode"""
        response_dict = {
            'responses': []
        }

        try:
            for file_response in response.responses:
                file_data = {
                    'pages': []
                }

                for page_response in file_response.responses:
                    if not hasattr(page_response, 'full_text_annotation'):
                        continue

                    text_annotation = page_response.full_text_annotation
                    if not text_annotation or not text_annotation.pages:
                        continue

                    page = text_annotation.pages[0]
                    page_data = {
                        'page_number': len(file_data['pages']) + 1,
                        'text': text_annotation.text,
                        'width': page.width,
                        'height': page.height,
                        'confidence': page.confidence,
                        'blocks': []
                    }

                    # Add language detection
                    if (hasattr(page, 'property') and
                        hasattr(page.property, 'detected_languages')):
                        page_data['detected_languages'] = [
                            {
                                'language_code': lang.language_code,
                                'confidence': lang.confidence
                            }
                            for lang in page.property.detected_languages
                        ]

                    # Process blocks
                    for block in page.blocks:
                        if (block.confidence <
                            self.output_config['min_confidence_threshold']):
                            continue

                        block_data = {
                            'text': '',
                            'confidence': block.confidence if self.output_config['include_confidence'] else None
                        }

                        # Add bounding box if configured
                        if self.output_config['include_bounding_boxes']:
                            vertices = block.bounding_box.vertices
                            block_data['bounding_box'] = {
                                'vertices': [
                                    {'x': vertex.x, 'y': vertex.y}
                                    for vertex in vertices
                                ]
                            }

                        # Extract text and build block content
                        for paragraph in block.paragraphs:
                            for word in paragraph.words:
                                word_text = ''.join(
                                    symbol.text for symbol in word.symbols
                                )
                                block_data['text'] += word_text + ' '

                        block_data['text'] = block_data['text'].strip()
                        page_data['blocks'].append(block_data)

                    file_data['pages'].append(page_data)

                response_dict['responses'].append(file_data)

        except Exception as e:
            logger.error(f"Error in detailed output processing: {str(e)}")
            raise

        return response_dict
