"""
MCP tools for worklog management.

This module provides a collection of MCP tools for managing worklogs,
including user management, posting, reading, searching, and analytics.
"""

from .register import register_tools

# Also import the log_mcp_tool decorator for backward compatibility
# with individual tool modules that need it
try:
    # Import from the original tools module for backward compatibility
    from ..tools import log_mcp_tool

    __all__ = ["register_tools", "log_mcp_tool"]
except ImportError:
    # If the original tools module doesn't exist yet, just export register_tools
    __all__ = ["register_tools"]
