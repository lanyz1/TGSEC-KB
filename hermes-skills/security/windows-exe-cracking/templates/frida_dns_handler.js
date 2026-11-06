/*
 * Frida DNS hook template — drop into:
 *   __handlers__/WS2_32.dll/getaddrinfo.js   (ASCII hostname)
 *   __handlers__/WS2_32.dll/GetAddrInfoW.js  (UTF-16 hostname)
 *
 * Usage:
 *   frida-trace -p <childPID> -i "getaddrinfo" -i "GetAddrInfoW"
 *   (edit handlers, RESTART frida-trace, then trigger a login/register in the app)
 *
 * Captures the verification-server hostname even when a system proxy
 * (v2rayN/xray/Clash) masks all outbound TCP from the target process —
 * DNS resolution still happens in-process.
 */

defineHandler({
  onEnter(log, args, state) {
    try {
      var node = args[0];
      if (!node.isNull()) {
        // getaddrinfo:     readUtf8String()
        // GetAddrInfoW:    readUtf16String()
        log('DNS(HOST: ' + node.readUtf8String() + ')');
      } else {
        log('DNS(HOST: null)');
      }
    } catch (e) {
      log('DNS(err: ' + e + ')');
    }
  },

  onLeave(log, retval, state) {
  }
});
