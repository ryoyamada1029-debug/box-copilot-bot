from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, validator
import uuid
from enum import Enum


class UserRole(str, Enum):
    """ユーザー権限の列挙型"""
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    """ユーザー基本情報のベースモデル"""
    name: str
    email: EmailStr
    role: UserRole = UserRole.USER
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('氏名は必須です')
        if len(v) > 100:
            raise ValueError('氏名は100文字以内で入力してください')
        return v.strip()


class UserCreate(UserBase):
    """ユーザー作成用モデル"""
    pass


class UserUpdate(BaseModel):
    """ユーザー更新用モデル（部分更新対応）"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('氏名は必須です')
            if len(v) > 100:
                raise ValueError('氏名は100文字以内で入力してください')
            return v.strip()
        return v


class User(UserBase):
    """ユーザー情報の完全モデル"""
    id: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """API レスポンス用ユーザーモデル"""
    id: str
    name: str
    email: str
    role: UserRole
    created_at: datetime
    updated_at: datetime


class APIError(BaseModel):
    """API エラーレスポンス用モデル"""
    error_code: str
    message: str
    details: Optional[dict] = None


class UserService:
    """ユーザー管理サービスクラス"""
    
    def __init__(self):
        # 実際の実装では、データベース接続などを初期化
        self.users_db = {}  # メモリ上の仮想DB（実装例）
    
    def get_all_users(self) -> List[User]:
        """全ユーザー取得（削除されていないもののみ）"""
        return [user for user in self.users_db.values() if not user.is_deleted]
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """ID指定でユーザー取得"""
        user = self.users_db.get(user_id)
        if user and not user.is_deleted:
            return user
        return None
    
    def create_user(self, user_data: UserCreate) -> User:
        """新規ユーザー作成"""
        # メール重複チェック
        existing_users = [u for u in self.users_db.values() if not u.is_deleted]
        if any(u.email == user_data.email for u in existing_users):
            raise ValueError("このメールアドレスは既に使用されています")
        
        # 新規ユーザー作成
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        new_user = User(
            id=user_id,
            name=user_data.name,
            email=user_data.email,
            role=user_data.role,
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        
        self.users_db[user_id] = new_user
        return new_user
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """ユーザー情報更新"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # メール重複チェック（自分以外）
        if user_data.email:
            existing_users = [u for u in self.users_db.values() 
                            if not u.is_deleted and u.id != user_id]
            if any(u.email == user_data.email for u in existing_users):
                raise ValueError("このメールアドレスは既に使用されています")
        
        # 更新処理
        update_fields = user_data.dict(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """ユーザー削除（論理削除）"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_deleted = True
        user.updated_at = datetime.utcnow()
        return True


class UserAPIHandler:
    """ユーザー管理API ハンドラークラス"""
    
    def __init__(self):
        self.user_service = UserService()
    
    def handle_get_users(self) -> dict:
        """GET /users - ユーザー一覧取得"""
        try:
            users = self.user_service.get_all_users()
            return {
                "status": "success",
                "data": [UserResponse(**user.dict()) for user in users],
                "count": len(users)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": APIError(
                    error_code="INTERNAL_ERROR",
                    message="サーバー内部エラーが発生しました"
                ).dict()
            }
    
    def handle_create_user(self, user_data: dict) -> dict:
        """POST /users - ユーザー作成"""
        try:
            # バリデーション
            create_data = UserCreate(**user_data)
            
            # ユーザー作成
            new_user = self.user_service.create_user(create_data)
            
            return {
                "status": "success",
                "data": UserResponse(**new_user.dict()).dict(),
                "message": "ユーザーが正常に作成されました"
            }
            
        except ValueError as e:
            return {
                "status": "error",
                "error": APIError(
                    error_code="VALIDATION_ERROR",
                    message=str(e)
                ).dict()
            }
        except Exception as e:
            return {
                "status": "error", 
                "error": APIError(
                    error_code="INTERNAL_ERROR",
                    message="サーバー内部エラーが発生しました"
                ).dict()
            }
    
    def handle_update_user(self, user_id: str, user_data: dict) -> dict:
        """PUT /users/{id} - ユーザー更新"""
        try:
            # バリデーション
            update_data = UserUpdate(**user_data)
            
            # ユーザー更新
            updated_user = self.user_service.update_user(user_id, update_data)
            
            if not updated_user:
                return {
                    "status": "error",
                    "error": APIError(
                        error_code="NOT_FOUND",
                        message="指定されたユーザーが見つかりません"
                    ).dict()
                }
            
            return {
                "status": "success",
                "data": UserResponse(**updated_user.dict()).dict(),
                "message": "ユーザー情報が正常に更新されました"
            }
            
        except ValueError as e:
            return {
                "status": "error",
                "error": APIError(
                    error_code="VALIDATION_ERROR", 
                    message=str(e)
                ).dict()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": APIError(
                    error_code="INTERNAL_ERROR",
                    message="サーバー内部エラーが発生しました"
                ).dict()
            }
    
    def handle_delete_user(self, user_id: str) -> dict:
        """DELETE /users/{id} - ユーザー削除"""
        try:
            success = self.user_service.delete_user(user_id)
            
            if not success:
                return {
                    "status": "error",
                    "error": APIError(
                        error_code="NOT_FOUND",
                        message="指定されたユーザーが見つかりません"
                    ).dict()
                }
            
            return {
                "status": "success",
                "message": "ユーザーが正常に削除されました"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": APIError(
                    error_code="INTERNAL_ERROR",
                    message="サーバー内部エラーが発生しました"
                ).dict()
            }