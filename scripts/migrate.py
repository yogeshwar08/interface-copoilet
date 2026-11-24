#!/usr/bin/env python3
"""
Database Migration and Schema Initialization Script
Executes idempotent SQL DDL and seed data against the configured local PostgreSQL database.
Tracks applied schema versions in the `schema_migrations` table.
"""

import sys
import logging
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg
from psycopg.rows import dict_row

from app.config import settings
from app.database.postgres import mask_database_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

INIT_SQL_PATH = Path(__file__).resolve().parent.parent / "docker" / "init.sql"


def run_migrations():
    masked_url = mask_database_url(settings.database_url)
    logger.info(f"Target Database: {masked_url}")

    if not INIT_SQL_PATH.exists():
        logger.error(f"Migration file not found at: {INIT_SQL_PATH}")
        sys.exit(1)

    sql_content = INIT_SQL_PATH.read_text(encoding="utf-8")

    try:
        logger.info("Connecting to PostgreSQL...")
        with psycopg.connect(settings.database_url, connect_timeout=10, row_factory=dict_row) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                logger.info("Applying schema definitions and idempotent seed data...")
                cur.execute(sql_content)

                # Record migration if table exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(50) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    INSERT INTO schema_migrations (version, name)
                    VALUES ('001_initial_schema', 'Initial enterprise tables and seed records')
                    ON CONFLICT (version) DO NOTHING;
                """)

                # Validate expected tables
                expected_tables = ["users", "customer_profiles", "documents", "approval_requests", "schema_migrations"]
                logger.info("Verifying schema tables and row counts:")
                for table in expected_tables:
                    cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
                    row = cur.fetchone()
                    count = row["count"] if row else 0
                    logger.info(f"  ✓ Table '{table}': {count} records")

        logger.info("✅ Database migration and schema verification completed successfully!")
        return True

    except Exception as exc:
        logger.error(f"❌ Migration failed: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
