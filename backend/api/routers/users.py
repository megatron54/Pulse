from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas import UserCreateRequest, UserOut
from models.schema import UserProfile

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(verify_api_key)])


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserProfile:
    usuario = UserProfile(**payload.model_dump())
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserProfile:
    usuario = db.get(UserProfile, user_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail=f"No existe usuario con id={user_id}")
    return usuario
