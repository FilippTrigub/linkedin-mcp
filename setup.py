"""Setup file for the LinkedIn MCP package."""
from setuptools import setup, find_packages

setup(
    name="linkedin-mcp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "mcp[cli]>=1.2.0",
        "httpx>=0.24.0",
        "python-jose[cryptography]>=3.3.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
)