# -*- coding: utf-8 -*-
"""
Created on Wed Jul 24 15:39:13 2019

@author: chris.kerklaan - N&S

TODOs:
    1. Code review
    2. Extra checks op shapefiles 
    3. Check slds werken nog niet goed
    4. 3D dimensions 
"""
# system imports
import os
import sys
import logging
from time import sleep
from configparser import RawConfigParser

# Third-party imports
import ogr
import gdal
import argparse
from glob import glob

# Local imports
from nens_gs_uploader.postgis import (
    SERVERS,
    PG_DATABASE,
    copy2pg_database,
    add_metadata_pgdatabase,
)
from nens_gs_uploader.project import (
    logger,
    log_time,
    percentage,
    print_list,
    print_dictionary,
)

from nens_gs_uploader.wrap import wrap_geoserver
from nens_gs_uploader.vector import wrap_shape
from nens_gs_uploader.sld import wrap_sld
from nens_gs_uploader.sld import replace_sld_field_based_on_shape
from nens_gs_uploader.upload_ready import correct

# Globals
DRIVER_OGR_SHP = ogr.GetDriverByName("ESRI Shapefile")
DRIVER_OGR_MEM = ogr.GetDriverByName("Memory")

FILE = os.path.dirname(os.path.abspath(__file__))
SLD_PATH = os.path.join(FILE, "nens_gs_uploader", "sld")


# Exceptions
ogr.UseExceptions()
gdal.UseExceptions()

# GDAL configuration options
gdal.SetConfigOption("CPL_DEBUG", "ON")
gdal.SetConfigOption("CPL_ERROR", "ON")
gdal.SetConfigOption("CPL_CURL_VERBOSE", "ON")

# Logging configuration options
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)


def get_parser():
    """ Return argument parser. """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inifile", metavar="INIFILE", help="Settings voor inifile."
    )
    return parser


def get_subject_from_path(path):
    return os.path.basename(path).split(".")[0]


def get_standard_sld(sld_name):
    return os.path.join(SLD_PATH, sld_name + ".sld")

def get_paths_and_subjects(setting, source):
    
    if source == 'directory':
        in_paths = glob(setting.directory + "/*.shp")
        in_paths = in_paths + glob(setting.directory + "/*.gpkg")

        subjects = [get_subject_from_path(in_path) for in_path in in_paths]
    elif source == 'postgis':
        in_paths = setting.config.sections()[5:]
        subjects = setting.get_postgis_subjects()
    else:
        print('choose source')
        
    return in_paths, subjects


def set_log_config(location, name="log"):
    path = os.path.join(location, name)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=path + ".log",
        level=logging.DEBUG,
    )
    gdal.SetConfigOption("CPL_LOG_ERRORS", path + "_gdal_err.log")
    gdal.SetConfigOption("CPL_LOG", path + "_gdal.log")


class settings_object(object):
    """Reads settings from inifile settings from command line tool"""

    def __init__(self, ini_file=None):
        if ini_file is not None:
            config = RawConfigParser()
            config.read(ini_file)
            self.ini = ini_file
            self.ini_location = os.path.dirname(ini_file)
            self.config = config

            self.set_project()

    def add(self, key, value):
        setattr(self, key, value)

    def get_postgis_subjects(self):
        subjects = []
        for section in self.config.sections()[5:]:
            for i in self.config.items(section):
                if i[0] == "out_layer":
                    subjects.append(i[1])

        return subjects

    def set_project(self):
        self.set_values("project")
        self.set_values("input_directory")
        self.set_values("tool")
        self.set_values("input_styling")
        self.set_values("input_postgis")

    def set_values(self, section):
        for key in self.config[section]:
            value = self.config[section][key]
            if value == "True":
                value = True
            elif value == "False":
                value = False
            else:
                pass

            self.key = value
            setattr(self, key, value)

    def postgis_sld_generator(self):
        for layer in self.config.items("input_postgis"):
            if "style" in layer[0]:
                yield layer[1]


def add_output_settings(setting, onderwerp, in_path):
    """ Returns geoserver settings in an organized manner"""
    """conform https://sites.google.com/nelen-schuurmans.nl/handleiding-klimaatatlas/data-protocol"""

    # layer names, workspace names en server names
    if "PRODUCTIE" in setting.server_naam:
        layer_name = "{}_{}_{}".format(
            setting.bo_nummer, setting.organisatie, onderwerp
        )
        workspace_name = setting.organisatie + "_" + setting.product_naam
        
    elif "PROJECTEN" in setting.server_naam:
        layer_name = "{}_{}_{}_{}".format(
            setting.project_nummer.lower(), setting.organisatie, onderwerp, setting.einddatum
        )
        workspace_name = "p_{}_{}".format(setting.organisatie, setting.product_naam)
        
    else:
        raise ValueError("servernaam fout")

    store_name = setting.project_nummer.lower() + "_" + PG_DATABASE[setting.server_naam]["database"]
        

    # abstracts
    if setting.product_naam == "klimaatatlas" :

        abstract_data = """
        De laag {omschrijving} komt van {bron}. Voor meer informatie over 
        deze laag, ga naar de klimaatatlas www.{bron}.klimaatatlas.net. 
        """.format(
            omschrijving=onderwerp.lower(), bron=setting.organisatie.lower()
        )

    elif setting.product_naam == "dashboard":
        abstract_data = """
        De laag {omschrijving} komt van {bron}. Voor meer informatie over 
        deze laag, ga naar het dashboard. 
        """.format(
            omschrijving=onderwerp.lower(), bron=setting.organisatie.lower()
        )
        
    elif setting.product_naam == "storymap":
        abstract_data = """ Deze laag is afkomsting van de storymap van
        {bron}.
        """.format(
            omschrijving=onderwerp.lower(), bron=setting.organisatie.lower()
        )
    else:
        raise ValueError("productnaam fout")

    # Source inputs
    if setting.use_postgis and not os.path.isfile(in_path):
        
        setting.set_values(in_path)
        setting.in_datasource = {
            "host": setting.host,
            "port": setting.port,
            "database": setting.database,
            "username": setting.username,
            "password": setting.password,
        }
        setting.in_layer = in_path

    elif setting.use_directory and os.path.isfile(in_path):

        setting.in_datasource = in_path
        setting.in_layer = None
        setting.in_sld_path = in_path.replace(os.path.splitext(in_path)[1], ".sld")
        setting.skip = False

    else:
        print("use either use_postgis or use_batch")

    # Overwrite sld path if standard sld is used
    if setting.use_standard_sld:
        styles = [
            "begaanbaarheid_wegen",
            "kwetsbaarheid_panden",
            "kwetsbare_objecten",
            "regenwaterstructuur"
        ]
        list_style = [style for style in styles if style in onderwerp]
        setting.in_sld_path = get_standard_sld(list_style[0])

    # Set metadata
    metadata = {
        "pg_layer": layer_name,
        "gs_workspace": workspace_name,
        "gs_store": store_name,
        "gs_layer": layer_name,
        "uploader": setting.eigen_naam.lower(),
        "projectnummer": setting.project_nummer.lower(),
        "einddatum": setting.einddatum,
    }

    # Overwrite all
    if setting.overwrite_all:
        setting.overwrite_postgres = True
        setting.overwrite_abstract = True
        setting.overwrite_feature = True
        setting.overwrite_sld = True

    # Outputs
    setting.workspace_name = workspace_name
    setting.store_name = store_name
    setting.layer_name = layer_name
    setting.abstract_data = abstract_data
    setting.metadata = metadata
    setting.subject = onderwerp

    return setting


def batch_upload(inifile):
    """ Returns batch upload shapes for one geoserver """
    setting = settings_object(inifile)

    # set logging
    set_log_config(setting.ini_location)
    sys.stdout = logger(setting.ini_location)

    # get vectors 
    if setting.use_directory:
        in_paths, subjects = get_paths_and_subjects(setting, 'directory')

    elif setting.use_postgis:
        in_paths, subjects = get_paths_and_subjects(setting, 'postgis')
        
              
    elif setting.use_directory and setting.use_postgis:
        in_paths, subjects = get_paths_and_subjects(setting, 'directory')
        pg_in_paths, pg_subjects = get_paths_and_subjects(setting, 'postgis')

        in_paths = in_paths + pg_in_paths
        subjects = subjects + pg_subjects
        
        
    else:
        print("use either use_postgis or use_batch")

    print_list(in_paths, "Paths")
    print_dictionary(setting.__dict__, "Settings")

    failures = {}
    succes = {}
    for count, (in_path, subject) in enumerate(zip(in_paths, subjects)):
        log_time("info", percentage(count, len(in_paths)), subject, "l")

        # set last settings
        setting.server = wrap_geoserver(setting.server_naam)
        setting = add_output_settings(setting, subject, in_path)
        
        if not setting.skip:

#            try:
                succes[setting.subject] = upload(setting)

#            except Exception as e:
#                print(e)
#                failures[setting.subject] = e

        
        if not setting.skip:
            log_time("info", "sleeping to decrease load on server....")
            sleep(30)

    print_dictionary(succes, "Succes")
    print_dictionary(failures, "Failures")

def upload(setting):
    log_time("info", setting.layer_name, "0. starting.....")
    shape = wrap_shape(setting.in_datasource, setting.in_layer)

    log_time("info", setting.layer_name, "1. vector corrections")
    datasource, layer_name = correct(shape.layer, setting.layer_name)
    shape = wrap_shape(datasource)
    setting.layer_name = layer_name

    if shape.layer.GetFeatureCount() == 0:
        log_time("error", setting.layer_name, "vector feature count is 0")

    log_time("info", setting.layer_name, "2. Upload shape to pg database.")
    pg_details = PG_DATABASE[setting.server_naam]
    pg_database = wrap_shape(pg_details)

    # set metadata
    add_metadata_pgdatabase(setting, pg_database)

    pg_layer_present = setting.layer_name in pg_database.layers
    if not pg_layer_present or setting.overwrite_postgres:
        copy2pg_database(pg_database, shape.layer, setting.layer_name)

    else:
        log_time("info", setting.layer_name, "Layer already in database.")

    log_time("info", setting.server_naam, "Loading...")
    server = setting.server

    log_time("info", setting.layer_name, "3. Create workspace.")
    server.create_workspace(setting.workspace_name)

    log_time("info", setting.layer_name, "4. Create store.")
    server.create_postgis_datastore(
        setting.store_name, setting.workspace_name, pg_details
    )

    log_time("info", setting.layer_name, "5. Publish featuretype.")
    server.publish_layer(setting.layer_name, setting.overwrite_feature)

    log_time("info", setting.layer_name, "6. Load Style Layer Descriptor.")
    sld = wrap_sld(setting.in_sld_path, _type="path")

    log_time("info", setting.layer_name, "7. Possibly check sld.")
    pg_database.get_layer(setting.layer_name)

    # lower all field names if necessary
    pg_database.lower_all_field_names
    sld.lower_all_property_names()

    if setting.check_sld:
        if sld._type() == "category":
            for sld_field_name in sld.get_all_property_names():
                if not sld_field_name in pg_database.get_all_field_names():
                    replace_sld_field_based_on_shape(
                        pg_database, sld, sld_field_name
                    )

    log_time("info", setting.layer_name, "8. Upload sld.")
    style_name = setting.layer_name + "_style"
    server.upload_sld(
        style_name,
        setting.workspace_name,
        sld.get_xml(),
        setting.overwrite_sld,
    )

    log_time("info", "9. Connect sld to layer.")
    server.set_sld_for_layer()

    log_time("info", setting.layer_name, "10. Add to abstract.")
    if setting.overwrite_abstract:
        server.write_abstract(setting.abstract_data)

    log_time("info", setting.layer_name, "11. Returning wms, slug")
    wms = SERVERS[setting.server_naam].replace("rest", "{}/wms".format(setting.workspace_name))
    slug = "{}:{}".format(setting.workspace_name, setting.layer_name)

    return wms, slug


if __name__ == "__main__":
    batch_upload(**vars(get_parser().parse_args()))
