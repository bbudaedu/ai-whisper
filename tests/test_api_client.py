"""
ResilientAPIClient 測試套件
===========================
使用 mock 避免真實 API 呼叫。
"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from pipeline.api_client import ResilientAPIClient


@pytest.fixture
def client():
    """建立基本 API client（短延遲供測試用）。"""
    return ResilientAPIClient(
        api_base_url="http://fake-api:8045/v1/chat/completions",
        api_key="test-key",
        model="test-model",
        max_retries=3,
        base_delay=0.01,
        max_delay=0.1,
        timeout=5,
        circuit_threshold=3,
    )


@pytest.fixture
def client_with_email():
    """建立帶 Email 功能的 API client。"""
    email_func = MagicMock()
    return ResilientAPIClient(
        api_base_url="http://fake-api:8045/v1/chat/completions",
        api_key="test-key",
        model="test-model",
        max_retries=2,
        base_delay=0.01,
        max_delay=0.1,
        timeout=5,
        circuit_threshold=2,
        email_func=email_func,
        email_to=["admin@test.com"],
    ), email_func


class TestSuccessfulCalls:
    @patch("pipeline.api_client.requests.post")
    def test_successful_call_returns_content(self, mock_post, client, mock_api_success_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_api_success_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        result = client.call("校對這段文字")
        assert result == "[1] 佛教公案選集\n[2] 簡豐文居士"
        assert client.stats["total_calls"] == 1
        assert client.stats["total_failures"] == 0

    @patch("pipeline.api_client.requests.post")
    def test_successful_call_returns_reasoning_content(self, mock_post, client, mock_api_reasoning_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_api_reasoning_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        result = client.call("校對這段文字")
        assert result == "[1] 佛教公案選集\n[2] 簡豐文居士"


class TestRetryBehavior:
    @patch("pipeline.api_client.requests.post")
    def test_retry_on_503(self, mock_post, client, mock_api_success_response):
        error_resp = MagicMock()
        error_resp.status_code = 503
        error_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_resp)
        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = mock_api_success_response
        success_resp.raise_for_status.return_value = None
        mock_post.side_effect = [error_resp, success_resp]
        result = client.call("test prompt")
        assert result is not None
        assert mock_post.call_count == 2
        assert client.stats["total_retries"] == 1
        assert client.stats["consecutive_failures"] == 0

    @patch("pipeline.api_client.requests.post")
    def test_retry_on_timeout(self, mock_post, client, mock_api_success_response):
        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = mock_api_success_response
        success_resp.raise_for_status.return_value = None
        mock_post.side_effect = [requests.exceptions.Timeout(), success_resp]
        result = client.call("test prompt")
        assert result is not None
        assert mock_post.call_count == 2
        assert client.stats["total_retries"] == 1

    @patch("pipeline.api_client.requests.post")
    def test_retry_on_connection_error(self, mock_post, client, mock_api_success_response):
        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = mock_api_success_response
        success_resp.raise_for_status.return_value = None
        mock_post.side_effect = [requests.exceptions.ConnectionError(), success_resp]
        result = client.call("test prompt")
        assert result is not None
        assert mock_post.call_count == 2

    @patch("pipeline.api_client.requests.post")
    def test_max_retries_exceeded_returns_none(self, mock_post, client):
        error_resp = MagicMock()
        error_resp.status_code = 503
        error_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_resp)
        mock_post.return_value = error_resp
        result = client.call("test prompt")
        assert result is None
        assert mock_post.call_count == 3
        assert client.stats["total_failures"] == 1


class TestNonRetryableErrors:
    @patch("pipeline.api_client.requests.post")
    def test_400_not_retried(self, mock_post, client):
        error_resp = MagicMock()
        error_resp.status_code = 400
        error_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_resp)
        mock_post.return_value = error_resp
        result = client.call("test prompt")
        assert result is None
        assert mock_post.call_count == 1

    @patch("pipeline.api_client.requests.post")
    def test_401_not_retried(self, mock_post, client):
        error_resp = MagicMock()
        error_resp.status_code = 401
        error_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_resp)
        mock_post.return_value = error_resp
        result = client.call("test prompt")
        assert result is None
        assert mock_post.call_count == 1


class TestCircuitBreaker:
    @patch("pipeline.api_client.time.sleep")
    @patch("pipeline.api_client.requests.post")
    def test_circuit_breaker_triggers_email(self, mock_post, mock_sleep, client_with_email):
        client, email_func = client_with_email
        error_resp = MagicMock()
        error_resp.status_code = 503
        error_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_resp)
        mock_post.return_value = error_resp
        client.call("prompt 1")
        client.call("prompt 2")
        email_func.assert_called_once()
        call_args = email_func.call_args
        assert "連續失敗" in call_args[0][0] or "連續失敗" in call_args[0][1]

    @patch("pipeline.api_client.time.sleep")
    @patch("pipeline.api_client.requests.post")
    def test_circuit_breaker_resets_on_success(self, mock_post, mock_sleep, client, mock_api_success_response):
        error_resp = MagicMock()
        error_resp.status_code = 503
        error_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_resp)
        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = mock_api_success_response
        success_resp.raise_for_status.return_value = None
        mock_post.return_value = error_resp
        client.call("prompt 1")
        assert client.consecutive_failures == 1
        mock_post.return_value = success_resp
        result = client.call("prompt 2")
        assert result is not None
        assert client.consecutive_failures == 0


class TestExponentialBackoff:
    def test_delay_calculation(self, client):
        assert client._get_delay(0) == 0.01
        assert client._get_delay(1) == 0.02
        assert client._get_delay(2) == 0.04

    def test_delay_capped_at_max(self):
        client = ResilientAPIClient(
            api_base_url="http://fake",
            api_key="test",
            model="test",
            base_delay=10,
            max_delay=100,
        )
        assert client._get_delay(0) == 10
        assert client._get_delay(1) == 20
        assert client._get_delay(2) == 40
        assert client._get_delay(3) == 80
        assert client._get_delay(4) == 100


class TestStats:
    @patch("pipeline.api_client.requests.post")
    def test_stats_tracking(self, mock_post, client, mock_api_success_response):
        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = mock_api_success_response
        success_resp.raise_for_status.return_value = None
        mock_post.return_value = success_resp
        client.call("prompt 1")
        client.call("prompt 2")
        stats = client.stats
        assert stats["total_calls"] == 2
        assert stats["total_failures"] == 0
        assert stats["circuit_open"] is False
