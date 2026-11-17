from cookbook.ingest import CachedTranscriber
from fakes import FakeTranscriber


def cached(inner, tmp_path, namespace="model-a/prompt-v1"):
    return CachedTranscriber(inner, tmp_path / "cache", namespace)


def test_second_call_for_the_same_image_does_not_reach_the_model(tmp_path):
    inner = FakeTranscriber("Sauerbraten")
    transcriber = cached(inner, tmp_path)

    first = transcriber.transcribe(b"image-bytes", "image/jpeg")
    second = transcriber.transcribe(b"image-bytes", "image/jpeg")

    assert len(inner.calls) == 1
    assert second.text == first.text == "Sauerbraten"
    assert second.uncertain == first.uncertain


def test_cached_result_is_flagged_so_cost_is_not_counted_twice(tmp_path):
    transcriber = cached(FakeTranscriber(), tmp_path)

    first = transcriber.transcribe(b"image-bytes", "image/jpeg")
    second = transcriber.transcribe(b"image-bytes", "image/jpeg")

    assert not first.usage.cached
    assert second.usage.cached


def test_different_image_is_a_cache_miss(tmp_path):
    inner = FakeTranscriber()
    transcriber = cached(inner, tmp_path)

    transcriber.transcribe(b"page-1", "image/jpeg")
    transcriber.transcribe(b"page-2", "image/jpeg")

    assert len(inner.calls) == 2


def test_changing_model_or_prompt_invalidates_the_cache(tmp_path):
    inner = FakeTranscriber()

    cached(inner, tmp_path, "model-a/prompt-v1").transcribe(b"page", "image/jpeg")
    cached(inner, tmp_path, "model-a/prompt-v2").transcribe(b"page", "image/jpeg")
    cached(inner, tmp_path, "model-b/prompt-v1").transcribe(b"page", "image/jpeg")

    assert len(inner.calls) == 3


def test_cache_survives_a_new_instance(tmp_path):
    inner = FakeTranscriber()

    cached(inner, tmp_path).transcribe(b"page", "image/jpeg")
    cached(inner, tmp_path).transcribe(b"page", "image/jpeg")

    assert len(inner.calls) == 1
