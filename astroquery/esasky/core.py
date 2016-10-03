# Licensed under a 3-clause BSD style license - see LICENSE.rst

import urllib.request
import json
import os
import tempfile
import tarfile
import sys

from astropy.extern import six
import astropy.io.votable as votable
from astropy.table import Table
from astropy.io import fits
import astropy.units
import astropy.utils

from ..query import BaseQuery
from ..utils import commons
from ..utils import async_to_sync
from . import conf
from ..exceptions import TableParseError

@async_to_sync
class ESASkyClass(BaseQuery):

    URLbase = conf.urlBase
    TIMEOUT = conf.timeout
    
    __FITS_STRING = ".fits"
    __FTZ_STRING = ".FTZ"
    __TAR_STRING = ".tar"
    __ALL_STRING = "all"
    __CATALOGS_STRING = "catalogs"
    __OBSERVATIONS_STRING = "observations"
    __MISSION_STRING = "mission"
    __TAP_TABLE_STRING = "tapTable"
    __TAP_NAME_STRING = "tapName"
    __FILTER_STRING = "filter"
    __LABEL_STRING = "label"
    __OBSERVATION_ID_STRING = "observation_id"
    __METADATA_STRING = "metadata"
    __MAPS_STRING = "Maps"
    __PRODUCT_URL_STRING = "product_url"
    __SOURCE_LIMIT_STRING = "sourceLimit"
    __POLYGON_NAME_STRING = "polygonNameTapColumn"
    __POLYGON_RA_STRING = "polygonRaTapColumn"
    __POLYGON_DEC_STRING = "polygonDecTapColumn"
    __POS_TAP_STRING = "posTapColumn"
    __ORDER_BY_STRING = "orderBy"
    __IS_SURVEY_MISSION_STRING = "isSurveyMission"
    __ZERO_ARCMIN_STRING = "0 arcmin"

    __HERSCHEL_STRING = 'herschel'
    __HST_STRING = 'hst'
    __INTEGRAL_STRING = 'integral'

    
    def list_maps(self):
        """
        Get a list of the mission names of the available observations in ESASky
        """
        return self._json_object_field_to_list(self._get_observation_json(), self.__MISSION_STRING)
    
    def list_catalogs(self):
        """
        Get a list of the mission names of the available catalogs in ESASky
        """
        return self._json_object_field_to_list(self._get_catalogs_json(), self.__MISSION_STRING)    
    
    def query_object_maps(self, position, missions = __ALL_STRING, get_query_payload = False):
        """
        This method queries a chosen object or coordinate for all available maps
        and returns a TableList with all the found maps metadata for the chosen missions and object.

        Parameters
        ----------
        position : str or `astropy.coordinates` object
            Can either be a string of the location, eg 'M51', or the coordinates of the object.
        missions : string or list, optional
            Can be either a specific mission or a list of missions (all mission names are found in list_missions()) 
            or 'all' to search in all missions. Defaults to 'all'. 
        get_query_payload : bool, optional
            When set to True the method returns the HTTP request parameters. Defaults to False.
            
        Returns
        -------
        table_list : `astroquery.utils.TableList`
            Each mission returns a `astroquery.table.Table` with the metadata and observations available 
            for the chosen missions and object.
            It is structured in a TableList like this:
                TableList with 8 tables:
                    '0:HERSCHEL' with 8 column(s) and 25 row(s) 
                    '1:HST' with 8 column(s) and 735 row(s) 
        
        Examples
        --------
        query_object_maps("m101", "all")
        
        import astropy.units as u
        query_object_maps("265.05, 69.0", "Herschel")
        query_object_maps("265.05, 69.0", ["Herschel", "HST"])
        """
        self.query_region_maps(position, self.__ZERO_ARCMIN_STRING, missions, get_query_payload)
        
    def query_object_catalogs(self, position, catalogs = __ALL_STRING, get_query_payload = False):
        """
        This method queries a chosen object or coordinate for all available catalogs
        and returns a TableList with all the found catalogs metadata for the chosen missions and object.

        Parameters
        ----------
        position : str or `astropy.coordinates` object
            Can either be a string of the location, eg 'M51', or the coordinates of the object.
        catalogs : string or list, optional
            Can be either a specific catalog or a list of catalogs (all catalog names are found in list_catalogs()) 
            or 'all' to search in all catalogs. Defaults to 'all'. 
        get_query_payload : bool, optional
            When set to True the method returns the HTTP request parameters. Defaults to False.

        Returns
        -------
        table_list : `astroquery.utils.TableList`
            Each mission returns a `astroquery.table.Table` with the metadata of the catalogs available 
            for the chosen mission and object.
            It is structured in a TableList like this:
                TableList with 8 tables:
                    '0:Gaia DR1 TGA' with 8 column(s) and 25 row(s) 
                    '1:HSC' with 8 column(s) and 75 row(s) 
        
        Examples
        --------
        query_object_catalogs("m101", "all")
        
        import astropy.units as u
        query_object_catalogs("265.05, 69.0", "Gaia DR1 TGA")
        query_object_catalogs("265.05, 69.0", ["Gaia DR1 TGA", "HSC"])
        """
        self.query_region_catalogs(position, self.__ZERO_ARCMIN_STRING, catalogs, get_query_payload)

    def query_region_maps(self, position, radius, missions = __ALL_STRING, get_query_payload = False):
        """
        This method queries a chosen region for all available maps
        and returns a TableList with all the found maps metadata for the chosen missions and region.

        Parameters
        ----------
        position : str or `astropy.coordinates` object
            Can either be a string of the location, eg 'M51', or the coordinates of the object.
        radius : str or `~astropy.units.Quantity`
            The radius of a region.
        missions : string or list, optional
            Can be either a specific mission or a list of missions (all mission names are found in list_missions()) 
            or 'all' to search in all missions. Defaults to 'all'. 
        get_query_payload : bool, optional
            When set to True the method returns the HTTP request parameters. Defaults to False.
            
        Returns
        -------
        table_list : `astroquery.utils.TableList`
            Each mission returns a `astroquery.table.Table` with the metadata and observations available 
            for the chosen missions and region.
            It is structured in a TableList like this:
                TableList with 8 tables:
                    '0:HERSCHEL' with 8 column(s) and 25 row(s) 
                    '1:HST' with 8 column(s) and 735 row(s) 
        
        Examples
        --------
        query_region_maps("m101", "14'", "all")
        
        import astropy.units as u
        query_region_maps("265.05, 69.0", 14*u.arcmin, "Herschel")
        query_region_maps("265.05, 69.0", ["Herschel", "HST"])
        """        
        sanatized_position = self._sanatize_input_position(position)
        sanatized_radius = self._sanatize_input_radius(radius)
        sanatized_missions = self._sanatize_input_mission(missions)
                
        query_result = {}

        coordinates = commons.parse_coordinates(sanatized_position)
            
        self._store_query_result_maps(query_result, sanatized_missions, coordinates, sanatized_radius, get_query_payload)
        
        if(get_query_payload):
            return query_result
        
        return commons.TableList(query_result)
    
    def query_region_catalogs(self, position, radius, catalogs = __ALL_STRING, get_query_payload = False):
        """
        This method queries a chosen region for all available catalogs
        and returns a TableList with all the found catalogs metadata for the chosen missions and region.

        Parameters
        ----------
        position : str or `astropy.coordinates` object
            Can either be a string of the location, eg 'M51', or the coordinates of the object.
        radius : str or `~astropy.units.Quantity`
            The radius of a region.
        catalogs : string or list, optional
            Can be either a specific catalog or a list of catalogs (all catalog names are found in list_catalogs()) 
            or 'all' to search in all catalogs. Defaults to 'all'. 
        get_query_payload : bool, optional
            When set to True the method returns the HTTP request parameters. Defaults to False.

        Returns
        -------
        table_list : `astroquery.utils.TableList`
            Each mission returns a `astroquery.table.Table` with the metadata of the catalogs available 
            for the chosen mission and region.
            It is structured in a TableList like this:
                TableList with 8 tables:
                    '0:Gaia DR1 TGA' with 8 column(s) and 25 row(s) 
                    '1:HSC' with 8 column(s) and 75 row(s) 
        
        Examples
        --------
        query_region_catalogs("m101", "14'", "all")
        
        import astropy.units as u
        query_region_catalogs("265.05, 69.0", 14*u.arcmin, "Gaia DR1 TGA")
        query_region_catalogs("265.05, 69.0", 14*u.arcmin, ["Gaia DR1 TGA", "HSC"])
        """  
        sanatized_position = self._sanatize_input_position(position)
        sanatized_radius = self._sanatize_input_radius(radius)
        sanatized_catalogs = self._sanatize_input_catalogs(catalogs)

        coordinates = commons.parse_coordinates(sanatized_position)
        
        query_result = {}
                
        self._store_query_result_catalogs(query_result, sanatized_catalogs, coordinates, sanatized_radius, get_query_payload)
        
        if(get_query_payload):
            return query_result
        
        return commons.TableList(query_result)
    
    def get_maps(self, query_table_list, missions = __ALL_STRING, download_folder = __MAPS_STRING):
        """
        This method takes the dictionary of missions and metadata as returned by query_region_maps
        and downloads all maps to the selected folder.
        The method returns a dictionary which is divided by mission and observation id. 

        Parameters
        ----------
        query_table_list : `astroquery.utils.TableList`
            A TableList with all the missions wanted and their respective metadata.
            Usually the return value of query_region_maps.
        missions : string or list, optional
            Can be either a specific mission or a list of missions (all mission names are found in list_missions()) 
            or 'all' to search in all missions. Defaults to 'all'. 
        download_folder : string, optional
            The folder where all downloaded maps should be stored. 
            Defaults to a folder called 'Maps' in the current working directory. 

        Returns
        -------
        maps : dict
            Each mission returns dict where each observation id has a HDUList. 
            The exception is Herschel as it has multiple fits files per observation id.
            For Herschel each observation id got the used filters with their respective HDULists.
            It is structured in a dictionary like this:
                dict: {'XMM-EPIC': {'observationID_x': [HDUList], 'observationID_y': [HDUList], ...}, 'HST': {'observationID_z': [HDUList], ...},
                    'HERSCHEL': {'observationID_a': {'filter_a':[HDUList], filter_b: [HDUList]}, 'observationID_b': {'filter_a':[HDUList], filter_b: [HDUList]}, ... }}
        
        Examples
        --------
        get_maps(query_region_catalogs("m101", "14'", "all"))
        
        """    
        sanatized_query_table_list = self._sanatize_input_table_list(query_table_list)
        sanatized_missions = self._sanatize_input_mission(missions)

        maps = dict()
         
        for query_mission in sanatized_query_table_list.keys():
            for mission in sanatized_missions:
                #INTEGRAL does not have a product url yet.
                if(query_mission.lower() == self.__INTEGRAL_STRING):
                    break
                if(query_mission.lower() == mission.lower()):
                    maps[query_mission] = self._get_maps_for_mission(sanatized_query_table_list[query_mission], query_mission, download_folder)
                    break
        if(len(sanatized_query_table_list) > 0):
            print("Maps available at %s" %os.path.abspath(download_folder))
        else:
            print("No maps found")
        return commons.TableList(maps)
    
    def get_images(self, position, radius = 0, missions = __ALL_STRING, download_folder = __MAPS_STRING):
        """
        This method gets the fits files available for the selected position and mission
        and downloads all maps to the folder /Maps.
        The method returns a dictionary which is divided by mission and observation id. 

        Parameters
        ----------
        position : str or `astropy.coordinates` object
            Can either be a string of the location, eg 'M51', or the coordinates of the object.
        radius : str or `~astropy.units.Quantity`, optional
            The radius of a region. Defaults to 0.
        missions : string or list, optional
            Can be either a specific mission or a list of missions (all mission names are found in list_missions()) 
            or 'all' to search in all missions. Defaults to 'all'. 
        download_folder : string, optional
            The folder where all downloaded maps should be stored. 
            Defaults to a folder called 'Maps' in the current working directory. 

        Returns
        -------
        maps : `dict`
            Each mission returns dictionary where each observation id has a HDUList. 
            The exception is Herschel as it has multiple fits files per observation id.
            For Herschel each observation id got the used filters with their respective HDULists.
            It is structured in a dictionary like this:
                dict: {'XMM-EPIC': {'observationID_x': [HDUList], 'observationID_y': [HDUList], ...}, 'HST': {'observationID_z': [HDUList], ...},
                    'HERSCHEL': {'observationID_a': {'filter_a':[HDUList], filter_b: [HDUList]}, 'observationID_b': {'filter_a':[HDUList], filter_b: [HDUList]}, ... }}
        
        Examples
        --------
        get_images("m101", "14'", "all")
        
        """    
        sanatized_position = self._sanatize_input_position(position)
        sanatized_radius = self._sanatize_input_radius(radius)
        sanatized_missions = self._sanatize_input_mission(missions)
        
        maps = dict()
        
        map_query_result = self.query_region_maps(sanatized_position, sanatized_radius, sanatized_missions, False)
                
        for query_mission in map_query_result:
            #INTEGRAL does not have a product url yet.
            if(query_mission.lower() == self.__INTEGRAL_STRING):
                continue
            maps[query_mission] = self._get_maps_for_mission(map_query_result[query_mission], query_mission, download_folder)

        
        print("Maps available at %s" %os.path.abspath(self.download_folder))
        return maps
    
    def _sanatize_input_position(self, position):
        if (isinstance(position, str) or isinstance(position, commons.CoordClasses)):
            return position
        else:
            raise ValueError("Position must be either a string or astropy.coordinates")

    def _sanatize_input_radius(self, radius):
        if (isinstance(radius, str) or isinstance(radius, astropy.units.Quantity)):
            return radius
        else:
            raise ValueError("Radius must be either a string or astropy.units.Quantity")

    def _sanatize_input_mission(self, missions):
        if (isinstance(missions, list)):
            return missions
        if (isinstance(missions, str)):
            if(missions.lower() == self.__ALL_STRING):
                return self.list_maps()
            else:
                return [missions]
        raise ValueError("Mission must be either a string or a list of missions")
    
    def _sanatize_input_catalogs(self, catalogs):
        if (isinstance(catalogs, list)):
            return catalogs
        if (isinstance(catalogs, str)):
            if(catalogs.lower() == self.__ALL_STRING):
                return self.list_maps()
            else:
                return [catalogs]
        raise ValueError("Catalog must be either a string or a list of catalogs")

    def _sanatize_input_table_list(self, table_list):
        if (isinstance(table_list, commons.TableList)):
            return table_list
        raise ValueError("Query_table_list must be an astropy.utils.TableList")
      
    def _get_maps_for_mission(self, maps_table, mission, download_folder):
        maps = dict()
        
        if(len(maps_table[self.__PRODUCT_URL_STRING]) > 0):
            mission_directory = self._create_mission_directory(mission, download_folder)    
            print("Starting download of %s data. (%d files)" %(mission, len(maps_table[self.__PRODUCT_URL_STRING])))
            for index in range(len(maps_table)):
                product_url = maps_table[self.__PRODUCT_URL_STRING][index].decode('utf-8')
                observation_id = maps_table[self.__OBSERVATION_ID_STRING][index].decode('utf-8')
                print("Downloading Observation ID: %s from %s" %(observation_id, product_url), end=" ")
                sys.stdout.flush()
                directory_path = mission_directory + "/"
                if(mission.lower() == self.__HERSCHEL_STRING):
                    herschel_filter = maps_table[self.__FILTER_STRING][index].decode('utf-8').split(",")
                    maps[observation_id] = self._get_herschel_observation(product_url, directory_path, herschel_filter)
                    
                else:
                    with urllib.request.urlopen(product_url) as response:
                        file_name = ""
                        if(product_url.endswith(self.__FITS_STRING)):
                            file_name = directory_path + self._extract_file_name_from_url(product_url)
                        else:
                            file_name = directory_path + self._extract_file_name_from_response_header(response.headers)
                        
                        fits_data = response.read()
                        with open(file_name, 'wb') as fits_file:
                            fits_file.write(fits_data)
                            fits_file.close()
                            maps[observation_id] = fits.open(file_name)
                
                print("[Done]")
            print("Downloading of %s data complete." %mission)
        
        return maps
    
    def _get_herschel_observation(self, product_url, directory_path, filters):
        observation = dict()            
        tar_file = tempfile.NamedTemporaryFile()
        with urllib.request.urlopen(product_url) as response:
            tar_file.write(response.read())    
        with tarfile.open(tar_file.name,'r') as tar:
            i = 0
            for member in tar.getmembers():
                member_name = member.name.lower()
                if ('hspire' in member_name or 'hpacs' in member_name):
                    tar.extract(member, directory_path)
                    member.name = self._remove_extra_herschel_directory(member.name, directory_path)
                    observation[filters[i]] = fits.open(directory_path + member.name)
                    i += 1
        return observation
    
    def _remove_extra_herschel_directory(self, file_and_directory_name, directory_path):
        full_directory_path = os.path.abspath(directory_path)
        file_name = file_and_directory_name[file_and_directory_name.index("/") + 1:]
        os.renames(os.path.join(full_directory_path, file_and_directory_name), os.path.join(full_directory_path, file_name))
        return file_name
    
    def _create_mission_directory(self, mission, download_folder):
        if (download_folder == self.__MAPS_STRING):
            mission_directory = self.__MAPS_STRING + "/" + mission
        else:
            mission_directory = download_folder + "/" + self.__MAPS_STRING + "/" + mission
        if not os.path.exists(mission_directory):
            os.makedirs(mission_directory)
        return mission_directory
    
    def _extract_file_name_from_response_header(self, headers):
        content_disposition = headers.get('Content-Disposition')
        filename_string = "filename="
        start_index = content_disposition.index(filename_string) + len(filename_string)
        if (content_disposition[start_index] == "\""):
            start_index += 1
       
        if (self.__FITS_STRING in content_disposition[start_index : ]):
            end_index = content_disposition.index(self.__FITS_STRING, start_index + 1) + len(self.__FITS_STRING)
            return content_disposition[start_index : end_index]
        elif (self.__FTZ_STRING in content_disposition[start_index : ]):
            end_index = content_disposition.index(self.__FTZ_STRING, start_index + 1) + len(self.__FTZ_STRING)
            return content_disposition[start_index : end_index]
        elif (self.__TAR_STRING in content_disposition[start_index : ]):
            end_index = content_disposition.index(self.__TAR_STRING, start_index + 1) + len(self.__TAR_STRING)
            return content_disposition[start_index : end_index]
        else:
            raise ValueError("Could not find file name in header. Content disposition: %s." %content_disposition)
            return None
    
    def _extract_file_name_from_url(self, product_url):
        start_index = product_url.rindex("/") + 1
        return product_url[start_index:]
    
    def _query_region_maps(self, coordinates, radius, observation_name, get_query_payload):
        observation_tap_name = self._find_observation_tap_table_name(observation_name)
        query = self._build_observation_query(coordinates, radius, self._find_observation_parameters(observation_tap_name))
        request_payload = self._create_request_payload(query)
        if(get_query_payload):
            return request_payload
        return self._get_and_parse_from_tap(request_payload)
    
    def _query_region_catalog(self, coordinates, radius, catalog_name, get_query_payload):
        catalog_tap_name = self._find_catalog_tap_table_name(catalog_name)
        query = self._build_catalog_query(coordinates, radius, self._find_catalog_parameters(catalog_tap_name))
        request_payload = self._create_request_payload(query)
        if(get_query_payload):
            return request_payload
        return self._get_and_parse_from_tap(request_payload)
        
    def _build_observation_query(self, coordinates, radius, json):
        raHours, dec = commons.coord_to_radec(coordinates)
        ra = raHours * 15.0 # Converts to degrees
        radiusDeg = commons.radius_to_unit(radius, unit='deg')
        
        select_query = "SELECT DISTINCT"
        
        metadata = json[self.__METADATA_STRING]
        metadata_tap_names = ""
        for i in range(len(metadata)): 
            if(i < len(metadata) - 1):
                metadata_tap_names += " %s," %metadata[i][self.__TAP_NAME_STRING]
            else:
                metadata_tap_names += " %s" %metadata[i][self.__TAP_NAME_STRING]

        from_query = " FROM %s" %json[self.__TAP_TABLE_STRING]
        if (json[self.__IS_SURVEY_MISSION_STRING]):
            where_query = " WHERE 1=CONTAINS(pos,"
        else:
            where_query = " WHERE 1=CONTAINS(fov,"
            
        region_query = " CIRCLE('ICRS', %f, %f, %f));" %(ra, dec, radiusDeg) 
        
        query = select_query + metadata_tap_names + from_query + where_query + region_query
        return query  
               
    def _build_catalog_query(self, coordinates, radius, json):
        raHours, dec = commons.coord_to_radec(coordinates) 
        ra = raHours * 15.0 # Converts to degrees
        radiusDeg = commons.radius_to_unit(radius, unit='deg')
        
        select_query = "SELECT TOP %s " %json[self.__SOURCE_LIMIT_STRING]
          
        metadata = json[self.__METADATA_STRING]
        metadata_tap_names = ""
        for i in range(len(metadata)): 
            if(i < len(metadata) - 1):
                metadata_tap_names += " %s," %metadata[i][self.__TAP_NAME_STRING]
            else:
                metadata_tap_names += " %s" %metadata[i][self.__TAP_NAME_STRING]

        from_query = " FROM %s" %json[self.__TAP_TABLE_STRING]
        where_query = " WHERE 1=CONTAINS(%s, CIRCLE('ICRS', %f, %f, %f))"%(json[self.__POS_TAP_STRING], ra, dec, radiusDeg)  
        order_by_query = " ORDER BY %s;" %json[self.__ORDER_BY_STRING]
        
        query = select_query + metadata_tap_names + from_query + where_query + order_by_query      
        
        return query    
    
    def _store_query_result_maps(self, query_result, missions, coordinates, radius, get_query_payload):
        for mission in missions:
            mission_table = self._query_region_maps(coordinates, radius, mission, get_query_payload)
            if (len(mission_table) > 0):
                query_result[mission.upper()] = mission_table
        return
    
    def _store_query_result_catalogs(self, query_result, catalogs, coordinates, radius, get_query_payload):
        for catalog in catalogs:
            catalog_table = self._query_region_catalog(coordinates, radius, catalog, get_query_payload)
            if (len(catalog_table) > 0):
                query_result[catalog.upper()] = catalog_table
        return        
            
    def _find_observation_parameters(self, mission_name):
        return self._find_mission_parameters_in_json(mission_name, self._get_observation_json())
    
    def _find_catalog_parameters(self, catalog_name):
        return self._find_mission_parameters_in_json(catalog_name, self._get_catalogs_json())
        
    def _find_mission_parameters_in_json(self, mission_tap_name, json):
        for mission in json:
            if (mission[self.__TAP_TABLE_STRING] == mission_tap_name):
                return mission
        raise ValueError("Input tap name %s not available." %mission_tap_name)
        return None  

    def _find_observation_tap_table_name(self, mission_name):
        return self._find_mission_tap_table_name(self._fetch_and_parse_json(self.__OBSERVATIONS_STRING), mission_name)

    def _find_catalog_tap_table_name(self, mission_name):
        return self._find_mission_tap_table_name(self._fetch_and_parse_json(self.__CATALOGS_STRING), mission_name)
    
    def _find_mission_tap_table_name(self, json, mission_name):
        for i in range(len(json)):
            if (json[i][self.__MISSION_STRING].lower() == mission_name.lower()):
                return json[i][self.__TAP_TABLE_STRING]
        
        raise ValueError("Input %s not available." %mission_name)
        return None  
  
    def _get_observation_json(self):
        return self._fetch_and_parse_json(self.__OBSERVATIONS_STRING)

    def _get_catalogs_json(self):
        return self._fetch_and_parse_json(self.__CATALOGS_STRING)
  
    def _fetch_and_parse_json(self, object_name):
        url = self.URLbase + "/" + object_name
        with urllib.request.urlopen(url) as response:
            string_response = response.read().decode('utf-8')
        json_response = json.loads(string_response)
        return json_response[object_name]
    
    def _json_object_field_to_list(self, json, field_name):
        response_list = []
        for i in range(len(json)):
            response_list.append(json[i][field_name])
        return response_list
    
    def _create_request_payload(self, query):
        return {'REQUEST':'doQuery', 'LANG':'ADQL', 'FORMAT': 'VOTABLE', 'QUERY': query}
    
    def _get_and_parse_from_tap(self, request_payload, cache = True):
        response = self._send_get_request("/tap/sync", request_payload, cache)
        return self._parse_xml_table(response)
    
    def _send_get_request(self, url_extension, request_payload, cache):
        URL = self.URLbase + url_extension
        return self._request('GET', URL, params=request_payload,
                                 timeout=self.TIMEOUT, cache=cache)

    def _parse_xml_table(self, response):
        # try to parse the result into an astropy.Table, else
        # return the raw result with an informative error message.
        try:
            tf = six.BytesIO(response.content)
            vo_table = votable.parse(tf, pedantic = False)
            first_table = vo_table.get_first_table()
            table = first_table.to_table(use_names_over_ids = True)
            return table
        except Exception as ex:
            self.response = response
            self.table_parse_error = ex
            raise TableParseError(
                "Failed to parse ESASky VOTABLE result! The raw response can be "
                "found in self.response, and the error in "
                "self.table_parse_error.")
        return Table()

ESASky = ESASkyClass()
