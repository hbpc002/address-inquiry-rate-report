import zipfile
import io
import re
from xml.etree import ElementTree as ET
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

from app.models.database import get_db
from app.models.training_record import TrainingRecord
from app.models.employee import Employee
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api/training-records", tags=["培训记录"])


class TrainingRecordItem(BaseModel):
    emp_no: str
    record_date: str
    start_time: str
    end_time: str
    type: str = "培训"
    reason: Optional[str] = None


class BatchCreateRequest(BaseModel):
    records: list[TrainingRecordItem]


class TrainingRecordResponse(BaseModel):
    id: int
    emp_no: str
    record_date: str
    start_time: str
    end_time: str
    duration_minutes: int
    type: str
    reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


def _duration_minutes(start: str, end: str) -> int:
    sh, sm = map(int, start.split(':'))
    eh, em = map(int, end.split(':'))
    return max(0, (eh * 60 + em) - (sh * 60 + sm))


@router.get("")
def list_training_records(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    emp_no: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "training_records.view")
    query = db.query(TrainingRecord)
    if start_date:
        query = query.filter(TrainingRecord.record_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(TrainingRecord.record_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    if emp_no:
        query = query.filter(TrainingRecord.emp_no == emp_no)
    if type:
        query = query.filter(TrainingRecord.type == type)
    records = query.order_by(TrainingRecord.record_date.desc(), TrainingRecord.emp_no).all()
    total_minutes = sum(r.duration_minutes for r in records)
    return {
        "total": len(records),
        "total_minutes": total_minutes,
        "items": [
            {
                "id": r.id,
                "emp_no": r.emp_no,
                "record_date": r.record_date.isoformat() if r.record_date else None,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "duration_minutes": r.duration_minutes,
                "type": r.type,
                "reason": r.reason,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


@router.post("/batch")
def batch_create(
    data: BatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "training_records.create")
    created = []
    for item in data.records:
        d = datetime.strptime(item.record_date, "%Y-%m-%d").date()
        minutes = _duration_minutes(item.start_time, item.end_time)
        record = TrainingRecord(
            emp_no=item.emp_no,
            record_date=d,
            start_time=item.start_time,
            end_time=item.end_time,
            duration_minutes=minutes,
            type=item.type,
            reason=item.reason,
            created_by=current_user.get("display_name") or current_user.get("username"),
        )
        db.add(record)
        created.append(record)
    db.commit()
    return {
        "message": f"成功创建 {len(created)} 条记录",
        "count": len(created)
    }


@router.delete("/{record_id}")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "training_records.delete")
    record = db.query(TrainingRecord).filter(TrainingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"message": "删除成功"}


def _parse_training_duration(time_str: str) -> int:
    if not time_str or time_str.strip() in ("", "0"):
        return 0
    s = time_str.replace("：", ":").replace("．", ":").replace("。", ":")
    segments = re.split(r"[\n\r]+|(?<=\d)\s+(?=\d)", s.strip())
    total = 0
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"(\d{1,2})[:.](\d{2})(?::\d{2})?\s*[-—]\s*(\d{1,2})[:.](\d{2})", seg)
        if m:
            sh, sm, eh, em = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            duration = (eh * 60 + em) - (sh * 60 + sm)
            if duration > 0:
                total += duration
    return total


def _date_col_name(col_letter: str) -> str:
    return "".join(c for c in col_letter if c.isalpha())


def _parse_xlsx_cell_text(cell, ns) -> str:
    t = cell.get("t", "")
    v_el = cell.find("s:v", ns)
    v = v_el.text if v_el is not None else ""
    if t == "inlineStr":
        t_el = cell.find(".//s:t", ns)
        return t_el.text if t_el is not None else ""
    return v


MAX_IMPORT_ROWS = 5000


@router.post("/import")
async def import_training_records(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "training_records.create")
    content = await file.read()

    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    sheets = []
    with zipfile.ZipFile(io.BytesIO(content), "r") as z:
        for name in z.namelist():
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue
            sheets.append((name, z.read(name)))

    if not sheets:
        raise HTTPException(status_code=400, detail="文件不包含任何工作表")

    xml_content = sheets[-1][1]
    root = ET.fromstring(xml_content)
    all_rows = root.findall(".//s:row", ns)

    if len(all_rows) < 3:
        raise HTTPException(status_code=400, detail="文件格式无效，至少需要3行")

    header1_cells = all_rows[0].findall("s:c", ns)

    date_cols = {}
    for cell in header1_cells:
        ref = cell.get("r")
        col_letter = _date_col_name(ref)
        value = _parse_xlsx_cell_text(cell, ns).strip()
        if re.match(r"^\d{8}$", value):
            date_cols[col_letter] = value

    if not date_cols:
        raise HTTPException(status_code=400, detail="未能在表头中识别日期列")

    header2_cells = all_rows[1].findall("s:c", ns)
    time_cols = {}
    for cell in header2_cells:
        ref = cell.get("r")
        col_letter = _date_col_name(ref)
        value = _parse_xlsx_cell_text(cell, ns).strip()
        if value == "签出时间段":
            for dcol, dval in date_cols.items():
                if col_letter == dcol:
                    time_cols[dcol] = dval

    if not time_cols:
        raise HTTPException(status_code=400, detail="未能找到时间段列")

    date_col_letters = sorted(time_cols.keys())

    created = []
    errors = []
    row_count = 0

    for row_el in all_rows[3:]:
        row_count += 1
        if row_count > MAX_IMPORT_ROWS:
            errors.append(f"超过最大行数限制 {MAX_IMPORT_ROWS}")
            break

        cells = row_el.findall("s:c", ns)
        cell_map = {}
        for cell in cells:
            ref = cell.get("r")
            col_letter = _date_col_name(ref)
            cell_map[col_letter] = _parse_xlsx_cell_text(cell, ns)

        emp_no = (cell_map.get("A") or "").strip()
        team = (cell_map.get("B") or "").strip()
        name = (cell_map.get("C") or "").strip()

        if not emp_no and not name:
            continue

        if not emp_no:
            existing = db.query(Employee).filter(Employee.name == name).first()
            if existing:
                emp_no = existing.emp_no
            else:
                errors.append(f"第{row_count + 4}行: 找不到员工'{name}'")
                continue

        for dcol in date_col_letters:
            date_str = time_cols[dcol]
            time_value = (cell_map.get(dcol) or "").strip()
            if not time_value or time_value == "0":
                continue

            duration_minutes = _parse_training_duration(time_value)
            if duration_minutes <= 0:
                continue

            try:
                record_date = datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                errors.append(f"第{row_count + 4}行: 无效日期 '{date_str}'")
                continue

            record = TrainingRecord(
                emp_no=emp_no,
                record_date=record_date,
                start_time="",
                end_time="",
                duration_minutes=duration_minutes,
                type="培训",
                reason=file.filename,
                created_by=current_user.get("display_name") or current_user.get("username"),
            )
            db.add(record)
            created.append(record)

    db.commit()

    return {
        "message": f"成功导入 {len(created)} 条培训记录",
        "count": len(created),
        "errors": errors,
    }
