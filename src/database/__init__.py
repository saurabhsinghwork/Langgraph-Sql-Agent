"""Database package for LangGraph SQL Agents (MCA and GST)."""

# [Project-Defined Imports from src.database.connection]: Connection engine getters and connection testers
from src.database.connection import (
    get_engine,
    get_mca_engine,
    get_gst_engine,
    test_connection,
    test_all_connections,
)
# [Project-Defined Imports from src.database.schema_inspector]: Schema inspector and approved tables constants
from src.database.schema_inspector import (
    SchemaInspector,
    APPROVED_TABLES,
    APPROVED_MCA_TABLES,
    APPROVED_GST_TABLES,
)
# [Project-Defined Imports from src.database.seeder]: Database seeding functions
from src.database.seeder import (
    seed_database,
    seed_mca_database,
    seed_gst_database,
)

# [Built-in Python: __all__]: Public exports for the database package
__all__ = [
    "get_engine",
    "get_mca_engine",
    "get_gst_engine",
    "test_connection",
    "test_all_connections",
    "SchemaInspector",
    "APPROVED_TABLES",
    "APPROVED_MCA_TABLES",
    "APPROVED_GST_TABLES",
    "seed_database",
    "seed_mca_database",
    "seed_gst_database",
]
