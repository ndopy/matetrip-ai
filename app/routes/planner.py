import json
import logging

from fastapi import APIRouter, HTTPException, status

from app.core.llm import global_llm

from app.schemas.plan import PlanGenerationRequest, PlanResponseIDs

from langchain_core.prompts import ChatPromptTemplate

router = APIRouter(prefix="/plan", tags=["Planner"])

# 1. 프롬프트 정의
# AI에게 주어진 장소 리스트 안에서만 사용해라 라고 강하게 지시
plan_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a professional travel planner. Your task is to create a structured JSON itinerary **using only place IDs**.\n\n"
        "**<rules>**\n"
        "1. **(Source Data)** You will get a <place_list> containing 'id', 'placeName', 'summary', 'latitude', and 'longitude'.\n\n"
        "2. **(Curation Logic)** Read the 'placeName' and 'summary' to understand each place.\n\n"
        "3. **(Grouping Logic)** Create a logical {total_date}-day plan by selecting a subset of the best places.\n"
        "   - A good plan has 2-4 places per day.\n"
        "   - **Use the 'latitude' and 'longitude' fields to group places that are geographically close to each other on the same day.**\n"
        "   - This proximity grouping is the most important task to minimize user travel time.\n\n"
        "   - Logically group the selected places into {total_date} separate daily plans.\n\n"
        
        "4. **(Output Format - CRITICAL)**\n"
        "   - You MUST return your plan in the 'PlanResponseIDs' JSON format.\n"
        "   - **DO NOT** return the full place details (name, summary, etc.).\n"
        "   - **ONLY return the 'placeIDs'** you selected for each day in the 'daily_plans' array."
    )),
    ("human", (
        "Here is the list of recommended places:\n"
        "<place_list>\n{places_json}\n</place_list>\n\n"
        "Please select the best places, **grouping them by proximity (latitude/longitude)**, "
        "and create a {total_date}-day itinerary (IDs only)."
    ))
])

# 2. LLM 체인 생성
# .with_structured_output()이 AI가 PlanResponse DTO에 맞춰 JSON을 생성하도록 강제
planner_chain = plan_prompt | global_llm.with_structured_output(PlanResponseIDs)

# 3. 엔드포인트 생성
@router.post("/generate", response_model=PlanResponseIDs)
async def generate_plan(request: PlanGenerationRequest):
    """
    NestJS로부터 장소 리스트와 날짜를 받아 여행 계획 JSON을 생성합니다.
    """
    try:
        # DTO 리스트를 AI가 읽기 쉽도록 JSON 문자열로 변환
        places_json = json.dumps(request.places, indent=2, ensure_ascii=False)

        # AI 호출
        plan_object: PlanResponseIDs = await planner_chain.ainvoke({
            "places_json": places_json,
            "total_date": request.total_date,
        })

        return plan_object
    except Exception as e:
        logging.error(f"Error generating ID plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate travel plan IDs."
        )