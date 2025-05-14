"""Configure logging for the LinkedIn MCP server."""
import logging
import os
import sys

def configure_logging(log_level="INFO", log_file=None):
    """Configure logging with enhanced format and optional file output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to save logs
    """
    # Parse the log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}", file=sys.stderr)
        numeric_level = logging.INFO
    
    # Basic configuration for logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    handlers = []
    
    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # Add file handler if specified
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure the root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=handlers
    )
    
    # Set more conservative log levels for some noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Our code should get the specified log level
    logger = logging.getLogger("linkedin_mcp")
    logger.setLevel(numeric_level)
    
    logger.debug(f"Logging configured with level: {log_level}")
    if log_file:
        logger.debug(f"Logs will be saved to: {log_file}")
