import datetime
from typing import Optional

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from .pvoutput import PVOutput


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

    @intent_handler(IntentBuilder("Energy Generated Today").require("Energy").require("Generated").optionally("Today"))
    def energy_generated_today(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        generated_watt_hours = pvo.get_status().energy_generation
        self.speak_dialog("energy.generated.today", data={"amount": generated_watt_hours / 1000.0})

    @intent_handler(IntentBuilder("Energy Generated Yesterday").require("Energy").require("Generated")
                    .require("Yesterday"))
    def energy_generated_yesterday(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        generated_watt_hours = pvo.get_status(date=datetime.datetime.today().date() - datetime.timedelta(days=1)).energy_generation
        self.speak_dialog("energy.generated.yesterday", data={"amount": generated_watt_hours / 1000.0})

    @intent_handler(IntentBuilder("Energy Used Today").require("Energy").require("Used").optionally("Today"))
    def energy_used_today(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        generated_watt_hours = pvo.get_status().energy_consumption
        self.speak_dialog("energy.used.today", data={"amount": generated_watt_hours / 1000.0})

    @intent_handler(IntentBuilder("Energy Used Yesterday").require("Energy").require("Used").require("Yesterday"))
    def energy_used_yesterday(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        generated_watt_hours = pvo.get_status(date=datetime.datetime.today().date() - datetime.timedelta(days=1)).energy_consumption
        self.speak_dialog("energy.used.yesterday", data={"amount": generated_watt_hours / 1000.0})

    @intent_handler(IntentBuilder("Power Generating Now").require("Power").require("Generating").optionally("Now"))
    def power_generating_now(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        generating_watts = pvo.get_status().power_generation
        self.speak_dialog("power.generating.now", data={"amount": generating_watts / 1000.0})

    @intent_handler(IntentBuilder("Power Using Now").require("Power").require("Using").optionally("Now"))
    def power_using_now(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        using_watts = pvo.get_status().power_consumption
        self.speak_dialog("power.using.now", data={"amount": using_watts / 1000.0})

    @intent_handler(IntentBuilder("Peak Power Today").require("PeakPower").optionally("Today"))
    def peak_power_today(self, message):
        pvo = self.get_pvoutput()
        if not pvo:
            return
        status = pvo.get_status(day_statistics=True)
        peak_power = status.standard.peak_power
        time: datetime.time = status.standard.peak_power_time
        self.speak_dialog("peak.power.today", data={"amount": peak_power / 1000.0, "time": self.time_to_str(time)})


def create_skill():
    return PVOutputSkill()
