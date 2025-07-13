from src.prp_compiler.agents.base_agent import BaseAgent


class DummyModel:
    def generate_content(self, *args, **kwargs):
        class Response:
            candidates = []

            @property
            def text(self):
                raise ValueError("Could not convert `part.function_call` to text.")

        return Response()


def test_generate_content_handles_text_error(monkeypatch):
    agent = BaseAgent()
    agent.model = DummyModel()
    # disable debug to keep output clean
    monkeypatch.setattr(agent, "_log_debug", lambda *a, **k: None)
    response = agent.generate_content("prompt")
    assert response.__class__.__name__ == "Response"
