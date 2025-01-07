# gcp-ocr-exp/src/processors/vision_processor.py
from google.cloud import vision
import os
import json
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from ..utils.gcp_utils import GCPClient
from config.settings import (
    VISION_CONFIG,
    FILE_CONFIG,
    LOGGING_CONFIG,
    SECURITY_CONFIG,
    VISION_CONSTANTS,
    GCP_CONFIG
)

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    filename=LOGGING_CONFIG['file_path']
)
logger = logging.getLogger(__name__)

class VisionProcessor:
    def __init__(self):
        self.gcp_client = GCPClient()
        self.confidence_threshold = VISION_CONFIG['confidence_threshold']
        self.max_retries = VISION_CONFIG['max_retries']
        self.timeout = VISION_CONFIG['timeout']

    def _process_with_vision_api(self, gcs_uri: str) -> Optional[Dict[str, Any]]:
        """
        Process document with Vision API
        """
        try:
            # Create annotator client
            client = self.gcp_client.vision_client

            # For PDF/TIFF files, use document_text_detection
            feature = vision.Feature(
                type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION,
            )

            gcs_source = vision.GcsSource(uri=gcs_uri)
            input_config = vision.InputConfig(
                gcs_source=gcs_source,
                # Explicitly specify the mime type
                mime_type='application/pdf'
            )

            # Configure the output location for async requests
            gcs_destination = vision.GcsDestination(
                uri=f"gs://{GCP_CONFIG['storage_bucket']}/temp/output/"
            )
            output_config = vision.OutputConfig(
                gcs_destination=gcs_destination,
                batch_size=1  # Process one page at a time
            )

            # Create the async request
            async_request = vision.AsyncAnnotateFileRequest(
                features=[feature],
                input_config=input_config,
                output_config=output_config
            )

            # Make the request
            operation = client.async_batch_annotate_files(
                requests=[async_request]
            )

            logger.info("Waiting for Vision API operation to complete...")
            operation_result = operation.result(timeout=self.timeout)

            # Process the results
            extracted_data = {
                'pages': [],
                'metadata': {
                    'total_pages': 0,
                    'language_codes': set(),
                    'average_confidence': 0.0
                }
            }

            total_confidence = 0.0
            page_count = 0

            for response in operation_result.responses:
                # Get the JSON file from GCS
                output_bucket = self.gcp_client.storage_client.bucket(GCP_CONFIG['storage_bucket'])
                # List all the output files
                blobs = list(output_bucket.list_blobs(prefix='temp/output/'))

                for blob in blobs:
                    if blob.name.endswith('.json'):
                        # Download and parse the JSON content
                        json_content = blob.download_as_text()
                        ocr_response = json.loads(json_content)

                        # Process each page in the response
                        if 'responses' in ocr_response:
                            for page_response in ocr_response['responses']:
                                if 'fullTextAnnotation' in page_response:
                                    page_count += 1
                                    page_data = self._process_page_annotation(
                                        page_response['fullTextAnnotation'],
                                        page_count
                                    )
                                    extracted_data['pages'].append(page_data)
                                    total_confidence += page_data['confidence']
                                    extracted_data['metadata']['language_codes'].update(
                                        page_data['language']
                                    )

            # Update metadata
            if page_count > 0:
                extracted_data['metadata'].update({
                    'total_pages': page_count,
                    'language_codes': list(extracted_data['metadata']['language_codes']),
                    'average_confidence': total_confidence / page_count
                })

            # Clean up the output files
            for blob in blobs:
                blob.delete()

            return extracted_data

        except Exception as e:
            logger.error(f"Error processing with Vision API: {str(e)}")
            return None

    def _process_page_annotation(
        self,
        annotation: Dict[str, Any],
        page_number: int
    ) -> Dict[str, Any]:
        """
        Process a single page annotation
        """
        page_data = {
            'page_number': page_number,
            'blocks': [],
            'confidence': 0.0,
            'language': [],
            'text': annotation.get('text', '')
        }

        if 'pages' in annotation and len(annotation['pages']) > 0:
            page = annotation['pages'][0]

            # Extract language
            if 'property' in page and 'detectedLanguages' in page['property']:
                for lang in page['property']['detectedLanguages']:
                    if lang.get('languageCode'):
                        page_data['language'].append(lang['languageCode'])

            # Process blocks
            total_confidence = 0.0
            block_count = 0

            for block in page.get('blocks', []):
                if 'confidence' not in block or block['confidence'] < self.confidence_threshold:
                    continue

                block_text = ''
                for paragraph in block.get('paragraphs', []):
                    for word in paragraph.get('words', []):
                        word_text = ''.join(
                            symbol.get('text', '')
                            for symbol in word.get('symbols', [])
                        )
                        block_text += word_text + ' '

                block_data = {
                    'text': block_text.strip(),
                    'confidence': block['confidence'],
                    'bounding_box': block.get('boundingBox')
                }

                page_data['blocks'].append(block_data)
                total_confidence += block['confidence']
                block_count += 1

            if block_count > 0:
                page_data['confidence'] = total_confidence / block_count

        return page_data

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
                'language_codes': [],
                'average_confidence': 0.0
            }
        }

        try:
            total_confidence = 0.0
            page_count = 0
            detected_languages = set()

            # Vision APIのレスポンス構造に合わせて修正
            for response in vision_response.responses:
                if not hasattr(response, 'document'):
                    logger.warning("No document in response")
                    continue

                document = response.document

                # Process each page
                for page in document.pages:
                    page_data = {
                        'page_number': page_count + 1,
                        'blocks': [],
                        'confidence': 0.0,
                        'language': []
                    }

                    # Add detected languages to metadata
                    if hasattr(page, 'property') and hasattr(page.property, 'detected_languages'):
                        for language in page.property.detected_languages:
                            detected_languages.add(language.language_code)
                            if language.language_code not in page_data['language']:
                                page_data['language'].append(language.language_code)

                    # Process blocks of text
                    for block in page.blocks:
                        if not hasattr(block, 'confidence') or block.confidence < self.confidence_threshold:
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
                            ) if hasattr(block, 'bounding_box') else None
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
                'language_codes': list(detected_languages),
                'average_confidence': total_confidence / page_count if page_count > 0 else 0
            })

            # Log the structure for debugging
            logger.debug(f"Structured data: {json.dumps(structured_data, indent=2)}")

            return structured_data

        except Exception as e:
            logger.error(f"Error structuring Vision results: {str(e)}")
            return structured_data

    def _format_bounding_box(
        self,
        bounding_box: Any
    ) -> Dict[str, list[Dict[str, float]]]:
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
