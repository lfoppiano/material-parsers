[![Python CI](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml/badge.svg)](https://github.com/lfoppiano/grobid-superconductors-tools/actions/workflows/python-app.yml)

# Grobid-superconductors (Python) Tools

This project contains tools developed in Python that are used in the [grobid-superconductors](https://github.com/lfoppiano/grobid-superconductors).

The main part is composed by a lightweight service that allow to process materials names, link entities, and extract structure type from text.

Normally this service is available as a docker image. 

## For developers

> python -m spacy download en_core_web_sm

## Additional scripts and libraries:

 - [Converters](./converters) TSV to/from Grobid XML files conversion
 
 - [Commons libraries](./commons): contains common code shared between the various component. The Grobid client was borrowed from [here](https://github.com/kermitt2/grobid-client-python), the tokenizer from [there](https://github.com/kermitt2/delft).
