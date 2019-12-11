# -*- coding: utf-8 -*-
"""#
Created on Tue Aug 13 08:14:18 2019

@author: chris.kerklaan - N&S
"""

# system imports

# Third-party imports
import ogr
import osr
from tqdm import tqdm

# Local imports
from nens_gs_uploader.project import log_time

# Globals
DRIVER_OGR_MEM = ogr.GetDriverByName("Memory")
MEM_NUM = 0

# Exceptions
ogr.UseExceptions()

def create_mem_ds():
    global MEM_NUM
    mem_datasource = DRIVER_OGR_MEM.CreateDataSource("mem{}".format(MEM_NUM))
    MEM_NUM = MEM_NUM + 1
    return mem_datasource

def geom_transform(in_spatial_ref, out_epsg):
    out_spatial_ref = osr.SpatialReference()
    out_spatial_ref.ImportFromEPSG(out_epsg)
    coordTrans = osr.CoordinateTransformation(in_spatial_ref, out_spatial_ref)
    return coordTrans


def multipoly2poly(in_layer, out_layer):

    layer_defn = in_layer.GetLayerDefn()
    field_names = []
    for n in range(layer_defn.GetFieldCount()):
        field_names.append(layer_defn.GetFieldDefn(n).name)

    for count, in_feat in enumerate(in_layer):
        content = {}
        for field_name in field_names:
            content[field_name] = in_feat.GetField(field_name)

        geom = in_feat.GetGeometryRef()
        if geom == None:
            log_time("warning", "FID {} has no geometry.".format(count))
            continue
        if (geom.GetGeometryName() == "MULTIPOLYGON" or 
            geom.GetGeometryName() == "MULTILINESTRING"):
            for geom_part in geom:               
                addPolygon(geom_part.ExportToWkb(), content, out_layer)
        else:
            addPolygon(geom.ExportToWkb(), content, out_layer)


def addPolygon(simple_polygon, content, out_lyr):
    featureDefn = out_lyr.GetLayerDefn()

    polygon = ogr.CreateGeometryFromWkb(simple_polygon)
    out_feat = ogr.Feature(featureDefn)
    out_feat.SetGeometry(polygon)

    for key, value in content.items():
        try:
            out_feat.SetField(key, value)
        except Exception as e:
            print(e)
            
    out_lyr.CreateFeature(out_feat)


def correct(in_layer, layer_name, epsg=3857):
    try:
        # lower layer_name
        layer_name = layer_name.lower()

        # Get inspatial reference and geometry from in shape
        geom_type = in_layer.GetGeomType()
        in_spatial_ref = in_layer.GetSpatialRef()
        in_layer.ResetReading()

        log_time("info", "check 1 - Name length")
        if len(layer_name) + 10 > 64:
            log_time("error", "laagnaam te lang, 50 characters max.")
            log_time("info", "formatting naar 50.")
            layer_name = layer_name[:50]
            
        mem_datasource = create_mem_ds()

        
        mem_layer = mem_datasource.CreateLayer(
            layer_name, in_spatial_ref, geom_type
        )

        layer_defn = in_layer.GetLayerDefn()
        for i in range(layer_defn.GetFieldCount()):
            field_defn = layer_defn.GetFieldDefn(i)
            mem_layer.CreateField(field_defn)

        log_time("info", "check 2 - Multipart to singlepart")
        multipoly2poly(in_layer, mem_layer)

        if mem_layer.GetFeatureCount() == 0:
            log_time("error", "Multipart to singlepart failed")
            raise ValueError("Multipart to singlepart failed")

        spatial_ref_3857 = osr.SpatialReference()
        spatial_ref_3857.ImportFromEPSG(int(epsg))
        reproject = osr.CoordinateTransformation(
            in_spatial_ref, spatial_ref_3857
        )
        flatten = False
        geom_name = ogr.GeometryTypeToName(geom_type)
        if (geom_name  == '3D Multi Polygon' or 
            geom_name == '3D Line String'):
            log_time("warning", "geom type: " + geom_name)
            log_time("info", "Flattening to 2D")
            flatten = True
            
        elif geom_type < 0:
            log_time("error", "geometry invalid, most likely has a z-type")
            raise ValueError(
                "geometry invalid, most likely has a z-type",
                "geom type: ",
                geom_name,
            )
            
        
        # Create output dataset and force dataset to multiparts
        if geom_type == 3 or geom_type == 6:
            geom_type = 3  # polygon

        elif geom_type == 2 or geom_type == 5:
            geom_type = 2  # linestring

        elif geom_type == 1 or geom_type == 4:
            geom_type = 1  # point

        out_datasource = create_mem_ds()
        out_layer = out_datasource.CreateLayer(
            layer_name, spatial_ref_3857, geom_type
        )
        layer_defn = in_layer.GetLayerDefn()
        

        # Copy fields from memory layer to output dataset
        for i in range(layer_defn.GetFieldCount()):
            out_layer.CreateField(layer_defn.GetFieldDefn(i))

        log_time("info", "check 3 - Reproject layer to {}".format(str(epsg)))
        for out_feat in tqdm(mem_layer):
            out_geom = out_feat.GetGeometryRef()
            

            # validity check
            if not out_geom.IsValid():
                # remove self intersection
                out_geom = out_geom.Buffer(0)
                if not out_geom.IsValid():
                    log_time("warning", "geometry invalid even with buffer, skipping")
                    continue

            # Force and transform geometry
            out_geom = ogr.ForceTo(out_geom, geom_type)
            out_geom.Transform(reproject)

            # flattening to 2d
            if flatten:
                out_geom.FlattenTo2D()

            # Set geometry and create feature
            out_feat.SetGeometry(out_geom)
            out_layer.CreateFeature(out_feat)

        log_time("info", "check 4 - delete ogc_fid if exists")
        out_layer_defn = out_layer.GetLayerDefn()
        for n in range(out_layer_defn.GetFieldCount()):
            field = out_layer_defn.GetFieldDefn(n)
            if field.name == "ogc_fid":
                out_layer.DeleteField(n)
                break

    except Exception as e:
        print(e)

    finally:
        mem_layer = None
        mem_datasource = None
        out_layer = None

    return out_datasource, layer_name


if __name__ == "__main__":
    in_datasource = ogr.Open(
        "C:/Users/chris.kerklaan/Documents\Projecten/HHNK_klimaatatlas/temp/nwm_mediaan_peilgebied_ghg_2050.gpkg"
    )
    in_layer = in_datasource[0]
    layer_name = "beweegbare_bruggen"
    out_datasource, out_layer = correct(in_layer, layer_name)
    out_layer.GetFeatureCount()
