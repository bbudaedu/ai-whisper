import os
import json
import logging
import sys
from pipeline.api_client import ResilientAPIClient

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def test_gemini_25_pro():
    # 1. 載入設定
    config_path = "config.json"
    if not os.path.exists(config_path):
        logger.error(f"找不到 {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    api_base_url = config.get("api_base_url")
    api_key = config.get("api_key")
    
    if not api_base_url or not api_key:
        logger.error("config.json 中缺少 api_base_url 或 api_key")
        return

    logger.info(f"API Base: {api_base_url}")
    
    # 2. 探測模型列表
    logger.info("--- 正在探測可用模型 ---")
    available_models = ResilientAPIClient.list_models(api_base_url, api_key)
    
    gemini_25_pro_exists = False
    for model in available_models:
        model_id = model.get("id")
        status = model.get("status", "✅" if "available" in model.get("status", "") else "")
        logger.info(f"模型: {model_id} - 狀態: {status}")
        if model_id == "gemini-2.5-pro":
            gemini_25_pro_exists = True

    if not gemini_25_pro_exists:
        logger.warning("在探測列表中未發現 gemini-2.5-pro，但仍會嘗試直接調用。")

    # 3. 測試校對功能
    test_model = "gemini-2.5-pro"
    logger.info(f"--- 正在測試模型: {test_model} ---")
    
    client = ResilientAPIClient(
        api_base_url=api_base_url,
        api_key=api_key,
        model=test_model
    )
    
    test_prompt = """你是一個佛學大師，幫我校對以下字幕文本。
<字幕>
[1] 南無本師釋迦摩尼佛
[2] 我們今天要講的公案是關於阿育王的
</字幕>
請直接輸出校對後的結果，格式完全相同（[序號] 校對後文字），不要有任何說明。"""

    logger.info("發送測試 Prompt...")
    result = client.call(test_prompt)
    
    if result:
        logger.info("--- 測試成功！ ---")
        logger.info(f"模型回應內容:\n{result}")
        if "釋迦牟尼佛" in result:
            logger.info("✅ 佛學用詞修正成功 (釋迦摩尼佛 -> 釋迦牟尼佛)")
        else:
            logger.warning("❌ 佛學用詞自修正未觸發")
    else:
        logger.error("--- 測試失敗：模型無回應 ---")

if __name__ == "__main__":
    test_gemini_25_pro()
