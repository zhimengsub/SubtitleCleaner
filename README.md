# 字幕清理工具

## 简介

对ts源中提取出的ass字幕进行处理，包括合并多行对白、清理各种不必要的符号、说话人备注、转换假名半角等，输出ass或txt。

## 程序下载

在[Releases](https://github.com/zhimengsub/SubtitleCleaner/releases)页面选择最新版本的程序下载。

## 功能具体说明

⚠️部分功能可以在[配置文件](#配置文件格式)中详细设置，括号中即配置文件中对应的条目。

### 合并

合并多行对白及其时间（需要保证字幕按时间顺序排列）

📝 分隔符：一般使用`merge.sep`（默认为空格）或`merge.sep_on_overlap`（默认为空格）；
当新行以`merge.special_prefix`开头时（默认为空字符串，表示关闭该功能），则改为使用`merge.sep_on_special_prefix`分隔。

1. 按成对括号合并（开关：`merge.pair`，默认开启）：
   
   包含以下符号的左括号，经过多行后出现对应的右括号，则将这些行合并，使用`merge.sep`分隔。⚠️合并时左括号后和右括号前后不添加分隔符。
    
    `《》` `<>` `＜＞` `〈〉` `「」` `｢｣` `『』` `()` `[]`

2. 按单个符号合并（开关：`merge.singlesuf`，默认开启）：
   
    以`→`结尾的对白，和下一行合并，使用`merge.sep`分隔。

3. 按时间合并（开关：`merge.time`，默认关闭）：

   时间有重叠的相邻对白合并，使用`merge.sep_on_overlap`分隔。

- 可配置参数：

  - 📝 合并行数限制`merge.limit`：

    整数。为避免合并后内容过长，可以限制合并行数达到`merge.limit`后强制新建一行。
  
    默认为2，设为0表示不限制。

  - 📝 忽略按时间合并时的行数限制`merge.ignore_limit_on_overlap`：
    
    默认关闭。开启后可以保证输出的每一行都不会有时间重叠。

### 清理

1. 直接删除以下**单个**字符（配置：`symbols.remove`，把所有需要删除的**单个**字符依次写入）：

   `…` `｡` `。` `！` `!` `？` `?` `~` `～` `∼` `・` `♪` `≫` `《` `》` `<` `>` `＜` `＞` `〈` `〉` 

    🗈：如果添加`「` `」` `『` `』`等各种括号也不影响前面的合并。
2. 如果以下字符在行尾（合并前），则将其删除（不可配置）：
   `→`
3. 直接删除以下字符（不可配置）：
   `\N`
4. 方括号`[]`及其括起来的的内容（不可配置）；
5. 圆括号`()`及其括起来的内容，一般为说话人或环境音提示（开关：`remove_comments`，默认开启）；
6. 替换**单个**字符（配置：`symbols.replace_key` `symbols.replace_val`）：
   
    默认`、` `､`替换为半角空格。

    配置方法：替换前的**单个**字符写在`symbols.replace_key`中，替换后的**单个**字符**一一对应**按顺序依次写在`symbols.replace_val`中。

7. rubi字幕（平假名注音字幕）（开关：`remove_rubi`，默认开启）
8. 特效标签（花括号括起来的），开启时全部删除，关闭时保留（如果合并了多行，只保留第一行的）（开关：`remove_format_tags`，默认开启）

### 其他

1. 假名宽度替换（`FullwidthConverter.py`）（开关：`convert_width`，默认开启）：

   将半角片假名，以及`｡` `｢` `｣` `､` `･`等符号转换为全角；

   将全角数字、空格转换为半角。

2. 添加前缀（开关：`add_newline_prefix`，默认开启）：

    在输出的每一行开头添加`\N`前缀。
    
3. 数字宽度替换（开关：`format_digit`，默认开启）：

    若一行对白只含有一个数字，则数字使用全角，若含有多个数字，则所有数字均使用半角。

- 可配置参数：
    
  - 📝 输出格式`format`：

    字符串，默认为 `ass`，表示输出ass字幕文件，也可设置为`txt`，表示文本文件。


## 配置文件格式

配置文件为同目录下的`configs.json`，使用[JSON语法](https://www.runoob.com/json/json-syntax.html)。

📝 如果误删，重新运行一次`SubCleaner.exe`即可生成。

默认配置：

```json
{
    "format": "ass",
    "merge": {
        "pair": true,
        "singlesuf": true,
        "time": false,
        "limit": 2,
        "ignore_limit_on_overlap": false,
        "sep": " ",
        "sep_on_overlap": " ",
        "special_prefix": "",
        "sep_on_special_prefix": "\\N"
    },
    "symbols": {
      "remove": "…。｡！!？?~～∼・♪≫《》<>＜＞〈〉",
      "replace_key": "、､",
      "replace_val": "  "
    },
    "remove_rubi": true,
    "remove_format_tags": true,
    "remove_comments": true,
    "convert_width": true,
    "add_newline_prefix": true,
    "format_digit": true
}
```

## 使用方式

按需求修改配置文件`configs.json`，然后将需要处理的字幕文件`ass`拖放到`SubCleaner.exe`上，即可得到处理后的文件，默认输出文件名为`<输入文件名>_cleaned`。

也可以[使用命令行](#其他命令行参数)进行更多配置。

## 其他命令行参数

格式
```
SubCleaner.py [-h] [-o OUTFILE] [-q] [--offsetms OFFSETMS] [--log] InputFile
```

可选参数说明：


`-o OUTPUT, --output OUTPUT`

输出文件路径，默认为<输入文件名>_cleaned。

`-q, --quit`

结束后不暂停程序直接退出，方便命令行调用。不加该参数程序结束时会提示`请按任意键继续...`。

`--offsetms OFFSETMS` 

输出ass整体时间偏移毫秒数，负数为提前，正数为延后。

`--log`

记录日志，日志存储到同目录下的<输入文件名>_log.txt。


📝 使用命令行参数需要先[在`SubCleaner.exe`所在目录打开命令行](#在指定目录打开命令行)，然后输入`Subcleaner.exe <字幕文件路径> <其他命令行参数>`，如`Subcleaner.exe input.ass -o output.ass --offsetms -355 --log -q`。



## FAQ

### 在指定目录打开命令行

点击资源管理器的地址栏，输入`cmd`后按回车。

![参考](https://imgconvert.csdnimg.cn/aHR0cHM6Ly9naXRlZS5jb20vYWxleF9kL0dyYXBoLWJlZC9yYXcvbWFzdGVyLzIwMTYvMTExMC9leHBsb3Jlcl9vcGVuX2NtZF8xLnBuZw?x-oss-process=image/format,png)

---

# Caption2Txt.bat

说明：批处理文件，依次调用`Caption2Ass`(请自行搜索下载)提取ts中的ass、`SubCleaner`对提取出的字幕进行清理。

使用方法：拖放ts文件到批处理文件上。

⚠️必须把本脚本与Caption2Ass_PCR.exe、SubCleaner.exe放在同一目录下才能正常工作！

# 提出修改建议 / 运行时的错误和BUG

请给我提出[Issue](https://github.com/zhimengsub/SubtitleCleaner/issues)，看到后我会及时处理。

# Changelog

## FullwidthConverter

- 1.0.4_halfwidth-sp
  - 空格全部变为半角

- v1.0.4
  - 空格全部变为全角

- v1.0.3
  - 修改全角数字为半角数字

- v1.0.2
  - 添加`-q, --quit` `--log`参数，方便命令行调用

- v1.0.1
  - 优化直接运行程序时的提示

- v1.0
  - 实现基本功能
  - 支持UTF-8 (with BOM)、GBK编码格式文件
  - 一次只支持单个文件

## SubCleaner

- v3.0.2
  - 支持新的参数

- v3.0.0
  - 重构代码，支持输出ass
  - 支持更多可配置参数，并使用配置文件读取

- v2.4.5.001
  - 一句话内只有一位数字时改为全角，同时出现多位数字时保持半角

- v2.4.4.002_halfwidth-sp
  - 空格全部变为半角

- v2.4.4.002:
  - 使用假名转换器v1.0.4
  - 不含拟声词删除功能

- v2.4.3
  - 顿号替换为全角空格
  - v2.4.3.002: 拟声词误删较多，暂时关闭该功能

- v2.4.2
  - 使用假名转换器v1.0.3

- v2.4.1
  - 完善台词清理符号

- v2.4.0
  - 完善台词清理符号
  - 台词清理新增删除拟声词v0.2
  - 完善台词合并行为（每两行合并一次）

- v2.3.1
  - 转移仓库至zhimengsub

- v2.3.0
  - 改进台词合并的规则
  - 跳过Rubi(注音)的台词

- v2.2.0
  - 优化输出内容（存在bug：时间相同的台词合并时也会以全角空格隔开）

- v2.1.0
  - 新增几对合并标志符号，优化输出内容

- v2.0.0
  - 修改台词合并逻辑
  - 修复合并及清理时的一些bug
  - 修改默认输出文件名为`<输入文件名>.txt`
  - 添加`-q, --quit` `--log`参数，方便命令行调用

- v1.0.1
  - 优化直接运行程序时的提示

- v1.0
  - 实现基本功能 
  - 一次只支持单个文件
