import json
from wedge.db import Database

def test_create_and_get_job():
    db = Database(":memory:")
    db.init_schema()
    job_id = db.create_job(idea="AI notes")
    job = db.get_job(job_id)
    assert job["idea"] == "AI notes"
    assert job["status"] == "planning"

def test_update_status_and_artifact():
    db = Database(":memory:")
    db.init_schema()
    jid = db.create_job(idea="x")
    db.set_status(jid, "complete")
    db.save_artifact(jid, "brief_json", {"tldr": "t"})
    job = db.get_job(jid)
    assert job["status"] == "complete"
    assert json.loads(job["brief_json"]) == {"tldr": "t"}

def test_increment_bright_data_calls():
    db = Database(":memory:")
    db.init_schema()
    jid = db.create_job(idea="x")
    db.bump_calls(jid, 5)
    db.bump_calls(jid, 3)
    assert db.get_job(jid)["bright_data_calls"] == 8
