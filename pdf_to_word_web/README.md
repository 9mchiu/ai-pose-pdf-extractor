# PDF → Word 轉換器（網頁版）

把 PDF 拖進網頁，自動萃取內容並下載 Word 檔：
- **文字** → 以文字呈現（掃描版也能讀，用 Claude 視覺 OCR）
- **圖片 / 圖表** → 以圖片呈現（從原頁裁切後嵌入 Word）

## 安裝與啟動

```bash
cd ~/ai-pose-pdf-extractor/pdf_to_word_web
python3 -m venv .venv && source .venv/bin/activate     # 建議用虛擬環境
pip install -r requirements.txt
export ANTHROPIC_API_KEY="你的 API key"
python app.py
```

啟動後打開瀏覽器： **http://127.0.0.1:5000**
把 PDF 拖進去，稍候即可下載同名的 `.docx`。

## 運作原理

每一頁先渲染成高解析圖，交給 Claude（`claude-opus-4-8`，支援高解析視覺）判讀，
回傳「依閱讀順序排列的區塊」：
- 文字區塊 → 逐字轉錄後寫進 Word 段落
- 圖片區塊 → Claude 給出位置框 (bbox)，後端從原頁裁切該圖並嵌入 Word

## 調整

在 `app.py` 最上方：
- `RENDER_DPI`（預設 200）：調高圖更清楚但更慢/更貴
- `MAX_IMG_WIDTH_IN`（預設 6.0）：Word 內嵌圖片的最大寬度（英吋）
- `MODEL`：使用的模型

## 注意

- 需要有 `ANTHROPIC_API_KEY`，每頁會呼叫一次 API（掃描頁屬圖片輸入，token 成本較高）。
- 這是本機工具（只監聽 127.0.0.1），API key 不會外洩到前端。
- 頁數多時處理時間較長；bbox 裁切為 v1 版本，位置可能略有誤差。
