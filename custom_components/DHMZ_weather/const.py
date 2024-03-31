"""Constants for DHMZ_weather."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "DHMZ Weather"
DOMAIN = "DHMZ_weather"
VERSION = "0.1.1"
ATTRIBUTION = "Data provided by DHMZ (https://meteo.DHMZ.gov.si/)."

CONF_LOCATION = "meteo_location"
CONF_REGION = "meteo_region"
