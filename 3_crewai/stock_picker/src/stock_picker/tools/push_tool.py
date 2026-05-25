from mcp import os

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import requests
import os


class PushNotificationToolInput(BaseModel):
    """Input schema for PushNotificationTool."""
    message: str = Field(..., description="The message to be sent as a push notification.")

class PushNotificationTool(BaseTool):
    

    name: str = "Send a Push Notification"
    description: str = (
        "This tool is used to send a push notification to the user."
    )
    args_schema: Type[BaseModel] = PushNotificationToolInput

    def _run(self, message: str) -> str:
        pushover_user = os.getenv("PUSHOVER_USER")
        pushover_token = os.getenv("PUSHOVER_TOKEN")
        pushover_url = "https://api.pushover.net/1/messages.json"
        if not pushover_user or not pushover_token:
            return "Pushover credentials are not set."
        
        print(f"Push: {message}")
        payload = {"user": pushover_user, "token": pushover_token, "message": message}
        requests.post(pushover_url, data=payload)
        return '{"Notification": "ok"}'
