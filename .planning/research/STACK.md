# Stack Research

**Domain:** 語音處理平台（Whisper-based transcription + API + 外部 Web UI）
**Researched:** 2026-03-21
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FastAPI | 0.135.1 | 後端 API 框架 | Python 生態主流的高效能 ASGI 框架，與 Pydantic v2 整合成熟。（Confidence: HIGH） |
| Uvicorn | 0.41.0 | ASGI 伺服器 | FastAPI 官方常用部署組合，效能與相容性佳。（Confidence: HIGH） |
| Pydantic | 2.12.5 | 資料驗證/序列化 | FastAPI 預設資料模型標準，型別與驗證成本低。（Confidence: HIGH） |
| PostgreSQL | 17.9 | 主要資料庫 | 穩定主流關聯式資料庫，適合任務、使用者、審計與權限資料。（Confidence: MEDIUM） |
| SQLAlchemy | 2.0.48 | ORM | Python 主流 ORM，v2 async API 成熟，適合 FastAPI。（Confidence: HIGH） |
| Alembic | 1.18.4 | DB migration | SQLAlchemy 官方遷移工具，版本相容性穩定。（Confidence: HIGH） |
| asyncpg | 0.31.0 | PostgreSQL async driver | 高效能 async driver，搭配 SQLAlchemy async 使用。（Confidence: HIGH） |
| Celery | 5.6.2 | 任務佇列/排程 | 成熟任務佇列，支援優先序、重試、分隊列，符合單 GPU 排程需求。（Confidence: HIGH） |
| Redis | 8.6.1 | Broker / 快取 | Celery 常用 broker，延遲低，適合排隊與短期狀態。（Confidence: HIGH） |
| pyannote-audio | 4.0.4 | Speaker diarization | 2025/2026 主流 diarization 套件，支援 A/B/C/D 標註流程。（Confidence: MEDIUM） |
| Authlib | 1.6.9 | OAuth 2.0 / OpenID Connect | FastAPI 常用 OAuth 套件，適合 Google OAuth。（Confidence: HIGH） |
| PyJWT | 2.12.1 | JWT 簽發/驗證 | 主流 JWT 函式庫，配合 FastAPI 做 access/refresh token。（Confidence: HIGH） |
| argon2-cffi | 25.1.0 | 密碼雜湊 | Argon2 目前安全建議首選，適合 Email/Password。（Confidence: HIGH） |
| boto3 | 1.42.72 | S3 物件儲存 | 標準 AWS S3 SDK，亦可對接 S3-compatible 儲存。（Confidence: HIGH） |
| React | 19.2.4 | 外部 Web UI 核心 | 2026 主流前端框架，與現有 React 19 一致。（Confidence: HIGH） |
| React DOM | 19.2.4 | React UI 渲染 | 與 React 版本必須一致，避免 runtime mismatch。（Confidence: HIGH） |
| Vite | 8.0.1 | 前端建置工具 | 目前主流前端建置工具，啟動快、DX 佳。（Confidence: HIGH） |
| react-router-dom | 7.13.1 | 前端路由 | React Router v7 為 2026 主流路由方案。（Confidence: HIGH） |
| @tanstack/react-query | 5.91.3 | 資料存取/快取 | API 驅動 UI 的標準方案，適合任務狀態輪詢與快取。（Confidence: HIGH） |
| tailwindcss | 4.2.2 | UI 樣式 | Mobile-first + responsive 開發效率高。（Confidence: HIGH） |
| zod | 4.3.6 | 前端資料驗證 | 與 TypeScript 型別整合佳，用於表單與 API payload 驗證。（Confidence: HIGH） |
| react-hook-form | 7.71.2 | 表單管理 | 與 Zod 搭配良好，表單效能佳。（Confidence: HIGH） |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi-mail | 1.6.2 | Email 通知 | 需要模板與背景寄信時。（Confidence: HIGH） |
| aiosmtplib | 5.1.0 | SMTP 寄信 | 需要更細 SMTP 控制、或整合既有 SMTP 伺服器時。（Confidence: HIGH） |
| APScheduler | 3.11.2 | 內建排程 | 只要簡單排程、且不想跑 Celery beat 時。（Confidence: HIGH） |
| whisperx | 3.8.2 | 對齊/字級時間戳 | 需要字級時間戳、或要用既有 WhisperX pipeline 時。（Confidence: MEDIUM） |
| psycopg | 3.3.3 | PostgreSQL driver | 偏好 psycopg 生態或需要同步 DB 連線時。（Confidence: HIGH） |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | 後端測試 | API/任務流程測試可配合 httpx。 |
| ruff | Python lint/format | 速度快、規則完整，適合 CI。 |
| mypy | 型別檢查 | 對 FastAPI/Pydantic 模型有效。 |
| vitest | 前端測試 | 與 Vite 生態一致。 |

## Installation

```bash
# Core (backend)
pip install fastapi==0.135.1 uvicorn==0.41.0 pydantic==2.12.5 \
  sqlalchemy==2.0.48 alembic==1.18.4 asyncpg==0.31.0 \
  celery==5.6.2 pyannote-audio==4.0.4 \
  authlib==1.6.9 pyjwt==2.12.1 argon2-cffi==25.1.0 \
  boto3==1.42.72

# Supporting (backend)
pip install fastapi-mail==1.6.2 aiosmtplib==5.1.0 apscheduler==3.11.2 \
  whisperx==3.8.2 psycopg==3.3.3

# Core (frontend)
npm install react@19.2.4 react-dom@19.2.4 react-router-dom@7.13.1 \
  @tanstack/react-query@5.91.3 tailwindcss@4.2.2 zod@4.3.6 \
  react-hook-form@7.71.2

# Dev dependencies (frontend)
npm install -D vite@8.0.1
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Celery + Redis | RQ + Redis | 只需要極簡任務佇列、沒有優先序與排程需求時。 |
| pyannote-audio | whisperx | 需要整合對齊與 diarization 的一體化流程時。 |
| fastapi-mail + SMTP | AWS SES（boto3） | 需要更高寄送成功率與可擴展寄信量時。 |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| fastapi-users | 官方標註 maintenance mode，只維護安全/相依更新。（LOW/MEDIUM 風險） | Authlib + PyJWT + 自建 user model |
| passlib | 最新版本停留在 2020 年，維護節奏慢。（LOW 信任） | argon2-cffi |
| SQLite（正式環境） | 檔案式 DB 不利於併發與持久化任務資料 | PostgreSQL |
| 檔案直接存本機磁碟（正式環境） | 無法支援長期保存、備援與跨節點 | S3/MinIO + boto3 |

## Stack Patterns by Variant

**If 只有單機部署、排程非常簡單：**
- Use APScheduler + FastAPI 背景任務
- Because 部署簡單，維運成本低

**If 需要多租戶與優先序排隊：**
- Use Celery + Redis，將內部/外部任務分離 queue，worker concurrency=1
- Because 可控優先序與重試策略，符合單 GPU 限制

**If 需自建物件儲存：**
- Use MinIO（S3-compatible）+ boto3
- Because 介面與 S3 一致，易於未來遷移

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| fastapi@0.135.1 | pydantic@2.12.5 | FastAPI 以 Pydantic v2 為主線，避免混用 v1。 |
| sqlalchemy@2.0.48 | alembic@1.18.4 | 同為 SQLAlchemy 2.x 世代，遷移功能較穩定。 |
| react@19.2.4 | react-dom@19.2.4 | 需版本一致以避免 runtime mismatch。 |

## Sources

- https://pypi.org/project/fastapi/ — FastAPI 最新版本
- https://pypi.org/project/uvicorn/ — Uvicorn 最新版本
- https://pypi.org/project/pydantic/ — Pydantic 最新版本
- https://www.postgresql.org/developer/roadmap/ — PostgreSQL 17.9/18.3 發布資訊
- https://pypi.org/project/SQLAlchemy/ — SQLAlchemy 最新版本
- https://pypi.org/project/alembic/ — Alembic 最新版本
- https://pypi.org/pypi/asyncpg/json — asyncpg 最新版本
- https://pypi.org/project/psycopg/ — psycopg 最新版本
- https://pypi.org/pypi/celery/ — Celery 最新版本
- https://download.redis.io/releases/ — Redis 最新穩定版本
- https://pypi.org/project/pyannote-audio/ — pyannote-audio 最新版本
- https://pypi.org/project/whisperx/ — whisperx 最新版本
- https://pypi.org/project/Authlib/ — Authlib 最新版本
- https://pypi.org/project/pyjwt/ — PyJWT 最新版本
- https://pypi.org/project/argon2-cffi/ — argon2-cffi 最新版本
- https://pypi.org/pypi/passlib/ — passlib 停更狀態
- https://pypi.org/project/fastapi-users/ — fastapi-users maintenance mode
- https://pypi.org/project/boto3/ — boto3 最新版本
- https://pypi.org/project/aiosmtplib/ — aiosmtplib 最新版本
- https://pypi.org/project/fastapi-mail/ — fastapi-mail 最新版本
- https://registry.npmjs.org/react/latest — React 版本
- https://registry.npmjs.org/react-dom/latest — React DOM 版本
- https://registry.npmjs.org/vite/latest — Vite 版本
- https://registry.npmjs.org/react-router-dom/latest — React Router DOM 版本
- https://registry.npmjs.org/%40tanstack/react-query/latest — TanStack Query 版本
- https://registry.npmjs.org/tailwindcss/latest — Tailwind CSS 版本
- https://registry.npmjs.org/zod/latest — Zod 版本
- https://registry.npmjs.org/react-hook-form/latest — React Hook Form 版本

---
*Stack research for: 語音處理平台（Whisper-based transcription + API + 外部 Web UI）*
*Researched: 2026-03-21*
