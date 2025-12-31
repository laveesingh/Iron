# Ntfy.sh MCP Server

This is a tiny MCP server that allows Cursor AI to send push notifications to your devices using [ntfy.sh](https://ntfy.sh).

## Setup

1.  **Install Ntfy App**:
    *   Download the **Ntfy** app on your iPhone or Android.
    *   No account required.

2.  **Choose a Topic**:
    *   Pick a unique topic name (e.g., `lavee_goals_8492`).
    *   **Subscribe** to this topic in the Ntfy app on your phone.
    *   *Note: Anyone who knows the topic name can subscribe, so make it random/unique.*

3.  **Environment Variables**:
    *   Create a `.env` file in `project_iron/mcp_server/` (copy `.env.example`).
    *   Set your default topic:
        ```bash
        NTFY_TOPIC=lavee_goals_8492
        ```

4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage in Cursor

1.  Go to **Cursor Settings** > **Features** > **MCP**.
2.  Add New MCP Server:
    *   **Name**: `ntfy-reminder`
    *   **Type**: `command`
    *   **Command**: `python /absolute/path/to/project_iron/mcp_server/server.py`

## Testing

Ask Cursor:
"Send a notification 'Time to check logs' with high priority"
