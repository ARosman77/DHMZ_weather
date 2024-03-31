"""Sample API Client."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import asyncio
import socket
import aiohttp
import async_timeout

from .const import LOGGER

# posibile conditions, and what should they be translated from
#    ‘clear-night’

#    ‘cloudy’ = prevCloudy, overcast,
#    ‘sunny’ = clear, mostClear, slightCloudy
#    ‘partlycloudy’ = , partCloudy, modCloudy

# cloud condition mapping
CLOUD_CONDITION_MAPPING = {
    "clear": "sunny",
    "mostClear": "sunny",
    "slightCloudy": "sunny",
    "partCloudy": "partlycloudy",
    "modCloudy": "partlycloudy",
    "prevCloudy": "cloudy",
    "overcast": "cloudy",
    "FG": "fog",
}

# phenomena condition mapping
#   ‘fog’ = FG
#   ‘hail’ = SHGR, TSGR
#   ‘lightning’ = TS
#   ‘lightning-rainy’ = TSRA
#   ‘rainy’ = RA, DZ, FZDZ, FZRA, SHRA
#   ‘snowy’ = SN, SHSN, TSSN
#   ‘snowy-rainy’ = RASN, SHRASN, TSRASN
PHENOMENA_CONDITION_MAPPING = {
    "FG": "fog",
    "SHGR": "hail",
    "TSGR": "hail",
    "TS": "lightning",
    "TSRA": "lightning-rainy",
    "RA": "rainy",
    "DZ": "rainy",
    "FZDZ": "rainy",
    "FZRA": "rainy",
    "SHRA": "rainy",
    "SN": "snowy",
    "SHSN": "snowy",
    "TSSN": "snowy",
    "RASN": "snowy-rainy",
    "SHRASN": "snowy-rainy",
    "TSRASN": "snowy-rainy",
}

# Processed sepparately
#   ‘pouring’ = heavyRA

#
# This ones don't exist in meteo data
#
#    ‘windy’
#    ‘windy-variant’
#    ‘exceptional’
#


class DHMZApiClientError(Exception):
    """Exception to indicate a general API error."""


class DHMZApiClientCommunicationError(DHMZApiClientError):
    """Exception to indicate a communication error."""


class DHMZApiClientAuthenticationError(DHMZApiClientError):
    """Exception to indicate an authentication error."""


class DHMZMeteoData:
    """Meteo data class."""

    def __init__(
        self,
        current_data: str,
        forecast_data: str,
    ) -> None:
        """Initialize Meteo data class."""
        self._current_data = current_data
        self._forecast_data = forecast_data
        self._meteo_data_all = []
        self._meteo_fc_data_all = []

        data_selection = [
            "domain_title",
            "domain_longTitle",
            "domain_lat",
            "domain_lon",
            "domain_altitude",
            "t",
            "rh",
            "msl",
            "nn_icon-wwsyn_icon",
            "dd_val",
            "ff_val",
            "tp_12h_acc",
            "vis_val",
        ]

        data_fc_selection = [
            "domain_shortTitle",
            "domain_lat",
            "domain_lon",
            "domain_altitude",
            "valid_UTC",  # time and date
            "nn_icon-wwsyn_icon",  # condition, neeeds to be decoded
            "td",  # dew point
            "dd_decodeText",  # wind direction, needs to be decoded?
            "ff_val",  # wind m/s
            "ffmax_val",  # gusts of wind m/s
            "t",  # apparent temperature (proboably average?)
            "tnsyn",  # min temp
            "txsyn",  # max temp
            "msl",  # air pressure
            "rh",  # humidity, not present?
        ]

        root = ET.fromstring(current_data)
        for meteo_parent in root.findall("metData"):
            meteo_data_location = {}
            for data in data_selection:
                meteo_data_location[data] = meteo_parent.find(data).text
            self._meteo_data_all.append(meteo_data_location)

        root = ET.fromstring(forecast_data)
        for meteo_parent in root.findall("metData"):
            meteo_data_region = {}
            for data in data_fc_selection:
                meteo_data_region[data] = meteo_parent.find(data).text
            self._meteo_fc_data_all.append(meteo_data_region)

    def current_temperature(self, location: str) -> str:
        """Return temperature of the location."""
        return self.current_meteo_data(location, "t")

    def current_humidity(self, location: str) -> float:
        """Return humidity of the location."""
        humidity = self.current_meteo_data(location, "rh")
        return float(humidity) if humidity else None

    def current_air_pressure(self, location: str) -> str:
        """Return air pressure of the location."""
        return self.current_meteo_data(location, "msl")

    def _decode_meteo_condition(self, description: str) -> str:
        """Decode meteo condition to home assistant condition."""
        if description is None:
            return None
        list_of_conditions = description.split("_")
        cloud_condition = list_of_conditions[0] if len(list_of_conditions) > 0 else None
        phenomena_condition = (
            list_of_conditions[1] if len(list_of_conditions) > 1 else None
        )

        if phenomena_condition is not None:
            phenomena_type = "".join([c for c in phenomena_condition if c.isupper()])
            phenomena_strength = "".join(
                [c for c in phenomena_condition if c.islower()]
            )
        else:
            phenomena_type = None
            phenomena_strength = None

        LOGGER.debug("API.py > _decode_meteo_condition()")
        LOGGER.debug(
            "--> cloud=%s / type=%s / strength=%s",
            str(cloud_condition),
            str(phenomena_type),
            str(phenomena_strength),
        )

        # complicated decoding done here:
        if phenomena_type is None:
            return CLOUD_CONDITION_MAPPING[cloud_condition]
        # ‘pouring’ = heavyRA
        if (phenomena_type == "RA") and (phenomena_strength == "heavy"):
            return "pouring"
        return PHENOMENA_CONDITION_MAPPING[phenomena_type]

    def current_condition(self, location: str) -> str:
        """Return current condition of the location."""
        LOGGER.debug("API.py > current_condition()")
        LOGGER.debug(
            "--> decoding '%s' to condition '%s' ",
            str(self.current_meteo_data(location, "nn_icon-wwsyn_icon")),
            str(
                self._decode_meteo_condition(
                    self.current_meteo_data(location, "nn_icon-wwsyn_icon")
                )
            ),
        )
        return self._decode_meteo_condition(
            self.current_meteo_data(location, "nn_icon-wwsyn_icon")
        )

    def current_wind_direction(self, location: str) -> float:
        """Return current wind direction."""
        wind_dir = self.current_meteo_data(location, "dd_val")
        return float(wind_dir) if wind_dir else None

    def current_wind_speed(self, location: str) -> float:
        """Return current wind speed."""
        wind_speed = self.current_meteo_data(location, "ff_val")
        return float(wind_speed) if wind_speed else None

    def current_precipitation(self, location: str) -> float:
        """Return current precipitation."""
        precipitation = self.current_meteo_data(location, "tp_12h_acc")
        return float(precipitation) if precipitation else None

    def current_visibility(self, location: str) -> float:
        """Return current visibility."""
        visibility = self.current_meteo_data(location, "vis_val")
        return float(visibility) if visibility else None

    def current_meteo_data(self, location: str, data_type: str) -> str:
        """Return temperature of the location."""
        meteo_data_location = next(
            (
                item
                for item in self._meteo_data_all
                if item["domain_longTitle"] == location
            ),
            None,
        )
        return None if meteo_data_location is None else meteo_data_location[data_type]

    def list_of_locations(self) -> list:
        """Return list of possible locations."""
        list_of_locations = []
        for meteo_data_location in self._meteo_data_all:
            list_of_locations.append(meteo_data_location["domain_longTitle"])
        return list_of_locations

    def list_of_forecast_regions(self) -> list:
        """Return list of possible forecast regions."""
        list_of_regions = []
        for meteo_data_region in self._meteo_fc_data_all:
            list_of_regions.append(meteo_data_region["domain_shortTitle"])
        return list(set(list_of_regions))  # Using set to remove duplicate entries

    def fc_list_of_dates(self, region) -> list:
        """Return list of dates in the forecast data."""
        decoded_dates = []
        raw_list_of_dates = self.fc_list_of_meteo_data(region, "valid_UTC")
        for date in raw_list_of_dates:
            decoded_dates.append(
                datetime.strptime(date, "%d.%m.%Y %H:%M UTC").isoformat() + "Z"
            )
        return decoded_dates

    def fc_list_of_min_temps(self, region) -> list:
        """Return list of temperatures in the forecast data."""
        return self.fc_list_of_meteo_data(region, "tnsyn")

    def fc_list_of_max_temps(self, region) -> list:
        """Return list of temperatures in the forecast data."""
        return self.fc_list_of_meteo_data(region, "txsyn")

    def fc_list_of_temps(self, region) -> list:
        """Return list of temperatures (avg/apparent) in the forecast data."""
        return self.fc_list_of_meteo_data(region, "t")

    def fc_list_of_condtions(self, region) -> list:
        """Return list of dates in the forecast data."""
        decoded_conditions = []
        raw_list_of_conditions = self.fc_list_of_meteo_data(
            region, "nn_icon-wwsyn_icon"
        )
        for condition in raw_list_of_conditions:
            decoded_conditions.append(self._decode_meteo_condition(condition))
        return decoded_conditions

    def fc_list_of_humidities(self, region) -> list:
        """Return list of humidities in the forecast data."""
        return self.fc_list_of_meteo_data(region, "rh")

    def fc_list_of_presures(self, region) -> list:
        """Return list of presures in the forecast data."""
        return self.fc_list_of_meteo_data(region, "msl")

    def fc_list_of_dew_points(self, region) -> list:
        """Return list of dew points in the forecast data."""
        return self.fc_list_of_meteo_data(region, "td")

    def fc_list_of_wind_speeds(self, region) -> list:
        """Return list of wind speeds in the forecast data."""
        return self.fc_list_of_meteo_data(region, "ff_val")

    def fc_list_of_wind_gusts(self, region) -> list:
        """Return list of wind gusts in the forecast data."""
        return self.fc_list_of_meteo_data(region, "ffmax_val")

    def fc_list_of_wind_bearing(self, region) -> list:
        """Return list of wind bearings in the forecast data."""
        return self.fc_list_of_meteo_data(region, "dd_decodeText")

    def fc_list_of_meteo_data(self, region: str, data_type: str) -> list:
        """Return list of forcast data for specific region."""
        meteo_data_region = []
        regional_fc_data = [
            item
            for item in self._meteo_fc_data_all
            if item["domain_shortTitle"] == region
        ]
        for data in regional_fc_data:
            meteo_data_region.append(data[data_type])
        return meteo_data_region


class DHMZApiClient:
    """Sample API Client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session

    async def async_get_data(self) -> any:
        """Get data from the API."""
        # pylint: disable=line-too-long
        meteo_data_xml = await self._api_wrapper(
            method="get",
            url="https://meteo.DHMZ.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_si_latest.xml",
        )
        meteo_forecast_xml = await self._api_wrapper(
            method="get",
            url="https://meteo.DHMZ.gov.si/uploads/probase/www/fproduct/text/sl/forecast_si_latest.xml",
        )
        return DHMZMeteoData(meteo_data_xml, meteo_forecast_xml)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                if response.status in (401, 403):
                    raise DHMZApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.text()

        except asyncio.TimeoutError as exception:
            raise DHMZApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise DHMZApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise DHMZApiClientError("Something really wrong happened!") from exception
