import pytest

from tests.conftest import ALICE, BOB, CAROL, auth

MISSING = "00000000-0000-0000-0000-00000000ffff"


def create(client, user=ALICE, **body):
    body.setdefault("title", "Write report")
    return client.post("/api/tasks", json=body, headers=auth(user))


def test_requires_auth(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.post("/api/tasks", json={"title": "x"}).status_code == 401


def test_create_task_unassigned(client):
    r = create(client, description="d")
    body = r.get_json()
    assert r.status_code == 201 and body["task"]["status"] == "pending" and body["task"]["created_by"] == ALICE
    assert body["notification"]["status"] == "not_required"


def test_created_by_comes_from_token_not_body(client):
    r = client.post("/api/tasks", json={"title": "x", "created_by": BOB}, headers=auth(ALICE))
    assert r.status_code == 422                      # unknown field refused
    assert create(client, ALICE).get_json()["task"]["created_by"] == ALICE


def test_assign_to_existing_user_sends_email(client, sender):
    r = create(client, assigned_to=BOB)
    assert r.get_json()["notification"]["status"] == "sent"
    assert sender.sent[0]["recipient_email"] == "bob@example.test" and sender.sent[0]["event_type"] == "task_assigned"


def test_assign_to_nonexistent_user_rejected(client, repo):
    r = create(client, assigned_to=MISSING)
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "assignee_not_found"
    assert repo.tasks == {}


def test_self_assignment_sends_no_email(client, sender):
    r = create(client, assigned_to=ALICE)
    assert r.get_json()["notification"]["status"] == "not_required" and sender.sent == []


@pytest.mark.parametrize("body", [{}, {"title": ""}, {"title": "   "}, {"title": "x" * 201},
                                  {"title": "ok", "assigned_to": "nope"}, {"title": "ok", "status": "completed"}])
def test_invalid_payloads_422(client, body):
    r = client.post("/api/tasks", json=body, headers=auth())
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "validation_error"


def test_non_json_body_400(client):
    r = client.post("/api/tasks", data="hello", headers=auth())
    assert r.status_code == 400


def test_list_roles_status_and_pagination(client):
    for i in range(3):
        create(client, ALICE, title=f"a{i}", assigned_to=BOB)
    create(client, BOB, title="b", assigned_to=ALICE)
    get = lambda user, q: client.get(f"/api/tasks?{q}", headers=auth(user)).get_json()
    assert get(ALICE, "role=created")["total"] == 3
    assert get(ALICE, "role=assigned")["total"] == 1
    assert get(ALICE, "")["total"] == 4
    assert get(BOB, "role=assigned")["total"] == 3
    assert get(CAROL, "")["total"] == 0
    page = get(ALICE, "page=2&page_size=3")
    assert len(page["tasks"]) == 1 and page["total"] == 4
    assert get(ALICE, "status=completed")["total"] == 0
    assert client.get("/api/tasks?status=bogus", headers=auth()).status_code == 422
    assert client.get("/api/tasks?page_size=1000", headers=auth()).status_code == 422


def test_summary_counts(client):
    t = create(client, assigned_to=BOB).get_json()["task"]["id"]
    create(client)
    client.patch(f"/api/tasks/{t}/status", json={"status": "completed"}, headers=auth(BOB))
    assert client.get("/api/tasks/summary", headers=auth(ALICE)).get_json()["counts"] == {"pending": 1, "in_progress": 0, "completed": 1}


def test_unrelated_user_gets_404_everywhere(client):
    t = create(client, assigned_to=BOB).get_json()["task"]["id"]
    h = auth(CAROL)
    assert client.get(f"/api/tasks/{t}", headers=h).status_code == 404
    assert client.patch(f"/api/tasks/{t}", json={"title": "x"}, headers=h).status_code == 404
    assert client.patch(f"/api/tasks/{t}/status", json={"status": "completed"}, headers=h).status_code == 404
    assert client.patch(f"/api/tasks/{t}/assignee", json={"assigned_to": CAROL}, headers=h).status_code == 404
    assert client.delete(f"/api/tasks/{t}", headers=h).status_code == 404
    assert client.get(f"/api/tasks/{MISSING}", headers=h).status_code == 404     # same answer as 'not yours'


def test_bad_uuid_in_url_422(client):
    assert client.get("/api/tasks/not-a-uuid", headers=auth()).status_code == 422


def test_get_task_includes_permissions(client):
    t = create(client, assigned_to=BOB).get_json()["task"]["id"]
    creator_view = client.get(f"/api/tasks/{t}", headers=auth(ALICE)).get_json()["task"]["permissions"]
    assignee_view = client.get(f"/api/tasks/{t}", headers=auth(BOB)).get_json()["task"]["permissions"]
    assert creator_view == {"can_edit": True, "can_reassign": True, "can_delete": True, "can_change_status": True}
    assert assignee_view == {"can_edit": False, "can_reassign": False, "can_delete": False, "can_change_status": True}


def test_creator_can_edit_assignee_cannot(client):
    t = create(client, assigned_to=BOB).get_json()["task"]["id"]
    ok = client.patch(f"/api/tasks/{t}", json={"title": "New"}, headers=auth(ALICE))
    assert ok.status_code == 200 and ok.get_json()["task"]["title"] == "New"
    assert client.patch(f"/api/tasks/{t}", json={"title": "Hack"}, headers=auth(BOB)).status_code == 403
    assert client.patch(f"/api/tasks/{t}", json={}, headers=auth(ALICE)).status_code == 422


def test_only_creator_can_reassign_and_delete(client, repo):
    t = create(client, assigned_to=BOB).get_json()["task"]["id"]
    assert client.patch(f"/api/tasks/{t}/assignee", json={"assigned_to": CAROL}, headers=auth(BOB)).status_code == 403
    assert client.delete(f"/api/tasks/{t}", headers=auth(BOB)).status_code == 403
    r = client.patch(f"/api/tasks/{t}/assignee", json={"assigned_to": CAROL}, headers=auth(ALICE))
    assert r.status_code == 200 and r.get_json()["task"]["assigned_to"] == CAROL
    assert client.patch(f"/api/tasks/{t}", json={"title": "x"}, headers=auth(BOB)).status_code == 404  # no longer involved
    assert client.delete(f"/api/tasks/{t}", headers=auth(ALICE)).status_code == 204
    assert t not in repo.tasks


def test_reassign_to_nonexistent_user_rejected(client):
    t = create(client).get_json()["task"]["id"]
    r = client.patch(f"/api/tasks/{t}/assignee", json={"assigned_to": MISSING}, headers=auth())
    assert r.status_code == 422
    assert client.patch(f"/api/tasks/{t}/assignee", json={}, headers=auth()).status_code == 422


def test_assignee_completes_and_reopens(client):
    t = create(client, assigned_to=BOB).get_json()["task"]["id"]
    done = client.patch(f"/api/tasks/{t}/status", json={"status": "completed"}, headers=auth(BOB)).get_json()
    assert done["task"]["status"] == "completed" and done["task"]["completed_at"]
    reopened = client.patch(f"/api/tasks/{t}/status", json={"status": "in_progress"}, headers=auth(BOB)).get_json()
    assert reopened["task"]["status"] == "in_progress" and reopened["task"]["completed_at"] is None
    assert client.patch(f"/api/tasks/{t}/status", json={"status": "weird"}, headers=auth(BOB)).status_code == 422
