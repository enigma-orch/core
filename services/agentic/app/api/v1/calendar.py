"""GET /api/v1/calendar/today — upcoming events + derived occasion tag."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.user import User
from app.services import google_calendar as gcal_svc
from app.services.jwt import get_current_user_id_verified
from app.services.shuffle import occasion_from_event_title

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CalendarEventOut(BaseModel):
    title: str
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    location: Optional[str] = None
    mapped_occasion: Optional[str] = None


class CalendarTodayOut(BaseModel):
    linked: bool
    fetched_at: str
    events: List[CalendarEventOut]
    suggested_occasion: Optional[str] = None


def _event_time(ev: dict, side: str) -> str | None:
    s = ev.get(side) or {}
    return s.get("dateTime") or s.get("date")


@router.get("/today", response_model=CalendarTodayOut)
async def calendar_today(
    lookahead_days: int = Query(1, ge=1, le=7),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> CalendarTodayOut:
    user = await db.get(User, uuid.UUID(current_user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.google_access_token:
        return CalendarTodayOut(
            linked=False,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            events=[],
            suggested_occasion=None,
        )

    try:
        raw_events = await gcal_svc.list_upcoming_events(
            user.google_access_token,
            calendar_id=user.google_calendar_id or "primary",
            max_results=10,
        )
    except Exception as exc:
        logger.warning("Calendar fetch failed for user %s: %s", user.id, exc)
        raise HTTPException(status_code=502, detail="Calendar lookup failed")

    events: list[CalendarEventOut] = []
    suggested: str | None = None
    for ev in raw_events:
        title = ev.get("summary") or ""
        mapped = occasion_from_event_title(title)
        events.append(
            CalendarEventOut(
                title=title,
                starts_at=_event_time(ev, "start"),
                ends_at=_event_time(ev, "end"),
                location=ev.get("location"),
                mapped_occasion=mapped,
            )
        )
        if suggested is None and mapped:
            suggested = mapped

    return CalendarTodayOut(
        linked=True,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        events=events,
        suggested_occasion=suggested,
    )
