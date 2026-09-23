# Polyformer 실행 가이드

실제 구매 → 출력 → 조립까지 바로 실행할 수 있도록 정리한 가이드입니다.

---

## 1. 구매 체크리스트 (BOM 기반)

### 🔩 하드웨어

- [ ] M3x5x4mm 히트셋 인서트 — **108개**
- [ ] 623 베어링 (3x10x4mm) — **4개** (PolyCutter_Lite용 2개 별도 추가 → 총 6개)
- [ ] 608 베어링 (8x22x7mm) — **3개**
- [ ] 1/16in(1.6mm) 드릴비트 — **1개**
- [ ] 12mm x 300mm 튜빙/봉 (스테인리스, 나무 도웰 금지) — **5개** + PolyCutter_Lite용 1개 = **총 6개**
  > ⚠️ 품귀 품목. 가장 먼저 주문할 것
- [ ] M3 와셔 (외경 7mm, 흑산화 탄소강, DIN 125A) — **11개**
- [ ] M3 BHCS 나사 세트 (6/8/12/20/30mm 혼합 키트) — **1세트**
- [ ] M3 BHCS 12mm 100개입 — **1팩** (세트만으로 부족)
- [ ] PTFE 윤활제 — **1개**
- [ ] (선택) 2mm 육각 드라이버 80mm 이상 — **1개**

**나사 최종 수량 (파스너 목록 기준, ±10%)**
- BHCS M3x6mm: 39개
- BHCS M3x8mm: 14개
- BHCS M3x12mm: 58개 (+PolyCutter_Lite용 5개 = 총 63개)
- BHCS M3x20mm: 9개
- 스테인리스 BHCS M3x30mm: 4개
- M3 너트: 13개
- 탄소강 M3 와셔: 11개

### ⚡ 전자부품

- [ ] BigTreeTech EBB42 또는 EBB36 (max31865 없는 버전) — **1개**
  > ⚠️ V1.2.1은 구펌웨어 비호환 → **V1.1 또는 V1.2 지정 구매**
- [ ] 6020 또는 6025 24V 팬 — **1개**
- [ ] NEMA17 스텝모터 (1.8도, 59Ncm, 48mm 미만) — **1개**
- [ ] C13 전원 케이블 — **1개**
- [ ] C14 패널 마운트 플러그 — **1개**
- [ ] MeanWell LRS-75-24 또는 LRS-100-24 — **1개**
- [ ] 핫엔드 구성 (**옵션 중 1가지만 선택**)
  - **[옵션 A - 저가형, 권장]** Volcano+서미스터+노즐 번들 1개 + 24V 40W 히터 카트리지 1개(번들 동봉 64W는 미사용) + JST XH 연장 케이블 3개
  - **[옵션 B - 정품]** E3D Volcano 히터 블록 + 24V 40W 히터 카트리지 + M3 나사형 서미스터 104NT 2개 + E3D 정품 황동 노즐(3.0mm x 1.2mm)

### 🔧 기타

- [ ] 6mm x 3mm 네오디움 마그넷 — **24개**
- [ ] (선택) 60°C 안전 온도 라벨 — **1개**
- [ ] (선택) E3D Volcano 실리콘 삭스 — **1개**

### 🖨️ 프린팅 소재

- [ ] 메인 컬러 필라멘트 **2.0kg**
- [ ] 포인트(액센트) 컬러 필라멘트 **0.5kg**
- 소재: PLA / ABS / PETG / PET 중 선택 (수축률: ABS 약 0.6%, PETG 약 0.15%, PLA 기준)

### 📦 구매처 (지역별)

| 지역 | 업체 |
|---|---|
| 유럽 | Fermiolabs, Decoprint3d, Kris3D_de, Vonwange, Lecktor |
| 미국 | DFH(Formossisima 3D Printing), Fabreeko, Printed_Solid, Digmach, kb3d, Filastruder |
| 캐나다 | Sparta3D, 3dlabtech |
| 호주 | Uniqueprints |
| 공통 | AliExpress(저렴하지만 배송 오래 걸림), Amazon, Boltdepot(나사 개별 구매) |

---

## 2. 필수 출력 부품 (프린팅 우선순위)

Polyformer는 기능 모듈별로 부품이 나뉩니다. 조립 순서에 맞춰 아래 순서로 출력하는 것을 권장합니다.

| 우선순위 | 모듈 | 설명 |
|---|---|---|
| 1 | **메인 프레임 / 본체 구조부** | 전체 기계를 지지하는 뼈대. 가장 크고 오래 걸리므로 가장 먼저 시작 |
| 2 | **PolyCutter (절단부)** | 623 베어링 스택 기반, 페트병을 리본으로 절단하는 모듈. `PolyCutter_Lite` 버전 부품 포함 |
| 3 | **핫엔드 마운트 / 압출부** | Volcano 핫엔드를 장착하는 하우징 |
| 4 | **스풀(권취) 어셈블리** | 완성된 필라멘트를 감는 모터 구동 스풀 |
| 5 | **전자부품 인클로저** | EBB42 보드, 디스플레이, 파워서플라이를 담는 케이스 |
| 6 | **포인트 컬러 디테일 파츠** | 로고/버튼 등 소형 파츠 (가장 마지막, 시간 여유 있을 때 진행) |

> 💡 정확한 파일명 목록은 GitHub `STL` 폴더에서 직접 확인하세요. 저장소 내 파일이 주기적으로 업데이트되므로, 다운로드 시점 기준 최신 버전을 받는 것이 중요합니다.
> 👉 https://github.com/a-leyva/Polyformer/tree/main/STL

---

## 3. 조립 가이드 (실제 영상 자료)

Polyformer 공식 Hackaday.io 프로젝트 페이지에 **실제 조립 영상 3편**과 **조립 순서도(Assembly Graphs)**가 공개되어 있습니다.

### 🎥 공식 조립 영상

1. https://www.youtube.com/watch?v=gqaRRzHKmp0
2. https://www.youtube.com/watch?v=NvOG5K5bJ6M
3. https://www.youtube.com/watch?v=LeM5dLHGVpM

### 📋 조립 순서도 (Assembly Graphs)

👉 https://github.com/Reiten966/Polyformer/tree/main/Build%20Guide

### 🔗 출처 페이지

👉 https://hackaday.io/project/185304/instructions

---

## 4. 조립 단계 요약

1. **히트셋 인서트 삽입** — 소재별 권장 인두 온도로 130개 인서트 삽입 (인서트 개수는 부품 출력 완료 후 실측 확인 권장)
2. **베어링 장착** — 623(6개), 608(3개) 위치에 PTFE 윤활제 도포 후 장착
3. **PolyCutter 조립** — 623 베어링 스택 방식으로 절단 도구 구성
4. **튜빙/봉 절단 및 고정** — 12mm x 300mm 6개를 설계 치수에 맞게 절단
5. **마그넷 삽입** — 24개, 극성 방향 확인 후 접착
6. **핫엔드 조립** — 선택한 옵션(A/B)에 따라 히터 카트리지·서미스터·노즐 장착
7. **전자부품 배선** — EBB42 보드, 스텝모터, 팬, 디스플레이 연결 (배선도: `POLYFORMER-MAIN_WIRING_GUIDE.png`, hackaday.io/project/185304/files 에서 확인 가능)
8. **전원 테스트** — 260°C 이상 가열 확인, 이상 발열/누전 여부 점검
9. **시험 가동** — 소량 PET 병으로 절단·압출 테스트

---

## 5. 참고 링크 모음

| 자료 | 링크 |
|---|---|
| GitHub (최신 포크) | https://github.com/a-leyva/Polyformer |
| GitHub (원본) | https://github.com/Reiten966/Polyformer |
| Hackaday.io 프로젝트 | https://hackaday.io/project/185304-polyformer-ideal-filament-recycler |
| Hackaday 파일(STL/CAD/배선도 zip) | https://hackaday.io/project/185304/files |
| Printables | https://www.printables.com/model/296063-polyformer |
| Discord (Q&A) | GitHub README 내 링크 참고 |

---

*본 가이드는 공식 GitHub·Hackaday.io 공개 자료를 바탕으로 정리했습니다. 조립 전 반드시 GitHub Build Guide 원문 및 위 조립 영상을 함께 확인하시기 바랍니다.*
