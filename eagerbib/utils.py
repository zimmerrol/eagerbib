import itertools
import os
import re
import hashlib
from typing import Iterable, Any
import platformdirs


def chunk_iterable(
        iterable: Iterable[Any], n: int, fillvalue: Any = None
) -> Iterable[list[Any]]:
    """Chunks an iterable into chunks of size n.

    Args:
        iterable (Iterable[Any]): The iterable to chunk.
        n (int): The size of the chunks.
        fillvalue (Any, optional): The value to use to fill the last chunk if the
            iterable is not divisible by n. Defaults to None.

    Returns:
        Iterable[list[Any]]: The chunks.
    """
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def cleanup_title(title: str) -> str:
    """Cleans up a title string by removing extra spaces, non-alphanumeric characters.

    Args:
        title (str): The title to clean up.

    Returns:
        str: The cleaned up title.
    """
    title = re.sub(r"[^a-zA-Z0-9]", r" ", title)
    title = re.sub(r"\s\s", r" ", title)
    title = re.sub(r"  ", r" ", title)
    title = title.strip()
    return title


def cleanup_author(author: str) -> str:
    """Cleans up an author string by removing newlines and double spaces.

    Args:
        author (str): The author to clean up.

    Returns:
        str: The cleaned up author.
    """
    author = author.replace("\n", " ")
    author = re.sub(r"\s\s", r" ", author)
    author = re.sub(r"  ", r" ", author)
    author = author.strip()
    return author


def get_md5_hash(fn: str) -> str:
    """Compute the MD5 hash of a file.

    Args:
        fn (str): The path to the file.

    Returns:
        str: The MD5 hash of the file.
    """
    hash_md5 = hashlib.md5()
    with open(fn, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_default_data_directory() -> str:
    """Returns the default data directory.

    Returns:
        str: The default data directory.
    """
    path = os.path.join(platformdirs.user_data_dir("eagerbib"), "data")
    if not os.path.exists(path):
        os.makedirs(path)
    return path
