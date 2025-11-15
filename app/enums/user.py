from enum import Enum


class Gender(str, Enum):
    MALE = "남성"
    FEMALE = "여성"


class MBTIType(str, Enum):
    ISFJ = "ISFJ"
    ISFP = "ISFP"
    ISTJ = "ISTJ"
    ISTP = "ISTP"
    INFJ = "INFJ"
    INFP = "INFP"
    INTJ = "INTJ"
    INTP = "INTP"
    ESFJ = "ESFJ"
    ESFP = "ESFP"
    ESTJ = "ESTJ"
    ESTP = "ESTP"
    ENFJ = "ENFJ"
    ENFP = "ENFP"
    ENTJ = "ENTJ"
    ENTP = "ENTP"
