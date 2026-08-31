from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Float, JSON, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class SeverityLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String, primary_key=True)
    application = Column(String, nullable=False, index=True)
    environment = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)
    problem_summary = Column(Text, nullable=False)
    symptoms = Column(JSON, default=list)
    error_codes = Column(JSON, default=list)
    root_cause = Column(Text)
    resolution = Column(JSON, default=list)
    status = Column(String, nullable=False, default="RESOLVED")
    lob = Column(String, index=True)
    issue = Column(Text)
    identified_time = Column(String)
    upstream_downstream = Column(Text)
    impacted_users = Column(String)
    failed_cases = Column(String)
    business_impact = Column(Text)
    created_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime)
    source_space = Column(String)
    source_thread_id = Column(String, unique=True, index=True)
    source_message_ids = Column(JSON, default=list)
    conversation_text = Column(Text)
    embedding_text = Column(Text)
