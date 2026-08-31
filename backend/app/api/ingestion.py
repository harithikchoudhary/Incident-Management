import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, HTTPException

from app.schemas.resolution import IngestionResponse
from app.services.ingestion_service import MockChatSource
from app.services.incident_service import get_incident_service
from app.agents.incident_extractor import IncidentExtractor
from app.config.settings import get_settings

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

        # Wipe existing incidents and search index before re-ingesting
        service.clear_all()

        # Extract incidents in parallel since the LLM call is the bottleneck
        incidents = []
        failed = 0
        max_workers = get_settings().ingestion_max_workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_thread = {executor.submit(extractor.extract, t): t for t in threads}
            for future in as_completed(future_to_thread):
                thread = future_to_thread[future]
                try:
                    incident = future.result()
                    if incident:
                        incidents.append(incident)
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Failed to process thread {thread.thread_id}: {e}")
                    failed += 1

        # Persist and index in a single batch
        successful = service.create_incidents_bulk(incidents)

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
