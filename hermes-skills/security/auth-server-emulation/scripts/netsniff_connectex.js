// netsniff_connectex.js — 诊断:程序到底怎么连服务器?
// 用途:当普通 connect hook 抓不到连接时(getaddrinfo 触发了但 connect 无输出),
// 用本脚本打印 ALL connect/WSAConnect/ConnectEx 目标,确认是否走 IOCP 异步连接。
// 用法: frida -p <PID> -l netsniff_connectex.js
'use strict';

var ws2 = Process.findModuleByName('ws2_32.dll');

function getExp(mod, name) {
    try { return mod.getExportByName(name); } catch (e) { return null; }
}

function logSockaddr(sockaddr, tag) {
    try {
        if (sockaddr.isNull()) { send('[' + tag + '] null sockaddr'); return; }
        var family = sockaddr.readU16();
        if (family === 2) { // AF_INET
            var port = (sockaddr.readU8(2) << 8) | sockaddr.readU8(3);
            var ipBytes = new Uint8Array(sockaddr.add(4).readByteArray(4));
            send('[' + tag + '] ' + ipBytes.join('.') + ':' + port);
        } else if (family === 23) { // AF_INET6
            var port6 = (sockaddr.readU8(2) << 8) | sockaddr.readU8(3);
            send('[' + tag + '] [ipv6]:' + port6);
        } else {
            send('[' + tag + '] family=' + family);
        }
    } catch (e) {
        send('[' + tag + '] err: ' + e);
    }
}

var connectPtr = getExp(ws2, 'connect');
if (connectPtr) {
    Interceptor.attach(connectPtr, {
        onEnter: function (args) { logSockaddr(args[1], 'connect'); }
    });
    console.log('[+] hooked connect');
}

var wsaPtr = getExp(ws2, 'WSAConnect');
if (wsaPtr) {
    Interceptor.attach(wsaPtr, {
        onEnter: function (args) { logSockaddr(args[1], 'WSAConnect'); }
    });
    console.log('[+] hooked WSAConnect');
}

// ConnectEx: Python asyncio ProactorEventLoop 在 Windows 用 IOCP 异步连接。
// 函数指针通过 WSAIoctl(SIO_GET_EXTENSION_FUNCTION_POINTER, WSAID_CONNECTEX) 运行时获取。
var CONNECTEX_GUID = [
    0xb9, 0x07, 0xa2, 0x25, 0xf3, 0xdd, 0x60, 0x46,
    0x8e, 0xe9, 0x76, 0xe5, 0x8c, 0x74, 0x06, 0x3e
];
function guidMatches(ptr) {
    try {
        var b = new Uint8Array(ptr.readByteArray(16));
        for (var i = 0; i < 16; i++) if (b[i] !== CONNECTEX_GUID[i]) return false;
        return true;
    } catch (e) { return false; }
}

var wsaIoctl = getExp(ws2, 'WSAIoctl');
if (wsaIoctl) {
    Interceptor.attach(wsaIoctl, {
        onEnter: function (args) {
            try {
                // args[1]=dwIoControlCode, args[2]=lpInBuffer(GUID), args[6]=lpOutBuffer
                if (args[1].toInt32() === 0xC8000006 && guidMatches(args[2])) {
                    this.isConnectEx = true;
                    this.outBuf = args[6];
                }
            } catch (e) {}
        },
        onLeave: function () {
            try {
                if (this.isConnectEx) {
                    var fnPtr = this.outBuf.readPointer();
                    send('[+] ConnectEx pointer: ' + fnPtr);
                    Interceptor.attach(fnPtr, {
                        onEnter: function (a) { logSockaddr(a[1], 'ConnectEx'); }
                    });
                    this.isConnectEx = false;
                }
            } catch (e) {}
        }
    });
    console.log('[+] hooked WSAIoctl (ConnectEx capture)');
}

console.log('[*] netsniff ready');
