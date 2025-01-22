# LinkedIn MCP Server

Post to LinkedIn directly from Claude Desktop with support for text and media attachments.

## Features

- Post text updates to LinkedIn
- Attach images and videos to posts
- Control post visibility (public/connections)
- OAuth2 authentication flow
- Secure token storage

## Tools

- `authenticate`: Start LinkedIn OAuth flow
- `handle_oauth_callback`: Complete authentication
- `create_post`: Create posts

## Setup

1. Create a LinkedIn Developer App:
   ```
   Visit https://www.linkedin.com/developers/apps
   Create new app
   Add product permissions: Log In to LinkedIn and Share on LinkedIn 
   Configure OAuth redirect URL: http://localhost:3000/callback
   ```

2. Clone and install:
   ```bash
   git clone https://github.com/FilippTrigub/linkedin-mcp.git
   cd linkedin-mcp
   uv venv
   ```

3. Create `.env` file:
   ```env
   LINKEDIN_CLIENT_ID=your_client_id
   LINKEDIN_CLIENT_SECRET=your_client_secret
   LINKEDIN_REDIRECT_URI=http://localhost:3000/callback
   ```

## Claude Desktop Configuration
