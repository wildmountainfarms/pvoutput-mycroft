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

Statistic = namedtuple("Statistic",
                       "energy_generated energy_exported average_generation minimum_generation maximum_generation "
                       "average_efficiency outputs actual_date_from actual_date_to record_efficiency record_date "
                       "energy_consumed peak_energy_import off_peak_energy_import shoulder_energy_import "
                       "high_shoulder_energy_import average_consumption minimum_consumption maximum_consumption "
                       "credit_amount debit_amount")


def to_pvoutput_time(time: datetime.time):
    return time.strftime("%H:%M")


def from_pvoutput_time(time: str):
    return datetime.datetime.strptime(time, "%H:%M").time()


def to_pvoutput_date(date: datetime.date):
    return date.strftime("%Y%m%d")


def from_pvoutput_date(date: str):
    return datetime.datetime.strptime(date, "%Y%m%d").date()


class PVOutputException(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoStatusPVOutputException(PVOutputException):
    def __init__(self, message):
        super().__init__(message)


class UnauthorizedPVOutputException(PVOutputException):
    def __init__(self, message):
        super().__init__(message)


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

    @staticmethod
    def _check_response(response, content):
        status = int(response.status)
        if status == 401:
            raise UnauthorizedPVOutputException(content)
        elif status != 200:
            if "No status found" in content:
                raise NoStatusPVOutputException(content)

            raise PVOutputException(content)

    def get_status(self, date: Optional[datetime.date] = None, time: Optional[datetime.time] = None,
                   history: bool = False, ascending: bool = False, limit: Optional[int] = None,
                   time_from: Optional[datetime.time] = None, time_to: Optional[datetime.time] = None,
                   extended_data: bool = False, system_id: Optional[int] = None,
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
        self._check_response(response, content)
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

    def get_statistic(self, date_from: datetime.date = None, date_to: datetime.date = None,
                      consumption_and_import: bool = False, credits_debits: bool = False, system_id: int = None):
        params = {}
        if date_from:
            params["df"] = to_pvoutput_date(date_from)
        if date_to:
            params["dt"] = to_pvoutput_date(date_to)
        if consumption_and_import:
            params["c"] = "1"
        if credits_debits:
            params["crdr"] = "1"
        if system_id:
            params["sid1"] = str(system_id)
        (response, content) = self._send("GET", "service/r2/getstatistic.jsp", params)
        self._check_response(response, content)
        split = content.split(",")
        standard = split[:11]
        (energy_generated, energy_exported, average_generation, minimum_generation, maximum_generation,
         average_efficiency, outputs, actual_date_from, actual_date_to, record_efficiency, record_date) = standard

        extra = split[11:]

        (energy_consumed, peak_energy_import, off_peak_energy_import, shoulder_energy_import,
         high_shoulder_energy_import, average_consumption,
         minimum_consumption, maximum_consumption) = extra[:8] if consumption_and_import else [None] * 8

        (credit_amount, debit_amount) = extra[-2:] if credits_debits else [None] * 2

        return Statistic(int(energy_generated), int(energy_exported), int(average_generation), int(minimum_generation),
                         int(maximum_generation), float(average_efficiency), int(outputs),
                         from_pvoutput_date(actual_date_from), from_pvoutput_date(actual_date_to),
                         float(record_efficiency), from_pvoutput_date(record_date),
                         None if energy_consumed is None else int(energy_consumed),
                         None if peak_energy_import is None else int(peak_energy_import),
                         None if off_peak_energy_import is None else int(off_peak_energy_import),
                         None if shoulder_energy_import is None else int(shoulder_energy_import),
                         None if high_shoulder_energy_import is None else int(high_shoulder_energy_import),
                         None if average_consumption is None else int(average_consumption),
                         None if minimum_consumption is None else int(minimum_consumption),
                         None if maximum_consumption is None else int(maximum_consumption),
                         None if credit_amount is None else float(credit_amount),
                         None if debit_amount is None else float(debit_amount))
