#!/usr/bin/python3

# requirements:
# pip install git+https://github.com/Mark-Wing/python-gedcom.git

import gedcom.tags
import os

from gedcom.element.individual import IndividualElement
from gedcom.element.source import SourceElement
from gedcom.element.family import FamilyElement
from gedcom.parser import Parser

from rdflib import Graph, URIRef, Literal, BNode, Namespace, RDF, PROV

# Initialize file handling
name = 'proef'
file_path = 'examples/' + name + '.ged'
dir = 'examples/' + name + '/'
try: os.makedirs(dir)
except: pass

# Initialize rdflib variables
baseUri = 'https://gen.example.com/' + name + '/'
PICO = Namespace('https://personsincontext.org/model/')
SCHEMA = Namespace('http://schema.org/')
BIO = Namespace('http://purl.org/vocab/bio/0.1/')

# Initialize the parser
gedcom_parser = Parser()
gedcom_parser.parse_file(file_path)
root_child_elements = gedcom_parser.get_root_child_elements()

# Create dict of NOTE elements with urls
url_dict = {}
for element in root_child_elements:
    tag = element.get_tag()
    if tag == 'NOTE':
        value = element.get_value()
        conc_elements = element.get_child_elements()
        for conc in conc_elements:
            value = value + conc.get_value()
        pointer = element.get_pointer()[1:-1]
        if value.startswith('url:'):
            value = value[len("url: "):]
            url_dict[pointer] = value

# Iterate through all root child elements
for element in root_child_elements:
    # Get identifier for element, unique within the GEDCOM file
    pointer = element.get_pointer()[1:-1]

    # Create a Graph
    g = Graph()
    g.bind("pico", PICO)
    g.bind("schema", SCHEMA)
    g.bind("prov", PROV)
    g.bind("bio", BIO)

    # Create URI for the resource and filename to export to
    subject = URIRef(baseUri + pointer)
    g_file = dir + pointer + ".ttl"

    # Handle INDI
    if isinstance(element, IndividualElement):
        # rdf:type
        g.add((subject, RDF.type, PICO.PersonReconstruction))

        # schema:name
        (first, last) = element.get_name()
        g.add((subject, SCHEMA.name, Literal(first + " " + last)))

        # prov:wasDerivedFrom
        list = element.get_sources_by_tag_and_values(tag = gedcom.tags.GEDCOM_TAG_BIRTH)
        list = list + element.get_sources_by_tag_and_values(tag = gedcom.tags.GEDCOM_TAG_DEATH)

        for item in list:
            # Relate Blanknode for PICO.PersonObservation to subject
            blank_node = BNode()
            g.add((subject, PROV.wasDerivedFrom, blank_node))
            
            # Add triples to the blank node
            g.add((blank_node, RDF.type, PICO.PersonObservation))
            src = item.get_value()[1:-1]
            g.add((blank_node, PROV.hadPrimarySource, URIRef(baseUri + src)))

        # schema:spouse
        for spouse in gedcom_parser.get_spouses(element):
            pointer = spouse.get_pointer()[1:-1]
            g.add((subject, SCHEMA.spouse, URIRef(baseUri + pointer)))

        #schema:children
        for child in gedcom_parser.get_children(element):
            pointer = child.get_pointer()[1:-1]
            g.add((subject, SCHEMA.children, URIRef(baseUri + pointer)))

        # schema:gender
        gender = element.get_gender()
        if gender == 'F':
            g.add((subject, SCHEMA.gender, SCHEMA.Female))
        elif gender == 'M':
            g.add((subject, SCHEMA.gender, SCHEMA.Male))
            

    # Handle SOUR
    elif isinstance(element, SourceElement):
        # rdf:type
        g.add((subject, RDF.type, SCHEMA.ArchiveComponent))

        # schema:name
        title = element.get_title()
        g.add((subject, SCHEMA.name, Literal(title)))

        # schema:url
        child_elements = element.get_child_elements()
        for child_element in child_elements:
            tag = child_element.get_tag()
            if tag == "NOTE":
                url = url_dict[child_element.get_value()[1:-1]]
                g.add((subject, SCHEMA.url, Literal(url)))

    # Handle FAM
    elif isinstance(element, FamilyElement):
        # rdf:type
        g.add((subject, RDF.type, BIO.Marriage))

    else:
        pass

    # Serialize and save the graph to the file
    if len(g) > 0:
        g.serialize(destination = g_file, format = 'turtle')
