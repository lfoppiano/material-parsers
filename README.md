[![Python CI](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml/badge.svg)](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml)

# Material Parsers (and other tools)

Previously this project was released as `grobid-superconductors-tools`, born as aister project of [grobid-superconductors](https://github.com/lfoppiano/grobid-superconductors) containing a web service that interfaces with the python libraries (e.g. Spacy).

The service provides the following functionalities:

- [Convert material name to formula](#convert-material-name-to-formula) (e.g. Lead -> Pb, Hydrogen -> H): `/convert/name/formula`
- [Decompose formula into structured dict of elements](#decompose-formula-into-structured-dict-of-elements) (e.g. La x Fe 1-x O7-> {La: x, Fe: 1-x, O: 7}):  `/convert/formula/composition`
- Classify material in classes (from the superconductors domain) using a rule-base table (e.g. "La Cu Fe" -> Cuprates): `/classify/formula`
- Tc's classification (Tc, not-Tc): `/classify/tc` **for information please open an issue**
- Relation extraction given a sentence and two entities: `/process/link` **for information please open an issue**
- Material processing using Deep Learning models and rule-based processing `/process/material`

## Usage

The service is deployed on huggingface spaces, and [can be used right away](https://lfoppiano-grobid-superconductors-tools.hf.space/version). For installing the service in your own environment see below.


### Convert material name to formula

```
curl --location 'https://lfoppiano-grobid-superconductors-tools.hf.space/convert/name/formula' \
--form 'input="Hydrogen"'
```

output:

```
{"composition": {"H": "1"}, "name": "Hydrogen", "formula": "H"}
```

### Decompose formula in a structured dict of elements

Example:

```
curl --location 'https://lfoppiano-grobid-superconductors-tools.hf.space/convert/formula/composition' \

--form 'input="CaBr2-x"'
```

output:

```
{"composition": {"Ca": "1", "Br": "2-x"}}
```

### Classify materials in classes

Example:

```
curl --location 'https://lfoppiano-grobid-superconductors-tools.hf.space/classify/formula' \
--form 'input="(Mo 0.96 Zr 0.04 ) 0.85 B x "'
```

output:

```
['Alloys']
```

### Process material
This process includes a combination of everything listed above, after passing the material sequence through a DL model 

Example:

```
curl --location 'https://lfoppiano-material-parsers.hf.space/process/material' \
--form 'text="(Mo 0.96 Zr 0.04 ) 0.85 B x "'
```

output:

```json
[
    {
        "formula": {
            "rawValue": "(Mo 0.96 Zr 0.04 ) 0.85 B x"
        },
        "resolvedFormulas": [
            {
                "rawValue": "(Mo 0.96 Zr 0.04 ) 0.85 B x",
                "formulaComposition": {
                    "Mo": "0.816",
                    "Zr": "0.034",
                    "B": "x"
                }
            }
        ]
    }
]
```

## Installing in your environment

```
docker run -it lfoppiano/grobid-superconductors-tools:2.1
```

## References

If you use our work, and write about it, please cite [our paper](https://hal.inria.fr/hal-03776658):

```bibtex
@article{doi:10.1080/27660400.2022.2153633,
    author = {Luca Foppiano and Pedro Baptista Castro and Pedro Ortiz Suarez and Kensei Terashima and Yoshihiko Takano and Masashi Ishii},
    title = {Automatic extraction of materials and properties from superconductors scientific literature},
    journal = {Science and Technology of Advanced Materials: Methods},
    volume = {3},
    number = {1},
    pages = {2153633},
    year = {2023},
    publisher = {Taylor & Francis},
    doi = {10.1080/27660400.2022.2153633},
    URL = {
    https://doi.org/10.1080/27660400.2022.2153633
    },
    eprint = {
    https://doi.org/10.1080/27660400.2022.2153633
    }
}
```

## Overview of the repository

- [Converters](material_parsers/converters) TSV to/from Grobid XML files conversion
- [Linking](material_parsers/linking) module: A rule based python algorithm to link entities
- [Commons libraries](material_parsers/commons): contains common code shared between the various component. The Grobid client was borrowed from [here](https://github.com/kermitt2/grobid-client-python), the tokenizer from [there](https://github.com/kermitt2/delft).

## Developer's notes

### Set up on Apple M1 

```shell
conda install -c apple tensorflow-deps
```

```shell
pip install -r requirements.macos.txt 
```

```shell
conda install scikit-learn=1.0.1
```
 
We need to remove tensorflow, h5py, scikit-learn from the delft dependencies in setup.py

```shell
pip install -e ../../delft 
```

```shell
pip install -r requirements.txt 
```

Finally, don't forget to install the spacy model

```shell
python -m spacy download en_core_web_sm
```


### Release 

```shall
bump-my-version bump patch|minor|major
```

