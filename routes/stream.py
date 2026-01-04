import asyncio
from typing import AsyncGenerator, Callable, Tuple

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from services.nico import NicoNicoAPI

router = APIRouter()


async def genAudioStream(
    nico: NicoNicoAPI, hslContentUrl: str
) -> Tuple[AsyncGenerator, Callable]:
    cookies = nico.http.cookies

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-headers",
        f"cookie: {'; '.join(f'{k}={v}' for k, v in cookies.items())}",
        "-reconnect",
        "1",
        "-reconnect_streamed",
        "1",
        "-reconnect_delay_max",
        "5",
        "-i",
        hslContentUrl,
        "-bufsize",
        "64k",
        "-analyzeduration",
        "2147483647",
        "-probesize",
        "2147483647",
        "-vn",
        "-acodec",
        "copy",
        "-f",
        "adts",
        "-",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def sendHeartBeat():
        while True:
            await nico.sendHeartBeat()
            await asyncio.sleep(5)

    task = asyncio.create_task(sendHeartBeat())

    async def stream():
        try:
            while True:
                data = await process.stdout.read(4096)
                if not data:
                    break
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            await cleanup()

    async def cleanup():
        if process.returncode is None:
            process.kill()
            await process.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    return stream(), cleanup


@router.get("/video/{videoId:str}/stream")
async def getVideoDetail(videoId: str, backgroundTasks: BackgroundTasks):
    """Get video detail."""
    nico = NicoNicoAPI()

    data = await nico.getWatchData(videoId)
    outputs = nico.getOutputs(data, audioOnly=True)
    outputLabel = next(iter(outputs))

    hslContentUrl = await nico.getHlsContentUrl(data, [outputs[outputLabel]])
    if hslContentUrl is None:
        raise HTTPException(500, "Failed to get the HLS content URL")

    print(hslContentUrl)

    stream, cleanup = await genAudioStream(nico, hslContentUrl)
    backgroundTasks.add_task(cleanup)
    return StreamingResponse(stream, media_type="audio/aac")
