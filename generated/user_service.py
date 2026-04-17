from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# ユーザーデータモデル
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

# メモリ内データストレージ（実際の実装ではデータベースを使用）
users_db = {}
next_user_id = 1

@app.get("/users", response_model=List[User])
async def get_users():
    """ユーザー一覧取得"""
    return list(users_db.values())

@app.post("/users", response_model=User)
async def create_user(user: User):
    """ユーザー新規作成"""
    global next_user_id
    
    user.id = next_user_id
    users_db[next_user_id] = user
    next_user_id += 1
    
    return user

@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user_update: UserUpdate):
    """ユーザー情報更新"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing_user = users_db[user_id]
    
    # 更新データが提供された場合のみ更新
    if user_update.name is not None:
        existing_user.name = user_update.name
    if user_update.email is not None:
        existing_user.email = user_update.email
    
    users_db[user_id] = existing_user
    return existing_user

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """ユーザー削除"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    del users_db[user_id]
    return {"message": "User deleted successfully"}

# アプリケーション起動用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)