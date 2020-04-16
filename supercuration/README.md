# Supercuration
Supercuration (Superconductors Curation) is an interface based on [Grobid Superconductor](https://github.com/lfoppiano/grobid-superconductors) 
which allows extraction and visualisation of material and properties from Superconductors-related papers. 

Grobid-superconductors provides a basic interface that allows extraction of entities such as `material`, `superconducting critical temperature`, etc.. 
This interface adds apply a simple linking algorithm to the extracted entities. 

The interface provides a visualisation of the extracted tabular information (material - tc), and the ability to:
  - scroll automatically to the relative part of the document
  - correct the extracted information in the interface     
 
![Screenshot 1](docs/images/grobid-superconductors-web-home.png "Screenshot 1")

By clicking on each annotation in the text, is possible to see the details (for the moment just the supscript/superscript formatting and the Critical temperature):  

![Screenshot 2](docs/images/grobid-superconductors-web-home-2.png "Screenshot 2")
