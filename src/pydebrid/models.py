from typing import Optional
from pydantic import BaseModel, HttpUrl


class FileData(BaseModel):
    """
    For use in TorrentInfo
    """

    id: int
    path: str
    bytes: int
    selected: int


class MagnetResponse(BaseModel):
    id: str
    url: HttpUrl


class LinkData(BaseModel):
    """
    Data returned from unrestricted links
    """

    id: str
    filename: str
    mimeType: str
    filesize: int
    link: str
    host: str
    host_icon: str
    chunks: int
    crc: int
    download: str
    streamable: int
    downloaded: bool = False


class TorrentInfo(BaseModel):
    """
    Data returned from /torrents/info/{tid}
    Specific information about a torrent
    """

    id: str
    filename: str
    original_filename: str
    hash: str
    bytes: int
    original_bytes: int
    host: str
    split: int
    progress: float
    status: str
    added: str
    files: list[FileData]
    links: list[str] = []
    ended: Optional[str] = None
    speed: Optional[int] = None
    seeders: Optional[int] = None
    unrestricted: list[LinkData] = []


class TorrentData(BaseModel):
    """
    Data returned from /torrents
    General information about all torrents
    """

    id: str
    filename: str
    hash: str
    bytes: int
    host: str
    split: int
    progress: float
    status: str
    added: str
    links: list[str]
    unrestricted: list[LinkData] = []
