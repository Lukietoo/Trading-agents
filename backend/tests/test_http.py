# Retry and backoff. `sleep` is injected and records what it was asked to
# wait, so the delays are asserted rather than spent.

import httpx
import pytest

from app.data.http import RetryPolicy, UpstreamError, get_json


class SleepSpy:
    def __init__(self):
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


class Responder:
    """Returns each queued response in turn, repeating the last one forever."""

    def __init__(self, *responses: httpx.Response | Exception):
        self.responses = list(responses)
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        outcome = self.responses[index]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def ok(body=None) -> httpx.Response:
    return httpx.Response(200, json=body if body is not None else {"ok": True})


def status(code: int, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(code, json={"message": "nope"}, headers=headers or {})


NO_WAIT = RetryPolicy(attempts=4, base_delay=0.5, jitter=False)


async def call(responder: Responder, *, policy=NO_WAIT, sleep=None):
    sleep = sleep or SleepSpy()
    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
        return await get_json(
            client, "https://example.test/data", policy=policy, sleep=sleep, source="testsource"
        )


async def test_a_successful_call_returns_the_body():
    assert await call(Responder(ok({"value": 1}))) == {"value": 1}


async def test_a_successful_call_does_not_sleep():
    sleep = SleepSpy()

    await call(Responder(ok()), sleep=sleep)

    assert sleep.delays == []


async def test_a_rate_limit_is_retried_and_then_succeeds():
    responder = Responder(status(429), ok({"value": 2}))

    assert await call(responder) == {"value": 2}
    assert responder.calls == 2


@pytest.mark.parametrize("code", [500, 502, 503, 504])
async def test_transient_server_errors_are_retried(code: int):
    responder = Responder(status(code), ok())

    await call(responder)

    assert responder.calls == 2


@pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
async def test_client_errors_are_not_retried(code: int):
    # Repeating a bad request just repeats the mistake.
    responder = Responder(status(code))

    with pytest.raises(UpstreamError, match="Not retryable"):
        await call(responder)

    assert responder.calls == 1


async def test_a_connection_failure_is_retried():
    responder = Responder(httpx.ConnectError("connection reset"), ok())

    await call(responder)

    assert responder.calls == 2


async def test_attempts_are_exhausted_then_it_raises():
    responder = Responder(status(503))

    with pytest.raises(UpstreamError) as caught:
        await call(responder)

    assert responder.calls == NO_WAIT.attempts
    assert "testsource" in str(caught.value)
    assert "HTTP 503" in str(caught.value)


async def test_the_error_names_the_last_connection_failure():
    responder = Responder(httpx.ConnectTimeout("timed out"))

    with pytest.raises(UpstreamError, match="ConnectTimeout"):
        await call(responder)


async def test_backoff_grows_exponentially():
    sleep = SleepSpy()
    responder = Responder(status(503))

    with pytest.raises(UpstreamError):
        await call(responder, sleep=sleep)

    # One sleep fewer than attempts: nothing is gained by waiting after the
    # final failure.
    assert sleep.delays == [0.5, 1.0, 2.0]


async def test_backoff_is_capped():
    sleep = SleepSpy()
    policy = RetryPolicy(attempts=8, base_delay=1.0, max_delay=4.0, jitter=False)

    with pytest.raises(UpstreamError):
        await call(Responder(status(503)), policy=policy, sleep=sleep)

    assert max(sleep.delays) == 4.0


async def test_jitter_keeps_the_delay_within_the_computed_ceiling():
    # Full jitter: a batch of clients must not retry in lockstep, but no wait
    # may exceed what plain backoff would have chosen.
    policy = RetryPolicy(attempts=6, base_delay=1.0, max_delay=8.0, jitter=True)
    sleep = SleepSpy()

    with pytest.raises(UpstreamError):
        await call(Responder(status(503)), policy=policy, sleep=sleep)

    ceilings = [1.0, 2.0, 4.0, 8.0, 8.0]
    assert all(0 <= delay <= ceiling for delay, ceiling in zip(sleep.delays, ceilings, strict=True))
    assert len(set(sleep.delays)) > 1


async def test_retry_after_overrides_the_computed_backoff():
    # The server knows when it will serve us again.
    sleep = SleepSpy()
    responder = Responder(status(429, {"Retry-After": "3"}), ok())

    await call(responder, sleep=sleep)

    assert sleep.delays == [3.0]


async def test_retry_after_is_still_capped():
    sleep = SleepSpy()
    policy = RetryPolicy(attempts=2, base_delay=0.5, max_delay=5.0, jitter=False)

    await call(Responder(status(429, {"Retry-After": "600"}), ok()), policy=policy, sleep=sleep)

    assert sleep.delays == [5.0]


async def test_an_unparseable_retry_after_falls_back_to_backoff():
    # The header also permits an HTTP date, which we do not parse.
    sleep = SleepSpy()
    responder = Responder(status(429, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), ok())

    await call(responder, sleep=sleep)

    assert sleep.delays == [0.5]


async def test_the_error_message_does_not_leak_the_response_body():
    # FRED takes its API key in the query string, and an error body can echo
    # the request back. Nothing from the body reaches the message.
    responder = Responder(httpx.Response(403, json={"error": "bad key abc123secret"}))

    with pytest.raises(UpstreamError) as caught:
        await call(responder)

    assert "abc123secret" not in str(caught.value)
