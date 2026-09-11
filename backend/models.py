from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime, timezone
from database import Base

class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_usage_percent = Column(Float, nullable=False)
    top_process_name = Column(String, nullable=False)
    top_process_cpu = Column(Float, nullable=False)

class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String, index=True)
    severity = Column(String)
    summary = Column(String)
    analysis = Column(String)
    recommended_action = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)