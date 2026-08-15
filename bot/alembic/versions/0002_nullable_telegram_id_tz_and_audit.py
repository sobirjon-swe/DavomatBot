"""telegram_id nullable, vaqt mintaqali ustunlar, rad etish izi, urinishlar jadvali

Nima o'zgaradi:
  * users.telegram_id -> NULL bo'lishi mumkin. Admin qo'lda qo'shgan hodim
    hali botga kirmagan bo'ladi; ilgari u 0 qiymat bilan yozilar va ikkinchi
    hodimda unique cheklov buzilardi.
  * Barcha vaqt ustunlari TIMESTAMP -> TIMESTAMPTZ. Mavjud qiymatlar UTC deb
    talqin qilinadi (kod ularni `datetime.utcnow()` bilan yozgan).
  * reports ga rad etish izi qo'shiladi — hisobot endi o'chirilmaydi.
  * confirmed_by / created_by tashqi kalitlari ON DELETE SET NULL bo'ladi.
  * access_attempts jadvali: parolni xato kiritish urinishlari bazada
    saqlanadi, ilgari xotirada edi va restartda yo'qolardi.

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (jadval, ustun, nullable)
_TIMESTAMP_COLUMNS = [
    ("users", "created_at", False),
    ("reports", "created_at", False),
    ("reports", "confirmed_at", True),
    ("access_passwords", "created_at", False),
]


def upgrade() -> None:
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=True)

    for table, column, nullable in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    op.add_column(
        "reports",
        sa.Column(
            "is_rejected", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("reports", sa.Column("rejected_by", sa.Integer(), nullable=True))
    op.add_column(
        "reports",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "reports_rejected_by_fkey",
        "reports",
        "users",
        ["rejected_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Hodim o'chirilganda tasdiqlagan/parol yaratgan havolasi NULL bo'lsin,
    # aks holda o'chirish tashqi kalit xatosi bilan tugaydi.
    op.drop_constraint("reports_confirmed_by_fkey", "reports", type_="foreignkey")
    op.create_foreign_key(
        "reports_confirmed_by_fkey",
        "reports",
        "users",
        ["confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "access_passwords_created_by_fkey", "access_passwords", type_="foreignkey"
    )
    op.create_foreign_key(
        "access_passwords_created_by_fkey",
        "access_passwords",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "access_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_access_attempts_telegram_id"),
        "access_attempts",
        ["telegram_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_access_attempts_telegram_id"), table_name="access_attempts"
    )
    op.drop_table("access_attempts")

    op.drop_constraint(
        "access_passwords_created_by_fkey", "access_passwords", type_="foreignkey"
    )
    op.create_foreign_key(
        "access_passwords_created_by_fkey",
        "access_passwords",
        "users",
        ["created_by"],
        ["id"],
    )
    op.drop_constraint("reports_confirmed_by_fkey", "reports", type_="foreignkey")
    op.create_foreign_key(
        "reports_confirmed_by_fkey", "reports", "users", ["confirmed_by"], ["id"]
    )

    op.drop_constraint("reports_rejected_by_fkey", "reports", type_="foreignkey")
    op.drop_column("reports", "rejected_at")
    op.drop_column("reports", "rejected_by")
    op.drop_column("reports", "is_rejected")

    for table, column, nullable in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    op.execute("DELETE FROM users WHERE telegram_id IS NULL")
    op.alter_column(
        "users", "telegram_id", existing_type=sa.BigInteger(), nullable=False
    )
