from ass import Dialogue

from utils.misc import MergeType


class MyDialogue(Dialogue):
    def __init__(self, event: Dialogue, mergetype: MergeType):
        super().__init__(**event.fields)
        self.mergetype = mergetype