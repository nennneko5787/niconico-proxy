from fastapi import APIRouter
from pydantic import BaseModel

from services.nico import NicoNicoAPI

router = APIRouter()


class VideoDetail(BaseModel):
    id: str
    title: str
    author: str
    duration: int
    thumbnail: str


@router.get("/video/{videoId:str}")
async def getVideoDetail(videoId: str):
    """Get video detail."""
    data = await NicoNicoAPI().getWatchData(videoId)

    videoId = data["data"]["response"]["video"]["id"]
    title = data["data"]["response"]["video"]["title"]
    author = data["data"]["response"]["owner"]["nickname"]
    duration = int(data["data"]["response"]["video"]["duration"]) * 1000
    thumbnail = data["data"]["response"]["video"]["thumbnail"]["ogp"]

    return VideoDetail(
        id=videoId,
        title=title,
        author=author,
        duration=duration,
        thumbnail=thumbnail,
    )
