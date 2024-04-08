"""Constants for DHMZ_weather."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "DHMZ Weather"
DOMAIN = "DHMZ_weather"
VERSION = "0.1.0"
ATTRIBUTION = "Data provided by DHMZ (http://www.meteo.hr/)."

CONF_LOCATION = "meteo_location"
CONF_REGION = "meteo_region"
