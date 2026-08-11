import logging
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config.settings import get_settings
from app.models.incident import Incident, Base

logger = logging.getLogger(__name__)


class IncidentRepository:
    def __init__(self):
        settings = get_settings()
        self.engine = create_engine(settings.database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

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

    def search_by_application(self, application: str) -> List[Incident]:
        session = self._get_session()
        try:
            return session.query(Incident).filter(
                Incident.application.ilike(f"%{application}%")
            ).all()
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
