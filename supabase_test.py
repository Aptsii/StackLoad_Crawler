import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_basic_connection():
    """기본 연결 테스트"""
    try:
        SUPABASE_URL = os.environ['SUPABASE_URL']
        SUPABASE_KEY = os.environ['SUPABASE_KEY']

        print(f"URL: {SUPABASE_URL}")
        print(f"Key: {SUPABASE_KEY[:20]}...")

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase 클라이언트 생성 성공")

        return supabase
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return None

def test_table_access(supabase):
    """테이블 접근 테스트"""
    try:
        print("\n🔍 테이블 접근 테스트 중...")
        result = supabase.table('techs').select('*').limit(1).execute()
        print("✅ 테이블 접근 성공")
        print(f"응답: {result}")
        return True
    except Exception as e:
        print(f"❌ 테이블 접근 실패: {e}")
        return False

def test_simple_insert(supabase):
    """간단한 삽입 테스트"""
    try:
        print("\n➕ 간단한 데이터 삽입 테스트...")
        test_data = {
            'name': 'Test Tech',
            'slug': 'test-tech',
            'category': 'test',
            'description': 'Test description',
            'popularity': 50,
            'learning_resources': [{'url': 'https://test.com/learn', 'type': 'tutorial', 'title': 'Test Tutorial'}],
            'ai_explanation': 'AI generated explanation for test tech.',
            'homepage': 'https://test.com',
            'repo': 'https://github.com/test/test-tech',
            'project_suitability': ['Small projects', 'Learning purposes'],
            'learning_difficulty': {'label': '초급', 'stars': [True, False, False, False, False], 'description': 'Very easy to learn.'}
        }

        result = supabase.table('techs').insert(test_data).execute()
        print("✅ 데이터 삽입 성공")
        print(f"삽입된 데이터: {result.data}")

        # 삽입한 테스트 데이터 삭제
        supabase.table('techs').delete().eq('slug', 'test-tech').execute()
        print("🗑️ 테스트 데이터 삭제 완료")

        return True
    except Exception as e:
        print(f"❌ 데이터 삽입 실패: {e}")
        return False

def test_rpc_function(supabase):
    """RPC 함수 테스트"""
    try:
        print("\n🚀 RPC 함수 테스트...")
        result = supabase.rpc('upsert_tech_stack', {
            'p_name': 'RPC Test',
            'p_slug': 'rpc-test',
            'p_category': 'test',
            'p_description': 'RPC test description',
            'p_popularity': 75,
            'p_learning_resources': [{'url': 'https://rpc.com/learn', 'type': 'documentation', 'title': 'RPC Docs'}],
            'p_ai_explanation': 'AI generated explanation for RPC test.',
            'p_homepage': 'https://rpc.com',
            'p_repo': 'https://github.com/rpc/rpc-test',
            'p_project_suitability': ['API testing', 'Integration testing'],
            'p_learning_difficulty': {'label': '중급', 'stars': [True, True, True, False, False], 'description': 'Requires understanding of RPC.'}
        }).execute()

        print("✅ RPC 함수 실행 성공")
        print(f"RPC 결과: {result.data}")

        # 테스트 데이터 삭제
        supabase.table('techs').delete().eq('slug', 'rpc-test').execute()
        print("🗑️ RPC 테스트 데이터 삭제 완료")

        return True
    except Exception as e:
        print(f"❌ RPC 함수 실행 실패: {e}")
        return False

def main():
    print("🧪 Supabase 연결 테스트 시작\n")

    # 1. 기본 연결 테스트
    supabase = test_basic_connection()
    if not supabase:
        return

    # 2. 테이블 접근 테스트
    if not test_table_access(supabase):
        print("\n💡 해결 방법:")
        print("1. Supabase 대시보드 → SQL Editor")
        print("2. simplified_supabase_setup.sql 내용 실행")
        print("3. 다시 이 스크립트 실행")
        return

    # 3. 간단한 삽입 테스트
    if not test_simple_insert(supabase):
        print("\n💡 권한 문제일 수 있습니다. RLS 설정을 확인하세요.")
        return

    # 4. RPC 함수 테스트
    if not test_rpc_function(supabase):
        print("\n💡 해결 방법:")
        print("1. Supabase 대시보드 → SQL Editor")
        print("2. supabase_function_setup.sql 내용 실행")
        print("3. 다시 이 스크립트 실행")
        return

    print("\n🎉 모든 테스트 통과! Supabase 연동이 완료되었습니다.")
    print("이제 GUI 프로그램에서 'Supabase: 연결됨'으로 표시될 것입니다.")

if __name__ == '__main__':
    main()