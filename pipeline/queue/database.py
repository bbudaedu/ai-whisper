import os
from sqlmodel import SQLModel, Session, create_engine

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "task_queue.db",
)

_engine = None

def get_engine(db_path: str | None = None):
    """取得或建立 SQLite engine（單例模式）。

    設定：
    - WAL 模式（提高並發讀取效能）
    - busy_timeout = 5000ms（避免 SQLITE_BUSY）
    - check_same_thread = False（允許多執行緒存取）
    """
    global _engine
    if _engine is not None:
        return _engine

    if db_path is None:
        db_path = _DEFAULT_DB_PATH

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db_url = f"sqlite:///{db_path}"

    _engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # 啟用 WAL 模式與 busy_timeout
    with _engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        conn.exec_driver_sql("PRAGMA busy_timeout=5000")
        conn.commit()

    return _engine


def create_db_and_tables(engine=None):
    """建立所有 SQLModel 資料表。"""
    if engine is None:
        engine = get_engine()
    # 確保 models 已被載入
    from pipeline.queue.models import Task, StageTask, TaskEvent, TaskArtifact  # noqa: F401
    from api.models import ApiKey, RefreshToken, User, Identity  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session(engine=None) -> Session:
    """建立新的 Session。"""
    if engine is None:
        engine = get_engine()
    return Session(engine)


def reset_engine():
    """重設 engine（用於測試）。"""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
