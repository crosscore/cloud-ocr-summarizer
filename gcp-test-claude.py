from anthropic import AnthropicVertex
from dotenv import load_dotenv
import os
load_dotenv()

ANTHROPIC_VERTEX_PROJECT_ID = os.getenv("ANTHROPIC_VERTEX_PROJECT_ID")
LOCATION="us-east5"

client = AnthropicVertex(region=LOCATION, project_id=ANTHROPIC_VERTEX_PROJECT_ID)

message = client.messages.create(
  max_tokens=1024,
  messages=[
    {
      "role": "user",
      "content": "Send me a recipe for banana bread.",
    }
  ],
  model="claude-3-5-sonnet-v2@20241022",
)
print(message.model_dump_json(indent=2))
