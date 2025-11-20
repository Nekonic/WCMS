# 중복 PC 데이터 정리 가이드

## 문제 상황
`DESKTOP-HSKGGH9` 같은 이름의 PC가 2개 이상 등록되어 있는 경우

## 원인
- 이전 버전에서 `machine_id` 기반 중복 방지가 제대로 작동하지 않았음
- 같은 PC가 여러 번 등록됨
- IP, MAC, hostname은 같지만 machine_id만 다른 경우 발생 가능

## 해결 방법

### 방법 1: Python 스크립트 사용 (권장)

```bash
cd /Users/nekonic/PycharmProjects/WCMS/server
python3 clean_duplicates.py
```

**기능:**
- ✅ 중복된 PC 자동 탐지 (3가지 케이스)
  1. **machine_id 중복** - 자동 삭제 (최신 것만 유지)
  2. **실질적 중복** (IP+MAC+hostname 같음) - 사용자 확인 후 삭제
  3. **hostname만 중복** (IP/MAC 다름) - 참고만 표시 (삭제 안 함)
- ✅ 백업 자동 생성 옵션 제공
- ✅ 안전한 대화형 인터페이스

### 방법 2: SQL 직접 실행

1. **백업 먼저 생성:**
```bash
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
```

2. **중복 확인:**
```bash
sqlite3 db.sqlite3 < clean_duplicates.sql
```

3. **SQL 파일 수정 후 삭제 실행:**
- `clean_duplicates.sql` 파일을 열어서
- 맨 아래 주석 처리된 DELETE 구문의 주석을 해제 (`/*` `*/` 제거)
- 다시 실행

### 방법 3: 수동 확인 및 삭제

```bash
sqlite3 db.sqlite3
```

```sql
-- 1. 중복 확인
SELECT machine_id, COUNT(*) as cnt, 
       GROUP_CONCAT(id || ':' || hostname) as pcs
FROM pc_info
GROUP BY machine_id
HAVING cnt > 1;

-- 2. 특정 machine_id의 PC 상세 조회
SELECT id, hostname, machine_id, created_at, last_seen, is_online
FROM pc_info
WHERE machine_id = 'YOUR_MACHINE_ID_HERE'
ORDER BY last_seen DESC;

-- 3. 오래된 PC 삭제 (ID 확인 후)
DELETE FROM pc_status WHERE pc_id = OLD_PC_ID;
DELETE FROM pc_specs WHERE pc_id = OLD_PC_ID;
DELETE FROM pc_command WHERE pc_id = OLD_PC_ID;
DELETE FROM seat_map WHERE pc_id = OLD_PC_ID;
DELETE FROM pc_info WHERE id = OLD_PC_ID;
```

## 예방 조치

서버 코드가 업데이트되어 이제 다음과 같이 동작합니다:

1. **machine_id 기반 중복 방지**
   - 같은 `machine_id`를 가진 PC는 절대 2개 이상 등록되지 않음
   - 기존 PC가 있으면 업데이트만 수행

2. **hostname 변경 대응**
   - PC 이름이 바뀌어도 `machine_id`로 추적
   - 자동으로 업데이트

3. **IP/MAC 주소 변경 대응**
   - 네트워크 설정이 바뀌어도 정상 작동

## 중복 유형 설명

### 1. machine_id 중복 ⚠️
같은 `machine_id`를 가진 PC가 여러 개 등록된 경우
- **처리:** 자동 삭제 (최신 것만 유지)
- **원인:** 이전 버전의 버그

### 2. 실질적 중복 ⚠️⚠️
IP, MAC, hostname이 모두 같지만 `machine_id`만 다른 경우
- **처리:** 사용자 확인 후 삭제
- **원인:** 같은 PC인데 machine_id가 재생성된 경우
- **예시:** 
  ```
  PC1: IP=192.168.1.100, MAC=AA:BB:CC:DD:EE:FF, hostname=DESKTOP-ABC, machine_id=12345
  PC2: IP=192.168.1.100, MAC=AA:BB:CC:DD:EE:FF, hostname=DESKTOP-ABC, machine_id=67890
  → 실제로는 같은 PC!
  ```

### 3. hostname만 중복 ℹ️
hostname은 같지만 IP 또는 MAC이 다른 경우
- **처리:** 참고만 표시 (삭제 안 함)
- **원인:** 실제로 다른 PC (정상)
- **예시:**
  ```
  PC1: IP=192.168.1.100, MAC=AA:BB:CC:DD:EE:FF, hostname=DESKTOP-ABC
  PC2: IP=192.168.1.101, MAC=11:22:33:44:55:66, hostname=DESKTOP-ABC
  → 다른 PC인데 이름만 같음 (정상)
  ```

## 확인

정리 후 다음 명령으로 확인:

```sql
-- 중복 PC 확인 (결과 없어야 정상)
SELECT machine_id, COUNT(*) as cnt
FROM pc_info
WHERE machine_id IS NOT NULL
GROUP BY machine_id
HAVING cnt > 1;

-- 전체 PC 수 확인
SELECT COUNT(*) FROM pc_info;
```

## 주의사항

⚠️ **반드시 백업을 먼저 생성하세요!**
⚠️ **삭제된 데이터는 복구할 수 없습니다!**
⚠️ **운영 중인 서버에서는 유지보수 시간에 작업하세요!**

