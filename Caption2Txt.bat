@REM 根据ts生成清理后的台词文本文件。
@REM 使用方法：拖入ts文件，会先生成ass，然后生成处理后的txt文件。
@REM 注意：必须把本脚本与Caption2Ass_PCR.exe、SubCleaner.exe放在同一目录下才能正常工作！
@REM by 谢耳朵w v1.1

@echo off
cd /d "%~dp0"

Caption2Ass_PCR.exe -norubi "%~1"

echo.

@REM 添加--log可以把程序的输出保存到文件中
SubCleaner.exe "%~dpn1.ass" -q

pause
