from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field, field_validator

import config
from database.models import Report, User

T = TypeVar("T")


# ─── Chiqish ────────────────────────────────────────────────────────────────

class DistrictOut(BaseModel):
    id: int
    name_uz: str
    name_ru: str


class UserBrief(BaseModel):
    id: int
    full_name: str
    position: str


class UserOut(UserBrief):
    role: str
    language: str
    is_active: bool
    # Hodim botga kirib, yozuvini o'z hisobiga bog'laganmi
    is_linked: bool
    created_at: datetime
    districts: list[DistrictOut]


class LocationOut(BaseModel):
    lat: float
    lon: float


class ReportOut(BaseModel):
    id: int
    author: UserBrief
    report_type: str
    district: DistrictOut
    customer_name: str
    location: LocationOut
    plots_count: int | None
    partners: list[UserBrief]
    photo_file_ids: list[str]
    status: Literal["pending", "confirmed", "rejected"]
    created_at: datetime


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    pages: int


class PhotoOut(BaseModel):
    file_id: str


class OkOut(BaseModel):
    ok: bool = True


# ─── Kirish ─────────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    report_type: Literal["laboratory", "visual", "instrumental"]
    district_id: int
    customer_name: str = Field(min_length=1, max_length=500)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    plots_count: int | None = Field(default=None, ge=0)
    partner_ids: list[int] = Field(default_factory=list)
    photo_file_ids: list[str]

    @field_validator("photo_file_ids")
    @classmethod
    def _check_photos(cls, value: list[str]) -> list[str]:
        if not config.MIN_REPORT_PHOTOS <= len(value) <= config.MAX_REPORT_PHOTOS:
            raise ValueError(
                f"rasmlar soni {config.MIN_REPORT_PHOTOS} dan "
                f"{config.MAX_REPORT_PHOTOS} tagacha bo'lishi kerak"
            )
        return value

    @field_validator("partner_ids")
    @classmethod
    def _unique_partners(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    position: str = Field(min_length=1, max_length=255)
    district_ids: list[int] = Field(min_length=1)


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    position: str | None = Field(default=None, min_length=1, max_length=255)
    district_ids: list[int] | None = Field(default=None, min_length=1)


class RoleUpdate(BaseModel):
    role: Literal["admin", "employee"]


class LanguageUpdate(BaseModel):
    language: Literal["uz", "ru"]


class DistrictsUpdate(BaseModel):
    district_ids: list[int] = Field(min_length=1)


# ─── ORM -> sxema ───────────────────────────────────────────────────────────

def district_out(district) -> DistrictOut:
    return DistrictOut(id=district.id, name_uz=district.name_uz, name_ru=district.name_ru)


def user_brief(user: User) -> UserBrief:
    return UserBrief(id=user.id, full_name=user.full_name, position=user.position)


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        position=user.position,
        role=user.role.value,
        language=user.language,
        is_active=user.is_active,
        is_linked=user.telegram_id is not None,
        created_at=user.created_at,
        districts=[district_out(ud.district) for ud in user.user_districts],
    )


def report_status(report: Report) -> Literal["pending", "confirmed", "rejected"]:
    if report.is_confirmed:
        return "confirmed"
    if report.is_rejected:
        return "rejected"
    return "pending"


def report_out(report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        author=user_brief(report.user),
        report_type=report.report_type.value,
        district=district_out(report.district),
        customer_name=report.customer_name,
        location=LocationOut(lat=report.location_lat, lon=report.location_lon),
        plots_count=report.plots_count,
        partners=[user_brief(rp.partner) for rp in report.partners],
        photo_file_ids=[p.file_id for p in report.photos],
        status=report_status(report),
        created_at=report.created_at,
    )
