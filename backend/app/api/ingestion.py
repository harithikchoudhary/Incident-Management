import logging
from fastapi import APIRouter, HTTPException

from app.schemas.resolution import IngestionResponse
from app.services.ingestion_service import MockChatSource
from app.services.incident_service import get_incident_service
from app.agents.incident_extractor import IncidentExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/mock-chat", response_model=IngestionResponse)
def ingest_mock_chat():
    try:
        source = MockChatSource()
        threads = source.get_threads()
        total_threads = len(threads)

        extractor = IncidentExtractor()
        service = get_incident_service()

        successful = 0
        failed = 0

        for thread in threads:
            try:
                incident = extractor.extract(thread)
                if incident:
                    service.create_incident(incident)
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to process thread {thread.thread_id}: {e}")
                failed += 1

        return IngestionResponse(
            total_threads=total_threads,
            incidents_extracted=successful + failed,
            successful=successful,
            failed=failed,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Mock chat data file not found")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
