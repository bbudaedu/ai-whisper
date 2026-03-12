import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json

def test_email_attachment_issue():
    CONFIG_FILE = "config.json"
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    EMAIL_USER = os.environ.get("EMAIL_USER") or config.get("email_user")
    EMAIL_PASS = os.environ.get("EMAIL_PASS") or config.get("email_pass")
    EMAIL_TO = config.get("email_to")
    SMTP_SERVER = config.get("smtp_server", "smtp.gmail.com")
    SMTP_PORT = int(config.get("smtp_port", 587))
    
    if not EMAIL_USER or not EMAIL_PASS:
        print("Missing email credentials in .env or config.json")
        return

    subject = "【附件測試】中文字幕測試"
    body = "這是一封測試附件檔名的郵件。"
    
    # 建立一個測試用的中文名檔案
    test_files = [
        "測試檔案_校對後.srt",
        "佛教公案選集001_簡豐文居士.docx"
    ]
    
    for fn in test_files:
        with open(fn, "w", encoding="utf-8") as f:
            f.write("test content")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(EMAIL_TO) if isinstance(EMAIL_TO, list) else EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for filename in test_files:
        try:
            with open(filename, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            
            # 這是原本有問題的寫法：有空格且沒有對中文進行編碼
            # part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            
            # 修復後的建議寫法 (使用 Header 或 utf-8 編碼)
            from email.header import Header
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=('utf-8', '', filename)
            )
            msg.attach(part)
        except Exception as e:
            print(f"Failed to attach {filename}: {e}")

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        server.quit()
        print(f"Sent successfully to {EMAIL_TO}")
    except Exception as e:
        print(f"Send failed: {e}")
    finally:
        for fn in test_files:
            if os.path.exists(fn):
                os.remove(fn)

if __name__ == "__main__":
    test_email_attachment_issue()
