import datetime
import os
import traceback
from argparse import RawTextHelpFormatter
from copy import deepcopy
from typing import Optional

import ass
from ass import Dialogue

from FullwidthConverter import convertline, lookup
from utils.argparser import MyParser
from utils.const import *
from utils.logfile import _print, setLogfile, closeLogfile, print, warning, error
from utils.misc import mkFilepath, remove_tags, overlaps, save, formatDelta, joinEvents, splitEvents
from utils.mergetype import MergeType
from utils.conf import loadConfigs, conf
from utils.mydialogue import MyDialogue
from utils.patterns import pairs, singlesufs, pats_stripsuf, pats_rm, pats_rmcomment, pats_rmpairs, pats_prefix, \
    pats_final, pats_speaker

VER = 'v3.0.9'

DESCRIPTION = '字幕清理器\n' + \
              '对ts源中提取出的ass字幕进行处理，包括合并多行对白、清理各种不必要的符号、说话人备注、转换假名半角等，输出ass或txt\n' + \
              '—— ' + VER + ' by 谢耳朵w\n\n' + \
              '使用方法：将待转换文件拖放到本程序上即可，也可以使用命令行运行进行更多配置。\n\n' + \
              '详细介绍、获取最新版本、提交bug请前往 https://github.com/zhimengsub/SubtitleCleaner'


def initparser():
    parser = MyParser(description=DESCRIPTION, formatter_class=RawTextHelpFormatter)
    parser.add_argument('InputFile', type=str, help='待转换ass文件的路径。', default='', nargs='?')
    parser.add_argument('-o', '--output', type=str, help='输出文件路径，默认为<输入文件名>_cleaned。')
    parser.add_argument('-q', '--quit', action='store_true', help='结束后不暂停程序直接退出，方便命令行调用。不加该参数程序结束时会暂停。')
    parser.add_argument('--offsetms', type=int, default=0, help='输出ass整体时间偏移毫秒数，负数为提前，正数为延后。')
    parser.add_argument('--log', action='store_true', help='记录日志，日志存储到同目录下的<输入文件名>_log.txt。')
    parser.add_argument('--config', '-c', type=str, help='配置文件路径，默认为当前目录下的config.json。')
    return parser


def cleanEvent(event:Dialogue, pats:list[tuple[re.Pattern, str]]):
    text = event.text
    for pat, repl in pats:
        text = pat.sub(repl, text)
    text = text.strip(' 　' + MERGE_SEP)  # 清理两边多余的半角和全角空格和分隔符
    event.text = text


def format_digit(event: Dialogue):
    text = event.text
    digit_count = len(re.findall(r'\d', text))
    if digit_count == 1:
        # 一位数字替换成全角
        text = re.sub(r'\d', lambda x: to_fullwidth.get(x.group(), x.group()), text)
    elif digit_count > 1:
        # 多位数字换成半角
        out = ''
        for c in text:
            out += to_halfwidth.get(c, c)
        text = out
    event.text = text


def findMergeStart(event: MyDialogue, ignored_mergetypes: list[MergeType]) -> tuple[MergeType, str]:
    """
    :returns: mergetype and matched symbol
    """
    if conf.merge.pair and MergeType.Pair not in ignored_mergetypes:
        for pairleft in pairs:
            if pairleft in event.plain_text:
                return MergeType.Pair, pairleft

    if conf.merge.singlesuf and MergeType.Singlesuf not in ignored_mergetypes:
        for suf in singlesufs:
            if event.plain_text.endswith(suf):
                return MergeType.Singlesuf, suf

    if conf.merge.time and MergeType.Time not in ignored_mergetypes:
        return MergeType.Time, ''

    return MergeType.No, ''


def findMergeEnd(events: list[Dialogue],
                 start: int,
                 mergetype: MergeType,
                 symb: str='') -> tuple[int, str]:
    """
    symb: merge symbol to look for
    :returns: end index that should be merged; merge reason, or warning msg if end index == -1
    """
    if mergetype == MergeType.Pair:
        j = start
        reason = pairs.inv[symb] + '...' + symb

        while j < len(events) and symb not in events[j].text:
            j += 1

        if j == len(events):
            # error
            reason = '仅匹配到' + pairs.inv[symb] + '，请确认左右括号个数一致！'
            return -1, reason
        return j, reason

    elif mergetype == MergeType.Singlesuf:
        j = start + 1
        reason = symb

        while j < len(events) - 1 and events[j].text.endswith(symb):
            # 如果j是数组最后一个，不论是否还以symb结尾，都直接返回
            j += 1

        return j, reason

    elif mergetype == MergeType.Time:
        j = start + 1
        reason = '时间重合'

        while j < len(events) and overlaps(events[j-1], events[j]):
            j += 1

        # j-1是最后一个有时间重合的
        return j-1, reason

    else:
        raise NotImplementedError('Unexpected mergetype ' + str(mergetype))


def findMergeInterval(events: list[MyDialogue], start: int, ignored_mergetypes: list[MergeType]) -> tuple[int, str, MergeType]:
    """
    :returns: end index of merged events; merge reason (or warning msg if end index == -1); Mergetype
    """
    eventL = events[start]
    mergetype, symb = findMergeStart(eventL, ignored_mergetypes)

    reason = ''
    if mergetype == MergeType.No:
        return start, reason, MergeType.No

    if mergetype == MergeType.Pair:
        symbR = pairs[symb]
        end, reason = findMergeEnd(events, start, mergetype, symbR)
    else:
        end, reason = findMergeEnd(events, start, mergetype, symb)

    return end, reason, mergetype


def mergeEvents(
    events: list[MyDialogue],
    start: int,
    limit: int,
    procid: int,
    warnings: list,
    log_reason: list,
    ignore_limit_on_overlap: bool,
) -> tuple[int, list[Dialogue]]:
    """
    returns: end index of merged events; merged events; start and end index of each merged event
    """
    merge_list: list[MyDialogue] = [events[start]]  # 所有需要合并的对白
    start_ = start
    ignored_mergetypes = []  # 不考虑的mergetype
    while True:
        # 考虑到存在下一行时间仍相同，或者出现新的标识符的情况，故不断搜索直到没有合并的情况
        end, reason, mergetype = findMergeInterval(events, start_, ignored_mergetypes)

        if end == -1:
            warning(reason)
            warnings.append((procid, reason))
            end = start_

        if end == start_:
            # 只有MergeType.No或MergeType.Pair时才会出现此情况，
            # 后者时应考虑存在其他的mergetype，故需要排除掉pair后continue
            if mergetype == MergeType.No:
                break
            ignored_mergetypes.append(mergetype)
            continue

        log_reason.append(reason)
        merge_list.extend(MyDialogue(event, mergetype) for event in events[start_+1:end+1])
        start_ = end

    for event in merge_list:
        # 清理合并标志符号
        cleanEvent(event, pats_stripsuf)
        # 清理各种符号
        cleanEvent(event, pats_rm)

    # clean format_tags (remove all or only keep the first one)
    events_need_remove_tags = (merge_list if conf.remove_format_tags else merge_list[1:])
    for event in events_need_remove_tags:
        remove_tags(event)

    # 1.合并后清理，2.再拆开，3.然后再每隔limit个用conf.merge.sep合并在一起
    # 1.
    merged = joinEvents(
        merge_list,
        sep=MERGE_SEP,
        sep_on_overlap=MERGE_SEP_ON_OVERLAP,
        ignore_sep_on_pairs=False
    )
    cleanEvent(merged, pats_rmpairs)
    if conf.remove_comments:
        cleanEvent(merged, pats_rmcomment)
    # 2.
    merge_list_cleaned = splitEvents(
        merged,
        sep=MERGE_SEP,
        sep_on_overlap=MERGE_SEP_ON_OVERLAP,
        overlapped_chunk_prefix=OVERLAPPED_CHUNK_PREFIX
    )
    # 3.
    merged_events = []
    limit = len(merge_list_cleaned) if limit <= 0 else limit
    if ignore_limit_on_overlap:
        limit = len(merge_list_cleaned)
    for i in range(0, len(merge_list_cleaned), limit):
        joined = joinEvents(
            merge_list_cleaned[i: i+limit],
            sep=conf.merge.sep,
            sep_on_overlap=conf.merge.sep_on_overlap,
            special_prefix=conf.merge.special_prefix,
            sep_on_special_prefix=conf.merge.sep_on_special_prefix,
            ignore_sep_on_pairs=True
        )
        merged_events.append(joined)
    return end, merged_events


def processDoc(doc: ass.Document,
               lookup: dict,
               offsetms: datetime.timedelta) -> ass.Document:

    events_old = [None] * len(doc.events)  # type: list[Optional[Dialogue]]
    for i, event in enumerate(doc.events):
        if event.TYPE == 'Dialogue':
            # add plain_text field for easier merge finding
            doc.events[i] = MyDialogue(doc.events[i])
            # record old event for logging
            events_old[i] = deepcopy(event)

    warnings = []
    events_out = []
    cnter_mg = 0
    cnter_ono = 0
    cnter_cv = 0
    procid = 0  # number of processed lines
    outid = 0  # line number of output
    print('\n开始处理字幕...\n')
    i = 0  # event index
    while i < len(doc.events):
        # filter out non Dialogue and non rubi
        if doc.events[i].TYPE != 'Dialogue' or (doc.events[i].style.lower() == 'rubi' and conf.remove_rubi):
            if doc.events[i].style.lower() == 'rubi':
                print('[跳过Rubi台词]')
                print(doc.events[i].text)
                print()

            i += 1
            continue

        procid += 1

        # reason = ''
        # 清理语气词 # TODO 开关
        # tmp = nline
        # nline = cleanline(nline, pats_ono)
        # if nline != tmp:
        #     reason = '[清理语气词]'
        #     print(reason)
        #     cnter_ono += 1

        # merge and clean lines
        # end, reason = findMergeInterval(doc.events, i)
        if not doc.events[i].text:
            time_start = formatDelta(events_old[i].start)
            time_end = formatDelta(events_old[i].end)
            text = events_old[i].text
            print(f'{procid}.\n'+time_start, time_end, text, '\n->\n<删除>')
            print()
            i += 1
            continue

        log_reason = []
        if doc.events[i].style.lower() == 'rubi':
            # don't merge rubi
            end, merged_events = i, [doc.events[i]]
        else:
            # merged_events包含了从第i个开始所有要合并的event
            end, merged_events = mergeEvents(
                doc.events,
                i,
                conf.merge.limit,
                procid,
                warnings,
                log_reason,
                conf.merge.ignore_limit_on_overlap
            )
        if end != i:
            cnter_mg += end - i + 1

        print(f'{procid}.', ' '.join(log_reason))

        # 这里得到的是已经合并了的event，只不过根据limit又进行了分隔
        for event in merged_events:
            # convert half-width katakana and symbols
            if conf.convert_width:
                converted = convertline(event.text, lookup)
                if converted != event.text:
                    event.text = converted
                    reason = '[转换假名]'
                    print(reason)
                    cnter_cv += 1

            # post process
            # 删除说话人
            if conf.remove_speaker:
                cleanEvent(event, pats_speaker)
            # 处理数字
            if conf.format_digit:
                format_digit(event)
            # 添加\N
            if conf.add_newline_prefix:
                cleanEvent(event, pats_prefix)

            cleanEvent(event, pats_final)

            event.start += offsetms
            event.end += offsetms

        tmp = []
        for ind in range(i, end + 1):
            time_start = formatDelta(events_old[ind].start)
            time_end = formatDelta(events_old[ind].end)
            text = events_old[ind].text
            tmp.append((time_start, time_end, text))
        print(' +\n'.join([time_start + ' ' + time_end + ' ' + text for time_start, time_end, text in tmp]))
        print('->')

        for event in merged_events:
            if event.text and event.text != '\\N':
                outid += 1
                time_start = formatDelta(event.start)
                time_end = formatDelta(event.end)
                text = event.text
                print(f'[{outid}]', time_start, time_end, text)
                events_out.append(event)
            else:
                print('<删除>')

        print()
        i = end + 1

    # 在"actor"栏标注时间重叠情况
    overlap_id = 0
    if conf.mark_overlap:
        i = 0
        while i < len(events_out) - 1:
            overlap_end = i
            while overlaps(events_out[overlap_end], events_out[overlap_end+1]):
                overlap_end += 1
            if overlap_end != i:
                overlap_id += 1
                for j in range(i, overlap_end+1):
                    events_out[j].name += '重叠' + str(overlap_id)
            i = overlap_end + 1

    print('处理完成！共合并了', cnter_mg, '行文本，清理了', cnter_ono, '行对白的语气词，转换了', cnter_cv, '行对白的假名，存在', overlap_id, '处时间重叠，最终生成了', outid, '行对白。')

    if warnings:
        print('\n存在WARNING，请根据下方信息向上查找对应记录')
        for procid, msg in warnings:
            print(f'{procid}.', msg)

    doc.events = events_out
    return doc


if __name__ == '__main__':
    global conf
    parser = initparser()
    args = parser.parse_args()
    offsetms = datetime.timedelta(milliseconds=args.offsetms)
    try:
        print(DESCRIPTION)
        print()
        assert args.config is None or Path(args.config).is_file(), '传入的配置文件不存在：' + str(Path(args.config).absolute())
        args.config = Path(args.config) if args.config else PATHS.CONF
        conf = loadConfigs(args.config)
        print('已更新配置文件到', args.config)
        print()

        assert Path(args.InputFile).is_file(), '输入文件不存在：' + str(Path(args.InputFile).absolute())

        if args.log:
            logpath = mkFilepath(args.InputFile, '.txt', '_log')
            setLogfile(logpath)

        print('正在读取', args.InputFile)

        with open(args.InputFile, encoding='utf-8-sig') as f:
            doc = ass.parse(f)
        doc = processDoc(doc, lookup, offsetms)

        if args.output:
            outpath = mkFilepath(args.output, conf.format)
        else:
            outpath = mkFilepath(args.InputFile, conf.format, '_cleaned')

        save(conf.format, doc, outpath)
        print('\n已保存至', outpath)
        print()
    except AssertionError as err:
        error(err)
    except Exception as err:
        error(
            '\n请将下面的报错信息及待转换文件提交到 https://github.com/zhimengsub/SubtitleCleaner/issues')
        traceback.print_exc()
    finally:
        if args.log:
            closeLogfile()
            _print('日志文件已保存至', str(logpath))
            _print()

        if not args.quit:
            os.system('pause')

