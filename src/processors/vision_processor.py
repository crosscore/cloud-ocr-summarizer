# gcp-ocr-exp/src/processors/vision_processor.py
import os
import json
import logging
from typing import Optional, Dict, Any, Tuple, List
from google.cloud import vision
from datetime import datetime
from ..utils.gcp_utils import GCPClient
from config.settings import (
    VISION_CONFIG,
    FILE_CONFIG,
    LOGGING_CONFIG,
    SECURITY_CONFIG,
    VISION_CONSTANTS
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    filename=LOGGING_CONFIG['file_path']
)
logger = logging.getLogger(__name__)

class VisionProcessor:
    """Process documents using Google Cloud Vision API"""

    def __init__(self):
        """Initialize the Vision processor with GCP client"""
        self.gcp_client = GCPClient()
        self.confidence_threshold = VISION_CONFIG['confidence_threshold']
        self.max_retries = VISION_CONFIG['max_retries']
        self.timeout = VISION_CONFIG['timeout']

    def process_document(self, file_path: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Process a document through the complete workflow

        Args:
            file_path: Path to the local document file

        Returns:
            Tuple of (success status, extracted data dictionary, error message if any)
        """
        try:
            # Validate file
            if not self._validate_file(file_path):
                return False, None, "Invalid file format or size"

            # Generate unique identifier for this processing
            process_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Upload to Cloud Storage
            file_name = os.path.basename(file_path)
            destination_blob_name = os.path.join(
                'temp',
                process_id,
                file_name
            )

            upload_success, gcs_uri = self.gcp_client.upload_to_storage(
                file_path,
                destination_blob_name
            )

            if not upload_success:
                return False, None, f"Failed to upload file: {gcs_uri}"

            # Process with Vision API
            result_data = self._process_with_vision_api(gcs_uri)
            if not result_data:
                return False, None, "Failed to process with Vision API"

            # Save results
            self._save_results(result_data, process_id)

            # Clean up temporary files if configured
            if SECURITY_CONFIG['delete_after_processing']:
                self.gcp_client.delete_from_storage(destination_blob_name)

            # Save audit log if enabled
            if SECURITY_CONFIG['enable_audit_logs']:
                self._save_audit_log(file_path, process_id, result_data)

            return True, result_data, None

        except Exception as e:
            error_msg = f"Error processing document: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def _validate_file(self, file_path: str) -> bool:
        """
        Validate file extension and size

        Args:
            file_path: Path to the file to validate

        Returns:
            bool: Whether the file is valid
        """
        try:
            # Check file extension
            extension = os.path.splitext(file_path)[1].lower()
            if extension not in FILE_CONFIG['allowed_extensions']:
                logger.error(f"Invalid file extension: {extension}")
                return False

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > FILE_CONFIG['max_file_size']:
                logger.error(
                    f"File size {file_size} exceeds limit of "
                    f"{FILE_CONFIG['max_file_size']}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return False

    def _process_with_vision_api(self, gcs_uri: str) -> Optional[Dict[str, Any]]:
        """
        Process document with Vision API

        Args:
            gcs_uri: URI of the document in Cloud Storage

        Returns:
            Optional[Dict[str, Any]]: Extracted data or None if processing failed
        """
        try:
            # Create the request
            input_config = vision.InputConfig(
                gcs_source=vision.GcsSource(uri=gcs_uri),
                mime_type=VISION_CONSTANTS['supported_mime_types']['.pdf']
            )

            # Configure features
            features = [
                vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
            ]

            # Configure output
            output_config = vision.OutputConfig(
                gcs_destination=vision.GcsDestination(
                    uri=f"gs://{self.gcp_client.storage_client.bucket(gcs_uri).name}/temp/"
                ),
                batch_size=VISION_CONFIG['batch_size']
            )

            # Create async request
            request = vision.AsyncAnnotateFileRequest(
                input_config=input_config,
                features=features,
                output_config=output_config
            )

            # Make the request
            operation = self.gcp_client.vision_client.async_batch_annotate_files(
                requests=[request]
            )

            # Wait for the operation to complete
            result = operation.result(timeout=self.timeout)

            # Process and structure the results
            extracted_data = self._structure_vision_results(result)

            return extracted_data

        except Exception as e:
            logger.error(f"Error processing with Vision API: {str(e)}")
            return None

    def _structure_vision_results(
        self,
        vision_response: Any
    ) -> Dict[str, Any]:
        """
        Structure the Vision API results into a consistent format

        Args:
            vision_response: Raw response from Vision API

        Returns:
            Dict[str, Any]: Structured data
        """
        structured_data = {
            'pages': [],
            'metadata': {
                'total_pages': 0,
                'language_codes': set(),
                'average_confidence': 0.0
            }
        }

        try:
            total_confidence = 0.0
            page_count = 0

            for response in vision_response.responses:
                document = response.full_text_annotation

                # Process each page
                for page in document.pages:
                    page_data = {
                        'page_number': page_count + 1,
                        'blocks': [],
                        'confidence': 0.0,
                        'language': document.pages[page_count].property.detected_languages
                    }

                    # Add detected languages to metadata
                    for language in page.property.detected_languages:
                        structured_data['metadata']['language_codes'].add(
                            language.language_code
                        )

                    # Process blocks of text
                    for block in page.blocks:
                        if block.confidence < self.confidence_threshold:
                            continue

                        block_text = ''
                        for paragraph in block.paragraphs:
                            for word in paragraph.words:
                                word_text = ''.join(
                                    [symbol.text for symbol in word.symbols]
                                )
                                block_text += word_text + ' '

                        block_data = {
                            'text': block_text.strip(),
                            'confidence': block.confidence,
                            'bounding_box': self._format_bounding_box(
                                block.bounding_box
                            )
                        }
                        page_data['blocks'].append(block_data)
                        page_data['confidence'] += block.confidence

                    # Calculate page average confidence
                    if page_data['blocks']:
                        page_data['confidence'] /= len(page_data['blocks'])
                        total_confidence += page_data['confidence']

                    structured_data['pages'].append(page_data)
                    page_count += 1

            # Update metadata
            structured_data['metadata'].update({
                'total_pages': page_count,
                'language_codes': list(structured_data['metadata']['language_codes']),
                'average_confidence': total_confidence / page_count if page_count > 0 else 0
            })

            return structured_data

        except Exception as e:
            logger.error(f"Error structuring Vision results: {str(e)}")
            return structured_data

    def _format_bounding_box(
        self,
        bounding_box: Any
    ) -> Dict[str, List[Dict[str, float]]]:
        """
        Format the bounding box coordinates

        Args:
            bounding_box: Vision API bounding box

        Returns:
            Dict with formatted coordinates
        """
        return {
            'vertices': [
                {'x': vertex.x, 'y': vertex.y}
                for vertex in bounding_box.vertices
            ]
        }

    def _save_results(
        self,
        result_data: Dict[str, Any],
        process_id: str
    ) -> None:
        """
        Save processing results to file

        Args:
            result_data: Processed data to save
            process_id: Unique identifier for this process
        """
        try:
            output_file = os.path.join(
                FILE_CONFIG['output_directory'],
                f'vision_results_{process_id}.json'
            )

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved results to {output_file}")

        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")

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
