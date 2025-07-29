from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx


class NicoNicoAPI:
    def __init__(self):
        self.http = httpx.AsyncClient(
            headers={
                "User-Agent": "neko-s-music-bot",
                "X-Frontend-Id": "6",
                "X-Frontend-Version": "0",
                "X-Niconico-Language": "ja-jp",
                "X-Client-Os-Type": "others",
                "X-Request-With": "https://www.nicovideo.jp",
                "Referer": "https://www.nicovideo.jp/",
            }
        )
        self.watchId: str = None
        self.trackId: str = None
        self.outputs: Dict[str, List[str]] = None
        self.nicosid: str = None
        self.domandBid: str = None

    async def getWatchData(self, videoId: str) -> dict:
        response = await self.http.get(
            f"https://www.nicovideo.jp/watch/{videoId}?responseType=json"
        )
        response.raise_for_status()
        self.domandBid = response.cookies.get("domand_bid", None)
        return response.json()

    def getOutputs(
        self, videoInfo: dict, *, audioOnly: bool = True
    ) -> Dict[str, List[str]]:
        outputs: Dict[str, List[str]] = {}
        topAudioId = None
        topAudioQuality = -1

        for audio in videoInfo["data"]["response"]["media"]["domand"]["audios"]:
            if audio["isAvailable"] and audio["qualityLevel"] > topAudioQuality:
                topAudioId = audio["id"]
                topAudioQuality = audio["qualityLevel"]

        if topAudioId is None:
            return outputs

        for video in videoInfo["data"]["response"]["media"]["domand"]["videos"]:
            if video["isAvailable"]:
                outputs[video["label"]] = (
                    [topAudioId] if audioOnly else [video["id"], topAudioId]
                )

        return outputs

    async def getHlsContentUrl(
        self, videoInfo: Dict[Any, Any], outputs: Dict[str, List[str]]
    ) -> str | None:
        videoId = videoInfo["data"]["response"]["client"]["watchId"]
        actionTrackId = videoInfo["data"]["response"]["client"]["watchTrackId"]
        accessRightKey = videoInfo["data"]["response"]["media"]["domand"][
            "accessRightKey"
        ]

        headers = self.http.headers
        headers["X-Access-Right-Key"] = accessRightKey

        response = await self.http.post(
            f"https://nvapi.nicovideo.jp/v1/watch/{videoId}/access-rights/hls?actionTrackId={actionTrackId}",
            json={"outputs": outputs},
            headers=headers,
        )

        if response.status_code == 201:
            self.watchId = videoId
            self.trackId = actionTrackId
            self.outputs = outputs
            self.nicosid = self.http.cookies["nicosid"]
            self.domandBid = response.cookies.get("domand_bid", None)
            jsonData = response.json()
            if jsonData["data"] is not None:
                return jsonData["data"]["contentUrl"]
        return None

    async def sendHeartBeat(self) -> bool:
        response = await self.http.post(
            f"https://nvapi.nicovideo.jp/v1/watch/{self.watchId}/access-rights/hls?actionTrackId={self.trackId}&__retry=0",
            json={
                "outputs": self.outputs,
                "heartbeat": {
                    "method": "regular",
                    "params": {
                        "eventType": "start",
                        "eventOccurredAt": datetime.now(
                            timezone(timedelta(hours=9))
                        ).isoformat(),
                        "watchMilliseconds": 0,
                        "endCount": 0,
                        "additionalParameters": {
                            "___pc_v": 1,
                            "os": "Windows",
                            "os_version": "15.0.0",
                            "nicosid": self.nicosid,
                            "referer": "",
                            "query_parameters": {},
                            "is_ad_block": False,
                            "has_playlist": False,
                            "___abw": None,
                            "abw_show": False,
                            "abw_closed": False,
                            "abw_seen_at": None,
                            "viewing_source": "",
                            "viewing_source_detail": {},
                            "playback_rate": "",
                            "use_flip": False,
                            "quality": [],
                            "auto_quality": [],
                            "loop_count": 0,
                            "suspend_count": 0,
                            "load_failed": False,
                            "error_description": [],
                            "end_position_milliseconds": None,
                            "performance": {
                                "watch_access_start": datetime.now(
                                    timezone(timedelta(hours=9))
                                ).timestamp()
                                * 1000,
                                "watch_access_finish": None,
                                "video_loading_start": (
                                    datetime.now(
                                        timezone(timedelta(hours=9))
                                    ).timestamp()
                                    + 10
                                )
                                * 1000,
                                "video_loading_finish": None,
                                "video_play_start": None,
                                "end_context": {
                                    "ad_playing": False,
                                    "video_playing": False,
                                    "is_suspending": False,
                                },
                            },
                        },
                    },
                },
            },
        )
        if response.status_code == 200:
            return True
        else:
            return False
