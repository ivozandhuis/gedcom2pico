#!/usr/bin/python3

# requirements:
# pip install git+https://github.com/Mark-Wing/python-gedcom.git

import gedcom.tags
import os

from gedcom.element.individual import IndividualElement
from gedcom.element.source import SourceElement
from gedcom.element.family import FamilyElement
from gedcom.parser import Parser

from rdflib import Graph, URIRef, Literal, BNode, Namespace, RDF, PROV, SDO, XSD


def date_converter(gedcom_date: str):
    month_dict = {"JAN":"01","FEB":"02","MAR":"03","APR":"04","MAY":"05","JUN":"06",
                    "JUL":"07","AUG":"08","SEP":"09","OCT":"10","NOV":"11","DEC":"12"}
    date = gedcom_date.split(' ')
    date.reverse()
    ISOdate = ""
    if len(date) == 3:
        year = date[0]
        month = date[1]
        day = date[2]
        if month in month_dict.keys():
            ISOmonth = month_dict[month]
        if len(day) == 1:
            ISOday = "0" + day
        else:
            ISOday = day 
        ISOdate = year + "-" + ISOmonth + "-" + ISOday
    elif len(date) == 1:
        year = date[0]
        ISOdate = year

    return ISOdate


# Initialize file handling
name = 'proef'
file_path = 'examples/' + name + '.ged'
dir = 'examples/' + name + '/'
try: os.makedirs(dir)
except: pass

# Initialize rdflib variables
baseUri = 'https://gen.example.com/' + name + '/'
PICO = Namespace('https://personsincontext.org/model#')
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
    g.bind("sdo", SDO)
    g.bind("prov", PROV)
    g.bind("bio", BIO)

    # Create URI for the resource and filename to export to
    subject = URIRef(baseUri + pointer)
    g_file = dir + pointer + ".ttl"

    # Handle INDI
    if isinstance(element, IndividualElement):
        # rdf:type
        g.add((subject, RDF.type, PICO.PersonReconstruction))

        # sdo:name
        (first, last) = element.get_name()
        g.add((subject, SDO.name, Literal(first + " " + last)))

        # sdo:birthDate
        birth_date = element.get_birth_date()
        if birth_date != "":
            ISOdate = date_converter(birth_date)
            if len(ISOdate) == 10:
                datatype = XSD.date
                g.add((subject, SDO.birthDate, Literal(ISOdate, datatype = datatype)))
            elif len(ISOdate) == 4:
                datatype = XSD.gYear
                g.add((subject, SDO.birthDate, Literal(ISOdate, datatype = datatype)))

        # sdo:birthPlace
        birth_place = element.get_birth_place()
        if birth_place != "":
            g.add((subject, SDO.birthPlace, Literal(birth_place)))

        # sdo:deathDate
        death_date = element.get_death_date()
        if death_date != "":
            ISOdate = date_converter(death_date)
            if len(ISOdate) == 10:
                datatype = XSD.date
            elif len(ISOdate) == 4:
                datatype = XSD.gYear
            g.add((subject, SDO.deathDate, Literal(ISOdate, datatype = datatype)))

        # sdo:deathPlace
        death_place = element.get_death_place()
        if death_place != "":
            g.add((subject, SDO.deathPlace, Literal(death_place)))

        # prov:wasDerivedFrom
        list = element.get_sources_by_tag_and_values(tag = gedcom.tags.GEDCOM_TAG_BIRTH)
        list = list + element.get_sources_by_tag_and_values(tag = gedcom.tags.GEDCOM_TAG_DEATH)
        list = list + element.get_sources_by_tag_and_values(tag = gedcom.tags.GEDCOM_TAG_BURIAL)

        child_elements = element.get_child_elements()
        for child_element in child_elements:
            tag = child_element.get_tag()
            if tag == 'SOUR': list.append(child_element)

        for item in list:
            # Relate Blanknode for PICO.PersonObservation to subject
            blank_node = BNode()
            g.add((subject, PROV.wasDerivedFrom, blank_node))
            # Add triples to the blank node
            g.add((blank_node, RDF.type, PICO.PersonObservation))
            src = item.get_value()[1:-1]
            g.add((blank_node, PROV.hadPrimarySource, URIRef(baseUri + src)))

        # sdo:spouse
        for spouse in gedcom_parser.get_spouses(element):
            pointer = spouse.get_pointer()[1:-1]
            g.add((subject, SDO.spouse, URIRef(baseUri + pointer)))

        # sdo:children
        for child in gedcom_parser.get_children(element):
            pointer = child.get_pointer()[1:-1]
            g.add((subject, SDO.children, URIRef(baseUri + pointer)))

        # sdo:gender
        gender = element.get_gender()
        if gender == 'F':
            g.add((subject, SDO.gender, SDO.Female))
        elif gender == 'M':
            g.add((subject, SDO.gender, SDO.Male))
            

    # Handle SOUR
    elif isinstance(element, SourceElement):
        # rdf:type
        g.add((subject, RDF.type, SDO.ArchiveComponent))

        # sdo:name
        title = element.get_title()
        g.add((subject, SDO.name, Literal(title)))

        # sdo:url
        child_elements = element.get_child_elements()
        for child_element in child_elements:
            tag = child_element.get_tag()
            if tag == "NOTE":
                url = url_dict[child_element.get_value()[1:-1]]
                g.add((subject, SDO.url, Literal(url)))

    # Handle FAM
    elif isinstance(element, FamilyElement):
        # rdf:type
        g.add((subject, RDF.type, BIO.Marriage))

    else:
        pass

    # Serialize and save the graph to the file
    if len(g) > 0:
        g.serialize(destination = g_file, format = 'turtle')
