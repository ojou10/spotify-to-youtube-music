import json
from pathlib import Path

from app.domain.enums import MatchStatus, SupportStatus
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.persistence.tables import MatchCandidateRow
from app.reporting.export import ReportExporter


def test_reports_include_each_source_position_and_neutralize_formula_cells(tmp_path: Path):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.add(status="completed", source_url="spotify:playlist:p", source_name="Playlist", source_track_count=1, destination_name="YouTube")
        item = repos.items.add(job_id=job.id, source_position=0, title='=HYPERLINK("bad")', artists=["Artist"], support_status=SupportStatus.SUPPORTED.value, match_status=MatchStatus.MANUAL_ACCEPTED.value, selected_video_id="abcdefghijk")
        session.add(MatchCandidateRow(source_item_id=item.id, video_id="abcdefghijk", title="Song", artists=["Artist"], result_type="song", score=90, score_breakdown={"title": 35}, rank=1))
        session.flush()
        job_id = job.id
    exporter = ReportExporter(database)
    document = b"".join(exporter.build_json_report(job_id))
    assert json.loads(document)["items"][0]["source_position"] == 0
    csv = b"".join(exporter.build_csv_report(job_id)).decode()
    assert "'=HYPERLINK" in csv
    assert "secret" not in document.decode()
