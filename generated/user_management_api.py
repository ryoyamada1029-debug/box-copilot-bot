from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime

app = FastAPI(title="User Management API", version="1.0.0")

# Pydanticモデル定義
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = None

class User(BaseModel):
    id: str
    name: str
    email: str
    age: Optional[int] = None
    created_at: datetime
    updated_at: datetime

# メモリ上のデータストレージ（実用時はデータベースに置き換え）
users_db: Dict[str, User] = {}

@app.get("/users", response_model=List[User])
async def get_users():
    """ユーザー一覧取得"""
    return list(users_db.values())

@app.post("/users", response_model=User, status_code=201)
async def create_user(user_data: UserCreate):
    """ユーザー新規作成"""
    # メールアドレスの重複チェック
    for existing_user in users_db.values():
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    # 新規ユーザー作成
    user_id = str(uuid.uuid4())
    now = datetime.now()
    
    new_user = User(
        id=user_id,
        name=user_data.name,
        email=user_data.email,
        age=user_data.age,
        created_at=now,
        updated_at=now
    )
    
    users_db[user_id] = new_user
    return new_user

@app.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str = Path(..., description="User ID"),
    user_data: UserUpdate = None
):
    """ユーザー情報更新"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    user = users_db[user_id]
    
    # メールアドレス重複チェック（変更時のみ）
    if user_data.email and user_data.email != user.email:
        for existing_user in users_db.values():
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered"
                )
    
    # 更新処理
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.now()
    users_db[user_id] = user
    
    return user

@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str = Path(..., description="User ID")):
    """ユーザー削除"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    del users_db[user_id]
    return None

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str = Path(..., description="User ID")):
    """特定ユーザー取得（追加エンドポイント）"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return users_db[user_id]

# ヘルスチェック用エンドポイント
@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)