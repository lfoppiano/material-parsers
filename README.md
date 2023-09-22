[![Python CI](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml/badge.svg)](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml)


# Grobid-superconductors material name tools

## Usage

### Convert material name to formula

```
curl --location 'https://lfoppiano-grobid-superconductors-tools.hf.space/convert/name/formula' \
--form 'input="Hydrogen"'
```

output: 

```
{"composition": {"H": "1"}, "name": "Hydrogen", "formula": "H"}
```

### Decompose formula 

Example: 
```
curl --location 'https://lfoppiano-grobid-superconductors-tools.hf.space/convert/formula/composition' \

--form 'input="CaBr2-x"'
```

output:  

```
{"composition": {"Ca": "1", "Br": "2-x"}}
```

## Overview of the repository

 - [Converters](./converters) TSV to/from Grobid XML files conversion
 
 - [Linking](./linking) module: A rule based python algorithm to link entities 
 
 - [Commons libraries](./commons): contains common code shared between the various component. The Grobid client was borrowed from [here](https://github.com/kermitt2/grobid-client-python), the tokenizer from [there](https://github.com/kermitt2/delft).
 
 - [Extraction process](/.process): a set of scripts for extracting and linking data from collections of PDFs. 
