"""Download 端點測試：zip 結構、格式篩選、認證與 RBAC。"""

import io
import zipfile

import pytest
from sqlmodel import Session

from api.auth import create_access_token
from pipeline.queue.models import Task, TaskSource, TaskStatus


@pytest.fixture
def done_task_with_files(client, db_engine):
    """建立 DONE 狀態的任務與對應的輸出檔案。"""
    import api.routers.download as download_mod

    output_base = download_mod.OUTPUT_BASE

    with Session(db_engine) as session:
        task = Task(
            title="Download Test",
            video_id="dl_test_vid",
            status=TaskStatus.DONE,
            requester="test-requester-dl",
            source=TaskSource.EXTERNAL,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        output_dir = output_base / str(task.id)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "result.docx").write_bytes(b"fake word content")
        (output_dir / "result.xlsx").write_bytes(b"fake excel content")
        (output_dir / "result.txt").write_text("fake text content")
        (output_dir / "result.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\ntest\n")

        return task


@pytest.fixture
def dl_auth_header():
    """產生 requester=test-requester-dl 的 auth header。"""
    token = create_access_token({"user_id": "test-requester-dl", "role": "external"})
    return {"Authorization": f"Bearer {token}"}


class TestDownloadFormats:
    """GET /api/tasks/{id}/download — 格式篩選。"""

    def test_download_all_formats(self, client, done_task_with_files, dl_auth_header):
        """無 format 參數，zip 應包含所有 ALLOWED_SUFFIXES 的檔案。"""
        task = done_task_with_files
        response = client.get(f"/api/tasks/{task.id}/download", headers=dl_auth_header)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert len(names) == 4
        assert any(n.endswith(".docx") for n in names)
        assert any(n.endswith(".xlsx") for n in names)
        assert any(n.endswith(".txt") for n in names)
        assert any(n.endswith(".srt") for n in names)

    def test_download_word_alias(self, client, done_task_with_files, dl_auth_header):
        """?format=word 應只回傳 .docx 檔案。"""
        task = done_task_with_files
        response = client.get(
            f"/api/tasks/{task.id}/download?format=word",
            headers=dl_auth_header,
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert len(names) == 1
        assert names[0].endswith(".docx")

    def test_download_excel_alias(self, client, done_task_with_files, dl_auth_header):
        """?format=excel 應只回傳 .xlsx 檔案。"""
        task = done_task_with_files
        response = client.get(
            f"/api/tasks/{task.id}/download?format=excel",
            headers=dl_auth_header,
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert len(names) == 1
        assert names[0].endswith(".xlsx")

    def test_download_txt_format(self, client, done_task_with_files, dl_auth_header):
        """?format=txt 應只回傳 .txt 檔案。"""
        task = done_task_with_files
        response = client.get(
            f"/api/tasks/{task.id}/download?format=txt",
            headers=dl_auth_header,
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert len(names) == 1
        assert names[0].endswith(".txt")


class TestDownloadAuth:
    """Download 端點認證機制。"""

    def test_download_with_token_query_param(self, client, done_task_with_files):
        """?token=xxx query param 應等同 Bearer header。"""
        task = done_task_with_files
        token = create_access_token({"user_id": "test-requester-dl", "role": "external"})
        response = client.get(f"/api/tasks/{task.id}/download?token={token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    def test_download_without_auth_returns_401(self, client, done_task_with_files):
        """無 token 下載應回 401。"""
        task = done_task_with_files
        response = client.get(f"/api/tasks/{task.id}/download")
        assert response.status_code == 401


class TestDownloadRBAC:
    """Download 端點角色隔離。"""

    def test_download_forbidden_for_other_external_user(self, client, done_task_with_files, auth_header):
        """external user 下載別人的任務應回 403。"""
        task = done_task_with_files
        response = client.get(f"/api/tasks/{task.id}/download", headers=auth_header)
        assert response.status_code == 403

    def test_download_allowed_for_internal(self, client, done_task_with_files, internal_auth_header):
        """internal user 可以下載任何人的任務。"""
        task = done_task_with_files
        response = client.get(f"/api/tasks/{task.id}/download", headers=internal_auth_header)
        assert response.status_code == 200


class TestDownloadErrors:
    """Download 端點錯誤情境。"""

    def test_download_pending_task_returns_400(self, client, db_engine, internal_auth_header):
        """status=PENDING 的任務下載應回 400。"""
        with Session(db_engine) as session:
            task = Task(
                title="Pending Task",
                video_id="pending_vid",
                status=TaskStatus.PENDING,
                requester="some-other-user",
                source=TaskSource.EXTERNAL,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            task_id = task.id

        response = client.get(f"/api/tasks/{task_id}/download", headers=internal_auth_header)
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    def test_download_done_but_no_files_returns_404(self, client, db_engine):
        """DONE 任務但無輸出檔案應回 404。"""
        with Session(db_engine) as session:
            task = Task(
                title="Empty Done",
                video_id="empty_done_vid",
                status=TaskStatus.DONE,
                requester="empty-user",
                source=TaskSource.EXTERNAL,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            task_id = task.id

        token = create_access_token({"user_id": "empty-user", "role": "external"})
        response = client.get(
            f"/api/tasks/{task_id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


class TestZipStructure:
    """驗證 zip 封裝結構。"""

    def test_zip_arcname_is_relative(self, client, done_task_with_files, dl_auth_header):
        """zip 內的 arcname 應為相對路徑（不含絕對路徑前綴）。"""
        task = done_task_with_files
        response = client.get(f"/api/tasks/{task.id}/download", headers=dl_auth_header)
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        for name in zf.namelist():
            assert not name.startswith("/"), f"arcname should be relative: {name}"
            assert ".." not in name, f"arcname should not contain ..: {name}"
