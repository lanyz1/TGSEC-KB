#!/bin/bash
# ADBKeyboard 文本输入封装 —— 给 Flutter/自绘 UI 输入文字的唯一可靠方式
# 用法:
#   bash adbkb_input.sh install [apk路径]
#   bash adbkb_input.sh type "<PHONE-REDACTED>"          # 当前已聚焦的输入框
#   bash adbkb_input.sh tap-type 540 1034 "779"     # 先点坐标聚焦再输入
#
# 背景: `adb shell input text` / `input keyevent` / 界面"粘贴"按钮 / 宿主剪贴板同步
#       对 Flutter 等自绘输入框全部无效(实测)。ADBKeyboard 是广播式 IME, 通吃所有 App。

ADB=${ADB:-adb}
SER=${SER:-}
if [ -n "$SER" ]; then ADB="$ADB -s $SER"; fi

case "$1" in
  install)
    APK=${2:-ADBKeyboard.apk}
    $ADB install -r -g "$APK" || exit 1
    # 注意: `ime set` 常报 "Unknown input method ... cannot be selected"
    #       直接改 secure settings 才生效
    CUR=$($ADB shell settings get secure enabled_input_methods | tr -d '\r')
    $ADB shell "settings put secure enabled_input_methods '${CUR}:com.android.adbkeyboard/.AdbIME'"
    $ADB shell "settings put secure default_input_method com.android.adbkeyboard/.AdbIME"
    sleep 2
    echo "enabled  = $($ADB shell settings get secure enabled_input_methods | tr -d '\r')"
    echo "default  = $($ADB shell settings get secure default_input_method | tr -d '\r')"
    ;;
  type)
    # 先确认 App 在前台, 且输入框已聚焦(点过坐标)
    $ADB shell "am broadcast -a ADB_INPUT_TEXT --es msg '$2'" | tail -1
    ;;
  tap-type)
    $ADB shell input tap "$2" "$3"; sleep 3
    $ADB shell "am broadcast -a ADB_INPUT_TEXT --es msg '$4'" | tail -1
    ;;
  clear)
    # 清空当前聚焦输入框(退格 xN)
    N=${2:-20}; for i in $(seq $N); do $ADB shell input keyevent 67; done
    ;;
  hidekb)
    $ADB shell input keyevent 111      # 收键盘: 避免键盘顶动布局导致按钮坐标失效
    ;;
  *) echo "usage: $0 install|type|tap-type|clear|hidekb"; exit 1 ;;
esac

# 配套检查清单:
#   $ADB shell "dumpsys window | grep mCurrentFocus"   # App 必须在前台
#   $ADB shell wm size                                 # 截图尺寸 = input tap 坐标空间
#   $ADB shell screencap -p /sdcard/s.png && $ADB pull /sdcard/s.png .   # 视觉确认
# 输入成功后 App 底部/状态栏会显示 "ADB Keyboard (ON)"
