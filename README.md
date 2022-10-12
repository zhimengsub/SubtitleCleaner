# 程序下载

在[Releases](https://github.com/barryZZJ/SubtitleCleaner/releases)页面选择最新版本的程序下载。

# FullwidthConverter / 全角片假名转换器

可以将半角片假名/符号转换为全角形式

## 使用方法

1. 将待转换文件直接拖放到本程序上即可。

2. 也可以使用命令行进行更多配置：
    `-o FILE`：输出文件名，默认为`<输入文件名>_out.txt`。

## TODO List

- [ ] 批量处理多个文件同时拖入
- [ ] 制作GUI界面

---
# SubCleaner / 字幕清理器

输入`.ass`字幕文件，输出清理后的文本文件，具体处理内容如下：

1. 台词合并：
   - 以`…\N`结尾时，与下一行拼接，并用全角空格隔开
   - 与下一行开始和结束时间相同时，二者拼接，并用半角空格隔开
2. 台词清理：
   - 直接删除：`…` `｡`(半角) `。`(全角) `！` `(文字)` `[文字]` `{文字}` `\N` `空行`
   - 每一行使用`FullWidthConverter`处理半角平假名
   - 每一行开头添加`\N`

## 使用方法

1. 将待转换文件直接拖放到本程序上即可。

2. 也可以使用命令行进行更多配置：
    `-o FILE`：输出文件名，默认为`<输入文件名>_out.txt`。


## TODO List

- [ ] 批量处理多个文件同时拖入
- [ ] 制作GUI界面

# 提出修改建议 / 运行时的错误和BUG

请给我提出[Issue](https://github.com/barryZZJ/SubtitleCleaner/issues)，看到后我会及时处理。

# Changelog

## FullwidthConverter

- v1.0

  实现基本功能

  支持UTF-8 (with BOM)、GBK编码格式文件

  一次只支持单个文件

## SubCleaner

- v1.0
    
  实现基本功能 

  一次只支持单个文件
