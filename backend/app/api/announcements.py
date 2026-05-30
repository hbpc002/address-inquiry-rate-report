from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.database import get_db
from app.models.announcement import Announcement
from app.models.operation_log import OperationLog
from app.core.security import get_current_user, require_permission
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/announcements", tags=["更新日志管理"])



class AnnouncementCreate(BaseModel):
    type: str = "更新日志"
    title: str
    content: str
    is_active: bool = True


class AnnouncementUpdate(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
def list_announcements(
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Announcement)
    if type:
        query = query.filter(Announcement.type == type)

    total = query.count()
    items = (
        query.order_by(Announcement.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "items": [
            {
                "id": a.id,
                "type": a.type,
                "title": a.title,
                "content": a.content,
                "is_active": a.is_active,
                "created_by": a.created_by,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in items
        ],
        "total": total,
    }


@router.get("/changelog")
def get_changelog(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    items = (
        db.query(Announcement)
        .filter(Announcement.type == "更新日志")
        .order_by(Announcement.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in items
    ]


@router.post("")
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.announcements")
    announcement = Announcement(
        type=data.type,
        title=data.title,
        content=data.content,
        is_active=data.is_active,
        created_by=current_user["id"],
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    log_operation(
        db,
        current_user["id"],
        "create_announcement",
        "announcements",
        announcement.id,
        {"type": data.type, "title": data.title},
    )
    return {
        "id": announcement.id,
        "type": announcement.type,
        "title": announcement.title,
        "content": announcement.content,
        "is_active": announcement.is_active,
        "created_at": announcement.created_at.isoformat() if announcement.created_at else None,
    }


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.announcements")
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    if data.type is not None:
        announcement.type = data.type
    if data.title is not None:
        announcement.title = data.title
    if data.content is not None:
        announcement.content = data.content
    if data.is_active is not None:
        announcement.is_active = data.is_active

    db.commit()
    db.refresh(announcement)
    log_operation(
        db,
        current_user["id"],
        "update_announcement",
        "announcements",
        announcement.id,
        {"type": announcement.type, "title": announcement.title},
    )
    return {
        "id": announcement.id,
        "type": announcement.type,
        "title": announcement.title,
        "content": announcement.content,
        "is_active": announcement.is_active,
        "created_at": announcement.created_at.isoformat() if announcement.created_at else None,
        "updated_at": announcement.updated_at.isoformat() if announcement.updated_at else None,
    }


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.announcements")
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    db.delete(announcement)
    db.commit()
    log_operation(
        db,
        current_user["id"],
        "delete_announcement",
        "announcements",
        announcement_id,
        {},
    )
    return {"message": "已删除"}