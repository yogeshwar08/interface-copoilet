import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.sql_executor import (
    execute_readonly_query,
    validate_sql,
)


# ============================================================
# VALID QUERIES
# ============================================================

valid_queries = [
    "SELECT COUNT(*) FROM users",
    "SELECT COUNT(*) FROM customer_profiles",
    "SELECT COUNT(*) FROM documents",
    "SELECT COUNT(*) FROM approval_requests",
]


print("=" * 60)
print("VALID SQL TESTS")
print("=" * 60)

for query in valid_queries:

    try:

        safe_query = validate_sql(query)

        print("\nOriginal:")
        print(query)

        print("Validated:")
        print(safe_query)

    except Exception as exc:

        print("\nFAILED:")
        print(query)

        print("Error:")
        print(exc)


# ============================================================
# INVALID QUERIES
# ============================================================

invalid_queries = [
    "DROP TABLE users",
    "DELETE FROM users",
    "UPDATE users SET username = 'hacker'",
    "INSERT INTO users (username) VALUES ('hacker')",
    "SELECT * FROM pg_catalog.pg_tables",
    "SELECT * FROM employees",
    "SELECT * FROM users; DROP TABLE users",
]


print("\n")
print("=" * 60)
print("INVALID SQL TESTS")
print("=" * 60)

for query in invalid_queries:

    try:

        safe_query = validate_sql(query)

        print("\nSECURITY FAILURE:")
        print(query)

        print("Was incorrectly accepted as:")
        print(safe_query)

    except Exception as exc:

        print("\nBLOCKED:")
        print(query)

        print("Reason:")
        print(exc)
# ============================================================
# LIMIT PROTECTION TEST
# ============================================================

print("\n")
print("=" * 60)
print("LIMIT PROTECTION TEST")
print("=" * 60)

limit_test_queries = [
    "SELECT username, email FROM users",
    "SELECT customer_id, age FROM customer_profiles",
    "SELECT id, status FROM approval_requests",
]

for query in limit_test_queries:

    try:

        safe_query = validate_sql(query)

        print("\nOriginal:")
        print(query)

        print("Validated:")
        print(safe_query)

    except Exception as exc:

        print("\nFAILED:")
        print(query)

        print("Error:")
        print(exc)

# ============================================================
# REAL DATABASE TEST
# ============================================================

print("\n")
print("=" * 60)
print("DATABASE EXECUTION TEST")
print("=" * 60)

try:

    result = execute_readonly_query(
        "SELECT COUNT(*) FROM users"
    )

    print("\nQuery:")
    print("SELECT COUNT(*) FROM users")

    print("\nResult:")
    print(result)

except Exception as exc:

    print("\nDatabase execution failed:")
    print(exc)