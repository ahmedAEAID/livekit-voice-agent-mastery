import importlib.util
from pathlib import Path


def load_rpc_module():
    path = Path("04_rpc_communication/rpc_from_frontend.py")
    spec = importlib.util.spec_from_file_location("rpc_from_frontend_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rpc_state_crud_cycle() -> None:
    module = load_rpc_module()
    state = module.UserSessionData()

    object_id = state.create_object("note", {"title": "First", "content": "Body"})
    assert state.read_object(object_id)["data"]["title"] == "First"

    assert state.update_object(object_id, {"title": "Updated"}) is True
    assert state.read_object(object_id)["data"]["title"] == "Updated"
    assert "updated_at" in state.read_object(object_id)

    assert list(state.list_objects("note")) == [object_id]
    assert state.delete_object(object_id) is True
    assert state.read_object(object_id) is None
