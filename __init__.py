import datetime
import calendar
from typing import Optional

from adapt.intent import IntentBuilder
from mycroft import Message
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from mycroft.util.parse import extract_datetime
from mycroft.util.format import nice_date
from .pvoutput import PVOutput, NoStatusPVOutputException, DayStatistics, NoOutputsPVOutputException, \
    InvalidApiKeyPVOutputException


class PVOutputSkill(MycroftSkill):
    def __init__(self):
        super().__init__(name="PVOutput")
        # import httplib2
        # httplib2.debuglevel = 1

    @property
    def use_24hour(self):
        return self.config_core.get('time_format') == 'full'

    def time_to_str(self, time):
        if self.use_24hour:
            return time.strftime("%H:%M")
        return time.strftime("%I:%M %p")

    def get_pvoutput(self) -> Optional[PVOutput]:
        api_key = self.settings.get("api_key")
        system_id = self.settings.get("system_id")
        if api_key and system_id:
            LOG.info("Set up pv output for system id: {}".format(system_id))
            return PVOutput(api_key=api_key, system_id=system_id)
        self.speak_dialog("pvoutput.not.setup")
        LOG.info("No pvoutput setup id: {}".format(system_id))
        return None

    def format_date(self, date: datetime.date):
        return nice_date(datetime.datetime(date.year, date.month, date.day),
                         now=datetime.datetime.now(tz=self.location_timezone))

    def nice_format_period(self, date1, date2):
        if date1 == date2:
            return self.format_date(date1)
        return self.format_period(date1, date2)

    def format_period(self, date1, date2):
        return self.translate("between.dates", data={"date1": self.format_date(date1),
                                                     "date2": self.format_date(date2)})

    def get_date(self, message):
        utterance = message.data.get("utterance", "")
        now = datetime.datetime.now(tz=self.location_timezone)
        today = now.date()
        result = extract_datetime(utterance, anchorDate=now)
        if result is None:
            return today
        date = result[0].date()
        if (date - today).days > 3:  # date is in the future
            result = extract_datetime(utterance, anchorDate=(now - datetime.timedelta(days=365)))
            date = result[0].date()
        return date

    def get_this_week_start_date(self):
        today = datetime.datetime.now(tz=self.location_timezone).date()
        weekday = (today.weekday() + 1) % 7  # TODO only add 1 if that's normal for someone's language/region
        return today - datetime.timedelta(days=weekday)

    def get_period(self, message: Message):
        utterance = message.data.get("utterance", "")
        today = datetime.datetime.now(tz=self.location_timezone).date()
        start = None
        end = None
        if self.voc_match(utterance, "LastMonth"):
            if today.month == 1:
                start = datetime.date(today.year - 1, 12, 1)
            else:
                start = datetime.date(today.year, today.month - 1, 1)
            end = datetime.date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
        elif self.voc_match(utterance, "ThisMonth"):
            start = datetime.date(today.year, today.month, 1)
            end = today
        elif self.voc_match(utterance, "LastYear"):
            start = datetime.date(today.year - 1, 1, 1)
            end = datetime.date(today.year - 1, 12, 31)
        elif self.voc_match(utterance, "ThisYear"):
            start = datetime.date(today.year, 1, 1)
            end = today
        elif self.voc_match(utterance, "LastWeek"):
            start = self.get_this_week_start_date() - datetime.timedelta(days=7)
            end = start + datetime.timedelta(days=6)
        elif self.voc_match(utterance, "ThisWeek"):
            start = self.get_this_week_start_date()
            end = start + datetime.timedelta(days=6)

        if not start:
            return None
        return start, end

    def handle_errors(self, function, date_string):
        date_string = date_string or self.format_date(datetime.datetime.now(tz=self.location_timezone).date())
        try:
            function()
        except (NoStatusPVOutputException, NoOutputsPVOutputException) as e:
            LOG.info(e)
            self.speak_dialog("no.status.for.date", {"date": date_string})
        except InvalidApiKeyPVOutputException as e:
            LOG.info(e)
            self.speak_dialog("invalid.api.key")

    def process_message_for_statistic(self, message, process_statistic, consumption_and_import=False):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        period = self.get_period(message)
        if not period:
            date = self.get_date(message)
            period = (date, date)

        def period_function():
            statistic = pvo.get_statistic(date_from=period[0], date_to=period[1],
                                          consumption_and_import=consumption_and_import)
            date_string = self.nice_format_period(statistic.actual_date_from, statistic.actual_date_to)
            process_statistic(statistic, date_string)
        self.handle_errors(period_function, self.nice_format_period(period[0], period[1]))

    @intent_handler(IntentBuilder("Energy Generated").require("Energy").require("Generated").optionally("Solar")
                    .optionally("PVOutput"))
    def energy_generated(self, message):
        def process_statistic(statistic, date_string):
            generated_watt_hours = statistic.energy_generated
            self.speak_dialog("energy.generated", data={"amount": generated_watt_hours / 1000.0, "date": date_string})
        self.process_message_for_statistic(message, process_statistic)

    @intent_handler(IntentBuilder("Energy Used").require("Energy").require("Used").optionally("Solar")
                    .optionally("PVOutput"))
    def energy_used(self, message):
        def process_statistic(statistic, date_string):
            consumed_watt_hours = statistic.energy_consumed
            self.speak_dialog("energy.used", data={"amount": consumed_watt_hours / 1000.0, "date": date_string})
        self.process_message_for_statistic(message, process_statistic, consumption_and_import=True)

    @intent_handler(IntentBuilder("Power Generating Now").require("Power").require("Generating").optionally("Now")
                    .optionally("Solar").optionally("PVOutput"))
    def power_generating_now(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return

        def function():
            generating_watts = pvo.get_status().power_generation
            self.speak_dialog("power.generating.now", data={"amount": generating_watts / 1000.0})
        self.handle_errors(function, None)

    @intent_handler(IntentBuilder("Power Using Now").require("Power").require("Using").optionally("Now")
                    .optionally("Solar").optionally("PVOutput"))
    def power_using_now(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return

        def function():
            using_watts = pvo.get_status().power_consumption
            self.speak_dialog("power.using.now", data={"amount": using_watts / 1000.0})
        self.handle_errors(function, None)

    @intent_handler(IntentBuilder("Peak Power").require("PeakPower").optionally("Solar").optionally("PVOutput"))
    def peak_power(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        date = self.get_date(message)

        def function():
            status: DayStatistics = pvo.get_status(date=date, day_statistics=True)
            peak_power = status.standard.peak_power
            time: datetime.time = status.standard.peak_power_time
            self.speak_dialog("peak.power", data={"amount": peak_power / 1000.0, "time": self.time_to_str(time),
                                                  "date": self.format_date(date)})
        self.handle_errors(function, self.format_date(date))


def create_skill():
    return PVOutputSkill()
