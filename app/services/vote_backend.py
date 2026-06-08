from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum as _Enum
from typing import Any

import aiohttp
from sqlalchemy import and_, delete, exc as sa_exc, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from db.db_classes import Contest, Group, Photo, User, contest_user, group_photo, photo_like, tmp_photo_like
from db.db_operations import (
    LikeDB,
    ObjectFactory,
    PhotoRegistrationStatus,
    RegisterDB,
    VoteDB,
)

logger = logging.getLogger(__name__)

KNOWN_BUSINESS_ERROR_CODES = frozenset(
    {
        "no_photos",
        "no_vote_yet",
        "already_voted",
        "self_like",
        "photo_not_found",
        "group_not_found",
        "user_not_found",
    }
)


class VoteBackendError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class VoteBackendBusinessError(VoteBackendError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class VotePhotoState:
    group_id: int
    photo_id: int
    file_id: str
    file_type: str
    current_index: int
    total_photos: int
    liked_state: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "VotePhotoState":
        try:
            return cls(
                group_id=int(payload["group_id"]),
                photo_id=int(payload["photo_id"]),
                file_id=str(payload["file_id"]),
                file_type=str(payload["file_type"]),
                current_index=int(payload["current_index"]),
                total_photos=int(payload["total_photos"]),
                liked_state=int(payload["liked_state"]),
            )
        except (KeyError, TypeError, ValueError) as err:
            raise VoteBackendError("invalid vote photo state payload") from err


class _CircuitState(_Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class VoteBackend(LikeDB):
    CIRCUIT_FAILURE_THRESHOLD = 3
    CIRCUIT_COOLDOWN_SEC = 15.0

    def __init__(
        self,
        engine: AsyncEngine,
        api_url: str | None = None,
        timeout_sec: float = 3.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        super().__init__(engine)
        self._api_url = api_url.rstrip("/") if api_url else None
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)
        self._session = session
        self._owns_session = session is None
        self._circuit_state = _CircuitState.CLOSED
        self._circuit_failures = 0
        self._circuit_opened_at = 0.0

    async def start(self) -> None:
        if self._api_url and self._owns_session and (self._session is None or self._session.closed):
            self._session = aiohttp.ClientSession(timeout=self._timeout)

    async def close(self) -> None:
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def get_vote_session(self, group_id: int, user_id: int) -> VotePhotoState:
        if self._api_url:
            try:
                payload = await self._request(
                    "GET",
                    "/vote/session",
                    params={"group_id": group_id, "user_id": user_id},
                )
                return VotePhotoState.from_payload(payload)
            except VoteBackendBusinessError:
                raise
            except VoteBackendError as err:
                self._log_fallback("get_vote_session", err)
        return await self._fallback_get_vote_session(group_id, user_id)

    async def get_next_vote_photo(
        self, group_id: int, user_id: int, current_photo_id: int
    ) -> VotePhotoState:
        if self._api_url:
            try:
                payload = await self._request(
                    "GET",
                    "/vote/photos/next",
                    params={
                        "group_id": group_id,
                        "user_id": user_id,
                        "current_photo_id": current_photo_id,
                    },
                )
                return VotePhotoState.from_payload(payload)
            except VoteBackendBusinessError:
                raise
            except VoteBackendError as err:
                self._log_fallback("get_next_vote_photo", err)
        return await self._fallback_get_relative_photo(
            group_id, user_id, current_photo_id, "next"
        )

    async def get_prev_vote_photo(
        self, group_id: int, user_id: int, current_photo_id: int
    ) -> VotePhotoState:
        if self._api_url:
            try:
                payload = await self._request(
                    "GET",
                    "/vote/photos/prev",
                    params={
                        "group_id": group_id,
                        "user_id": user_id,
                        "current_photo_id": current_photo_id,
                    },
                )
                return VotePhotoState.from_payload(payload)
            except VoteBackendBusinessError:
                raise
            except VoteBackendError as err:
                self._log_fallback("get_prev_vote_photo", err)
        return await self._fallback_get_relative_photo(
            group_id, user_id, current_photo_id, "prev"
        )

    async def set_like(self, group_id: int, user_id: int, photo_id: int) -> int:
        if self._api_url:
            try:
                await self._request(
                    "POST",
                    "/vote/likes",
                    json_body={
                        "group_id": group_id,
                        "user_id": user_id,
                        "photo_id": photo_id,
                    },
                )
                return 1
            except VoteBackendBusinessError:
                raise
            except VoteBackendError as err:
                self._log_fallback("set_like", err)
        return await self._fallback_set_like(user_id, photo_id)

    async def unset_like(self, group_id: int, user_id: int, photo_id: int) -> None:
        if self._api_url:
            try:
                await self._request(
                    "DELETE",
                    "/vote/likes",
                    json_body={
                        "group_id": group_id,
                        "user_id": user_id,
                        "photo_id": photo_id,
                    },
                )
                return
            except VoteBackendBusinessError:
                raise
            except VoteBackendError as err:
                self._log_fallback("unset_like", err)
        await self.remove_like_photo(user_id, photo_id)

    async def submit_vote(self, group_id: int, user_id: int) -> None:
        if self._api_url:
            try:
                await self._request(
                    "POST",
                    "/vote/submit",
                    json_body={"group_id": group_id, "user_id": user_id},
                )
                return
            except VoteBackendBusinessError:
                raise
            except VoteBackendError as err:
                self._log_fallback("submit_vote", err)
        await self._fallback_submit_vote(group_id, user_id)

    async def register_contest_submission(
        self,
        group_id: int,
        user_id: int,
        username: str,
        full_name: str,
        file_id: str,
        file_type: str,
    ) -> PhotoRegistrationStatus:
        if self._api_url:
            try:
                payload = await self._request(
                    "POST",
                    "/contest/submissions",
                    json_body={
                        "group_id": group_id,
                        "user_id": user_id,
                        "username": username,
                        "full_name": full_name,
                        "file_id": file_id,
                        "file_type": file_type,
                    },
                )
                status = payload.get("status")
                if status == PhotoRegistrationStatus.NEW.value:
                    return PhotoRegistrationStatus.NEW
                if status == PhotoRegistrationStatus.CHANGED.value:
                    return PhotoRegistrationStatus.CHANGED
                raise VoteBackendError("unexpected submission status")
            except VoteBackendBusinessError:
                raise
            except VoteBackendError as err:
                self._log_fallback("register_contest_submission", err)
        return await self._fallback_register_contest_submission(
            group_id, user_id, username, full_name, file_id, file_type
        )

    async def _fallback_get_vote_session(
        self, group_id: int, user_id: int
    ) -> VotePhotoState:
        photo_ids = await self.select_contest_photos_primary_ids(group_id)
        if not photo_ids:
            raise VoteBackendBusinessError("no_photos")

        vote_db = VoteDB(self.engine)
        if await vote_db.get_current_vote_status(group_id) is False:
            raise VoteBackendBusinessError("no_vote_yet")
        if await vote_db.is_user_not_allowed_to_vote(group_id, user_id) is True:
            raise VoteBackendBusinessError("already_voted")

        first_photo_id = photo_ids[0]
        file_id = await self.select_file_id(first_photo_id)
        file_type = await self.select_file_type(first_photo_id)
        liked_state = await self.is_photo_liked(user_id, first_photo_id)
        return VotePhotoState(
            group_id=group_id,
            photo_id=first_photo_id,
            file_id=file_id,
            file_type=file_type,
            current_index=1,
            total_photos=len(photo_ids),
            liked_state=liked_state,
        )

    async def _fallback_get_relative_photo(
        self, group_id: int, user_id: int, current_photo_id: int, direction: str
    ) -> VotePhotoState:
        photo_ids = await self.select_contest_photos_primary_ids(group_id)
        if not photo_ids:
            raise VoteBackendBusinessError("no_photos")

        if direction == "next":
            next_photo = await self.select_next_contest_photo(group_id, current_photo_id)
        else:
            next_photo = await self.select_prev_contest_photo(group_id, current_photo_id)

        if len(next_photo) != 2:
            raise VoteBackendBusinessError("photo_not_found")

        file_id, photo_id = next_photo
        file_type = await self.select_file_type(int(photo_id))
        liked_state = await self.is_photo_liked(user_id, int(photo_id))

        try:
            current_index = photo_ids.index(int(photo_id)) + 1
        except ValueError as err:
            raise VoteBackendError("unknown photo position") from err

        return VotePhotoState(
            group_id=group_id,
            photo_id=int(photo_id),
            file_id=file_id,
            file_type=file_type,
            current_index=current_index,
            total_photos=len(photo_ids),
            liked_state=liked_state,
        )

    async def _fallback_set_like(self, user_id: int, photo_id: int) -> int:
        try:
            return await self.like_photo(user_id, photo_id)
        except sa_exc.IntegrityError:
            return 1

    async def _fallback_submit_vote(self, group_id: int, user_id: int) -> None:
        vote_db = VoteDB(self.engine)
        if await vote_db.is_user_not_allowed_to_vote(group_id, user_id) is True:
            raise VoteBackendBusinessError("already_voted")

        contest_id = await vote_db.get_contest_id(group_id)
        db_user_id = await vote_db.get_user_id(user_id)

        likes_select = (
            select(tmp_photo_like.c.user_id, tmp_photo_like.c.photo_id)
            .join(User, User.id == tmp_photo_like.c.user_id)
            .join(group_photo, tmp_photo_like.c.photo_id == group_photo.c.photo_id)
            .join(Photo, Photo.id == tmp_photo_like.c.photo_id)
            .join(Group, Group.id == group_photo.c.group_id)
            .where(
                (Group.telegram_id == group_id)
                & (User.telegram_id == user_id)
            )
        )
        insert_likes = insert(photo_like).from_select(
            ["user_id", "photo_id"], likes_select
        )
        delete_tmp = delete(tmp_photo_like).where(
            and_(
                tmp_photo_like.c.user_id == likes_select.subquery().c.user_id,
                tmp_photo_like.c.photo_id == likes_select.subquery().c.photo_id,
            )
        )
        mark_voted = insert(contest_user).values(
            contest_id=contest_id, user_id=db_user_id
        )

        try:
            async with AsyncSession(self.engine) as session:
                async with session.begin():
                    await session.execute(insert_likes)
                    await session.execute(delete_tmp)
                    await session.execute(mark_voted)
        except sa_exc.IntegrityError as err:
            raise VoteBackendBusinessError("already_voted") from err

    async def _fallback_register_contest_submission(
        self,
        group_id: int,
        user_id: int,
        username: str,
        full_name: str,
        file_id: str,
        file_type: str,
    ) -> PhotoRegistrationStatus:
        register_unit = RegisterDB(self.engine)
        user = ObjectFactory.build_user(username, full_name, user_id)
        await register_unit.register_user(user, group_id)
        registration_status = await register_unit.register_photo_for_contest(
            user_id,
            group_id,
            file_get_id=file_id,
            type=file_type,
        )
        if registration_status == PhotoRegistrationStatus.NEW:
            try:
                await register_unit.register_participant(user_id, group_id)
            except sa_exc.IntegrityError:
                pass
        return registration_status

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._api_url:
            raise VoteBackendError("sidecar disabled")

        self._check_circuit()

        session = await self._get_session()
        url = f"{self._api_url}{path}"
        try:
            async with session.request(
                method,
                url,
                params=params,
                json=json_body,
            ) as response:
                try:
                    payload = await response.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError):
                    payload = {}

                if response.status >= 400:
                    code = payload.get("code") if isinstance(payload, dict) else None
                    if response.status < 500 and code in KNOWN_BUSINESS_ERROR_CODES:
                        self._circuit_record_success()
                        raise VoteBackendBusinessError(code)
                    self._circuit_record_failure()
                    raise VoteBackendError(
                        "unexpected sidecar status",
                        status=response.status,
                        code=code if isinstance(code, str) else None,
                    )

                if not isinstance(payload, dict):
                    self._circuit_record_failure()
                    raise VoteBackendError("sidecar payload must be an object")
                self._circuit_record_success()
                return payload
        except VoteBackendBusinessError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            self._circuit_record_failure()
            raise VoteBackendError("sidecar request failed") from err

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            raise RuntimeError(
                "VoteBackend session not initialized — call start() first"
            )
        return self._session

    def _check_circuit(self) -> None:
        if self._circuit_state is _CircuitState.CLOSED:
            return
        if self._circuit_state is _CircuitState.OPEN:
            elapsed = time.monotonic() - self._circuit_opened_at
            if elapsed >= self.CIRCUIT_COOLDOWN_SEC:
                self._circuit_state = _CircuitState.HALF_OPEN
                logger.info("Circuit breaker half-open, allowing probe request")
                return
            raise VoteBackendError("circuit breaker open", status=None, code="circuit_open")
        # HALF_OPEN — allow one probe request through

    def _circuit_record_success(self) -> None:
        if self._circuit_state is not _CircuitState.CLOSED:
            logger.info("Circuit breaker closed after successful probe")
        self._circuit_state = _CircuitState.CLOSED
        self._circuit_failures = 0

    def _circuit_record_failure(self) -> None:
        self._circuit_failures += 1
        if self._circuit_failures >= self.CIRCUIT_FAILURE_THRESHOLD:
            self._circuit_state = _CircuitState.OPEN
            self._circuit_opened_at = time.monotonic()
            logger.warning(
                "Circuit breaker opened after %d consecutive failures",
                self._circuit_failures,
            )

    def _log_fallback(self, operation: str, err: VoteBackendError) -> None:
        logger.warning(
            "Go sidecar failed for %s; falling back to Python DB path "
            "(status=%s, code=%s): %s",
            operation,
            err.status,
            err.code,
            err,
        )
