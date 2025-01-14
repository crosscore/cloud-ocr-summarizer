import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
from google.cloud import vision
from config import (
    VISION_CONFIG, FILE_CONFIG,
    VISION_CONSTANTS, VISION_OUTPUT_CONFIG
)
from src.utils.gcp_utils import GCPClient
from src.utils.token_counter import TokenCounter

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
        Saves OCR results and logs token statistics without modifying the output JSON structure
        """
        try:
            timestamp = datetime.now().strftime(FILE_CONFIG['timestamp_format'])
            output_filename = FILE_CONFIG['vision_output_filename_pattern'].format(timestamp=timestamp)
            output_path = os.path.join(FILE_CONFIG['vision_output_directory'], output_filename)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Process and save results
            result_dict = {
                'simple': self._process_simple_output,
                'detailed': self._process_detailed_output,
            }.get(self.output_config['output_mode'], self._process_simple_output)(response)

            # Save JSON result
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)

            # Save raw response if configured
            if self.output_config.get('save_raw_response', True):
                raw_output_path = output_path.replace('.json', '_raw.txt')
                with open(raw_output_path, 'w', encoding='utf-8') as f:
                    f.write(str(response))
                logger.info(f"Raw response saved to: {raw_output_path}")

            # Log token statistics
            token_stats = TokenCounter.count_json_file(output_path)
            logger.info(f"Document processing completed. Total tokens: {token_stats['total_tokens']}, "
                    f"Pages: {token_stats['structure_stats']['pages']}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to save OCR results: {str(e)}")
            return ""

    def _process_simple_output(self, response) -> Dict[str, Any]:
        """Process response in simple mode with added type and confidence information"""
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

                        # Extract text blocks for type and confidence information
                        blocks = []
                        if text_annotation and text_annotation.pages:
                            page = text_annotation.pages[0]
                            for block in page.blocks:
                                block_text = ''
                                for paragraph in block.paragraphs:
                                    for word in paragraph.words:
                                        word_text = ''
                                        for symbol in word.symbols:
                                            word_text += symbol.text
                                        block_text += word_text + ' '

                                blocks.append({
                                    'text': block_text.strip(),
                                    'confidence': block.confidence if self.output_config['include_confidence'] else None,
                                    'block_type': 'TEXT'  # Default to TEXT type in simple mode
                                })

                        page_data = {
                            'page_number': len(file_data['pages']) + 1,
                            'text': text_annotation.text if text_annotation else '',
                            'confidence': text_annotation.pages[0].confidence if text_annotation and text_annotation.pages else 0.0,
                            'blocks': blocks
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
        """
        Process response in detailed mode with enhanced bounding box information

        Args:
            response: Vision API response object

        Returns:
            Dict containing processed response data
        """
        response_dict = {
            'responses': [],
            'total_pages': getattr(response.responses[0], 'total_pages', len(response.responses))
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

                    # Process blocks with enhanced bounding box information
                    for block in page.blocks:
                        if (block.confidence <
                            self.output_config['min_confidence_threshold']):
                            continue

                        block_data = self._process_block(block)
                        page_data['blocks'].append(block_data)

                    file_data['pages'].append(page_data)

                response_dict['responses'].append(file_data)

        except Exception as e:
            logger.error(f"Error in detailed output processing: {str(e)}")
            raise

        return response_dict

    def _process_block(self, block) -> Dict[str, Any]:
        """
        Process a single block with enhanced bounding box information

        Args:
            block: Vision API block object

        Returns:
            Dict containing processed block data
        """
        block_types = {
            0: 'UNKNOWN',  # Unknown block type
            1: 'TEXT',     # Regular text block
            2: 'TABLE',    # Table block
            3: 'PICTURE',  # Image block
            4: 'RULER',    # Horizontal/vertical line box
            5: 'BARCODE',  # Barcode block
        }
        block_data = {
            'text': '',
            'confidence': block.confidence if self.output_config['include_confidence'] else None,
            'block_type': block_types.get(int(str(block.block_type)), 'UNKNOWN'),
        }

        # Add normalized bounding box coordinates
        if self.output_config['include_bounding_boxes'] and hasattr(block, 'bounding_box'):
            block_data['bounding_box'] = {
                'normalized_vertices': [
                    {
                        'x': vertex.x,
                        'y': vertex.y
                    }
                    for vertex in block.bounding_box.normalized_vertices
                ]
            }

        # Process paragraphs
        if hasattr(block, 'paragraphs'):
            block_data['paragraphs'] = []
            for paragraph in block.paragraphs:
                para_data = self._process_paragraph(paragraph)
                block_data['paragraphs'].append(para_data)

                # Append paragraph text to block text
                block_data['text'] += para_data['text'] + '\n'

        block_data['text'] = block_data['text'].strip()
        return block_data

    def _process_paragraph(self, paragraph) -> Dict[str, Any]:
        """
        Process a single paragraph with detailed information

        Args:
            paragraph: Vision API paragraph object

        Returns:
            Dict containing processed paragraph data
        """
        para_data = {
            'text': '',
            'confidence': paragraph.confidence if self.output_config['include_confidence'] else None,
        }

        # Add normalized bounding box coordinates for paragraph
        if self.output_config['include_bounding_boxes'] and hasattr(paragraph, 'bounding_box'):
            para_data['bounding_box'] = {
                'normalized_vertices': [
                    {
                        'x': vertex.x,
                        'y': vertex.y
                    }
                    for vertex in paragraph.bounding_box.normalized_vertices
                ]
            }

        # Process words
        if hasattr(paragraph, 'words'):
            para_data['words'] = []
            for word in paragraph.words:
                word_data = self._process_word(word)
                para_data['words'].append(word_data)
                para_data['text'] += word_data['text'] + ' '

        para_data['text'] = para_data['text'].strip()
        return para_data

    def _process_word(self, word) -> Dict[str, Any]:
        """
        Process a single word with detailed information

        Args:
            word: Vision API word object

        Returns:
            Dict containing processed word data
        """
        word_data = {
            'text': '',
            'confidence': word.confidence if self.output_config['include_confidence'] else None,
        }

        # Add normalized bounding box coordinates for word
        if self.output_config['include_bounding_boxes'] and hasattr(word, 'bounding_box'):
            word_data['bounding_box'] = {
                'normalized_vertices': [
                    {
                        'x': vertex.x,
                        'y': vertex.y
                    }
                    for vertex in word.bounding_box.normalized_vertices
                ]
            }

        # Process symbols
        if hasattr(word, 'symbols'):
            word_text = ''
            for symbol in word.symbols:
                symbol_text = symbol.text
                word_text += symbol_text

            word_data['text'] = word_text

        return word_data
