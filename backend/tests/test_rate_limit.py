# Rate limiter, on a hand-cranked clock. A test that actually waited a minute
# to prove the limiter waits a minute would not survive contact with CI.

import asyncio

import pytest

from app.data.rate_limit import RateLimiter


class FakeClock:
    """A clock whose only way of moving is being told to.

    `sleep` advances it, which is what makes the limiter's own waiting
    observable: every delay it asks for shows up in `slept`.
    """

    def __init__(self):
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def limiter(clock: FakeClock, max_calls: int = 3, per: float = 60.0) -> RateLimiter:
    return RateLimiter(max_calls, per, now=clock, sleep=clock.sleep)


async def test_calls_under_the_limit_never_wait(clock: FakeClock):
    limit = limiter(clock, max_calls=3)

    for _ in range(3):
        await limit.acquire()

    assert clock.slept == []


async def test_the_call_that_would_break_the_limit_waits(clock: FakeClock):
    # N+1 rapid calls: the last one is made to wait rather than rejected.
    limit = limiter(clock, max_calls=3, per=60.0)

    for _ in range(4):
        await limit.acquire()

    assert clock.slept == [60.0]


async def test_no_window_ever_holds_more_than_the_limit(clock: FakeClock):
    # The property that matters, checked directly: slide a window of `per`
    # across every recorded call time and count.
    limit = limiter(clock, max_calls=5, per=60.0)
    made: list[float] = []

    for _ in range(23):
        await limit.acquire()
        made.append(clock.now)

    for start in made:
        in_window = [t for t in made if start <= t < start + 60.0]
        assert len(in_window) <= 5


async def test_it_waits_only_as_long_as_it_must(clock: FakeClock):
    # Half the window has already passed, so only the remainder is owed.
    limit = limiter(clock, max_calls=2, per=60.0)
    await limit.acquire()
    await limit.acquire()

    clock.advance(45.0)
    await limit.acquire()

    assert clock.slept == [15.0]


async def test_a_call_outside_the_window_does_not_count(clock: FakeClock):
    limit = limiter(clock, max_calls=2, per=60.0)
    await limit.acquire()
    await limit.acquire()

    clock.advance(61.0)
    await limit.acquire()
    await limit.acquire()

    assert clock.slept == []


async def test_a_steady_drip_never_waits(clock: FakeClock):
    limit = limiter(clock, max_calls=6, per=60.0)

    for _ in range(50):
        await limit.acquire()
        clock.advance(10.0)

    assert clock.slept == []


async def test_concurrent_callers_do_not_collectively_overrun(clock: FakeClock):
    # The failure this guards: twenty coroutines started by gather each see an
    # empty window, all decide they are within the limit, and fire at once.
    limit = limiter(clock, max_calls=4, per=60.0)
    made: list[float] = []

    async def caller():
        await limit.acquire()
        made.append(clock.now)

    await asyncio.gather(*(caller() for _ in range(20)))

    assert len(made) == 20
    for start in made:
        assert len([t for t in made if start <= t < start + 60.0]) <= 4


async def test_calls_in_window_reports_the_live_count(clock: FakeClock):
    limit = limiter(clock, max_calls=5, per=60.0)
    await limit.acquire()
    await limit.acquire()

    assert limit.calls_in_window == 2

    clock.advance(61.0)
    assert limit.calls_in_window == 0


def test_a_limit_below_one_is_rejected():
    # Would deadlock on the first acquire rather than fail visibly.
    with pytest.raises(ValueError, match="at least 1"):
        RateLimiter(0)
