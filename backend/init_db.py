"""
Database initialization script for PostgreSQL.
Creates the incident_management database and incident schema.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize the PostgreSQL database and schema.
    
    Connection details:
    - Host: localhost
    - Port: 5432
    - Username: postgres
    - Password: root
    - Database: incident_management
    - Schema: incident
    """
    
    # Connect to PostgreSQL server (default postgres database)
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'incident_management'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("CREATE DATABASE incident_management")
            logger.info("✓ Database 'incident_management' created successfully")
        else:
            logger.info("✓ Database 'incident_management' already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"✗ Error creating database: {e}")
        raise
    
    # Connect to the incident_management database to create schema
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="root",
            database="incident_management"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create schema if it doesn't exist
        cursor.execute("CREATE SCHEMA IF NOT EXISTS incident")
        logger.info("✓ Schema 'incident' created successfully")
        
        # Set search_path to include incident schema
        cursor.execute("ALTER DATABASE incident_management SET search_path TO incident, public")
        logger.info("✓ Search path configured for incident schema")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✓ Database initialization completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Run: pip install -r requirements.txt")
        logger.info("2. Copy .env.example to .env and configure as needed")
        logger.info("3. Run: uvicorn app.main:app --reload")
        logger.info("\nTables will be created automatically on first application start.")
        
    except Exception as e:
        logger.error(f"✗ Error creating schema: {e}")
        raise


if __name__ == "__main__":
    init_database()
