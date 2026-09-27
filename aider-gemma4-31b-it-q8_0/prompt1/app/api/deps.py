from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import decode_token
from app.core.config import settings
from app.models.models import User, UserRole
from app.schemas.schemas import UserOut

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Mock DB session dependency
def get_db():
    # In a real app, this would yield a session from a sessionmaker
    # For initialization, we assume a session is provided or mocked
    yield None 

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing or invalid"
        )
    
    user_id = payload.get("sub")
    # In real implementation: user = db.query(User).filter(User.id == user_id).first()
    # Mocking user for structure
    user = User(id=int(user_id), role=UserRole.CUSTOMER) 
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action"
            )
        return user
