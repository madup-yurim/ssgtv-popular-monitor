# Google Sheets 연동 설정 (1회만)

## 소요 시간: 약 5분

---

## 1단계 — Google Cloud 프로젝트 & API 활성화

1. https://console.cloud.google.com/ 접속
2. 상단 프로젝트 선택 → **새 프로젝트** 생성 (이름 예: `shinsegae-monitor`)
3. 왼쪽 메뉴 → **API 및 서비스** → **라이브러리**
4. "Google Sheets API" 검색 → **사용 설정**

---

## 2단계 — 서비스 계정 생성 & 키 다운로드

1. 왼쪽 메뉴 → **API 및 서비스** → **사용자 인증 정보**
2. **+ 사용자 인증 정보 만들기** → **서비스 계정**
3. 서비스 계정 이름 입력 (예: `sheets-writer`) → **만들기 및 계속**
4. 역할은 선택하지 않고 → **계속** → **완료**
5. 생성된 서비스 계정 클릭 → **키** 탭 → **키 추가** → **새 키 만들기** → **JSON**
6. 다운로드된 JSON 파일을 아래 경로에 저장:

```
C:\Users\MADUP\Desktop\dev\신세계쇼핑\인기상품_모니터링\service_account.json
```

---

## 3단계 — 스프레드시트 공유

다운로드한 JSON 파일을 메모장으로 열면 `"client_email"` 항목이 있습니다.

예시:
```
"client_email": "sheets-writer@shinsegae-monitor.iam.gserviceaccount.com"
```

1. 대상 스프레드시트 열기:
   https://docs.google.com/spreadsheets/d/1NR55kj6kwK1vSG3J-3T_IROYibAgv5WUqw46adh3sKU
2. 우상단 **공유** 버튼
3. 위의 `client_email` 주소를 추가, 역할 **편집자**로 설정 → 공유

---

## 4단계 — 테스트 실행

```bash
cd C:\Users\MADUP\Desktop\dev\신세계쇼핑\인기상품_모니터링
python sheets_writer.py
```

성공 시:
```
✅ 250행 → 2026-05-18 탭 업데이트 완료
📊 https://docs.google.com/spreadsheets/d/...
```
