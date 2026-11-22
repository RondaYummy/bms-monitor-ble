"""Energy economics API: tariffs, daily/monthly savings report and CSV export."""
import asyncio
import csv
import io
import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from python import energy
from python.auth.verify_token import require_admin

router = APIRouter(prefix="/energy", tags=["Energy economics"])

HOUR_RE = re.compile(r"^([01]\d|2[0-3]):00$")
MAX_RANGE_DAYS = 400


class Tariffs(BaseModel):
    currency: str = Field("грн", min_length=1, max_length=8)
    day_price: float = Field(..., ge=0, le=1000)
    two_zone: bool = False
    night_price: float = Field(..., ge=0, le=1000)
    night_start: str = "23:00"
    night_end: str = "07:00"
    export_price: float = Field(0.0, ge=0, le=1000)

    @field_validator("night_start", "night_end")
    @classmethod
    def whole_hours(cls, value: str) -> str:
        if not HOUR_RE.match(value):
            raise ValueError("Use whole hours, e.g. 23:00")
        return value


def _range(from_date: Optional[str], to_date: Optional[str]) -> tuple[date, date]:
    today = date.today()
    try:
        start = date.fromisoformat(from_date) if from_date else today.replace(day=1)
        end = date.fromisoformat(to_date) if to_date else today
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must be YYYY-MM-DD")
    if end < start or (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(status_code=400, detail=f"Invalid range (max {MAX_RANGE_DAYS} days)")
    return start, end


@router.get("/tariffs")
def read_tariffs():
    return energy.get_tariffs()


@router.put("/tariffs", dependencies=[Depends(require_admin)])
def update_tariffs(body: Tariffs):
    return energy.save_tariffs(body.model_dump())


@router.get("/summary")
async def energy_summary(from_date: Optional[str] = Query(None, alias="from"), to_date: Optional[str] = Query(None, alias="to")):
    start, end = _range(from_date, to_date)
    return await asyncio.to_thread(energy.summary, start, end)


@router.get("/months")
async def energy_months():
    return await asyncio.to_thread(energy.months_overview)


CSV_COLUMNS = [
    ("date", "Дата"), ("pv", "Генерація, кВт·год"), ("load", "Споживання, кВт·год"),
    ("grid_in", "З мережі, кВт·год"), ("grid_in_day", "З мережі (день)"), ("grid_in_night", "З мережі (ніч)"),
    ("grid_out", "В мережу, кВт·год"), ("bat_charge", "Заряд батареї"), ("bat_discharge", "Розряд батареї"),
    ("cost", "Вартість"), ("cost_without_system", "Вартість без системи"), ("export_income", "Дохід від продажу"),
    ("savings", "Економія"), ("self_sufficiency", "Автономність, %"),
]


@router.get("/export.csv")
async def export_csv(from_date: Optional[str] = Query(None, alias="from"), to_date: Optional[str] = Query(None, alias="to")):
    start, end = _range(from_date, to_date)
    report = await asyncio.to_thread(energy.summary, start, end)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([title for _, title in CSV_COLUMNS])

    def cells(row: dict) -> list:
        values = []
        for key, _ in CSV_COLUMNS:
            value = row.get(key)
            if key == "self_sufficiency" and value is not None:
                value = round(value * 100, 1)
            values.append("" if value is None else value)
        return values

    for row in report["days"]:
        writer.writerow(cells(row))
    writer.writerow(cells({**report["totals"], "date": "Разом"}))
    filename = f"energy-{start.isoformat()}_{end.isoformat()}.csv"
    # BOM: Excel otherwise opens UTF-8 (Cyrillic headers) as mojibake.
    return Response(
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
