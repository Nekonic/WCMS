"""
코드 품질 도구 설정 및 실행

사용:
    python code_quality.py              # 모든 도구 실행
    python code_quality.py --format     # Black 포맷팅만
    python code_quality.py --lint       # Flake8 린팅만
    python code_quality.py --type       # Mypy 타입 체크만
"""
import subprocess
import sys
import os
from pathlib import Path


class CodeQualityChecker:
    """코드 품질 검사 클래스"""

    DIRECTORIES = ['server', 'client', 'tests']

    @staticmethod
    def format_code() -> int:
        """Black을 사용한 코드 포맷팅"""
        print("=" * 60)
        print("Black - 코드 포맷팅")
        print("=" * 60)
        try:
            result = subprocess.run(
                ['black', '--line-length', '100'] + CodeQualityChecker.DIRECTORIES,
                check=False
            )
            return result.returncode
        except FileNotFoundError:
            print("오류: Black이 설치되지 않았습니다.")
            print("설치: pip install black")
            return 1

    @staticmethod
    def lint_code() -> int:
        """Flake8을 사용한 린팅"""
        print("\n" + "=" * 60)
        print("Flake8 - 린팅")
        print("=" * 60)
        try:
            result = subprocess.run(
                ['flake8'] + CodeQualityChecker.DIRECTORIES,
                check=False
            )
            return result.returncode
        except FileNotFoundError:
            print("오류: Flake8이 설치되지 않았습니다.")
            print("설치: pip install flake8")
            return 1

    @staticmethod
    def check_types() -> int:
        """Mypy를 사용한 타입 검사"""
        print("\n" + "=" * 60)
        print("Mypy - 타입 검사")
        print("=" * 60)
        try:
            result = subprocess.run(
                ['mypy'] + CodeQualityChecker.DIRECTORIES,
                check=False
            )
            return result.returncode
        except FileNotFoundError:
            print("오류: Mypy가 설치되지 않았습니다.")
            print("설치: pip install mypy")
            return 1

    @staticmethod
    def install_tools() -> None:
        """모든 코드 품질 도구 설치"""
        print("코드 품질 도구 설치 중...")
        print("\nUV를 사용하는 것을 권장합니다:")
        print("  uv sync --all-extras")
        print("\n또는 pip를 사용하려면:")
        tools = ['black', 'flake8', 'mypy', 'isort', 'pytest']
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + tools)

    @staticmethod
    def run_all() -> int:
        """모든 검사 실행"""
        print("WCMS 코드 품질 검사")
        print("=" * 60)

        results = {
            'Black (포맷팅)': CodeQualityChecker.format_code(),
            'Flake8 (린팅)': CodeQualityChecker.lint_code(),
            'Mypy (타입 검사)': CodeQualityChecker.check_types(),
        }

        print("\n" + "=" * 60)
        print("검사 결과 요약")
        print("=" * 60)
        for tool, returncode in results.items():
            status = "✓ 통과" if returncode == 0 else "✗ 실패"
            print(f"{tool}: {status}")

        print("=" * 60)
        return max(results.values())


if __name__ == '__main__':
    checker = CodeQualityChecker()

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == '--install':
            checker.install_tools()
        elif arg == '--format':
            sys.exit(checker.format_code())
        elif arg == '--lint':
            sys.exit(checker.lint_code())
        elif arg == '--type':
            sys.exit(checker.check_types())
        else:
            print("사용법:")
            print("  python code_quality.py              # 모든 검사 실행")
            print("  python code_quality.py --format     # Black 포맷팅만")
            print("  python code_quality.py --lint       # Flake8 린팅만")
            print("  python code_quality.py --type       # Mypy 타입 검사만")
            print("  python code_quality.py --install    # 도구 설치")
            sys.exit(1)
    else:
        sys.exit(checker.run_all())

