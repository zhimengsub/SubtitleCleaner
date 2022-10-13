@ 根据ts生成清理后的台词文本文件。
@ 使用方法：拖入ts文件，会先生成ass，然后生成处理后的txt文件。
@ 注意：必须把本脚本与Caption2Ass_PCR.exe、SubCleaner.exe放在同一目录下才能正常工作！
@ by 谢耳朵w v1.0

@echo off

Caption2Ass_PCR.exe -norubi "%~1"

echo.

SubCleaner.exe "%~n1.ass" -q

pause
