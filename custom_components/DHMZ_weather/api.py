"""Sample API Client."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import asyncio
import socket
import aiohttp
import async_timeout

from .const import LOGGER

CONDITION_CLASSES = {
    "clear-night": ["1n"],
    "cloudy": ["5", "6", "5n", "6n"],
    "fog": [
        "7",
        "8",
        "9",
        "10",
        "11",
        "39",
        "40",
        "41",
        "42",
        "7n",
        "8n",
        "9n",
        "10n",
        "11n",
        "39n",
        "40n",
        "41n",
        "42n",
    ],
    "hail": [],
    "lightning": ["15", "25", "29", "15n", "25n", "29n"],
    "lightning-rainy": [
        "16",
        "17",
        "18",
        "30",
        "31",
        "16n",
        "17n",
        "18n",
        "30n",
        "31n",
    ],
    "partlycloudy": ["2", "3", "4", "2n", "3n", "4n"],
    "pouring": ["14", "28", "32", "14n", "28n", "32n"],
    "rainy": ["12", "13", "26", "27", "12n", "13n", "26n", "27n"],
    "snowy": [
        "22",
        "23",
        "24",
        "36",
        "37",
        "38",
        "22n",
        "23n",
        "24n",
        "36n",
        "37n",
        "38n",
    ],
    "snowy-rainy": [
        "19",
        "20",
        "21",
        "33",
        "34",
        "35",
        "19n",
        "20n",
        "21n",
        "33n",
        "34n",
        "35n",
    ],
    "sunny": ["1", "-"],
    "windy": [],
    "windy-variant": [],
    "exceptional": [],
}

# Currently not needed
# But can be used to convert string direction to degrees:
#   WIND_DIRECTION.index(direction) * 22.5
WIND_DIRECTION = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
    "N",
]


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
        forecast_data_3d: str,
        forecast_data_7d: str | None = None,
        forecast_data_today: str | None = None,
        forecast_data_tomorrow: str | None = None,
        sea_temp_data: str | None = None,
    ) -> None:
        """Initialize Meteo data class."""
        self._current_data = current_data
        self._forecast_data_3d = forecast_data_3d
        self._forecast_data_7d = forecast_data_7d
        self._forecast_data_today = forecast_data_today
        self._forecast_data_tomorrow = forecast_data_tomorrow
        self._sea_temp_data = sea_temp_data
        self._meteo_data_all = []
        self._meteo_fc_data_all = []
        self._meteo_sea_data_all = []

        data_selection = [
            "Temp",
            "Vlaga",
            "Tlak",
            "VjetarBrzina",
            "VjetarSmjer",
            "Vrijeme",
            "VrijemeZnak",
        ]

        data_fc_selection = [
            "t_2m",
            "simbol",
            "vjetar",
            "oborina",
        ]

        # Current data processing -> _meteo_data_all
        root = ET.fromstring(current_data)
        for meteo_city_data in root.findall("Grad"):
            meteo_data_location = {}
            meteo_data_location["GradIme"] = meteo_city_data.find("GradIme").text
            meteo_parent = meteo_city_data.find("Podatci")
            for data in data_selection:
                meteo_data_location[data] = meteo_parent.find(data).text
            self._meteo_data_all.append(meteo_data_location)

        # Sea temperature data -> _meteo_sea_data_all
        list_of_hours = []
        root = ET.fromstring(sea_temp_data)
        sea_data_date = root.find("Datum").text
        LOGGER.debug("Datum: %s", str(sea_data_date))
        for count_locations, meteo_sea_data in enumerate(root.findall("Podatci")):
            if count_locations > 0:
                meteo_sea_data_location = {}
                for count, data in enumerate(meteo_sea_data):
                    if count > 0:
                        if data.text is not None:
                            # only last Termin with value is used as this is dictonary
                            meteo_sea_data_location[data.tag] = data.text
                            meteo_sea_data_location["datetime"] = list_of_hours[count]
                    else:
                        meteo_sea_data_location[data.tag] = data.text
                self._meteo_sea_data_all.append(meteo_sea_data_location)
            else:
                for count, data in enumerate(meteo_sea_data):
                    if count > 0:
                        list_of_hours.append(
                            datetime.strptime(
                                (sea_data_date + " " + data.text + ":00 +0200"),
                                "%d.%m.%Y %H:%M %z",
                            ).isoformat()
                        )
        LOGGER.debug("list_of_hours: %s", list_of_hours)
        LOGGER.debug("All data: %s", self._meteo_sea_data_all)

        # 3 Days forecast data processing -> _meteo_fc_data_all
        root = ET.fromstring(forecast_data_3d)
        for meteo_parent in root.findall("grad"):
            city_name = meteo_parent.attrib["ime"]
            for date_data in meteo_parent.findall("dan"):
                meteo_data_region = {}
                meteo_data_region["GradIme"] = city_name
                meteo_data_region["datum"] = date_data.attrib["datum"]
                meteo_data_region["sat"] = date_data.attrib["sat"]
                for data in data_fc_selection:
                    meteo_data_region[data] = date_data.find(data).text
                self._meteo_fc_data_all.append(meteo_data_region)
        # LOGGER.debug("all_data: %s", str(self._meteo_fc_data_all))

    def current_temperature(self, location: str) -> str:
        """Return temperature of the location."""
        return self.current_meteo_data(location, "Temp")

    def current_humidity(self, location: str) -> float:
        """Return humidity of the location."""
        humidity = self.current_meteo_data(location, "Vlaga")
        return float(humidity) if humidity else None

    def current_air_pressure(self, location: str) -> str:
        """Return air pressure of the location."""
        return self.current_meteo_data(location, "Tlak")

    def _decode_meteo_condition(self, description: str) -> str:
        """Decode meteo condition to home assistant condition."""
        try:
            s_ret = [k for k, v in CONDITION_CLASSES.items() if description in v][0]
            return s_ret
        except IndexError:
            LOGGER.warning("Unknown DHMZ weather symbol: %s", description)
            return None

    def current_condition(self, location: str) -> str:
        """Return current condition of the location."""
        return self._decode_meteo_condition(
            self.current_meteo_data(location, "VrijemeZnak")
        )

    def current_wind_direction(self, location: str) -> str:
        """Return current wind direction."""
        wind_dir = self.current_meteo_data(location, "VjetarSmjer")
        return str(wind_dir) if wind_dir else None

    def current_wind_speed(self, location: str) -> float:
        """Return current wind speed."""
        wind_speed = self.current_meteo_data(location, "VjetarBrzina")
        return float(wind_speed) if wind_speed else None

    # def current_precipitation(self, location: str) -> float:
    #    """Return current precipitation."""
    #    precipitation = self.current_meteo_data(location, "tp_12h_acc")
    #    return float(precipitation) if precipitation else None

    # def current_visibility(self, location: str) -> float:
    #    """Return current visibility."""
    #    visibility = self.current_meteo_data(location, "vis_val")
    #    return float(visibility) if visibility else None

    def current_meteo_data(self, location: str, data_type: str) -> str:
        """Return data_type of the location."""
        meteo_data_location = next(
            (item for item in self._meteo_data_all if item["GradIme"] == location),
            None,
        )
        return None if meteo_data_location is None else meteo_data_location[data_type]

    def current_sea_temp_data(self, location: str, data_type: str) -> str:
        """Return sea temperature of the location."""
        meteo_data_location = next(
            (item for item in self._meteo_sea_data_all if item["Postaja"] == location),
            None,
        )
        LOGGER.debug("current_sea_temp_data: %s", meteo_data_location[data_type])
        return None if meteo_data_location is None else meteo_data_location[data_type]

    def list_of_locations(self) -> list:
        """Return list of possible locations."""
        list_of_locations = []
        for meteo_data_location in self._meteo_data_all:
            LOGGER.debug("Location : %s", meteo_data_location["GradIme"])
            list_of_locations.append(meteo_data_location["GradIme"])
        return list_of_locations

    def list_of_forecast_regions(self) -> list:
        """Return list of possible forecast regions."""
        list_of_regions = []
        # Read list of regions for meteo.hr
        for meteo_data_region in self._meteo_fc_data_all:
            list_of_regions.append(meteo_data_region["GradIme"])
        return list(set(list_of_regions))  # Using set to remove duplicate entries

    def list_of_sea_locations(self) -> list:
        """Return list of possible sea temperature locations."""
        list_of_sea_locations = []
        # Read list of regions for meteo.hr
        for meteo_data_sea_location in self._meteo_sea_data_all:
            list_of_sea_locations.append(meteo_data_sea_location["Postaja"])
        return list_of_sea_locations

    def fc_list_of_dates(self, region) -> list:
        """Return list of dates in the forecast data."""
        decoded_dates = []
        raw_list_of_dates = []
        # raw_list_of_dates = self.fc_list_of_meteo_data(region, "datum")
        list_of_dates = self.fc_list_of_meteo_data(region, "datum")
        list_of_times = self.fc_list_of_meteo_data(region, "sat")
        for date in zip(list_of_dates, list_of_times):
            raw_list_of_dates.append(date[0] + " " + date[1] + ":00")
        # LOGGER.debug("ListOfDates: %s", str(raw_list_of_dates))
        for date in raw_list_of_dates:
            decoded_dates.append(
                datetime.strptime(date, "%d.%m.%Y. %H:%M").isoformat() + "Z"
            )
        # LOGGER.debug("ListOfDecodedDates: %s", str(decoded_dates))
        return decoded_dates

    def fc_list_of_min_temps(self, region) -> list:
        """Return list of temperatures in the forecast data."""
        return self.fc_list_of_meteo_data(region, "t_2m")

    def fc_list_of_max_temps(self, region) -> list:
        """Return list of temperatures in the forecast data."""
        return self.fc_list_of_meteo_data(region, "t_2m")

    def fc_list_of_temps(self, region) -> list:
        """Return list of temperatures (avg/apparent) in the forecast data."""
        return self.fc_list_of_meteo_data(region, "t_2m")

    def fc_list_of_condtions(self, region) -> list:
        """Return list of dates in the forecast data."""
        decoded_conditions = []
        raw_list_of_conditions = self.fc_list_of_meteo_data(region, "simbol")
        for condition in raw_list_of_conditions:
            decoded_conditions.append(self._decode_meteo_condition(condition))
        return decoded_conditions

    # def fc_list_of_humidities(self, region) -> list:
    #    """Return list of humidities in the forecast data."""
    #    return self.fc_list_of_meteo_data(region, "rh")

    # def fc_list_of_presures(self, region) -> list:
    #    """Return list of presures in the forecast data."""
    #    return self.fc_list_of_meteo_data(region, "msl")

    # def fc_list_of_dew_points(self, region) -> list:
    #    """Return list of dew points in the forecast data."""
    #    return self.fc_list_of_meteo_data(region, "td")

    def fc_list_of_wind_speeds(self, region) -> list:
        """Return list of wind speeds in the forecast data."""
        return self.fc_list_of_meteo_data(region, "ff_val")

    # def fc_list_of_wind_gusts(self, region) -> list:
    #    """Return list of wind gusts in the forecast data."""
    #    return self.fc_list_of_meteo_data(region, "ffmax_val")

    def fc_list_of_wind_bearing(self, region) -> list:
        """Return list of wind bearings in the forecast data."""
        return self.fc_list_of_meteo_data(region, "dd_decodeText")

    def fc_list_of_meteo_data(self, region: str, data_type: str) -> list:
        """Return list of forcast data for specific region."""
        meteo_data_region = []
        regional_fc_data = [
            item for item in self._meteo_fc_data_all if item["GradIme"] == region
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
        meteo_data_xml = await self._api_wrapper(
            method="get",
            url="https://vrijeme.hr/hrvatska_n.xml",
        )
        meteo_forecast_xml = await self._api_wrapper(
            method="get",
            url="https://prognoza.hr/tri/3d_graf_i_simboli.xml",
        )
        meteo_sea_temp_xml = await self._api_wrapper(
            method="get",
            url="https://vrijeme.hr/more_n.xml",
        )
        return DHMZMeteoData(
            meteo_data_xml, meteo_forecast_xml, sea_temp_data=meteo_sea_temp_xml
        )

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
