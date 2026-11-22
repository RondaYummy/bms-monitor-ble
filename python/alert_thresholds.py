"""Configurable alert thresholds with chemistry presets (stored as JSON in configs.alert_thresholds)."""
import json
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

import python.db as db
from python.auth.verify_token import require_admin

router = APIRouter(prefix="/alert-thresholds", tags=["Alerts"])

# Per-cell voltages and cycle life by chemistry. Pack voltages = per-cell value x cell count.
CHEMISTRY_PRESETS = {
    "LiFePO4": {"cell_low_critical": 2.90, "cell_low_error": 3.05, "cell_high_error": 3.55, "cell_high_critical": 3.65,
                "cycles_warning": 3000, "cycles_high": 4000},
    "Li-ion": {"cell_low_critical": 3.00, "cell_low_error": 3.30, "cell_high_error": 4.15, "cell_high_critical": 4.25,
               "cycles_warning": 500, "cycles_high": 800},
    "LTO": {"cell_low_critical": 1.90, "cell_low_error": 2.10, "cell_high_error": 2.70, "cell_high_critical": 2.80,
            "cycles_warning": 10000, "cycles_high": 15000},
}

COMMON_DEFAULTS = {
    "soc_critical": 10, "soc_error": 20, "soc_warning_no_charge": 30,
    "cell_diff_error": 0.05, "cell_diff_critical": 0.10,
    "temp_error": 50, "temp_critical": 60,
    "charge_current_error": 80, "charge_current_critical": 100,
    "discharge_current_error": 80, "discharge_current_critical": 100,
    "soh_error": 90, "soh_critical": 80,
    "resistance_error": 0.3, "resistance_critical": 0.5,
    "emergency_error_min": 10, "emergency_critical_min": 5,
}


def build_preset(chemistry: str, cell_count: int = 16) -> dict:
    cell = CHEMISTRY_PRESETS[chemistry]
    return {
        "chemistry": chemistry,
        "cell_count": cell_count,
        **COMMON_DEFAULTS,
        "avg_cell_low_critical": cell["cell_low_critical"],
        "avg_cell_low_error": cell["cell_low_error"],
        "avg_cell_high_error": cell["cell_high_error"],
        "avg_cell_high_critical": cell["cell_high_critical"],
        "pack_low_critical": round(cell["cell_low_critical"] * cell_count, 1),
        "pack_low_error": round(cell["cell_low_error"] * cell_count, 1),
        "pack_high_error": round(cell["cell_high_error"] * cell_count, 1),
        "pack_high_critical": round(cell["cell_high_critical"] * cell_count, 1),
        "cycles_warning": cell["cycles_warning"],
        "cycles_high": cell["cycles_high"],
        "disabled_codes": [],
    }


DEFAULT_THRESHOLDS = build_preset("LiFePO4", 16)


class AlertThresholds(BaseModel):
    chemistry: Literal["LiFePO4", "Li-ion", "LTO", "custom"] = "LiFePO4"
    cell_count: int = Field(16, ge=1, le=32)

    soc_critical: float = Field(..., ge=0, le=100)
    soc_error: float = Field(..., ge=0, le=100)
    soc_warning_no_charge: float = Field(..., ge=0, le=100)
    cell_diff_error: float = Field(..., gt=0, le=1)
    cell_diff_critical: float = Field(..., gt=0, le=1)
    avg_cell_low_critical: float = Field(..., gt=0, le=5)
    avg_cell_low_error: float = Field(..., gt=0, le=5)
    avg_cell_high_error: float = Field(..., gt=0, le=5)
    avg_cell_high_critical: float = Field(..., gt=0, le=5)
    pack_low_critical: float = Field(..., gt=0, le=200)
    pack_low_error: float = Field(..., gt=0, le=200)
    pack_high_error: float = Field(..., gt=0, le=200)
    pack_high_critical: float = Field(..., gt=0, le=200)
    temp_error: float = Field(..., ge=-40, le=120)
    temp_critical: float = Field(..., ge=-40, le=120)
    charge_current_error: float = Field(..., gt=0, le=1000)
    charge_current_critical: float = Field(..., gt=0, le=1000)
    discharge_current_error: float = Field(..., gt=0, le=1000)
    discharge_current_critical: float = Field(..., gt=0, le=1000)
    soh_error: float = Field(..., ge=0, le=100)
    soh_critical: float = Field(..., ge=0, le=100)
    resistance_error: float = Field(..., gt=0, le=10)
    resistance_critical: float = Field(..., gt=0, le=10)
    emergency_error_min: float = Field(..., gt=0, le=1000)
    emergency_critical_min: float = Field(..., gt=0, le=1000)
    cycles_warning: int = Field(..., gt=0, le=100000)
    cycles_high: int = Field(..., gt=0, le=100000)
    disabled_codes: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_order(self):
        checks = [
            (self.soc_critical < self.soc_error <= self.soc_warning_no_charge, "SOC: critical < error <= warning"),
            (self.cell_diff_error < self.cell_diff_critical, "Cell difference: error < critical"),
            (self.avg_cell_low_critical < self.avg_cell_low_error < self.avg_cell_high_error < self.avg_cell_high_critical,
             "Average cell voltage: low critical < low error < high error < high critical"),
            (self.pack_low_critical < self.pack_low_error < self.pack_high_error < self.pack_high_critical,
             "Pack voltage: low critical < low error < high error < high critical"),
            (self.temp_error < self.temp_critical, "Temperature: error < critical"),
            (self.charge_current_error < self.charge_current_critical, "Charge current: error < critical"),
            (self.discharge_current_error < self.discharge_current_critical, "Discharge current: error < critical"),
            (self.soh_critical < self.soh_error, "SOH: critical < error"),
            (self.resistance_error < self.resistance_critical, "Resistance: error < critical"),
            (self.emergency_critical_min < self.emergency_error_min, "Emergency countdown: critical < error"),
            (self.cycles_warning < self.cycles_high, "Cycles: warning < high"),
        ]
        errors = [message for ok, message in checks if not ok]
        if errors:
            raise ValueError("; ".join(errors))
        return self


_cache: dict = {"raw": None, "value": None}


def get_thresholds() -> dict:
    raw = (db.get_config() or {}).get("alert_thresholds")
    if raw == _cache["raw"] and _cache["value"] is not None:
        return _cache["value"]
    value = dict(DEFAULT_THRESHOLDS)
    if raw:
        try:
            # Missing keys (e.g. added in a later version) fall back to defaults.
            value.update(json.loads(raw))
        except (ValueError, TypeError):
            print("⚠️ Invalid alert_thresholds JSON in config, using defaults.")
    _cache.update(raw=raw, value=value)
    return value


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def render_message(template: str, thresholds: Optional[dict] = None) -> str:
    """Error-code messages contain placeholders like {soc_critical}; unknown ones stay as is."""
    values = {k: _fmt(v) for k, v in (thresholds or get_thresholds()).items() if not isinstance(v, list)}

    class _Safe(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    try:
        return template.format_map(_Safe(values))
    except (ValueError, IndexError):
        return template


@router.get("")
def read_thresholds():
    return get_thresholds()


@router.get("/presets")
def read_presets(cell_count: int = 16):
    cell_count = max(1, min(32, cell_count))
    return {name: build_preset(name, cell_count) for name in CHEMISTRY_PRESETS}


@router.put("", dependencies=[Depends(require_admin)])
def save_thresholds(body: AlertThresholds):
    data = body.model_dump()
    config = db.update_config_fields(alert_thresholds=json.dumps(data))
    if not config:
        raise HTTPException(status_code=500, detail="Failed to save thresholds")
    return get_thresholds()
