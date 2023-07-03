import datetime
import re
from functools import reduce
from pathlib import Path
from typing import Literal

import ass

from utils.mergetype import MergeType
from utils.patterns import pairs
from utils.mydialogue import MyDialogue, DIALOGUE


def mkFilepath(infile: str, filesuf: str, namesuf='') -> Path:
    p = Path(infile)
    newname = p.stem + namesuf + '.' + filesuf.replace('.', '')
    p = p.parent / newname
    return p


def remove_tags(event: MyDialogue) -> MyDialogue:
    event.text = event.plain_text
    return event


def overlaps(e1: DIALOGUE, e2: DIALOGUE) -> bool:
    return e1.end > e2.start and e2.end > e1.start


def extendEvent(
    e1: MyDialogue,
    e2: MyDialogue,
    sep: str,
    sep_on_overlap: str,
    special_prefix: str,
    sep_on_special_prefix: str,
    *,
    ignore_sep_on_pairs=True,
) -> MyDialogue:
    """ignore_sep_on_pairs: do not add sep after left symbol / before end symbol, i.e. `[text]` not `[ text ]`"""
    if e2.text:
        # extend end time
        e1.end = e2.end
        # extend text
        real_sep: str
        if (
            ignore_sep_on_pairs and
            any(e1.text.endswith(left) or e2.text.startswith(right) for left, right in pairs.items())
        ):
            # do not add sep inside pairs, i.e. `[text]` not `[ text ]`
            real_sep = ''
        elif special_prefix and e2.plain_text.startswith(special_prefix):
            real_sep = sep_on_special_prefix
        elif e2.mergetype == MergeType.Time:
            real_sep = sep_on_overlap
        else:
            real_sep = sep

        e1.text = e1.text + real_sep + e2.text
    return e1


def joinEvents(
    events: list[MyDialogue],
    sep: str,
    sep_on_overlap: str,
    *,
    special_prefix: str = '',
    sep_on_special_prefix: str = '',
    ignore_sep_on_pairs: bool,
) -> MyDialogue:
    joined = reduce(
        lambda e1, e2: extendEvent(
            e1, e2, sep,
            sep_on_overlap,
            special_prefix,
            sep_on_special_prefix,
            ignore_sep_on_pairs=ignore_sep_on_pairs,
        ), events)
    return joined


def splitEvents(
    event: MyDialogue,
    sep: str,
    sep_on_overlap: str,
    overlapped_chunk_prefix: str,
) -> list[MyDialogue]:
    # mark a chunk as overlapped, used to restore the mergetype
    text = event.text.replace(sep_on_overlap, sep_on_overlap + overlapped_chunk_prefix)
    events = []
    splited_texts = re.split(sep + '|' + sep_on_overlap, text)
    for chunk in splited_texts:
        mergetype = MergeType.Time if chunk.startswith(overlapped_chunk_prefix) else MergeType.No
        event = MyDialogue(event, mergetype)

        chunk = chunk.replace(overlapped_chunk_prefix, '')
        event.text = chunk
        events.append(event)
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
