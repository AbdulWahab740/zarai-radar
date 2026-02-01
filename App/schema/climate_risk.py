from pydantic import BaseModel
from typing import List


class RiskItem(BaseModel):
    """Single risk item (e.g. climate risk) with level, message, actions."""
    type_key: str  # "diseaseRisk" | "pestRisk" | "climateRisk"
    level: str     # "HIGH" | "MEDIUM" | "LOW"
    message_en: str
    message_ur: str
    actions_en: List[str]
    actions_ur: List[str]


class WeatherSnapshot(BaseModel):
    """Current weather used for risk evaluation."""
    temp_c: float
    humidity: int
    wind_kph: float
    chance_of_rain: int


class ClimateRiskResponse(BaseModel):
    """Response for GET /dashboard/climate-risk."""
    overall_level: str
    crop: str
    stage: str
    district: str
    province: str
    weather_snapshot: WeatherSnapshot
    risks: List[RiskItem]
