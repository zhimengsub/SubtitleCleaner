from pathlib import Path
from typing import Optional

from addict import Dict

import utils.jsonlib as json
from utils.patterns import load_patterns_from_conf


def update_from(base: dict, new: dict):
    for key in base.keys():
        if key in new:
            if isinstance(base[key], dict) and isinstance(new[key], dict):
                update_from(base[key], new[key])  # Recursively update nested dicts
            else:
                base[key] = new[key]  # Update values for non-dict keys


def loadConfigs(path: Path) -> Dict:
    conf = Dict(
        format='ass',  # choices: ['ass', 'txt']
        merge=Dict(
            pair=True,
            singlesuf=True,
            time=False,
            # limit: split merged line every `limit` lines, in case line become too long;
            # 0 is infinite
            limit=2,
            # True to ensure no overlap
            ignore_limit_on_overlap=False,
            sep=' ',
            # if merge.time is True, then join overlapped lines with `sep_on_overlap`
            sep_on_overlap=' ',
            # special prefix for sep_on_special_prefix
            special_prefix='',
            # if overlapped line has the above prefix, then use another sep
            # (usually a break line for a different speaker)
            sep_on_special_prefix=r'\N',
            # 标志合并的符号对
            merge_pairs_left='《<＜〈「｢『(（[［',
            merge_pairs_right='》>＞〉」｣』)）]］',
            # 标志合并的后缀符号
            merge_suffix='→➡',
        ),
        symbols=Dict(
            remove='。｡！!？?~～∼・♪≫《》<>＜＞〈〉',
            replace_key='、､⚟',
            replace_val='   ',
        ),
        texts=Dict(
            replace=Dict({
                # replace key with val
                'ウソ': '嘘',
                'イヤ': '嫌',
                'ダメ': 'だめ',
                'ヤツ': '奴',
                'ジャマ': '邪魔',
                'ケンカ': '喧嘩',
                'ホント': '本当',
            }),
        ),
        # remove 注音假名
        remove_rubi=True,
        # remove format tags that are enclosed in '{}'
        remove_format_tags=True,
        # remove_comments: remove (...) format
        remove_comments=True,
        # remove speaker name, 规则为从行首开始全是片假名，跟一个冒号。如果说话人在句中则处理不了 see pats_speaker
        remove_speaker=True,
        convert_width=True,
        # add '\N' at each line's start
        add_newline_prefix=True,
        # if line contain 1 digit, to full-width, otherwise all digits to half-with
        format_digit=True,
        # 在Actor栏标注时间重叠的条目
        mark_overlap=True,
        # 均分为多个部分，每段的开始标注在Actor栏，方便分工（置0表示关闭功能）
        mark_segment=3,
    )

    if path.is_file():
        with path.open('r', encoding='utf8') as f:
            read = Dict(json.load(f))
        update_from(conf, read)
    else:
        path.touch()
    saveConfigs(path, conf)
    load_patterns_from_conf(conf)
    return conf


def saveConfigs(path: Path, conf: Dict):
    with path.open('w', encoding='utf8') as f:
        json.dump(conf.to_dict(), f, indent=4, ensure_ascii=False)


conf: Optional[Dict] = None
