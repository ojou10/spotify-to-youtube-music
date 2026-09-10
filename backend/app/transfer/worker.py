from __future__ import annotations

import random
import threading
import time

from app.domain.enums import JobStatus, MatchStatus, SupportStatus
from app.domain.models import SourceItemValue
from app.matching.queries import build_queries
from app.matching.score import score_candidates
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.persistence.tables import MatchCandidateRow, SourceItemRow


class TransferWorker:
    def __init__(self, database: Database, spotify=None, youtube=None, *, sleep=time.sleep, spacing=None):
        self.database = database
        self.spotify = spotify
        self.youtube = youtube
        self.sleep = sleep
        self.spacing = spacing or (lambda: random.uniform(0.5, 0.9))
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.recover_abandoned_jobs()
        self._thread = threading.Thread(target=self._run, name="playlist-bridge-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=5)

    def wake(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            did_work = self.run_one_cycle()
            if not did_work:
                self._wake.wait(0.5)
                self._wake.clear()

    def recover_abandoned_jobs(self) -> None:
        with self.database.session() as session:
            repos = RepositorySet(session)
            active = {JobStatus.IMPORTING_SOURCE, JobStatus.MATCHING, JobStatus.PREPARING_DESTINATION, JobStatus.TRANSFERRING}
            for job in repos.jobs.list_status(active):
                repos.jobs.update(job.id, status=JobStatus.PAUSED.value, revision=job.revision + 1, last_error_code="recovery_required", last_error_summary="A previous worker stopped before this job completed")
                repos.events.add(job.id, job.revision + 1, "job_paused_for_recovery", {})

    def run_one_cycle(self) -> bool:
        if self.youtube is None:
            return False
        with self.database.session() as session:
            repos = RepositorySet(session)
            jobs = repos.jobs.list_status({JobStatus.MATCHING})
            if not jobs:
                return False
            job = jobs[0]
            rows = repos.items.list(job.id)
            for row in rows:
                if row.source_position < job.match_cursor or row.support_status != SupportStatus.SUPPORTED.value:
                    continue
                self._match_item(session, job, row)
                repos.jobs.update(job.id, match_cursor=row.source_position + 1)
                break
            refreshed = repos.jobs.get(job.id)
            if refreshed and refreshed.match_cursor >= refreshed.source_track_count:
                unresolved = any(row.match_status in {MatchStatus.PENDING.value, MatchStatus.REVIEW_REQUIRED.value, MatchStatus.UNMATCHED.value} for row in repos.items.list(job.id) if row.support_status == SupportStatus.SUPPORTED.value)
                target = JobStatus.AWAITING_REVIEW if unresolved else JobStatus.READY_TO_TRANSFER
                refreshed = repos.jobs.transition(job.id, refreshed.revision, target)
            return True

    def _match_item(self, session, job, row: SourceItemRow) -> None:
        source = SourceItemValue(row.source_position, row.spotify_id, row.title, tuple(row.artists), row.album, row.duration_ms, row.isrc, SupportStatus(row.support_status), row.support_reason)
        candidates = []
        seen = set()
        for query in build_queries(source):
            self.sleep(self.spacing())
            for candidate in self.youtube.search_songs(query, limit=5):
                if candidate.video_id not in seen:
                    seen.add(candidate.video_id)
                    candidates.append(candidate)
            if len(candidates) >= 5:
                break
        result = score_candidates(source, candidates[:5])
        for scored in result.candidates:
            session.add(MatchCandidateRow(source_item_id=row.id, video_id=scored.candidate.video_id, title=scored.candidate.title, artists=list(scored.candidate.artists), album=scored.candidate.album, duration_ms=scored.candidate.duration_ms, result_type=scored.candidate.result_type, thumbnail_url=scored.candidate.thumbnail_url, url=scored.candidate.url, score=scored.score, score_breakdown={"title": scored.breakdown.title, "artists": scored.breakdown.artists, "duration": scored.breakdown.duration, "album": scored.breakdown.album, "result_type": scored.breakdown.result_type, "version": scored.breakdown.version, "penalties": list(scored.breakdown.penalties), "penalty_points": scored.breakdown.penalty_points}, rank=scored.rank))
        row.match_status = result.classification.value
        row.selected_video_id = result.selected_video_id
