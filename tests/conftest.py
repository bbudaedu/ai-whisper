"""共用 fixtures for ai-whisper tests."""

import pytest

from api.auth import hash_password
from api.models import Identity, User


@pytest.fixture
def mock_api_success_response():
    """模擬成功的 API 回應。"""
    return {
        "choices": [
            {
                "message": {
                    "content": "[1] 佛教公案選集\n[2] 簡豐文居士",
                    "reasoning_content": "",
                }
            }
        ]
    }


@pytest.fixture
def mock_api_reasoning_response():
    """模擬只有 reasoning_content 的回應（某些中轉模型）。"""
    return {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning_content": "[1] 佛教公案選集\n[2] 簡豐文居士",
                }
            }
        ]
    }


@pytest.fixture
def sample_srt_content():
    """SRT 字幕範本。"""
    return (
        "1\n"
        "00:00:01,000 --> 00:00:05,000\n"
        "請最大的功念三稱本師聖號\n\n"
        "2\n"
        "00:00:05,000 --> 00:00:10,000\n"
        "南無本師釋迦摩尼佛\n\n"
        "3\n"
        "00:00:10,000 --> 00:00:15,000\n"
        "無上聖身唯妙法\n"
    )


@pytest.fixture
def sample_subtitles():
    """解析後的字幕列表。"""
    return [
        {"idx": "1", "timestamp": "00:00:01,000 --> 00:00:05,000", "text": "請最大的功念三稱本師聖號"},
        {"idx": "2", "timestamp": "00:00:05,000 --> 00:00:10,000", "text": "南無本師釋迦摩尼佛"},
        {"idx": "3", "timestamp": "00:00:10,000 --> 00:00:15,000", "text": "無上聖身唯妙法"},
    ]


# --- Task Queue Test Fixtures ---
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

@pytest.fixture
def db_engine():
    """建立 in-memory SQLite engine（每個測試獨立）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from pipeline.queue.models import Task, StageTask  # noqa: F401
    from api.models import ApiKey, RefreshToken, User, Identity  # noqa: F401
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    """建立 Session，測試後自動 rollback。"""
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def user_fixture(db_session):
    """建立啟用的測試帳號與 email identity。"""
    hashed_password = hash_password("StrongPassword123")
    user = User(email="test@example.com", is_active=True, role="external")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    identity = Identity(
        user_id=user.user_id,
        provider="email",
        provider_id=user.email,
        hashed_password=hashed_password,
    )
    db_session.add(identity)
    db_session.commit()

    return user


@pytest.fixture
def disabled_user(db_session):
    """建立停用的測試帳號與 email identity。"""
    hashed_password = hash_password("StrongPassword123")
    user = User(email="disabled@example.com", is_active=False, role="external")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    identity = Identity(
        user_id=user.user_id,
        provider="email",
        provider_id=user.email,
        hashed_password=hashed_password,
    )
    db_session.add(identity)
    db_session.commit()

    return user
