# gcp-ocr-exp/test_run.py
from src.processors.vision_processor import VisionProcessor
import logging
from config.settings import LOGGING_CONFIG
import os
import json

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format']
)
logger = logging.getLogger(__name__)

def display_results(result_data):
    """
    Display the OCR results in a readable format

    Args:
        result_data: Processed data from Vision API
    """
    logger.info("=== OCR Processing Results ===")

    # Display metadata
    logger.info("\nMetadata:")
    logger.info(f"Total Pages: {result_data['metadata']['total_pages']}")
    logger.info(f"Detected Languages: {', '.join(result_data['metadata']['language_codes'])}")
    logger.info(f"Average Confidence: {result_data['metadata']['average_confidence']:.2f}")

    # Display sample text from each page
    logger.info("\nSample text from each page:")
    for page in result_data['pages']:
        logger.info(f"\nPage {page['page_number']}:")
        logger.info(f"Page Confidence: {page['confidence']:.2f}")

        # Display first 3 text blocks from the page
        for i, block in enumerate(page['blocks'][:3], 1):
            logger.info(f"Block {i}:")
            logger.info(f"Text: {block['text']}")
            logger.info(f"Confidence: {block['confidence']:.2f}")

def main():
    # Initialize processor
    processor = VisionProcessor()

    # Process test file
    logger.info("Starting document processing...")

    test_file = "data/input/3page.pdf"  # テスト用PDFファイルのパス

    # Check if test file exists
    if not os.path.exists(test_file):
        logger.error(f"Test file not found: {test_file}")
        return

    success, result_data, error = processor.process_document(test_file)

    if success:
        logger.info("Successfully processed document")

        # Display results
        display_results(result_data)

        # Show output file location
        output_dir = os.path.join(os.path.dirname(test_file), '..', 'output')
        logger.info(f"\nDetailed results have been saved to: {output_dir}")

        # Display list of output files
        output_files = [f for f in os.listdir(output_dir) if f.startswith('vision_results_')]
        if output_files:
            logger.info("Output files:")
            for file in output_files:
                logger.info(f"- {file}")
    else:
        logger.error(f"Failed to process document: {error}")

def cleanup_test_files():
    """
    Clean up test output files (optional)
    """
    try:
        output_dir = "data/output"
        for file in os.listdir(output_dir):
            if file.startswith('vision_results_') or file == 'audit_log.jsonl':
                os.remove(os.path.join(output_dir, file))
        logger.info("Cleaned up test output files")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test OCR processing with Vision API')
    parser.add_argument('--cleanup', action='store_true', help='Clean up test output files')
    parser.add_argument('--input', type=str, help='Input PDF file path (optional)')

    args = parser.parse_args()

    if args.cleanup:
        cleanup_test_files()
    else:
        main()
