from datetime import datetime
from typing import List, Optional
from uuid import uuid4
import re
from enum import Enum

class UserRole(Enum):
    """ユーザー権限の定義"""
    ADMIN = "admin"
    USER = "user"

class User:
    """ユーザーエンティティ"""
    def __init__(self, name: str, email: str, role: UserRole = UserRole.USER):
        self.id = str(uuid4())  # システム自動採番
        self.name = name
        self.email = email
        self.role = role
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.is_deleted = False  # 論理削除フラグ

    def to_dict(self) -> dict:
        """辞書形式への変換"""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class UserValidator:
    """ユーザー情報バリデーション"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """メールアドレス形式チェック"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """氏名バリデーション（1-100文字）"""
        return bool(name and 1 <= len(name.strip()) <= 100)
    
    @staticmethod
    def validate_role(role: str) -> bool:
        """権限バリデーション"""
        return role in [r.value for r in UserRole]

class UserService:
    """ユーザー管理サービス"""
    
    def __init__(self):
        self._users: List[User] = []
    
    def get_all_users(self) -> List[dict]:
        """ユーザー一覧取得（論理削除されていないもののみ）"""
        active_users = [user for user in self._users if not user.is_deleted]
        return [user.to_dict() for user in active_users]
    
    def create_user(self, name: str, email: str, role: str = "user") -> dict:
        """ユーザー新規作成"""
        # バリデーション
        if not UserValidator.validate_name(name):
            raise ValueError("氏名は1-100文字で入力してください")
        
        if not UserValidator.validate_email(email):
            raise ValueError("正しいメールアドレス形式で入力してください")
        
        if not UserValidator.validate_role(role):
            raise ValueError("権限は'admin'または'user'を指定してください")
        
        # メールアドレス重複チェック
        if self._email_exists(email):
            raise ValueError("このメールアドレスは既に登録されています")
        
        # ユーザー作成
        user_role = UserRole.ADMIN if role == "admin" else UserRole.USER
        user = User(name=name, email=email, role=user_role)
        self._users.append(user)
        
        return user.to_dict()
    
    def update_user(self, user_id: str, name: Optional[str] = None, 
                   email: Optional[str] = None, role: Optional[str] = None) -> dict:
        """ユーザー情報更新"""
        user = self._find_user_by_id(user_id)
        if not user:
            raise ValueError("指定されたユーザーが見つかりません")
        
        # バリデーション
        if name is not None:
            if not UserValidator.validate_name(name):
                raise ValueError("氏名は1-100文字で入力してください")
            user.name = name
        
        if email is not None:
            if not UserValidator.validate_email(email):
                raise ValueError("正しいメールアドレス形式で入力してください")
            if email != user.email and self._email_exists(email):
                raise ValueError("このメールアドレスは既に登録されています")
            user.email = email
        
        if role is not None:
            if not UserValidator.validate_role(role):
                raise ValueError("権限は'admin'または'user'を指定してください")
            user.role = UserRole.ADMIN if role == "admin" else UserRole.USER
        
        user.updated_at = datetime.now()
        return user.to_dict()
    
    def delete_user(self, user_id: str) -> bool:
        """ユーザー削除（論理削除）"""
        user = self._find_user_by_id(user_id)
        if not user:
            raise ValueError("指定されたユーザーが見つかりません")
        
        user.is_deleted = True
        user.updated_at = datetime.now()
        return True
    
    def _find_user_by_id(self, user_id: str) -> Optional[User]:
        """ID指定でユーザー検索（論理削除されていないもののみ）"""
        for user in self._users:
            if user.id == user_id and not user.is_deleted:
                return user
        return None
    
    def _email_exists(self, email: str) -> bool:
        """メールアドレス重複チェック（論理削除されていないもののみ）"""
        for user in self._users:
            if user.email == email and not user.is_deleted:
                return True
        return False

class UserAPIResponse:
    """API応答の統一フォーマット"""
    
    @staticmethod
    def success(data=None, message="成功"):
        """成功レスポンス"""
        return {
            "status": "success",
            "message": message,
            "data": data
        }
    
    @staticmethod
    def error(message: str, status_code: int = 400):
        """エラーレスポンス"""
        return {
            "status": "error",
            "message": message,
            "status_code": status_code
        }

class UserController:
    """ユーザー管理コントローラー（API層）"""
    
    def __init__(self):
        self.service = UserService()
    
    def get_users(self) -> dict:
        """GET /users - ユーザー一覧取得"""
        try:
            users = self.service.get_all_users()
            return UserAPIResponse.success(users, "ユーザー一覧を取得しました")
        except Exception as e:
            return UserAPIResponse.error(str(e), 500)
    
    def create_user(self, request_data: dict) -> dict:
        """POST /users - ユーザー新規作成"""
        try:
            name = request_data.get("name")
            email = request_data.get("email")
            role = request_data.get("role", "user")
            
            user = self.service.create_user(name, email, role)
            return UserAPIResponse.success(user, "ユーザーを作成しました")
            
        except ValueError as e:
            return UserAPIResponse.error(str(e), 400)
        except Exception as e:
            return UserAPIResponse.error("サーバーエラーが発生しました", 500)
    
    def update_user(self, user_id: str, request_data: dict) -> dict:
        """PUT /users/{id} - ユーザー情報更新"""
        try:
            name = request_data.get("name")
            email = request_data.get("email")
            role = request_data.get("role")
            
            user = self.service.update_user(user_id, name, email, role)
            return UserAPIResponse.success(user, "ユーザー情報を更新しました")
            
        except ValueError as e:
            if "見つかりません" in str(e):
                return UserAPIResponse.error(str(e), 404)
            return UserAPIResponse.error(str(e), 400)
        except Exception as e:
            return UserAPIResponse.error("サーバーエラーが発生しました", 500)
    
    def delete_user(self, user_id: str) -> dict:
        """DELETE /users/{id} - ユーザー削除"""
        try:
            self.service.delete_user(user_id)
            return UserAPIResponse.success(None, "ユーザーを削除しました")
            
        except ValueError as e:
            return UserAPIResponse.error(str(e), 404)
        except Exception as e:
            return UserAPIResponse.error("サーバーエラーが発生しました", 500)

# 使用例
if __name__ == "__main__":
    controller = UserController()
    
    # ユーザー作成テスト
    create_result = controller.create_user({
        "name": "山田太郎",
        "email": "yamada@example.com",
        "role": "admin"
    })
    print("作成結果:", create_result)
    
    # ユーザー一覧取得テスト
    list_result = controller.get_users()
    print("一覧取得結果:", list_result)