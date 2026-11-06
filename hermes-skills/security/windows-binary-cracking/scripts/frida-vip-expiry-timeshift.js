// Frida time-shift expiry bypass — VERIFIED WORKING on Nuitka/PyInstaller apps
// with fndata-style network verification (VipTime expiry check).
//
// Shifts the app's perceived wall-clock back ~1 year so VipTime expiry
// never fires _shutdown_after_delay. Runtime-only: re-attach after every
// app restart (pair with the one-click relaunch pattern).
//
// Usage: frida -p <pid> -l frida-vip-expiry-timeshift.js
'use strict';

var SHIFT_100NS = BigInt(86400) * BigInt(10000000) * BigInt(365); // 1 year, 100ns units
var SHIFT_SEC = 86400 * 365; // 1 year, seconds

function getExp(mod, name) {
    try { return mod.getExportByName(name); } catch (e) { return null; }
}

// 1. GetSystemTimeAsFileTime (kernel32) — classic FILETIME source
var modK = Process.findModuleByName('kernel32.dll');
var p1 = getExp(modK, 'GetSystemTimeAsFileTime');
if (p1) {
    Interceptor.attach(p1, {
        onEnter: function (args) { this.out = args[0]; },
        onLeave: function () {
            try {
                var ft = this.out.readU64();
                this.out.writeU64(ft - SHIFT_100NS);
            } catch (e) {}
        }
    });
    console.log('[+] hooked GetSystemTimeAsFileTime');
}

// 2. GetSystemTimePreciseAsFileTime (kernelbase) — modern source, datetime.now() on Win10+
var modKb = Process.findModuleByName('kernelbase.dll');
var p2 = getExp(modKb, 'GetSystemTimePreciseAsFileTime');
if (p2) {
    Interceptor.attach(p2, {
        onEnter: function (args) { this.out = args[0]; },
        onLeave: function () {
            try {
                var ft = this.out.readU64();
                this.out.writeU64(ft - SHIFT_100NS);
            } catch (e) {}
        }
    });
    console.log('[+] hooked GetSystemTimePreciseAsFileTime');
}

// 3. ucrtbase time() — C runtime epoch seconds (may be absent; Python uses FILETIME)
var modU = Process.findModuleByName('ucrtbase.dll');
var p3 = getExp(modU, 'time');
if (p3) {
    Interceptor.attach(p3, {
        onLeave: function (retval) {
            try {
                var t = retval.toInt32();
                retval.replace(ptr(t - SHIFT_SEC));
            } catch (e) {}
        }
    });
    console.log('[+] hooked ucrtbase!time');
}

// 4. api-ms-win-crt-time time() — CRT shim variant
var modA = Process.findModuleByName('api-ms-win-crt-time-l1-1-0.dll');
var p4 = getExp(modA, 'time');
if (p4) {
    Interceptor.attach(p4, {
        onLeave: function (retval) {
            try {
                var t = retval.toInt32();
                retval.replace(ptr(t - SHIFT_SEC));
            } catch (e) {}
        }
    });
    console.log('[+] hooked api-ms-win-crt-time!time');
}

console.log('[*] time shift ready (back 1 year)');
