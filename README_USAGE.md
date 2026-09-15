# AI 문서화 워크플로우 (Issue → PR 자동화)

## 흐름

```
1. GitHub 이슈 생성 (템플릿 "3D 프린터 기록 (자동 문서화)" 사용)
   - 카테고리 선택 (auto 가능)
   - 메모 작성 + 사진은 텍스트박스에 드래그 앤 드롭

2. 이슈가 열리면 GitHub Action이 자동 실행:
   - 이슈 본문 파싱 (카테고리 / 메모 / 이미지 URL)
   - 이미지 다운로드 → 리사이즈/webp 변환 → asset/<category>/<slug>/
   - Claude API 호출 → docs/<category>/<slug>.md 생성
   - README.md 요약 표에 새 행 자동 삽입
   - 새 브랜치 커밋 + PR 오픈 (원본 이슈에 링크, "Closes #N")

3. PR을 검토하고 머지
   → 머지 커밋이 곧 "잔디"가 됨. 초안 내용에 개입할 필요 없음.
   → 마음에 안 들면 PR에서 직접 수정하거나, Close 후 이슈 다시 작성.
```

## 레포에 넣을 파일

이 zip 안의 아래 구조를 레포 루트에 그대로 복사하세요.

```
your-repo/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   └── log-entry.yml
│   └── workflows/
│       └── generate-doc.yml
├── templates/            (4종 카테고리 템플릿)
├── prompts/
│   └── system_prompt.md
└── scripts/
    ├── generate_doc.py
    └── requirements.txt
```

## 최초 설정 (한 번만)

1. Anthropic API 키 발급 (console.anthropic.com)
2. 레포 → Settings → Secrets and variables → Actions →
   `ANTHROPIC_API_KEY` 이름으로 New repository secret 등록
3. 레포 → Settings → Actions → General →
   "Workflow permissions"를 Read and write permissions로 변경
   (Action이 브랜치를 push하고 PR을 열어야 하므로 필요)
4. Settings → Actions → General → 아래에서
   "Allow GitHub Actions to create and approve pull requests" 체크

이후로는 별도 설치나 로컬 실행이 전혀 필요 없습니다. 이슈만 쓰면 됩니다.

## 사용 예시

이슈 제목: `[log] 노즐 클로그 이슈`
카테고리: `auto`
메모:
```
노즐이 자꾸 막혀서 출력이 중간에 끊김
PLA, 210도, 압출 안됨
콜드풀로 뚫었더니 해결됨
아마 필라멘트에 먼지 낀 것 같음
```
(사진 2장 드래그 앤 드롭)

→ 몇 분 뒤 PR이 자동으로 열림 → 확인 후 Merge 버튼 클릭 → 끝.

## 왜 검수를 초안이 아니라 PR 머지로만 하는가

- 초안 문장 하나하나를 고칠 필요 없이, "이 기록을 남길지 말지"만 결정하면 됨
- PR 안에서 직접 파일을 수정(GitHub 웹 에디터)한 뒤 머지하는 것도 가능 — 그 경우도 여전히 "머지"가 최종 승인 지점
- 마음에 안 들면 그냥 PR을 닫고 이슈에 코멘트로 다시 요청하면 됨

## 기록이 쌓일수록 좋아지는 이유

`generate_doc.py`는 `docs/<category>/` 안에 이미 존재하는 문서를 카테고리당 최대 2개씩
few-shot 예시로 자동으로 읽어 Claude에 전달합니다. PR을 머지해서 실제 문서가 쌓일수록,
다음 초안의 문체가 점점 더 실제 스타일에 수렴합니다.

## 참고사항

- 이미지가 없는 메모만으로도 정상 동작합니다.
- 카테고리를 auto가 아니라 직접 지정하면 그 값을 강제로 사용합니다 (분류 실패 방지용).
- 워크플로우가 실패하면(예: API 키 누락) 원본 이슈에 실패 코멘트가 자동으로 남습니다.
- 커밋 잔디를 매일 쌓고 싶다면, 짧은 메모라도 그날그날 이슈로 남기고 바로 PR을 머지하는 습관을 들이면 됩니다.
