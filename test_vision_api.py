from src.processors.vision_processor import VisionProcessor
from src.utils.token_counter import TokenCounter
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

def display_results(result_data, result_path):
    """
    Display the OCR results in a readable format and log token statistics

    Args:
        result_data: Processed data from Vision API
        result_path: Path to the result JSON file
    """
    logger.info("=== OCR Processing Results ===")

    # Display response structure metadata
    total_responses = len(result_data.get('responses', []))
    logger.info("\nResponse Structure:")
    logger.info(f"Total Responses: {total_responses}")

    total_pages = 0
    detected_languages = set()
    total_confidence = 0
    page_count = 0

    # Process each response and collect metadata
    for response in result_data.get('responses', []):
        for page in response.get('pages', []):
            page_count += 1
            total_pages += 1
            if 'detected_languages' in page:
                for lang in page['detected_languages']:
                    detected_languages.add(lang['language_code'])
            if 'confidence' in page:
                total_confidence += page['confidence']

    # Calculate and display overall metadata
    logger.info("\nDocument Metadata:")
    logger.info(f"Total Pages Processed: {total_pages}")
    if detected_languages:
        logger.info(f"Detected Languages: {', '.join(sorted(detected_languages))}")
    if page_count > 0:
        avg_confidence = total_confidence / page_count
        logger.info(f"Average Document Confidence: {avg_confidence:.2f}")

    # Calculate and log token statistics
    token_stats = TokenCounter.count_json_file(result_path)
    logger.info("\nToken Statistics:")
    logger.info(f"Total tokens: {token_stats['total_tokens']}")

    structure_stats = token_stats['structure_stats']
    logger.info(f"Pages: {structure_stats['pages']}")
    logger.info(f"Blocks: {structure_stats['blocks']}")
    logger.info(f"Paragraphs: {structure_stats['paragraphs']}")
    logger.info(f"Words: {structure_stats['words']}")
    if 'average_confidence' in structure_stats:
        logger.info(f"Structure Average Confidence: {structure_stats['average_confidence']:.2f}")

    # Display detailed page information
    logger.info("\nDetailed Page Information:")
    for response in result_data.get('responses', []):
        for page in response.get('pages', []):
            page_number = page.get('page_number', 'Unknown')
            logger.info(f"\nPage {page_number}:")
            if 'confidence' in page:
                logger.info(f"Confidence: {page['confidence']:.2f}")

            # Process blocks
            blocks = page.get('blocks', [])
            if blocks:
                logger.info(f"Number of blocks: {len(blocks)}")
                # Display first 3 blocks as sample
                for i, block in enumerate(blocks[:3], 1):
                    logger.info(f"  Block {i}:")
                    logger.info(f"  Text: {block.get('text', '')}")
                    if 'confidence' in block:
                        logger.info(f"  Confidence: {block['confidence']:.2f}")

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
