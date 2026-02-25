"""
ResilientAPIClient — 統一 API 呼叫模組
=======================================
支援指數退避重試、Circuit Breaker、Email 告警。
取代 auto_proofread.py / auto_postprocess.py 中重複的 call_api 邏輯。
"""

import time
import logging
import requests

logger = logging.getLogger(__name__)


class ResilientAPIClient:
    """帶有指數退避和 Circuit Breaker 的 API 呼叫客戶端。"""

    def __init__(
        self,
        api_base_url,
        api_key,
        model,
        max_retries=5,
        base_delay=10,
        max_delay=300,
        timeout=300,
        circuit_threshold=3,
        email_func=None,
        email_to=None,
    ):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.circuit_threshold = circuit_threshold
        self.email_func = email_func
        self.email_to = email_to

        # Circuit breaker state
        self.consecutive_failures = 0
        self.total_calls = 0
        self.total_failures = 0
        self.total_retries = 0
        self._circuit_open = False
        self._pause_duration = 900  # 暫停 15 分鐘

    def call(self, prompt, max_tokens=8192):
        """送出 LLM API 請求，帶指數退避重試。

        Returns:
            str: API 回應文字，失敗回傳 None。
        """
        self.total_calls += 1
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    self.api_base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                message = data["choices"][0]["message"]
                content = message.get("content", "")
                reasoning = message.get("reasoning_content", "")
                result_text = content if content else reasoning

                # 成功 → 重置 circuit breaker
                self.consecutive_failures = 0
                self._circuit_open = False
                return result_text

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 0
                is_retryable = status_code in (429, 500, 502, 503, 504)

                if not is_retryable:
                    logger.error(f"不可重試的 HTTP 錯誤 {status_code}: {e}")
                    self._record_failure()
                    return None

                delay = self._get_delay(attempt)
                logger.warning(
                    f"HTTP {status_code} (第 {attempt + 1}/{self.max_retries} 次) "
                    f"— 等待 {delay:.0f} 秒後重試"
                )
                self.total_retries += 1
                time.sleep(delay)

            except requests.exceptions.Timeout:
                delay = self._get_delay(attempt)
                logger.warning(
                    f"API 逾時 (第 {attempt + 1}/{self.max_retries} 次) "
                    f"— 等待 {delay:.0f} 秒後重試"
                )
                self.total_retries += 1
                time.sleep(delay)

            except requests.exceptions.ConnectionError:
                delay = self._get_delay(attempt)
                logger.warning(
                    f"連線失敗 (第 {attempt + 1}/{self.max_retries} 次) "
                    f"— 等待 {delay:.0f} 秒後重試"
                )
                self.total_retries += 1
                time.sleep(delay)

            except Exception as e:
                logger.error(f"未預期錯誤: {e}")
                self._record_failure()
                return None

        # 所有重試用盡
        logger.error(f"API 呼叫失敗，已重試 {self.max_retries} 次")
        self._record_failure()
        return None

    def _get_delay(self, attempt):
        """計算指數退避延遲時間。"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay

    def _record_failure(self):
        """記錄失敗，觸發 circuit breaker 檢查。"""
        self.total_failures += 1
        self.consecutive_failures += 1

        if self.consecutive_failures >= self.circuit_threshold:
            self._trigger_circuit_breaker()

    def _trigger_circuit_breaker(self):
        """Circuit breaker 觸發：暫停 + 發送 Email 告警。"""
        self._circuit_open = True
        logger.critical(
            f"🔴 Circuit Breaker 觸發！連續 {self.consecutive_failures} 次失敗。"
            f"暫停 {self._pause_duration // 60} 分鐘。"
        )

        # 發送告警 Email
        if self.email_func and self.email_to:
            subject = "⚠️ AI-Whisper API 連續失敗告警"
            body = (
                f"API 連續失敗 {self.consecutive_failures} 次，已觸發 Circuit Breaker。\n\n"
                f"API 端點: {self.api_base_url}\n"
                f"使用模型: {self.model}\n"
                f"總呼叫數: {self.total_calls}\n"
                f"總失敗數: {self.total_failures}\n"
                f"總重試數: {self.total_retries}\n\n"
                f"系統將暫停 {self._pause_duration // 60} 分鐘後自動恢復。\n"
                f"如需人工介入，請檢查中轉 API 服務狀態。"
            )
            try:
                self.email_func(subject, body)
                logger.info("已發送告警 Email")
            except Exception as e:
                logger.error(f"告警 Email 發送失敗: {e}")

        # 暫停
        logger.info(f"暫停 {self._pause_duration // 60} 分鐘...")
        time.sleep(self._pause_duration)

        # 暫停結束，重置計數器給予再一次機會
        self.consecutive_failures = 0
        self._circuit_open = False
        logger.info("Circuit Breaker 已重置，恢復請求。")

    @property
    def stats(self):
        """回傳呼叫統計。"""
        return {
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_retries": self.total_retries,
            "consecutive_failures": self.consecutive_failures,
            "circuit_open": self._circuit_open,
        }

    @staticmethod
    def list_models(api_base_url, api_key, timeout=15):
        """探測中轉 API 可用的模型列表。

        嘗試 OpenAI 相容的 /v1/models 端點。
        如果不支援，會嘗試發送一個小型 prompt 測試常見模型名稱。

        Returns:
            list[dict]: 可用模型列表，每個含 id 和 status。
        """
        # 從 chat/completions URL 推導出 models URL
        models_url = api_base_url.replace("/chat/completions", "/models")
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        # 方法 1: 標準 /v1/models 端點
        try:
            resp = requests.get(models_url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    return [
                        {"id": m.get("id", "unknown"), "owned_by": m.get("owned_by", "")}
                        for m in data["data"]
                    ]
        except Exception as e:
            logger.warning(f"標準 /v1/models 端點不可用: {e}")

        # 方法 2: 逐一探測常見模型
        candidate_models = [
            "gemini-3-flash",
            "gemini-3-pro",
            "gemini-3-pro-low",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gpt-4o",
            "gpt-4o-mini",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet",
            "deepseek-chat",
            "deepseek-reasoner",
        ]
        results = []
        for model_name in candidate_models:
            try:
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                }
                resp = requests.post(
                    api_base_url,
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload,
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    results.append({"id": model_name, "status": "✅ available"})
                elif resp.status_code in (400, 404):
                    results.append({"id": model_name, "status": "❌ not found"})
                elif resp.status_code == 429:
                    results.append({"id": model_name, "status": "⚠️ rate limited (but exists)"})
                elif resp.status_code == 503:
                    results.append({"id": model_name, "status": "⚠️ 503 (may be temporary)"})
                else:
                    results.append({"id": model_name, "status": f"❓ HTTP {resp.status_code}"})
            except requests.exceptions.Timeout:
                results.append({"id": model_name, "status": "⏱️ timeout"})
            except Exception:
                results.append({"id": model_name, "status": "❌ error"})
        return results
