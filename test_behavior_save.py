#!/usr/bin/env python3
"""Direct test of behavior embedding service"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.database.database import get_db
from service.behavior.behavior_service import BehaviorService
from app.schemas.behavior import SaveBehaviorEventDto


def main():
    print("Testing behavior event save...")

    # Get DB session
    db = next(get_db())

    try:
        service = BehaviorService(db)

        # Create test DTO
        dto = SaveBehaviorEventDto(
            user_id="0c77142e-5fa1-41f4-9a6a-07d80709b660",
            event_type="POI_MARK",
            event_data={
                "placeId": "2a56ea65-fa1d-4359-80fe-101096665ba5",
                "placeName": "테스트 장소",
                "category": "관광지",
                "workspaceId": None,
            },
            weight=3.0,
            workspace_id=None,
            place_id="2a56ea65-fa1d-4359-80fe-101096665ba5",
        )

        print(f"Saving event: {dto}")
        event_id = service.save_behavior_event(dto)
        print(f"✓ Event saved successfully! ID: {event_id}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
