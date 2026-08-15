from fastapi import APIRouter, HTTPException, status

from api.deps import CurrentUser, SessionDep
from api.schemas import (
    DistrictOut,
    DistrictsUpdate,
    LanguageUpdate,
    UserOut,
    district_out,
    user_out,
)
from database.crud import (
    get_all_districts,
    get_districts_by_ids,
    get_user_by_id,
    set_user_districts,
    update_user,
)

router = APIRouter(tags=["me"])


async def ensure_districts_exist(session, district_ids: list[int]) -> None:
    """Mavjud bo'lmagan tuman id si tashqi kalit xatosiga olib kelmasin."""
    found = await get_districts_by_ids(session, district_ids)
    if len(found) != len(set(district_ids)):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "bad_district", "message": "Tuman topilmadi"},
        )


@router.get("/me", response_model=UserOut)
async def read_me(user: CurrentUser) -> UserOut:
    return user_out(user)


@router.patch("/me/language", response_model=UserOut)
async def change_language(
    payload: LanguageUpdate, user: CurrentUser, session: SessionDep
) -> UserOut:
    await update_user(session, user.id, language=payload.language)
    return user_out(await get_user_by_id(session, user.id))


@router.put("/me/districts", response_model=UserOut)
async def change_my_districts(
    payload: DistrictsUpdate, user: CurrentUser, session: SessionDep
) -> UserOut:
    await ensure_districts_exist(session, payload.district_ids)
    await set_user_districts(session, user.id, payload.district_ids)
    return user_out(await get_user_by_id(session, user.id))


@router.get("/districts", response_model=list[DistrictOut])
async def list_districts(user: CurrentUser, session: SessionDep) -> list[DistrictOut]:
    return [district_out(d) for d in await get_all_districts(session)]
