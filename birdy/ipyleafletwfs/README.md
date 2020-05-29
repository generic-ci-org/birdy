# IpyleafletWFS

This module facilitates the use of a WFS service through the ipyleaflet module in jupyter notebooks.

It uses owslib to get a geojson out of a WFS service, and then creates an ipyleaflet GeoJSON layer with it.

## Use

This module is to be used inside a jupyter notebook, either with a standard server or through vscode/pycharm.

There are a notebook examples which show how to use this module and what can be done with it.

The WFS request is filtered by the extent of the visible map, to make large layers easier to work with. 
Using the on-map 'Refresh WFS layer' button will make a new request for the current extent.

**Warning**
WFS requests and GeoJSON layers can take a long time to process and render. Trying to load a lake layers for a nation wide extent will take a long time
and probably crash. The denser and complex the layer, the more zoomed in the map extent should be.