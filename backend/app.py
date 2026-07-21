import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.v1.auth import router as auth_router
from backend.api.v1.endpoints import router
from backend.api.v1.history import router as history_router
from backend.llm_providers.openrouter import LLMProviderError

app = FastAPI()
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(router)


@app.exception_handler(LLMProviderError)
async def llm_provider_error_handler(
    request: Request, exc: LLMProviderError
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
