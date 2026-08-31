# PostgreSQL Migration Guide

## Changes Made

### 1. Updated Requirements
- Added `psycopg2-binary>=2.9.9` to `requirements.txt` for PostgreSQL support

### 2. Updated Configuration (`app/config/settings.py`)
- Changed default `database_url` from SQLite to PostgreSQL:
  - Old: `sqlite:///./data/incidents.db`
  - New: `postgresql://postgres:root@localhost:5432/incident_management`

### 3. Updated Repository (`app/repositories/incident_repository.py`)
- Added schema support for PostgreSQL
- Automatically creates `incident` schema if it doesn't exist
- Sets search_path to `incident,public` for PostgreSQL connections
- All tables will be created in the `incident` schema

### 4. Created Database Initialization Script (`init_db.py`)
- Creates `incident_management` database if it doesn't exist
- Creates `incident` schema
- Configures search_path

## Database Schema

All tables and columns are in lowercase as required:

**Schema:** `incident`

**Table:** `incidents`
- `incident_id` (String, Primary Key)
- `application` (String, Indexed)
- `environment` (String, Indexed)
- `severity` (String, Indexed)
- `problem_summary` (Text)
- `symptoms` (JSON)
- `error_codes` (JSON)
- `root_cause` (Text)
- `resolution` (JSON)
- `status` (String)
- `created_at` (DateTime)
- `resolved_at` (DateTime)
- `source_space` (String)
- `source_thread_id` (String, Unique, Indexed)
- `source_message_ids` (JSON)
- `conversation_text` (Text)
- `embedding_text` (Text)

## Setup Instructions

### 1. Install PostgreSQL (if not already installed)
- Download from https://www.postgresql.org/download/
- Default port: 5432
- Default user: postgres

### 2. Initialize Database
```bash
cd backend
python init_db.py
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env if you need to change any settings
```

### 5. Start the Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will automatically create all tables in the `incident` schema on first run.

## Verification

### Check Database and Schema
```sql
-- Connect to PostgreSQL
psql -U postgres -d incident_management

-- List schemas
\dn

-- Check tables in incident schema
\dt incident.*

-- Verify table structure
\d incident.incidents
```

### Check Data Migration
If you had existing data in SQLite, you'll need to migrate it manually or reingest from the source JSON file.

## Connection Details

- **Host:** localhost
- **Port:** 5432
- **Username:** postgres
- **Password:** (empty)
- **Database:** incident_management
- **Schema:** incident

## Troubleshooting

### Connection Error
If you get connection errors, verify:
1. PostgreSQL service is running
2. Port 5432 is not blocked
3. User `postgres` exists and has no password (or update credentials in .env)

### Schema Not Found
If tables are not created in the correct schema:
1. Run `init_db.py` again
2. Check that search_path is set correctly
3. Restart the application

### Permission Denied
If you get permission errors:
```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON SCHEMA incident TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA incident TO postgres;
```
