"""LinkedIn MCP Server Package.

This package provides a Model Context Protocol (MCP) server for LinkedIn integration.
"""
import logging

# Set up a null handler to avoid "No handler found" warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())

__version__ = "0.1.0"
