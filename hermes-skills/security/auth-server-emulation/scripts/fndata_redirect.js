// fndata_redirect.js - redirect outbound connections from the real auth server
// to a local fake server. Usage: frida -p <PID> -l fndata_redirect.js
// Edit TARGET_IP / TARGET_PORT to match the real server discovered in step 4.
'use strict';

var TARGET_IP = '101.35.246.71';
var TARGET_PORT = 18888;

var ws2 = Process.findModuleByName('ws2_32.dll');

function getExp(mod, name) {
    try { return mod.getExportByName(name); } catch (e) { return null; }
}

// Hook connect - rewrite sockaddr to 127.0.0.1 when target is the auth server
var connectPtr = getExp(ws2, 'connect');
if (connectPtr) {
    Interceptor.attach(connectPtr, {
        onEnter: function (args) {
            try {
                var sockaddr = args[1];
                if (sockaddr.isNull()) return;
                var family = sockaddr.readU16();
                if (family === 2) { // AF_INET
                    var port = (sockaddr.readU8(2) << 8) | sockaddr.readU8(3);
                    var ip = sockaddr.add(4).readByteArray(4);
                    var ipStr = Array.prototype.slice.call(new Uint8Array(ip)).join('.');
                    if (ipStr === TARGET_IP && port === TARGET_PORT) {
                        // rewrite to 127.0.0.1 (same port)
                        sockaddr.writeU8(0x7f, 4); // 127
                        sockaddr.writeU8(0x00, 5); // .0
                        sockaddr.writeU8(0x00, 6); // .0
                        sockaddr.writeU8(0x01, 7); // .1
                        send('REDIRECTED connect: ' + ipStr + ':' + port + ' -> 127.0.0.1:' + port);
                    }
                }
            } catch (e) {
                send('connect hook err: ' + e);
            }
        }
    });
    console.log('[+] hooked connect');
}

// Also hook WSAConnect
var wsaPtr = getExp(ws2, 'WSAConnect');
if (wsaPtr) {
    Interceptor.attach(wsaPtr, {
        onEnter: function (args) {
            try {
                var sockaddr = args[1];
                if (sockaddr.isNull()) return;
                var family = sockaddr.readU16();
                if (family === 2) {
                    var port = (sockaddr.readU8(2) << 8) | sockaddr.readU8(3);
                    var ip = sockaddr.add(4).readByteArray(4);
                    var ipStr = Array.prototype.slice.call(new Uint8Array(ip)).join('.');
                    if (ipStr === TARGET_IP && port === TARGET_PORT) {
                        sockaddr.writeU8(0x7f, 4);
                        sockaddr.writeU8(0x00, 5);
                        sockaddr.writeU8(0x00, 6);
                        sockaddr.writeU8(0x01, 7);
                        send('REDIRECTED WSAConnect: ' + ipStr + ':' + port + ' -> 127.0.0.1:' + port);
                    }
                }
            } catch (e) {}
        }
    });
    console.log('[+] hooked WSAConnect');
}

console.log('[*] fndata redirect ready');
