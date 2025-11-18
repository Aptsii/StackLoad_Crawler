#!/usr/bin/env python3
"""
AI Stack List 관리자 실행 스크립트

이 스크립트는 의존성 확인 후 GUI 관리자를 실행합니다.
"""

import sys
import subprocess
import importlib.util
import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """필요한 의존성 패키지들을 확인하고 설치"""
    required_packages = {
        'tkinter': 'tkinter',
        'PIL': 'pillow',
        'requests': 'requests',
        'json': None,  # 내장 모듈
        'threading': None,  # 내장 모듈
        'subprocess': None,  # 내장 모듈
        'os': None,  # 내장 모듈
        'datetime': None,  # 내장 모듈
        'webbrowser': None,  # 내장 모듈
    }

    missing_packages = []

    for package, pip_name in required_packages.items():
        if package == 'tkinter':
            # tkinter 특별 처리
            try:
                import tkinter
            except ImportError:
                missing_packages.append('tkinter (시스템 패키지)')
                continue

        elif pip_name:  # pip으로 설치 가능한 패키지
            if importlib.util.find_spec(package) is None:
                missing_packages.append(pip_name)

    return missing_packages

def install_missing_packages(packages):
    """누락된 패키지들 설치"""
    if not packages:
        return True

    print("다음 패키지들을 설치합니다:")
    for package in packages:
        print(f"  - {package}")

    try:
        for package in packages:
            if package == 'tkinter (시스템 패키지)':
                print("⚠️  tkinter는 Python과 함께 설치되어야 합니다.")
                print("   Ubuntu/Debian: sudo apt-get install python3-tk")
                print("   CentOS/RHEL: sudo yum install tkinter")
                print("   macOS: brew install python-tk")
                return False

            print(f"설치 중: {package}")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} 설치 완료")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 패키지 설치 실패: {e}")
        return False

def check_data_files():
    """필요한 데이터 파일들 확인"""
    import os

    files_to_check = ['stacks.json']
    missing_files = []

    for file in files_to_check:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print("누락된 파일들을 생성합니다:")
        for file in missing_files:
            if file == 'stacks.json':
                # 빈 JSON 배열 생성
                import json
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                print(f"✅ {file} 생성 완료")

def run_manager():
    """GUI 관리자 실행"""
    try:
        from final_tech_stack_manager import main
        print("AI Stack List 관리자를 시작합니다...")
        main()
    except ImportError as e:
        print(f"모듈 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"실행 중 오류 발생: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("AI Stack List 관리자")
    print("=" * 60)

    # 1. 의존성 확인
    print("\n1. 의존성 확인 중...")
    missing = check_dependencies()

    if missing:
        print(f"누락된 패키지: {', '.join(missing)}")

        # 자동 설치 시도
        print("\n2. 누락된 패키지 설치 중...")
        if not install_missing_packages(missing):
            print("패키지 설치 실패. 수동으로 설치해주세요:")
            print("pip install -r requirements.txt")
            return 1
    else:
        print("모든 의존성이 충족되었습니다.")

    # 2. 데이터 파일 확인
    print("\n3. 데이터 파일 확인 중...")
    check_data_files()

    # 3. GUI 관리자 실행
    print("\n4. GUI 관리자 실행 중...")
    if not run_manager():
        return 1

    print("\n프로그램이 정상적으로 종료되었습니다.")
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)