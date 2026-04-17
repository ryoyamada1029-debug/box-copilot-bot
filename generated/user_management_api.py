from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
import uvicorn

app = FastAPI(title="User Management API", version="1.0.0")

# データモデル
class UserCreate(BaseModel):
    name: str
    email: EmailStr

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

# メモリ内データストレージ
users_db: Dict[int, dict] = {}
next_user_id = 1

@app.get("/users", response_model=List[UserResponse])
async def get_users():
    """ユーザー一覧取得"""
    return [UserResponse(id=user_id, **user_data) 
            for user_id, user_data in users_db.items()]

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """ユーザー新規作成"""
    global next_user_id
    
    # メールアドレスの重複チェック
    for existing_user in users_db.values():
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = next_user_id
    user_data = user.dict()
    users_db[user_id] = user_data
    next_user_id += 1
    
    return UserResponse(id=user_id, **user_data)

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate):
    """ユーザー情報更新"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # メールアドレスの重複チェック（自分以外）
    if user.email:
        for existing_id, existing_user in users_db.items():
            if existing_id != user_id and existing_user["email"] == user.email:
                raise HTTPException(status_code=400, detail="Email already registered")
    
    # 既存データの更新
    existing_user = users_db[user_id]
    update_data = user.dict(exclude_unset=True)
    for field, value in update_data.items():
        existing_user[field] = value
    
    return UserResponse(id=user_id, **existing_user)

@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    """ユーザー削除"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    del users_db[user_id]
    return None

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)