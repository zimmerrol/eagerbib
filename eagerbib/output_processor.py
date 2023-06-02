import abc
import re
import sys
from datetime import datetime
from typing import Literal, Union
import eagerbib.config as cfg


class BaseProcessingCommand(abc.ABC):
    """Base class for processing commands."""
    def __init__(self, current_item: dict[str, str]):
        self.current_item = current_item

    @property
    @abc.abstractmethod
    def output(self) -> dict[str, str]:
        pass


class UpdateItemProcessingCommand(BaseProcessingCommand):
    """A command to update an item in the bibliography.

    Args:
        current_item (dict[str, str]): The current item in the bibliography.
        new_item (dict[str, str]): The new item to replace the current item with.
    """
    def __init__(self, current_item: dict[str, str], new_item: dict[str, str],
                 method: Union[Literal["automated"], Literal["manual"]]):
        super().__init__(current_item)

        # Update id/key of the new item to match the current item.
        new_item["ID"] = current_item["ID"]

        current_date = datetime.now().strftime("%Y-%m-%d")
        new_item["eagerbib_comment"] = f"{method} update on {current_date}"

        self.new_item = new_item

    @property
    def output(self) -> dict[str, str]:
        return self.new_item


class KeepItemProcessingCommand(BaseProcessingCommand):
    """A command to keep an item in the bibliography.

    Args:
        current_item (dict[str, str]): The current item in the bibliography.
    """
    def __init__(self, current_item: dict[str, str]):
        super().__init__(current_item)

    @property
    def output(self) -> dict[str, str]:
        return self.current_item


def transform_reference_dict_to_lines(item: dict[str, str]) -> list[str]:
    """Transform a reference dictionary to a list of lines."""
    item_lines = [f"@{item['ENTRYTYPE']}{{{item['ID']},"]
    for key, value in item.items():
        if key == "ENTRYTYPE" or key == "ID":
            continue
        item_lines += [f"  {key} = {{{value}}},"]
    item_lines += ["}"]
    return item_lines


def _normalize_preprints(entries: list[dict[str, str]]):
    """Normalizes preprints in the bibliography.

    Args:
        entries (list[dict[str, str]]): The bibliography entries that will be updated
            in-place.
    """
    print("Normalizing preprints:")
    for i in range(len(entries)):
        entry = entries[i]
        entry_str = " ".join(transform_reference_dict_to_lines(entry)).lower()
        arxiv_ids = set()
        # Find arXiv IDs in the entry. This pattern was proposed by the rebiber authors.
        for m in re.finditer(
                r"(arxiv:|arxiv.org\/abs\/|arxiv.org\/pdf\/)([0-9]{4}).([0-9]{5})",
                entry_str):
            arxiv_ids.add(f"{m.group(2)}.{m.group(3)}")
        if len(arxiv_ids) > 1:
            print(f"• Cannot normalize {entry['ID']}: conflicting arXiv IDs found.")
        elif len(arxiv_ids) == 1:
            new_entry = {k: entry[k] for k in ["ID", "ENTRYTYPE", "author", "title"]}
            new_entry["eprint"] = arxiv_ids.pop()
            new_entry["journal"] = "arXiv preprint"
            new_entry["volume"] = f"abs/{new_entry['eprint']}"
            new_entry["year"] = "20" + new_entry["eprint"].split(".")[0][:2]
            new_entry["url"] = f"https://arxiv.org/abs/{new_entry['eprint']}"
            # Update entry by removing old and inserting new entry.
            entries.pop(i)
            entries.insert(i, new_entry)


def _remove_duplicates(entries: list[dict[str, str]]):
    """Removes duplicate entries from the bibliography.

    Args:
        entries (list[dict[str, str]]): The bibliography entries that will be updated
            in-place.
    """
    # Remove duplicate entries based on their ID.
    duplicated_idxs = []
    for i1 in range(len(entries)):
        for i2 in range(i1 + 1, len(entries)):
            if entries[i1]["ID"] == entries[i2]["ID"]:
                print(entries[i1])
                print(entries[i2])
                duplicated_idxs.append(i2)
    if len(duplicated_idxs) > 0:
        print("Detected duplicate keys:")
        for i in sorted(duplicated_idxs, reverse=True):
            print(f"• {entries[i]['ID']}")
            del entries[i]

    # Remove duplicate entries based on their properties.
    duplicated_idx_pairs = []
    for i1 in range(len(entries)):
        l1 = transform_reference_dict_to_lines(entries[i1])
        s1 = "\n".join(l1[1:])
        for i2 in range(i1 + 1, len(entries)):
            l2 = transform_reference_dict_to_lines(entries[i2])
            s2 = "\n".join(l2[1:])
            if s1 == s2:
                duplicated_idx_pairs.append((i1, i2))
    duplicated_idxs = sorted(duplicated_idx_pairs, key=lambda x: x[1], reverse=True)
    if len(duplicated_idxs) > 0:
        print("Detected duplicate entries:")
        for (i1, i2) in duplicated_idxs:
            print(f"• {entries[i2]['ID']} -> {entries[i1]['ID']}")
            del entries[i2]


def _remove_fields(entries: list[dict[str, str]], fields: list[str]):
    """Removes fields from the bibliography entries.

    Args:
        entries (list[dict[str, str]]): The bibliography entries that will be updated
            in-place.
        fields (list[str]): The fields that will be removed.
    """

    print("Removing fields:")
    for fk in fields:
        print(f"• {fk}")
        for entry in entries:
            if fk in entry:
                del entry[fk]


def _apply_abbreviations(entries: list[dict[str, str]],
                         abbreviations: list[cfg.NameNormalizationConfig]):
    """Applies name_normalizations to the bibliography entries.

    Args:
        entries (list[dict[str, str]]): The bibliography entries that will be updated
            in-place.
        abbreviations (list[cfg.NameNormalizationConfig]): The name_normalizations that will be
            used to update the entries.
    """

    if len(abbreviations) == 0:
        return
    print("Normalizing names.")

    for abbreviation in abbreviations:
        for full_name in abbreviation.alternative_names:
            # Check if the regular expression is valid.
            try:
                re.compile(full_name)
            except re.error:
                print(f"• Invalid regular expression for {abbreviation.name}: {full_name}")
                sys.exit(-1)
            for entry in entries:
                for field in ["journal", "booktitle"]:
                    if field in entry and re.match(full_name, entry[field]):
                        entry[field] = abbreviation.name


def process_commands(commands: list[BaseProcessingCommand],
                     config: cfg.OutputProcessorConfig) -> list[dict[str, str]]:
    """Process the commands and return the output bibliography items.

    Args:
        commands (list[BaseProcessingCommand]): The processing commands.
        config: (cfg.OutputProcessorConfig): The output writer configuration.

    Returns:
        list[dict[str, str]]: The output bibliography items.
    """
    entries = [command.output for command in commands]

    # Sort entries.
    if config.sort:
        entries = sorted(entries, key=lambda x: x["ID"])

    # Apply name_normalizations.
    if len(config.name_normalizations) > 0:
        _apply_abbreviations(entries, config.name_normalizations)

    # Normalize preprints.
    if config.normalize_preprints:
        _normalize_preprints(entries)

    # Remove unwanted fields.
    if len(config.remove_fields) > 0:
        _remove_fields(entries, config.remove_fields)

    # Remove duplicates.
    if config.deduplicate:
        _remove_duplicates(entries)

    return entries


def write_output(output: list[dict[str, str]], output_fn: str) -> None:
    """Write the output to a file in BibTeX format.

    Args:
        output (list[dict[str, str]]): The output bibliography items to write.
        output_fn (str): The path to the output file.
    """
    all_lines = []
    for item in output:
        all_lines += transform_reference_dict_to_lines(item) + [""]

    # Remove the last newline.
    if len(all_lines) > 0:
        del all_lines[-1]

    with open(output_fn, "w") as f:
        f.write("\n".join(all_lines))
