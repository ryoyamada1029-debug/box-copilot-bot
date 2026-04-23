from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import uvicorn

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="User Management API", version="1.0.0")

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(String(50), nullable=False, default="user")  # "admin" or "user"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # 論理削除用
    is_deleted = Column(Boolean, default=False)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "user"
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('氏名は必須です')
        if len(v) > 100:
            raise ValueError('氏名は100文字以内で入力してください')
        return v.strip()
    
    @validator('role')
    def role_must_be_valid(cls, v):
        if v not in ['admin', 'user']:
            raise ValueError('権限は admin または user を指定してください')
        return v

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('氏名は必須です')
            if len(v) > 100:
                raise ValueError('氏名は100文字以内で入力してください')
            return v.strip()
        return v
    
    @validator('role')
    def role_must_be_valid(cls, v):
        if v is not None and v not in ['admin', 'user']:
            raise ValueError('権限は admin または user を指定してください')
        return v

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Endpoints
@app.get("/users", response_model=List[UserResponse], summary="ユーザー一覧取得")
async def get_users(db: Session = Depends(get_db)):
    """
    登録済みユーザーを全件取得します。
    論理削除されたユーザーは除外されます。
    """
    try:
        users = db.query(User).filter(User.is_deleted == False).all()
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー一覧の取得に失敗しました"
        )

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="ユーザー新規作成")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    新しいユーザーをシステムに登録します。
    IDはシステム側で自動採番されます。
    """
    try:
        # メールアドレスの重複チェック
        existing_user = db.query(User).filter(
            User.email == user.email,
            User.is_deleted == False
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このメールアドレスは既に登録されています"
            )
        
        # 新規ユーザー作成
        db_user = User(
            name=user.name,
            email=user.email,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザーの作成に失敗しました"
        )

@app.put("/users/{user_id}", response_model=UserResponse, summary="ユーザー情報更新")
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """
    指定したIDのユーザー情報を更新します。
    """
    try:
        # ユーザー存在チェック
        db_user = db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたユーザーが見つかりません"
            )
        
        # メールアドレス重複チェック（更新時）
        if user_update.email:
            existing_user = db.query(User).filter(
                User.email == user_update.email,
                User.id != user_id,
                User.is_deleted == False
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="このメールアドレスは既に登録されています"
                )
        
        # 更新処理
        update_data = user_update.dict(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(db_user, field, value)
            db_user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_user)
        
        return db_user
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー情報の更新に失敗しました"
        )

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="ユーザー削除")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    指定したIDのユーザーを論理削除します。
    """
    try:
        # ユーザー存在チェック
        db_user = db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたユーザーが見つかりません"
            )
        
        # 論理削除実行
        db_user.is_deleted = True
        db_user.deleted_at = datetime.utcnow()
        db_user.updated_at = datetime.utcnow()
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザーの削除に失敗しました"
        )

# Health Check
@app.get("/health", summary="ヘルスチェック")
async def health_check():
    """
    APIの稼働状況を確認します。
    """
    return {"status": "ok", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile=None, ssl_certfile=None)