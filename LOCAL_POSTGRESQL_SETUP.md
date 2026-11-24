# 🐘 Local Self-Hosted PostgreSQL Setup Guide

> **Production-grade, zero-cloud dependency guide for running PostgreSQL locally using Docker for the Agentic Enterprise Knowledge Copilot.**

---

## 📌 Table of Contents

- [Architectural Overview](#-architectural-overview)
- [Prerequisites](#-prerequisites)
- [Environment Configuration (`.env`)](#-environment-configuration-env)
- [Quickstart: Starting the Local Database](#-quickstart-starting-the-local-database)
- [Developer Commands Reference](#-developer-commands-reference)
- [Running Schema Migrations](#-running-schema-migrations)
- [Automated Backup & Restore System](#-automated-backup--restore-system)
- [Recovering Data from Render (If Access is Restored)](#-recovering-data-from-render-if-access-is-restored)
- [Backend Connection & Thread-Safe Connection Pooling](#-backend-connection--thread-safe-connection-pooling)
- [Verification & Testing](#-verification--testing)
- [Troubleshooting & Common Docker Issues](#-troubleshooting--common-docker-issues)

---

## 🏗️ Architectural Overview

This system replaces remote cloud-hosted PostgreSQL instances (such as Render or cloud DBaaS providers) with a self-hosted, containerized PostgreSQL 16 database running on your local machine via Docker.

```
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend (Host Machine)             │
│  - app.main (Lifespan Startup & Shutdown Management)   │
│  - app.database.postgres (Thread-Safe Connection Pool) │
│  - app.database.sql_executor (Read-Only AST Firewall)  │
└───────────────────────────┬────────────────────────────┘
                            │
               TCP Port 5432 (127.0.0.1)
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│        Docker Container: enterprise_copilot_postgres   │
│  - Image: postgres:16-alpine                           │
│  - Bound exclusively to loopback (127.0.0.1:5432)       │
│  - Persistent Docker Named Volume: postgres_data       │
│  - Auto-initialization from docker/init.sql            │
│  - Automated Healthcheck: pg_isready                   │
└────────────────────────────────────────────────────────┘
```

### Key Engineering Principles
1. **Loopback Binding (`127.0.0.1:5432`)**: The database port is bound to `127.0.0.1` rather than `0.0.0.0` to prevent exposure across your local area network (LAN) or public interfaces.
2. **Persistent Storage (`postgres_data`)**: Database records, schemas, and sequences persist across container restarts, stops, and computer reboots.
3. **Thread-Safe Connection Pooling (`psycopg3`)**: Uses a connection pool with health probes (`SELECT 1`), automatic stale connection pruning, transaction rollbacks before checkout, and clean lifespan shutdowns.
4. **Credential Protection**: Passwords are never committed to source control or logged in plain text. All logs sanitize database URLs using password masking (`postgresql://user:***@host:port/db`).

---

## 💻 Prerequisites

- **Docker Desktop** (or Docker Engine on Linux) running and operational.
- **Python 3.11+** with virtual environment (`.venv`) activated.
- **PowerShell** (Windows) or **Bash** (macOS/Linux).

---

## ⚙️ Environment Configuration (`.env`)

Ensure your local `.env` file contains the following PostgreSQL settings:

```ini
# ============================================================
# Database Configuration (Locally Self-Hosted PostgreSQL via Docker)
# ============================================================
POSTGRES_DB=aegisdb
POSTGRES_USER=aegis_readonly
POSTGRES_PASSWORD=aegis_readonly_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
DATABASE_URL=postgresql://aegis_readonly:aegis_readonly_password@127.0.0.1:5432/aegisdb
```

> [!TIP]
> **Use `127.0.0.1` instead of `localhost` on Windows**: On Windows systems, `localhost` resolves to IPv6 `::1` before falling back to IPv4 `127.0.0.1`, which can introduce a 2-second connection timeout latency. Using `127.0.0.1` achieves sub-millisecond connection times.

---

## 🚀 Quickstart: Starting the Local Database

### 1. Start the PostgreSQL Container

```bash
# Using Docker Compose
docker compose up -d postgres

# On older Docker installations
docker-compose up -d postgres
```

### 2. Verify Container Health

```bash
docker compose ps postgres
```
Expected output:
```
NAME                          IMAGE                STATUS
enterprise_copilot_postgres   postgres:16-alpine   Up (healthy)   127.0.0.1:5432->5432/tcp
```

### 3. Verify Database Connectivity & Schema

Run the built-in diagnostic verifier:

```bash
# Windows
python scripts/verify_db.py

# Linux / macOS
python3 scripts/verify_db.py
```

Expected output:
```
============================================================
 🐘 PostgreSQL Local Database Health & Schema Verifier
============================================================
Connection Target: postgresql://aegis_readonly:***@127.0.0.1:5432/aegisdb

✅ Connection SUCCESSFUL (Ping Latency: 16.12ms)

Querying Enterprise Tables:
------------------------------------------------------------
  • users                     :     5 records
  • customer_profiles         :     5 records
  • documents                 :     6 records
  • approval_requests         :     3 records
  • schema_migrations         :     1 records
------------------------------------------------------------
✅ All enterprise database checks passed!
```

### 4. Start the FastAPI Backend Application

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Access the application:
- **Interactive UI**: [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui)
- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Deep Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 🛠️ Developer Commands Reference

| Operation | PowerShell (Windows) | Bash (Linux/macOS) |
| :--- | :--- | :--- |
| **Start PostgreSQL** | `docker compose up -d postgres` | `docker compose up -d postgres` |
| **Check Container Status** | `docker compose ps` | `docker compose ps` |
| **View Database Logs** | `docker compose logs -f postgres` | `docker compose logs -f postgres` |
| **Stop PostgreSQL** | `docker compose stop postgres` | `docker compose stop postgres` |
| **Tear Down (Keeps Data)** | `docker compose down` | `docker compose down` |
| **Verify Connectivity** | `python scripts/verify_db.py` | `python3 scripts/verify_db.py` |
| **Run Schema Migration** | `python scripts/migrate.py` | `python3 scripts/migrate.py` |
| **Create Database Backup**| `powershell -File scripts/backup_db.ps1` | `bash scripts/backup_db.sh` |
| **Restore from Backup** | `powershell -File scripts/restore_db.ps1` | `bash scripts/restore_db.sh` |
| **Export Render Database**| `powershell -File scripts/export_render_db.ps1` | `bash scripts/export_render_db.sh` |
| **Import SQL Dump** | `powershell -File scripts/import_local_db.ps1` | `bash scripts/import_local_db.sh` |

---

## 📦 Running Schema Migrations

The database includes an idempotent schema migration tool that applies DDL and seed records without destroying existing data. Applied migrations are tracked in the `schema_migrations` table.

```bash
python scripts/migrate.py
```

This runs against the local database, ensures all enterprise tables exist (`users`, `customer_profiles`, `documents`, `approval_requests`, `schema_migrations`), seeds default records with `ON CONFLICT DO NOTHING`, and prints the record count for each table.

---

## 💾 Automated Backup & Restore System

All database backups are stored in the dedicated `backups/` directory (ignored by git, preserving `.gitkeep`).

### 1. Creating a Backup

The backup script automatically uses `pg_dump` from inside the running Docker container, requiring zero host dependencies.

**On Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_db.ps1
```

**On Linux / macOS (Bash):**
```bash
bash scripts/backup_db.sh
```

Example created file:
`backups/agentic_copilot_2026-11-24_210034.sql`

### 2. Restoring from a Backup

To prevent accidental data loss, the restore tool:
1. Lists the target database and selected backup file.
2. Requires explicit confirmation (`Type 'YES' to proceed`).
3. Executes transactional restoration.
4. Immediately runs the verification probe.

**On Windows (PowerShell):**
```powershell
# Restore specific backup
powershell -ExecutionPolicy Bypass -File scripts/restore_db.ps1 -BackupFile "backups/agentic_copilot_2026-11-24_210034.sql"

# Or let it auto-select the latest backup:
powershell -ExecutionPolicy Bypass -File scripts/restore_db.ps1
```

**On Linux / macOS (Bash):**
```bash
bash scripts/restore_db.sh "backups/agentic_copilot_2026-11-24_210034.sql"
```

---

## 🔄 Recovering Data from Render (If Access is Restored)

If your Render PostgreSQL database is temporarily reactivated or access is restored, you can migrate your data seamlessly to your local database:

### Step 1: Export Data from Render

Obtain your Render external connection URL from the Render Dashboard and run:

**On Windows (PowerShell):**
```powershell
$env:RENDER_DATABASE_URL = "postgresql://user:password@dpg-xxxxxx.oregon-postgres.render.com/aegisdb"
powershell -ExecutionPolicy Bypass -File scripts/export_render_db.ps1
```

**On Linux / macOS (Bash):**
```bash
export RENDER_DATABASE_URL="postgresql://user:password@dpg-xxxxxx.oregon-postgres.render.com/aegisdb"
bash scripts/export_render_db.sh
```

This generates `backups/render_backup_YYYYMMDD_HHMMSS.sql`.

### Step 2: Import into Local PostgreSQL

**On Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/import_local_db.ps1 -BackupFile "backups/render_backup_YYYYMMDD_HHMMSS.sql"
```

**On Linux / macOS (Bash):**
```bash
bash scripts/import_local_db.sh "backups/render_backup_YYYYMMDD_HHMMSS.sql"
```

---

## 🧠 Backend Connection & Thread-Safe Connection Pooling

The backend integration in `app/database/postgres.py` features:

```python
from app.database.postgres import get_connection, test_connection

# Check connection health (non-blocking)
if test_connection():
    # Context-managed connection checkout & return to pool
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM users")
            row = cur.fetchone()
            print(f"Active users: {row['total']}")
```

### Features:
- **Lifespan Integration**: The pool is initialized on FastAPI startup (`init_db_pool()`) and cleanly closed upon shutdown (`close_db_pool()`).
- **Connection Isolation**: Stale or terminated connections are automatically evicted and replaced with fresh connections.
- **Rollback on Return**: Uncommitted transactions are rolled back prior to returning connections to the pool, preventing dirty reads or leaked locks.

---

## 🧪 Verification & Testing

Verify that all security policies, API endpoints, and database interactions function correctly:

```bash
# 1. Run database tests
python scripts/database_test.py

# 2. Run SQL security & AST validation tests
python scripts/sql_security_test.py

# 3. Run all unit and integration tests (30/30 test suite)
python -m pytest tests/ -v
```

---

## 🔍 Troubleshooting & Common Docker Issues

### 1. "failed to connect to docker API at npipe:////./pipe/docker_engine"
- **Cause**: Docker Desktop is not currently running.
- **Fix**: Launch Docker Desktop from the Start menu or run:
  ```powershell
  Start-Process "C:\Users\yoges\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
  ```
  Wait approximately 15 seconds until the Docker daemon reports online (`docker version`).

### 2. "Port 5432 is already in use"
- **Cause**: Another local PostgreSQL instance (e.g., native Windows Postgres service) is using port 5432.
- **Fix**:
  1. Check what is listening on port 5432:
     ```powershell
     netstat -ano | findstr 5432
     ```
  2. Change `POSTGRES_PORT` in `.env` and `docker-compose.yml` (e.g., `5433:5432`):
     ```ini
     POSTGRES_PORT=5433
     DATABASE_URL=postgresql://aegis_readonly:aegis_readonly_password@127.0.0.1:5433/aegisdb
     ```

### 3. "Permission denied / Access is denied" on `~/.docker/config.json`
- **Cause**: Windows user profile permissions on Docker config file.
- **Fix**: Point `DOCKER_CONFIG` to a workspace directory:
  ```powershell
  $env:DOCKER_CONFIG = "$PWD\.docker"
  docker compose up -d postgres
  ```

### 4. Data Loss on `docker compose down -v`
- **Caution**: `docker compose down` retains your data volume. However, running `docker compose down -v` with the `-v` (volumes) flag deletes all named volumes.
- **Safety**: Always create a backup with `scripts/backup_db.ps1` before performing volume maintenance.
