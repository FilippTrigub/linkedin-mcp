# LinkedIn MCP Server

Post to LinkedIn directly from Claude Desktop with support for text and media attachments.

## Features

- Post text updates to LinkedIn
- Attach images and videos to posts
- Control post visibility (public/connections)
- OAuth2 authentication flow
- Secure token storage

## Tools

- `authenticate`: Authenticate with LinkedIn
- `create_post`: Create and share posts optionally with media attachments
  - state the file path to the relevant media file to attach it to the post

## Setup

1. Create a LinkedIn Developer App:
   ```
   Visit https://www.linkedin.com/developers/apps
   Create new app
   Add product permissions: Log In to LinkedIn and Share on LinkedIn 
   Configure OAuth redirect URL: http://localhost:3000/callback
   ```

2. Install
   Install `pipx` if not already installed
   ```bash
   pip install pipx
   ```
   Install linkedin-mcp
   ```bash
   pipx install linkedin-mcp
   ```

3. Create `.env` file:
   ```env
   LINKEDIN_CLIENT_ID=your_client_id
   LINKEDIN_CLIENT_SECRET=your_client_secret
   LINKEDIN_REDIRECT_URI=http://localhost:3000/callback
   ```

## Claude Desktop Configuration

Add the following configuration to `claude-desktop.json`:

```json
{
  "mcpServers": {
    "linkedin-mcp": {
      "command": "linkedin-mcp",
      "env": {
        "LINKEDIN_CLIENT_ID": "<yours>",
        "LINKEDIN_CLIENT_SECRET": "<yours>",
        "LINKEDIN_REDIRECT_URI": "<yours>"
      }
    }
  }
}
```

## Development
Clone the repository and install the package in editable mode:
   ```bash
   git clone https://github.com/FilippTrigub/linkedin-mcp.git
   cd linkedin-mcp
   uv venv
   ```
Run the server from development directory:

```json
{
  "mcpServers": {
    "linkedin-mcp": {
       "command": "uv",
      "args": [
        "--directory",
        "absolute\\path\\to\\linkedin-mcp",
        "run",
        "-m",
        "linkedin_mcp.server"
      ],
      "env": {
        "LINKEDIN_CLIENT_ID": "<yours>",
        "LINKEDIN_CLIENT_SECRET": "<yours>",
        "LINKEDIN_REDIRECT_URI": "<yours>"
      }
    }
  }
}
```
   

## License
MIT License