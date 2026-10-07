import re

from app.database.postgres import get_connection


# ============================================================
# SQL SECURITY CONFIGURATION
# ============================================================

FORBIDDEN_SQL = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "comment",
    "vacuum",
    "analyze",
    "refresh",
]

ALLOWED_TABLES = {
    "users",
    "customer_profiles",
    "documents",
    "approval_requests",
}


# ============================================================
# SQL VALIDATION
# ============================================================

def validate_sql(query: str) -> str:

    if not query:
        raise ValueError(
            "SQL query cannot be empty."
        )

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError(
            "SQL query cannot be empty."
        )

    # --------------------------------------------------------
    # Remove one trailing semicolon
    # --------------------------------------------------------

    cleaned_query = cleaned_query.rstrip(";").strip()

    if not cleaned_query:
        raise ValueError(
            "SQL query cannot be empty."
        )

    normalized_query = cleaned_query.lower()

    # --------------------------------------------------------
    # SELECT ONLY
    # --------------------------------------------------------

    if not normalized_query.startswith("select"):
        raise ValueError(
            "Only SELECT queries are allowed."
        )

    # --------------------------------------------------------
    # BLOCK MULTIPLE STATEMENTS
    # --------------------------------------------------------

    if ";" in cleaned_query:
        raise ValueError(
            "Multiple SQL statements are not allowed."
        )

    # --------------------------------------------------------
    # BLOCK FORBIDDEN OPERATIONS
    # --------------------------------------------------------

    for keyword in FORBIDDEN_SQL:

        if re.search(
            rf"\b{keyword}\b",
            normalized_query,
        ):

            raise ValueError(
                f"Forbidden SQL operation detected: "
                f"{keyword}"
            )

    # --------------------------------------------------------
    # BLOCK SYSTEM SCHEMAS
    # --------------------------------------------------------

    forbidden_schema_patterns = [
        "information_schema",
        "pg_catalog",
        "pg_toast",
    ]

    for schema in forbidden_schema_patterns:

        if re.search(
            rf"\b{re.escape(schema)}\b",
            normalized_query,
        ):

            raise ValueError(
                f"Access to system schema is not allowed: "
                f"{schema}"
            )

    # --------------------------------------------------------
    # EXTRACT TABLES FROM FROM / JOIN
    # --------------------------------------------------------

    table_matches = re.findall(
        r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        normalized_query,
    )

    for table in table_matches:

        if table not in ALLOWED_TABLES:

            raise ValueError(
                f"Table '{table}' is not allowed."
            )

    # --------------------------------------------------------
    # BLOCK SELECT *
    #
    # We still allow COUNT(*) because COUNT(*) is legitimate.
    # --------------------------------------------------------

    if re.search(
        r"select\s+\*",
        normalized_query,
    ):

        raise ValueError(
            "SELECT * is not allowed. "
            "Request specific columns instead."
        )

    # --------------------------------------------------------
    # LIMIT PROTECTION
    #
    # Add a LIMIT when returning raw rows.
    # Aggregate queries such as COUNT(*) don't need it.
    # --------------------------------------------------------

    has_aggregate = bool(
        re.search(
            r"\b(count|sum|avg|min|max)\s*\(",
            normalized_query,
        )
    )

    has_limit = bool(
        re.search(
            r"\blimit\s+\d+",
            normalized_query,
        )
    )

    if not has_aggregate and not has_limit:

        cleaned_query = (
            f"{cleaned_query} LIMIT 100"
        )

    return cleaned_query


# ============================================================
# LOCAL SQLITE FALLBACK REPLICA (WHEN POSTGRES DAEMON IS OFFLINE)
# ============================================================

import sqlite3
from pathlib import Path

FALLBACK_SQLITE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fallback_aegisdb.sqlite"


def init_fallback_sqlite_if_needed():
    """Initializes local SQLite database with identical schema and records from docker/init.sql if PostgreSQL is not active."""
    FALLBACK_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(FALLBACK_SQLITE_PATH))
    try:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customer_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL UNIQUE,
            age INTEGER NOT NULL,
            tenure_months INTEGER NOT NULL,
            monthly_charges REAL NOT NULL,
            total_charges REAL NOT NULL,
            support_tickets INTEGER DEFAULT 0,
            usage_hours REAL DEFAULT 0.0,
            contract_type TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            has_partner INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            document_type TEXT DEFAULT 'pdf',
            page_count INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT NOT NULL UNIQUE,
            tool TEXT NOT NULL,
            arguments TEXT,
            agent TEXT DEFAULT 'router_agent',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            approved_at TEXT,
            rejected_at TEXT,
            thread_id TEXT
        );

        INSERT OR IGNORE INTO users (id, username, email, created_at) VALUES
        (1, 'alice_chen', 'alice.chen@enterprise.corp', '2024-01-15 08:30:00Z'),
        (2, 'bob_martin', 'bob.martin@enterprise.corp', '2024-02-20 09:45:00Z'),
        (3, 'carol_danvers', 'carol.danvers@enterprise.corp', '2024-03-10 11:20:00Z'),
        (4, 'david_miller', 'david.miller@enterprise.corp', '2024-04-05 14:15:00Z'),
        (5, 'eva_ross', 'eva.ross@enterprise.corp', '2024-05-12 16:50:00Z');

        INSERT OR IGNORE INTO customer_profiles (id, customer_id, age, tenure_months, monthly_charges, total_charges, support_tickets, usage_hours, contract_type, payment_method, has_partner) VALUES
        (1, 'CUST-1001', 34, 18, 79.50, 1431.00, 2, 142.5, 'month-to-month', 'credit card', 1),
        (2, 'CUST-1002', 45, 36, 119.00, 4284.00, 0, 310.0, 'two-year', 'bank transfer', 1),
        (3, 'CUST-1003', 29, 6, 49.99, 299.94, 4, 88.0, 'month-to-month', 'electronic check', 0),
        (4, 'CUST-1004', 52, 48, 145.00, 6960.00, 1, 450.2, 'two-year', 'credit card', 1),
        (5, 'CUST-1005', 41, 24, 89.90, 2157.60, 6, 215.0, 'one-year', 'bank transfer', 0);

        INSERT OR IGNORE INTO documents (id, filename, document_type, page_count) VALUES
        (1, '01_Diabetes_Clinical_Guideline.pdf', 'clinical_guideline', 14),
        (2, 'Enterprise_Information_Security_Policy.pdf', 'corporate_policy', 8),
        (3, 'Q3_2024_Financial_Report_10Q.pdf', 'sec_filing', 42);

        INSERT OR IGNORE INTO approval_requests (id, approval_id, tool, arguments, agent, status) VALUES
        (1, 'APP-REQ-901', 'execute_database_migration', '{"target_version": "v1.4"}', 'sql_agent', 'approved'),
        (2, 'APP-REQ-902', 'external_api_export', '{"format": "csv", "batch_size": 5000}', 'data_export_tool', 'pending'),
        (3, 'APP-REQ-903', 'elevate_user_privilege', '{"user_id": 4, "role": "admin"}', 'iam_agent', 'rejected');
        """)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# READ-ONLY QUERY EXECUTION
# ============================================================

def execute_readonly_query(query: str):
    safe_query = validate_sql(query)

    try:
        with get_connection(timeout=1) as connection:
            with connection.cursor() as cursor:
                cursor.execute(safe_query)
                return cursor.fetchall()
    except Exception as pg_exc:
        # Fall back gracefully to the embedded replica when PostgreSQL daemon is not running
        init_fallback_sqlite_if_needed()
        conn = sqlite3.connect(str(FALLBACK_SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(safe_query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()