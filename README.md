# docstruct

    Document structure detection from PAGE to METS

Provides an [OCR-D processor](https://ocr-d.de/en/spec/cli)
which will parse the input page-level structure (as detected by
some [OCR-D](https://ocr-d.de/en/about) workflow including preprocessing,
layout analysis and OCR) of a document annotated via [PAGE-XML](https://ocr-d.de/en/spec/page)
and [METS-XML](https://ocr-d.de/en/spec/mets), further analyse it
(...) and wrap it into a document-level structure in the METS using
logical `mets:structMap` and either …
- `mets:structLink` ([DFG profile](http://dfg-viewer.de/fileadmin/groups/dfgviewer/METS-Anwendungsprofil_2.3.1.pdf)), or
- `mets:area` ([ENMAP profile](http://www.europeana-newspapers.eu/wp-content/uploads/2015/05/D5.3_Final_release_ENMAP_1.0.pdf))

… for representation.
