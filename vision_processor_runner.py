from src.processors.vision_processor import VisionProcessor
from src.utils.token_counter import TokenCounter
import logging
from config import LOGGING_CONFIG, FILE_CONFIG
import os
import json

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['file_path']),
        logging.StreamHandler()
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

def display_results(result_data, result_path):
    """
    Display the OCR results in a readable format and log token statistics
    Supports both simple and detailed JSON formats
    """
    logger.info("=== OCR Processing Results ===")

    # Display response structure metadata
    total_responses = len(result_data.get('responses', []))
    logger.info("\nDocument Overview:")
    logger.info(f"Total Responses: {total_responses}")

    total_pages = 0
    detected_languages = set()
    page_confidences = []

    # Process each response and collect metadata
    for response in result_data.get('responses', []):
        for page in response.get('pages', []):
            total_pages += 1
            if 'detected_languages' in page:
                for lang in page['detected_languages']:
                    detected_languages.add(lang['language_code'])
            if 'confidence' in page:
                page_confidences.append(page['confidence'])

    # Display document metadata
    logger.info(f"Total Pages: {total_pages}")
    if detected_languages:
        logger.info(f"Detected Languages: {', '.join(sorted(detected_languages))}")
    if page_confidences:
        avg_confidence = sum(page_confidences) / len(page_confidences)
        logger.info(f"Average Confidence: {avg_confidence:.2f}")

    # Calculate and log token statistics
    token_stats = TokenCounter.count_json_file(result_path)
    logger.info("\nStructure Analysis:")
    logger.info(f"Total tokens: {token_stats['total_tokens']}")
    structure_stats = token_stats['structure_stats']
    logger.info(f"Blocks: {structure_stats['blocks']}")
    logger.info(f"Paragraphs: {structure_stats['paragraphs']}")
    logger.info(f"Words: {structure_stats['words']}")

    # Display page contents
    logger.info("\nPage Contents:")
    for response in result_data.get('responses', []):
        for page in response.get('pages', []):
            page_number = page.get('page_number', 'Unknown')
            logger.info(f"\nPage {page_number}:")

            # Check if the page has blocks (detailed mode)
            if 'blocks' in page and page['blocks']:
                # Display first 3 blocks
                for i, block in enumerate(page['blocks'][:3], 1):
                    if block.get('text'):
                        logger.info(f"  Block {i}: {block['text']}")

                        # Optionally display confidence for each block
                        if block.get('confidence') is not None:
                            logger.info(f"    Confidence: {block['confidence']:.2f}")

                        # Display block type if available
                        if block.get('block_type'):
                            logger.info(f"    Type: {block['block_type']}")

            # If no blocks are present (simple mode), display the text directly
            elif 'text' in page:
                lines = page['text'].split('\n')
                # Display first 3 lines
                for i, line in enumerate(lines[:3], 1):
                    if line.strip():  # Only show non-empty lines
                        logger.info(f"  Line {i}: {line}")

            # Add a separator line between pages for better readability
            logger.info("  " + "-" * 50)


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

        # Load and display results
        result_data = load_ocr_result(result_path)
        if result_data:
            display_results(result_data, result_path)
        else:
            logger.error("Failed to load OCR results")
    else:
        logger.error("Failed to process document")

if __name__ == "__main__":
    main()
