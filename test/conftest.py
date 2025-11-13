"""
pytest 설정 파일

프로젝트 루트를 Python path에 추가하여 app 모듈을 import할 수 있게 합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
