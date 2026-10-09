"""The real SupabaseRepository can't be run without a real Supabase project. These tests check what CAN be checked:
the RPC argument names Python sends must match the SQL function parameter names, and filters are built as intended."""
import pathlib
import re
from unittest.mock import MagicMock

from app.repositories.supabase_repository import SupabaseRepository

SQL = "".join(p.read_text() for p in sorted((pathlib.Path(__file__).parents[2] / "supabase/migrations").glob("*.sql")))
UID = "00000000-0000-0000-0000-0000000000a1"


def sql_params(fn):
    m = re.search(rf"create function public\.{fn}\((.*?)\)\s*returns", SQL, re.DOTALL)
    return {part.strip().split()[0] for part in m.group(1).split(",")}


def repo_with_mock():
    r = SupabaseRepository.__new__(SupabaseRepository)
    r.db = MagicMock()
    return r


def sent_params(r):
    return set(r.db.rpc.call_args.args[1])


def test_rpc_param_names_match_sql_signatures():
    r = repo_with_mock()
    r.rpc_create_task(UID, "t", "d", None)
    assert r.db.rpc.call_args.args[0] == "create_task" and sent_params(r) == sql_params("create_task")
    r.rpc_reassign_task("t", None)
    assert sent_params(r) == sql_params("reassign_task")
    r.rpc_set_task_status("t", "completed", UID)
    assert sent_params(r) == sql_params("set_task_status")
    r.claim_notifications(["x"], 5)
    assert sent_params(r) == sql_params("claim_notifications")


def test_visibility_filter_uses_validated_uuid():
    r = repo_with_mock()
    chain = r.db.table.return_value.select.return_value
    chain.or_.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[], count=0)
    r.list_tasks(UID, "all", None, 1, 20)
    chain.or_.assert_called_once_with(f"created_by.eq.{UID},assigned_to.eq.{UID}")


def test_filter_injection_attempt_is_rejected_before_reaching_database():
    import pytest

    from app.utils.errors import ApiError
    r = repo_with_mock()
    with pytest.raises(ApiError):
        r.list_tasks("x,assigned_to.not.is.null", "all", None, 1, 20)
    r.db.table.assert_not_called()


def test_embedded_relationship_names_exist_in_schema():
    assert "constraint tasks_created_by_fkey" in SQL and "constraint tasks_assigned_to_fkey" in SQL
