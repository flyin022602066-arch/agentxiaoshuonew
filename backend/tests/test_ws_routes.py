import pytest


@pytest.mark.asyncio
async def test_websocket_route_keeps_connection_manager_after_task_status_lookup(client, monkeypatch):
    from app.api import ws_routes

    events = []

    class StubWebSocket:
        async def accept(self):
            events.append(("accept", None))

        async def send_json(self, payload):
            events.append(("send_json", payload))

        async def receive_json(self):
            if not hasattr(self, "_sent_task_status"):
                self._sent_task_status = True
                return {"type": "get_task_status", "data": {"task_id": "task-1"}}
            raise ws_routes.WebSocketDisconnect()

    class StubConnectionManager:
        async def connect(self, websocket, client_id):
            events.append(("connect", client_id))

        async def disconnect(self, client_id):
            events.append(("disconnect", client_id))

        def subscribe(self, client_id, topic):
            events.append(("subscribe", client_id, topic))

        def unsubscribe(self, client_id, topic):
            events.append(("unsubscribe", client_id, topic))

        async def send_personal_message(self, message, client_id):
            events.append(("personal_message", client_id, message))

        async def handle_message(self, client_id, data):
            events.append(("handle_message", client_id, data))

    class StubBroadcaster:
        async def broadcast_log(self, level, message, agent_id="system"):
            events.append(("broadcast_log", level, message, agent_id))

    class StubTask:
        def to_dict(self):
            return {"task_id": "task-1", "status": "running"}

    class StubTaskManager:
        def get_task(self, task_id):
            events.append(("get_task", task_id))
            return StubTask()

    connection_manager = StubConnectionManager()

    monkeypatch.setattr(ws_routes, "get_connection_manager", lambda: connection_manager, raising=False)
    monkeypatch.setattr(ws_routes, "get_agent_broadcaster", lambda: StubBroadcaster(), raising=False)
    monkeypatch.setattr("app.api.websocket.get_connection_manager", lambda: connection_manager)
    monkeypatch.setattr("app.api.websocket.get_agent_broadcaster", lambda: StubBroadcaster())
    monkeypatch.setattr("app.tasks.task_manager.get_task_manager", lambda: StubTaskManager())

    await ws_routes.websocket_endpoint(StubWebSocket(), client_id="client-1")

    assert ("get_task", "task-1") in events
    assert ("disconnect", "client-1") in events
