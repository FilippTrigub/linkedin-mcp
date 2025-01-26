"""OAuth callback server implementation."""
import asyncio
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

class CallbackServer(HTTPServer):
    """Custom HTTP server with auth data storage."""
    def __init__(self, server_address, RequestHandlerClass, auth_received: asyncio.Event):
        super().__init__(server_address, RequestHandlerClass)
        self.auth_code = None
        self.state = None
        self.auth_received = auth_received


class CallbackHandler(BaseHTTPRequestHandler):
    """Handler for OAuth callback requests."""
    
    def do_GET(self):
        """Handle GET request to callback URL."""
        try:
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            code = params.get('code', [None])[0]
            state = params.get('state', [None])[0]
            
            if code and state:
                self.server.auth_code = code
                self.server.state = state
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authentication successful! You can close this window.")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authentication failed! Invalid callback parameters.")
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Internal server error!")
        finally:
            logger.info("Authentication received")
            self.server.auth_received.set()

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger."""
        logger.info(format % args)


class LinkedInCallbackServer:
    """Server to handle LinkedIn OAuth callbacks."""
    
    def __init__(self, port: int = 3000):
        self.port = port
        self.server: Optional[CallbackServer] = None
        self.auth_received = asyncio.Event()

    async def start(self) -> None:
        """Start the callback server."""
        try:
            self.server = CallbackServer(
                ('localhost', self.port), 
                CallbackHandler,
                self.auth_received
            )

            self.server_thread = Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            logger.info(f"Callback server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start callback server: {str(e)}")
            raise

    def stop(self) -> None:
        """Stop the callback server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Callback server stopped")

    async def wait_for_callback(self, timeout: float = 300) -> Tuple[Optional[str], Optional[str]]:
        """Wait for authentication callback.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (auth_code, state) or (None, None) on timeout
        """
        logger.info("Waiting for authentication callback...")
        try:
            await asyncio.wait_for(self.auth_received.wait(), timeout)
            return self.server.auth_code, self.server.state
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for authentication callback")
            return None, None
        finally:
            self.stop()