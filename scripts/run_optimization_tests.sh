#!/bin/bash

# 경로 최적화 테스트 실행 스크립트

echo "=================================================="
echo "🧪 경로 최적화 단위 테스트"
echo "=================================================="

# 1. Mock 데이터 기반 단위 테스트만 실행
echo ""
echo "1️⃣  Mock 테스트 실행 (API 호출 없음, 빠름)"
echo "--------------------------------------------------"
uv run pytest test/test_route_optimization.py -v -m "not integration" --tb=short

# 테스트 결과 확인
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Mock 테스트 통과!"
else
    echo ""
    echo "❌ Mock 테스트 실패!"
    exit 1
fi

# 2. 통합 테스트 실행 여부 확인
echo ""
echo "=================================================="
read -p "실제 API를 호출하는 통합 테스트를 실행하시겠습니까? (y/n): " run_integration

if [ "$run_integration" = "y" ] || [ "$run_integration" = "Y" ]; then
    echo ""
    echo "2️⃣  통합 테스트 실행 (실제 API 호출, 느림)"
    echo "--------------------------------------------------"
    uv run pytest test/test_route_optimization.py -v -m integration --tb=short

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ 통합 테스트 통과!"
    else
        echo ""
        echo "❌ 통합 테스트 실패!"
        echo "   - .env에 KAKAO_MOBILITY_API_KEY가 설정되어 있는지 확인하세요"
        exit 1
    fi
else
    echo ""
    echo "⏭️  통합 테스트 스킵"
fi

echo ""
echo "=================================================="
echo "✅ 모든 테스트 완료!"
echo "=================================================="
