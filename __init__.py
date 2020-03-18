from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from pvoutput import PVOutput


class PVOutputSkill(MycroftSkill):
    def __init__(self):
        super().__init__(name="PVOutput")
        
    @intent_handler(IntentBuilder("").require("Hello").require("World"))
    def handle_hello_world_intent(self, message):
        self.speak_dialog("hello.world")


def create_skill():
    return PVOutputSkill()
