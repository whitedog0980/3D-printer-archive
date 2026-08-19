# 3D-printer-archive
troubleshooting, print-quality, maintenance, parts 등 3D프린터 출력관련된 시행착오 모음
# 🖨️ 3D Printer Operating & Troubleshooting Logs

> **3D 프린터 운용, 출력 품질 칼리브레이션, 유지보수 및 트러블 슈팅 이력을 기록하는 저장소입니다.**  
> 모든 기록은 Git 커밋 이력을 통해 문제 발생부터 해결까지의 과정을 추적합니다.

---

## 📌 Quick Links (바로가기)

* 🚨 [**Troubleshooting Logs**](./docs/troubleshooting/) — 출력 불량, 하드웨어 이슈 및 해결 내역
* 🎯 [**Print Quality & Calibration**](./docs/quality/) — 슬라이서 프로필, 소재별 레시피, 튜닝 기록
* 🛠️ [**Maintenance**](./docs/maintenance/) — 주기적 점검, 청소, 벨트 장력 및 구조부 관리
* 🧩 [**Parts & Upgrades**](./docs/parts/) — 부품 교체, 노즐 변경, 업그레이드 히스토리

---

## ⚙️ Hardware & Firmware Setup

| 구분 | 사양 / 설정값 |
| :--- | :--- |
| **Printer Model** |  |
| **Firmware** | *예: Klipper / Marlin v2.1.x* |
| **Slicer** | *예: OrcaSlicer / PrusaSlicer / Cura* |
| **Main Nozzle** | *예: Brass 0.4mm (Hardened Steel 0.6mm)* |
| **Default Bed Type** | *예: PEI Texture Sheet* |

---

## 🔍 Recent Troubleshooting Summary

| 날짜 | 이슈 항목 | 원인 및 핵심 조치 | 상태 | 링크 |
| :---: | :--- | :--- | :---: | :---: |
| 2026-08-19 | 1차 레이어 안착 불량 | Z-Offset 재설정 (-1.25 -> -1.38mm) 및 베드 수동 레벨링 | `SOLVED` | [보기](./docs/troubleshooting/) |
| 2026-08-15 | PETG 거미줄(Stringing) 현상 | Retraction 거리(6.5mm) 및 이동 속도(180mm/s) 증가 | `SOLVED` | [보기](./docs/troubleshooting/) |
| YYYY-MM-DD | *이슈 제목 작성* | *간단한 원인 및 조치 내용* | `IN PROGRESS` | [보기](./docs/troubleshooting/) |

---

## 📂 Repository Structure

```text
3d-printer-docs/
├── docs/
│   ├── troubleshooting/   # 트러블 슈팅 (원인, 해결책, Git Log)
│   ├── quality/           # 출력 품질 (슬라이서 설정, 칼리브레이션)
│   ├── maintenance/       # 주기적 점검 및 청소/벨트 장력 관리
│   └── parts/             # 부품 교체 및 업그레이드 이력
├── assets/                # 이미지 및 미디어 파일 (WebP/JPG 압축본)
└── README.md              # 대시보드 (현재 파일)
