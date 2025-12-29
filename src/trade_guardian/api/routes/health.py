from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Liveness/Readiness probe", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


