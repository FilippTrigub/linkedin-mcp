"""OAuth callback server implementation."""
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Event as ThreadingEvent
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

class CallbackServer(HTTPServer):
    """Custom HTTP server with auth data storage."""
    def __init__(self, server_address, RequestHandlerClass, auth_received: ThreadingEvent):
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
                logger.info("Received auth code and state from LinkedIn")
                self.server.auth_code = code
                self.server.state = state
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authentication successful! You can close this window.")
            else:
                logger.error("Missing code or state in callback parameters")
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
            logger.info("Authentication received, setting event")
            self.server.auth_received.set()

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger."""
        logger.info(format % args)


class LinkedInCallbackServer:
    """Server to handle LinkedIn OAuth callbacks."""
    
    def __init__(self, port: int = 3000):
        self.port = port
        self.server: Optional[CallbackServer] = None
        # Use threading.Event instead of asyncio.Event for thread safety
        self.auth_received = ThreadingEvent()
        self.server_thread = None

    async def start(self) -> None:
        """Start the callback server."""
        try:
            logger.info(f"Starting callback server on port {self.port}")
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
            logger.info("Stopping callback server")
            self.server.shutdown()
            self.server.server_close()
            logger.info("Callback server stopped")

    async def wait_for_callback(self, timeout: float = 120) -> Tuple[Optional[str], Optional[str]]:
        """Wait for authentication callback with thread-safe approach.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (auth_code, state) or (None, None) on timeout
        """
        logger.info("Waiting for authentication callback...")
        
        # Check if the event was already set (thread race condition)
        if self.auth_received.is_set():
            logger.info("Event was already set before waiting")
            auth_code = self.server.auth_code
            state = self.server.state
            logger.debug(f"Auth code present: {auth_code is not None}, State present: {state is not None}")
            return auth_code, state
        
        try:
            # Use a separate thread to wait for the threading.Event
            # and set an asyncio.Event when it's done
            loop = asyncio.get_running_loop()
            asyncio_event = asyncio.Event()
            
            def wait_for_threading_event():
                # Wait for the threading event in a separate thread
                logger.debug("Starting thread to wait for threading event")
                result = self.auth_received.wait(timeout)
                logger.debug(f"Threading event wait completed with result: {result}")
                # Then notify the asyncio loop
                loop.call_soon_threadsafe(asyncio_event.set)
                logger.debug("Asyncio event set from thread")
            
            # Start the thread
            logger.debug("Creating thread for event monitoring")
            thread = threading.Thread(target=wait_for_threading_event)
            thread.daemon = True
            thread.start()
            
            # Wait for the asyncio event
            logger.debug("Waiting for asyncio event to be set")
            await asyncio.wait_for(asyncio_event.wait(), timeout)
            
            logger.info("Authentication callback received")
            auth_code = self.server.auth_code
            state = self.server.state
            logger.debug(f"Auth code present: {auth_code is not None}, State present: {state is not None}")
            
            return auth_code, state
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for authentication callback after {timeout} seconds")
            return None, None
        finally:
            self.stop()
