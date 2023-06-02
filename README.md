# eagerbib: Updating and normalizing your BibTex bibliography.



## Installation

```bash
pip install git+https://github.com/zimmerrol/eagerbib.git
```

## Usage

```bash
usage: eagerbib [-h] [--config CONFIG] --input INPUT --output OUTPUT [--bibliography-folder BIBLIOGRAPHY_FOLDER] [--online-updater.enable ONLINE_UPDATER.ENABLE] [--online-updater.n-suggestions ONLINE_UPDATER.N_SUGGESTIONS]
                [--online-updater.services ONLINE_UPDATER.SERVICES] [--online-updater.n-parallel-requests ONLINE_UPDATER.N_PARALLEL_REQUESTS] [--output-processor.name-normalizations OUTPUT_PROCESSOR.NAME_NORMALIZATIONS]
                [--output-processor.deduplicate OUTPUT_PROCESSOR.DEDUPLICATE] [--output-processor.shorten OUTPUT_PROCESSOR.SHORTEN] [--output-processor.sort OUTPUT_PROCESSOR.SORT] [--output-processor.remove-fields OUTPUT_PROCESSOR.REMOVE_FIELDS]
                [--output-processor.normalize-preprints OUTPUT_PROCESSOR.NORMALIZE_PREPRINTS]

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        The config yaml file to use.
  --input INPUT, -i INPUT
                        The input bib file.
  --output OUTPUT, -o OUTPUT
                        The output bib file.
  --bibliography-folder BIBLIOGRAPHY_FOLDER, -l BIBLIOGRAPHY_FOLDER
                        Folder to load offline candidate bibliography files from.
  --online-updater.enable ONLINE_UPDATER.ENABLE
                        True to enable the online/semi-automated reference updater.
  --online-updater.n-suggestions ONLINE_UPDATER.N_SUGGESTIONS
                        Number of suggestions per service to show.
  --online-updater.services ONLINE_UPDATER.SERVICES
                        The services to use.
  --online-updater.n-parallel-requests ONLINE_UPDATER.N_PARALLEL_REQUESTS
                        Number of parallel requests. Higher values may lead to to less buffering while updating references but this requires sufficiently high network bandwidth.
  --output-processor.name-normalizations OUTPUT_PROCESSOR.NAME_NORMALIZATIONS
                        The list of conference name data.
  --output-processor.deduplicate OUTPUT_PROCESSOR.DEDUPLICATE
                        True to remove entries that are duplicates based oneither their properties or their ID.
  --output-processor.shorten OUTPUT_PROCESSOR.SHORTEN
                        True to shorten the conference names.
  --output-processor.sort OUTPUT_PROCESSOR.SORT
                        True to sort the output BibTeX entries alphabetically by ID.
  --output-processor.remove-fields OUTPUT_PROCESSOR.REMOVE_FIELDS
                        A list of fields to remove from the output entries.
  --output-processor.normalize-preprints OUTPUT_PROCESSOR.NORMALIZE_PREPRINTS
                        True to normalize preprints (e.g., arXiv) to the same format.
```

### Configuring eagerbib
Instead of passing command line arguments, you can also control everything in eagerbib
via a config yaml file. For an example, refer to the [default config file](default_config.yaml).

To use a custom config file, simply pass it to eagerbib via the `--config` argument.


## Acknowledgements
This project was inspired by [rebiber](https://github.com/yuchenlin/rebiber).