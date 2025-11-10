"""
DB 연결 및 테이블 설정 테스트 스크립트
"""
import sys
from sqlalchemy import text, inspect
from app.database.database import SessionLocal, engine
from app.models.place import Place
from app.models.review import PlaceReview

def test_connection():
    """DB 연결 테스트"""
    print("=" * 60)
    print("1. DB 연결 테스트")
    print("=" * 60)
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✓ DB 연결 성공")
            print(f"  PostgreSQL 버전: {version[:50]}...")
        return True
    except Exception as e:
        print(f"✗ DB 연결 실패: {e}")
        return False

def test_pgvector():
    """pgvector 확장 확인"""
    print("\n" + "=" * 60)
    print("2. pgvector 확장 확인")
    print("=" * 60)
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"))
            row = result.fetchone()
            if row:
                print(f"✓ pgvector 설치됨: version {row[1]}")
                return True
            else:
                print("✗ pgvector가 설치되지 않음")
                return False
    except Exception as e:
        print(f"✗ pgvector 확인 실패: {e}")
        return False

def test_table_schema():
    """테이블 스키마 확인"""
    print("\n" + "=" * 60)
    print("3. 테이블 스키마 확인")
    print("=" * 60)

    inspector = inspect(engine)

    # places 테이블
    print("\n[places 테이블]")
    places_columns = {col['name']: col['type'] for col in inspector.get_columns('places')}

    required_place_fields = ['embedding', 'updated_at']
    for field in required_place_fields:
        if field in places_columns:
            print(f"  ✓ {field}: {places_columns[field]}")
        else:
            print(f"  ✗ {field}: 누락됨")
            return False

    # place_review 테이블
    print("\n[place_review 테이블]")
    review_columns = {col['name']: col['type'] for col in inspector.get_columns('place_review')}

    required_review_fields = ['is_deleted', 'updated_at']
    for field in required_review_fields:
        if field in review_columns:
            print(f"  ✓ {field}: {review_columns[field]}")
        else:
            print(f"  ✗ {field}: 누락됨")
            return False

    print("\n✓ 모든 필드가 정상적으로 추가됨")
    return True

def test_model_compatibility():
    """모델과 DB 스키마 호환성 테스트"""
    print("\n" + "=" * 60)
    print("4. 모델과 DB 스키마 호환성 테스트")
    print("=" * 60)

    try:
        with SessionLocal() as db:
            # places 조회 테스트
            place = db.query(Place).first()
            if place:
                print(f"\n✓ Place 모델 조회 성공")
                print(f"  - id: {place.id}")
                print(f"  - title: {place.title}")
                print(f"  - embedding: {'있음' if place.embedding else '없음'}")
                print(f"  - updated_at: {place.updated_at}")
            else:
                print("  (places 테이블에 데이터 없음)")

            # place_review 조회 테스트
            review = db.query(PlaceReview).first()
            if review:
                print(f"\n✓ PlaceReview 모델 조회 성공")
                print(f"  - id: {review.id}")
                print(f"  - place_id: {review.place_id}")
                print(f"  - is_deleted: {review.is_deleted}")
                print(f"  - updated_at: {review.updated_at}")
                print(f"  - embedding: {'있음' if review.embedding is not None else '없음'}")
            else:
                print("  (place_review 테이블에 데이터 없음)")

        print("\n✓ 모델과 DB 스키마 호환성 정상")
        return True

    except Exception as e:
        print(f"✗ 모델 호환성 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_counts():
    """데이터 개수 확인"""
    print("\n" + "=" * 60)
    print("5. 데이터 개수 확인")
    print("=" * 60)

    try:
        with SessionLocal() as db:
            place_count = db.query(Place).count()
            review_count = db.query(PlaceReview).count()

            # 임베딩이 있는 리뷰 개수
            reviews_with_embedding = db.query(PlaceReview).filter(
                PlaceReview.embedding.isnot(None),
                PlaceReview.is_deleted == False
            ).count()

            # 장소 임베딩이 있는 개수
            places_with_embedding = db.query(Place).filter(
                Place.embedding.isnot(None)
            ).count()

            print(f"  - 전체 장소: {place_count:,}개")
            print(f"  - 전체 리뷰: {review_count:,}개")
            print(f"  - 임베딩이 있는 리뷰: {reviews_with_embedding:,}개")
            print(f"  - 임베딩이 있는 장소: {places_with_embedding:,}개")

            # 임베딩이 필요한 장소 개수
            places_need_embedding = db.query(Place).filter(
                Place.embedding.is_(None)
            ).count()

            print(f"\n  📊 임베딩이 필요한 장소: {places_need_embedding:,}개")

        return True

    except Exception as e:
        print(f"✗ 데이터 개수 확인 실패: {e}")
        return False

def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("🔍 DB 연결 및 테이블 설정 검증 시작")
    print("=" * 60)

    results = []

    # 1. DB 연결 테스트
    results.append(("DB 연결", test_connection()))

    # 2. pgvector 확인
    results.append(("pgvector 확장", test_pgvector()))

    # 3. 테이블 스키마 확인
    results.append(("테이블 스키마", test_table_schema()))

    # 4. 모델 호환성 테스트
    results.append(("모델 호환성", test_model_compatibility()))

    # 5. 데이터 개수 확인
    results.append(("데이터 개수", test_data_counts()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약")
    print("=" * 60)

    for test_name, result in results:
        status = "✓ 통과" if result else "✗ 실패"
        print(f"  {test_name}: {status}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과! DB 설정이 정상입니다.")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ 일부 테스트 실패. 위 내용을 확인하세요.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
