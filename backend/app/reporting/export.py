from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator
from uuid import UUID

from sqlalchemy import select

from app.persistence.db import Database
from app.persistence.tables import MatchCandidateRow, SourceItemRow, TransferJobRow


def _safe_csv(value):
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


class ReportExporter:
    def __init__(self, database: Database):
        self.database = database

    def _rows(self, job_id: UUID | str) -> tuple[dict, list[dict]]:
        with self.database.session() as session:
            job = session.get(TransferJobRow, str(job_id))
            if not job:
                return {}, []
            items = list(session.scalars(select(SourceItemRow).where(SourceItemRow.job_id == str(job_id)).order_by(SourceItemRow.source_position)))
            rows = []
            for item in items:
                candidate = session.scalar(select(MatchCandidateRow).where(MatchCandidateRow.source_item_id == item.id, MatchCandidateRow.video_id == item.selected_video_id).order_by(MatchCandidateRow.rank)) if item.selected_video_id else None
                rows.append({"source_position": item.source_position, "source_title": item.title, "source_artists": item.artists, "source_album": item.album, "support_status": item.support_status, "support_reason": item.support_reason, "match_status": item.match_status, "selected_video_id": item.selected_video_id, "selected_title": candidate.title if candidate else None, "score": candidate.score if candidate else None, "score_breakdown": candidate.score_breakdown if candidate else None, "transfer_status": item.transfer_status, "error_summary": item.error_summary})
            metadata = {"schema_version": 1, "job_id": job.id, "status": job.status, "source_url": job.source_url, "source_name": job.source_name, "source_owner": job.source_owner, "source_track_count": job.source_track_count, "destination_playlist_id": job.destination_playlist_id, "destination_name": job.destination_name, "counts": job.counts or {}}
            return metadata, rows

    def build_json_report(self, job_id: UUID | str) -> Iterator[bytes]:
        metadata, rows = self._rows(job_id)
        yield b"{\"schema_version\":1,\"job\":" + json.dumps(metadata, ensure_ascii=False).encode("utf-8") + b",\"items\":["
        for index, row in enumerate(rows):
            if index:
                yield b"," 
            yield json.dumps(row, ensure_ascii=False).encode("utf-8")
        yield b"]}"

    def build_csv_report(self, job_id: UUID | str) -> Iterator[bytes]:
        _, rows = self._rows(job_id)
        columns = ["source_position", "source_title", "source_artists", "source_album", "support_status", "support_reason", "match_status", "selected_video_id", "selected_title", "score", "score_breakdown", "transfer_status", "error_summary"]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        yield buffer.getvalue().encode("utf-8")
        for row in rows:
            buffer.seek(0)
            buffer.truncate(0)
            writer.writerow({column: _safe_csv(json.dumps(row[column], ensure_ascii=False) if isinstance(row[column], (list, dict)) else row[column]) for column in columns})
            yield buffer.getvalue().encode("utf-8")
