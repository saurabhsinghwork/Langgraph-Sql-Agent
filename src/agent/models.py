"""Result and status models for the LangGraph SQL Agent."""

# [Built-in Python] Postponed evaluation of type annotations for Python 3.7+
from __future__ import annotations

# [Standard Library: enum] Enum class used to define constrained set of status values
from enum import Enum

# [Standard Library: typing] Generic type hints used for static analysis and IDE autocomplete
from typing import Any, Dict, List, Optional

# [Third-party Library: pydantic] Data validation and parsing framework
# BaseModel: base class that provides automatic data validation and JSON serialization
# Field: function providing metadata, descriptions, and default values for schema generation
from pydantic import BaseModel, Field


# [Project-Defined Enum Class]: Inherits from Python's built-in 'str' and 'enum.Enum'
# Enforces a strict set of permitted execution status outcomes defined in PRD and SPECS
class AgentStatus(str, Enum):
    """Execution status outcomes defined in PRD and SPECS."""

    # [Class Variable: str]: Query successfully validated, executed, and explained
    SUCCESS = "success"
    # [Class Variable: str]: Question is materially ambiguous and needs user input
    CLARIFICATION_REQUIRED = "clarification_required"
    # [Class Variable: str]: Candidate SQL violated security policy (e.g. DROP, table not allowed)
    VALIDATION_REJECTED = "validation_rejected"
    # [Class Variable: str]: Database engine failed to execute the query (e.g. connection error)
    EXECUTION_FAILED = "execution_failed"
    # [Class Variable: str]: Recovery retry limit reached without a successful query
    RETRY_EXHAUSTED = "retry_exhausted"
    # [Class Variable: str]: Missing API keys or invalid environment configuration
    CONFIGURATION_ERROR = "configuration_error"


# [Project-Defined Data Model Class]: Inherits from 'pydantic.BaseModel'
# Serves as the canonical data contract returned by the agent for each independent question
class AgentResult(BaseModel):
    """The canonical result contract returned by the agent for each independent question."""

    # [Attribute]: Uses created enum 'AgentStatus' validated by Pydantic 'Field'
    status: AgentStatus = Field(
        description="The outcome status of the agent execution.",
    )
    # [Attribute]: Built-in type 'str', original question submitted by the user
    question: str = Field(
        description="The user's original independent question.",
    )
    # [Attribute]: Built-in type 'str', plain English answer grounded in returned rows
    explanation: str = Field(
        default="",
        description="Natural language summary grounded in the query results or failure explanation.",
    )
    # [Attribute]: Optional 'str', the exact SQL query generated and executed (if any)
    sql_query: Optional[str] = Field(
        default=None,
        description="The generated and executed SQL query (if one was run).",
    )
    # [Attribute]: List of 'str', column headers returned from SQL execution
    columns: List[str] = Field(
        default_factory=list,
        description="List of column names returned by query execution.",
    )
    # [Attribute]: List of dicts, bounded data rows returned by database execution
    rows: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Bounded rows returned by database execution.",
    )
    # [Attribute]: Built-in type 'int', count of records fetched
    row_count: int = Field(
        default=0,
        description="Count of rows returned in the result set.",
    )
    # [Attribute]: Optional 'str', sanitized error description if execution or validation failed
    error_message: Optional[str] = Field(
        default=None,
        description="Sanitized user-facing error message (contains no credentials).",
    )
    # [Attribute]: Optional 'str', clarification question presented to user if query was vague
    clarification_prompt: Optional[str] = Field(
        default=None,
        description="Specific question asked to user when the request is materially ambiguous.",
    )
    # [Attribute]: Built-in type 'int', number of correction retry attempts made during this run
    retry_count: int = Field(
        default=0,
        description="Number of SQL correction retries attempted during this request.",
    )
    # [Attribute]: Optional 'str', the search keyword or term identified for full-text search highlighting
    search_term: Optional[str] = Field(
        default=None,
        description="The search keyword or phrase used for full-text search and result highlighting.",
    )
    # [Attribute]: List of 'str', unique word tokens and roots identified for whole-word highlighting
    highlight_tokens: List[str] = Field(
        default_factory=list,
        description="List of search keyword tokens, roots, and expanded terms to highlight in results.",
    )

