# aac-QRapp
using QR code for AAC html
# AAC 溝通 — QR code 卡片播放器

掃描 QR code 卡片 → 播放對應錄音 → 大字顯示文字訊息。
可在 Android、iPhone、iPad 的瀏覽器使用，也可加到主畫面當成 APP，離線也能用。

## 檔案說明

```
aac-QRapp/            ← 整個上傳到 GitHub
├── index.html      所有程式、外觀、函式庫、圖示、預設卡片清單都在這裡
├── sw.js           離線功能（瀏覽器規定必須是獨立檔案）
└── audio/          預設音檔（.wav）
prepare_audio.py    在電腦上整理音檔用，不需上傳
texts_example.csv   批次設定文字訊息的範例
```

預設卡片清單在 `index.html` 最上方，用記事本或 VS Code 打開就能直接改：

```
"help": {"text": "我需要幫忙", "file": "help.wav"},
```

## 一、把現有的 20 多個音檔放進來

1. 安裝 ffmpeg（Windows 可用 `winget install ffmpeg`；Mac 用 `brew install ffmpeg`）。
   沒有 ffmpeg 也能用，但只能處理 16-bit 的 .wav，`.3gp` 會被略過。
2. 照 `texts_example.csv` 的格式寫一個 `texts.csv`，列出每個音檔名稱和要顯示的文字（存成 UTF-8）。
3. 在 `prepare_audio.py` 所在的資料夾開終端機執行：

   ```
   python prepare_audio.py "D:\我的音檔" --texts texts.csv
   ```

   腳本會：
   - 把 .wav / .3gp / .m4a / .mp3 全部轉成 16-bit 單聲道 .wav，放進 `aac-app/audio/`
   - 檔名轉小寫、空白換成底線（`Go Home.wav` → `go_home.wav`，QR 內容就是 `go_home`）
   - 自動更新 `index.html` 裡的預設卡片清單，已經寫好的文字不會被覆蓋
   - 最後列出還沒填文字或找不到音檔的項目

   如果 `aac-app` 資料夾放在別處，加上 `--app "路徑\aac-app"`。

4. 打開 `sw.js`，把第二行 `const VERSION = 'aac-v1';` 改成 `aac-v2`（之後每次更新都加 1）。

> 原始音檔不會被修改，轉好的檔案另存在 `aac-app/audio/`。

## 二、部署到 GitHub Pages（不需要會用 git）

1. 到 <https://github.com> 註冊或登入。
2. 右上角 **＋ → New repository**
   - Repository name：例如 `aac-app`
   - 選 **Public**（免費帳號的 GitHub Pages 需要公開儲存庫，見下方「隱私提醒」）
   - 按 **Create repository**
3. 在新儲存庫頁面點 **uploading an existing file**。
4. 打開電腦上的 `aac-app` 資料夾，**選取裡面的 `index.html`、`sw.js` 和 `audio` 資料夾**（不是 `aac-app` 資料夾本身），拖進網頁。
5. 下方按 **Commit changes**。
6. 到儲存庫的 **Settings → Pages**：
   - Source 選 **Deploy from a branch**
   - Branch 選 **main**、資料夾選 **/ (root)**，按 **Save**
7. 等 1–2 分鐘，重新整理 Settings → Pages，上方會出現網址：
   `https://你的帳號.github.io/aac-app/`

### 之後要更新

在儲存庫頁面點 **Add file → Upload files**，拖入改過的檔案（同名會直接覆蓋）→ Commit。
記得同時上傳改過 VERSION 的 `sw.js`，使用者的手機重新開啟兩次就會更新。

## 三、在手機上使用

1. 用手機瀏覽器開啟上面的網址（Android 用 Chrome；iPhone 用 Safari）。
2. 加到主畫面：
   - **Android Chrome**：右上角 ⋮ →「加到主畫面」或「安裝應用程式」
   - **iPhone Safari**：下方分享按鈕 →「加入主畫面」
3. 從主畫面圖示開啟，第一次按「開始掃描」時允許使用相機；第一次錄音時允許使用麥克風。

### 使用模式
- 按「開始掃描」→ 對準卡片 → 播放錄音並大字顯示文字
- 勾選「連續掃描」時，相機保持開啟，可以一張接一張掃；同一張卡 3 秒內不會重複觸發
- 「再播一次」重播上一張
- **記憶**：每次掃到的訊息會依序累積在下方的記憶列，可以組成句子
  - 「▶ 記憶播放」：從第一則開始依序播放，正在播的那則會亮起來，播完後上方顯示整句；播放中再按一次就停止
  - 「✕ 清除記憶」：要在 3 秒內連按兩次才會清除，避免誤觸
  - 記憶會一直保留（關掉 APP 再開也在），直到按清除為止，最多保留最近 50 則

### 編輯模式
1. 輸入文字訊息（中英文皆可）
2. 輸入英文名稱（也就是 QR code 的內容）
3. 按「開始錄音」→ 說話 → 「停止錄音」，可用下方播放器試聽；或用「匯入現有音檔」選手機裡的檔案
4. 按「儲存並產生 QR code」→「下載 QR code 圖片」
- 「所有卡片」清單可以試聽、編輯、刪除；「列印全部 QR 卡片」可一次印出所有卡片（每列 3 張）
- 只改文字、不重錄也可以：按「編輯」→ 改文字 → 儲存

## 資料存在哪裡

| 資料 | 位置 | 所有裝置共用？ |
|---|---|---|
| `index.html` 的預設卡片清單 + `audio/` | GitHub 網站 | ✅ 是 |
| 編輯模式新增的文字 | 這台裝置瀏覽器的 localStorage | ❌ 只有這台 |
| 編輯模式錄的音 | 這台裝置瀏覽器的 IndexedDB | ❌ 只有這台 |

- 播放順序：先找這台裝置錄的音，找不到再用網站上的預設音檔。
- 編輯模式的「匯出備份」會下載一個 `.json` 檔，可在另一台裝置「匯入備份」。
- 想讓手機上新錄的卡片變成**所有裝置的預設卡片**：
  ```
  python prepare_audio.py --from-backup aac-backup-20261031.json
  ```
  再把 `audio/`、`index.html`、`sw.js`（VERSION 加 1）上傳到 GitHub。

## 隱私提醒

免費 GitHub Pages 的儲存庫是**公開**的，`audio/` 裡的錄音任何人都能下載。

- 適合上傳：治療師或家長代錄的通用詞彙
- 不建議上傳：個案本人的聲音或可辨識個人身分的內容。這類錄音請在個案的裝置上用編輯模式錄製，只會存在該裝置，不會上傳

## 常見問題

**按掃描沒反應／相機打不開**
網址必須是 `https://`。在 iPhone 請用 Safari；並到系統設定確認瀏覽器有相機權限。

**掃到了但沒聲音**
確認手機不是靜音模式（iPhone 側邊靜音鍵會讓網頁沒有聲音）。按一次「再播一次」。

**`.3gp` 不能播**
瀏覽器不支援 .3gp（AMR）格式，請先用 `prepare_audio.py` 轉成 .wav。手機上用「匯入現有音檔」選 .3gp 也會提示同樣的訊息。

**更新後手機還是舊內容**
確認 `sw.js` 的 VERSION 有改，然後在手機上完全關閉 APP 再開啟兩次。

**電腦上測試**
在 `aac-app` 資料夾執行 `python -m http.server 8000`（直接雙擊 index.html 開啟無法使用鏡頭），用電腦瀏覽器開 `http://localhost:8000`（localhost 允許使用鏡頭）。
