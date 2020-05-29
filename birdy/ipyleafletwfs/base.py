from ipyleaflet import GeoJSON, WidgetControl
from ipywidgets import HTML, Button
from owslib.wfs import WebFeatureService
import json


# # # # # # # # # # #
# Utility functions #
# # # # # # # # # # #


def _map_extent_to_bbox_filter(source_map):
    """Return formatted coordinates, from ipylealet format to owslib.wfs format.

    This function takes the result of ipyleaflet's Map.bounds() function and formats it
    so it can be used as a bbox filter in an owslib WFS request.

    Parameters
    ----------
    source_map: Map instance
        The map instance from which the extent will calculated

    Returns
    -------
    Tuple
        Coordinates formatted to WebFeatureService bounding box filter.
    """
    coords = source_map.bounds
    lon1 = coords[0][1]
    lat1 = coords[0][0]
    lon2 = coords[1][1]
    lat2 = coords[1][0]
    formatted_coordinates = (lon1, lat1, lon2, lat2)

    return formatted_coordinates


class IpyleafletWFS(object):
    """Create a connection to a WFS service capable of geojson output.

    This class is a small wrapper for ipylealet to facilitate the use of
    a WFS service, as well as provide some automation.

    Request to the WFS service is done through the owslib module and requires
    a geojson output capable WFS. The geojson data is filtered for the map extent
    and loaded as an ipyleaflet GeoJSON layer.

    The automation done through build_layer() supports only a single
    layer per instance is supported.

    For multiple layers, used different instances of IpylealetWFS and Ipyleaflet.Map()
    or use the create_wfsgeojson_layer() function to build your own custom map and widgets
    with ipyleaflet.

    Parameters:
    -----------
    url: string
      The url of the WFS service

    wfs_version: string
      The version of the WFS service to use. Defaults to 2.0.0

    Returns
    -------
    IpyleafletWFS instance
      Instance from which the WFS layers can be created.
    """

    def __init__(self, url, wfs_version='2.0.0'):
        self._geojson = None
        self._layer = None
        self._layer_typename = ''
        self._layerstyle = {}
        self._property = None
        self._property_widgets = {}
        self._refresh_widget = None
        self._source_map = None
        self._wfs = WebFeatureService(url, version=wfs_version)

        # _property_widgets structure is as follows
        # { 'widget_name': {
        #       'widget': widget instance,
        #       'property_key': property_string,
        #       'position': position_string,
        #       },
        # }

    # # # # # # # # # # # # # # #
    # Layer creation function   #
    # # # # # # # # # # # # # # #

    def build_layer(self, layer_typename, source_map, layer_style={}, property=None):
        """ Return an ipyleaflet GeoJSON layer from a geojson wfs request.

        Requires the WFS service to be capable of geojson output.

        Running this function multiple times will overwrite the previous layer and widgets.

        Parameters
        ----------
        layer_typename: string
          Typename of the layer to display. Listed as Layer_ID by get_layer_list().
          Must include namespace and layer name, separated  by a colon.

          ex: public:canada_forest_layer

        source_map: Map instance
          The map instance on which the layer is to be added

        layer_style: dictionnary
          ipyleaflet GeoJSON style format. See ipyleaflet documentation for more information

          ex: { 'color': 'white', 'opacity': 1, 'dashArray': '9', 'fillOpacity': 0.1, 'weight': 1 }

        property: string
          The property key to be used by the widget. Use the property_list() function
          to get a list of the available properties

        """
        # Check if layer already exists
        if self._layer:
            self._source_map.remove_layer(self._layer)

        # Set parameters
        self._layer_typename = layer_typename
        self._source_map = source_map
        if property is not None:
            self._property = property
        if layer_style is not None:
            self._layerstyle = layer_style

        # Calculate extent filter
        bbox_filter_coords = _map_extent_to_bbox_filter(self._source_map)

        # Fetch and prepare data
        data = self._wfs.getfeature(typename=self._layer_typename, bbox=bbox_filter_coords, outputFormat='JSON')
        self._geojson = json.loads(data.getvalue().decode())

        # Create layer and add to the map
        self._layer = GeoJSON(data=self._geojson, style=layer_style)
        self._source_map.add_layer(self._layer)

        # Create default property widget
        self.create_feature_property_widget('main_widget', self._property)

        # Create refresh button
        self._create_refresh_widget()

    def create_wfsgeojson_layer(self, layer_typename, source_map, layer_style={}):
        """Create a static ipyleaflett GeoJSON layer from a WFS service

        Simple wrapper for a WFS => GeoJSON layer, using owslib.

        Will create a GeoJSON layer, filtered by the extent of the source_map parameter.
        If no source map is given, it will not filter by extent, which can cause problems
        with large layers

        WFS service need to have geojson output.

        Parameters
        ----------
        layer_typename: string
          Typename of the layer to display. Listed as Layer_ID by get_layer_list().
          Must include namespace and layer name, separated  by a colon.

          ex: public:canada_forest_layer

        source_map: Map instance
          The map instance from which the extent will be used to filter the request

        layer_style: dictionnary
          ipyleaflet GeoJSON style format. See ipyleaflet documentation for more information

          ex: { 'color': 'white', 'opacity': 1, 'dashArray': '9', 'fillOpacity': 0.1, 'weight': 1 }

        Returns
        -------
        GeoJSON layer: an instance of an ipyleaflet GeoJSON layer
        """
        # Calculate extent filter
        bbox_filter_coords = _map_extent_to_bbox_filter(source_map)

        # Fetch and prepare data
        data = self._wfs.getfeature(typename=layer_typename, bbox=bbox_filter_coords, outputFormat='JSON')
        self._geojson = json.loads(data.getvalue().decode())

        # Create layer, default widget and add to the map
        layer = GeoJSON(data=self._geojson, style=layer_style)

        return layer

    def _refresh_layer(self, layer_style=None, property=None):
        """Refresh the wfs layer for the current map extent.

        Also updates the existing widgets.

        Can also be used to change the layer style and the default property widget

        Parameters
        ----------
        layer_style: dictionnary
          ipyleaflet GeoJSON style format. See ipyleaflet documentation for more information
          ex: { 'color': 'white', 'opacity': 1, 'dashArray': '9', 'fillOpacity': 0.1, 'weight': 1 }

        property: string
          The property key to be used by the widget. Use the property_list() function
          to get a list of the available properties
        """
        if self._layer:
            self.build_layer(self._layer_typename, self._source_map, self._layerstyle, self._property)

            for widget in self._property_widgets:
                self.create_feature_property_widget(widget_name=widget,
                                                    property=self._property_widgets[widget]['property_key'],
                                                    widget_position=self._property_widgets[widget]['position'])
        else:
            print('There is no layer to refresh')

    def remove_layer(self):
        """Remove layer instance and it's widgets from map
        """
        if self._layer:
            # Remove maps elements
            self.clear_property_widgets()
            self._source_map.remove_control(self._refresh_widget)
            self._source_map.remove_layer(self._layer)

            # Reset instance
            self._layer = None
            self._layer_typename = ''
            self._layerstyle = {}
            self._property = None
            self._geojson = None
            self._refresh_widget = None
        else:
            print('There is no layer to remove')

    # # # # # # # # # # # # # # # #
    # Layer information functions #
    # # # # # # # # # # # # # # # #

    def feature_properties_by_id(self, feature_id):
        """Return the properties of a feature

        The id field is usually the first field. Since the name is
        always different, this is the only assumption that can be
        made to automate this process. Hence, this will not work if
        the layer in question does not follow this formatting.

        Parameters
        ----------
        feature_id: int
          The feature id.

        Returns
        -------
        Dict
          A dictionary  of the layer's properties
        """
        for feature in self._geojson['features']:
            # The id field is usually the first field. Since the name is
            # always different, this is the only assumption I could make
            # to automate this process.
            first_key = list(feature['properties'].keys())[0]
            current_feature_id = feature['properties'][first_key]

            if current_feature_id == feature_id:
                return feature['properties']

    @ property
    def geojson(self):
        """Return the imported geojson data in a python object format.
        """
        return self._geojson

    @ property
    def layer_list(self):
        """Return a simple layer list available to the WFS service

        Returns
        -------
        List
          A List of the WFS layers available
        """
        return sorted(self._wfs.contents.keys())

    @ property
    def property_list(self):
        """Return a list containing the properties of the first feature.

        Retrieves the available properties for use subsequent use
        by the feature property widget

        Returns
        -------
        Dict
          A dictionary  of the layer properties
        """
        return self._geojson['features'][0]['properties']

    @property
    def layer(self):
        return self._layer

    # # # # # # # # # #
    # Widget creation #
    # # # # # # # # # #

    def _set_widget(self, widget_name, property, src_map, textbox, widget_position):
        if widget_name in self._property_widgets:
            src_map.remove_control(self._property_widgets[widget_name]['widget'])

        self._property_widgets[widget_name] = {}
        self._property_widgets[widget_name]['property_key'] = property
        self._property_widgets[widget_name]['position'] = widget_position
        self._property_widgets[widget_name]['widget'] = WidgetControl(widget=textbox,
                                                                      position=widget_position,
                                                                      min_width=120,
                                                                      max_width=120)

        src_map.add_control(self._property_widgets[widget_name]['widget'])

    def _create_refresh_widget(self):
        if self._refresh_widget is None:
            button = Button(description="Refresh WFS layer")
            button.on_click(self._refresh_layer)
            self._refresh_widget = WidgetControl(widget=button, position='topright')
            self._source_map.add_control(self._refresh_widget)

    def clear_property_widgets(self):
        """Remove all property widgets from a map.

        This function will remove the property widgets from a given map, without
        affecting other widgets

        Parameters
        ----------
        src_map: Map instance
          The map instance from which the widgets are to be removed
        """
        for widget in self._property_widgets:
            self._source_map.remove_control(self._property_widgets[widget]['widget'])
        self._property_widgets.clear()

    def create_feature_property_widget(self, widget_name, property=None, widget_position='bottomright'):
        """Create a visualization widget for a specific feature property

        Will create a widget for the layer and source map used to create
        Once the widget is created, click on a map feature to have the information
        appear in the corresponding box.

        To replace the default widget that get created by the build_layer() function,
        set the  widget_name parameter to 'main_widget'

        Widgets create by this function are unique by their widget_name variable.

        Parameters
        ----------
        widget_name: string
          Name of the widget. Must be unique or will overwrite existing widget

        property: string
          The property key to be used by the widget. Use the property_list() function
          to get a list of the available properties. If left empty, it will default to
          the first property attribute in the list.

        widget_position: string
          Position on the map for the widget. Choose between ‘bottomleft’, ‘bottomright’, ‘topleft’, or ‘topright’

        """

        textbox = HTML('''
            Click on a feature
        ''')
        textbox.layout.margin = '20px 20px 20px 20px'

        self._set_widget(widget_name, property, self._source_map, textbox, widget_position)

        def _update_textbox(properties=None, **kwargs):
            # The check for properties is necessary because of a bug in ipylealet.
            # On_click registers twice, which causes a TypeError
            # See https://github.com/jupyter-widgets/ipyleaflet/issues/373
            if properties is None:
                return

            key = list(properties.keys())[0]
            if property:
                key = property
            textbox.value = '''
                <h4>{}<h4>
                <b style="font-size:10px">{}<b>
            '''.format(key, properties[key])

        self._layer.on_click(_update_textbox)
