"""
Tool Registry for Conditional Tool Registration

This module provides a registry system that allows tools to be conditionally registered
based on tier configuration, replacing direct @server.tool() decorators.
"""

import logging
from typing import Set, Optional, Callable

from auth.oauth_config import is_oauth21_enabled
from auth.scopes import is_read_only_mode, get_all_read_only_scopes

logger = logging.getLogger(__name__)

# Global registry of enabled tools
_enabled_tools: Optional[Set[str]] = None


def set_enabled_tools(tool_names: Optional[Set[str]]):
    """Set the globally enabled tools."""
    global _enabled_tools
    _enabled_tools = tool_names


def get_enabled_tools() -> Optional[Set[str]]:
    """Get the set of enabled tools, or None if all tools are enabled."""
    return _enabled_tools


def is_tool_enabled(tool_name: str) -> bool:
    """Check if a specific tool is enabled."""
    if _enabled_tools is None:
        return True  # All tools enabled by default
    return tool_name in _enabled_tools


def conditional_tool(server, tool_name: str):
    """
    Decorator that conditionally registers a tool based on the enabled tools set.

    Args:
        server: The FastMCP server instance
        tool_name: The name of the tool to register

    Returns:
        Either the registered tool decorator or a no-op decorator
    """

    def decorator(func: Callable) -> Callable:
        if is_tool_enabled(tool_name):
            logger.debug(f"Registering tool: {tool_name}")
            return server.tool()(func)
        else:
            logger.debug(f"Skipping tool registration: {tool_name}")
            return func

    return decorator


def wrap_server_tool_method(server):
    """
    Track tool registrations and filter them post-registration.
    """
    original_tool = server.tool
    server._tracked_tools = []

    def tracking_tool(*args, **kwargs):
        original_decorator = original_tool(*args, **kwargs)

        def wrapper_decorator(func: Callable) -> Callable:
            tool_name = func.__name__
            server._tracked_tools.append(tool_name)
            # Always apply the original decorator to register the tool
            return original_decorator(func)

        return wrapper_decorator

    server.tool = tracking_tool


def filter_server_tools(server):
    """Remove disabled tools from the server after registration.

    Bridges sync callers to the async implementation.
    """
    import asyncio

    asyncio.run(_filter_server_tools_async(server))


async def _filter_server_tools_async(server):
    """Async implementation of tool filtering using public FastMCP APIs."""
    enabled_tools = get_enabled_tools()
    oauth21_enabled = is_oauth21_enabled()
    if enabled_tools is None and not oauth21_enabled:
        return

    tools_removed = 0
    read_only_mode = is_read_only_mode()
    allowed_scopes = set(get_all_read_only_scopes()) if read_only_mode else None

    tool_list = await server.list_tools()
    tool_names = {t.name for t in tool_list}
    tools_to_remove = set()

    # 1. Tier filtering
    if enabled_tools is not None:
        for tool_name in tool_names:
            if not is_tool_enabled(tool_name):
                tools_to_remove.add(tool_name)

    # 2. OAuth 2.1 filtering
    if oauth21_enabled and "start_google_auth" in tool_names:
        tools_to_remove.add("start_google_auth")
        logger.info("OAuth 2.1 enabled: disabling start_google_auth tool")

    # 3. Read-only mode filtering
    if read_only_mode:
        for tool_name in tool_names:
            if tool_name in tools_to_remove:
                continue

            tool_obj = await server.get_tool(tool_name)
            func_to_check = tool_obj
            if hasattr(tool_obj, "fn"):
                func_to_check = tool_obj.fn

            required_scopes = getattr(
                func_to_check, "_required_google_scopes", []
            )

            if required_scopes:
                if not all(
                    scope in allowed_scopes for scope in required_scopes
                ):
                    logger.info(
                        f"Read-only mode: Disabling tool '{tool_name}' (requires write scopes: {required_scopes})"
                    )
                    tools_to_remove.add(tool_name)

    for tool_name in tools_to_remove:
        if hasattr(server, "local_provider"):
            server.local_provider.remove_tool(tool_name)
        else:
            server.remove_tool(tool_name)
        tools_removed += 1

    if tools_removed > 0:
        enabled_count = len(enabled_tools) if enabled_tools is not None else "all"
        mode = "Read-Only" if is_read_only_mode() else "Full"
        logger.info(
            f"Tool filtering: removed {tools_removed} tools, {enabled_count} enabled. Mode: {mode}"
        )
