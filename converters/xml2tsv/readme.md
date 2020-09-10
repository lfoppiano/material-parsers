
conda activate grobidSuperconductors

python ~/development/projects/grobid/grobid-superconductors/resources/web/converters/xml2tsv/tsv2xml.py --input supercon-batch-6_project_2020-09-10_1056/annotation --recursive 

for filename in `find supercon-batch-6_project_2020-09-10_1056/annotation -name *.xml`; do cp $filename batch6/$(b=${filename##*/}; echo ${b%%.*})/`awk -F/ '{ print $(NF-1) }' <<< "$filename"`.xml; done;

