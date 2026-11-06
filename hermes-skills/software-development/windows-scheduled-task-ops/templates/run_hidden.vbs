' run_hidden.vbs —— 计划任务用的"隐藏外壳"模板（复制后改 3 个常量即可）
' 注册方式：wscript.exe //B //Nologo run_hidden.vbs
'
' 原理：进程树最顶层由 wscript 建一个**隐藏**控制台，后代全部继承 → 不再新建可见窗口。
' 重定向必须写在这里（pythonw 没有 stdout，日志靠 cmd 层重定向创建句柄）。
Option Explicit
Dim sh, exePath, scriptPath, logPath, cmd

exePath    = "C:\path\to\pythonw.exe"      ' pythonw = GUI 子系统，本身无控制台；也可用 python.exe
scriptPath = "D:\path\to\job.py"
logPath    = "D:\path\to\job.log"          ' 追加写，便于与 LastRunTime 互钉

Set sh = CreateObject("WScript.Shell")
cmd = """" & exePath & """ """ & scriptPath & """ >> """ & logPath & """ 2>&1"
sh.Run cmd, 0, False                        ' 0 = 隐藏窗口；False = 不等待
' 注意：不要用 cmd /c 再套一层拼引号 —— 直接 Run 解释器，重定向写在这行字符串里最稳。
