import os

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Ntfy Reminder")

# Configuration
# You can set a default topic in .env or pass it as an argument
DEFAULT_TOPIC = os.getenv("NTFY_TOPIC", "lavee_goals_26_1ef3")


@mcp.tool()
def send_notification(message: str, title: str = "Iron Reminder", priority: int = 3) -> str:
    """
    Sends a push notification to your phone using ntfy.sh.

    Args:
        message: The content of the notification.
        title: The title of the notification (default: "Iron Reminder").
        priority: Priority level 1-5 (1=min, 3=default, 5=max/urgent).
    """
    topic = DEFAULT_TOPIC
    url = f"https://ntfy.sh/{topic}"

    try:
        response = requests.post(
            url, data=message.encode("utf-8"), headers={"Title": title, "Priority": str(priority)}
        )

        if response.status_code == 200:
            return f"Notification sent to ntfy.sh/{topic}"
        else:
            return f"Failed to send. Status: {response.status_code}, Body: {response.text}"

    except Exception as e:
        return f"Error sending notification: {str(e)}"


if __name__ == "__main__":
    mcp.run()
