import datetime
import urllib.parse
from collections import namedtuple
from typing import Optional

import httplib2

"""
Welcome to my PVOutput API for Python. This api is just useful for getting data from pvoutput.org and is not
meant to send data to pvoutput.org. If you want to use this in your project, feel free to copy this file into
your own project and keep this comment block

retrodaredevil
"""

DayStatisticsStandard = namedtuple("DayStatisticsStandard",
                                   "energy_generation power_generation peak_power peak_power_time")
DayStatisticsOwner = namedtuple("DayStatisticsOwner",
                                "energy_consumption power_consumption standby_power standby_power_time")
DayStatisticsTemperature = namedtuple("DayStatisticsTemperature",
                                      "temperature_min temperature_max temperature_average")
DayStatistics = namedtuple("DayStatistics", "standard owner temperature")

HistoryStatus = namedtuple("HistoryStatus", "date time energy_generation energy_efficiency instantaneous_power "
                                            "average_power normalised_output energy_consumption power_consumption "
                                            "temperature voltage extended_values")

GetStatus = namedtuple("GetStatus", "date time energy_generation power_generation energy_consumption power_consumption "
                                    "normalised_output temperature voltage extended_values")


def to_pvoutput_time(time: datetime.time):
    return time.strftime("%H:%M")


def from_pvoutput_time(time: str):
    return datetime.datetime.strptime(time, "%H:%M").time()


def to_pvoutput_date(date: datetime.date):
    return date.strftime("%Y%m%d")


def from_pvoutput_date(date: str):
    return datetime.datetime.strptime(date, "%Y%m%d").date()


class PVOutputException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)


class UnauthorizedPVOutputException(PVOutputException):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)


class PVOutput:
    def __init__(self, system_id: int, api_key: str, host: str = "https://pvoutput.org"):
        self.__system_id = int(system_id)
        self.__api_key = "" + api_key
        self.__host = "" + host
        self.debug = False

    def _send(self, method, path, params):
        h = httplib2.Http()
        # httplib2.debuglevel = 1
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Accept": "text/plain",
            "X-Pvoutput-Apikey": self.__api_key,
            "X-Pvoutput-SystemId": str(self.__system_id)
        }
        uri = urllib.parse.urljoin(self.__host, path)
        if params:
            uri += "?" + urllib.parse.urlencode(params)
        (response, content) = h.request(uri=uri, method=method, headers=headers)
        if self.debug:
            print((response, content))
        return response, content.decode("utf-8")

    def get_status(self, date: datetime.date = None, time: datetime.time = None,
                   history: bool = False, ascending: bool = False, limit: int = None,
                   time_from: datetime.time = None, time_to: datetime.time = None,
                   extended_data: bool = False, system_id: Optional[bool] = None,
                   day_statistics: bool = False):
        params = {}
        if date:
            params["d"] = to_pvoutput_date(date)
        if time:
            params["t"] = to_pvoutput_time(time)
        if history:
            params["h"] = "1"
        if ascending:
            params["asc"] = "1"
        if limit:
            params["limit"] = str(limit)
        if time_from:
            params["from"] = to_pvoutput_time(time_from)
        if time_to:
            params["to"] = to_pvoutput_time(time_to)
        if extended_data:
            params["ext"] = "1"
        if system_id:
            params["sid1"] = str(system_id)
        if day_statistics:
            params["stats"] = "1"

        (response, content) = self._send("GET", "service/r2/getstatus.jsp", params)
        status = int(response.status)
        if status == 401:
            raise UnauthorizedPVOutputException(content)
        elif status != 200:
            raise PVOutputException(content)
        if day_statistics:
            split_content = [a.split(",") for a in content.split(";")]
            standard_content = split_content[0]
            owner_content = None
            temperature_content = None
            if len(split_content) == 2:
                if len(split_content[1]) == 4:
                    owner_content = split_content[1]
                else:
                    temperature_content = split_content[1]
            elif len(split_content) >= 3:
                owner_content = split_content[1]
                temperature_content = split_content[2]

            (energy_generation, power_generation, peak_power, peak_power_time) = standard_content
            standard = DayStatisticsStandard(int(energy_generation), int(power_generation), int(peak_power),
                                             from_pvoutput_time(peak_power_time))
            owner = None
            temperature = None
            if owner_content:
                (energy_consumption, power_consumption, standby_power, standby_power_time) = owner_content
                owner = DayStatisticsOwner(int(energy_consumption), int(power_consumption), int(standby_power),
                                           from_pvoutput_time(standby_power_time))
            if temperature_content:
                (temperature_min, temperature_max, temperature_average) = temperature_content
                temperature = DayStatisticsTemperature(float(temperature_min), float(temperature_max),
                                                       float(temperature_average))

            return DayStatistics(standard, owner, temperature)
        if history:
            split_data = [a.split(",") for a in content.split(";")]
            r = []
            for data in split_data:
                standard_data = data[:11]
                extended_values = None
                if len(data) > 11:
                    extended_values = data[11:]
                (date, time, energy_generation, energy_efficiency, instantaneous_power, average_power,
                 normalised_output, energy_consumption, power_consumption, temperature, voltage) = standard_data
                r.append(HistoryStatus(from_pvoutput_date(date), from_pvoutput_time(time), int(energy_generation),
                                       float(energy_efficiency), int(instantaneous_power), int(average_power),
                                       float(normalised_output),
                                       None if energy_consumption == "NaN" else int(energy_consumption),
                                       None if power_consumption == "NaN" else int(power_consumption),
                                       None if temperature == "NaN" else float(temperature),
                                       None if voltage == "NaN" else float(voltage), extended_values))
            return r

        split = content.split(",")
        standard_data = split[:9]
        extended_values = None
        if len(split) > 9:
            extended_values = split[9:]
        (date, time, energy_generation, power_generation, energy_consumption, power_consumption, normalised_output,
         temperature, voltage) = standard_data
        return GetStatus(from_pvoutput_date(date), from_pvoutput_time(time), int(energy_generation),
                         int(power_generation), int(energy_consumption),
                         int(power_consumption), float(normalised_output),
                         None if temperature == "NaN" else float(temperature),
                         None if voltage == "NaN" else float(voltage), extended_values)

    # TODO getstatistic.jsp
