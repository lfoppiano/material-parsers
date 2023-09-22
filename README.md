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
		year  = {2023},
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

 - [Converters](grobid_superconductors/converters) TSV to/from Grobid XML files conversion
 
 - [Linking](./linking) module: A rule based python algorithm to link entities 
 
 - [Commons libraries](./commons): contains common code shared between the various component. The Grobid client was borrowed from [here](https://github.com/kermitt2/grobid-client-python), the tokenizer from [there](https://github.com/kermitt2/delft).
 
 - [Extraction process](/.process): a set of scripts for extracting and linking data from collections of PDFs. 
