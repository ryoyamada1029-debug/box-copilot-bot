import os, anthropic

SYSTEM_PROMPT = '''
あなたはシニアPythonエンジニアです。
設計書・要件定義書を読み取り、必ず以下のXMLタグで応答してください。

<summary>
- 参照ドキュメント名と概要
- 実装した機能の要点（3〜5点）
- 設計上の判断・前提条件
</summary>

<code>
# 実装コード（Python）
</code>

<filename>
保存ファイル名（例: user_service.py）
</filename>
'''

def parse_response(text):
    def extract(tag, content):
        s = content.find(f'<{tag}>')
        e = content.find(f'</{tag}>')
        if s == -1 or e == -1: return ''
        return content[s+len(tag)+2:e].strip()
    return {
        'summary': extract('summary', text),
        'code': extract('code', text),
        'filename': extract('filename', text) or 'generated_code.py',
    }

def main():
    if os.environ.get('NO_FILES') == 'true': return

    with open('doc_content.txt', encoding='utf-8') as f:
        doc_content = f.read()

    doc_name = os.environ.get('DOC_NAME', 'ドキュメント')
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    message = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content':
            f'【ドキュメント名】{doc_name}\n\n【内容】\n{doc_content}'}]
    )

    result = parse_response(message.content[0].text)
    os.makedirs('generated', exist_ok=True)
    filepath = f"generated/{result['filename']}"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result['code'])

    pr_body = f'''## AI生成コード
**参照ドキュメント:** {doc_name}

### 実装サマリー
{result['summary']}

> このPRはClaude APIによって自動生成されました。
'''

    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f'GENERATED_FILE={filepath}\n')
    with open('pr_body.txt', 'w', encoding='utf-8') as f:
        f.write(pr_body)
    with open('slack_summary.txt', 'w', encoding='utf-8') as f:
        f.write(result['summary'])

if __name__ == '__main__':
    main()

