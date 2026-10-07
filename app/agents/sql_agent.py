from app.database.sql_executor import (
    execute_readonly_query,
    validate_sql,
)
from app.llm.gemini import llm


DATABASE_SCHEMA = """
PostgreSQL database: aegisdb

Available tables:

users
- id
- username
- email
- created_at
- updated_at

customer_profiles
- id
- customer_id
- age
- tenure_months
- monthly_charges
- total_charges
- support_tickets
- usage_hours
- contract_type
- payment_method
- has_partner

documents
- id
- ...
- created_at

approval_requests
- id
- approval_id
- tool
- arguments
- agent
- status
- created_at
- approved_at
- rejected_at
- thread_id

Rules:
- Generate ONLY SELECT queries.
- Use only the tables and columns listed above.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
  CREATE, GRANT, or REVOKE.
- Do not modify database data.
- Do not access system tables.
- Return only the SQL query.
"""


def generate_sql(question: str) -> str:
    prompt = f"""
You are a PostgreSQL SQL generation agent.

Convert the user's natural-language question into
ONE safe PostgreSQL SELECT query.

Database schema:
{DATABASE_SCHEMA}

Rules:
1. Return ONLY SQL.
2. Do not use markdown code fences.
3. Only generate SELECT queries.
4. Never modify data.
5. Use only the listed tables and columns.
6. Do not invent tables or columns.
7. For count questions, use COUNT(*).
8. For aggregate questions, use appropriate SQL functions.
9. Do not include explanations.

User question:
{question}

SQL:
"""

    response = llm.generate_raw(prompt)

    sql = response.strip()

    # Remove accidental markdown code fences.
    sql = sql.replace("```sql", "")
    sql = sql.replace("```", "")
    sql = sql.strip()

    return sql


def run_sql_agent(question: str) -> dict:
    """
    Convert natural language to SQL,
    validate the generated SQL,
    execute the query,
    and return the result.
    """

    sql = generate_sql(question)

    # Validate BEFORE sending anything to PostgreSQL.
    safe_sql = validate_sql(sql)

    # Execute only validated read-only SQL.
    rows = execute_readonly_query(safe_sql)

    return {
        "question": question,
        "sql": safe_sql,
        "rows": rows,
    }