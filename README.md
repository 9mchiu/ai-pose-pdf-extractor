# ai-pose-pdf-extractor

處理 AI 3D 姿勢檢測（及一般）PDF 報告的小工具集，皆使用 Claude 視覺能力，掃描版 PDF 也能讀。

## 工具

### 0. 🌐 免安裝網頁版 PDF → Word（推薦給一般使用者）
打開連結、把 PDF 拖進去就能下載 Word，**文字→文字、圖片→圖片**。
全程在瀏覽器執行（pdf.js + Tesseract.js OCR + docx.js），**檔案不上傳、免裝任何東西**。

👉 **線上使用：** https://9mchiu.github.io/ai-pose-pdf-extractor/

原始碼在 [`docs/index.html`](docs/index.html)。掃描頁用瀏覽器內建 OCR，品質中等；要最高品質可用下方需 API key 的版本。

### 1. `pdf_to_word_web/` — PDF → Word 轉換器（Claude 版，需 API key）
本機跑 Flask，品質最好（Claude 視覺判讀，圖片區域分離較準）。適合進階使用。
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
