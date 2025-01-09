import os
import time
from anthropic import AnthropicVertex
import logging
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_claude_api():
    """Simple test for Claude API with detailed logging"""
    try:
        logger.info(f"Project ID: {os.getenv('GCP_PROJECT_ID')}")
        logger.info("Creating HTTP client...")

        # Initialize httpx client with detailed settings
        timeout = httpx.Timeout(30.0, read=None)
        client = httpx.Client(
            transport=httpx.HTTPTransport(retries=0),
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )

        logger.info("Initializing Claude client...")
        anthropic_client = AnthropicVertex(
            project_id=os.getenv('GCP_PROJECT_ID'),
            region="us-east5",
            http_client=client,
        )

        logger.info("Sending request to Claude API...")
        message = anthropic_client.messages.create(
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": "Hi"
                }
            ],
            model="claude-3-5-sonnet-v2@20241022",
        )

        logger.info("Response received successfully")
        logger.info(f"Response text: {message.content[0].text}")

    except Exception as e:
        logger.error(f"Error details: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response headers: {e.response.headers}")
    finally:
        client.close()
        logger.info("Client closed")

if __name__ == "__main__":
    logger.info("Starting Claude API test...")
    test_claude_api()
