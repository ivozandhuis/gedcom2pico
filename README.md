# GEDCOM to PICO transformer

First approach to transform a GEDCOM 5.5 file into [PiCo](https://personsincontext.org/), using [Mark Wings fork of python-gedcom](https://github.com/Mark-Wing/python-gedcom)

All records are transformed pico:PersonReconstruction-s with implicit pico:PersonObservations (as 'blank nodes'), related to a source.

Specific usage of GEDCOM:
- For every NOTE linked to a SOUR starting with the string "url: " followed by a webaddress, these webaddresses are added as schema:url-s to the source. See for example line 454 of the GEDCOM example, and the resulting S0042.ttl file. Notice to create a separate NOTE per webaddress.

I used [GRAMPS](https://gramps-project.org/) to generate the GEDCOM file.

