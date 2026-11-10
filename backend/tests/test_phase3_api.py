import time
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.api.routes.export as export_routes
import app.api.routes.research as research_routes
import app.api.websocket as websocket_module
import app.main as main_module
from app.services.session_manager import ResearchSessionManager


def _graph_state(values=None, interrupt=None, next_nodes=()):
    tasks = () if interrupt is None else (
        SimpleNamespace(interrupts=(SimpleNamespace(value=interrupt),)),
    )
    return SimpleNamespace(values=values or {}, tasks=tasks, next=next_nodes)


class ApprovalGraph:
    plan = [{
        "id": "sq_1",
        "question": "Which evidence supports this question?",
        "target_source": "web",
        "status": "pending",
    }]

    def __init__(self):
        self.calls = 0
        self.state = _graph_state()

    async def astream(self, value, config, stream_mode):
        assert stream_mode == "updates"
        assert config["configurable"]["thread_id"]
        self.calls += 1

        if self.calls == 1:
            self.state = _graph_state(
                values={"research_plan": self.plan},
                interrupt={
                    "type": "PLAN_APPROVAL_REQUIRED",
                    "plan": self.plan,
                    "message": "Approve the plan.",
                },
                next_nodes=("plan_approval",),
            )
            yield {"planner": {}}
        elif self.calls == 2:
            decision = value["resume"]
            assert decision["action"] == "approve"
            self.state = _graph_state(
                values={"research_plan": self.plan, "report_draft": "# Draft report"},
                interrupt={
                    "type": "REPORT_APPROVAL_REQUIRED",
                    "report_draft": "# Draft report",
                    "message": "Review the report.",
                },
                next_nodes=("report_approval",),
            )
            yield {"searcher": {}}
        elif self.calls == 3:
            decision = value["resume"]
            assert decision["action"] == "approve"
            self.state = _graph_state(
                values={
                    "research_plan": self.plan,
                    "report_approved": True,
                    "final_report": "# Approved report",
                },
            )
            yield {"report_approval": {}}
        else:
            raise AssertionError("A session transition ran the graph more than once.")

    async def aget_state(self, _config):
        return self.state


@pytest.fixture
def api_env(monkeypatch):
    graph = ApprovalGraph()
    manager = ResearchSessionManager(
        graph,
        lambda decision: {"resume": decision},
        websocket_module.broadcast_to_session,
    )
    monkeypatch.setattr(research_routes, "session_manager", manager)
    monkeypatch.setattr(export_routes, "session_manager", manager)
    monkeypatch.setattr(websocket_module, "session_manager", manager)

    @asynccontextmanager
    async def no_service_lifespan(_app):
        yield

    # Keep the real routes and session manager while preventing DB startup.
    monkeypatch.setattr(main_module.app.router, "lifespan_context", no_service_lifespan)
    with TestClient(main_module.app) as client:
        yield client, graph, manager


def _new_session(client):
    response = client.post(
        "/api/v1/research/start",
        json={"question": "Which factors explain the observed result?"},
    )
    assert response.status_code == 200
    return response.json()["session_id"]


def _wait_for_status(client, session_id, expected):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/research/{session_id}")
        assert response.status_code == 200
        if response.json()["status"] == expected:
            return response.json()
        time.sleep(0.01)
    pytest.fail(f"Session {session_id} did not reach {expected!r}.")


def test_create_is_read_only_until_run_and_api_validates_inputs(api_env):
    client, graph, _manager = api_env
    session_id = _new_session(client)

    status = client.get(f"/api/v1/research/{session_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "created"
    assert graph.calls == 0

    assert client.get("/api/v1/research/missing-session").status_code == 404
    assert client.post(
        "/api/v1/research/start",
        json={"question": "Which factors explain this?", "depth": "deep"},
    ).status_code == 422
    assert client.post(
        "/api/v1/research/start",
        json={"question": "Which factors explain this?", "urls": ["https://example.org"]},
    ).status_code == 422
    assert client.post(
        "/api/v1/research/start",
        json={"question": "Which factors explain this?", "unexpected": True},
    ).status_code == 422
    assert graph.calls == 0


def test_run_is_single_use_and_approval_ids_gate_rest_transitions(api_env):
    client, graph, _manager = api_env
    session_id = _new_session(client)
    other_session_id = _new_session(client)

    started = client.post(f"/api/v1/research/{session_id}/run")
    assert started.status_code == 200
    assert started.json()["status"] == "running"
    assert client.post(f"/api/v1/research/{session_id}/run").status_code == 409
    plan_state = _wait_for_status(client, session_id, "awaiting_plan")
    assert graph.calls == 1

    plan_interrupt_id = plan_state["pending_interrupt"]["interrupt_id"]
    invalid_academic_plan = client.post(
        f"/api/v1/research/{session_id}/resume",
        json={
            "action": "modify",
            "interrupt_id": plan_interrupt_id,
            "plan": [{
                "id": "sq_1",
                "question": "Find academic sources for the claim",
                "target_source": "academic",
            }],
        },
    )
    assert invalid_academic_plan.status_code == 422
    assert client.post(
        f"/api/v1/research/{session_id}/resume",
        json={"action": "approve", "interrupt_id": "stale-plan-id"},
    ).status_code == 409
    assert graph.calls == 1

    resumed = client.post(
        f"/api/v1/research/{session_id}/resume",
        json={"action": "approve", "interrupt_id": plan_interrupt_id},
    )
    assert resumed.status_code == 200
    report_state = _wait_for_status(client, session_id, "awaiting_report")
    report_interrupt_id = report_state["pending_interrupt"]["interrupt_id"]
    assert report_interrupt_id != plan_interrupt_id
    assert graph.calls == 2

    draft = client.get(f"/api/v1/research/{session_id}/report")
    assert draft.status_code == 200
    assert draft.json() == {
        "session_id": session_id,
        "status": "awaiting_report",
        "report_markdown": "# Draft report",
        "approved": False,
    }
    assert client.get(f"/api/v1/research/{session_id}/export").status_code == 409
    assert client.get(f"/api/v1/research/{other_session_id}/report").status_code == 409

    assert client.post(
        f"/api/v1/research/{session_id}/resume",
        json={"action": "approve", "interrupt_id": plan_interrupt_id},
    ).status_code == 409
    finished = client.post(
        f"/api/v1/research/{session_id}/resume",
        json={"action": "approve", "interrupt_id": report_interrupt_id},
    )
    assert finished.status_code == 200
    _wait_for_status(client, session_id, "completed")
    assert graph.calls == 3

    final = client.get(f"/api/v1/research/{session_id}/report")
    assert final.status_code == 200
    assert final.json()["approved"] is True
    assert final.json()["report_markdown"] == "# Approved report"
    exported = client.get(f"/api/v1/research/{session_id}/export?format=md")
    assert exported.status_code == 200
    assert exported.text == "# Approved report"
    assert f"research_report_{session_id[:8]}.md" in exported.headers["content-disposition"]
    assert client.get(f"/api/v1/research/{other_session_id}/export").status_code == 409
    assert graph.calls == 3


def test_websockets_only_observe_snapshots_and_the_same_session_broadcast(api_env):
    client, graph, _manager = api_env
    session_id = _new_session(client)
    url = f"/ws/research/{session_id}"

    with client.websocket_connect(url) as first, client.websocket_connect(url) as second:
        first_snapshot = first.receive_json()
        second_snapshot = second.receive_json()
        assert first_snapshot["event"] == second_snapshot["event"] == "SNAPSHOT"
        assert first_snapshot["data"] == second_snapshot["data"]
        assert graph.calls == 0

        started = client.post(f"/api/v1/research/{session_id}/run")
        assert started.status_code == 200
        first_event = first.receive_json()
        second_event = second.receive_json()
        assert first_event["event"] == second_event["event"] == "STEP_UPDATE"
        assert first_event["data"] == second_event["data"]
        first_hitl = first.receive_json()
        second_hitl = second.receive_json()
        assert first_hitl["event"] == second_hitl["event"] == "HITL_TRIGGER"
        assert first_hitl["data"] == second_hitl["data"]
        assert graph.calls == 1

        first.send_text("approve")
        with pytest.raises(WebSocketDisconnect) as disconnected:
            first.receive_text()
        assert disconnected.value.code == 1008
        assert graph.calls == 1
