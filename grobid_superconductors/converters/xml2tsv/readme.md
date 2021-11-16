# Getting started 
0. Activate the conda environment 

    > conda activate grobidSuperconductors
1. Enter the directory of the unpacked inception export 

## Curated data 
1. Copy the files from the curation directory to a TSV directory where each filename is correctly placed 
 
    > for x in `gfind curation -type f -name '*.tsv'`; do y=${x%/*}; cp ${x}    ../../batch1/$(echo "tsv/$(b=${y##*/}; echo ${b%.*})" | cut -f 1-3 -d '.').tsv ; done;
                                                                                                                                                                                                                         
1. Conversion 
    > python ~/development/projects/grobid/grobid-superconductors/resources/web/converters/xml2tsv/tsv2xml.py --input supercon-batch-6_project_2020-09-10_1056/annotation --recursive 

## Annotated data 

1. Copy the files from the annotation directory 
    > for x in `gfind annotation -type f -name '*.tsv'`; do y=${x%/*}; mkdir ../../batch7/tsv/$(b=${x##*/}; echo ${b%.*}); cp ${x} ../../batch7/tsv/$(echo "$(b=${x##*/}; echo ${b%.*})/$(b=${y##*/}; echo ${b%.*})" | cut -f 1-3 -d '.').tsv ; done;

1. Conversion
   > python ~/development/projects/grobid/grobid-superconductors/resources/web/converters/xml2tsv/tsv2xml.py --input ../../batch7/tsv --output ../../batch7/xml --recursive
   
1. Not sure 
    > for filename in `find supercon-batch-6_project_2020-09-10_1056/annotation -name *.xml`; do cp $filename batch6/$(b=${filename##*/}; echo ${b%%.*})/`awk -F/ '{ print $(NF-1) }' <<< "$filename"`.xml; done;

