from typing import Dict, List, Optional
from uuid import uuid4
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify

app = Flask(__name__)

@dataclass
class User:
    """ユーザー情報を管理するデータクラス"""
    id: str
    name: str
    email: str
    role: str = "user"
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

class UserService:
    """ユーザー管理サービスクラス"""
    
    def __init__(self):
        # メモリベースでのユーザー管理（詳細設計でDB連携予定）
        self.users: Dict[str, User] = {}
    
    def validate_email(self, email: str) -> bool:
        """メールアドレスの形式バリデーション"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_user_data(self, data: dict, is_update: bool = False) -> List[str]:
        """ユーザーデータのバリデーション"""
        errors = []
        
        # 必須項目チェック（新規作成時のみ）
        if not is_update:
            if not data.get('name'):
                errors.append("名前は必須です")
            if not data.get('email'):
                errors.append("メールアドレスは必須です")
        
        # メールアドレス形式チェック
        if 'email' in data and data['email']:
            if not self.validate_email(data['email']):
                errors.append("メールアドレスの形式が正しくありません")
        
        # 権限の値チェック
        if 'role' in data and data['role']:
            valid_roles = ['admin', 'user', 'guest']
            if data['role'] not in valid_roles:
                errors.append(f"権限は {', '.join(valid_roles)} のいずれかを指定してください")
        
        return errors
    
    def get_all_users(self) -> List[dict]:
        """全ユーザー一覧取得"""
        return [asdict(user) for user in self.users.values()]
    
    def create_user(self, data: dict) -> tuple[dict, int]:
        """新規ユーザー作成"""
        # バリデーション
        errors = self.validate_user_data(data)
        if errors:
            return {"error": "バリデーションエラー", "details": errors}, 400
        
        # メールアドレス重複チェック
        email = data['email']
        for user in self.users.values():
            if user.email == email:
                return {"error": "指定されたメールアドレスは既に使用されています"}, 409
        
        # ユーザー作成
        user_id = str(uuid4())
        new_user = User(
            id=user_id,
            name=data['name'],
            email=email,
            role=data.get('role', 'user')
        )
        
        self.users[user_id] = new_user
        return asdict(new_user), 201
    
    def update_user(self, user_id: str, data: dict) -> tuple[dict, int]:
        """ユーザー情報更新"""
        # ユーザー存在チェック
        if user_id not in self.users:
            return {"error": "指定されたユーザーが見つかりません"}, 404
        
        # バリデーション
        errors = self.validate_user_data(data, is_update=True)
        if errors:
            return {"error": "バリデーションエラー", "details": errors}, 400
        
        # メールアドレス重複チェック（自分以外）
        if 'email' in data:
            for uid, user in self.users.items():
                if uid != user_id and user.email == data['email']:
                    return {"error": "指定されたメールアドレスは既に使用されています"}, 409
        
        # ユーザー情報更新
        user = self.users[user_id]
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        
        user.updated_at = datetime.now().isoformat()
        
        return asdict(user), 200
    
    def delete_user(self, user_id: str) -> tuple[dict, int]:
        """ユーザー削除"""
        if user_id not in self.users:
            return {"error": "指定されたユーザーが見つかりません"}, 404
        
        del self.users[user_id]
        return {"message": "ユーザーが正常に削除されました"}, 200

# サービスインスタンス生成
user_service = UserService()

@app.route('/users', methods=['GET'])
def get_users():
    """ユーザー一覧取得API"""
    try:
        users = user_service.get_all_users()
        return jsonify({"users": users, "count": len(users)}), 200
    except Exception as e:
        return jsonify({"error": "内部サーバーエラー", "details": str(e)}), 500

@app.route('/users', methods=['POST'])
def create_user():
    """ユーザー新規作成API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "リクエストボディが必要です"}), 400
        
        result, status_code = user_service.create_user(data)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": "内部サーバーエラー", "details": str(e)}), 500

@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id: str):
    """ユーザー情報更新API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "リクエストボディが必要です"}), 400
        
        result, status_code = user_service.update_user(user_id, data)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": "内部サーバーエラー", "details": str(e)}), 500

@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id: str):
    """ユーザー削除API"""
    try:
        result, status_code = user_service.delete_user(user_id)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": "内部サーバーエラー", "details": str(e)}), 500

if __name__ == '__main__':
    # 開発用サーバー起動
    app.run(debug=True, host='0.0.0.0', port=5000)