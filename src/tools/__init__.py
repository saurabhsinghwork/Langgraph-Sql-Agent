"""Tools package for LangGraph SQL Agents (MCA and GST).

Exposes database tool services, LangChain tool callables for schema inspection and validated SQL execution,
and agent tool factories for both the MCA and GST agents.
"""

# [Project-Defined Imports from src.tools.sql_tools]: Database tool service, singleton resolvers, and LangChain tools
from src.tools.sql_tools import (
    # [Project-Defined Class]: Core service executing schema introspection and SQL validation
    DatabaseToolService,
    # [Project-Defined Function]: Retrieves or initializes singleton DatabaseToolService by database type
    get_tool_service,
    # [Project-Defined Function]: Convenience helper returning DatabaseToolService for MCA database
    get_mca_tool_service,
    # [Project-Defined Function]: Convenience helper returning DatabaseToolService for GST database
    get_gst_tool_service,
    # [Project-Defined LangChain Tool]: Inspects MCA tables schema ('companies', 'directors')
    describe_mca_schema_tool,
    # [Project-Defined LangChain Tool]: Validates and runs read-only SQL on MCA database
    execute_mca_sql_query_tool,
    # [Project-Defined LangChain Tool]: Inspects GST table schema ('taxpayers')
    describe_gst_schema_tool,
    # [Project-Defined LangChain Tool]: Validates and runs read-only SQL on GST database
    execute_gst_sql_query_tool,
    # [Project-Defined Function]: Returns the list of tools bound to an agent based on target database
    get_tools_for_agent,
    # [Project-Defined LangChain Tool]: Backward compatibility alias for MCA schema inspection
    describe_schema_tool,
    # [Project-Defined LangChain Tool]: Backward compatibility alias for MCA SQL execution
    execute_sql_query_tool,
)

# [Built-in Python: __all__]: Public exports for the tools package
__all__ = [
    "DatabaseToolService",
    "get_tool_service",
    "get_mca_tool_service",
    "get_gst_tool_service",
    "describe_mca_schema_tool",
    "execute_mca_sql_query_tool",
    "describe_gst_schema_tool",
    "execute_gst_sql_query_tool",
    "get_tools_for_agent",
    "describe_schema_tool",
    "execute_sql_query_tool",
]
