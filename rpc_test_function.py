import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    SUPABASE_URL = os.environ['SUPABASE_URL']
    SUPABASE_KEY = os.environ['SUPABASE_KEY']
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client created.")
except KeyError as e:
    print(f"❌ ERROR: Environment variable {e} not set.")
    exit()

def test_rpc_function():
    """RPC 함수가 제대로 설정되었는지 테스트"""

    print("🧪 Testing RPC function...")

    # 테스트 데이터
    test_data = {
        'p_name': 'Test Framework',
        'p_slug': 'test-framework',
        'p_category': '테스트',
        'p_description': '테스트용 프레임워크입니다.',
        'p_logo_url': 'https://example.com/logo.svg',
        'p_popularity': 50,
        'p_ai_explanation': 'AI가 생성한 테스트 설명입니다.',
        'p_homepage': 'https://example.com',
        'p_repo': 'https://github.com/example/test',
        'p_project_suitability': ['테스트 프로젝트', '학습용 프로젝트'],
        'p_learning_difficulty': {
            'stars': [True, False, False, False, False],
            'label': '초급',
            'description': '매우 쉽습니다.'
        }
    }

    try:
        # RPC 함수 호출
        response = supabase.rpc('upsert_tech_stack', test_data).execute()

        if response.data:
            print("✅ RPC 함수 테스트 성공!")
            print(f"📊 응답 데이터: {response.data}")

            # 데이터 읽기 테스트
            read_test = supabase.rpc('get_all_tech_stacks').execute()
            if read_test.data:
                print(f"✅ 데이터 읽기 테스트 성공! 총 {len(read_test.data)}개 항목")

            return True
        else:
            print("❌ RPC 함수가 데이터를 반환하지 않았습니다.")
            return False

    except Exception as e:
        print(f"❌ RPC 함수 테스트 실패: {e}")
        print("💡 supabase_setup.sql을 먼저 실행하세요!")
        return False

def cleanup_test_data():
    """테스트 데이터 삭제"""
    try:
        supabase.table('techs').delete().eq('slug', 'test-framework').execute()
        print("🧹 테스트 데이터 삭제 완료")
    except:
        print("⚠️  테스트 데이터 삭제 실패 (무시해도 됩니다)")

if __name__ == '__main__':
    print("🚀 Supabase RPC 함수 테스트 시작...")

    if test_rpc_function():
        print("\n🎉 모든 테스트 통과! 이제 final_working_script.py를 실행하세요.")
        cleanup_test_data()
    else:
        print("\n❌ 테스트 실패. supabase_setup.sql을 먼저 실행하세요.")
        print("\n📝 단계별 해결 방법:")
        print("1. Supabase 대시보드 → SQL Editor 열기")
        print("2. supabase_setup.sql 파일 내용 복사")
        print("3. SQL Editor에 붙여넣기 후 실행")
        print("4. 다시 이 테스트 스크립트 실행")