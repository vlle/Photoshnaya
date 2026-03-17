from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import aiohttp
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncEngine

from db.db_operations import (
    LikeDB,
    ObjectFactory,
    PhotoRegistrationStatus,
    RegisterDB,
    VoteDB,
)


class VoteBackendError(Exception):
    pass


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
        return cls(
            group_id=int(payload["group_id"]),
            photo_id=int(payload["photo_id"]),
            file_id=str(payload["file_id"]),
            file_type=str(payload["file_type"]),
            current_index=int(payload["current_index"]),
            total_photos=int(payload["total_photos"]),
            liked_state=int(payload["liked_state"]),
        )


class VoteBackend(LikeDB):
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
            except VoteBackendError:
                pass
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
            except VoteBackendError:
                pass
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
            except VoteBackendError:
                pass
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
            except VoteBackendError:
                pass
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
            except VoteBackendError:
                pass
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
            except VoteBackendError:
                pass
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
            except VoteBackendError:
                pass
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

        try:
            await self.insert_all_likes(user_id, group_id)
            await self.delete_likes_from_tmp_vote(user_id, group_id)
            await vote_db.mark_user_voted(group_id, user_id)
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
                    if isinstance(code, str):
                        raise VoteBackendBusinessError(code)
                    raise VoteBackendError(f"unexpected sidecar status: {response.status}")

                if not isinstance(payload, dict):
                    raise VoteBackendError("sidecar payload must be an object")
                return payload
        except VoteBackendBusinessError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise VoteBackendError("sidecar request failed") from err

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session
