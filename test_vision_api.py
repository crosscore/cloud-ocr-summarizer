# gcp-ocr-exp/test_vision_api.py
from src.processors.vision_processor import VisionProcessor
import logging
from config.settings import LOGGING_CONFIG, FILE_CONFIG
import os
import json

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['file_path']),
        logging.StreamHandler()  # 標準出力にも表示
    ]
)
logger = logging.getLogger(__name__)

def load_ocr_result(file_path: str):
    """Load OCR result from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading OCR result: {str(e)}")
        return None

def display_results(result_data):
    """
    Display the OCR results in a readable format

    Args:
        result_data: Processed data from Vision API
    """
    logger.info("=== OCR Processing Results ===")

    # Display metadata
    logger.info("\nMetadata:")
    logger.info(f"Total Pages: {len(result_data['responses'])}")
    logger.info(f"Detected Languages: {', '.join(result_data['responses'][0]['fullTextAnnotation']['pages'][0]['property']['detectedLanguages'][0]['languageCode'])}")
    logger.info(f"Average Confidence: {result_data['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']:.2f}")

    # Display sample text from each page
    logger.info("\nSample text from each page:")
    for page in result_data['responses']:
        logger.info(f"\nPage {page['context']['pageNumber']}:")
        logger.info(f"Page Confidence: {page['fullTextAnnotation']['pages'][0]['confidence']:.2f}")

        # Display first 3 text blocks from the page
        for i, block in enumerate(page['fullTextAnnotation']['pages'][0]['blocks'][:3], 1):
            logger.info(f"Block {i}:")
            text = ""
            for paragraph in block['paragraphs']:
                for word in paragraph['words']:
                    for symbol in word['symbols']:
                        text += symbol['text']
            logger.info(f"Text: {text}")
            logger.info(f"Confidence: {block['confidence']:.2f}")

def main():
    # Initialize processor
    try:
        processor = VisionProcessor()
    except Exception as e:
        logger.error(f"Failed to initialize VisionProcessor: {str(e)}")
        return

    # Process test file
    logger.info("Starting document processing...")

    test_file = os.path.join(FILE_CONFIG['input_directory'], "test_page.pdf")

    # Check if test file exists
    if not os.path.exists(test_file):
        logger.error(f"Test file not found: {test_file}")
        logger.info(f"Please place a test PDF file at: {test_file}")
        return

    result_path = processor.process_document(test_file)

    if result_path:
        logger.info("Successfully processed document")
        logger.info(f"Results saved to: {result_path}")
    else:
        logger.error("Failed to process document")

if __name__ == "__main__":
    main()
