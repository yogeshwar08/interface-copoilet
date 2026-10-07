from app.database.postgres import test_connection
from app.database.sql_executor import execute_readonly_query


print(
    "PostgreSQL connection:",
    test_connection(),
)


queries = [
    "SELECT COUNT(*) AS user_count FROM users",
    "SELECT COUNT(*) AS customer_count FROM customer_profiles",
    "SELECT COUNT(*) AS document_count FROM documents",
    "SELECT COUNT(*) AS approval_count FROM approval_requests",
]


for query in queries:
    print("\nSQL:")
    print(query)

    rows = execute_readonly_query(query)

    print("Result:")
    print(rows)