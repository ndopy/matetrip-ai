#!/usr/bin/env python3
"""
장소 데이터 수집 CLI 도구

사용법:
    # 전체 수집 (리뷰 처리 포함)
    python scripts/cli.py collect --with-reviews

    # 장소만 수집 (리뷰 처리 제외)
    python scripts/cli.py collect

    # 특정 카테고리만 수집
    python scripts/cli.py collect --categories food tourism

    # 스케줄러 실행
    python scripts/cli.py schedule

    # 도움말
    python scripts/cli.py --help
"""

import sys
import os
import asyncio
import argparse
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from scripts.collect_places import PlaceCollector
from scripts.scheduler import main as run_scheduler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def collect_command(args):
    """데이터 수집 명령어"""
    db = SessionLocal()

    try:
        # 카테고리 설정
        categories = args.categories if args.categories else ["tourism", "food"]

        # PlaceCollector 초기화
        collector = PlaceCollector(
            db=db,
            max_naver_api_calls=args.max_naver_calls,
            region_filter=args.region,
        )

        logger.info(f"수집 카테고리: {categories}")
        logger.info(f"대상 지역: {args.region if args.region else '전국'}")
        logger.info(f"리뷰 처리: {'ON' if args.with_reviews else 'OFF'}")
        if args.with_reviews:
            logger.info(f"네이버 API 제한: {args.max_naver_calls}건")

        await collector.collect_and_process(
            categories=categories, process_reviews=args.with_reviews
        )

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


def schedule_command(args):
    """스케줄러 실행 명령어"""
    logger.info("스케줄러를 시작합니다...")
    run_scheduler()


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description="장소 데이터 수집 CLI 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령어")

    # collect 명령어
    collect_parser = subparsers.add_parser("collect", help="장소 데이터 수집 (전국)")
    collect_parser.add_argument(
        "--categories",
        nargs="+",
        choices=["food", "tourism", "cafe", "accommodation", "culture"],
        help="수집할 카테고리 (기본값: food tourism)",
    )
    collect_parser.add_argument(
        "--with-reviews",
        action="store_true",
        help="리뷰 자동 처리 활성화",
    )
    collect_parser.add_argument(
        "--region",
        type=str,
        choices=[
            "서울",
            "부산",
            "인천",
            "대구",
            "대전",
            "광주",
            "울산",
            "세종",
            "경기",
            "강원",
            "충북",
            "충남",
            "전북",
            "전남",
            "경북",
            "경남",
            "제주",
        ],
        help="특정 지역만 수집 (기본값: 전국)",
    )
    collect_parser.add_argument(
        "--max-naver-calls",
        type=int,
        default=20000,
        help="네이버 API 최대 호출 수 (기본값: 20000)",
    )

    # schedule 명령어
    schedule_parser = subparsers.add_parser(
        "schedule", help="스케줄러 실행 (매주 월요일 오전 2시)"
    )

    args = parser.parse_args()

    if args.command == "collect":
        asyncio.run(collect_command(args))
    elif args.command == "schedule":
        schedule_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
