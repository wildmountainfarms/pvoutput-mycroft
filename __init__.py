from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from pvoutput import PVOutput


class PVOutputSkill(MycroftSkill):
    def __init__(self):
        super().__init__(name="PVOutput")

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.on_settings_changed()

    def on_settings_changed(self):
        pass
        
    @intent_handler(IntentBuilder("").require("Hello").require("World"))
    def handle_hello_world_intent(self, message):
        self.speak_dialog("hello.world")


def create_skill():
    return PVOutputSkill()
