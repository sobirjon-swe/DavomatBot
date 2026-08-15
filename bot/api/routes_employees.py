import logging

from fastapi import APIRouter, HTTPException, Query, status

from api.deps import AdminUser, SessionDep, SuperAdminUser
from api.routes_me import ensure_districts_exist
from api.schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    Page,
    RoleUpdate,
    UserOut,
    user_out,
)
from database.crud import (
    count_users,
    create_user,
    get_all_users,
    get_user_by_id,
    set_user_active,
    set_user_districts,
    update_user,
)
from database.models import UserRole
from keyboards.pagination import PER_PAGE, page_count

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employees", tags=["employees"])


async def _get_or_404(session, user_id: int):
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Hodim topilmadi"},
        )
    return user


@router.get("", response_model=Page[UserOut])
async def list_employees(
    admin: AdminUser,
    session: SessionDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(PER_PAGE, ge=1, le=100),
    only_active: bool = False,
) -> Page[UserOut]:
    total = await count_users(session, only_active=only_active)
    users = await get_all_users(
        session, only_active=only_active, offset=(page - 1) * per_page, limit=per_page
    )
    return Page(
        items=[user_out(u) for u in users],
        total=total,
        page=page,
        pages=page_count(total, per_page=per_page),
    )


@router.get("/{user_id}", response_model=UserOut)
async def read_employee(user_id: int, admin: AdminUser, session: SessionDep) -> UserOut:
    return user_out(await _get_or_404(session, user_id))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate, admin: AdminUser, session: SessionDep
) -> UserOut:
    """Hodimni oldindan kiritish.

    `telegram_id` bo'sh qoladi — hodim botga birinchi kirganda o'z yozuvini
    tanlab, hisobiga bog'laydi.
    """
    await ensure_districts_exist(session, payload.district_ids)

    user = await create_user(
        session,
        full_name=payload.full_name,
        position=payload.position,
        language="uz",
    )
    await set_user_districts(session, user.id, payload.district_ids)

    logger.info("API orqali hodim qo'shildi: id=%s (admin id=%s)", user.id, admin.id)
    return user_out(await get_user_by_id(session, user.id))


@router.patch("/{user_id}", response_model=UserOut)
async def edit_employee(
    user_id: int, payload: EmployeeUpdate, admin: AdminUser, session: SessionDep
) -> UserOut:
    await _get_or_404(session, user_id)

    fields = payload.model_dump(exclude_unset=True, exclude_none=True)
    district_ids = fields.pop("district_ids", None)

    if fields:
        await update_user(session, user_id, **fields)
    if district_ids is not None:
        await ensure_districts_exist(session, district_ids)
        await set_user_districts(session, user_id, district_ids)

    return user_out(await get_user_by_id(session, user_id))


@router.post("/{user_id}/deactivate", response_model=UserOut)
async def deactivate_employee(
    user_id: int, admin: SuperAdminUser, session: SessionDep
) -> UserOut:
    """Hodimni faolsizlantiradi.

    O'chirish emas: `users` ni o'chirish `reports` ni ham kaskad
    o'chirib yuborardi va davomat tarixi yo'qolardi.
    """
    if user_id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "self_deactivate",
                "message": "O'zingizni faolsizlantira olmaysiz",
            },
        )

    await _get_or_404(session, user_id)
    await set_user_active(session, user_id, False)
    logger.info("Hodim id=%s faolsizlantirildi (admin id=%s)", user_id, admin.id)
    return user_out(await get_user_by_id(session, user_id))


@router.post("/{user_id}/activate", response_model=UserOut)
async def activate_employee(
    user_id: int, admin: SuperAdminUser, session: SessionDep
) -> UserOut:
    await _get_or_404(session, user_id)
    await set_user_active(session, user_id, True)
    logger.info("Hodim id=%s tiklandi (admin id=%s)", user_id, admin.id)
    return user_out(await get_user_by_id(session, user_id))


@router.patch("/{user_id}/role", response_model=UserOut)
async def change_role(
    user_id: int, payload: RoleUpdate, admin: SuperAdminUser, session: SessionDep
) -> UserOut:
    target = await _get_or_404(session, user_id)

    if target.role == UserRole.superadmin:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "superadmin_locked",
                "message": "Superadmin roli o'zgartirilmaydi",
            },
        )

    new_role = UserRole.admin if payload.role == "admin" else UserRole.employee
    await update_user(session, user_id, role=new_role)
    logger.info(
        "Hodim id=%s roli %s ga o'zgardi (admin id=%s)", user_id, new_role.value, admin.id
    )
    return user_out(await get_user_by_id(session, user_id))
