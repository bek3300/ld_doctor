from importlib.resources import path
from django.shortcuts import render
from geo.Geoserver import Geoserver
import glob
import fiona
import rasterio
import rasterio.mask
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
import numpy as np
import geopandas as gpd
import gemgis as gg
from django.views.decorators.csrf import csrf_exempt
import os
from django.core import serializers
from .models import ShapeFile
import geopandas as gpd 
import shapely
context = {}
geo = Geoserver('http://localhost:8088/geoserver', username='admin', password='geoserver')
modelDataType = {
'carbon': np.int32,
'erosion' : np.int8,
'productivity' :np.int32,
'moisture' :np.int32
}

maskedPath = {
    'carbon':r'/home/ghost/Desktop/ld_layers/carbon/output/carbon_mask.tif',
'erosion' : r'/home/ghost/Desktop/ld_layers/erosion/output/erosion_mask.tif',
'productivity' : r'/home/ghost/Desktop/ld_layers/productivity/output/productivity_mask.tif',
'moisture' :r'/home/ghost/Desktop/ld_layers/moisture/output/moisture_mask.tif'
    
}
sldPath={
'carbon': r'/home/ghost/Desktop/ld_layers/sld/carbon.sld',
'erosion' : r'/home/ghost/Desktop/ld_layers/sld/erosion.sld',
'productivity' :r'/home/ghost/Desktop/ld_layers/sld/productivity.sld',
'moisture' :r'/home/ghost/Desktop/ld_layers/sld/moisture.sld'
}
outputPathswithoutr = {
'carbon': '/home/ghost/Desktop/ld_layers/carbon/output/carbon_clipped.tif',
'erosion' : '/home/ghost/Desktop/ld_layers/erosion/output/erosion_clipped.tif',
'productivity' :'/home/ghost/Desktop/ld_layers/productivity/output/productivity_clipped.tif',
'moisture' :'/home/ghost/Desktop/ld_layers/moisture/output/moisture_clipped.tif' 
}
inputPaths={
'carbon': r'/home/ghost/Desktop/ld_layers/carbon/soil_carbon.tif',
'erosion' : r'/home/ghost/Desktop/ld_layers/erosion/soil_erosion.tif',
'productivity' :r'/home/ghost/Desktop/ld_layers/productivity/soil_productivity.tif',
'moisture' :r'/home/ghost/Desktop/ld_layers/moisture/soil_moisture.tif'
}
outputPaths = {
'carbon': r'/home/ghost/Desktop/ld_layers/carbon/output/carbon.tif',
'erosion' : r'/home/ghost/Desktop/ld_layers/erosion/output/erosion.tif',
'productivity' :r'/home/ghost/Desktop/ld_layers/productivity/output/productivity.tif',
'moisture' :r'/home/ghost/Desktop/ld_layers/moisture/output/moisture.tif' 
}
uplod_files="/home/ghost/Documents/django/DjangoGEE (2)/DjangoGEE/media/uploads/"
ld_layers = "/home/ghost/Desktop/ld_layers/"

def getEachPixelValue(array):
    eachPixel = []
    for pixels in array:
                for pixel in pixels:
                    for p in pixel:
                        eachPixel.append(p)
    return eachPixel


def getMasked(model):
    for key, value in maskedPath.items():
        if(key==model):
            return value
    

def selectModelPath(model):
    for key, value in inputPaths.items():
        if(key==model):
            return value

def selectedStylePath(model):
    for key, value in sldPath.items():
        if(key==model):
            return value


def getOutputPath(model):
    for key, value in inputPaths.items():
        if(key==model):
            return value


def getOutputPathr(model):
    for key, value in outputPathswithoutr.items():
        if(key==model):
            return value


def getDataType(model):
    for key, value in modelDataType.items():
        if(key==model):
            return value


def geoServerPublisher(model,clipType):
    if clipType=='clipped':
        raster_path = glob.glob(getOutputPathr(model))
    if clipType=='masked':
         raster_path = glob.glob(getMasked(model))
    for i in range(len(raster_path)):
        path=raster_path[i]
        geo.create_coveragestore(path=path, workspace=clipType)
        if clipType=='clipped':
          geo.delete_style(style_name=model, workspace=clipType)
          geo.upload_style(path=selectedStylePath(model), workspace=clipType)
          geo.publish_style(layer_name=str(model+'_clipped'), style_name=model, workspace=clipType)
        if clipType=='masked':
          geo.delete_style(style_name=model, workspace=clipType)
          geo.upload_style(path=selectedStylePath(model), workspace=clipType)
          geo.publish_style(layer_name=str(model+'_mask'), style_name=model, workspace=clipType)
        # return True
# def publishStyle(model,clipType):
     
#      return True

def genrateAnalysisData(dataset):
    int_array = {}
    width = {}
    height = {}
    area = {}
    pixelData = {}
    for key, value in dataset.items():
        array = value.read()
        int_array[key] = array.astype(getDataType(key))
        width[key]= value.width
        height[key]= value.height
        area[key]= width[key]*height[key]
        pixelData[key]=getEachPixelValue(int_array[key])
    context['area']=area
    context['pixelData']=pixelData
    return context


csrf_exempt
@api_view(['POST'])
@renderer_classes([JSONRenderer]) 
def byCliping(request,lat1,lon1,lat2,lon2):
    clipped_models ={}
    dataset={}
    if request.method=='POST':
        for model in request.data['modelSelection'].split(','):
            rasterPath = selectModelPath(model)
            raster = rasterio.open(rasterPath)
            bbox = [lat1,lon1,lat2,lon2]  
            clipped_models[model]=gg.raster.clip_by_bbox(raster=raster,bbox=bbox, save_clipped_raster=True,path=getOutputPathr(model), overwrite_file=True)
            geoServerPublisher(model,'clipped')
            dataset[model]=rasterio.open(getOutputPath(model))
        result = genrateAnalysisData(dataset)
        return Response(result)


csrf_exempt
@api_view(['POST'])
@renderer_classes([JSONRenderer]) 
def shapeLoader(request):
    if request.method == 'POST':
        dataset={}
        file_path = glob.glob(r'/home/ghost/Documents/django/DjangoGEE (2)/DjangoGEE/media/uploads/*')
        for file in file_path:
            os.remove(str(file))
    shp = request.data['shp']
    shx = request.data['shx']
    dbf = request.data['dbf']
    prj = request.data['prj']
    import ast
    selectedModels = ast.literal_eval(request.data['selected'])
    ShapeFile.objects.create(shp=shp,shx=shx,dbf=dbf,prj=prj)
    src = fiona.open("/home/ghost/Documents/django/DjangoGEE (2)/DjangoGEE/media/uploads/"+str(shp))
    feature = src.next()
    bounds = rasterio.features.bounds(feature['geometry'])
    context['bound']=bounds
    for selectedModel in selectedModels:
        with fiona.open(uplod_files+str(shp), "r") as shapefile:
                shapes = [feature["geometry"] for feature in shapefile]
        with rasterio.open(ld_layers+selectedModel+"/soil_"+selectedModel+".tif") as src:
                out_image, out_transform = rasterio.mask.mask(src, shapes, crop=False)
        out_meta = src.meta
        out_meta.update({"driver": "GTiff", "height": out_image.shape[1], "width": out_image.shape[2], "transform": out_transform})
        with rasterio.open(ld_layers+selectedModel+"/output/"+selectedModel+"_mask.tif", "w", **out_meta) as dest:
                dest.write(out_image)
        dataset[selectedModel]=rasterio.open(getMasked(selectedModel))
        raster_path = glob.glob(getMasked(selectedModel))
        geoServerPublisher(selectedModel,'masked')
    result = genrateAnalysisData(dataset)
        
    return Response(result)
  