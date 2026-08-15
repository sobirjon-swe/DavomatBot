import enum
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Vaqt mintaqasi belgilangan hozirgi UTC vaqti.

    `datetime.utcnow()` naive qiymat qaytaradi va Python 3.12 dan deprecated;
    bazadagi barcha vaqtlar UTC va tz-aware bo'lishi uchun shu funksiya
    ishlatiladi.
    """
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    employee = "employee"


class ReportType(str, enum.Enum):
    laboratory = "laboratory"
    visual = "visual"
    instrumental = "instrumental"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Admin qo'lda qo'shgan hodim hali botga kirmagan bo'ladi — o'shanda NULL.
    # Shu sababli unique cheklov NULL larni hisobga olmaydi (Postgres xatti-harakati).
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(255))
    position: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.employee)
    language: Mapped[str] = mapped_column(String(2), default="uz")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    user_districts: Mapped[list["UserDistrict"]] = relationship(
        "UserDistrict", back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="user", foreign_keys="Report.user_id"
    )
    confirmed_reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="confirmer", foreign_keys="Report.confirmed_by"
    )
    partner_in: Mapped[list["ReportPartner"]] = relationship(
        "ReportPartner", back_populates="partner"
    )
    created_passwords: Mapped[list["AccessPassword"]] = relationship(
        "AccessPassword", back_populates="creator"
    )


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_uz: Mapped[str] = mapped_column(String(255))
    name_ru: Mapped[str] = mapped_column(String(255))

    user_districts: Mapped[list["UserDistrict"]] = relationship(
        "UserDistrict", back_populates="district"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="district"
    )


class UserDistrict(Base):
    __tablename__ = "user_districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"))

    user: Mapped["User"] = relationship("User", back_populates="user_districts")
    district: Mapped["District"] = relationship("District", back_populates="user_districts")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"))
    customer_name: Mapped[str] = mapped_column(String(500))
    location_lat: Mapped[float] = mapped_column(Float)
    location_lon: Mapped[float] = mapped_column(Float)
    plots_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Rad etilgan hisobot o'chirilmaydi — audit izi qolishi uchun belgilanadi.
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    rejected_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="reports", foreign_keys=[user_id])
    confirmer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="confirmed_reports", foreign_keys=[confirmed_by]
    )
    rejecter: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[rejected_by]
    )
    district: Mapped["District"] = relationship("District", back_populates="reports")
    partners: Mapped[list["ReportPartner"]] = relationship(
        "ReportPartner", back_populates="report", cascade="all, delete-orphan"
    )
    photos: Mapped[list["ReportPhoto"]] = relationship(
        "ReportPhoto", back_populates="report", cascade="all, delete-orphan"
    )


class ReportPartner(Base):
    __tablename__ = "report_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    partner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    report: Mapped["Report"] = relationship("Report", back_populates="partners")
    partner: Mapped["User"] = relationship("User", back_populates="partner_in")


class ReportPhoto(Base):
    __tablename__ = "report_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    file_id: Mapped[str] = mapped_column(String(500))

    report: Mapped["Report"] = relationship("Report", back_populates="photos")


class AccessPassword(Base):
    __tablename__ = "access_passwords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    password_hash: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    creator: Mapped[Optional["User"]] = relationship(
        "User", back_populates="created_passwords"
    )


class AccessAttempt(Base):
    """Parolni xato kiritish urinishlari.

    Ilgari bu ma'lumot xotirada saqlangani uchun bot qayta ishga tushishi
    bilan blok bekor bo'lardi. Endi bazada saqlanadi.
    """

    __tablename__ = "access_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
