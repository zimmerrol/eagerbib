"""Download bibtex data from dblp.org for a pre-define set of reoccurring venues.

This will save overall bandwidth and time, as the data is cached locally and less
queries need to be send to dblp.org in the long run.
"""
import contextlib
import inspect
import os
import re
import time
import warnings
from typing import Optional

import requests
import tqdm


def get_all_occurrences_of_venue(venue_key: str) -> list[Optional[str]]:
    """Get all occurrences of a venue from dblp.org.

    Args:
        venue_key (str): The dblp.org key of the venue.

    Returns:
        list[str]: A list of dblp.org keys of all occurrences of the venue.
    """
    url = (
        "https://dblp.org/search/publ/api?q=Editorship+"
        "stream%3Astreams/{0}%3A&h=1000&format=json"
    ).format(venue_key)

    def _get_bht(dblp_url: str) -> Optional[str]:
        """Get the BHT identifier from a dblp.org URL without sending too many requests.
        See `get_bht_identifier_from_dblp_url` for more information.

        Args:
            dblp_url (str): The dblp.org URL.

        Returns:
            Optional[str]: The BHT identifier or None if it could not be obtained.
        """
        time.sleep(1)
        return get_bht_identifier_from_dblp_url(dblp_url)

    while True:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data["result"]["status"]["@code"] == "200":
                hits_info = data["result"]["hits"]
                if hits_info["@sent"] != hits_info["@total"]:
                    raise NotImplementedError("Pagination not implemented yet.")
                urls = [hit["info"]["url"] for hit in hits_info["hit"]]
                bhts = [
                    _get_bht(url)
                    for url in tqdm.tqdm(
                        urls, desc="Obtaining BHT identifiers", position=1, leave=False
                    )
                ]

                return bhts
        time.sleep(1)


@contextlib.contextmanager
def redirect_to_tqdm():
    """Redirect print to tqdm.write allowing comfortable printing while using tqdm."""
    # Store builtin print
    old_print = print

    def new_print(*args, **kwargs):
        # If tqdm.tqdm.write raises error, use builtin print
        try:
            value = " ".join(args)
            tqdm.tqdm.write(value, **kwargs)
        except:
            old_print(*args, **kwargs)

    try:
        # Globally replace print with new_print
        inspect.builtins.print = new_print
        yield
    finally:
        inspect.builtins.print = old_print


def download_bibtex_of_venue_occurrence(
    bht_identifier: str, base_folder: str, n_max_attempts: int = 10
) -> None:
    """Download the bibtex data of a venue occurrence from dblp.org.

    Args:
        bht_identifier (str): The BHT name on dblp.org of the venue occurrence.
        base_folder (str): The base folder where the bibtex data will be stored.
        n_max_attempts (int, optional): The maximum number of attempts to download
            the bibtex data. Defaults to 10.
    """
    venue_occurrence_key = bht_identifier
    if venue_occurrence_key.startswith("db/"):
        venue_occurrence_key = venue_occurrence_key[3:]
    else:
        raise ValueError(f"unexpected value for `bht_identifier`: {bht_identifier}")

    base_url = (
        "https://dblp.org/search/publ/api?q=toc%3A{0}.bht%3A"
        "&f={{0}}&h={{1}}&format=bibtex"
    ).format(bht_identifier.replace("/", "%2F"))

    fn = os.path.join(base_folder, f"{venue_occurrence_key.replace('/', '_')}.bib")
    # Skip if file already exists.
    if os.path.exists(fn):
        return

    def fetch(url: str, n_max_attempts: int) -> Optional[str]:
        for _ in range(n_max_attempts):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return response.text
                else:
                    time.sleep(1)
            except requests.exceptions.RequestException:
                time.sleep(1)
        return None

    # The dblp API can only return 1000 entries at a time. We need to paginate.
    data = ""
    start_idx = 0
    pagination_reached_end = False
    while not pagination_reached_end:
        url = base_url.format(start_idx, start_idx + 1000)
        start_idx += 1000

        response = fetch(url, n_max_attempts)
        if response is None:
            warnings.warn(
                f"Max attempts reached for `{venue_occurrence_key}`. Skipping. "
            )
            return
        else:
            data += response
        if len(response) == 0:
            pagination_reached_end = True

    if len(data) == 0:
        warnings.warn(f"No data for `{venue_occurrence_key}`. Skipping.")
        return

    with open(fn, "w") as f:
        f.write(data)


def get_bht_identifier_from_dblp_url(
    dblp_url: str, n_max_attempts: int = 3
) -> Optional[str]:
    """Get the BHT identifier from a dblp.org URL.

    Args:
        dblp_url (str): The dblp.org URL.

    Returns:
        Optional[str]: The BHT identifier if it can be found.
    """
    text = ""
    for _ in range(n_max_attempts):
        pattern = re.compile(
            r'<a class="toc-link" href="(https?://[^\s"]+)">\[contents\]<\/a>'
        )
        with requests.get(dblp_url, stream=True) as r:
            if r.status_code != 200:
                time.sleep(1)
                continue
            iterator = r.iter_content(chunk_size=1024)
            for bytes in iterator:
                new_text = bytes.decode("utf-8")
                text += new_text
                matches = pattern.findall(text)
                if len(matches) > 0:
                    value = matches[0]
                    if value.startswith("https://dblp.org/"):
                        value = value[17:]
                    if value.endswith(".html"):
                        value = value[:-5]
                    return value
    warnings.warn(f"Could not detect BHT identifier for {dblp_url}. Skipping.")
    return None


def main():
    venues = [
        "conf/aaai",
        "conf/aistats",
        # "conf/eccv",
        "conf/cvpr",
        # "conf/iccv"
        "conf/iclr",
        "conf/icml",
        # "conf/nips",
        "conf/ijcai",
        "conf/colt",
        "conf/uai",
        "conf/icra",
    ]

    for venue in tqdm.tqdm(venues, desc="Processing venues", position=0):
        occurrences = get_all_occurrences_of_venue(venue)
        # Filter out None values for which no BHT key could be extracted.
        # This should rarely/never happen.
        occurrences = [oc for oc in occurrences if oc is not None]
        for oc in tqdm.tqdm(
            occurrences, desc="Downloading BibTex data", position=1, leave=False
        ):
            with redirect_to_tqdm():
                download_bibtex_of_venue_occurrence(oc, "test_data")


if __name__ == "__main__":
    main()
