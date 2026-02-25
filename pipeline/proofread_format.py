"""合併校對+標點 — 單次 LLM 呼叫同時完成
============================================
將原本分開的校對和標點步驟合併為一次 API 呼叫。
請求 LLM 同時輸出「校對版」和「排版版」。
A/B 測試用，不改原有代碼。
"""

import re
import logging

logger = logging.getLogger(__name__)


def build_merged_prompt(srt_text_only, lecture_text=""):
    """建立合併版 prompt：同時請求校對 + 標點。

    Args:
        srt_text_only: 字幕文字（格式：[1] 文字\n[2] 文字\n...)
        lecture_text: 講義參考文字

    Returns:
        str: 合併版 prompt
    """
    lecture_section = ""
    if lecture_text:
        lecture_section = f"""
以下是上課講義內容（供你參考佛學詞彙正確用字）：
<講義>
{lecture_text[:3000]}
...(講義節錄，僅供參考詞彙校對)
</講義>
"""

    return f"""你是一個佛學大師兼專業編輯，精通經律論三藏十二部經典。
以下文本是 whisper 產生的佛教公案選集字幕，有很多同音字錯誤。

請同時完成以下兩個任務，並用指定格式輸出：

## 任務一：校對版（不加標點，用於 SRT 對齊）
- 修正同音字錯誤
- 保留原始斷句和重複內容
- 輸出繁體中文
- 不要加標點符號

## 任務二：排版版（有標點分段，用於 Docx）
- 同樣修正同音字錯誤
- 加上正確的中文全形標點符號
- 適當分段
- 絕對禁止增減、替換、改寫講者的任何一個字
{lecture_section}
請用以下格式輸出：

<校對版>
[序號] 校對後文字（無標點）
...
</校對版>

<排版版>
有標點分段的完整文本
</排版版>

以下是需要處理的字幕文本：
<字幕>
{srt_text_only}
</字幕>

請直接輸出，不要有任何說明或額外文字。"""


def parse_merged_response(response_text):
    """解析合併版回應，提取校對版和排版版。

    Returns:
        tuple: (proofread_text, formatted_text) 或 (None, None) 如果解析失敗
    """
    if not response_text:
        return None, None

    # 提取 <校對版> ... </校對版>
    proofread_match = re.search(
        r'<校對版>\s*(.+?)\s*</校對版>', response_text, re.DOTALL
    )
    # 提取 <排版版> ... </排版版>
    formatted_match = re.search(
        r'<排版版>\s*(.+?)\s*</排版版>', response_text, re.DOTALL
    )

    proofread_text = proofread_match.group(1).strip() if proofread_match else None
    formatted_text = formatted_match.group(1).strip() if formatted_match else None

    if not proofread_text:
        logger.warning("無法解析 <校對版> 區塊")
    if not formatted_text:
        logger.warning("無法解析 <排版版> 區塊")

    return proofread_text, formatted_text
