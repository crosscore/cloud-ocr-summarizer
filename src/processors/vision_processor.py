# gcp-ocr-exp/src/processors/vision_processor.py
import os
import json
import logging
from typing import List, Dict, Any
from google.cloud import vision
from google.protobuf.json_format import MessageToJson
from config.settings import VISION_CONFIG, FILE_CONFIG, LOGGING_CONFIG, VISION_CONSTANTS
from src.utils.gcp_utils import GCPClient
import datetime

# Configure logging
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
        self.gcp_client = GCPClient()
        self.vision_client = self.gcp_client.vision_client

    def process_document(self, file_path: str) -> str:
        """
        Processes a document using the Vision API

        Args:
            file_path: Path to the document

        Returns:
            Path to the saved JSON file containing OCR results
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
            features = [
                {"type_": vision.Feature.Type.TEXT_DETECTION},
                {"type_": vision.Feature.Type.DOCUMENT_TEXT_DETECTION}
            ]
            mime_type = self._get_mime_type(file_path)
            input_config = {
                "gcs_source": {"uri": gcs_uri},
                "mime_type": mime_type
            }
            context = {
                "language_hints": self.vision_config['default_language_hints']
            }
            request = {
                "input_config": input_config,
                "features": features,
                "image_context": context,
                "pages": list(range(1, VISION_CONSTANTS['max_pages_per_request'] + 1))
            }

            # Perform OCR
            logger.info("Performing OCR...")
            response = self.vision_client.annotate_file(request=request)

            # Save results to file
            logger.info("Saving OCR results...")
            output_path = self._save_results(response, file_path)

            # Delete file from GCS (optional)
            if os.getenv('DELETE_AFTER_PROCESSING', 'false').lower() == 'true':
                logger.info(f"Deleting {gcs_uri} from GCS...")
                self.gcp_client.delete_from_storage(gcs_uri)

            return output_path

        except Exception as e:
            logger.error(f"Error processing document with Vision API: {str(e)}")
            return ""

    def _get_mime_type(self, file_path: str) -> str:
        """
        Gets the MIME type of a file based on its extension

        Args:
            file_path: Path to the file

        Returns:
            MIME type of the file
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        return VISION_CONSTANTS['supported_mime_types'].get(
            file_ext,
            'application/octet-stream'
        )

    def _parse_ocr_results(
        self,
        response: vision.AnnotateFileResponse
    ) -> List[Dict[str, Any]]:
        """
        Parses OCR results from the Vision API response

        Args:
            response: Vision API response

        Returns:
            List of dictionaries containing parsed OCR results
        """
        results = []
        for page_response in response.responses:
            page_data = {
                'page_number': page_response.context.page_number,
                'text': page_response.full_text_annotation.text,
                'blocks': [],
                'confidence': page_response.full_text_annotation.pages[0].confidence,
                'language': [
                    detected_language.language_code for detected_language
                    in page_response.full_text_annotation.pages[0].property.detected_languages
                ]
            }

            for block in page_response.full_text_annotation.pages[0].blocks:
                block_data = {
                    'text': '',
                    'confidence': block.confidence,
                    'bounding_box': {
                        'normalizedVertices': [
                            {
                                'x': vertex.x,
                                'y': vertex.y
                            } for vertex in block.bounding_box.normalized_vertices
                        ]
                    }
                }

                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        word_text = ''.join([
                            symbol.text for symbol in word.symbols
                        ])
                        block_data['text'] += word_text + ' '

                page_data['blocks'].append(block_data)

            results.append(page_data)

        return results

    def _save_results(self, response: vision.AnnotateFileResponse, input_file: str) -> str:
        """Saves OCR results to a JSON file"""
        try:
            timestamp = datetime.datetime.now().strftime(FILE_CONFIG['timestamp_format'])
            output_filename = FILE_CONFIG['vision_output_filename_pattern'].format(timestamp=timestamp)
            output_path = os.path.join(FILE_CONFIG['vision_output_directory'], output_filename)

            # Convert the response object to a JSON formatted string.
            json_string = MessageToJson(response)

            # Save the JSON string to a file.
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_string)

            logger.info(f"OCR results saved to: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save OCR results: {str(e)}")
            return ""

    def _save_audit_log(
        self,
        file_path: str,
        process_id: str,
        result_data: Dict[str, Any]
    ) -> None:
        """
        Save audit log entry

        Args:
            file_path: Original file path
            process_id: Process identifier
            result_data: Processed data
        """
        try:
            audit_data = {
                'timestamp': datetime.now().isoformat(),
                'file_name': os.path.basename(file_path),
                'process_id': process_id,
                'total_pages': result_data['metadata']['total_pages'],
                'average_confidence': result_data['metadata']['average_confidence'],
                'detected_languages': result_data['metadata']['language_codes']
            }

            log_file = os.path.join(
                FILE_CONFIG['output_directory'],
                'audit_log.jsonl'
            )

            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump(audit_data, f, ensure_ascii=False)
                f.write('\n')

        except Exception as e:
            logger.error(f"Error saving audit log: {str(e)}")
