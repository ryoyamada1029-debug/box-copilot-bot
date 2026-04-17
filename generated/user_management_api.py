from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

app = FastAPI(title="User Management API", version="1.0.0")

# Pydanticモデル定義
class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="ユーザー名")
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$', description="メールアドレス")
    age: Optional[int] = Field(None, ge=0, le=120, description="年齢")

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    age: Optional[int] = Field(None, ge=0, le=120)

class UserResponse(UserBase):
    id: int = Field(..., description="ユーザーID")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

    class Config:
        from_attributes = True

# インメモリデータストア
users_db: Dict[int, dict] = {}
next_user_id = 1

# ユーザー一覧取得
@app.get("/users", response_model=List[UserResponse], summary="ユーザー一覧取得")
async def get_users():
    """
    登録されている全ユーザーの一覧を取得します。
    """
    return list(users_db.values())

# ユーザー新規作成
@app.post("/users", response_model=UserResponse, status_code=201, summary="ユーザー新規作成")
async def create_user(user: UserCreate):
    """
    新しいユーザーを作成します。
    """
    global next_user_id
    
    # メールアドレスの重複チェック
    for existing_user in users_db.values():
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=400, detail="このメールアドレスは既に使用されています")
    
    now = datetime.now()
    new_user = {
        "id": next_user_id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "created_at": now,
        "updated_at": now
    }
    
    users_db[next_user_id] = new_user
    next_user_id += 1
    
    return new_user

# ユーザー情報更新
@app.put("/users/{user_id}", response_model=UserResponse, summary="ユーザー情報更新")
async def update_user(user_id: int, user: UserUpdate):
    """
    指定されたIDのユーザー情報を更新します。
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # メールアドレスの重複チェック（更新対象以外）
    if user.email:
        for uid, existing_user in users_db.items():
            if uid != user_id and existing_user["email"] == user.email:
                raise HTTPException(status_code=400, detail="このメールアドレスは既に使用されています")
    
    # 更新データの準備
    update_data = user.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するデータが指定されていません")
    
    # ユーザー情報更新
    existing_user = users_db[user_id]
    for field, value in update_data.items():
        existing_user[field] = value
    existing_user["updated_at"] = datetime.now()
    
    return existing_user

# ユーザー削除
@app.delete("/users/{user_id}", status_code=204, summary="ユーザー削除")
async def delete_user(user_id: int):
    """
    指定されたIDのユーザーを削除します。
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    del users_db[user_id]
    return

# ヘルスチェックエンドポイント
@app.get("/health", summary="ヘルスチェック")
async def health_check():
    """
    APIの稼働状況を確認します。
    """
    return {"status": "ok", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)