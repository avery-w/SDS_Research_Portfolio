from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import AnalyticsResponse
from app.api.deps import get_db, RoleChecker
from app.models.models import UserRole

router = APIRouter()
allow_admin = RoleChecker([UserRole.ADMIN])

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(user=Depends(allow_admin), db: Session = Depends(get_db)):
    # Mock aggregation logic
    return AnalyticsResponse(
        total_revenue=15000.0,
        top_selling_products=[{"product_id": 101, "count": 50}],
        seller_performance=[{"seller_id": 1, "avg_fulfillment_days": 2.5}]
    )
