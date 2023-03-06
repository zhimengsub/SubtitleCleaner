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
            sep=' ',
            # limit: split merged line every `limit` lines, in case line become too long;
            # 0 is infinite
            limit=2,
            # if `remove_overlap` is True, then join overlapped lines with `sep_on_overlap`
            sep_on_overlap=' ',
        ),
        # remove_comments: remove (...) format
        remove_comments=True,
        remove_overlap=False,
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
        json.dump(conf.to_dict(), f, indent=4)


conf = loadConfigs(PATHS.CONF)

if __name__ == '__main__':
    print(conf)
