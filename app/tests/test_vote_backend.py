import asyncio
import time

import aiohttp
import pytest

from db.db_operations import PhotoRegistrationStatus
from services.vote_backend import (
    VoteBackend,
    VoteBackendBusinessError,
    VoteBackendError,
    VotePhotoState,
    _CircuitState,
)


class FakeResponse:
    def __init__(self, status: int, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse | None = None, err: Exception | None = None):
        self._response = response
        self._err = err
        self.closed = False

    def request(self, method, url, params=None, json=None):
        if self._err is not None:
            raise self._err
        assert self._response is not None
        return self._response


class TrackingVoteBackend(VoteBackend):
    def __init__(self, session: FakeSession):
        super().__init__(engine=None, api_url="http://go-api:8080", session=session)
        self.fallback_calls: list[tuple] = []

    async def _fallback_get_vote_session(self, group_id: int, user_id: int) -> VotePhotoState:
        self.fallback_calls.append(("get_vote_session", group_id, user_id))
        return VotePhotoState(
            group_id=group_id,
            photo_id=11,
            file_id="fallback-file",
            file_type="photo",
            current_index=1,
            total_photos=2,
            liked_state=0,
        )

    async def _fallback_get_relative_photo(
        self,
        group_id: int,
        user_id: int,
        current_photo_id: int,
        direction: str,
    ) -> VotePhotoState:
        self.fallback_calls.append(
            ("get_relative_photo", group_id, user_id, current_photo_id, direction)
        )
        return VotePhotoState(
            group_id=group_id,
            photo_id=current_photo_id + 1 if direction == "next" else current_photo_id - 1,
            file_id=f"{direction}-fallback",
            file_type="photo",
            current_index=2 if direction == "next" else 1,
            total_photos=3,
            liked_state=0,
        )

    async def _fallback_set_like(self, user_id: int, photo_id: int) -> int:
        self.fallback_calls.append(("set_like", user_id, photo_id))
        return 1

    async def remove_like_photo(self, user_id: int, photo_id: int) -> None:
        self.fallback_calls.append(("unset_like", user_id, photo_id))

    async def _fallback_submit_vote(self, group_id: int, user_id: int) -> None:
        self.fallback_calls.append(("submit_vote", group_id, user_id))

    async def _fallback_register_contest_submission(
        self,
        group_id: int,
        user_id: int,
        username: str,
        full_name: str,
        file_id: str,
        file_type: str,
    ) -> PhotoRegistrationStatus:
        self.fallback_calls.append(
            (
                "register_contest_submission",
                group_id,
                user_id,
                username,
                full_name,
                file_id,
                file_type,
            )
        )
        return PhotoRegistrationStatus.NEW


async def test_get_vote_session_falls_back_on_internal_error():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    state = await backend.get_vote_session(100, 42)

    assert state.file_id == "fallback-file"
    assert backend.fallback_calls == [("get_vote_session", 100, 42)]


async def test_get_vote_session_falls_back_on_malformed_payload():
    backend = TrackingVoteBackend(FakeSession(FakeResponse(200, {"group_id": 100})))

    state = await backend.get_vote_session(100, 42)

    assert state.photo_id == 11
    assert backend.fallback_calls == [("get_vote_session", 100, 42)]


async def test_get_vote_session_keeps_business_errors():
    backend = TrackingVoteBackend(FakeSession(FakeResponse(404, {"code": "no_photos"})))

    with pytest.raises(VoteBackendBusinessError) as err:
        await backend.get_vote_session(100, 42)

    assert err.value.code == "no_photos"
    assert backend.fallback_calls == []


async def test_get_next_vote_photo_falls_back_on_internal_error():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    state = await backend.get_next_vote_photo(100, 42, 11)

    assert state.file_id == "next-fallback"
    assert backend.fallback_calls == [("get_relative_photo", 100, 42, 11, "next")]


async def test_get_prev_vote_photo_falls_back_on_internal_error():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    state = await backend.get_prev_vote_photo(100, 42, 11)

    assert state.file_id == "prev-fallback"
    assert backend.fallback_calls == [("get_relative_photo", 100, 42, 11, "prev")]


async def test_set_like_falls_back_on_internal_error():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    result = await backend.set_like(100, 42, 11)

    assert result == 1
    assert backend.fallback_calls == [("set_like", 42, 11)]


async def test_unset_like_falls_back_on_internal_error():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    await backend.unset_like(100, 42, 11)

    assert backend.fallback_calls == [("unset_like", 42, 11)]


async def test_submit_vote_falls_back_on_timeout():
    backend = TrackingVoteBackend(FakeSession(err=asyncio.TimeoutError()))

    await backend.submit_vote(100, 42)

    assert backend.fallback_calls == [("submit_vote", 100, 42)]


async def test_register_submission_falls_back_on_internal_error():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    status = await backend.register_contest_submission(
        100,
        42,
        "user",
        "User Name",
        "file-1",
        "photo",
    )

    assert status == PhotoRegistrationStatus.NEW
    assert backend.fallback_calls == [
        (
            "register_contest_submission",
            100,
            42,
            "user",
            "User Name",
            "file-1",
            "photo",
        )
    ]


async def test_set_like_keeps_self_like_business_error():
    backend = TrackingVoteBackend(FakeSession(FakeResponse(409, {"code": "self_like"})))

    with pytest.raises(VoteBackendBusinessError) as err:
        await backend.set_like(100, 42, 11)

    assert err.value.code == "self_like"
    assert backend.fallback_calls == []


async def test_get_vote_session_falls_back_on_connection_error():
    backend = TrackingVoteBackend(FakeSession(err=aiohttp.ClientError()))

    state = await backend.get_vote_session(100, 42)

    assert state.file_id == "fallback-file"
    assert backend.fallback_calls == [("get_vote_session", 100, 42)]


# --- Session lifecycle tests ---


async def test_start_creates_session():
    backend = VoteBackend(engine=None, api_url="http://go-api:8080")
    assert backend._session is None

    await backend.start()

    assert backend._session is not None
    assert not backend._session.closed
    await backend.close()


async def test_get_session_before_start_raises():
    backend = VoteBackend(engine=None, api_url="http://go-api:8080")

    with pytest.raises(RuntimeError, match="call start"):
        await backend._get_session()


async def test_close_closes_session():
    backend = VoteBackend(engine=None, api_url="http://go-api:8080")
    await backend.start()
    session = backend._session

    await backend.close()

    assert session.closed


async def test_double_start_reuses_session():
    backend = VoteBackend(engine=None, api_url="http://go-api:8080")
    await backend.start()
    first_session = backend._session

    await backend.start()

    assert backend._session is first_session
    await backend.close()


async def test_start_noop_without_api_url():
    backend = VoteBackend(engine=None, api_url=None)
    await backend.start()

    assert backend._session is None


# --- Circuit breaker tests ---


async def test_circuit_opens_after_consecutive_failures():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    for _ in range(VoteBackend.CIRCUIT_FAILURE_THRESHOLD):
        await backend.get_vote_session(100, 42)

    assert backend._circuit_state is _CircuitState.OPEN
    # Next call should skip HTTP entirely (instant fallback via circuit)
    backend.fallback_calls.clear()
    await backend.get_vote_session(100, 42)
    assert backend.fallback_calls == [("get_vote_session", 100, 42)]


async def test_circuit_half_open_after_cooldown():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(500, {"code": "internal_error"}))
    )

    for _ in range(VoteBackend.CIRCUIT_FAILURE_THRESHOLD):
        await backend.get_vote_session(100, 42)

    assert backend._circuit_state is _CircuitState.OPEN

    # Simulate cooldown elapsed
    backend._circuit_opened_at = time.monotonic() - VoteBackend.CIRCUIT_COOLDOWN_SEC - 1

    backend.fallback_calls.clear()
    await backend.get_vote_session(100, 42)
    # Should have transitioned to HALF_OPEN, allowed the probe, which failed -> OPEN again
    assert backend._circuit_state is _CircuitState.OPEN


async def test_circuit_closes_on_success():
    ok_session = FakeSession(
        FakeResponse(200, {
            "group_id": 100, "photo_id": 12, "file_id": "f",
            "file_type": "photo", "current_index": 1,
            "total_photos": 5, "liked_state": 0,
        })
    )
    backend = TrackingVoteBackend(ok_session)

    # Force circuit open
    backend._circuit_state = _CircuitState.HALF_OPEN
    backend._circuit_failures = VoteBackend.CIRCUIT_FAILURE_THRESHOLD

    state = await backend.get_vote_session(100, 42)

    assert state.file_id == "f"
    assert backend._circuit_state is _CircuitState.CLOSED
    assert backend._circuit_failures == 0


async def test_circuit_resets_on_success_in_closed():
    ok_session = FakeSession(
        FakeResponse(200, {
            "group_id": 100, "photo_id": 12, "file_id": "f",
            "file_type": "photo", "current_index": 1,
            "total_photos": 5, "liked_state": 0,
        })
    )
    backend = TrackingVoteBackend(ok_session)
    backend._circuit_failures = 2  # just below threshold

    await backend.get_vote_session(100, 42)

    assert backend._circuit_failures == 0


async def test_business_error_does_not_trip_circuit():
    backend = TrackingVoteBackend(
        FakeSession(FakeResponse(404, {"code": "no_photos"}))
    )

    for _ in range(VoteBackend.CIRCUIT_FAILURE_THRESHOLD + 1):
        with pytest.raises(VoteBackendBusinessError):
            await backend.get_vote_session(100, 42)

    assert backend._circuit_state is _CircuitState.CLOSED
    assert backend._circuit_failures == 0
