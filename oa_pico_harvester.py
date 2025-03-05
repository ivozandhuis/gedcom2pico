#!/usr/bin/python3

# requirements:
# pip install git+https://github.com/Mark-Wing/python-gedcom.git

import os
import requests

from gedcom.parser import Parser
from gedcom.element.source import SourceElement

from rdflib import Graph, Namespace, URIRef, RDF, SDO, OWL


# Initialize file handling
name = 'export'
file_path = 'examples/' + name + '.ged'
dir = 'examples/' + name + '/'
try: os.makedirs(dir)
except: pass

# Initialize rdflib variables
baseUri = 'https://gen.example.com/' + name + '/'

# Initialize the parser
gedcom_parser = Parser()
gedcom_parser.parse_file(file_path)
root_child_elements = gedcom_parser.get_root_child_elements()

# Create dict of NOTE elements
note_dict = {}
for element in root_child_elements:
    tag = element.get_tag()
    if tag == 'NOTE':
        value = element.get_value()
        conc_elements = element.get_child_elements()
        for conc in conc_elements:
            value = value + conc.get_value()
        pointer = element.get_pointer()[1:-1]
        note_dict[pointer] = value

#Create dictionary mapping source identifier to openarchieven.nl url.
sour_url_dict = {}
for element in root_child_elements:
    # Handle SOUR
    if isinstance(element, SourceElement):
        sour_pointer = element.get_pointer()[1:-1]
        child_elements = element.get_child_elements()
        for child_element in child_elements:
            tag = child_element.get_tag()
            if tag == "NOTE":
                note_pointer = child_element.get_value()[1:-1]
                note = note_dict[note_pointer] 
                if note.startswith("url: https://www.openarchieven.nl/"):
                    sour_url_dict[sour_pointer] = note[len("url: "):]


# resolving and relating source
oa_source_uri = None
amount = 0

for sour, url in sour_url_dict.items():

    request_url = url.strip() + "/ttl:pico"
    print(request_url)
    try:
        response = requests.get(request_url)
        turtle = response.text
    except:
        break

    g = Graph()
    g.parse(data = turtle, format = "turtle")

    my_sour_uri = URIRef(baseUri + sour)

    for s, p, o in g.triples((oa_source_uri, RDF.type, SDO.ArchiveComponent)):
        g.add((my_sour_uri, OWL.sameAs, s))
    
    g_file = dir + s[len("https://www.openarchieven.nl/id/record_"):] + ".ttl"

    # Serialize and save the graph to the file
    if len(g) > 0:
        g.serialize(destination = g_file, format = 'turtle')

    amount = amount - 1
    if amount == 0: break
