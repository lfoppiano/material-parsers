[![Python CI](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml/badge.svg)](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml)


# Grobid-superconductors material name tools

Syster project of [grobid-superconductors](https://github.com/lfoppiano/grobid-superconductors) containing a webservice that interfaces with the python libraries (e.g. Spacy). 

The service provides the following functionalities: 
 - Material name convertion to formula (e.g. Oxigen -> O, Hydrogen -> H): `/convert/name/formula`
 - Material name formula decomposition (e.g. La x Fe 1-x O7-> {La: x, Fe: 1-x, O: 7}):  `/convert/formula/composition`
 - Material class (in superconductors domain) calculation using a rule-base table (e.g. "La Cu Fe" -> Cuprates): `/classify/formula`
 - Tc classification (Tc, not-Tc): `/classify/tc`
 - Relation extraction given a sentence and two entities: `/process/link`

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
