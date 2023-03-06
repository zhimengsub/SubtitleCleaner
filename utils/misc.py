import datetime
from copy import deepcopy
from enum import Enum, auto
from functools import reduce
from pathlib import Path
from typing import Literal

import ass
from ass import Dialogue
from ass_tag_parser import parse_ass, AssText

from utils.const import pairs


def mkFilepath(infile: str, filesuf: str, namesuf='') -> Path:
    p = Path(infile)
    newname = p.stem + namesuf + '.' + filesuf.replace('.', '')
    p = p.parent / newname
    return p


class MergeType(Enum):
    No = auto()
    Pair = auto()
    Singlesuf = auto()
    Time = auto()


def removeSFX(event: Dialogue) -> Dialogue:
    arr = parse_ass(event.text)
    texts = [a.text for a in arr if isinstance(a, AssText)]
    event.text = ''.join(texts)
    return event


def overlaps(e1: Dialogue, e2: Dialogue) -> bool:
    return e1.end > e2.start and e2.end > e1.start


def extendEvent(e1: Dialogue, e2: Dialogue, sep: str, ignore_sep_on_pairs=True) -> Dialogue:
    if e2.text:
        # extend end time
        e1.end = e2.end
        # extend text
        if ignore_sep_on_pairs and any(e1.text.endswith(left) or e1.text.endswith(right) or e2.text.startswith(right) for left, right in pairs.items()):
            e1.text = e1.text + e2.text
        else:
            e1.text = e1.text + sep + e2.text
    return e1


def joinEvents(events: list[Dialogue], sep: str, ignore_sep_on_pairs: bool) -> Dialogue:
    joined = reduce(lambda e1, e2: extendEvent(e1, e2, sep, ignore_sep_on_pairs), events)
    return joined


def joinEventsByTime(events: list[Dialogue], sep: str) -> list[Dialogue]:
    if len(events) == 0:
        return events
    base = events[0]
    res = [base]
    for event in events[1:]:
        if overlaps(base, event):
            extendEvent(base, event, sep, ignore_sep_on_pairs=True)
        else:
            base = event
            res.append(base)
    return res


def splitEvents(event: Dialogue, sep: str) -> list[Dialogue]:
    splited_texts = event.text.split(sep)
    events = [deepcopy(event) for _ in range(len(splited_texts))]
    for text, event in zip(splited_texts, events):
        event.text = text
    return events


def save(format: Literal['ass', 'txt'], doc: ass.Document, filepath: Path):
    if format == 'ass':
        with open(filepath, 'w', encoding='utf_8_sig') as f:
            doc.dump_file(f)
    elif format == 'txt':
        with open(filepath, 'w', encoding='utf8') as f:
            for event in doc.events:
                if event.TYPE == 'Dialogue':
                    f.write(event.text)
                    f.write('\n')
    else:
        raise NotImplementedError('不支持的输出文件格式: ' + format)


def formatDelta(delta: datetime.timedelta) -> str:
    formatted = (datetime.datetime.min + delta).strftime('%H:%M:%S.%f')[:-3]
    return formatted
