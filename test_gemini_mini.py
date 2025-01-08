# test_gemini_basic.py
import os
import google.generativeai as genai
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gemini_basic():
    try:
        # Initialize Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        logger.info("Configuring Gemini API...")
        genai.configure(api_key=api_key)

        # Create model
        logger.info("Creating Gemini model...")
        model = genai.GenerativeModel('gemini-pro')

        # Simple test prompt
        test_prompt = "1+1の答えは何ですか？"

        logger.info("Sending test prompt to Gemini...")
        response = model.generate_content(test_prompt)

        if response.text:
            logger.info("Received response from Gemini:")
            logger.info("-" * 50)
            logger.info(response.text)
            logger.info("-" * 50)
            return True
        else:
            logger.error("No response text received from Gemini")
            return False

    except Exception as e:
        logger.error(f"Error during Gemini test: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting basic Gemini API test...")
    success = test_gemini_basic()
    if success:
        logger.info("Gemini API test completed successfully")
    else:
        logger.error("Gemini API test failed")
