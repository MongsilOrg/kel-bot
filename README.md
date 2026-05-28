# KelBot

이터널 리턴 KEL 스크림 신청·추첨 Discord 봇.

## 주요 기능

- 지역 단위 팀 신청 (`지역) 닉네임` 형식 강제)
- 매일 자동 랜덤 추첨 (00:30 KST) + 8팀 도달 즉시 추첨
- 우선권 시스템 (탈락 → 다음날 자동 부여, 17:00 데드라인 시 소멸)
- LayoutView 기반 영구 대시보드 (슬래시 명령어 없음)
- 봇 재시작 시 상태 복원 + 놓친 스케줄 자동 보정

자세한 사양은 `docs/FEATURES.md` 참고.

## 설치 및 실행

```bash
git clone <레포 주소>
cd kelbot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 환경변수 입력
python main.py
```

### 요구사항

- Python 3.10+
- Discord Developer Portal에서 봇 토큰 발급
- **Server Members Intent 활성화 필요**

## 환경변수

`.env`에 설정.

| 변수 | 필수 | 설명 |
|------|------|------|
| `DISCORD_TOKEN` | ✓ | Discord 봇 토큰 |
| `APPLY_CHANNEL_ID` | ✓ | 대시보드 채널 ID |
| `NOTICE_CHANNEL_ID` | ✓ | 추첨 결과 공지 채널 ID |
| `GUILD_ID` |   | 서버 ID (선택) |
| `LOG_CHANNEL_ID` |   | 에러 로그 채널 (선택) |
| `RESET_HOUR` |   | 일일 리셋 시각 (기본 `21`) |
| `DRAW_HOUR` |   | 1차 추첨 시각 시 (기본 `0`) |
| `DRAW_MINUTE` |   | 1차 추첨 시각 분 (기본 `30`) |
| `DEADLINE_HOUR` |   | 데드라인 시각 (기본 `17`) |
| `TEAM_SLOTS` |   | 추첨 정원 (기본 `8`) |

## 일일 타임라인 (KST)

| 시각 | 이벤트 |
|------|--------|
| 21:00 (D-1) | 신청 리셋·오픈, 우선권 갱신 |
| 00:30 (D) | 1차 추첨 (≥8팀이면 실행, 미달이면 보류) |
| 보류 중 | 8팀 도달 즉시 추첨 |
| 17:00 (D) | 데드라인 — 미달 시 당일 취소, 우선권 소멸 |

## 응급 대응

비정상 상태 시:
1. `data/*.json` 직접 수정
2. 봇 재시작 (`pmc restart kelbot` 또는 프로세스 재시작)
3. 대시보드 메시지 손상 시 `data/dashboard_message.json` 삭제 후 재시작

관리자 UI는 제공하지 않는다. 자동 운영 원칙.
