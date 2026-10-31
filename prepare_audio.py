#!/usr/bin/env python3
"""
prepare_audio.py — 把現有音檔整理成網站可以用的格式，並更新 index.html 裡的預設卡片清單

功能
  1. 把 .wav / .3gp / .m4a / .mp3 ... 統一轉成 16-bit 單聲道 .wav（瀏覽器無法播放 .3gp）
  2. 檔名轉成小寫並去掉不合法字元（QR code 內容 = 檔名去掉副檔名）
  3. 更新 index.html 裡的「預設卡片清單」（保留你已經寫好的文字訊息）
  4. 可用 CSV 一次設定所有文字訊息
  5. 可把 APP 匯出的備份檔（aac-backup-*.json）解開，放進網站成為預設卡片

用法（本檔放在 aac-app 資料夾旁邊，或用 --app 指定 aac-app 資料夾）
  python prepare_audio.py 我的音檔資料夾
  python prepare_audio.py 我的音檔資料夾 --texts texts.csv
  python prepare_audio.py --from-backup aac-backup-20261031.json
  python prepare_audio.py --texts texts.csv              （只更新文字，不重新處理音檔）
  python prepare_audio.py --merge-from 舊的index.html     （換新版 index.html 時保留卡片清單）

texts.csv 格式（UTF-8，第一列是標題）：
  name,text
  help,我需要幫忙
  eat,我想吃東西

轉檔需要 ffmpeg（https://ffmpeg.org/）。沒有 ffmpeg 時，只會複製本來就是 16-bit PCM 的 .wav。
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_DIR = HERE / "aac-app" if (HERE / "aac-app" / "index.html").is_file() else HERE
INDEX_PATH = APP_DIR / "index.html"
AUDIO_DIR = APP_DIR / "audio"
VOCAB_BLOCK = re.compile(
    r'(<script type="application/json" id="vocab-data">)(.*?)(</script>)', re.S)
AUDIO_EXTS = {".wav", ".3gp", ".amr", ".m4a", ".mp3", ".aac", ".ogg", ".webm", ".flac", ".mp4"}
NAME_RE = re.compile(r"^[\w-]+$")


def clean_name(stem: str) -> str:
    s = stem.strip().lower().replace(" ", "_").replace("\u3000", "_")
    return re.sub(r"[^\w-]", "", s)          # 保留英文、中文、數字、_ 和 -


def is_pcm16(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getsampwidth() == 2 and w.getcomptype() == "NONE"
    except Exception:
        return False


def convert(src: Path, dst: Path, ffmpeg: str | None) -> bool:
    if ffmpeg:
        cmd = [ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-i", str(src),
               "-ac", "1", "-c:a", "pcm_s16le", str(dst)]
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            print(f"  ✗ 轉檔失敗 {src.name}: {r.stderr.strip()[:200]}")
            return False
        return True
    if src.suffix.lower() == ".wav" and is_pcm16(src):
        shutil.copy2(src, dst)
        return True
    print(f"  ✗ 略過 {src.name}：需要 ffmpeg 才能轉換這個格式")
    return False


def read_index() -> str:
    if not INDEX_PATH.is_file():
        sys.exit(f"找不到 {INDEX_PATH}，請用 --app 指定 aac-app 資料夾")
    return INDEX_PATH.read_text(encoding="utf-8")


def load_vocab() -> dict:
    m = VOCAB_BLOCK.search(read_index())
    if not m:
        sys.exit("index.html 裡找不到預設卡片清單（id=\"vocab-data\"）")
    text = m.group(2).strip()
    return json.loads(text) if text else {}


def save_vocab(vocab: dict) -> None:
    ordered = vocab                                # 保留原本順序（新卡片接在最後）
    lines = [f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}' for k, v in ordered.items()]
    body = "{\n" + ",\n".join(lines) + "\n}"
    body = body.replace("</", "<\\/")          # 避免文字中出現 </script>
    html = read_index()
    html = VOCAB_BLOCK.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(3), html, count=1)
    INDEX_PATH.write_text(html, encoding="utf-8")


def same_text(a: str, b: str) -> bool:
    norm = lambda x: re.sub(r"\s+", "", x or "").lower()
    return norm(a) == norm(b)


def find_card_by_text(vocab: dict, text: str, exclude: str = "") -> str | None:
    """找文字訊息相同的既有卡片（例如 QR 內容是「我不要」的卡片）"""
    for k, v in vocab.items():
        if k != exclude and same_text(v.get("text", k), text):
            return k
    return None


def load_texts(csv_path: Path) -> dict:
    texts = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = clean_name(row.get("name", ""))
            text = (row.get("text") or "").strip()
            if name and text:
                texts[name] = text
    return texts


def import_folder(src_dir: Path, texts: dict) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("⚠ 找不到 ffmpeg：只能處理 16-bit PCM 的 .wav，其他格式會被略過。")

    AUDIO_DIR.mkdir(exist_ok=True)
    vocab = load_vocab()
    files = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS)
    if not files:
        sys.exit(f"在 {src_dir} 裡找不到音檔")

    seen = {}
    for src in files:
        name = clean_name(src.stem)
        if not name:
            print(f"  ✗ 略過 {src.name}：檔名需要包含文字或數字")
            continue
        if name in seen:
            print(f"  ✗ 略過 {src.name}：和 {seen[name]} 轉換後同名（{name}）")
            continue
        seen[name] = src.name

        dst = AUDIO_DIR / f"{name}.wav"
        # Windows 不分大小寫：I_want.wav 和 i_want.wav 是同一個檔案，要就地轉檔再改名
        same_file = dst.exists() and src.samefile(dst)
        if same_file:
            tmp = dst.with_name(f"__tmp__{name}.wav")
            ok = convert(src, tmp, ffmpeg)
            if ok:
                src.unlink()
                tmp.rename(dst)          # 改成小寫檔名（GitHub 網址分大小寫）
        else:
            ok = convert(src, dst, ffmpeg)
        if not ok:
            continue

        note = "" if src.stem == name else f"（原檔名 {src.name}）"
        text = texts.get(name)
        # 如果已經有文字相同的卡片（例如中文 QR 卡「我不要」），就把音檔接到那張卡片上
        target = name if name in vocab else (find_card_by_text(vocab, text) if text else None)
        if target and target != name:
            vocab[target]["file"] = dst.name
            print(f"  ✓ {src.name:<16} → 卡片「{vocab[target]['text']}」{note}")
            continue

        entry = vocab.get(name, {})
        entry["file"] = dst.name
        if text:
            entry["text"] = text
        entry.setdefault("text", name)
        vocab[name] = entry
        print(f"  ✓ {name:<16} {entry['text']}{note}")

    save_vocab(vocab)
    report(vocab)


def import_backup(backup_path: Path) -> None:
    with open(backup_path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("app") != "aac-qr":
        sys.exit("這不是 AAC APP 的備份檔")

    AUDIO_DIR.mkdir(exist_ok=True)
    vocab = load_vocab()
    for name, v in (data.get("vocab") or {}).items():
        vocab.setdefault(name, {})["text"] = v.get("text", name)
    for name, data_url in (data.get("audio") or {}).items():
        b64 = data_url.split(",", 1)[1]
        dst = AUDIO_DIR / f"{name}.wav"
        dst.write_bytes(base64.b64decode(b64))
        vocab.setdefault(name, {"text": name})["file"] = dst.name
        print(f"  ✓ {name:<16} {vocab[name].get('text', '')}")
    save_vocab(vocab)
    report(vocab)


def merge_from(old_index: Path) -> None:
    """把舊版 index.html 的預設卡片清單搬到新版 index.html"""
    m = VOCAB_BLOCK.search(old_index.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"{old_index} 裡找不到預設卡片清單")
    old = json.loads(m.group(2).strip() or "{}")
    vocab = load_vocab()
    for k, v in old.items():
        same = find_card_by_text(vocab, v.get("text", k), exclude=k)
        if k not in vocab and same:
            # 文字相同的卡片已存在：只把音檔接過去，不重複新增
            if v.get("file") and not (AUDIO_DIR / vocab[same].get("file", "")).is_file():
                vocab[same]["file"] = v["file"]
            print(f"  ✓ {k:<16} 併入卡片「{vocab[same]['text']}」")
        else:
            vocab[k] = v
    save_vocab(vocab)
    print(f"  ✓ 從 {old_index.name} 搬入 {len(old)} 張卡片")
    report(vocab)


def apply_texts(texts: dict) -> None:
    """只更新文字訊息，不處理音檔"""
    vocab = load_vocab()
    for name, text in texts.items():
        same = find_card_by_text(vocab, text, exclude=name)
        if name in vocab and same:
            # 例如 no 的文字改成「我不要」，而「我不要」卡片已存在 → 合併成一張
            if vocab[name].get("file"):
                vocab[same]["file"] = vocab[name]["file"]
            del vocab[name]
            print(f"  ✓ {name:<16} 併入卡片「{text}」")
        elif name in vocab:
            vocab[name]["text"] = text
            print(f"  ✓ {name:<16} {text}")
        else:
            print(f"  ✗ {name}：清單裡沒有這張卡片（請先放入同名音檔）")
    save_vocab(vocab)
    report(vocab)


def report(vocab: dict) -> None:
    missing_text = [k for k, v in vocab.items() if v.get("text", k) == k and k.isascii()]
    missing_file = [k for k, v in vocab.items() if not (AUDIO_DIR / v.get("file", "")).is_file()]
    bad_names = [k for k in vocab if not NAME_RE.match(k)]
    print(f"\n預設卡片清單共 {len(vocab)} 張 → 已寫入 {INDEX_PATH}")
    if missing_text:
        print(f"⚠ 以下卡片的文字訊息還是英文名稱，請在 texts.csv 或 index.html 的預設卡片清單裡補上：\n  {', '.join(missing_text)}")
    if missing_file:
        print(f"⚠ 以下卡片在 audio/ 裡找不到音檔：\n  {', '.join(missing_file)}")
    if bad_names:
        print(f"⚠ 以下名稱含不合法字元：{', '.join(bad_names)}")
    print("\n記得把 sw.js 裡的 VERSION 數字加 1，再把 index.html、sw.js、audio/ 上傳到 GitHub。")


def main() -> None:
    ap = argparse.ArgumentParser(description="整理 AAC APP 的音檔並更新 index.html 的預設卡片清單")
    ap.add_argument("src", nargs="?", type=Path, help="你的音檔資料夾")
    ap.add_argument("--texts", type=Path, help="name,text 的 CSV 檔，用來設定文字訊息")
    ap.add_argument("--from-backup", type=Path, help="APP 匯出的備份檔 (.json)")
    ap.add_argument("--app", type=Path, help="aac-app 資料夾（含 index.html）")
    ap.add_argument("--merge-from", type=Path, help="舊版 index.html：把它的卡片清單搬到新版")
    args = ap.parse_args()

    global APP_DIR, INDEX_PATH, AUDIO_DIR
    if args.app:
        APP_DIR = args.app.resolve()
        INDEX_PATH = APP_DIR / "index.html"
        AUDIO_DIR = APP_DIR / "audio"

    if args.merge_from:
        merge_from(args.merge_from)
    elif args.from_backup:
        import_backup(args.from_backup)
    elif args.src:
        texts = load_texts(args.texts) if args.texts else {}
        import_folder(args.src, texts)
    elif args.texts:
        apply_texts(load_texts(args.texts))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
