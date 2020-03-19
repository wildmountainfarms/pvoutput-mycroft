import datetime
from typing import Optional

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from mycroft.util.parse import extract_datetime
from mycroft.util.format import nice_date
from .pvoutput import PVOutput, NoStatusPVOutputException


class PVOutputSkill(MycroftSkill):
    def __init__(self):
        super().__init__(name="PVOutput")

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
        today = datetime.date.today()
        days = (today - date).days
        if days == 0:  # today
            return self.translate("today")
        elif days == 1:  # yesterday
            return self.translate("yesterday")
        elif 2 <= days <= 6:
            return self.translate("days.ago", data={"days": days})
        elif days <= 200:
            return ", ".join(nice_date(date).split(", ")[:2])  # the user doesn't care what the year is
        return nice_date(date)

    @staticmethod
    def get_date(message, prefer_past_date=True):
        result = extract_datetime(message.data.get("utterance", ""))
        if result is None:
            return datetime.date.today()
        date = result[0].date()
        if prefer_past_date:
            today = datetime.date.today()
            if (date - today).days > 30:  # date is pretty far in the future
                return datetime.date(date.year - 1, date.month, date.day)
        return date

    def handle_errors(self, function, date):
        try:
            function()
        except NoStatusPVOutputException:
            self.speak_dialog("no.status.for.date",
                              {"date": self.translate("today") if date is None else nice_date(date)})

    @intent_handler(IntentBuilder("Energy Generated").require("Energy").require("Generated").optionally("Solar")
                    .optionally("PVOutput"))
    def energy_generated(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        date = self.get_date(message)

        def function():
            generated_watt_hours = pvo.get_status(date=date).energy_generation
            self.speak_dialog("energy.generated", data={"amount": generated_watt_hours / 1000.0,
                                                        "date": self.format_date(date)})
        self.handle_errors(function, date)

    @intent_handler(IntentBuilder("Energy Used").require("Energy").require("Used").optionally("Solar")
                    .optionally("PVOutput"))
    def energy_used(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        date = self.get_date(message)

        def function():
            consumed_watt_hours = pvo.get_status(date=date).energy_consumption
            self.speak_dialog("energy.used", data={"amount": consumed_watt_hours / 1000.0,
                                                   "date": self.format_date(date)})
        self.handle_errors(function, date)

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
            status = pvo.get_status(date=date, day_statistics=True)
            peak_power = status.standard.peak_power
            time: datetime.time = status.standard.peak_power_time
            self.speak_dialog("peak.power", data={"amount": peak_power / 1000.0, "time": self.time_to_str(time),
                                                  "date": self.format_date(date)})
        self.handle_errors(function, date)


def create_skill():
    return PVOutputSkill()
