from typing import Generator


def number_set_generator(snum: str) -> Generator:
    for part in snum.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            yield from range(start, end + 1)
        else:
            yield int(part)
