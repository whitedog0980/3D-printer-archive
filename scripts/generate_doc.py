#!/usr/bin/env python3
"""
GitHub Actions 전용 스크립트.
환경변수:
  ANTHROPIC_API_KEY   - 필수
  ISSUE_TITLE         - 이슈 제목
  ISSUE_BODY_PATH     - 이슈 본문이 저장된 파일 경로
  GITHUB_OUTPUT       - Actions가 자동으로 세팅 (step output 기록용)

동작:
  1. 이슈 본문에서 카테고리 드롭다운 값과 메모, 이미지 URL을 파싱한다.
  2. 이미지 다운로드 후 리사이즈/webp 변환.
  3. docs/<category>/ 안의 기존 문서를 few-shot 예시로 모아 Claude에 요청.
  4. 결과를 docs/<category>/<slug>.md, asset/<category>/<slug>/ 에 저장.
  5. README.md 의 Recent Troubleshooting Summary 표에 새 행 삽입.
  6. category / slug / filename / status 를 GITHUB_OUTPUT 에 기록.

git add/commit/push, PR 생성은 워크플로우 yml에서 처리하고
이 스크립트는 파일만 만든다.
"""

import base64
import datetime
import mimetypes
import os
import re
import sys
from pathlib import Path

import requests

try:
    import anthropic
except ImportError:
    sys.exit("anthropic 패키지 필요")

try:
    from PIL import Image
except ImportError:
    sys.exit("pillow 패키지 필요")

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
PROMPTS_DIR = REPO_ROOT / "prompts"
DOCS_DIR = REPO_ROOT / "docs"
ASSETS_DIR = REPO_ROOT / "asset"  # 실제 레포 폴더명이 단수 "asset" 이므로 맞춤

CATEGORIES = ["troubleshooting", "quality", "maintenance", "parts"]
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_IMAGE_WIDTH = 1600
MAX_FEWSHOT_DOCS_PER_CATEGORY = 2

IMG_MD_RE = re.compile(r"!\[[^\]]*\]\((https?://[^\)\s]+)\)")


def write_output(key: str, value: str):
    out_path = os.environ.get("GITHUB_OUTPUT")
    line = f"{key}={value}"
    if out_path:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    else:
        print(line)


def slugify(name: str) -> str:
    name = re.sub(r"[^\w\-가-힣]+", "-", name.strip())
    return re.sub(r"-{2,}", "-", name).strip("-").lower()


def parse_issue_body(body: str):
    """이슈 폼(log-entry.yml)의 출력 형식을 파싱.
    GitHub 폼은 대략:
      ### 카테고리
      auto
      ### 메모
      ...(자유 텍스트, 이미지 마크다운 포함)...
    형태로 렌더링된다.
    """
    category = "auto"
    cat_match = re.search(r"###\s*카테고리\s*\n+\s*([a-z]+)", body, re.IGNORECASE)
    if cat_match:
        val = cat_match.group(1).strip().lower()
        if val in CATEGORIES or val == "auto":
            category = val

    notes_match = re.search(r"###\s*메모\s*\n+(.*)", body, re.DOTALL)
    notes = notes_match.group(1).strip() if notes_match else body.strip()

    image_urls = IMG_MD_RE.findall(body)
    return category, notes, image_urls


def download_and_optimize_images(urls, tmp_category: str, slug: str):
    saved = []
    for i, url in enumerate(urls, start=1):
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[warn] 이미지 다운로드 실패: {url} ({e})")
            continue
        tmp_raw = Path(f"/tmp/raw_img_{i}")
        tmp_raw.write_bytes(resp.content)
        dst = ASSETS_DIR / tmp_category / slug / f"img{i}.webp"
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            img = Image.open(tmp_raw).convert("RGB")
            if img.width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / img.width
                img = img.resize((MAX_IMAGE_WIDTH, int(img.height * ratio)))
            img.save(dst, "WEBP", quality=80)
            saved.append(dst)
        except Exception as e:
            print(f"[warn] 이미지 변환 실패: {url} ({e})")
    return saved


def image_to_content_block(path: Path):
    mime, _ = mimetypes.guess_type(str(path))
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": mime or "image/webp", "data": data}}


def collect_fewshot_examples() -> str:
    chunks = []
    if DOCS_DIR.exists():
        for cat in CATEGORIES:
            cat_dir = DOCS_DIR / cat
            if not cat_dir.exists():
                continue
            for f in sorted(cat_dir.glob("*.md"))[:MAX_FEWSHOT_DOCS_PER_CATEGORY]:
                chunks.append(f"### [{cat}] {f.name}\n\n{f.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(chunks) if chunks else "(아직 참고할 과거 문서가 없습니다.)"


def build_system_prompt() -> str:
    base = (PROMPTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    templates_text = "\n\n".join(
        f"### {cat} 템플릿\n```\n{(TEMPLATES_DIR / f'{cat}.md').read_text(encoding='utf-8')}\n```"
        for cat in CATEGORIES
    )
    return base.replace("{{few_shot_examples}}", collect_fewshot_examples()) + "\n\n" + templates_text


def insert_readme_row(readme_row: str):
    readme_path = REPO_ROOT / "README.md"
    if not readme_path.exists() or not readme_row:
        return
    content = readme_path.read_text(encoding="utf-8")
    # 헤더 구분선(| --- | --- | ...) 바로 다음 줄에 새 행 삽입
    sep_pattern = re.compile(r"(\|[\s\-|]+\|\n)")
    m = sep_pattern.search(content)
    if not m:
        return
    insert_at = m.end()
    new_content = content[:insert_at] + readme_row.strip() + "\n" + content[insert_at:]
    readme_path.write_text(new_content, encoding="utf-8")


def main():
    issue_title = os.environ.get("ISSUE_TITLE", "").strip()
    body_path = os.environ.get("ISSUE_BODY_PATH")
    if not body_path or not Path(body_path).exists():
        write_output("status", "error")
        sys.exit("이슈 본문 파일을 찾을 수 없습니다.")

    body = Path(body_path).read_text(encoding="utf-8")
    forced_category, notes, image_urls = parse_issue_body(body)

    today = datetime.date.today().isoformat()
    title_for_slug = issue_title.replace("[log]", "").strip() or "entry"
    slug = f"{today}-{slugify(title_for_slug)}"[:80]

    tmp_category = forced_category if forced_category in CATEGORIES else "_uncategorized"
    optimized_images = download_and_optimize_images(image_urls, tmp_category, slug)

    client = anthropic.Anthropic()
    system_prompt = build_system_prompt()

    user_content = [
        {
            "type": "text",
            "text": (
                f"오늘 날짜: {today}\n"
                f"이슈 제목: {issue_title}\n"
                f"슬러그: {slug}\n"
                f"카테고리 강제 지정: {forced_category}\n\n"
                f"--- 메모 원문 ---\n{notes}\n\n"
                f"(이미지 {len(optimized_images)}장 첨부됨. 파일 경로 규칙: "
                f"../../asset/<category>/{slug}/imgN.webp)"
            ),
        }
    ]
    for p in optimized_images:
        user_content.append(image_to_content_block(p))

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        print(f"[error] Claude API 호출 실패: {e}")
        write_output("status", "error")
        sys.exit(1)

    output_text = "".join(block.text for block in response.content if block.type == "text")

    readme_row = ""
    body_lines = []
    for line in output_text.splitlines():
        if line.strip().startswith("README_ROW:"):
            readme_row = line.split("README_ROW:", 1)[1].strip()
        else:
            body_lines.append(line)
    doc_body = "\n".join(body_lines).strip()

    m = re.search(r"docs/([a-z]+)/", readme_row)
    resolved_category = m.group(1) if m else (forced_category if forced_category in CATEGORIES else "troubleshooting")

    if tmp_category == "_uncategorized" and resolved_category != "_uncategorized":
        old_dir = ASSETS_DIR / "_uncategorized" / slug
        new_dir = ASSETS_DIR / resolved_category / slug
        if old_dir.exists():
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            old_dir.rename(new_dir)
            doc_body = doc_body.replace(f"asset/_uncategorized/{slug}/", f"asset/{resolved_category}/{slug}/")
            readme_row = readme_row.replace(f"asset/_uncategorized/{slug}/", f"asset/{resolved_category}/{slug}/")

    doc_dir = DOCS_DIR / resolved_category
    doc_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}.md"
    (doc_dir / filename).write_text(doc_body + "\n", encoding="utf-8")

    insert_readme_row(readme_row)

    write_output("status", "ok")
    write_output("category", resolved_category)
    write_output("slug", slug)
    write_output("filename", filename)

    print(f"[완료] docs/{resolved_category}/{filename} 생성")
    print(f"[README 행] {readme_row}")


if __name__ == "__main__":
    main()
