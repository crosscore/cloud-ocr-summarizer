# gcp-ocr-exp/test_gemini.py
import os
import json
import logging
from config.settings import FILE_CONFIG, LOGGING_CONFIG
from generative.gcp.gemini import GeminiProcessor
import datetime

logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format']
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

def display_summary(summary_data: dict):
    """Display summary results in a readable format"""
    logger.info("=== Summary Results ===")

    # Display metadata
    logger.info("\nMetadata:")
    logger.info(f"Total Pages: {summary_data['metadata']['total_pages']}")
    logger.info(f"Primary Language: {summary_data['metadata']['primary_language']}")

    # Display page summaries
    logger.info("\nPage Summaries:")
    for page_summary in summary_data['page_summaries']:
        logger.info(f"\nPage {page_summary['page_number']}:")
        logger.info(page_summary['summary'])

    # Display overall summary if available
    if summary_data.get('overall_summary'):
        logger.info("\nOverall Summary:")
        logger.info(summary_data['overall_summary'])

def save_summary_result(summary_data: dict, original_filename: str):
    """Save summary results to a new JSON file"""
    try:
        output_dir = FILE_CONFIG['gemini_output_directory']
        timestamp = datetime.datetime.now().strftime(FILE_CONFIG['timestamp_format'])
        output_filename = FILE_CONFIG['gemini_output_filename_pattern'].format(timestamp=timestamp)
        output_file = os.path.join(output_dir, output_filename)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Summary saved to: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error saving summary: {str(e)}")
        return None

def main():
    # Initialize processor
    try:
        processor = GeminiProcessor()
    except Exception as e:
        logger.error(f"Failed to initialize GeminiProcessor: {str(e)}")
        return

    # Find the latest OCR result file
    output_dir = FILE_CONFIG['vision_output_directory']
    ocr_files = [f for f in os.listdir(output_dir) if f.startswith('vision_results_') and f.endswith('.json')]
    if not ocr_files:
        logger.error("No OCR result files found")
        return

    # Sort by creation time and get the latest
    latest_file = max(ocr_files, key=lambda f: os.path.getctime(os.path.join(output_dir, f)))
    print(f'latest_file: {latest_file}')
    file_path = os.path.join(output_dir, latest_file)

    # Load OCR result
    ocr_data = load_ocr_result(file_path)
    if not ocr_data:
        return

    # Generate summary
    logger.info("Generating summary...")
    summary_result = processor.get_summary(ocr_data)

    if summary_result:
        # Save summary
        save_summary_result(summary_result, file_path) # 変更: file_pathを渡す

        # Display results
        display_summary(summary_result)
    else:
        logger.error("Failed to generate summary")

if __name__ == "__main__":
    main()
