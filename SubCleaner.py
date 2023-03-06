import datetime
import os
from argparse import RawTextHelpFormatter
import traceback
from copy import deepcopy
from typing import Optional

import ass
from ass import Dialogue

from FullwidthConverter import convertline, lookup
from utils.argparser import MyParser
from utils.const import *
from utils.logfile import _print, setLogfile, closeLogfile, print, warning, error
from utils.misc import mkFilepath, MergeType, removeSFX, overlaps, save, formatDelta, joinEvents, splitEvents, \
    joinEventsByTime
from utils.conf import conf
from utils.mydialogue import MyDialogue

VER = 'v3.0.0'

DESCRIPTION = '字幕清理器\n' + \
              '输入.ass字幕文件，提取对话文本，进行台词合并、清理、假名转换后输出为.ass或.txt文件\n' + \
              '—— ' + VER + ' by 谢耳朵w\n\n' + \
              '使用方法：将待转换文件拖放到本程序上即可，也可以使用命令行运行进行更多配置。\n\n' + \
              '详细介绍、获取最新版本、提交bug请前往 https://github.com/zhimengsub/SubtitleCleaner'


def initparser():
    parser = MyParser(description=DESCRIPTION, formatter_class=RawTextHelpFormatter)
    parser.add_argument('InputFile', type=str, help='待转换ass文件的路径。')
    parser.add_argument('-o', '--output', type=str, help='输出文件路径，默认为<输入文件名>_cleaned。')
    parser.add_argument('-q', '--quit', action='store_true', help='结束后不暂停程序直接退出，方便命令行调用。不加该参数程序结束时会暂停。')
    parser.add_argument('--offsetms', type=int, default=0, help='输出ass整体时间偏移毫秒数，负数为提前，正数为延后。')
    parser.add_argument('--log', action='store_true', help='记录日志，日志存储到同目录下的<输入文件名>_log.txt。')
    return parser


def cleanEvent(event:Dialogue, pats:list[tuple[re.Pattern, str]]):
    text = event.text
    for pat, repl in pats:
        text = pat.sub(repl, text)
    text = text.strip(' 　' + MERGE_SEP)  # 清理两边多余的半角和全角空格和分隔符
    event.text = text


def postProcess(event: Dialogue) -> Dialogue:
    text = event.text
    if conf.format_digit:
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
    return event


def findMergeStart(event: Dialogue) -> tuple[MergeType, str]:
    """
    :returns: mergetype and matched symbol
    """
    if conf.merge.pair:
        for pairleft in pairs:
            if pairleft in event.text:
                return MergeType.Pair, pairleft

    if conf.merge.singlesuf:
        for suf in singlesufs:
            if event.text.endswith(suf):
                return MergeType.Singlesuf, suf

    if conf.merge.time:
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


def findMergeInterval(events: list[Dialogue], start: int) -> tuple[int, str, MergeType]:
    """
    :returns: end index of merged events; merge reason (or warning msg if end index == -1); Mergetype
    """
    eventL = events[start]
    mergetype, symb = findMergeStart(eventL)

    reason = ''
    if mergetype == MergeType.No:
        return start, reason, MergeType.No

    if mergetype == MergeType.Pair:
        symbR = pairs[symb]
        end, reason = findMergeEnd(events, start, mergetype, symbR)
    else:
        end, reason = findMergeEnd(events, start, mergetype, symb)

    return end, reason, mergetype


def mergeEvents(events: list[Dialogue],
                start: int,
                limit: int,
                procid: int,
                warnings: list,
                log_reason: list,
                remove_overlap: bool) -> tuple[int,
                                           list[Dialogue]]:
    """
    returns: end index of merged events; merged events; start and end index of each merged event
    """
    merge_list = [events[start]]  # 所有需要合并的对白
    start_ = start
    while True:
        # 考虑到存在下一行时间仍相同，或者出现新的标识符的情况，故不断搜索直到没有合并的情况
        end, reason, mergetype = findMergeInterval(events, start_)

        if end == -1:
            warning(reason)
            warnings.append((procid, reason))
            end = start_

        if end == start_:
            break

        log_reason.append(reason)
        merge_list.extend(MyDialogue(event, mergetype) for event in events[start_+1:end+1])
        start_ = end

    # 清理合并标志符号
    for event in merge_list:
        cleanEvent(event, pats_stripsuf)

    # 合并后清理，再拆开，然后再每隔limit个用conf.merge.sep合并在一起

    merged = joinEvents(merge_list, MERGE_SEP, ignore_sep_on_pairs=False)
    cleanEvent(merged, pats_rmpairs)
    if conf.remove_comments:
        cleanEvent(merged, pats_rmcomment)
    merge_list = splitEvents(merged, MERGE_SEP)
    merged_events = []
    limit = len(merge_list) if limit <= 0 else limit
    for i in range(0, len(merge_list), limit):
        joined = joinEvents(merge_list[i: i+limit], conf.merge.sep, ignore_sep_on_pairs=True)
        merged_events.append(joined)

    if remove_overlap:
        # 如果时间有重叠，再把重叠时间的对白合并
        merged_events = joinEventsByTime(merged_events, conf.merge.sep_on_overlap)

    return end, merged_events


def processDoc(doc: ass.Document,
               lookup: dict,
               offsetms: datetime.timedelta) -> ass.Document:

    events_old = [None] * len(doc.events)  # type: list[Optional[Dialogue]]
    for i, event in enumerate(doc.events):
        if event.TYPE == 'Dialogue':
            removeSFX(event)
            events_old[i] = deepcopy(event)
            cleanEvent(event, pats_rm)
            if conf.remove_comments:
                cleanEvent(event, pats_rmcomment)

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
        if doc.events[i].TYPE != 'Dialogue' or doc.events[i].style.lower() == 'rubi':
            if doc.events[i].style.lower() == 'rubi':
                print('[跳过Rubi台词]')
                print(doc.events[i].text)
                print()
            i += 1
            continue

        procid += 1

        reason = ''
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
        end, merged_events = mergeEvents(doc.events, i, conf.merge.limit, procid, warnings, log_reason, conf.remove_overlap)
        if end != i:
            cnter_mg += end - i + 1

        print(f'{procid}.', ' '.join(log_reason))

        for merged in merged_events:
            # convert half-width katakana and symbols
            if conf.convert_width:
                converted = convertline(merged.text, lookup)
                if converted != merged.text:
                    merged.text = converted
                    reason = '[转换假名]'
                    print(reason)
                    cnter_cv += 1

            # post process
            if conf.add_newline_prefix:
                cleanEvent(merged, pats_prefix)
            cleanEvent(merged, pats_final)
            postProcess(merged)

            merged.start += offsetms
            merged.end += offsetms

        tmp = []
        for ind in range(i, end + 1):
            time_start = formatDelta(events_old[ind].start)
            time_end = formatDelta(events_old[ind].end)
            text = events_old[ind].text
            tmp.append((time_start, time_end, text))
        print(' +\n'.join([time_start + ' ' + time_end + ' ' + text for time_start, time_end, text in tmp]))
        print('->')

        for merged in merged_events:
            if merged.text:
                outid += 1
                time_start = formatDelta(merged.start)
                time_end = formatDelta(merged.end)
                text = merged.text
                print(f'[{outid}]', time_start, time_end, text)
                events_out.append(merged)
            else:
                print('<删除>')

        print()
        i = end + 1

    print('处理完成！共合并了', cnter_mg, '行文本，清理了', cnter_ono, '行对白的语气词，转换了', cnter_cv, '行对白的假名，最终生成了', outid, '行对白。')

    if warnings:
        print('\n存在WARNING，请根据下方信息向上查找对应记录')
        for procid, msg in warnings:
            print(f'{procid}.', msg)

    doc.events = events_out
    return doc


def main():
    parser = initparser()
    args = parser.parse_args()
    offsetms = datetime.timedelta(milliseconds=args.offsetms)
    try:
        if args.log:
            logpath = mkFilepath(args.InputFile, '.txt', '_log')
            setLogfile(logpath)

        print(DESCRIPTION)
        print()
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


if __name__ == '__main__':
    main()

