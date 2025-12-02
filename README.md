# AI StackList Manager (StackLoad Crawler)

**AI StackList Manager**는 최신 개발 기술 트렌드를 AI(Gemini)로 수집하고, Supabase 데이터베이스와 동기화하며 관리할 수 있는 강력한 데스크톱 애플리케이션입니다.

## 주요 기능 (Key Features)

### 1. 직관적인 GUI 관리자 (Tech Stack Manager)

- **VS Code 스타일 디자인**: 개발자에게 친숙한 Dark 테마 및 모던한 UI.
- **다중 선택 & 일괄 처리**: `Ctrl/Cmd` + 클릭으로 개별 선택, `Shift` + 클릭으로 범위 선택 후 **일괄 삭제** 가능.
- **실시간 로그 패널**: 크기 조절이 가능한 하단 로그 패널에서 AI 수집 및 DB 동기화 상태 실시간 확인.
- **상세 편집**: 기술 스택의 인기도, 난이도, 설명, AI 분석 내용을 손쉽게 편집.

### 2. AI 기반 기술 탐색 (Dynamic Tech Discovery)

- **Google Gemini Pro 연동**: 최신 트렌드, 인기도, 로고(SVG) 등을 AI가 자동으로 수집 및 분석.
- **엄격한 인기도 분석**: 0~100점 척도의 엄격한 기준(Rubric)을 적용하여 신뢰성 있는 인기도 점수 산출.
- **CTO 페르소나 분석**: 단순 설명이 아닌, 실무 관점에서의 장단점 및 프로젝트 적합성 분석 제공.
- **트렌드 키워드**: AI Agents, Rust Ecosystem, Edge Computing 등 최신 분야 집중 탐색.

### 3. Supabase 실시간 동기화

- **자동 동기화**: 기술 스택 추가, 수정, 삭제 시 Supabase DB에 즉시 반영.
- **데이터 무결성**: 로컬 `stacks.json`과 원격 DB 간의 데이터 일관성 유지.

---

## 시작하기 (Getting Started)

### 필수 조건 (Prerequisites)

- Python 3.9 이상
- Google Gemini API Key
- Supabase Project (URL & Key)

### 설치 (Installation)

1. **저장소 클론**

   ```bash
   git clone https://github.com/Aptsii/StackLoad_Crawler.git
   cd StackLoad_Crawler
   ```

2. **의존성 패키지 설치**

   ```bash
   pip install -r requirements.txt
   ```

3. **환경 변수 설정**
   `.env` 파일을 생성하고 다음 정보를 입력하세요:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   ```

### 실행 (Usage)

**관리자 앱 실행 (권장)**

```bash
python run_manager.py
```

앱이 실행되면 의존성을 확인하고 GUI가 열립니다.

---

## 프로젝트 구조 (Project Structure)

- `final_tech_stack_manager.py`: 메인 GUI 애플리케이션 소스 코드 (CustomTkinter).
- `dynamic_tech_discovery.py`: AI 기술 탐색 및 데이터 수집 스크립트.
- `run_manager.py`: 앱 실행 런처 (의존성 체크 포함).
- `stacks.json`: 로컬 데이터 저장소.
- `requirements.txt`: 파이썬 패키지 의존성 목록.

---

## 사용 팁 (Tips)

- **데이터 수집**: 앱 하단의 `Auto Collect` 버튼을 누르면 AI가 새로운 기술을 찾아옵니다.
- **다중 삭제**: 목록에서 `Shift` 또는 `Ctrl` 키를 사용하여 여러 항목을 선택한 후 `Delete Stack` 버튼을 누르세요.
- **로그 확인**: 하단 로그 패널의 경계선을 드래그하여 높이를 조절할 수 있습니다.
