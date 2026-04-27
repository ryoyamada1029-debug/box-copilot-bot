from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid

app = FastAPI(title="ユーザー管理API", version="1.0.0")

# データモデル定義
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "一般ユーザー"

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None

class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# メモリベースのデータストレージ（実装例）
users_db = {}

def generate_user_id() -> str:
    """ユーザーIDの自動生成"""
    return str(uuid.uuid4())

def validate_email_unique(email: str, exclude_id: str = None) -> bool:
    """メールアドレスの重複チェック"""
    for user_id, user in users_db.items():
        if user_id != exclude_id and user.email == email:
            return False
    return True

# USER-01: ユーザー一覧取得
@app.get("/users", response_model=List[User], status_code=status.HTTP_200_OK)
async def get_users():
    """登録されている全ユーザーの情報を取得する"""
    return list(users_db.values())

# USER-02: ユーザー新規作成
@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """新しいユーザーをシステムに登録する"""
    # メールアドレス重複チェック
    if not validate_email_unique(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="メールアドレスは既に登録されています"
        )
    
    # 新規ユーザー作成
    user_id = generate_user_id()
    now = datetime.now()
    
    new_user = User(
        id=user_id,
        name=user.name,
        email=user.email,
        role=user.role,
        created_at=now,
        updated_at=now
    )
    
    users_db[user_id] = new_user
    return new_user

# USER-03: ユーザー情報更新
@app.put("/users/{user_id}", response_model=User, status_code=status.HTTP_200_OK)
async def update_user(user_id: str, user_update: UserUpdate):
    """指定したIDのユーザー情報を更新する"""
    # ユーザー存在チェック
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    existing_user = users_db[user_id]
    
    # メールアドレス重複チェック（更新する場合のみ）
    if user_update.email and not validate_email_unique(user_update.email, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="メールアドレスは既に登録されています"
        )
    
    # 更新データの適用
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_user, field, value)
    
    existing_user.updated_at = datetime.now()
    
    users_db[user_id] = existing_user
    return existing_user

# USER-04: ユーザー削除
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """指定したIDのユーザーをシステムから削除する"""
    # ユーザー存在チェック
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    # 物理削除実行
    del users_db[user_id]

# ヘルスチェックエンドポイント
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """APIの稼働状態を確認する"""
    return {"status": "healthy", "timestamp": datetime.now()}

# エラーハンドリング用のカスタム例外ハンドラー
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="入力データが無効です"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)