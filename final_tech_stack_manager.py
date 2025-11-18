import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import tkinter.font as tkFont
import json
import threading
import subprocess
import os
from datetime import datetime
import webbrowser
import queue
import time
from supabase import create_client, Client
from dotenv import load_dotenv

class TechStackManager:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Stack List 관리자")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')

        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(family="맑은 고딕")

        # 로그 큐 (백그라운드 작업에서 GUI로 메시지 전달)
        self.log_queue = queue.Queue()

        # 로그 텍스트 위젯 초기화 (UI 설정 전)
        self.log_text = None

        # Supabase 관련 속성 초기화
        self.supabase = None
        self.supabase_enabled = False

        # 데이터 로드
        self.stacks_data = self.load_stacks_data()

        # 메인 UI 구성
        self.setup_ui()

        # Supabase 클라이언트 초기화 (UI 설정 후)
        self.init_supabase()

        # 데이터 새로고침
        self.refresh_stack_list()

        # 로그 큐 주기적 확인
        self.check_log_queue()

    def init_supabase(self):
        """Supabase 클라이언트 초기화"""
        try:
            load_dotenv()
            SUPABASE_URL = os.environ.get('SUPABASE_URL')
            SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

            self.add_log(f"환경변수 확인 - URL: {SUPABASE_URL[:30] if SUPABASE_URL else 'None'}...")
            self.add_log(f"환경변수 확인 - KEY: {SUPABASE_KEY[:20] if SUPABASE_KEY else 'None'}...")

            if SUPABASE_URL and SUPABASE_KEY:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                self.add_log("Supabase 클라이언트 생성 완료")

                # 실제 연결 테스트
                if self.test_supabase_connection():
                    self.supabase_enabled = True
                    self.add_log("Supabase 연결 테스트 성공!")
                    self.update_supabase_status("연결됨", "green")
                else:
                    self.supabase_enabled = False
                    self.add_log("Supabase 연결 테스트 실패")
                    self.update_supabase_status("연결 실패", "red")
            else:
                self.supabase = None
                self.supabase_enabled = False
                self.add_log("Supabase 환경변수가 설정되지 않았습니다.")
                self.update_supabase_status("환경변수 없음", "red")
        except Exception as e:
            self.supabase = None
            self.supabase_enabled = False
            self.add_log(f"Supabase 초기화 실패: {e}")
            self.update_supabase_status("초기화 실패", "red")

    def test_supabase_connection(self):
        """Supabase 연결 테스트"""
        try:
            self.add_log("Supabase 연결 테스트 중...")
            # 테이블 접근 테스트
            result = self.supabase.table('techs').select('*').limit(1).execute()
            self.add_log("테이블 접근 테스트 성공")

            # RPC 함수 테스트 (선택적)
            try:
                test_result = self.supabase.rpc('upsert_tech_stack', {
                    'p_name': 'connection_test',
                    'p_slug': 'connection-test'
                }).execute()

                # 테스트 데이터 삭제
                self.supabase.table('techs').delete().eq('slug', 'connection-test').execute()
                self.add_log("RPC 함수 테스트 성공")
                return True
            except Exception as rpc_error:
                self.add_log(f"RPC 함수 없음 (직접 삽입/업데이트 사용): {rpc_error}")
                # RPC 함수가 없어도 기본 연결은 성공으로 처리
                return True

        except Exception as e:
            self.add_log(f"연결 테스트 실패: {e}")
            return False

    def update_supabase_status(self, status_text, color):
        """Supabase 상태 업데이트"""
        if hasattr(self, 'supabase_status'):
            self.supabase_status.configure(text=f"Supabase: {status_text}", foreground=color)

    def reconnect_supabase(self):
        """Supabase 재연결"""
        self.add_log("Supabase 재연결을 시도합니다...")
        self.update_supabase_status("재연결 중...", "orange")
        self.init_supabase()

    def sync_with_supabase(self):
        """Supabase와 로컬 데이터 동기화"""
        if not self.supabase_enabled:
            messagebox.showwarning("경고", "Supabase가 연결되지 않았습니다.")
            return

        def sync_in_background():
            try:
                self.log_queue.put("데이터베이스 동기화를 시작합니다...")

                # 1. Supabase에서 모든 데이터 가져오기
                self.log_queue.put("Supabase에서 데이터를 가져오는 중...")
                supabase_data = self.get_all_supabase_data()

                # 2. 로컬 데이터 로드
                local_data = self.load_stacks_data()

                # 3. 데이터 비교 및 동기화
                sync_result = self.compare_and_sync_data(supabase_data, local_data)

                # 4. 결과 보고
                self.log_queue.put(f"동기화 완료: {sync_result}")

                # 5. GUI 새로고침
                self.root.after(100, self.refresh_stack_list)
                self.root.after(200, lambda: messagebox.showinfo("완료", f"동기화가 완료되었습니다!\n\n{sync_result}"))

            except Exception as e:
                self.log_queue.put(f"동기화 중 오류 발생: {e}")
                self.root.after(100, lambda: messagebox.showerror("오류", f"동기화 실패: {e}"))

        # 백그라운드에서 실행
        threading.Thread(target=sync_in_background, daemon=True).start()

    def get_all_supabase_data(self):
        """Supabase에서 모든 데이터 가져오기"""
        try:
            response = self.supabase.table('techs').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            self.add_log(f"Supabase 데이터 조회 실패: {e}")
            return []

    def compare_and_sync_data(self, supabase_data, local_data):
        """데이터 비교 및 동기화"""
        # slug를 키로 하는 딕셔너리 생성
        supabase_dict = {item.get('slug'): item for item in supabase_data}
        local_dict = {item.get('slug'): item for item in local_data}

        # 통계
        added_to_local = 0
        updated_in_local = 0
        added_to_supabase = 0
        updated_in_supabase = 0

        # Supabase에만 있는 데이터를 로컬에 추가/업데이트
        for slug, supabase_item in supabase_dict.items():
            if slug not in local_dict:
                # Supabase에만 있음 -> 로컬에 추가
                self.log_queue.put(f"로컬에 추가: {supabase_item.get('name')}")
                local_data.append(self.convert_supabase_to_local_format(supabase_item))
                added_to_local += 1
            else:
                # 양쪽에 있음 -> 최신 업데이트 시간 비교
                local_item = local_dict[slug]
                supabase_updated = supabase_item.get('updated_at', '')
                local_updated = local_item.get('updated_at', '')

                if supabase_updated > local_updated:
                    # Supabase가 더 최신 -> 로컬 업데이트
                    self.log_queue.put(f"로컬 업데이트: {supabase_item.get('name')}")
                    for i, item in enumerate(local_data):
                        if item.get('slug') == slug:
                            local_data[i] = self.convert_supabase_to_local_format(supabase_item)
                            break
                    updated_in_local += 1

        # 로컬에만 있는 데이터를 Supabase에 추가/업데이트
        for slug, local_item in local_dict.items():
            if slug not in supabase_dict:
                # 로컬에만 있음 -> Supabase에 추가
                self.log_queue.put(f"Supabase에 추가: {local_item.get('name')}")
                self.save_to_supabase(local_item)
                added_to_supabase += 1
            else:
                # 양쪽에 있음 -> 최신 업데이트 시간 비교
                supabase_item = supabase_dict[slug]
                supabase_updated = supabase_item.get('updated_at', '')
                local_updated = local_item.get('updated_at', '')

                if local_updated > supabase_updated:
                    # 로컬이 더 최신 -> Supabase 업데이트
                    self.log_queue.put(f"Supabase 업데이트: {local_item.get('name')}")
                    self.save_to_supabase(local_item)
                    updated_in_supabase += 1

        # 로컬 데이터 저장
        self.stacks_data = local_data
        self.save_stacks_data()

        # 결과 생성
        result = f"로컬 추가: {added_to_local}개, 로컬 업데이트: {updated_in_local}개\nSupabase 추가: {added_to_supabase}개, Supabase 업데이트: {updated_in_supabase}개"
        return result

    def convert_supabase_to_local_format(self, supabase_item):
        """Supabase 데이터를 로컬 형식으로 변환"""
        return {
            'name': supabase_item.get('name', ''),
            'slug': supabase_item.get('slug', ''),
            'category': supabase_item.get('category', ''),
            'description': supabase_item.get('description', ''),
            'logo_url': supabase_item.get('logo_url', ''),
            'popularity': supabase_item.get('popularity', 0),
            'learning_resources': supabase_item.get('learning_resources', []),
            'ai_explanation': supabase_item.get('ai_explanation', ''),
            'homepage': supabase_item.get('homepage', ''),
            'repo': supabase_item.get('repo', ''),
            'project_suitability': supabase_item.get('project_suitability', []),
            'learning_difficulty': supabase_item.get('learning_difficulty', {}),
            'updated_at': supabase_item.get('updated_at', '')
        }

    def load_stacks_data(self):
        """stacks.json 파일에서 데이터 로드"""
        try:
            with open('stacks.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_stacks_data(self):
        """stacks.json 파일에 데이터 저장"""
        try:
            with open('stacks.json', 'w', encoding='utf-8') as f:
                json.dump(self.stacks_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("오류", f"데이터 저장 실패: {e}")
            return False

    def setup_ui(self):
        """메인 UI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 타이틀
        title_label = ttk.Label(main_frame, text="AI Stack List 관리자",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # 상단 컨트롤 패널
        self.setup_control_panel(main_frame)

        # 메인 컨텐츠 영역 (3개 패널로 구성)
        self.setup_main_content(main_frame)

        # 하단 상태바
        self.setup_status_bar(main_frame)

        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

    def setup_control_panel(self, parent):
        """상단 제어 패널 구성"""
        control_frame = ttk.LabelFrame(parent, text="제어 패널", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 버튼들
        ttk.Button(control_frame, text="새로고침",
                  command=self.refresh_stack_list).grid(row=0, column=0, padx=(0, 5))

        ttk.Button(control_frame, text="새 기술 추가",
                  command=self.add_new_stack).grid(row=0, column=1, padx=5)

        ttk.Button(control_frame, text="자동 수집",
                  command=self.run_auto_discovery).grid(row=0, column=2, padx=5)

        ttk.Button(control_frame, text="웹사이트",
                  command=self.open_website).grid(row=0, column=3, padx=5)

        ttk.Button(control_frame, text="통계",
                  command=self.show_statistics).grid(row=0, column=4, padx=5)

        ttk.Button(control_frame, text="로그 지우기",
                  command=self.clear_log).grid(row=0, column=5, padx=5)

        ttk.Button(control_frame, text="재연결",
                  command=self.reconnect_supabase).grid(row=0, column=6, padx=5)

        ttk.Button(control_frame, text="DB 동기화",
                  command=self.sync_with_supabase).grid(row=0, column=7, padx=5)

        # Supabase 상태 표시
        self.supabase_status = ttk.Label(control_frame,
                                        text="Supabase: 초기화 중...",
                                        foreground="orange")
        self.supabase_status.grid(row=0, column=8, padx=10)

        # 검색 영역
        ttk.Label(control_frame, text="검색:").grid(row=0, column=9, padx=(20, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=20)
        search_entry.grid(row=0, column=10, padx=5)

    def setup_main_content(self, parent):
        """메인 컨텐츠 영역 구성 (3개 패널)"""
        content_frame = ttk.Frame(parent)
        content_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=2)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # 왼쪽: 기술 스택 리스트
        self.setup_stack_list(content_frame)

        # 가운데: 상세 정보 및 편집
        self.setup_detail_panel(content_frame)

        # 오른쪽: 로그 패널
        self.setup_log_panel(content_frame)

    def setup_stack_list(self, parent):
        """기술 스택 리스트 구성"""
        list_frame = ttk.LabelFrame(parent, text="기술 스택 목록", padding="5")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 트리뷰 생성
        columns = ('이름', '카테고리', '인기도', '난이도')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # 컬럼 설정
        self.tree.heading('이름', text='기술명')
        self.tree.heading('카테고리', text='카테고리')
        self.tree.heading('인기도', text='인기도')
        self.tree.heading('난이도', text='난이도')

        self.tree.column('이름', width=150, anchor='w')
        self.tree.column('카테고리', width=120, anchor='center')
        self.tree.column('인기도', width=90, anchor='center')
        self.tree.column('난이도', width=90, anchor='center')

        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 이벤트 바인딩
        self.tree.bind('<<TreeviewSelect>>', self.on_stack_select)
        self.tree.bind('<Double-1>', self.on_stack_double_click)

    def setup_detail_panel(self, parent):
        """상세 정보 및 편집 패널 구성"""
        detail_frame = ttk.LabelFrame(parent, text="상세 정보 및 편집", padding="10")
        detail_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        detail_frame.columnconfigure(1, weight=1)

        # 기본 정보
        row = 0
        ttk.Label(detail_frame, text="기술명:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(detail_frame, textvariable=self.name_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1
        ttk.Label(detail_frame, text="카테고리:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.category_var = tk.StringVar()
        category_combo = ttk.Combobox(detail_frame, textvariable=self.category_var,
                                     values=['frontend', 'backend', 'database', 'mobile', 'devops', 'language'])
        category_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1
        ttk.Label(detail_frame, text="인기도:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.popularity_var = tk.IntVar()
        popularity_frame = ttk.Frame(detail_frame)
        popularity_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        popularity_scale = ttk.Scale(popularity_frame, from_=0, to=100, variable=self.popularity_var, orient=tk.HORIZONTAL)
        popularity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.popularity_label = ttk.Label(popularity_frame, text="0%")
        self.popularity_label.pack(side=tk.RIGHT, padx=(5, 0))
        popularity_scale.configure(command=self.update_popularity_label)

        row += 1
        ttk.Label(detail_frame, text="홈페이지:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.homepage_var = tk.StringVar()
        ttk.Entry(detail_frame, textvariable=self.homepage_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1
        ttk.Label(detail_frame, text="GitHub:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.repo_var = tk.StringVar()
        ttk.Entry(detail_frame, textvariable=self.repo_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1
        ttk.Label(detail_frame, text="로고 URL:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.logo_url_var = tk.StringVar()
        ttk.Entry(detail_frame, textvariable=self.logo_url_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1
        ttk.Label(detail_frame, text="설명:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        self.description_text = scrolledtext.ScrolledText(detail_frame, height=4, width=40)
        self.description_text.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        row += 1
        ttk.Label(detail_frame, text="AI 설명:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        self.ai_explanation_text = scrolledtext.ScrolledText(detail_frame, height=4, width=40)
        self.ai_explanation_text.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        # 버튼들
        row += 1
        button_frame = ttk.Frame(detail_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="저장", command=self.save_current_stack).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="삭제", command=self.delete_current_stack).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="홈페이지", command=self.open_homepage).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="GitHub", command=self.open_repo).pack(side=tk.LEFT, padx=5)

        # 현재 선택된 스택 인덱스
        self.current_stack_index = -1

    def setup_log_panel(self, parent):
        """로그 패널 구성"""
        log_frame = ttk.LabelFrame(parent, text="실행 로그", padding="5")
        log_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # 로그 텍스트 영역
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=40)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 로그 텍스트 설정
        self.log_text.configure(state='disabled')

    def setup_status_bar(self, parent):
        """하단 상태바 구성"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        self.status_var = tk.StringVar()
        self.status_var.set("준비")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        # 오른쪽에 총 개수 표시
        self.count_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.count_var).pack(side=tk.RIGHT)

    def add_log(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        # 로그 텍스트 위젯이 초기화되었는지 확인
        if self.log_text is not None:
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, log_message)
            self.log_text.configure(state='disabled')
            self.log_text.see(tk.END)

            # UI 업데이트 강제 실행
            self.root.update_idletasks()
        else:
            # UI가 아직 준비되지 않았다면 콘솔에 출력
            print(log_message.strip())

    def clear_log(self):
        """로그 지우기"""
        if self.log_text is not None:
            self.log_text.configure(state='normal')
            self.log_text.delete('1.0', tk.END)
            self.log_text.configure(state='disabled')
            self.add_log("로그가 지워졌습니다.")

    def check_log_queue(self):
        """로그 큐에서 메시지 확인 (백그라운드 작업용)"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.add_log(message)
        except queue.Empty:
            pass
        finally:
            # 100ms마다 큐 확인
            self.root.after(100, self.check_log_queue)

    def update_popularity_label(self, value):
        """인기도 슬라이더 라벨 업데이트"""
        self.popularity_label.config(text=f"{int(float(value))}%")

    def refresh_stack_list(self):
        """기술 스택 리스트 새로고침"""
        self.add_log("기술 스택 목록을 새로고침합니다.")

        # 기존 데이터 클리어
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 데이터 다시 로드
        self.stacks_data = self.load_stacks_data()

        # 검색 필터 적용
        search_term = self.search_var.get().lower()
        filtered_data = []

        for stack in self.stacks_data:
            if (search_term in stack.get('name', '').lower() or
                search_term in stack.get('category', '').lower()):
                filtered_data.append(stack)

        # 트리뷰에 데이터 추가
        for i, stack in enumerate(filtered_data):
            # 난이도 계산 (stars 기반)
            difficulty = self.calculate_difficulty_from_stars(stack.get('learning_difficulty', {}))

            # 인기도 표시 개선
            popularity = stack.get('popularity', 0)
            popularity_display = f"{popularity}%" if popularity > 0 else "N/A"

            # 카테고리 한글화
            category = stack.get('category', 'N/A')
            category_mapping = {
                'frontend': '프론트엔드',
                'backend': '백엔드',
                'database': '데이터베이스',
                'devops': 'DevOps',
                'mobile': '모바일',
                'language': '언어',
                'framework': '프레임워크',
                '프론트엔드': '프론트엔드',
                '백엔드': '백엔드'
            }
            category_display = category_mapping.get(category.lower(), category)

            # 난이도 표시
            difficulty_display = difficulty

            self.tree.insert('', 'end', values=(
                stack.get('name', 'N/A'),
                category_display,
                popularity_display,
                difficulty_display
            ))

        # 상태 업데이트
        self.count_var.set(f"총 {len(filtered_data)}개 기술 스택")
        self.status_var.set(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")
        self.add_log(f"총 {len(filtered_data)}개 기술 스택을 로드했습니다.")

    def on_search_change(self, *args):
        """검색어 변경 시 호출"""
        self.refresh_stack_list()

    def on_stack_select(self, event):
        """기술 스택 선택 시 호출"""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        stack_name = item['values'][0]

        # 해당 스택 데이터 찾기
        for i, stack in enumerate(self.stacks_data):
            if stack.get('name') == stack_name:
                self.load_stack_to_editor(stack, i)
                break

    def on_stack_double_click(self, event):
        """기술 스택 더블클릭 시 홈페이지 열기"""
        self.open_homepage()

    def load_stack_to_editor(self, stack, index):
        """선택된 스택 데이터를 편집기에 로드"""
        self.current_stack_index = index

        # 기본 정보 로드
        self.name_var.set(stack.get('name', ''))
        self.category_var.set(stack.get('category', ''))
        popularity = stack.get('popularity', 0)
        self.popularity_var.set(popularity)
        self.update_popularity_label(popularity)
        self.homepage_var.set(stack.get('homepage', ''))
        self.repo_var.set(stack.get('repo', ''))
        self.logo_url_var.set(stack.get('logo_url', ''))

        # 텍스트 영역 로드
        self.description_text.delete('1.0', tk.END)
        self.description_text.insert('1.0', stack.get('description', ''))
        self.ai_explanation_text.delete('1.0', tk.END)
        self.ai_explanation_text.insert('1.0', stack.get('ai_explanation', ''))

    def save_current_stack(self):
        """현재 편집 중인 스택 저장"""
        if self.current_stack_index == -1:
            messagebox.showwarning("경고", "저장할 스택이 선택되지 않았습니다.")
            return

        stack_name = self.name_var.get()
        self.add_log(f"'{stack_name}' 기술 스택을 저장하는 중...")

        # 편집된 데이터 수집
        updated_stack = self.stacks_data[self.current_stack_index].copy()
        updated_stack.update({
            'name': stack_name,
            'category': self.category_var.get(),
            'popularity': self.popularity_var.get(),
            'description': self.description_text.get('1.0', tk.END).strip(),
            'logo_url': self.logo_url_var.get(),
            'learning_resources': updated_stack.get('learning_resources', []),
            'ai_explanation': self.ai_explanation_text.get('1.0', tk.END).strip(),
            'homepage': self.homepage_var.get(),
            'repo': self.repo_var.get(),
            'project_suitability': updated_stack.get('project_suitability', []),
            'learning_difficulty': updated_stack.get('learning_difficulty', {}),
            'updated_at': datetime.now().isoformat()
        })

        # 데이터 업데이트
        self.stacks_data[self.current_stack_index] = updated_stack

        # 로컬 파일 저장
        if self.save_stacks_data():
            # Supabase 업데이트 시도
            if self.supabase_enabled:
                self.save_to_supabase(updated_stack)

            self.refresh_stack_list()
            self.status_var.set("저장 완료!")
            self.add_log(f"'{stack_name}' 기술 스택이 성공적으로 저장되었습니다.")
            messagebox.showinfo("성공", "기술 스택이 성공적으로 저장되었습니다.")

    def save_to_supabase(self, stack_data):
        """Supabase에 데이터 저장 (상세 로깅 포함)"""
        if not self.supabase_enabled:
            self.add_log(f"[SKIP] Supabase가 비활성화되어 '{stack_data['name']}' 저장을 건너뜁니다.")
            return False

        try:
            self.add_log(f"[SUPABASE] '{stack_data['name']}' 저장 시작...")
            self.add_log(f"[DEBUG] 데이터: name={stack_data['name']}, slug={stack_data.get('slug')}")

            # 1. RPC 함수 시도
            try:
                self.add_log(f"[RPC] upsert_tech_stack 함수 호출 중...")
                response = self.supabase.rpc('upsert_tech_stack', {
                    'p_name': stack_data['name'],
                    'p_slug': stack_data.get('slug'),
                    'p_category': stack_data.get('category'),
                    'p_description': stack_data.get('description'),
                    'p_logo_url': stack_data.get('logo_url'),
                    'p_popularity': int(stack_data.get('popularity', 75)),
                    'p_learning_resources': stack_data.get('learning_resources', []),
                    'p_ai_explanation': stack_data.get('ai_explanation'),
                    'p_homepage': stack_data.get('homepage'),
                    'p_repo': stack_data.get('repo'),
                    'p_project_suitability': stack_data.get('project_suitability', []),
                    'p_learning_difficulty': stack_data.get('learning_difficulty', {})
                }).execute()

                self.add_log(f"[RPC] 응답 받음: {len(response.data) if response.data else 0}개 항목")
                if response.data:
                    self.add_log(f"[SUCCESS] '{stack_data['name']}' RPC 저장 완료!")
                    return True
                else:
                    self.add_log(f"[WARNING] RPC 응답이 비어있음")
            except Exception as rpc_error:
                self.add_log(f"[RPC FAILED] {rpc_error}")
                self.add_log(f"[FALLBACK] 직접 삽입/업데이트 시도...")

            # 2. 직접 삽입/업데이트 시도
            slug = stack_data.get('slug')
            if not slug:
                self.add_log(f"[ERROR] slug가 없어 저장할 수 없습니다.")
                return False

            # 기존 데이터 확인
            self.add_log(f"[CHECK] 기존 데이터 확인 중... (slug: {slug})")
            existing = self.supabase.table('techs').select('id').eq('slug', slug).execute()
            self.add_log(f"[CHECK] 기존 데이터: {len(existing.data) if existing.data else 0}개 발견")

            supabase_data = {
                'name': stack_data['name'],
                'slug': slug,
                'category': stack_data.get('category'),
                'description': stack_data.get('description'),
                'logo_url': stack_data.get('logo_url'),
                'popularity': int(stack_data.get('popularity', 75)),  # float을 int로 변환
                'learning_resources': stack_data.get('learning_resources', []),
                'ai_explanation': stack_data.get('ai_explanation'),
                'homepage': stack_data.get('homepage'),
                'repo': stack_data.get('repo'),
                'project_suitability': stack_data.get('project_suitability', []),
                'learning_difficulty': stack_data.get('learning_difficulty', {}),
                'updated_at': datetime.now().isoformat()
            }

            if existing.data:
                # 업데이트
                self.add_log(f"[UPDATE] 기존 데이터 업데이트 중...")
                response = self.supabase.table('techs').update(supabase_data).eq('slug', slug).execute()
                self.add_log(f"[SUCCESS] '{stack_data['name']}' 업데이트 완료! 응답: {len(response.data) if response.data else 0}개")
            else:
                # 삽입
                self.add_log(f"[INSERT] 새 데이터 삽입 중...")
                response = self.supabase.table('techs').insert(supabase_data).execute()
                self.add_log(f"[SUCCESS] '{stack_data['name']}' 삽입 완료! 응답: {len(response.data) if response.data else 0}개")

            return True

        except Exception as e:
            self.add_log(f"[ERROR] Supabase 저장 실패: {e}")
            self.add_log(f"[ERROR] 상세 오류: {str(e)}")
            return False

    def delete_current_stack(self):
        """현재 선택된 스택 삭제"""
        if self.current_stack_index == -1:
            messagebox.showwarning("경고", "삭제할 스택이 선택되지 않았습니다.")
            return

        stack_data = self.stacks_data[self.current_stack_index]
        stack_name = stack_data.get('name', 'Unknown')
        stack_slug = stack_data.get('slug', '')

        if messagebox.askyesno("확인", f"'{stack_name}'을(를) 정말 삭제하시겠습니까?"):
            self.add_log(f"'{stack_name}' 기술 스택을 삭제하는 중...")

            # Supabase에서 삭제 시도
            if self.supabase_enabled and stack_slug:
                self.delete_from_supabase(stack_slug, stack_name)

            # 로컬 데이터에서 삭제
            del self.stacks_data[self.current_stack_index]

            if self.save_stacks_data():
                self.refresh_stack_list()
                self.clear_editor()
                self.status_var.set("삭제 완료!")
                self.add_log(f"'{stack_name}' 기술 스택이 삭제되었습니다.")
                messagebox.showinfo("성공", "기술 스택이 삭제되었습니다.")

    def delete_from_supabase(self, slug, name):
        """Supabase에서 데이터 삭제"""
        try:
            self.add_log(f"Supabase에서 '{name}' 삭제 중...")

            response = self.supabase.table('techs').delete().eq('slug', slug).execute()

            if response.data:
                self.add_log(f"Supabase에서 '{name}' 삭제 완료")
            else:
                self.add_log(f"Supabase에서 '{name}' 삭제 - 데이터 없음")

        except Exception as e:
            self.add_log(f"Supabase 삭제 실패: {e}")

    def clear_editor(self):
        """편집기 초기화"""
        self.current_stack_index = -1
        self.name_var.set('')
        self.category_var.set('')
        self.popularity_var.set(0)
        self.update_popularity_label(0)
        self.logo_url_var.set('')
        self.description_text.delete('1.0', tk.END)

    def add_new_stack(self):
        """새 기술 스택 추가"""
        self.add_log("새 기술 스택을 추가합니다.")
        self.clear_editor()
        self.status_var.set("새 기술 스택 추가 모드")

        # 새 스택 템플릿
        new_stack = {
            'name': 'New Technology',
            'slug': 'new-technology',
            'category': 'frontend',
            'description': '',
            'logo_url': '',
            'popularity': 50,
            'learning_resources': [],
            'ai_explanation': '',
            'homepage': '',
            'repo': '',
            'project_suitability': [],
            'learning_difficulty': {},
            'updated_at': datetime.now().isoformat()
        }

        self.stacks_data.append(new_stack)
        self.current_stack_index = len(self.stacks_data) - 1
        self.load_stack_to_editor(new_stack, self.current_stack_index)

        self.add_log("새 기술 스택 템플릿이 생성되었습니다. 정보를 입력하고 저장하세요.")
        messagebox.showinfo("안내", "새 기술 스택이 추가되었습니다. 정보를 입력하고 저장하세요.")

    def run_auto_discovery(self):
        """자동 수집 실행"""
        def run_discovery():
            self.log_queue.put("자동 수집을 시작합니다...")

            try:
                # 프로세스 시작 (Windows 한글 인코딩 문제 완전 해결)
                env = os.environ.copy()
                env.update({
                    'LIMITED_MODE': 'true',
                    'MAX_TECHS': '1',
                    'PYTHONUNBUFFERED': '1',
                    'PYTHONIOENCODING': 'utf-8',
                    'PYTHONLEGACYWINDOWSSTDIO': '0',  # Windows 레거시 stdio 비활성화
                })

                # Windows에서 chcp 65001 (UTF-8) 실행 후 Python 실행
                if os.name == 'nt':
                    cmd = ['cmd', '/c', 'chcp 65001 >nul && python dynamic_tech_discovery.py']
                else:
                    cmd = ['python', 'dynamic_tech_discovery.py']

                process = subprocess.Popen(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT,
                                         text=False,  # 바이너리 모드로 읽기
                                         env=env,
                                         bufsize=0,
                                         shell=True if os.name == 'nt' else False,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

                # 실시간으로 모든 출력 읽기 (바이너리 모드에서 안전한 UTF-8 디코딩)
                while True:
                    line_bytes = process.stdout.readline()
                    if not line_bytes and process.poll() is not None:
                        break
                    if line_bytes:
                        try:
                            # 바이트를 안전하게 UTF-8로 디코딩
                            try:
                                line = line_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                # UTF-8 실패시 CP949로 시도
                                try:
                                    line = line_bytes.decode('cp949')
                                except UnicodeDecodeError:
                                    # 그것도 실패시 에러 무시하고 디코딩
                                    line = line_bytes.decode('utf-8', errors='ignore')

                            line = line.rstrip('\n\r')
                            if line.strip():  # 빈 줄이 아니면
                                # 한글이 포함된 로그 메시지 안전 처리
                                clean_line = self.clean_log_message_korean_safe(line)
                                if clean_line:
                                    self.log_queue.put(clean_line)
                                # 실시간 표시를 위한 즉시 처리
                                self.root.update_idletasks()
                        except Exception as e:
                            # 모든 오류를 포괄하여 안전하게 처리
                            self.log_queue.put(f"[LOG] 메시지 처리 중... (인코딩 복구 시도)")

                process.wait()

                if process.returncode == 0:
                    self.log_queue.put("자동 수집이 성공적으로 완료되었습니다!")
                    # GUI 업데이트는 메인 스레드에서
                    self.root.after(100, lambda: [
                        self.refresh_stack_list(),
                        messagebox.showinfo("성공", "자동 수집이 완료되었습니다!")
                    ])
                else:
                    self.log_queue.put("자동 수집 중 오류가 발생했습니다.")

            except Exception as e:
                self.log_queue.put(f"자동 수집 실행 중 오류: {str(e)}")

        # 백그라운드에서 실행
        self.add_log("자동 수집을 백그라운드에서 시작합니다...")
        threading.Thread(target=run_discovery, daemon=True).start()

    def clean_log_message(self, message):
        """로그 메시지에서 이모티콘 제거 (기본)"""
        # 일반적인 이모티콘 패턴들 제거
        emoji_patterns = [
            '🚀', '🔍', '🤖', '📊', '✅', '❌', '🎉', '💾', '🔧', '📝', '📁', '🌐',
            '⚠️', '💡', '🔥', '📋', '🎯', '⏰', '📈', '🔢', '📂', '⭐', '🏠', '📱',
            '💻', '🛠️', '🎨', '🔒', '🌟', '💼', '📚', '🎮', '🗂️', '📄', '🔄'
        ]

        for emoji in emoji_patterns:
            message = message.replace(emoji, '')

        # 추가적인 정리
        message = message.strip()
        if message.startswith('- '):
            message = message[2:]

        # 메시지가 너무 길면 앞부분만 유지
        if len(message) > 200:
            message = message[:200] + "..."

        return message

    def clean_log_message_detailed(self, message):
        """상세 로그용 메시지 정리 (모든 내용 보존)"""
        # 이모티콘만 제거하고 나머지는 모두 유지
        emoji_patterns = [
            '🚀', '🔍', '🤖', '📊', '✅', '❌', '🎉', '💾', '🔧', '📝', '📁', '🌐',
            '⚠️', '💡', '🔥', '📋', '🎯', '⏰', '📈', '🔢', '📂', '⭐', '🏠', '📱',
            '💻', '🛠️', '🎨', '🔒', '🌟', '💼', '📚', '🎮', '🗂️', '📄', '🔄'
        ]

        for emoji in emoji_patterns:
            message = message.replace(emoji, '')

        # 기본 정리만 하고 길이 제한 없이 모든 내용 보존
        return message.strip()

    def clean_log_message_korean_safe(self, message):
        """한글 안전 처리가 포함된 로그 메시지 정리"""
        try:
            # 메시지가 바이트인 경우 UTF-8로 디코드
            if isinstance(message, bytes):
                message = message.decode('utf-8', errors='ignore')

            # 문자열이 아닌 경우 문자열로 변환
            if not isinstance(message, str):
                message = str(message)

            # 이모티콘만 제거하고 나머지는 모두 유지
            emoji_patterns = [
                '🚀', '🔍', '🤖', '📊', '✅', '❌', '🎉', '💾', '🔧', '📝', '📁', '🌐',
                '⚠️', '💡', '🔥', '📋', '🎯', '⏰', '📈', '🔢', '📂', '⭐', '🏠', '📱',
                '💻', '🛠️', '🎨', '🔒', '🌟', '💼', '📚', '🎮', '🗂️', '📄', '🔄'
            ]

            for emoji in emoji_patterns:
                message = message.replace(emoji, '')

            # 한글이 깨진 경우 복구 시도
            try:
                # CP949로 잘못 인코딩된 경우 복구
                if '��' in message or '?' in message:
                    # 원본 메시지에서 한글 부분만 복구 시도
                    message = message.encode('latin1').decode('utf-8', errors='ignore')
            except:
                pass

            # 기본 정리
            message = message.strip()

            # 완전히 깨진 메시지는 간단한 정보로 대체
            if len(message) > 0 and all(ord(c) > 127 and c in '��?' for c in message):
                return "[한글 메시지] (인코딩 문제로 표시 불가)"

            return message

        except Exception as e:
            return f"[LOG ERROR] 메시지 처리 실패: {e}"

    def calculate_difficulty_from_stars(self, learning_difficulty):
        """Stars 배열로부터 난이도 라벨 계산"""
        if not learning_difficulty:
            return "N/A"

        # 기존 label이 있으면 우선 사용
        if learning_difficulty.get('label'):
            return learning_difficulty.get('label')

        # stars 배열로부터 계산
        stars = learning_difficulty.get('stars', [])
        if not stars:
            return "N/A"

        star_count = sum(1 for star in stars if star)

        if star_count <= 1:
            return "초급"
        elif star_count <= 2:
            return "초중급"
        elif star_count <= 3:
            return "중급"
        elif star_count <= 4:
            return "중고급"
        else:
            return "고급"

    def open_website(self):
        """웹사이트 열기"""
        try:
            file_path = os.path.abspath('index.html')
            webbrowser.open(f'file://{file_path}')
            self.add_log("웹사이트를 브라우저에서 열었습니다.")
        except Exception as e:
            self.add_log(f"웹사이트 열기 실패: {e}")
            messagebox.showerror("오류", f"웹사이트 열기 실패: {e}")

    def open_homepage(self):
        """선택된 스택의 홈페이지 열기"""
        homepage = self.homepage_var.get()
        if homepage:
            try:
                webbrowser.open(homepage)
                self.add_log(f"홈페이지를 열었습니다: {homepage}")
            except Exception as e:
                self.add_log(f"홈페이지 열기 실패: {e}")
                messagebox.showerror("오류", f"홈페이지 열기 실패: {e}")
        else:
            messagebox.showwarning("경고", "홈페이지 URL이 없습니다.")

    def open_repo(self):
        """선택된 스택의 GitHub 리포지토리 열기"""
        repo = self.repo_var.get()
        if repo:
            try:
                webbrowser.open(repo)
                self.add_log(f"GitHub 리포지토리를 열었습니다: {repo}")
            except Exception as e:
                self.add_log(f"GitHub 열기 실패: {e}")
                messagebox.showerror("오류", f"GitHub 열기 실패: {e}")
        else:
            messagebox.showwarning("경고", "GitHub URL이 없습니다.")

    def show_statistics(self):
        """통계 정보 표시"""
        self.add_log("통계 정보를 표시합니다.")

        stats_window = tk.Toplevel(self.root)
        stats_window.title("통계 정보")
        stats_window.geometry("500x400")

        # 통계 계산
        total_count = len(self.stacks_data)

        categories = {}
        difficulties = {}
        avg_popularity = 0

        for stack in self.stacks_data:
            # 카테고리별 통계
            cat = stack.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1

            # 난이도별 통계
            diff = stack.get('learning_difficulty', {}).get('label', 'unknown')
            difficulties[diff] = difficulties.get(diff, 0) + 1

            # 평균 인기도
            avg_popularity += stack.get('popularity', 0)

        if total_count > 0:
            avg_popularity /= total_count

        # 통계 표시
        stats_text = scrolledtext.ScrolledText(stats_window, width=60, height=25)
        stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        stats_content = f"""AI Stack List 통계 정보

전체 기술 수: {total_count}개
평균 인기도: {avg_popularity:.1f}%

카테고리별 분포:
"""
        for cat, count in categories.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            stats_content += f"  - {cat}: {count}개 ({percentage:.1f}%)\n"

        stats_content += f"\n학습 난이도별 분포:\n"
        for diff, count in difficulties.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            stats_content += f"  - {diff}: {count}개 ({percentage:.1f}%)\n"

        stats_content += f"\n마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        stats_text.insert('1.0', stats_content)
        stats_text.config(state='disabled')

def main():
    root = tk.Tk()
    app = TechStackManager(root)
    root.mainloop()

if __name__ == '__main__':
    main()