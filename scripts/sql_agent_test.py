import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.sql_agent import run_sql_agent


questions = [
    "How many users are in the database?",
    "How many customer profiles are there?",
    "How many documents are stored?",
    "How many approval requests are there?",
]


for question in questions:
    print("\n" + "=" * 60)
    print("Question:")
    print(question)

    try:
        result = run_sql_agent(question)

        print("\nGenerated SQL:")
        print(result["sql"])

        print("\nDatabase Result:")
        print(result["rows"])

    except Exception as exc:
        print("\nSQL Agent Error:")
        print(exc)