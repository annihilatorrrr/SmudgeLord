import re
import os
import json
import esprima
import contextlib

from bs4 import BeautifulSoup as bs
from yt_dlp import YoutubeDL

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

    async def instagram(self, url: str, captions: str):
        post_id = re.findall(r"/(?:reel|p)/([a-zA-Z0-9_-]+)/", url)[0]
        r = await http.get(
            f"https://www.instagram.com/p/{post_id}/embed/captioned",
            follow_redirects=True,
        )
        soup = bs(r.text, "html.parser")
        medias = []

        if soup.find("div", {"data-media-type": "GraphImage"}):
            caption = re.sub(
                r'.*</a><br/><br/>(.*)(<div class="CaptionComments">.*)',
                r"\1",
                str(soup.find("div", {"class": "Caption"})),
            ).replace("<br/>", "\n")
            self.caption = f"{caption}\n<a href='{url}'>🔗 Link</a>"
            file = soup.find("img", {"class": "EmbeddedMediaImage"}).get("src")
            with open(f"./downloads/{file[60:80]}.jpg", "wb") as f:
                f.write((await http.get(file)).content)
            path = f"./downloads/{file['p'][60:80]}.jpg"
            medias.append({"e": "jpg", "p": path, "w": 0, "h": 0})

        data = re.findall(
            r'<script>(requireLazy\(\["TimeSliceImpl".*)<\/script>', r.text
        )

        if data and "shortcode_media" in data[0]:
            tokenized = esprima.tokenize(data[0])
            for token in tokenized:
                if "shortcode_media" in token.value:
                    jsoninsta = json.loads(json.loads(token.value))["gql_data"][
                        "shortcode_media"
                    ]

                    if caption := jsoninsta["edge_media_to_caption"]["edges"]:
                        self.caption = (
                            f"{caption[0]['node']['text']}\n<a href='{url}'>🔗 Link</a>"
                        )
                    else:
                        self.caption = f"\n<a href='{url}'>🔗 Link</a>"

                    if jsoninsta["__typename"] == "GraphVideo":
                        url = jsoninsta["video_url"]
                        dimensions = jsoninsta["dimensions"]
                        medias.append(
                            {
                                "e": "mp4",
                                "p": url,
                                "w": dimensions["width"],
                                "h": dimensions["height"],
                            }
                        )
                    else:
                        for post in jsoninsta["edge_sidecar_to_children"]["edges"]:
                            url = post["node"]["display_url"]
                            ext = "jpg"
                            if post["node"]["is_video"] is True:
                                url = post["node"]["video_url"]
                                ext = "mp4"
                            dimensions = post["node"]["dimensions"]
                            medias.append(
                                {
                                    "e": ext,
                                    "p": url,
                                    "w": dimensions["width"],
                                    "h": dimensions["height"],
                                }
                            )

        for m in medias:
            with open(f"./downloads/{m['p'][60:80]}.{m['e']}", "wb") as f:
                f.write((await http.get(m["p"])).content)
            path = f"./downloads/{m['p'][60:80]}.{m['e']}"
            self.files.append({"p": path, "w": m["w"], "h": m["h"]})
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
            self.files.append({"p": path, "w": media["width"], "h": media["height"]})

        return

    async def TikTok(self, url: str, id: int):
        self.caption = f"<a href='{url}'>🔗 Link</a>"
        x = re.match(r".*tiktok.com\/.*?(:?@[A-Za-z0-9]+\/video\/)?([A-Za-z0-9]+)", url)
        ydl = YoutubeDL({"outtmpl": f"./downloads/{id}/{x[2]}.%(ext)s"})
        yt = await extract_info(ydl, url, download=True)
        self.files.append(
            {
                "p": f"./downloads/{id}/{x[2]}.mp4",
                "w": yt["formats"][0]["width"],
                "h": yt["formats"][0]["height"],
            }
        )
        return
