import re
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
        return removed_tags(removed_color(self.text))


def removed_color(text: str) -> str:
    '''当`\$c`特效不符合&Hxxxxxx&格式时，ass_tag_parser.parse_ass会报错，因此提前删掉这类特效'''
    text = re.sub(r'\\[1-4]?c[&Hh0-9a-fA-F]+?([\\}])', r'\1', text)
    return text


def removed_tags(text: str) -> str:
    arr = parse_ass(text)
    texts = [a.text for a in arr if isinstance(a, AssText)]
    return ''.join(texts)


