import base64
from types import SimpleNamespace

import pytest

from cookbook.ingest import ClaudeTranscriber, TranscriptionError


class FakeClient:
    """Stands in for anthropic.Anthropic; records the request it receives."""

    def __init__(self, stop_reason="end_turn", parsed=True):
        self.request = None
        self._stop_reason = stop_reason
        self._parsed = parsed
        self.messages = SimpleNamespace(parse=self._parse)

    def _parse(self, **request):
        self.request = request
        output = request["output_format"](
            text="Man läßt den Braten garbrötscheln[?].",
            decoration_text=["Korinthen", "189"],
            uncertain=["garbrötscheln"],
        )
        return SimpleNamespace(
            stop_reason=self._stop_reason,
            parsed_output=output if self._parsed else None,
            usage=SimpleNamespace(input_tokens=1500, output_tokens=300),
        )


def transcriber_with(client, model="claude-haiku-5-5"):
    return ClaudeTranscriber(model=model, client_factory=lambda: client)


def test_sends_the_image_and_maps_the_answer():
    client = FakeClient()

    result = transcriber_with(client).transcribe(b"jpeg-bytes", "image/jpeg")

    image_block = client.request["messages"][0]["content"][0]
    assert client.request["model"] == "claude-haiku-5-5"
    assert image_block["source"]["media_type"] == "image/jpeg"
    assert base64.standard_b64decode(image_block["source"]["data"]) == b"jpeg-bytes"
    assert result.text == "Man läßt den Braten garbrötscheln[?]."
    assert result.decoration_text == ("Korinthen", "189")
    assert result.uncertain == ("garbrötscheln",)


def test_reports_tokens_and_time_for_cost_tracking():
    result = transcriber_with(FakeClient()).transcribe(b"x", "image/jpeg")

    assert (result.usage.input_tokens, result.usage.output_tokens) == (1500, 300)
    assert result.usage.model == "claude-haiku-5-5"
    assert result.usage.seconds >= 0
    assert not result.usage.cached


def test_does_not_send_sampling_parameters_the_model_rejects():
    client = FakeClient()

    transcriber_with(client).transcribe(b"x", "image/jpeg")

    assert not {"temperature", "top_p", "top_k"} & client.request.keys()


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_unfinished_answer_is_an_error_not_a_partial_transcription(stop_reason):
    with pytest.raises(TranscriptionError, match=stop_reason):
        transcriber_with(FakeClient(stop_reason=stop_reason)).transcribe(b"x", "image/jpeg")


def test_missing_structured_output_is_an_error():
    with pytest.raises(TranscriptionError, match="no structured transcription"):
        transcriber_with(FakeClient(parsed=False)).transcribe(b"x", "image/jpeg")


def test_missing_credentials_become_a_readable_error():
    client = FakeClient()

    def no_credentials(**_):
        raise TypeError('"Could not resolve authentication method."')

    client.messages.parse = no_credentials

    with pytest.raises(TranscriptionError, match="set ANTHROPIC_API_KEY"):
        transcriber_with(client).transcribe(b"x", "image/jpeg")


def test_client_is_not_created_until_a_page_needs_it():
    created = []
    transcriber = ClaudeTranscriber(
        model="claude-haiku-5-5", client_factory=lambda: created.append(1) or FakeClient()
    )

    assert created == []
    transcriber.transcribe(b"x", "image/jpeg")
    transcriber.transcribe(b"y", "image/jpeg")
    assert created == [1]


def test_cache_namespace_changes_with_the_model():
    assert (
        transcriber_with(FakeClient(), "claude-haiku-5-5").cache_namespace
        != transcriber_with(FakeClient(), "claude-sonnet-5-5").cache_namespace
    )
