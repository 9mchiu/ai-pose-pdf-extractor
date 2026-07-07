#!/usr/bin/env python3
"""
AI 3D 姿勢檢測報告 — 掃描版 PDF 數據萃取工具
============================================

用途:
    把一整個資料夾的（掃描版 / 圖片為主的）PDF 報告丟給 Claude，
    自動「看」每一頁（含 OCR + 讀圖表），抽出數據指標
    (MPJPE、FPS、精度…) 成結構化資料，輸出成 JSON + CSV。

做法:
    - 用 Claude 原生 PDF/視覺能力，掃描版也能讀（不需另外裝 OCR）。
    - 用 Files API 上傳 PDF（支援大檔、避免 base64 膨脹）。
    - 用結構化輸出 (output_config.format) 確保回傳是乾淨可解析的 JSON。

使用:
    1. pip install -r requirements.txt
    2. export ANTHROPIC_API_KEY="你的 API key"
    3. 把 PDF 放進 ./pdfs 資料夾
    4. python extract_pose_metrics.py
    輸出: ./output/results.json  與  ./output/metrics.csv
"""

import os
import sys
import json
import csv
import glob

import anthropic

# ────────────────────────────── 設定 ──────────────────────────────
MODEL = "claude-opus-4-8"          # 支援視覺 + PDF、1M context
INPUT_DIR = "pdfs"                  # 放 PDF 的資料夾
OUTPUT_DIR = "output"              # 輸出資料夾
FILES_BETA = "files-api-2025-04-14"

# 抽取結果的結構 (JSON Schema)。value 用字串以容納 "45.2"、"45.2 ± 1.3"、"30-35" 等格式。
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "report_title": {"type": "string", "description": "報告 / 論文標題"},
        "summary": {"type": "string", "description": "一兩句話總結這份報告在做什麼"},
        "datasets": {
            "type": "array",
            "items": {"type": "string"},
            "description": "報告中用到的資料集名稱 (如 Human3.6M, MPI-INF-3DHP)",
        },
        "methods": {
            "type": "array",
            "items": {"type": "string"},
            "description": "報告中評估 / 比較的方法或模型名稱",
        },
        "metrics": {
            "type": "array",
            "description": "從表格與圖表中抽出的每一筆數據指標",
            "items": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "此數值對應的方法/模型；未知填 N/A"},
                    "dataset": {"type": "string", "description": "此數值對應的資料集；未知填 N/A"},
                    "metric_name": {"type": "string", "description": "指標名稱，如 MPJPE / PA-MPJPE / FPS / Accuracy"},
                    "value": {"type": "string", "description": "數值，原樣保留 (可含 ± 或範圍)"},
                    "unit": {"type": "string", "description": "單位，如 mm / fps / % ；無單位填 N/A"},
                    "source_page": {"type": "string", "description": "此數值出現的頁碼；不確定填 N/A"},
                    "notes": {"type": "string", "description": "補充說明，如來自哪個表/圖；沒有填 N/A"},
                },
                "required": ["method", "dataset", "metric_name", "value", "unit", "source_page", "notes"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["report_title", "summary", "datasets", "methods", "metrics"],
    "additionalProperties": False,
}

PROMPT = """你是一位專門判讀 AI 3D 姿勢檢測 (3D human pose estimation) 報告的分析助手。

這是一份掃描版 PDF，請逐頁仔細閱讀（含表格與圖表中的數字），抽出所有「數據指標」。

要求:
- 只抽取文件中「實際出現」的數值，不要自己推算或編造。
- 特別注意這類指標: MPJPE、PA-MPJPE、N-MPJPE、Accuracy、Precision、Recall、FPS、推論時間、參數量等。
- 一個「方法 × 資料集 × 指標」對應一筆 metric 紀錄。
- 表格裡每一格數字都盡量抽出來，並標明對應的方法、資料集、頁碼。
- 找不到的欄位一律填 "N/A"，不要留空。
- 標題、資料集、方法名稱請盡量用文件中的原文。

請依指定的 JSON 結構輸出。"""


def eprint(*args):
    print(*args, file=sys.stderr, flush=True)


def extract_one(client: anthropic.Anthropic, pdf_path: str) -> dict:
    """上傳單一 PDF 並回傳結構化萃取結果 (dict)。"""
    fname = os.path.basename(pdf_path)
    eprint(f"  → 上傳 {fname} ...")
    with open(pdf_path, "rb") as f:
        uploaded = client.beta.files.upload(
            file=(fname, f, "application/pdf"),
            betas=[FILES_BETA],
        )

    eprint(f"  → Claude 判讀中 (可能需數十秒) ...")
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=[FILES_BETA],
        thinking={"type": "adaptive"},          # 讓模型仔細判讀噪點多的掃描頁
        output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "document", "source": {"type": "file", "file_id": uploaded.id}},
            ],
        }],
    )

    # 結構化輸出保證第一個 text block 是合法 JSON
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if text is None:
        raise RuntimeError("模型未回傳文字內容")
    data = json.loads(text)
    data["_source_file"] = fname
    n = len(data.get("metrics", []))
    eprint(f"  ✓ 完成: 抽到 {n} 筆指標")
    return data


def write_csv(all_results: list, csv_path: str):
    """把所有報告的 metrics 攤平成一張可跨報告比較的 CSV。"""
    cols = ["source_file", "report_title", "method", "dataset",
            "metric_name", "value", "unit", "source_page", "notes"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig 讓 Excel 正確顯示中文
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in all_results:
            title = r.get("report_title", "N/A")
            src = r.get("_source_file", "N/A")
            for m in r.get("metrics", []):
                w.writerow({
                    "source_file": src,
                    "report_title": title,
                    "method": m.get("method", "N/A"),
                    "dataset": m.get("dataset", "N/A"),
                    "metric_name": m.get("metric_name", "N/A"),
                    "value": m.get("value", "N/A"),
                    "unit": m.get("unit", "N/A"),
                    "source_page": m.get("source_page", "N/A"),
                    "notes": m.get("notes", "N/A"),
                })


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        eprint("❌ 請先設定環境變數 ANTHROPIC_API_KEY")
        sys.exit(1)

    pdfs = sorted(glob.glob(os.path.join(INPUT_DIR, "*.pdf")) +
                  glob.glob(os.path.join(INPUT_DIR, "*.PDF")))
    if not pdfs:
        eprint(f"❌ 在 ./{INPUT_DIR}/ 找不到任何 PDF，請把報告放進去再執行。")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    client = anthropic.Anthropic()

    eprint(f"共找到 {len(pdfs)} 份 PDF，開始處理…\n")
    all_results = []
    for i, pdf in enumerate(pdfs, 1):
        eprint(f"[{i}/{len(pdfs)}] {os.path.basename(pdf)}")
        try:
            all_results.append(extract_one(client, pdf))
        except Exception as e:                   # 單檔失敗不中斷整批
            eprint(f"  ✗ 失敗: {e}")
            all_results.append({"_source_file": os.path.basename(pdf),
                                "error": str(e), "metrics": []})
        eprint("")

    json_path = os.path.join(OUTPUT_DIR, "results.json")
    csv_path = os.path.join(OUTPUT_DIR, "metrics.csv")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    write_csv(all_results, csv_path)

    total = sum(len(r.get("metrics", [])) for r in all_results)
    eprint("──────────────────────────────")
    eprint(f"✓ 全部完成，共抽出 {total} 筆指標")
    eprint(f"  完整結果: {json_path}")
    eprint(f"  比較表格: {csv_path}")


if __name__ == "__main__":
    main()
