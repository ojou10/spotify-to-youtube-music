import json
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from app.domain.enums import DestinationMode, Visibility
from app.domain.models import CreateJob
from app.transfer.service import TransferService

router = APIRouter(prefix="/transfers", tags=["transfers"])


class CreateTransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str
    destination_mode: DestinationMode = DestinationMode.CREATE
    destination_playlist_id: str | None = None
    destination_name: str | None = None
    destination_description: str = ""
    destination_visibility: Visibility = Visibility.PRIVATE


@router.post("")
def create_transfer(payload: CreateTransferRequest, request: Request):
    service = TransferService(request.app.state.database, request.app.state.spotify_connector)
    job = service.import_source(CreateJob(**payload.model_dump()))
    return {"id": job.id, "status": job.status, "revision": job.revision, "source_track_count": job.source_track_count, "supported_count": job.supported_count}


@router.get("/{job_id}/events")
def transfer_events(job_id: str, request: Request):
    def stream() -> Iterator[str]:
        with request.app.state.database.session() as session:
            from app.persistence.repositories import RepositorySet
            job = RepositorySet(session).jobs.get(job_id)
            if job is None:
                return
            payload = {"job_id": job.id, "revision": job.revision, "status": job.status, "counts": job.counts or {}, "last_event": job.last_error_summary}
            yield f"event: progress\\ndata: {json.dumps(payload)}\\n\\n"
            yield ": heartbeat\\n\\n"
    return StreamingResponse(stream(), media_type="text/event-stream")
