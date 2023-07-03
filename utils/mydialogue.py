from typing import Union

from ass import Dialogue
from ass_tag_parser import parse_ass, AssText
from utils.mergetype import MergeType

DIALOGUE = Union[Dialogue, 'MyDialogue']


class MyDialogue(Dialogue):
    def __init__(self, event: DIALOGUE, mergetype: MergeType = MergeType.No):
        super().__init__(**event.fields)
        self.mergetype = mergetype

    @property
    def plain_text(self):
        return removed_tags(self.text)


def removed_tags(text: str) -> str:
    arr = parse_ass(text)
    texts = [a.text for a in arr if isinstance(a, AssText)]
    return ''.join(texts)


