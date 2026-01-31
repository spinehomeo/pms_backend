from typing import Any
from datetime import date

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select

from api.deps import SessionDep, get_current_active_superuser
from core.security import get_password_hash
from models.users_model import User, UserPublic
from models.private_model import PrivateUserCreate, PrivateUserUpdate

router = APIRouter(tags=["🔐 Private"], prefix="/private")


@router.post("/users/", response_model=UserPublic)
def create_user(
    user_in: PrivateUserCreate, 
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    Create a new user (admin/internal use).
    """
    # Check if user already exists
    existing_user = session.exec(
        select(User).where(User.email == user_in.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        phone=user_in.phone,
        specialization=user_in.specialization,
        registration_number=user_in.registration_number,
        is_verified=user_in.is_verified,
        is_superuser=user_in.is_superuser,
        join_date=user_in.join_date,
        is_active=True
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user


@router.put("/users/{user_id}", response_model=UserPublic)
def update_user(
    user_id: str,
    user_in: PrivateUserUpdate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    Update a user (admin/internal use).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Check if email is being changed and if it already exists
    if user_in.email and user_in.email != user.email:
        existing_user = session.exec(
            select(User).where(User.email == user_in.email)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system.",
            )
    
    # Update fields
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Handle password update
    if 'password' in update_data and update_data['password']:
        update_data['hashed_password'] = get_password_hash(update_data.pop('password'))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    Delete a user (admin/internal use).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    session.delete(user)
    session.commit()
    
    return {"message": "User deleted successfully"}