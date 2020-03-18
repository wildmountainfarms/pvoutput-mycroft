from datetime import datetime
from datetime import timedelta
from typing import Optional

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from .pvoutput import PVOutput


class PVOutputSkill(MycroftSkill):
    def __init__(self):
        super().__init__(name="PVOutput")

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
        pvoutput = self.get_pvoutput()
        if not pvoutput:
            return
        generated_watt_hours = pvoutput.get_status().energy_generation
        self.speak_dialog("energy.generated.today", data={"amount": generated_watt_hours / 1000.0})

    @intent_handler(IntentBuilder("Energy Generated Yesterday").require("Energy").require("Generated")
                    .require("Yesterday"))
    def energy_generated_yesterday(self, message):
        pvoutput = self.get_pvoutput()
        if not pvoutput:
            return
        generated_watt_hours = pvoutput.get_status(datetime.today().date() - timedelta(days=1)).energy_generation
        self.speak_dialog("energy.generated.yesterday", data={"amount": generated_watt_hours / 1000.0})


def create_skill():
    return PVOutputSkill()
