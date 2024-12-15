import asyncio
from pathlib import Path

import httpx
import aiofiles

from pydebrid.progress import JobTracker
from pydebrid.models import MagnetResponse, TorrentInfo, TorrentData, LinkData


class Client(httpx.AsyncClient):
    progress = JobTracker()
    t_info: list[TorrentInfo] = list()

    def __init__(self, api_token: str):
        super().__init__(
            base_url="https://api.real-debrid.com/rest/1.0",
            headers={"Authorization": f"Bearer {api_token}"},
            http2=True,
        )

    async def get_torrent_data(self) -> list[TorrentData]:
        params = {"limit": 100}
        r = await self.get("/torrents", params=params)
        if r.status_code == 200:
            return [TorrentData(**data) for data in r.json()]
        raise ValueError(f"Error: {r.status_code}")

    async def get_tinfo(self, tid: str) -> TorrentInfo:
        r = await self.get(
            f"/torrents/info/{tid}",
        )
        if r.status_code == 200:
            return TorrentInfo(**r.json())
        raise ValueError(f"Error: {r.status_code}")

    async def torrent_unrestrict(self, data: TorrentData | TorrentInfo) -> None:
        responses = await asyncio.gather(
            *[
                self.post(
                    "/unrestrict/link",
                    data={"link": link},
                )
                for link in data.links
            ]
        )
        for r in responses:
            if r.status_code == 200:
                data.unrestricted.append(LinkData(**r.json()))
            else:
                raise ValueError(f"Error: {r.status_code}")

    async def unrestrict(self, url: str) -> LinkData:
        r = await self.post(
            "/unrestrict/link",
            data={"link": url},
        )
        if r.status_code == 200:
            return LinkData(**r.json())
        raise ValueError(f"Error: {r.status_code}")

    async def delete_torrent(self, tid: str):
        r = await self.delete(
            f"/torrents/delete/{tid}",
        )
        return r

    async def download(self, link_data: LinkData, savepath: str) -> None:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Pragma': 'no-cache',
            'Referer': 'https://real-debrid.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }
        spath = Path(savepath)
        if not spath.exists():
            raise ValueError("Save path does not exist")
        fname: str = link_data.filename
        total_size = link_data.filesize
        spath = Path(spath) / Path(fname)
        dlink: str = link_data.download
        chunk_size = 1024 * 1024
        task_id = self.progress.add_task(fname, total_size)

        async with self.stream("GET", dlink, headers=headers) as r:
            if r.status_code != 200:
                raise ValueError(f"Error: {r.status_code}")
            async with aiofiles.open(spath, "wb") as f:
                async for chunk in r.aiter_raw(chunk_size=chunk_size):
                    await f.write(chunk)
                    self.progress.update_task(task_id, len(chunk))
        if r.status_code == 200:
            link_data.downloaded = True

    async def download_delete(self, link_data: LinkData, savepath: str) -> None:
        await self.download(link_data, savepath)
        await self.delete_torrent(link_data.id)

    async def upload_magnet(self, link: str):
        r = await self.post(
            "/torrents/addMagnet",
            data={"magnet": link},
        )
        if not r.is_error:
            data = r.json()
            tid, url = data["id"], data["uri"]
            print(f"Torrent ID: {tid}")
            print(f"URL: {url}")
            return MagnetResponse(id=tid, url=url)
        raise ValueError(f"Error: {r.status_code}")

    async def select_files(self, tid: str, ids: str):
        r = await self.post(
            f"/torrents/selectFiles/{tid}",
            data={"files": ids},
        )
        return r

    async def batch_download(
        self, data: list[TorrentData], savepath: str
    ):
        self.progress.start_live_display()
        unrestrict_task = [self.unrestrict(link) for d in data for link in d.links]
        await asyncio.gather(*unrestrict_task)

        await asyncio.gather(
            *[
                self.download(link, savepath=savepath)
                for d in data
                for link in d.unrestricted
            ]
        )
        self.progress.stop_live_display()

    async def batch_hoster_download(self, links: list[str], savepath: str):
        self.progress.start_live_display()
        unrestrict_task = [self.unrestrict(link) for link in links]
        r = await asyncio.gather(*unrestrict_task)

        await asyncio.gather(*[self.download(link, savepath=savepath) for link in r])
        self.progress.stop_live_display()

    async def batch_tinfo(self, tids: list):
        return await asyncio.gather(*[self.get_tinfo(tid) for tid in tids])

    async def batch_unrestrict(self, links: list):
        return await asyncio.gather(*[self.unrestrict(link) for link in links])

    async def available_hosts(self):
        r = await self.get("/torrents/availableHosts")
        if r.status_code == 200:
            return r.json()
        raise httpx.HTTPStatusError(
            f"Error: {r.status_code}", request=r.request, response=r
        )

    async def add_torrent(self, torrent_path: Path):
        data = torrent_path.read_bytes()
        r = await self.put("/torrents/addTorrent", content=data)
        if r.status_code == 201:
            return r.json()
        raise httpx.HTTPStatusError(
            f"Error: {r.status_code}", request=r.request, response=r
        )

    async def unrestrict_check(self, link: str):
        r = await self.post("/unrestrict/check", data={"link": link})
        if r.status_code == 200:
            return r.json()
        raise httpx.HTTPStatusError(
            f"Error: {r.status_code}", request=r.request, response=r
        )

