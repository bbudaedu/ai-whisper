import re
import os

def replace_read_first_with_files(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    content = re.sub(r'<read_first>(.*?)</read_first>', r'<files>\1</files>', content)
    with open(filepath, 'w') as f:
        f.write(content)

# 02.1-01
replace_read_first_with_files('.planning/phases/02.1-email-password-google-oauth-token/02.1-01-PLAN.md')

# 02.1-02
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-02-PLAN.md', 'r') as f:
    content = f.read()
content = re.sub(r'<read_first>(.*?)</read_first>', r'<files>\1</files>', content)

# Add password validation to Task 1
action_addition = r"""    - 實作 `validate_password_strength(password: str) -> bool` 函數，檢查密碼是否符合 D-08 規則（至少 12 碼，且包含大寫字母、小寫字母與數字）。若不符合拋出 ValueError。"""
content = content.replace('    - 實作 `hash_password(password: str) -> str` 返回 hashed string.', 
                          action_addition + '\n    - 實作 `hash_password(password: str) -> str` 返回 hashed string.')
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-02-PLAN.md', 'w') as f:
    f.write(content)

# 02.1-03
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-03-PLAN.md', 'r') as f:
    content = f.read()
content = re.sub(r'<read_first>(.*?)</read_first>', r'<files>\1</files>', content)

# update files_modified
content = content.replace('files_modified: ["api/routers/auth.py", "api_server.py"]', 'files_modified: ["api/routers/auth.py", "api_server.py", "api/auth.py"]')
# Add D-13
content = content.replace('    - 調整 `api/auth.py` 的 `refresh_token_expiry` 讓其預設為 30 天 (REFRESH_TOKEN_EXPIRE_DAYS=30)。',
                          '    - 調整 `api/auth.py` 的 `refresh_token_expiry` 讓其預設為 30 天 (REFRESH_TOKEN_EXPIRE_DAYS=30)。\n    - 調整 access token expiry 預設為 15 分鐘 (ACCESS_TOKEN_EXPIRE_MINUTES=15) 以符合 D-13 規範。')
# Add api/auth.py to files of Task 1
content = content.replace('<files>api_server.py</files>', '<files>api_server.py, api/routers/auth.py, api/auth.py</files>')
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-03-PLAN.md', 'w') as f:
    f.write(content)

# 02.1-04
replace_read_first_with_files('.planning/phases/02.1-email-password-google-oauth-token/02.1-04-PLAN.md')

# 02.1-05
replace_read_first_with_files('.planning/phases/02.1-email-password-google-oauth-token/02.1-05-PLAN.md')

# 02.1-06
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-06-PLAN.md', 'r') as f:
    content = f.read()

checkpoint_replacement = """<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Verify Auth Flow</name>
  <action>Pause execution for human to verify the complete authentication flow.</action>
  <what-built>
    1. `User` 與 `Identity` 儲存模型
    2. Password Hashing (Argon2) 工具
    3. `/api/auth/login` (Email/Password 登入取得 access/refresh token)
    4. `/api/auth/refresh` (換新 token, 舊 token 失效)
    5. `/api/auth/revoke` (撤銷使用者所有 refresh tokens)
    6. Google OAuth 架構 (Authlib, SessionMiddleware, `/google/login`, `/google/callback`)
  </what-built>
  <how-to-verify>
    1. 確認 `api/models.py` 有 `User`, `Identity` 模型。
    2. 確認 `api_server.py` 加入了 `SessionMiddleware` 與 `auth_router`。
    3. 執行測試：`python3 -m pytest tests/test_external_api_auth.py` 確保通過。
    4. (可選) 啟動伺服器 `python3 api_server.py`，使用 curl 或 HTTP Client 測試 `/api/auth/login` (先在 DB manually add user)。
  </how-to-verify>
  <verify>
    <automated>python3 -m pytest tests/test_external_api_auth.py -v</automated>
  </verify>
  <done>Human has approved the auth flow</done>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>"""

content = re.sub(r'<task type="checkpoint:human-verify" gate="blocking">.*?<\/task>', checkpoint_replacement, content, flags=re.DOTALL)
content = content.replace('<read_first>.planning/ROADMAP.md</read_first>', '<files>.planning/ROADMAP.md, .planning/STATE.md</files>')
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-06-PLAN.md', 'w') as f:
    f.write(content)

# VALIDATION.md
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-VALIDATION.md', 'r') as f:
    content = f.read()
content = content.replace('tests/test_auth_flow.py', 'tests/test_external_api_auth.py')
with open('.planning/phases/02.1-email-password-google-oauth-token/02.1-VALIDATION.md', 'w') as f:
    f.write(content)

