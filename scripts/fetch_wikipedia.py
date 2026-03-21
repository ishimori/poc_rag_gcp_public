"""Wikipedia日本語版から記事を取得し、test-data/sources/wikipedia/ に保存する"""

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

OUTPUT_DIR = "test-data/sources/wikipedia"

# 取得する記事タイトル（カテゴリ別）
ARTICLES = {
    "metal_material": [
        "ステンレス鋼",
        "SUS304",
        "SUS316",
        "クロムモリブデン鋼",
        "炭素鋼",
        "オーステナイト",
        "マルテンサイト",
        "電食",
        "不動態",
        "焼入れ",
    ],
    "mechanical": [
        "ボルト (部品)",
        "ナット (部品)",
        "座金",
        "トルク",
        "公差",
        "ねじ",
        "六角穴付きボルト",
        "転がり軸受",
        "表面粗さ",
        "硬さ",
    ],
    "it_network": [
        "Virtual Private Network",
        "ファイアウォール",
        "Active Directory",
        "多要素認証",
        "情報セキュリティ",
        "マルウェア",
        "フィッシング (詐欺)",
        "SSID",
        "WPA3",
        "ゼロトラスト",
    ],
    "labor_law": [
        "年次有給休暇",
        "労働基準法",
        "就業規則",
        "社会保険",
        "雇用保険",
    ],
    "accounting": [
        "経費",
        "領収書",
        "減価償却",
        "勘定科目",
        "法人税",
    ],
    "manufacturing": [
        "品質管理",
        "ISO 9001",
        "抜取検査",
        "ロックウェル硬さ",
        "マイクロメータ",
        "ノギス",
        "熱処理",
        "めっき",
        "陽極酸化",
        "旋盤",
    ],
    "it_extra": [
        "パスワード",
        "ランサムウェア",
        "インシデント管理",
        "バックアップ",
        "クラウドコンピューティング",
    ],
}

WIKI_API = "https://ja.wikipedia.org/w/api.php"


def fetch_article(title: str) -> str | None:
    """Wikipedia API で記事本文を取得（プレーンテキスト）"""
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": True,
        "format": "json",
    }
    headers = {
        "User-Agent": "RAGPoCBot/1.0 (test data collection; contact@example.com)",
    }
    try:
        resp = requests.get(WIKI_API, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        pages = resp.json()["query"]["pages"]
        for page in pages.values():
            if "extract" in page:
                return page["extract"]
    except Exception as e:
        print(f"  [WARN] Failed to fetch '{title}': {e}")
    return None


def text_to_markdown(title: str, text: str) -> str:
    """プレーンテキストを簡易 Markdown に変換"""
    lines = text.split("\n")
    md_lines = [f"# {title}", ""]

    for line in lines:
        line = line.strip()
        if not line:
            md_lines.append("")
            continue
        # == Section == → ## Section
        m = re.match(r"^(=+)\s*(.+?)\s*=+$", line)
        if m:
            level = min(len(m.group(1)), 4)
            md_lines.append(f"{'#' * (level + 1)} {m.group(2)}")
        else:
            md_lines.append(line)

    return "\n".join(md_lines)


def sanitize_filename(title: str) -> str:
    """ファイル名に使えない文字を除去"""
    name = title.replace(" ", "_").replace("/", "_").replace("\\", "_")
    name = re.sub(r"[^\w\-\u3000-\u9fff\uff00-\uffef]", "", name)
    return name


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total = sum(len(v) for v in ARTICLES.values())
    fetched = 0
    skipped = 0

    for category, titles in ARTICLES.items():
        print(f"\n--- Category: {category} ({len(titles)} articles) ---")
        for title in titles:
            fname = sanitize_filename(title)
            out_path = os.path.join(OUTPUT_DIR, f"{fname}.md")

            if os.path.exists(out_path):
                print(f"  [SKIP] {title} (already exists)")
                skipped += 1
                continue

            text = fetch_article(title)
            if not text:
                print(f"  [MISS] {title} (not found)")
                skipped += 1
                continue

            # 長すぎる記事は先頭部分のみ
            if len(text) > 8000:
                text = text[:8000] + "\n\n（以下省略）"

            md = text_to_markdown(title, text)

            # frontmatter 追加
            content = f"---\ncategory: wikipedia\nsecurity_level: public\nallowed_groups: [\"all\"]\n---\n\n{md}\n"

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)

            fetched += 1
            print(f"  [OK] {title} → {fname}.md ({len(md)} chars)")

            time.sleep(0.5)  # API rate limiting

    print(f"\n=== Summary ===")
    print(f"Total: {total}, Fetched: {fetched}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
