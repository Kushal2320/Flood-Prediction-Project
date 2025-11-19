from fastapi import APIRouter, HTTPException, Query
from .temp import predict_flood_for_city

router = APIRouter()

@router.get("/predict_flood")
def predict_flood(city: str = Query(..., min_length=1)):
    try:
        return predict_flood_for_city(city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

