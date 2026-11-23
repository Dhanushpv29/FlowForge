import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from flowforge.models import (
    RunStatus,
    TaskDefinition,
    TaskRun,
    TaskStatus,
    Worker,
    WorkerStatus,
    Workflow,
    WorkflowRun,
)

pytestmark = pytest.mark.integration


def rejected(db, *objects):
    """Assert the database refuses these rows (inside a savepoint so the session survives)."""
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add_all(objects)
        db.flush()


def make_workflow(db, name="wf") -> Workflow:
    workflow = Workflow(name=name)
    workflow.tasks = [
        TaskDefinition(task_key="extract", task_type="demo.echo"),
        TaskDefinition(task_key="load", task_type="demo.echo", dependencies=["extract"]),
    ]
    db.add(workflow)
    db.flush()
    return workflow


def test_defaults_are_applied(db):
    workflow = make_workflow(db)
    db.refresh(workflow)
    assert workflow.max_concurrent_runs == 1
    assert workflow.description == ""
    assert workflow.schedule_cron is None
    assert workflow.created_at is not None

    run = WorkflowRun(workflow_id=workflow.id)
    db.add(run)
    db.flush()
    db.refresh(run)
    assert run.status is RunStatus.QUEUED
    assert run.input_payload == {}


def test_server_side_defaults_work_for_raw_sql(db):
    """Rows inserted outside the ORM (psql, other services) still get valid defaults."""
    wid = db.execute(text("INSERT INTO workflows (name) VALUES ('raw') RETURNING id")).scalar_one()
    rid = db.execute(
        text("INSERT INTO workflow_runs (workflow_id) VALUES (:w) RETURNING id"), {"w": wid}
    ).scalar_one()
    status = db.execute(
        text(
            "INSERT INTO task_runs (workflow_run_id, task_key, task_type) "
            "VALUES (:r, 't', 'demo.echo') RETURNING status"
        ),
        {"r": rid},
    ).scalar_one()
    assert status == "blocked"


def test_task_key_is_unique_within_a_workflow(db):
    workflow = make_workflow(db)
    rejected(db, TaskDefinition(workflow_id=workflow.id, task_key="extract", task_type="x"))


def test_same_task_key_allowed_in_different_workflows(db):
    make_workflow(db, "one")
    make_workflow(db, "two")
    assert db.scalar(select(func.count()).select_from(TaskDefinition)) == 4


def test_task_key_is_unique_within_a_run(db):
    workflow = make_workflow(db)
    run = WorkflowRun(workflow_id=workflow.id)
    db.add(run)
    db.flush()
    db.add(TaskRun(workflow_run_id=run.id, task_key="a", task_type="x"))
    db.flush()
    rejected(db, TaskRun(workflow_run_id=run.id, task_key="a", task_type="x"))


@pytest.mark.parametrize(
    "column,value",
    [("attempts", -1), ("max_retries", -1), ("retry_backoff_seconds", 0)],
)
def test_task_run_check_constraints(db, column, value):
    workflow = make_workflow(db)
    run = WorkflowRun(workflow_id=workflow.id)
    db.add(run)
    db.flush()
    rejected(db, TaskRun(workflow_run_id=run.id, task_key="a", task_type="x", **{column: value}))


def test_workflow_requires_positive_concurrency(db):
    rejected(db, Workflow(name="bad", max_concurrent_runs=0))


def test_database_rejects_invalid_status_values(db):
    """The CHECK constraint protects the state machine even from raw SQL."""
    workflow = make_workflow(db)
    run = WorkflowRun(workflow_id=workflow.id)
    task = TaskRun(workflow_run=run, task_key="a", task_type="x")
    worker = Worker(worker_name="w1")
    db.add_all([run, task, worker])
    db.flush()
    for table, row in (("workflow_runs", run), ("task_runs", task), ("workers", worker)):
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(text(f"UPDATE {table} SET status = 'bogus' WHERE id = :i"), {"i": row.id})


def test_every_status_value_is_storable(db):
    workflow = make_workflow(db)
    run = WorkflowRun(workflow_id=workflow.id)
    db.add(run)
    db.flush()
    for i, status in enumerate(TaskStatus):
        db.add(TaskRun(workflow_run_id=run.id, task_key=f"t{i}", task_type="x", status=status))
    for i, status in enumerate(WorkerStatus):
        db.add(Worker(worker_name=f"w{i}", status=status))
    db.flush()


def test_worker_name_is_unique(db):
    db.add(Worker(worker_name="w1"))
    db.flush()
    rejected(db, Worker(worker_name="w1"))


def test_deleting_workflow_cascades_to_task_definitions(db):
    workflow = make_workflow(db)
    db.delete(workflow)
    db.flush()
    assert db.scalar(select(func.count()).select_from(TaskDefinition)) == 0


def test_workflow_with_runs_cannot_be_deleted(db):
    workflow = make_workflow(db)
    db.add(WorkflowRun(workflow_id=workflow.id))
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.delete(workflow)
        db.flush()


def test_deleting_run_cascades_to_task_runs(db):
    workflow = make_workflow(db)
    run = WorkflowRun(workflow_id=workflow.id)
    run.tasks = [TaskRun(task_key="a", task_type="x")]
    db.add(run)
    db.flush()
    db.delete(run)
    db.flush()
    assert db.scalar(select(func.count()).select_from(TaskRun)) == 0
