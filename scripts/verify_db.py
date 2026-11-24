#!/usr/bin/env python3
"""
PostgreSQL Local Database Verification Script
Tests connectivity, health probe, and queries all enterprise tables.
"""

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database.postgres import test_connection, get_connection, mask_database_url


def verify_database():
    print("=" * 60)
    print(" 🐘 PostgreSQL Local Database Health & Schema Verifier")
    print("=" * 60)
    masked_url = mask_database_url(settings.database_url)
    print(f"Connection Target: {masked_url}")

    start = time.perf_counter()
    is_healthy = test_connection(timeout=3)
    latency_ms = (time.perf_counter() - start) * 1000

    if not is_healthy:
        print(f"\n❌ Connection probe FAILED (Latency: {latency_ms:.2f}ms)")
        print("\nPossible solutions:")
        print("  1. Make sure the PostgreSQL container is running:")
        print("     docker compose up -d postgres")
        print("  2. Check container logs:")
        print("     docker compose logs postgres")
        print("  3. Verify credentials in your .env file match docker-compose.yml")
        sys.exit(1)

    print(f"\n✅ Connection SUCCESSFUL (Ping Latency: {latency_ms:.2f}ms)")

    tables = ["users", "customer_profiles", "documents", "approval_requests", "schema_migrations"]
    print("\nQuerying Enterprise Tables:")
    print("-" * 60)

    try:
        with get_connection(timeout=3) as conn:
            with conn.cursor() as cur:
                for table in tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) AS total FROM {table}")
                        row = cur.fetchone()
                        count = row["total"] if row else 0
                        print(f"  • {table:<25} : {count:>5} records")
                    except Exception as err:
                        print(f"  • {table:<25} : ⚠️ Error ({err})")

                # Sample record check
                cur.execute("SELECT username, email FROM users LIMIT 3")
                users = cur.fetchall()
                if users:
                    print("\nSample Users:")
                    for u in users:
                        print(f"  - {u['username']} ({u['email']})")

        print("-" * 60)
        print("✅ All enterprise database checks passed!")

    except Exception as exc:
        print(f"❌ Error querying tables: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    verify_database()
