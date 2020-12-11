0. Activate the conda environment 

    > conda activate grobidSuperconductors
1. Enter the directory of the unpacked inception export 

1. Copy the files from the curation directory to a TSV directory where each filename is correctly placed 
 
    > for x in `gfind curation -type f -name '*.tsv'`; do y=${x%/*}; cp ${x}    ../../batch1/$(echo "tsv/$(b=${y##*/}; echo ${b%.*})" | cut -f 1-3 -d '.').tsv ; done;
                                                                                                                                                                                                                         
1. Conversion 
    > python ~/development/projects/grobid/grobid-superconductors/resources/web/converters/xml2tsv/tsv2xml.py --input supercon-batch-6_project_2020-09-10_1056/annotation --recursive 


1. Copy the files from the annotation directory 
    > for x in `gfind annotation -type f -name '*.tsv'`; do y=${x%/*}; mv ${x}    ../../batch2/$(echo "$(b=${x##*/}; echo ${b%.*})/$(b=${y##*/}; echo ${b%.*})" | cut -f 1-3 -d '.').tsv ; done;


for filename in `find supercon-batch-6_project_2020-09-10_1056/annotation -name *.xml`; do cp $filename batch6/$(b=${filename##*/}; echo ${b%%.*})/`awk -F/ '{ print $(NF-1) }' <<< "$filename"`.xml; done;

