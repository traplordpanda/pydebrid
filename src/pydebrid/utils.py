import re
from re import Match
from pathlib import Path

import httpx

from typing import Generator


def number_set_generator(snum: str) -> Generator:
    for part in snum.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            yield from range(start, end + 1)
        else:
            yield int(part)


def get_jav_info(dvd_id: str) -> dict | None:
    url = f"https://bot-api.r18.dev/videos/vod/movies/detail/-/dvd_id={dvd_id}/json"
    r = httpx.get(url)
    if r.status_code == 200:
        return r.json()
    return None


def clean_filename(fname: str) -> Match[str] | None:
    reg = re.compile(r"([a-zA-Z]{2,6}-\d{1,5})(?:-[a-zA-Z]{1,2})?")
    r = reg.search(fname)
    if r:
        return r
    return None


def sanitize_filename(filename: str) -> str:
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f\!\']'
    sanitized = re.sub(illegal_chars, "", filename)
    sanitized = sanitized.strip(". ")
    return sanitized


def clean_directory_filenames(directory: str | Path) -> list[str]:
    """
    Clean all filenames in the specified directory using the clean_filename function.

    Args:
        directory: Path to the directory containing files to clean

    Returns:
        List of tuples containing (original_name, new_name) for all processed files
    """
    dir_path = Path(directory) if isinstance(directory, str) else directory

    # Ensure directory exists
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"Invalid directory path: {dir_path}")

    renamed_files = []

    for file_path in dir_path.iterdir():
        if file_path.is_file():
            extension = file_path.suffix
            if extension != ".mp4":
                continue

            cleaned_name = clean_filename(file_path.stem)
            if cleaned_name:

                info = get_jav_info(cleaned_name.group(1))
                if info:
                    if title := info.get("title"):
                        info = sanitize_filename(title)
                        if len(info) > 200:
                            info = info[:150]
                        new_name = f"{cleaned_name.group().upper()} {info}{extension}"
                else:
                    new_name = cleaned_name.group().upper() + extension
                new_path = file_path.parent / new_name
                file_path.rename(new_path)
                renamed_files.append(new_name)

    return renamed_files
