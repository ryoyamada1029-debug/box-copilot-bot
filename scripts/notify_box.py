import os
from datetime import datetime, timezone
from boxsdk import JWTAuth, Client

def get_box_client():
    private_key = os.environ['BOX_PRIVATE_KEY'].replace('\\n', '\n')
    config = JWTAuth(
        client_id=os.environ['BOX_CLIENT_ID'],
        client_secret=os.environ['BOX_CLIENT_SECRET'],
        enterprise_id=os.environ['BOX_ENTERPRISE_ID'],
        jwt_key_id=os.environ['BOX_KEY_ID'],
        rsa_private_key_data=private_key,
        rsa_private_key_passphrase=None,
    )
    return Client(config)

def main():
    if os.environ.get('NO_FILES') == 'true': return

    doc_name  = os.environ.get('DOC_NAME', '不明')
    pr_url    = os.environ.get('PR_URL', '')
    pr_number = os.environ.get('PR_NUMBER', '')
    repo      = os.environ.get('GITHUB_REPOSITORY', '')
    run_id    = os.environ.get('GITHUB_RUN_ID', '')
    run_url   = f'https://github.com/{repo}/actions/runs/{run_id}'

    with open('slack_summary.txt', encoding='utf-8') as f:
        summary = f.read()

    lines = [f'- {l.strip().lstrip("- ")}' for l in summary.split('\n')
             if l.strip() and not l.strip().startswith('#')][:6]
    formatted = '\n'.join(lines)

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    safe = doc_name.replace(' ','_').replace('/','_').replace('.','_')
    filename = f'{date_str}_{safe}_#{pr_number}.md'

    content = f'''# AI生成完了通知

| 項目 | 内容 |
| --- | --- |
| 生成日時 | {now} |
| 参照ドキュメント | {doc_name} |
| PR番号 | #{pr_number} (Draft) |
| PRリンク | {pr_url} |
| Actionsログ | {run_url} |

## 実装サマリー
{formatted}

## 次のアクション
1. PRリンクを開いてコードを確認する
2. 問題なければDraftを解除してマージする
3. 修正が必要な場合はPR上でコメントを残す
'''

    client = get_box_client()
    client.folder(os.environ['BOX_NOTIFY_FOLDER_ID']).upload_stream(
        file_stream=content.encode('utf-8'),
        file_name=filename,
    )
    print(f'Box通知完了: {filename}')

if __name__ == '__main__':
    main()

