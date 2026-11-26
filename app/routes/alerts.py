from fastapi import APIRouter, Request

from app.models import AlertResponse


router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(request: Request) -> list[AlertResponse]:
    return request.app.state.device_repository.list_alerts()