# ai-pose-pdf-extractor

處理 AI 3D 姿勢檢測（及一般）PDF 報告的小工具集，皆使用 Claude 視覺能力，掃描版 PDF 也能讀。

## 工具

### 1. `pdf_to_word_web/` — PDF → Word 轉換器（網頁版）
把 PDF 拖進網頁，自動萃取內容並下載 Word 檔：**文字→文字、圖片→圖片**。
詳見 [`pdf_to_word_web/README.md`](pdf_to_word_web/README.md)。

```bash
cd pdf_to_word_web
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="你的 key"
python app.py       # 打開 http://127.0.0.1:5000
```

### 2. `extract_pose_metrics.py` — 數據指標萃取
把一整個資料夾的掃描版 PDF 報告，抽出數據指標（MPJPE、FPS、精度…）成 JSON + CSV，方便跨報告比較。

```bash
pip install anthropic
export ANTHROPIC_API_KEY="你的 key"
# 把 PDF 放進 ./pdfs
python extract_pose_metrics.py   # 輸出 output/results.json 與 output/metrics.csv
```

## 共通事項
- 需要 `ANTHROPIC_API_KEY`（透過環境變數，不寫進程式碼）。
- 使用模型 `claude-opus-4-8`（高解析視覺 + 大 context）。
- 掃描頁屬圖片輸入，token 成本較高。
