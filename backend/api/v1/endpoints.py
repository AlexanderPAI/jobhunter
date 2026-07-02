from fastapi import APIRouter

router = APIRouter(prefix="/v1")


@router.get("/test")
async def test_endpoint():
    return {"message": "Hello World"}
