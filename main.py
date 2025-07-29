from fastapi import FastAPI

from routes import detail, stream

app = FastAPI(
    title="NicoNico Proxy",
    description="ニコニコ動画をプロキシします。クッキー対応がだるすぎる",
)

app.include_router(detail.router)
app.include_router(stream.router)


@app.get("/")
def index():
    return {"detail": "ok"}
