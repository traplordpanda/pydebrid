import asyncio
import os
from itertools import islice
from pathlib import Path
from typing import Optional
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.table import Table

from pydebrid.client import Client
from pydebrid.progress import torrent_table, detailed_torrent_table

API_TOKEN = os.environ.get("RD_KEY")

if not API_TOKEN:
    raise ValueError("API Token not found")


client = Client(api_token=API_TOKEN)

console = Console()


async def cli_download(save_path: Path, num_downloads: Optional[int] = None):

    if not save_path.exists():
        raise ValueError("Save path does not exist")

    torrent_data = await client.get_torrent_data()
    downloads = (t for t in torrent_data if t.status == "downloaded")
    if num_downloads:
        downloads = list(islice(downloads, num_downloads))
    else:
        downloads = list(downloads)

    await asyncio.gather(*[client.torrent_unrestrict(t) for t in downloads])
    await client.batch_download(downloads, str(save_path))
    tasks = list()
    for t in downloads:
        if all([u.downloaded for u in t.unrestricted]):
            tasks.append(t.id)
    await asyncio.gather(*[client.delete_torrent(tid) for tid in tasks])


async def cli_magnet(magnet_link: str):
    rmagnet = await client.upload_magnet(magnet_link)
    rtinfo = await client.get_tinfo(rmagnet.id)
    if rtinfo:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("File", style="dim")
        for fdata in rtinfo.files:
            table.add_row(str(fdata.id), fdata.path)
        console.print(table)
        download_id = input("id to download: ")
        await client.select_files(rtinfo.id, download_id)


async def cli_check(n: Optional[int] = None):
    torrents = await client.get_torrent_data()
    if n:
        torrents = list(islice(torrents, n))
    table = torrent_table(torrents)
    console.print(table)


async def cli_check_detailed(n: Optional[int] = None):
    torrents = await client.get_torrent_data()
    if n:
        torrents = list(islice(torrents, n))

    detailed_torrent_data = await client.batch_tinfo([t.id for t in torrents])
    table = detailed_torrent_table(detailed_torrent_data)
    console.print(table)


async def cli_hoster_download(
    file_data: Path, save_path: Path, n: Optional[int] = None
):
    if not save_path.exists():
        raise ValueError("Save path does not exist")

    with open(file_data, "r") as f:
        links = f.readlines()

    if n:
        links = links[:n]
    links = [link.strip() for link in links]

    await client.batch_hoster_download(links, str(save_path))


app = typer.Typer()


@app.command()
def download(
    save_path: Path = typer.Argument(..., help="Path to save downloaded files"),
    n: Optional[int] = typer.Option(None, help="Number of downloads to start"),
):
    """
    Download files from Real-Debrid
    """

    asyncio.run(cli_download(save_path, n))


@app.command("m")
def magnet(magnet_link: str = typer.Argument(help="Magnet link to upload")):
    """
    Upload a magnet link and select files to download
    """
    asyncio.run(cli_magnet(magnet_link))


@app.command()
def check(
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    n: Optional[int] = typer.Option(None, help="Number of torrents to display"),
):
    """
    Show current status of torrents
    """
    if verbose:
        asyncio.run(cli_check_detailed(n))
    else:
        asyncio.run(cli_check(n))


@app.command()
def hoster(
    file_data: Path = typer.Argument(..., help="File containing hoster links"),
    save_path: Path = typer.Argument(..., help="Path to save downloaded files"),
    n: Optional[int] = typer.Option(None, help="Number of downloads to start"),
):
    """
    Download files from hoster links
    """
    asyncio.run(cli_hoster_download(file_data, save_path, n))


if __name__ == "__main__":
    p = "/home/kyle/code/pydebrid"
    app(["download", p, "--n", "1"])
