# -*- coding: utf-8 -*-
"""
Created on Mon Sep 23 10:29:05 2019

@author: chris.kerklaan
"""

# Documentation https://demo.lizard.net/doc/api.html#post--api-v3-rasters-


# System imports
import sys

# sys.path.append("C:/Users/chris.kerklaan/tools")

# Third-party imports
import json
from requests import get, post, codes, delete

# Local imports
from nens_gs_uploader.localsecret.localsecret import username, password
from atlas2catalogue.klimaatatlas import strip_information
from xml.dom import minidom


class wmslayers(object):
    def __init__(self, username=username, password=password):
        self.username = username
        self.password = password
        self.wmslayer_url = "https://demo.lizard.net/api/v4/wmslayers/"
        self.wmslayer_uuid = "https://demo.lizard.net/api/v4/wmslayers/{uuid}/"
        self.organisation_url = "https://demo.lizard.net/api/v4/organisations/"

        self.get_headers = {
            "username": username,
            "password": password,
            "Content-Type": "application/json",
        }
        self.post_headers = {"username": username, "password": password}

    def get_nens_id(self):
        r = get(
            url=self.organisation_url,
            headers=self.post_headers,
            params={"name__icontains": "nelen"},
        )
        self.organisation_uuid = r.json()["results"][0]["uuid"]
        return self.organisation_uuid

    def get_organisation_id(self, organisation):
        r = get(
            url=self.organisation_url,
            headers=self.post_headers,
            params={"name__icontains": organisation},
        )
        if r.json()["count"] == 0:
            print("zero results for", organisation)
            print("using Nelen & Schuurmans as organisation")
            self.organisation_uuid = self.get_nens_id()

        elif r.json()["count"] > 1:
            print("count search results more than 1", r.json())
            print("using Nelen & Schuurmans as organisation")
            self.organisation_uuid = self.get_nens_id()

        else:
            self.organisation_uuid = r.json()["results"][0]["uuid"]

        return self.organisation_uuid

    def get_layer(self, name):

        r = get(
            url=self.wmslayer_url,
            headers=self.post_headers,
            params={"name__icontains": name},
        )

        results_exists = r.json()["count"] > 0
        slug_exists = False
        slug_result = None

        if results_exists:
            for result in r.json()["results"]:
                layer_name = result["name"]
                if layer_name == name:
                    return result, True

        return slug_result, slug_exists

    def delete(self, uuid):

        r = delete(url=self.wmslayer_uuid.format(uuid=uuid), headers=self.get_headers)
        if r.status_code == 204:
            print("delete store succes", r.status_code)
        else:
            print("delete store failure:", r.json())

    def create(self, configuration, overwrite=False):
        _json, store_exists = self.get_layer(configuration["slug"])

        if not store_exists:
            # configuration["organisation"] = self.organisation_uuid
            r = post(
                url=self.wmslayer_url,
                data=json.dumps(configuration),
                headers=self.get_headers,
            )

            if not r.status_code == 201 or not r.status_code == 201:
                print("create store failure", r.status_code)
                print(r.json())
                return r.json()

            else:
                self.wmslayer_uuid = r.json()["uuid"]
                print("create store succes", r.status_code)
                return r.json()

        else:
            self.wmslayer_uuid = _json["uuid"]
            print(
                "rasterstore already exists, overwrite is false,"
                "thus using existing store"
            )
            return _json["wms_info"]

    def post_data(self, path):
        url = self.wmslayer_url + self.wmslayer_uuid + "/data/"

        r = post(url=url, files={"file": open(path, "rb")}, headers=self.post_headers)

        if not r.status_code == codes.ok:
            print("post data failure", r.status_code)
            print(r.json())

        else:
            print("post data succes", r.status_code)

    def atlas2wms(
        self, atlas_dict, organisation_uuid, dataset, supplier, organisation, product
    ):

        # correct data
        name = atlas_dict["name"][:80]
        slug_org = "_".join([organisation.lower(), product.lower()])
        slug = ":".join([slug_org, atlas_dict["slug"].lower()])[:64]
        description = strip_information(atlas_dict["information"])
        download_url = "{}?&request=GetFeature&typeName={}&OutputFormat=shape-zip".format(
            atlas_dict["url"].replace("wms", "wfs"), atlas_dict["slug"]
        )

        self.configuration = {
            "name": name,
            "description": description,
            "slug": slug,
            "tiled": True,
            "wms_url": atlas_dict["url"],
            "access_modifier": 0,
            "supplier": supplier,
            "options": {"transparent": "true"},
            "shared_with": [],
            "datasets": [dataset],
            "organisation": organisation_uuid,
            "download_url": download_url,
        }


if __name__ == "__main__":

    # test
    # wmslayer = wmslayers()
    # organisation_uuid = wmslayer.get_organisation_id('Hollands noorderkwartier')
    # wms_info, result_exists =  wmslayer.get_layer("test_name")
    # wmslayer.delete(wms_info['uuid'])

    # # Add wms layers
    # configuration =  {
    #             "name": "test_name",
    #             "description": "",
    #             "slug": "test_zeebrugge",
    #             "tiled": True,
    #             "wms_url": "https://geoserver9.lizard.net/geoserver/zeebrugge/wms",
    #             "access_modifier": 0,
    #             "supplier": "chris.kerklaan",
    #             "shared_with": [],
    #             "datasets":["hhnk_klimaatatlas"],
    #             "organisation":organisation_uuid
    #         }

    # r = post(
    #             url="https://hhnk.lizard.net/api/v4/wmslayers/",
    #             data=json.dumps(configuration),
    #             headers=get_headers,
    #         )
    # print(r.json())
    # wmsinfo = wmslayer.create(configuration, overwrite=True)
    pass
