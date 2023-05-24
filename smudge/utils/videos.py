import re
import os
import json
import contextlib

from yt_dlp import YoutubeDL
from urllib.parse import unquote

from ..utils import aiowrap, http
from ..config import BARRER_TOKEN


@aiowrap
def extract_info(instance: YoutubeDL, url: str, download=True):
    instance.params.update({"logger": MyLogger()})
    return instance.extract_info(url, download)


class MyLogger:
    def debug(self, msg):
        if not msg.startswith("[debug] "):
            self.info(msg)

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    @staticmethod
    def error(msg):
        if "There's no video" not in msg:
            print(msg)


async def search_yt(query):
    page = await http.get(
        "https://www.youtube.com/results",
        params=dict(search_query=query, pbj="1"),
        headers={
            "x-youtube-Client-name": "1",
            "x-youtube-Client-version": "2.20200827",
        },
    )
    page = json.loads(page.content)
    list_videos = []
    for video in page[1]["response"]["contents"]["twoColumnSearchResultsRenderer"][
        "primaryContents"
    ]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]:
        if video.get("videoRenderer"):
            dic = {
                "title": video["videoRenderer"]["title"]["runs"][0]["text"],
                "url": "https://www.youtube.com/watch?v="
                + video["videoRenderer"]["videoId"],
            }
            list_videos.append(dic)
    return list_videos


class DownloadMedia:
    def __init__(self):
        self.cors: str = "https://cors-bypass.amanoteam.com/"
        self.TwitterAPI: str = "https://api.twitter.com/2/"

    async def download(self, url: str, id: str):
        self.files: list = []
        if re.search(r"instagram.com/", url):
            await self.instagram(url, id)
        elif re.search(r"tiktok.com/", url):
            await self.TikTok(url, id)
        elif re.search(r"twitter.com/", url):
            await self.Twitter(url, id)
        return self.files, self.caption

    async def instagram(self, url: str, id: str):
        res = await http.post("https://igram.world/api/convert", data={"url": url})
        data = res.json()

        self.caption = f"\n<a href='{url}'>🔗 Link</a>"

        if data:
            data = [data] if isinstance(data, dict) else data

            for media in data:
                url = re.sub(
                    r".*(htt.+?//)(:?ins.+?.fna.f.+?net|s.+?.com)?(.+?)(&file.*)",
                    r"\1scontent.cdninstagram.com\3",
                    unquote(media["url"][0]["url"]),
                )
                ext = media["url"][0]["ext"]
                with open(f"./downloads/{url[60:80]}.{ext}", "wb") as f:
                    f.write((await http.get(url)).content)
                path = f"./downloads/{url[60:80]}.{ext}"
                self.files.append({"path": path, "width": 0, "height": 0})
            return

    async def Twitter(self, url: str, id: str):
        # Extract the tweet ID from the URL
        tweet_id = re.match(".*twitter.com/.+status/([A-Za-z0-9]+)", url)[1]
        params: str = "?expansions=attachments.media_keys,author_id&media.fields=type,variants,url,height,width&tweet.fields=entities"

        # Send the request and parse the response as JSON
        res = await http.get(
            f"{self.TwitterAPI}tweets/{tweet_id}{params}",
            headers={"Authorization": f"Bearer {BARRER_TOKEN}"},
        )
        tweet = json.loads(res.content)

        self.caption = f"<a href='{url}'>🔗 Link</a>"

        # Iterate over the media attachments in the tweet
        for media in tweet["includes"]["media"]:
            if media["type"] in ("animated_gif", "video"):
                bitrate = [
                    a["bit_rate"]
                    for a in media["variants"]
                    if a["content_type"] == "video/mp4"
                ]
                key = media["media_key"]
                for a in media["variants"]:
                    with contextlib.suppress(FileExistsError):
                        os.mkdir(f"./downloads/{id}/")
                    if a["content_type"] == "video/mp4" and a["bit_rate"] == max(
                        bitrate
                    ):
                        path = f"./downloads/{id}/{key}.mp4"
                        with open(path, "wb") as f:
                            f.write((await http.get(a["url"])).content)
            else:
                path = media["url"]
            self.files.append(
                {"path": path, "width": media["width"], "height": media["height"]}
            )

        return

    async def TikTok(self, url: str, id: int):
        self.caption = f"<a href='{url}'>🔗 Link</a>"
        x = re.match(r".*tiktok.com\/.*?(:?@[A-Za-z0-9]+\/video\/)?([A-Za-z0-9]+)", url)
        ydl = YoutubeDL({"outtmpl": f"./downloads/{id}/{x[2]}.%(ext)s"})
        yt = await extract_info(ydl, url, download=True)
        self.files.append(
            {
                "path": f"./downloads/{id}/{x[2]}.mp4",
                "width": yt["formats"][0]["width"],
                "height": yt["formats"][0]["height"],
            }
        )
        return
