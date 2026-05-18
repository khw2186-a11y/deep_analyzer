-- [1단계] 데이터베이스 보안을 위한 암호화 기능 활성화
-- pgcrypto는 Postgres에서 기본으로 제공하는 강력한 암호화 도구입니다.
-- 측정자 이름과 같은 민감한 정보를 암호화하여 안전하게 저장하기 위해 사용합니다.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- [2단계] 재질 정보 테이블 생성 (materials)
-- 테스트 대상이 되는 스테인리스 스틸(SS) 등의 재질 정보를 저장하는 곳입니다.
CREATE TABLE IF NOT EXISTS materials (
    id SERIAL PRIMARY KEY, -- 고유 번호 (자동으로 1, 2, 3... 증가함)
    name VARCHAR(50) NOT NULL UNIQUE, -- 재질명 (예: SS 304). 중복 저장을 막기 위해 UNIQUE 설정.
    description TEXT, -- 재질에 대한 부가적인 설명이나 특이사항을 적는 칸
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 등록된 날짜와 시간 (자동 기록)
);

-- [3단계] 질화 처리 공정 테이블 생성 (nitriding_processes)
-- 온도, 시간 등 염욕 질화를 어떻게 했는지(레시피)를 저장하는 곳입니다.
CREATE TABLE IF NOT EXISTS nitriding_processes (
    id SERIAL PRIMARY KEY, -- 고유 번호
    process_name VARCHAR(100) NOT NULL, -- 공정의 이름 (예: 표준 염욕 질화 A)
    temperature_celsius INTEGER NOT NULL, -- 처리 온도 (단위: ℃)
    duration_minutes INTEGER NOT NULL, -- 처리 시간 (단위: 분)
    bath_composition TEXT, -- 염욕의 화학적 조성 비율 등 설명
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 등록된 날짜와 시간
);

-- [4단계] 테스트 샘플 테이블 생성 (test_samples)
-- 각각의 샘플 조각들이 어떤 재질이고, 어떤 공정을 거쳤는지 기록하는 곳입니다.
CREATE TABLE IF NOT EXISTS test_samples (
    id SERIAL PRIMARY KEY, -- 샘플의 고유 번호
    material_id INTEGER REFERENCES materials(id) ON DELETE RESTRICT, -- 어떤 재질인지 (materials 테이블과 연결)
    process_id INTEGER REFERENCES nitriding_processes(id) ON DELETE SET NULL, -- 어떤 공정을 거쳤는지 (생지 상태 테스트라면 안 거쳤을 수 있으므로 null 허용)
    batch_number VARCHAR(50), -- 현장에서 관리하는 작업 그룹(Lot) 번호
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 샘플 등록 날짜
);

-- [5단계] 테스트 결과 테이블 생성 (test_results)
-- 질화 처리 전후의 표면 경도, 치수, 마찰 계수 등 핵심 데이터를 기록하는 곳입니다.
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY, -- 결과 고유 번호
    sample_id INTEGER REFERENCES test_samples(id) ON DELETE CASCADE, -- 어떤 샘플의 결과인지 연결 (샘플 삭제 시 결과도 같이 삭제)
    test_phase VARCHAR(20) CHECK (test_phase IN ('BEFORE_TREATMENT', 'AFTER_TREATMENT')), -- 테스트 시점이 '처리 전'인지 '처리 후'인지 구분
    surface_hardness_hv NUMERIC(10, 2), -- 표면 경도 측정값 (Vickers 기준 등, 소수점 둘째 자리까지)
    dimensional_change_mm NUMERIC(10, 4), -- 치수 변화량 측정값 (단위: mm)
    friction_coefficient NUMERIC(5, 4), -- 마찰 계수 측정값
    tester_name BYTEA, -- 측정자 이름 (평문이 아닌 암호화된 이진 데이터(BYTEA) 형태로 안전하게 저장됨)
    test_date DATE DEFAULT CURRENT_DATE, -- 측정 테스트를 진행한 날짜
    notes TEXT, -- 특이사항이나 기타 메모
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 결과 등록 날짜
);

-- [6단계] 강력한 보안 정책 적용 (Row Level Security - RLS)
-- 테이블의 데이터를 아무나 읽고 쓰지 못하도록 잠금 장치를 겁니다.
ALTER TABLE materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE nitriding_processes ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_results ENABLE ROW LEVEL SECURITY;

-- 아래는 예시 보안 정책입니다. Supabase 인증을 통과한 로그인한 사용자(authenticated)만 데이터를 조회하고 수정할 수 있도록 허용합니다.
CREATE POLICY "로그인한 사용자만 재질 조회 가능" ON materials FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "로그인한 사용자만 재질 수정 가능" ON materials FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "로그인한 사용자만 공정 조회 가능" ON nitriding_processes FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "로그인한 사용자만 공정 수정 가능" ON nitriding_processes FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "로그인한 사용자만 샘플 조회 가능" ON test_samples FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "로그인한 사용자만 샘플 수정 가능" ON test_samples FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "로그인한 사용자만 결과 조회 가능" ON test_results FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "로그인한 사용자만 결과 수정 가능" ON test_results FOR ALL USING (auth.role() = 'authenticated');


-- [7단계] 요청하신 초기 스테인리스(SS) 재질 데이터 입력
-- 테스트에 바로 사용할 수 있도록 기초 재질 데이터를 자동으로 넣어줍니다.
-- ON CONFLICT DO NOTHING을 사용하여 여러 번 실행해도 에러가 나지 않고 안전하게 처리합니다.
INSERT INTO materials (name, description) VALUES 
('SS 304', '가장 범용적인 오스테나이트계 스테인리스 스틸'),
('SS 316', '몰리브덴(Mo)이 첨가되어 내식성이 우수한 오스테나이트계'),
('SS 321H', '고온 강도와 크리프 저항성이 강화된 스테인리스'),
('SS 410', '기본적인 마르텐사이트계 스테인리스, 열처리로 경화 가능'),
('SS 420', 'SS 410보다 탄소가 높아 열처리 후 경도가 더 높은 마르텐사이트계'),
('SS 431', '크롬(Cr)과 니켈(Ni)이 첨가되어 기계적 성질과 내식성이 우수한 마르텐사이트계')
ON CONFLICT (name) DO NOTHING;
