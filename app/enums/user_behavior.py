from enum import Enum


# 서비스 안정화되면 사용하기(바뀌면 귀찮아서)
class BehaviorEventType(str, Enum):
    POI_MARK = "POI_MARK"
    POI_SCHEDULE = "POI_SCHEDULE"
    POI_UNMARK = "POI_UNMARK"
    POI_UNSCHEDULE = "POI_UNSCHEDULE"
