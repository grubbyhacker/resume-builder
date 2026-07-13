from __future__ import annotations

import re
from dataclasses import dataclass


MONTH_NAMES = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
MONTH_DATE_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
YEAR_DATE_RE = re.compile(r"^\d{4}$")
PRESENT = "present"


@dataclass(frozen=True, order=True)
class ResumeDate:
    year: int
    month: int


def parse_resume_date(value: str, *, allow_year: bool = False, allow_present: bool = True) -> ResumeDate:
    if allow_present and value == PRESENT:
        return ResumeDate(9999, 12)
    match = MONTH_DATE_RE.fullmatch(value)
    if match:
        return ResumeDate(int(match.group(1)), int(match.group(2)))
    if allow_year and YEAR_DATE_RE.fullmatch(value):
        return ResumeDate(int(value), 12)
    expected = "YYYY-MM"
    if allow_year:
        expected += " or YYYY"
    if allow_present:
        expected += f" or {PRESENT!r}"
    raise ValueError(f"expected {expected}, got {value!r}")


def format_resume_date(value: str) -> str:
    if value == PRESENT:
        return "Present"
    if YEAR_DATE_RE.fullmatch(value):
        return value
    parsed = parse_resume_date(value, allow_present=False)
    return f"{MONTH_NAMES[parsed.month - 1]} {parsed.year}"
