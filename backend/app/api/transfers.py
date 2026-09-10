import json
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

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
    service = TransferService(request.app.state.database, request.app.state.spotify_connector, request.app.state.youtube_connector)
    job = service.import_source(CreateJob(**payload.model_dump()))
    return {"id": job.id, "status": job.status, "revision": job.revision, "source_track_count": job.source_track_count, "supported_count": job.supported_count}


class ReviewDecisionRequest(BaseModel):
    action: str = Field(pattern="^(accept_candidate|accept_url|skip)$")
    revision: int | None = None
    candidate_id: str | None = None
    video_url: str | None = None


class ItemSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)


def _service(request: Request) -> TransferService:
    return TransferService(request.app.state.database, request.app.state.spotify_connector, request.app.state.youtube_connector)


@router.get("/{job_id}/items")
def review_items(job_id: str, request: Request, status: str | None = None, query: str | None = None, cursor: str | None = None, limit: int = 50):
    return _service(request).list_items(job_id, status=status, query=query, cursor=cursor, limit=limit)


@router.post("/{job_id}/items/{item_id}/search")
def search_review_item(job_id: str, item_id: str, payload: ItemSearchRequest, request: Request):
    return {"candidates": [candidate.__dict__ for candidate in _service(request).search_item(item_id, payload.query)]}


@router.put("/{job_id}/items/{item_id}/decision")
def decide_review_item(job_id: str, item_id: str, payload: ReviewDecisionRequest, request: Request):
    job = _service(request).decide(job_id, item_id, payload.action, revision=payload.revision, candidate_id=payload.candidate_id, video_url=payload.video_url)
    return {"id": job.id, "status": job.status, "revision": job.revision}


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
