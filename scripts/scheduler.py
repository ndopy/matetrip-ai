"""
장소 데이터 수집을 주기적으로 실행하는 스케줄러

실행 방법:
    python scripts/scheduler.py

또는 백그라운드 실행:
    nohup python scripts/scheduler.py > logs/scheduler.log 2>&1 &
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from scripts.collect_places import PlaceCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def scheduled_collection():
    """스케줄된 데이터 수집 작업"""
    logger.info("=" * 80)
    logger.info(f"[스케줄 실행] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        collector = PlaceCollector(db)
        await collector.collect_and_process(
            categories=["tourism", "food"], process_reviews=True
        )
    except Exception as e:
        logger.error(f"스케줄 실행 중 오류 발생: {e}", exc_info=True)
    finally:
        db.close()


def main():
    """스케줄러 메인 함수"""
    scheduler = AsyncIOScheduler()

    # 매주 월요일 오전 2시에 실행
    scheduler.add_job(
        scheduled_collection,
        CronTrigger(day_of_week="mon", hour=2, minute=0, timezone="Asia/Seoul"),
        id="weekly_place_collection",
        name="주간 장소 데이터 수집",
        replace_existing=True,
    )

    logger.info("=" * 80)
    logger.info("스케줄러 시작")
    logger.info("실행 주기: 매주 월요일 오전 2시")
    logger.info("대상: 서울 관광명소 + 음식점")
    logger.info("=" * 80)

    # 다음 실행 시간 표시
    jobs = scheduler.get_jobs()
    for job in jobs:
        logger.info(f"다음 실행 예정: {job.next_run_time}")

    scheduler.start()

    try:
        # 스케줄러 실행 유지
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 종료")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
