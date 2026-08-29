from fastapi import APIRouter
from .. import service

router = APIRouter(prefix="/rework", tags=["rework"])

@router.get("/report")
def report():
    """The weekly rework & quality report (issues, not people)."""
    return service.rework_report()
