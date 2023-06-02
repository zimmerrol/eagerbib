"""Update the offline bibliography files from pre-crawled data online."""
import argparse
import glob
import math
import os
import tarfile
import tempfile
from typing import Optional

import requests
import tqdm

import eagerbib.utils as ut

__predefined_bibliographies = {
    "mlcv": "TODO",
    "mlnlp": "TODO",
}


def download_bibliography_package(bibliography_url: str) -> str:
    """Download the bibliography package from the given URL to a temporary file.

    Args:
        bibliography_url (str): The URL to the bibliography package.

    Returns:
        str: The path to the temporary file.
    """
    # Download the .tar.gz file to a temporary file
    response = requests.get(bibliography_url, stream=True)
    if response.status_code != 200:
        raise ValueError(
            f"Could not download {bibliography_url}. "
            f"Status code: {response.status_code}"
        )
    length: Optional[int] = int(
        response.headers.get(
            "content-length", response.headers.get("Content-length", 0)
        )
    )
    if length is not None:
        length = int(math.ceil(length / (1024 * 1024)))
    else:
        length = None
    tmp_fn = os.path.join(tempfile.mkdtemp(), bibliography_url.split("/")[-1])
    with open(tmp_fn, "wb") as f:
        for data in tqdm.tqdm(
            response.iter_content(chunk_size=1024 * 1024), unit="mb", total=length,
            desc="Downloading bibliography package."
        ):
            f.write(data)

    return tmp_fn


def extract_bibliography_package(
    bibliography_package_fn: str, data_directory: str
) -> None:
    """Extract the bibliography package (tar.gz) to the given directory.

    Args:
        bibliography_package_fn (str): The path to the bibliography package.
        data_directory (str): The directory to extract the bibliography package to.
    """
    # Extract a .tar.gz file to a directory
    try:
        file = tarfile.open(bibliography_package_fn, "r:gz")
    except tarfile.ReadError:
        raise ValueError(f"Could not open {bibliography_package_fn} as a tar.gz file.")
    else:
        try:
            file.extractall(data_directory)
        except tarfile.ExtractError:
            raise ValueError(
                f"Could not extract {bibliography_package_fn} to " f"{data_directory}."
            )
        file.close()
        os.remove(bibliography_package_fn)


def clear_existing_bibliography_files(data_directory: str):
    """Clear the existing bibliography files.

    Args:
        data_directory (str): The directory to clear the bibliography files from.
    """
    for fn in glob.glob(f"{data_directory}/*.bib"):
        os.remove(fn)
    if os.path.exists(f"{data_directory}/cache.json.gz"):
        os.remove(f"{data_directory}/cache.json.gz")


def update_bibliography_files(
    bibliography_name_or_url: str, data_directory: str, replace_existing: bool
) -> None:
    """Update the bibliography files from the given URL.

    Args:
        bibliography_name_or_url (str): The name or URL of the bibliography to update.
        data_directory (str): The directory to store the bibliography files in.
        replace_existing (bool): True to replace/remove existing files.
    """
    if bibliography_name_or_url in __predefined_bibliographies:
        bibliography_url = __predefined_bibliographies[bibliography_name_or_url]
    else:
        bibliography_url = bibliography_name_or_url

    bibliography_fn = download_bibliography_package(bibliography_url)
    if replace_existing:
        clear_existing_bibliography_files(data_directory)
    extract_bibliography_package(bibliography_fn, data_directory)


def main() -> None:
    parser = argparse.ArgumentParser(
        "eagerbib-updater", description="Update the offline bibliography files."
    )
    parser.add_argument(
        "--bibliography",
        "-b",
        type=str,
        required=True,
        help="Name/URL of the bibliography to install/update locally.",
    )
    parser.add_argument(
        "--data-directory",
        "-d",
        type=str,
        default=ut.get_default_data_directory(),
        help="The directory to store the bibliography files in.",
    )
    parser.add_argument(
        "--replace-existing",
        "-re",
        action="store_true",
        help="True to replace/remove existing files.",
    )

    args = parser.parse_args()

    update_bibliography_files(
        args.bibliography, args.data_directory, args.replace_existing
    )


if __name__ == "__main__":
    main()
