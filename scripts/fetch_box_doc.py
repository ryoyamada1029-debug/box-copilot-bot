import os, json
import io
from datetime import datetime, timedelta, timezone
from boxsdk import JWTAuth, Client
from docx import Document as DocxDocument

def get_box_client():
    private_key = os.environ['BOX_PRIVATE_KEY'].replace('\\n', '\n')
    passphrase = os.environ.get("BOX_PRIVATE_KEY_PASSPHRASE", "")  # ← 追加
    config = JWTAuth(
        client_id=os.environ['BOX_CLIENT_ID'],
        client_secret=os.environ['BOX_CLIENT_SECRET'],
        enterprise_id=os.environ['BOX_ENTERPRISE_ID'],
        jwt_key_id=os.environ['BOX_KEY_ID'],
        rsa_private_key_data=private_key,
        rsa_private_key_passphrase=passphrase.encode("utf-8") if passphrase else None,
    )
    return Client(config)

def extract_text_from_docx(binary_content):
    """docxバイナリからプレーンテキストを抽出する"""
    doc = DocxDocument(io.BytesIO(binary_content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)

def main():
    client = get_box_client()
    folder_id = os.environ.get('BOX_WATCH_FOLDER_ID')
    specific_file_id = os.environ.get('FILE_ID', '')

    if specific_file_id:
        files = [client.file(specific_file_id).get()]
    else:
        folder = client.folder(folder_id)
        items = folder.get_items(limit=100)
        threshold = datetime.now(timezone.utc) - timedelta(hours=25)
        files = []
        for item in items:
            if item.object_type != 'file': continue
            info = client.file(item.id).get()
            modified = datetime.fromisoformat(
                info.modified_at.replace('Z', '+00:00'))
            if modified >= threshold:
                files.append(info)

    if not files:
        print('更新されたファイルはありません')
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write('NO_FILES=true\n')
        return

    # target = files[0]
    # content = client.file(target.id).content().decode('utf-8', errors='replace')
    
    target = files[0]
    binary = client.file(target.id).content()  # bytesのまま受け取る

    # 拡張子に応じてテキスト抽出方法を切り替え
    if target.name.lower().endswith(".docx"):
        content = extract_text_from_docx(binary)
    else:
        content = binary.decode("utf-8", errors="replace")

    
    with open('doc_content.txt', 'w', encoding='utf-8') as f:
        f.write(content)

    safe_name = target.name.replace(' ','_').replace('/','_')
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f'DOC_NAME={target.name}\n')
        f.write(f'SAFE_DOC_NAME={safe_name}\n')

if __name__ == '__main__':
    main()

