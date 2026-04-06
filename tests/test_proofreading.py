import pytest
from pydantic import BaseModel, Field
from typing import Optional

# 定義校對結果結構
class ProofreadResult(BaseModel):
    corrected_text: str = Field(..., description="校對後的文本")
    notes: Optional[str] = Field(None, description="校對筆記或修改說明")

def proofread_text(raw_text: str, context: Optional[str] = None) -> ProofreadResult:
    """
    基於 LLM 的校對函式。
    目前實作目標為滿足測試需求，後續整合 LangChain。
    """
    # 這裡將實作 prompt 鏈結邏輯
    # 簡單模擬回傳
    return ProofreadResult(
        corrected_text=raw_text.strip(),
        notes="校對完成"
    )

def test_proofreader_basic():
    """Test 1: proofreader accepts raw text"""
    text = "這是一個測試。"
    result = proofread_text(text)
    assert isinstance(result, ProofreadResult)
    assert result.corrected_text == text

def test_proofreader_with_context():
    """Test 2: proofreader accepts raw text and context text"""
    text = "這是一個測試。"
    context = "參考資料：校對原則說明。"
    result = proofread_text(text, context=context)
    assert isinstance(result, ProofreadResult)
    assert result.corrected_text == text
