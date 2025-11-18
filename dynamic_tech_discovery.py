import json
import os
import requests
from openai import OpenAI
import datetime
from bs4 import BeautifulSoup
from ddgs import DDGS
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import re
from urllib.parse import urljoin, urlparse
import sys
import codecs

# UTF-8 출력을 위한 환경 설정
def setup_utf8_output():
    """UTF-8 출력을 위한 환경 설정"""
    if os.name == 'nt':  # Windows
        try:
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
        except:
            pass

def safe_print(message):
    """UTF-8 안전 출력 함수"""
    try:
        print(message)
    except UnicodeEncodeError:
        # 유니코드 문자를 ASCII로 변환하여 출력
        message_ascii = message.encode('ascii', errors='ignore').decode('ascii')
        print(message_ascii)
    except Exception:
        print("[OUTPUT_ERROR]")

# UTF-8 출력 환경 설정
setup_utf8_output()

# Load environment variables
load_dotenv()

# --- API Key & Supabase Setup ---
try:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        print("[WARNING] OPENAI_API_KEY not set. Using dummy client.")
        openai_client = None
    else:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[SUCCESS] OpenAI API Key configured.")

    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[SUCCESS] Supabase client created.")
    else:
        print("[WARNING] Supabase credentials not set. Database operations will be skipped.")
        supabase = None

except Exception as e:
    print(f"[ERROR] Setup failed: {e}")
    exit()

# --- Dynamic Tech Stack Discovery ---

def discover_trending_technologies():
    """포괄적인 기술 스택 수집 - 빠른 수집 방식"""
    print("[SEARCH] Discovering comprehensive technologies...")

    discovered_techs = set()

    # 1. GitHub 트렌딩에서 수집 (빠름)
    github_techs = get_github_trending_languages()
    discovered_techs.update(github_techs)

    # 2. Stack Overflow Survey에서 수집 (빠름, 검색량 줄임)
    stackoverflow_techs = get_stackoverflow_popular_techs()
    discovered_techs.update(stackoverflow_techs)

    # 3. 포괄적 기본 기술 목록 추가 (매우 빠름)
    base_techs = get_comprehensive_base_technologies()
    discovered_techs.update(base_techs)

    # 4. Wikipedia에서 기술 목록 수집 (빠름, 검색량 줄임)
    wiki_techs = get_technologies_from_wikipedia()
    discovered_techs.update(wiki_techs)

    print(f"[INFO] 총 {len(discovered_techs)}개의 기술 스택 발견")
    return list(discovered_techs)

def get_github_trending_languages():
    """GitHub 트렌딩 언어들 수집"""
    print("  - [GITHUB] GitHub 트렌딩에서 수집 중...")
    techs = set()

    try:
        # GitHub 트렌딩 API는 공식적으로 없으므로 웹 스크래핑
        ddgs = DDGS()

        # GitHub 트렌딩 검색
        search_results = ddgs.text("site:github.com/trending programming languages", max_results=10)

        # 일반적인 프로그래밍 언어들 추가
        popular_languages = [
            'JavaScript', 'Python', 'TypeScript', 'Java', 'Go', 'Rust',
            'C++', 'C#', 'PHP', 'Ruby', 'Swift', 'Kotlin', 'Dart'
        ]
        techs.update(popular_languages)

        # 인기 프레임워크들
        popular_frameworks = [
            'React', 'Vue.js', 'Angular', 'Node.js', 'Express.js', 'Django',
            'Flask', 'Spring Boot', 'Laravel', 'Rails', 'Next.js', 'Nuxt.js'
        ]
        techs.update(popular_frameworks)

    except Exception as e:
        safe_print(f"    [ERROR] GitHub trending collection failed: {e}")

    return list(techs)

def get_stackoverflow_popular_techs():
    """Stack Overflow에서 인기 기술들 수집"""
    print("  - [SO] Stack Overflow에서 수집 중...")
    techs = set()

    try:
        ddgs = DDGS()

        # Stack Overflow 개발자 설문조사 관련 검색 (속도 최적화)
        search_queries = [
            "programming languages list complete",
            "database technologies all types",
            "web frameworks comprehensive list",
            "mobile development tools all platforms"
        ]

        for query in search_queries:
            results = ddgs.text(query, max_results=3)  # 5->3으로 줄임
            # 검색 결과에서 기술명 추출 (간단한 패턴 매칭)
            for result in results:
                text = result.get('body', '') + ' ' + result.get('title', '')
                extracted_techs = extract_tech_names_from_text(text)
                techs.update(extracted_techs)

            time.sleep(0.5)  # 1초->0.5초로 줄임

    except Exception as e:
        safe_print(f"    [ERROR] Stack Overflow collection failed: {e}")

    return list(techs)


def extract_tech_names_from_text(text):
    """텍스트에서 기술명 추출"""
    tech_patterns = [
        # 프로그래밍 언어
        r'\b(?:JavaScript|TypeScript|Python|Java|Go|Rust|C\+\+|C#|PHP|Ruby|Swift|Kotlin|Dart|Scala|R|MATLAB)\b',
        # 웹 프레임워크
        r'\b(?:React|Vue\.js|Angular|Node\.js|Express\.js|Django|Flask|Spring|Laravel|Rails|Next\.js|Nuxt\.js|Svelte)\b',
        # 데이터베이스
        r'\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|SQLite|MariaDB|Oracle|SQL Server)\b',
        # 클라우드/DevOps
        r'\b(?:AWS|Azure|Google Cloud|Docker|Kubernetes|Terraform|Jenkins|Git|GitHub|GitLab)\b',
        # 모바일
        r'\b(?:React Native|Flutter|Xamarin|Ionic|Cordova)\b'
    ]

    extracted = set()
    for pattern in tech_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        extracted.update(matches)

    return extracted

def get_comprehensive_base_technologies():
    """기본적으로 포함해야 할 다양한 기술들"""
    safe_print("  - [BASE] Comprehensive base technology list adding...")
    base_techs = [
        # 레거시/안정적 기술
        'COBOL', 'Fortran', 'Ada', 'Delphi', 'Visual Basic', 'Pascal', 'Assembly',
        # 니치/전문 기술
        'R', 'MATLAB', 'Haskell', 'Erlang', 'Prolog', 'Clojure', 'F#', 'OCaml',
        # 게임/그래픽
        'Unity', 'Unreal Engine', 'Blender', 'Maya', 'Godot', 'GameMaker', 'Construct',
        # 임베디드/IoT
        'Arduino', 'Raspberry Pi', 'FreeRTOS', 'Zephyr', 'Mbed OS', 'PlatformIO',
        # 과학/연구
        'Jupyter', 'Octave', 'SciPy', 'SPSS', 'Stata', 'SAS', 'Mathematica',
        # 모바일
        'Xamarin', 'Ionic', 'Cordova', 'PhoneGap', 'Titanium',
        # 웹 특화
        'Svelte', 'Elm', 'PureScript', 'ClojureScript', 'ReasonML',
        # 데이터베이스
        'CouchDB', 'RethinkDB', 'OrientDB', 'ArangoDB', 'InfluxDB', 'TimescaleDB',
        # DevOps/인프라
        'Ansible', 'Puppet', 'Chef', 'SaltStack', 'Vagrant', 'Packer',
        # 빅데이터
        'Hadoop', 'Spark', 'Kafka', 'Storm', 'Flink', 'Airflow',
        # 블록체인
        'Solidity', 'Vyper', 'Web3.js', 'Ethers.js'
    ]
    return base_techs

def get_technologies_from_wikipedia():
    """Wikipedia에서 기술 목록 수집"""
    print("  - [WIKI] Wikipedia에서 기술 목록 수집 중...")
    techs = set()

    try:
        ddgs = DDGS()

        # Wikipedia 기반 포괄적 검색 (속도 최적화)
        wiki_queries = [
            "site:en.wikipedia.org \"List of programming languages\"",
            "site:en.wikipedia.org \"List of database management systems\"",
            "site:en.wikipedia.org \"Web framework comparison\""
        ]

        for query in wiki_queries:
            results = ddgs.text(query, max_results=2)  # 3->2로 줄임
            for result in results:
                text = result.get('body', '') + ' ' + result.get('title', '')
                extracted_techs = extract_tech_names_from_text(text)
                techs.update(extracted_techs)

            time.sleep(0.3)  # 0.5->0.3초로 줄임

    except Exception as e:
        print(f"    [ERROR] Wikipedia 수집 실패: {e}")

    return list(techs)

def create_slug(name):
    """기술명을 슬러그로 변환"""
    return name.lower().replace(' ', '-').replace('.', 'dot').replace('#', 'sharp').replace('+', 'plus')

def get_tech_popularity_score(tech_name):
    """기술의 인기도 점수 계산 (1-100) - 속도 최적화"""
    try:
        ddgs = DDGS()

        # 검색 결과 수로 인기도 측정 (검색량 줄임)
        search_queries = [
            f"{tech_name} programming tutorial",
            f"{tech_name} github repositories"
        ]

        total_score = 0
        for query in search_queries:
            results = ddgs.text(query, max_results=20)  # 50->20으로 줄임
            total_score += len(results) * 10
            time.sleep(0.2)  # 0.5->0.2초로 줄임

        # 0-100 범위로 정규화
        normalized_score = total_score / 10  # 계산 공식 조정
        return round(min(100, max(10, normalized_score)), 1)

    except Exception as e:
        print(f"    [WARNING] {tech_name} 인기도 계산 실패: {e}")
        return 50  # 기본값

def enhance_with_ai(tech_name, scraped_info):
    """AI로 기술 정보 향상"""
    print(f"    - [AI] Enhancing '{tech_name}' data with AI...")

    # OpenAI 클라이언트가 없으면 기본값 반환
    if not openai_client:
        print(f"        [WARNING] OpenAI client not available. Using default data for {tech_name}")
        return {
            "description": f"{tech_name}은(는) 인기있는 개발 기술입니다.",
            "category": "language",
            "logoUrl": None,
            "color": "#6B7280",
            "learningResources": ["공식 문서", "온라인 튜토리얼", "커뮤니티 포럼"]
        }

    prompt = f"""
    ## 역할 및 전문성
    당신은 15년 경력의 수석 소프트웨어 아키텍트이자 기술 컨설턴트입니다. 수백 개의 프로젝트를 통해 다양한 기술 스택의 실무 적용과 성능 최적화 경험을 보유하고 있으며, Fortune 500 기업부터 스타트업까지 기술 선택과 아키텍처 설계를 지원해왔습니다.

    ## 분석 대상 기술
    기술명: {tech_name}
    수집된 정보: {scraped_info}

    ## 분석 목표
    개발자들이 기술 선택 시 올바른 의사결정을 할 수 있도록 정확하고 실용적인 정보를 제공하세요. 단순한 정의가 아닌 실무 관점에서의 깊이 있는 분석이 필요합니다.

    ## 출력 형식
    다음 JSON 스키마에 정확히 맞춰 모든 문자열을 한국어로 작성하세요:

    {{
        "description": "기술의 핵심 정의와 주요 목적을 명확하고 간결하게 설명 (20-30자)",
        "category": "다음 중 정확히 하나만 선택: frontend, backend, database, mobile, devops, language, framework, library, tool",
        "ai_explanation": "AI가 기술에 대해 심층적으로 설명하는 글 (200-300자)",
        "project_suitability": [
            "이 기술이 적합한 프로젝트 유형을 설명하는 문자열 배열 (3-5줄)",
            "예: '대규모 실시간 채팅 애플리케이션', '개인 포트폴리오 웹사이트'"
        ],
        "learning_difficulty": {{
            "label": "학습 난이도 (예: '초급', '중급', '고급')",
            "stars": [true, true, false, false, false],
            "description": "난이도에 대한 부가 설명 (100자 이내)"
        }},
        "logoUrl": "기술의 공식 로고 URL (없으면 null)",
        "learningResources": [
            {{
                "url": "리소스 URL",
                "type": "documentation | tutorial | video | book",
                "title": "리소스 제목"
            }}
        ]
    }}

    ## 품질 기준
    1. **정확성**: 검증된 정보만 사용하며, 추측이나 과장 금지
    2. **실용성**: 이론보다는 실무 적용 관점에서 설명
    3. **균형성**: 장점과 단점을 모두 언급하여 객관적 판단 지원
    4. **최신성**: 2024년 기준 최신 동향과 버전 정보 반영
    5. **명확성**: 기술 용어 사용 시 간단한 설명 추가

    ## 카테고리 분류 가이드
    - frontend: React, Vue, Angular 등 사용자 인터페이스 기술
    - backend: Express, Django, Spring 등 서버 사이드 기술
    - database: MySQL, MongoDB, Redis 등 데이터 저장 기술
    - mobile: React Native, Flutter 등 모바일 앱 개발 기술
    - devops: Docker, Kubernetes, Jenkins 등 배포/운영 기술
    - language: JavaScript, Python, Java 등 프로그래밍 언어
    - framework: Next.js, Laravel 등 개발 프레임워크
    - library: Lodash, Moment.js 등 유틸리티 라이브러리
    - tool: VS Code, Git, Webpack 등 개발 도구

    ## 응답 제약사항
    - 마크다운 포맷팅 사용 금지
    - JSON 형식 엄격 준수
    - 모든 문자열 값은 완전한 한국어로 작성 (logoUrl, color 제외)
    - 허위 정보나 과장 금지
    - 응답 길이: description 100-200자, learningResources 각 항목 50자 이내
    - logoUrl은 실제 존재하는 URL만 사용, 없으면 null
    - color는 반드시 # 포함한 HEX 코드 형식

    지금 위 기준에 따라 '{tech_name}' 기술에 대한 완벽한 분석을 JSON 형태로 제공하세요.
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5",  # GPT-5 nano (2025년 9월 기준)
            messages=[
                {"role": "system", "content": "You are a world-class software engineering expert."},
                {"role": "user", "content": prompt}
            ]
        )

        json_text = response.choices[0].message.content.strip().replace('```json', '').replace('```', '')
        return json.loads(json_text)
    except Exception as e:
        print(f"        [ERROR] AI enhancement failed: {e}")
        return None

def search_and_scrape(tech_name):
    """기술에 대한 정보 스크래핑"""
    print(f"    - [SCRAPE] Scraping info for '{tech_name}'...")
    scraped_info = {}

    try:
        ddgs = DDGS()

        # 공식 사이트와 GitHub 리포지토리 찾기
        search_results = ddgs.text(f'{tech_name} official website github', max_results=10)

        for result in search_results:
            href = result.get('href', '')
            if 'github.com' in href and not scraped_info.get('repo'):
                scraped_info['repo'] = href
            elif 'github.com' not in href and not scraped_info.get('homepage'):
                # 공식 사이트로 보이는 도메인 우선
                domain = urlparse(href).netloc
                if any(keyword in domain.lower() for keyword in [tech_name.lower().replace('.js', ''), tech_name.lower().replace(' ', '')]):
                    scraped_info['homepage'] = href

        # 홈페이지가 없으면 첫 번째 non-github 링크 사용
        if not scraped_info.get('homepage'):
            for result in search_results:
                href = result.get('href', '')
                if 'github.com' not in href:
                    scraped_info['homepage'] = href
                    break

        return scraped_info

    except Exception as e:
        print(f"    [ERROR] Scraping failed for {tech_name}: {e}")
        return {}

def save_to_local_json(data):
    """로컬 JSON 파일에 저장"""
    try:
        # 기존 데이터 읽기
        try:
            with open('stacks.json', 'r', encoding='utf-8') as f:
                existing_stacks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_stacks = []

        # 중복 제거 (slug 기준)
        existing_stacks = [s for s in existing_stacks if s.get('slug') != data.get('slug')]

        # 새 데이터 추가
        existing_stacks.append(data)

        # 인기도 순으로 정렬
        existing_stacks.sort(key=lambda x: x.get('popularity', 0), reverse=True)

        # 파일에 저장
        with open('stacks.json', 'w', encoding='utf-8') as f:
            json.dump(existing_stacks, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"        [ERROR] Failed to save to JSON: {e}")
        return False

def upsert_to_supabase_rpc(data):
    """RPC 함수를 사용한 업서트"""
    if not supabase:
        print(f"        [WARNING] Supabase not available. Skipping database upsert for '{data['name']}'")
        return False

    try:
        response = supabase.rpc('upsert_tech_stack', {
            'p_name': data['name'],
            'p_slug': data['slug'],
            'p_category': data.get('category'),
            'p_description': data.get('description'),
            'p_logo_url': data.get('logo_url'),
            'p_popularity': int(data.get('popularity', 0)),
            'p_learning_resources': data.get('learning_resources', []),
            'p_ai_explanation': data.get('ai_explanation'),
            'p_homepage': data.get('homepage'),
            'p_repo': data.get('repo'),
            'p_project_suitability': data.get('project_suitability', []),
            'p_learning_difficulty': data.get('learning_difficulty', {})
        }).execute()

        if response.data:
            print(f"        [SUCCESS] RPC upsert completed for '{data['name']}'")
            return True
        return False

    except Exception as e:
        print(f"        [ERROR] RPC upsert failed: {e}")
        return False

def process_technology(tech_name):
    """개별 기술 처리"""
    print(f"\n[PROCESS] Processing: {tech_name}")

    # 기술 정보 스크래핑
    scraped_info = search_and_scrape(tech_name)

    # 인기도 점수 계산
    popularity = get_tech_popularity_score(tech_name)

    # AI로 정보 향상
    ai_enhanced_data = enhance_with_ai(tech_name, scraped_info)

    if ai_enhanced_data:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        final_data = {
            'name': tech_name,
            'slug': create_slug(tech_name),
            'category': ai_enhanced_data.get('category'),
            'description': ai_enhanced_data.get('description'),
            'logo_url': ai_enhanced_data.get('logoUrl') or f"https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{create_slug(tech_name)}/{create_slug(tech_name)}-original.svg",
            'popularity': popularity,
            'learning_resources': ai_enhanced_data.get('learningResources', []),
            'ai_explanation': ai_enhanced_data.get('ai_explanation'),
            'homepage': scraped_info.get('homepage'),
            'repo': scraped_info.get('repo'),
            'project_suitability': ai_enhanced_data.get('project_suitability', []),
            'learning_difficulty': ai_enhanced_data.get('learning_difficulty', {}),
            'updated_at': now_utc
        }

        # Supabase 시도 후 로컬 저장
        if not upsert_to_supabase_rpc(final_data):
            save_to_local_json(final_data)
        else:
            save_to_local_json(final_data)  # 백업용으로도 저장

        return True

    return False

def main():
    print('[START] Starting Dynamic Tech Stack Discovery System...')

    # 제한된 모드 체크 (환경변수)
    limited_mode = os.environ.get('LIMITED_MODE', 'false').lower() == 'true'
    max_techs = int(os.environ.get('MAX_TECHS', '50'))

    if limited_mode:
        safe_print(f"[MODE] Limited mode: max {max_techs} technologies")

    # 1단계: 동적으로 인기 기술들 발견
    discovered_technologies = discover_trending_technologies()

    # 제한된 모드일 때 개수 제한
    if limited_mode:
        discovered_technologies = discovered_technologies[:max_techs]

    print(f"\n[LIST] 발견된 기술들: {', '.join(discovered_technologies[:10])}...")
    print(f"[COUNT] 총 처리할 기술 수: {len(discovered_technologies)}")

    # 2단계: 각 기술에 대해 상세 정보 수집 및 처리
    processed_count = 0
    failed_count = 0

    for i, tech in enumerate(discovered_technologies, 1):
        try:
            print(f"\n[{i}/{len(discovered_technologies)}] 처리 중: {tech}")

            if process_technology(tech):
                processed_count += 1
                print(f"    [SUCCESS] {tech} 처리 완료")
            else:
                failed_count += 1
                print(f"    [FAILED] {tech} 처리 실패")

            # Rate limiting (제한된 모드에서는 더 빠르게)
            sleep_time = 1 if limited_mode else 2
            time.sleep(sleep_time)

        except Exception as e:
            failed_count += 1
            print(f"    [ERROR] {tech} 처리 중 오류: {e}")

        # 제한된 모드에서 중간 진행상황 출력
        if limited_mode and i % 2 == 0:
            print(f"  [PROGRESS] 진행상황: {i}/{len(discovered_technologies)} ({(i/len(discovered_technologies)*100):.1f}%)")

    print(f'\n[COMPLETE] 동적 수집 완료!')
    print(f'[SUCCESS] 성공: {processed_count}개')
    print(f'[FAILED] 실패: {failed_count}개')
    print(f'[FILE] 결과는 stacks.json에 저장되었습니다.')

    # 요약 통계 출력
    try:
        with open('stacks.json', 'r', encoding='utf-8') as f:
            all_stacks = json.load(f)
            print(f'[STATS] 전체 데이터베이스: {len(all_stacks)}개 기술 스택')

            # 카테고리별 통계
            categories = {}
            for stack in all_stacks:
                cat = stack.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1

            print(f'[CATEGORY] 카테고리별 분포: {categories}')

    except Exception as e:
        print(f"[ERROR] 통계 생성 실패: {e}")

if __name__ == '__main__':
    main()