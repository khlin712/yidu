# 譯讀 Yidu

將英文 EPUB／PDF 翻譯成台灣繁體中文 EPUB，並在全書翻譯前確認術語，避免同一概念在不同章節漂移成不同譯法。

專案網站：<https://khlin712.github.io/yidu/>

## 最簡單的使用方式：從 Codex 安裝

在 Codex 對話中輸入：

```text
$skill-installer https://github.com/khlin712/yidu/tree/main/skills/yidu
```

安裝完成後，在下一個 Codex turn 使用：

```text
$yidu 翻譯這本 EPUB 成台灣繁中
```

或：

```text
$yidu 把這份 PDF 翻成台灣繁中 EPUB
```

也可以直接用自然語言。第一次使用時，Yidu 會自動建立固定版本的
Python runtime。EPUB 只準備基本依賴；PDF 會另外準備 Docling、PyTorch、
OCR、pypdfium2 與 Pandoc。你不需要另外研究 `pip`、虛擬環境或 Pandoc
設定。PDF 依賴較大，首次下載可能需要一些時間與磁碟空間。

依賴只會寫入使用者自己的 Codex runtime：

```text
$CODEX_HOME/runtimes/yidu/<upstream-commit>/
```

不會修改系統 Python、不會使用 `sudo`，也不會把 Pandoc 永久加入系統
PATH。若需要檢查目前 runtime：

```bash
python ~/.codex/skills/yidu/scripts/ensure_runtime.py \
  --book /path/to/book.pdf \
  --check
```

## 支援內容

- EPUB → 台灣繁中 EPUB
- PDF → 可重排的台灣繁中 EPUB
- 純繁中輸出（預設）或中英雙語輸出
- Codex 訂閱翻譯路徑
- 每本書專屬術語表與互動確認
- 翻譯中斷後續跑
- 翻譯後 EPUB 結構與術語一致性檢查
- 掃描 PDF 的 OCR 警告與英文 OCR 設定

PDF 會轉成可重排 EPUB，不承諾保留原始 PDF 的逐頁版面。圖片中的文字、
公式圖片與複雜版面可能需要人工處理。

## 翻譯前的術語確認

Yidu 會先提出容易漂移的候選術語，讓使用者確認譯法。例如：

```text
social self-efficacy → 社會自我效能
```

一旦確認，同一詞義不可在其他章節改成「社交自我效能」。不同語境的不同
詞義則分開管理。

## 手動安裝

將 `skills/yidu` 複製到自己的 Codex skills 目錄：

```text
$CODEX_HOME/skills/yidu
```

若沒有設定 `CODEX_HOME`，通常是：

```text
~/.codex/skills/yidu
```

安裝 skill 本身不會執行系統安裝；第一次呼叫 `$yidu` 時才會由內建
bootstrap 準備專用 runtime。這是為了避免只翻 EPUB 的使用者也被迫下載
大型 PDF 套件。

Codex skill 使用每位使用者自己的登入狀態與額度；本專案不包含 API key、
書籍內容或翻譯成果。

## 翻譯引擎與固定版本

Yidu 使用 [`yihong0618/bilingual_book_maker`](https://github.com/yihong0618/bilingual_book_maker)
作為底層翻譯引擎，固定使用已檢視的 upstream commit：

```text
e1027a4823e98f668ef950740b6f805ec30bd3b2
```

PDF runtime 使用固定版本 Pandoc 3.1.12；若使用者已有符合版本的 Pandoc，
Yidu 會重用它，否則下載到自己的 runtime 目錄。

## 版權與使用限制

請只翻譯你有權處理的內容。Yidu 不移除 DRM，也不應用來繞過加密或散布未經授權的翻譯書籍。翻譯結果仍需人工檢查，不是出版級定稿。

## 開發與授權

本專案採 MIT License。第三方資訊請見 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
