import logging
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config.settings import get_settings
from app.models.incident import Incident, Base

logger = logging.getLogger(__name__)


class IncidentRepository:
    def __init__(self):
        settings = get_settings()
        # Create engine with schema support for PostgreSQL
        engine_kwargs = {}
        if settings.database_url.startswith('postgresql'):
            engine_kwargs['connect_args'] = {'options': '-csearch_path=incident,public'}
        self.engine = create_engine(settings.database_url, **engine_kwargs)
        
        # Create schema if using PostgreSQL
        if settings.database_url.startswith('postgresql'):
            with self.engine.connect() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS incident"))
                conn.commit()
        
        # Create all tables in the incident schema
        Base.metadata.schema = 'incident' if settings.database_url.startswith('postgresql') else None
        Base.metadata.create_all(self.engine)
        self._run_migrations()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _run_migrations(self):
        """Add columns introduced after the initial table creation (create_all does not alter existing tables)."""
        from sqlalchemy import inspect
        is_pg = get_settings().database_url.startswith('postgresql')
        schema = 'incident' if is_pg else None
        new_columns = {
            'lob': 'VARCHAR',
            'issue': 'TEXT',
            'identified_time': 'VARCHAR',
            'upstream_downstream': 'TEXT',
            'impacted_users': 'VARCHAR',
            'failed_cases': 'VARCHAR',
            'business_impact': 'TEXT',
        }
        try:
            inspector = inspect(self.engine)
            existing = {c['name'] for c in inspector.get_columns('incidents', schema=schema)}
        except Exception as e:
            logger.warning(f"Could not inspect incidents table for migration: {e}")
            return
        table_ref = f'{schema}.incidents' if schema else 'incidents'
        with self.engine.connect() as conn:
            for col, col_type in new_columns.items():
                if col not in existing:
                    conn.execute(text(f'ALTER TABLE {table_ref} ADD COLUMN {col} {col_type}'))
                    logger.info(f"Added column '{col}' to incidents table")
            conn.commit()

    def _get_session(self) -> Session:
        return self.SessionLocal()

    def save(self, incident: Incident) -> Incident:
        session = self._get_session()
        try:
            session.merge(incident)
            session.commit()
            return incident
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save incident {incident.incident_id}: {e}")
            raise
        finally:
            session.close()

    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        session = self._get_session()
        try:
            return session.query(Incident).filter(Incident.incident_id == incident_id).first()
        finally:
            session.close()

    def get_by_thread_id(self, thread_id: str) -> Optional[Incident]:
        if not thread_id:
            return None
        session = self._get_session()
        try:
            return session.query(Incident).filter(Incident.source_thread_id == thread_id).first()
        finally:
            session.close()

    def get_all(self) -> List[Incident]:
        session = self._get_session()
        try:
            return session.query(Incident).order_by(Incident.created_at.desc()).all()
        finally:
            session.close()

    def delete_all(self) -> int:
        session = self._get_session()
        try:
            count = session.query(Incident).delete()
            session.commit()
            logger.info(f"Deleted {count} incidents from the database")
            return count
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete all incidents: {e}")
            raise
        finally:
            session.close()

    def search_by_application(self, application: str) -> List[Incident]:
        session = self._get_session()
        try:
            return session.query(Incident).filter(
                Incident.application.ilike(f"%{application}%")
            ).all()
        finally:
            session.close()

    def search_by_lob(self, lob: str) -> List[Incident]:
        session = self._get_session()
        try:
            return session.query(Incident).filter(
                Incident.lob.ilike(f"%{lob}%")
            ).order_by(Incident.created_at.desc()).all()
        finally:
            session.close()

    def distinct_lobs(self) -> List[str]:
        session = self._get_session()
        try:
            rows = session.query(Incident.lob).filter(Incident.lob.isnot(None)).distinct().all()
            return sorted({r[0].strip() for r in rows if r[0] and r[0].strip()})
        finally:
            session.close()

    def count(self) -> int:
        session = self._get_session()
        try:
            return session.query(Incident).count()
        finally:
            session.close()

    def count_by_status(self, status: str) -> int:
        session = self._get_session()
        try:
            return session.query(Incident).filter(Incident.status == status).count()
        finally:
            session.close()


_repository: Optional[IncidentRepository] = None


def get_incident_repository() -> IncidentRepository:
    global _repository
    if _repository is None:
        _repository = IncidentRepository()
    return _repository
