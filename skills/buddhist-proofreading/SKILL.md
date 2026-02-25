# 佛教校對 Skill

包含校對用的 prompt 模板、常錯字典、以及校對引擎。

## 結構

```
skills/buddhist-proofreading/
├── SKILL.md          # 此檔案
├── prompts/
│   ├── proofread.md  # 校對 prompt 模板
│   └── punctuate.md  # 標點 prompt 模板
└── dictionaries/
    └── common_errors.json  # 常見同音字錯誤字典
```

## 用法

```python
from pipeline.proofreading_engine import ProofreadingEngine

engine = ProofreadingEngine()
text = engine.pre_correct("請最大的功念三稱本師聖號")
prompt = engine.build_prompt(subtitles, lecture_text)
```
