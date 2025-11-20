-- WCMS 중복 PC 정리 SQL 스크립트

-- 1. machine_id 중복 확인
SELECT machine_id, COUNT(*) as cnt,
       GROUP_CONCAT(id || ':' || hostname || ':' || last_seen) as pcs
FROM pc_info
WHERE machine_id IS NOT NULL AND machine_id != ''
GROUP BY machine_id
HAVING cnt > 1;

-- 2. hostname 중복 확인 (참고용)
SELECT hostname, COUNT(*) as cnt,
       GROUP_CONCAT(id || ':' || machine_id || ':' || last_seen) as pcs
FROM pc_info
WHERE hostname IS NOT NULL
GROUP BY hostname
HAVING cnt > 1;

-- 3. 중복 삭제 (machine_id 기준, 최신 것만 유지)
-- 주의: 실행 전 백업 필수!

-- 3-1. 삭제할 PC ID 확인 (테스트용)
WITH ranked_pcs AS (
    SELECT id, machine_id, hostname, last_seen,
           ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY last_seen DESC, created_at DESC) as rn
    FROM pc_info
    WHERE machine_id IS NOT NULL AND machine_id != ''
)
SELECT id, machine_id, hostname, last_seen
FROM ranked_pcs
WHERE rn > 1
ORDER BY machine_id, rn;

-- 3-2. 실제 삭제 (주의: 되돌릴 수 없음!)
-- 아래 주석을 해제하고 실행하세요

/*
-- 관련 테이블에서 삭제
DELETE FROM pc_status WHERE pc_id IN (
    WITH ranked_pcs AS (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY last_seen DESC, created_at DESC) as rn
        FROM pc_info
        WHERE machine_id IS NOT NULL AND machine_id != ''
    )
    SELECT id FROM ranked_pcs WHERE rn > 1
);

DELETE FROM pc_specs WHERE pc_id IN (
    WITH ranked_pcs AS (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY last_seen DESC, created_at DESC) as rn
        FROM pc_info
        WHERE machine_id IS NOT NULL AND machine_id != ''
    )
    SELECT id FROM ranked_pcs WHERE rn > 1
);

DELETE FROM pc_command WHERE pc_id IN (
    WITH ranked_pcs AS (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY last_seen DESC, created_at DESC) as rn
        FROM pc_info
        WHERE machine_id IS NOT NULL AND machine_id != ''
    )
    SELECT id FROM ranked_pcs WHERE rn > 1
);

DELETE FROM seat_map WHERE pc_id IN (
    WITH ranked_pcs AS (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY last_seen DESC, created_at DESC) as rn
        FROM pc_info
        WHERE machine_id IS NOT NULL AND machine_id != ''
    )
    SELECT id FROM ranked_pcs WHERE rn > 1
);

-- pc_info에서 삭제
DELETE FROM pc_info WHERE id IN (
    WITH ranked_pcs AS (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY last_seen DESC, created_at DESC) as rn
        FROM pc_info
        WHERE machine_id IS NOT NULL AND machine_id != ''
    )
    SELECT id FROM ranked_pcs WHERE rn > 1
);
*/

-- 4. 정리 후 확인
SELECT COUNT(*) as total_pcs FROM pc_info;
SELECT COUNT(*) as online_pcs FROM pc_info WHERE is_online = 1;

