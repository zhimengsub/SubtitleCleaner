from pathlib import Path
from addict import Dict

import utils.jsonlib as json
from utils.const import PATHS


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
        ),
        symbols=Dict(
            remove='…。｡！!？?~～∼・♪≫《》<>＜＞〈〉',
            replace_key='、､',
            replace_val='  ',
        ),
        # remove 注音假名
        remove_rubi=True,
        # remove format tags that are enclosed in '{}'
        remove_format_tags=True,
        # remove_comments: remove (...) format
        remove_comments=True,
        convert_width=True,
        # add '\N' at each line's start
        add_newline_prefix=True,
        # if line contain 1 digit, to full-width, otherwise all digits to half-with
        format_digit=True,
    )

    if path.is_file():
        with path.open('r', encoding='utf8') as f:
            read = Dict(json.load(f))
        conf.update(read)
    else:
        path.touch()
    saveConfigs(path, conf)
    return conf


def saveConfigs(path: Path, conf: Dict):
    with path.open('w', encoding='utf8') as f:
        json.dump(conf.to_dict(), f, indent=4, ensure_ascii=False)


conf = loadConfigs(PATHS.CONF)

if __name__ == '__main__':
    print(conf)
