import argparse
import json
import os
import requests
from openai import OpenAI
import datetime
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import re
from urllib.parse import urljoin, urlparse
import asyncio
from crawl4ai import AsyncWebCrawler
import sys
import codecs
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
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        print("[WARNING] GEMINI_API_KEY not set. AI enhancement will be skipped.")
        genai_model = None
    else:
        # google-genai SDK 초기화
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        print("[SUCCESS] Gemini API configured with Google Search Grounding (google-genai SDK).")

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
    """Gemini Search를 이용한 최신 기술 트렌드 수집"""
    print("[SEARCH] Discovering trending technologies via Gemini Search...")

    if not genai_client:
        print("[WARNING] Gemini not available. Using fallback list.")
        return get_comprehensive_base_technologies()

    prompt = """
    Find 60 trending and popular technology stacks in 2024-2025.
    Focus on a mix of "Industry Standards" and "Emerging Trends".
    
    Include these specific categories:
    - AI Agents & LLM Ops (e.g., LangChain, AutoGPT, Pinecone)
    - Modern Web Frameworks (e.g., Next.js, Remix, SvelteKit)
    - Rust Ecosystem (e.g., Tauri, Actix, Axum)
    - Edge Computing & Serverless (e.g., Cloudflare Workers, Bun)
    - Next-Gen Databases (e.g., Supabase, Neon, SurrealDB)
    - DevOps & Infrastructure (e.g., Kubernetes, Terraform, Pulumi)
    
    Return ONLY a JSON array of strings. Example: ["Tech1", "Tech2", ...]
    """

    try:
        response = genai_client.models.generate_content(
            model='gemini-2.0-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        text = response.text.strip()
        
        # JSON 파싱
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        techs = json.loads(text.strip())
        
        # 기본 기술 목록도 추가하여 풍부하게 유지
        base_techs = get_comprehensive_base_technologies()
        combined_techs = list(set(techs + base_techs))
        
        print(f"[INFO] Discovered {len(combined_techs)} technologies.")
        return combined_techs
        
    except Exception as e:
        print(f"[ERROR] Discovery failed: {e}")
        return get_comprehensive_base_technologies()

def get_comprehensive_base_technologies():
    """기본적으로 포함해야 할 다양한 기술들 (Fallback)"""
    return [
        'Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust', 'C++',
        'React', 'Next.js', 'Vue.js', 'Angular', 'Svelte',
        'Node.js', 'Django', 'FastAPI', 'Spring Boot',
        'PostgreSQL', 'MongoDB', 'Redis', 'Supabase',
        'Docker', 'Kubernetes', 'AWS', 'Terraform',
        'Flutter', 'React Native', 'Swift', 'Kotlin',
        'TensorFlow', 'PyTorch', 'LangChain', 'OpenAI'
    ]

def create_slug(name):
    """기술명을 슬러그로 변환"""
    return name.lower().replace(' ', '-').replace('.', 'dot').replace('#', 'sharp').replace('+', 'plus')

def get_tech_popularity_score(tech_name):
    """기술의 인기도 점수 계산 (Gemini Search Grounding)"""
    if not genai_client:
        return 50

    prompt = f"""
    Determine the popularity score of '{tech_name}' in 2024-2025 on a scale of 0 to 100.
    
    STRICT SCORING RUBRIC (Do not inflate scores):
    - 90-100: Ubiquitous / Industry Standard (e.g., Python, React, AWS, Docker). Everyone knows it.
    - 75-89:  Mainstream / High Demand (e.g., TypeScript, Next.js, Kubernetes, Redis). Widely used in production.
    - 50-74:  Growing / Stable Niche (e.g., Svelte, Rust, Supabase, Flutter). Strong community but not universal.
    - 30-49:  New / Declining / Niche (e.g., Bun, jQuery, specialized libs). Early stage or legacy.
    - 0-29:   Obsolete / Unknown / Hobbyist only.
    
    Consider: GitHub stars, Job market demand, Stack Overflow trends, and Ecosystem size.
    BE CRITICAL. If a tech is new or niche, give it a lower score (e.g., 40-60).
    
    Return ONLY the integer number. Example: 85
    """
    
    try:
        response = genai_client.models.generate_content(
            model='gemini-2.0-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        score_text = response.text.strip()
        # 숫자만 추출
        import re
        match = re.search(r'\d+', score_text)
        if match:
            score = int(match.group())
            return min(100, max(0, score))
        return 50
    except Exception as e:
        print(f"    [WARNING] Popularity check failed: {e}")
        return 50


async def crawl_url(url):
    """Crawl4AI를 사용하여 URL의 콘텐츠를 마크다운으로 가져옴"""
    if not url:
        return ""
    
    # URL 보정 (프로토콜이 없으면 https:// 추가)
    if not url.startswith(('http://', 'https://', 'file://')):
        url = 'https://' + url
    
    print(f"    - [CRAWL] Crawling {url}...")
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
            if result.success:
                # 너무 긴 콘텐츠는 자름 (토큰 제한 고려)
                content = result.markdown
                if len(content) > 20000:
                    content = content[:20000] + "...(truncated)"
                return content
            else:
                print(f"        [WARNING] Crawl failed: {result.error_message}")
                return ""
    except Exception as e:
        print(f"        [ERROR] Crawl exception: {e}")
        return ""

def get_best_logo_url(tech_name, homepage_url):
    """최적의 로고 URL 찾기 (SVG Only: Devicon -> Simple Icons -> Gemini Search)"""
    
    slug = create_slug(tech_name)

    # 1. Devicon (SVG)
    devicon_url = f"https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{slug}/{slug}-original.svg"
    try:
        response = requests.head(devicon_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return devicon_url
    except Exception:
        pass

    # 2. Simple Icons (SVG) - 방대한 브랜드 아이콘 라이브러리
    simple_icons_url = f"https://cdn.simpleicons.org/{slug}"
    try:
        response = requests.head(simple_icons_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return simple_icons_url
    except Exception:
        pass

    # 3. Gemini Search로 SVG 로고 찾기 (Strict SVG)
    if genai_client:
        try:
            prompt = f"Find a direct URL for the official SVG logo of '{tech_name}'. Return ONLY the URL string. It MUST be an .svg file."
            response = genai_client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            url = response.text.strip()
            if url.startswith('http') and '.svg' in url:
                return url
        except Exception:
            pass

    return ""

def enhance_with_ai(tech_name, scraped_info, crawled_content=""):
    """AI로 기술 정보 향상 (Gemini 사용)"""
    print(f"    - [AI] Enhancing '{tech_name}' data with AI (Gemini)...")

    # Gemini 모델이 없으면 기본값 반환
    if not genai_client:
        print(f"        [WARNING] Gemini model not available. Using default data for {tech_name}")
        return {
            "description": f"{tech_name}은(는) 인기있는 개발 기술입니다.",
            "category": "language",
            "description": f"{tech_name}은(는) 인기있는 개발 기술입니다.",
            "category": "language",
            "color": "#6B7280",
            "learningResources": ["공식 문서", "온라인 튜토리얼", "커뮤니티 포럼"]
        }

    # 크롤링된 콘텐츠가 있으면 프롬프트에 포함
    context_str = f"수집된 정보: {scraped_info}"
    if crawled_content:
        context_str += f"\n\n[공식 홈페이지 콘텐츠 요약]\n{crawled_content[:5000]}"

    prompt = f"""
    ## 역할 및 전문성
    당신은 15년 경력의 CTO이자 수석 소프트웨어 아키텍트입니다. 기술의 장단점을 냉철하게 분석하고, 비즈니스와 엔지니어링 관점에서 최적의 기술 스택을 제안하는 능력이 탁월합니다.

    ## 분석 대상 기술
    기술명: {tech_name}
    {context_str}

    ## 분석 목표
    개발자와 의사결정권자가 이 기술을 도입할지 판단할 수 있도록, 단순한 소개가 아닌 "비판적이고 실무적인 분석"을 제공하세요. 마케팅 용어보다는 실제 엔지니어링 가치에 집중하세요.
    
    (이하 생략, 기존 프롬프트와 동일)
    ## 출력 형식
    다음 JSON 스키마에 정확히 맞춰 모든 문자열을 한국어로 작성하세요. 마크다운 코드 블록 없이 순수 JSON만 출력하세요:

    {{
        "description": "기술의 핵심 정의와 주요 목적을 명확하고 간결하게 설명 (20-30자)",
        "category": "다음 중 정확히 하나만 선택: frontend, backend, database, mobile, devops, language, framework, library, tool",
        "ai_explanation": "AI가 기술에 대해 심층적으로 설명하는 글 (200-300자). 크롤링된 콘텐츠 내용을 적극 반영하여 구체적으로 작성.",
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
    - 마크다운 포맷팅 사용 금지 (```json 등 포함 금지)
    - JSON 형식 엄격 준수
    - 모든 문자열 값은 완전한 한국어로 작성 (logoUrl, color 제외)
    - 허위 정보나 과장 금지
    - 응답 길이: description 100-200자, learningResources 각 항목 50자 이내
    - logoUrl은 실제 존재하는 URL만 사용, 없으면 null
    - color는 반드시 # 포함한 HEX 코드 형식

    지금 위 기준에 따라 '{tech_name}' 기술에 대한 완벽한 분석을 JSON 형태로 제공하세요.
    """

    try:
        # 재시도 로직 추가 (Rate Limit 대응)
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                response = genai_client.models.generate_content(
                    model='gemini-2.0-flash-lite',
                    contents=prompt
                )
                break
            except Exception as e:
                if "429" in str(e) or "Quota exceeded" in str(e):
                    if attempt < max_retries - 1:
                        print(f"        [WARNING] Rate limit hit. Retrying in {retry_delay}s... ({attempt+1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                raise e
        
        # 응답 텍스트 정제 (마크다운 코드 블록 제거)
        json_text = response.text.strip()
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.startswith('```'):
            json_text = json_text[3:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
            
        return json.loads(json_text.strip())
    except Exception as e:
        print(f"        [ERROR] AI enhancement failed: {e}")
        return None

def search_and_scrape(tech_name):
    """기술에 대한 정보 스크래핑 (Gemini Search Grounding)"""
    print(f"    - [SEARCH] Finding info for '{tech_name}'...")
    
    if not genai_client:
        return {}

    prompt = f"""
    Find the official homepage URL and the main GitHub repository URL for '{tech_name}'.
    
    Return ONLY a JSON object. Example:
    {{
        "homepage": "https://...",
        "repo": "https://github.com/..."
    }}
    If not found, use null.
    """

    try:
        response = genai_client.models.generate_content(
            model='gemini-2.0-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        text = response.text.strip()
        
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        print(f"    [ERROR] Info search failed for {tech_name}: {e}")
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
            'p_logo_url': data.get('logoUrl'),
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

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ... (imports remain the same)

async def process_technology(tech_name):
    """개별 기술 처리 (Async)"""
    start_time = time.time()
    print(f"\n[PROCESS] Processing: {tech_name}")

    # 1. 기술 정보 검색 (Gemini Search)
    t1 = time.time()
    scraped_info = search_and_scrape(tech_name)
    t2 = time.time()
    print(f"    [TIME] Searching '{tech_name}': {t2 - t1:.2f}s")
    
    # 2. 홈페이지 크롤링 (Crawl4AI)
    crawled_content = ""
    if scraped_info.get('homepage'):
        t_crawl_start = time.time()
        crawled_content = await crawl_url(scraped_info['homepage'])
        t_crawl_end = time.time()
        print(f"    [TIME] Crawling '{tech_name}': {t_crawl_end - t_crawl_start:.2f}s")

    # 3. 인기도 점수 계산
    t3 = time.time()
    popularity = get_tech_popularity_score(tech_name)
    t4 = time.time()
    print(f"    [TIME] Popularity '{tech_name}': {t4 - t3:.2f}s")

    # 4. AI로 정보 향상 (크롤링 데이터 포함)
    t5 = time.time()
    ai_enhanced_data = enhance_with_ai(tech_name, scraped_info, crawled_content)
    t6 = time.time()
    print(f"    [TIME] AI Enhancement '{tech_name}': {t6 - t5:.2f}s")

    # 5. 로고 URL 결정
    logo_url = get_best_logo_url(tech_name, scraped_info.get('homepage'))

    if ai_enhanced_data:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        final_data = {
            'name': tech_name,
            'slug': create_slug(tech_name),
            'category': ai_enhanced_data.get('category'),
            'description': ai_enhanced_data.get('description'),
            'logoUrl': logo_url,
            'popularity': popularity,
            'learning_resources': ai_enhanced_data.get('learningResources', []),
            'ai_explanation': ai_enhanced_data.get('ai_explanation'),
            'homepage': scraped_info.get('homepage'),
            'repo': scraped_info.get('repo'),
            'project_suitability': ai_enhanced_data.get('project_suitability', []),
            'learning_difficulty': ai_enhanced_data.get('learning_difficulty', {}),
            'updated_at': now_utc
        }

        # 5. Supabase 시도 후 로컬 저장
        t7 = time.time()
        if not upsert_to_supabase_rpc(final_data):
            save_to_local_json(final_data)
        else:
            save_to_local_json(final_data)  # 백업용으로도 저장
        t8 = time.time()
        print(f"    [TIME] DB Upsert '{tech_name}': {t8 - t7:.2f}s")
        
        print(f"    [SUCCESS] {tech_name} Total Time: {t8 - start_time:.2f}s")
        return True

    return False

def get_existing_slugs():
    """Supabase에서 이미 존재하는 기술들의 slug 목록을 가져옴"""
    if not supabase:
        return set()
    
    try:
        # 모든 기술의 slug만 조회 (페이지네이션 처리 필요할 수 있으나 일단 1000개로 제한)
        response = supabase.table('techs').select('slug').limit(1000).execute()
        if response.data:
            return {item['slug'] for item in response.data}
        return set()
    except Exception as e:
        print(f"[WARNING] Failed to fetch existing slugs: {e}")
        return set()

def _resolve_limit(max_techs_arg, force_limited_mode):
    """환경변수/CLI 조합으로 최대 처리 기술 수 계산"""
    limited_mode_env = os.environ.get('LIMITED_MODE', 'false').lower() == 'true'
    limited_mode = force_limited_mode or limited_mode_env

    env_max = os.environ.get('MAX_TECHS')
    env_max_value = None
    if env_max:
        try:
            env_max_value = int(env_max)
        except ValueError:
            safe_print(f"[WARNING] Invalid MAX_TECHS value '{env_max}'. 숫자로 설정해주세요.")

    resolved_max = max_techs_arg if max_techs_arg is not None else env_max_value
    if resolved_max is not None and resolved_max < 1:
        safe_print("[WARNING] max techs는 1 이상이어야 합니다. 1로 설정합니다.")
        resolved_max = 1

    if limited_mode and resolved_max is None:
        resolved_max = 50  # 과거 기본값 유지

    if resolved_max is not None:
        safe_print(f"[MODE] 기술 수 제한 활성화: 최대 {resolved_max}개 수집")

    return limited_mode or resolved_max is not None, resolved_max


async def main(max_techs=None, force_limited_mode=False, check_only=False):
    if check_only:
        print('[CHECK] Checking available technologies...')
        discovered = discover_trending_technologies()
        existing = get_existing_slugs()
        new_techs = [t for t in discovered if create_slug(t) not in existing]
        print(f"[RESULT] Available: {len(new_techs)}")
        return

    print('[START] Starting Dynamic Tech Stack Discovery System (Parallel Mode)...')

    limited_mode, max_limit = _resolve_limit(max_techs, force_limited_mode)

    # 1단계: 동적으로 인기 기술들 발견
    discovered_technologies = discover_trending_technologies()

    # 이미 존재하는 기술 필터링
    print("[CHECK] Checking for existing technologies in database...")
    existing_slugs = get_existing_slugs()
    print(f"[INFO] Found {len(existing_slugs)} existing technologies.")

    new_technologies = []
    for tech in discovered_technologies:
        slug = create_slug(tech)
        if slug not in existing_slugs:
            new_technologies.append(tech)
    
    skipped_count = len(discovered_technologies) - len(new_technologies)
    print(f"[INFO] Skipped {skipped_count} technologies that already exist.")
    
    discovered_technologies = new_technologies

    if not discovered_technologies:
        print("[INFO] No new technologies to process.")
        return

    # 개수 제한 적용
    if max_limit is not None:
        discovered_technologies = discovered_technologies[:max_limit]

    print(f"\n[LIST] 새로 처리할 기술들: {', '.join(discovered_technologies[:10])}...")
    print(f"[COUNT] 총 처리할 기술 수: {len(discovered_technologies)}")

    # 2단계: 병렬 처리 (Async)
    processed_count = 0
    failed_count = 0
    
    # 동시에 실행할 작업 수
    MAX_CONCURRENT = 2
    print(f"[INFO] 병렬 처리 시작 (Max Concurrent: {MAX_CONCURRENT})")

    # 세마포어로 동시 실행 제한
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def sem_task(tech):
        async with semaphore:
            try:
                return await process_technology(tech)
            except Exception as e:
                print(f"    [ERROR] {tech} 처리 중 예외 발생: {e}")
                return False

    tasks = [sem_task(tech) for tech in discovered_technologies]
    results = await asyncio.gather(*tasks)

    processed_count = sum(1 for r in results if r)
    failed_count = len(results) - processed_count

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
    parser = argparse.ArgumentParser(description="Dynamic Tech Discovery Runner")
    parser.add_argument('--max-techs', type=int, default=None, help='수집할 최대 기술 수')
    parser.add_argument('--limited-mode', action='store_true', help='LIMITED_MODE 강제 활성화')
    parser.add_argument('--check-only', action='store_true', help='수집 가능한 기술 수만 확인')
    args = parser.parse_args()
    
    asyncio.run(main(max_techs=args.max_techs, force_limited_mode=args.limited_mode, check_only=args.check_only))
