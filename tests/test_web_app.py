import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datssol.bot import BotRuntimeState
from datssol.bot import DecisionSummary
from datssol.ui.web_app import create_app


class FakeBotRunner:
    def __init__(self) -> None:
        self.state = BotRuntimeState(
            running=False,
            server="test",
            profile="safe",
            session_log_path="logs/bot-sessions/example.log",
            last_decision=DecisionSummary(turn_no=11, profile="safe", reason="idle", estimated_score=0.0, actions=()),
        )
        self.calls: list[tuple[str, object]] = []

    def get_state(self) -> BotRuntimeState:
        return self.state

    def start(self, *, server: str, profile: str, allow_prod: bool = False) -> BotRuntimeState:
        self.calls.append(("start", (server, profile, allow_prod)))
        if server == "prod" and not allow_prod:
            raise ValueError("Starting the bot on prod requires explicit allowProd=true.")
        self.state = BotRuntimeState(running=True, server=server, profile=profile, prod_guard_required=server == "prod")
        return self.state

    def stop(self) -> BotRuntimeState:
        self.calls.append(("stop", None))
        self.state = BotRuntimeState(running=False, server=self.state.server, profile=self.state.profile)
        return self.state

    def set_profile(self, profile: str) -> BotRuntimeState:
        self.calls.append(("set_profile", profile))
        self.state = BotRuntimeState(running=self.state.running, server=self.state.server, profile=profile)
        return self.state

    def set_server(self, server: str) -> BotRuntimeState:
        self.calls.append(("set_server", server))
        self.state = BotRuntimeState(running=False, server=server, profile=self.state.profile, prod_guard_required=server == "prod")
        return self.state


class WebAppBotEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = FakeBotRunner()
        self.app = create_app(bot_runner=self.runner)
        self.client = self.app.test_client()

    def test_state_endpoint_returns_bot_payload(self) -> None:
        response = self.client.get("/api/ui/bot/state")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["profile"], "safe")
        self.assertEqual(payload["data"]["sessionLogPath"], "logs/bot-sessions/example.log")
        self.assertEqual(payload["data"]["lastDecision"]["actionDetails"], [])

    def test_control_endpoint_rejects_prod_without_guard(self) -> None:
        response = self.client.post("/api/ui/bot/control", json={"action": "start", "server": "prod", "profile": "safe"})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])

    def test_control_endpoint_updates_profile(self) -> None:
        response = self.client.post("/api/ui/bot/control", json={"action": "set_profile", "profile": "aggressive"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["profile"], "aggressive")


if __name__ == "__main__":
    unittest.main()
