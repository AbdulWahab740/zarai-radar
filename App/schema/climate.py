from pydantic import BaseModel

class ClimateData(BaseModel):
    """Climate data for a given datetime"""
    temp_c: float
    humidity: int
    wind_kph: float
    chance_of_rain: int
    condition: str
    datetime: str