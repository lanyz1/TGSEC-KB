// 查询默认音频输出端点和所有活动渲染端点信息
// 编译运行:
//   powershell -NoProfile -Command "Add-Type -Path 'query_audio_endpoints.cs' -OutputAssembly 'query_audio_endpoints.exe' -OutputType ConsoleApplication; & '.\query_audio_endpoints.exe'"
// 注意: Add-Type 必须用 -Path 传文件, 不能用位置参数(会被当源码文本报 escape sequence 错)
using System;
using System.Runtime.InteropServices;

public static class AudioQuery
{
    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
    class MMDeviceEnumeratorComObject { }

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator
    {
        int EnumAudioEndpoints(int dataFlow, int dwStateMask, out IMMDeviceCollection ppDevices);
        int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
        int GetDevice(string pwstrId, out IMMDevice ppDevice);
        int RegisterEndpointNotificationCallback(IntPtr pClient);
        int UnregisterEndpointNotificationCallback(IntPtr pClient);
    }

    [ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceCollection
    {
        int GetCount(out int pcDevices);
        int Item(int nDevice, out IMMDevice ppDevice);
    }

    [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice
    {
        int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, out IntPtr ppInterface);
        int OpenPropertyStore(int stgmAccess, out IPropertyStore ppProperties);
        int GetId(out IntPtr ppstrId);
        int GetState(out int pdwState);
    }

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore
    {
        int GetCount(out int cProps);
        int GetAt(int iProp, out PropertyKey pkey);
        int GetValue(ref PropertyKey key, out PropVariant pv);
        int SetValue(ref PropertyKey key, ref PropVariant pv);
        int Commit();
    }

    [StructLayout(LayoutKind.Sequential)]
    struct PropertyKey
    {
        public Guid fmtid;
        public uint pid;
    }

    [StructLayout(LayoutKind.Explicit)]
    struct PropVariant
    {
        [FieldOffset(0)] public ushort vt;
        [FieldOffset(8)] public IntPtr pointerValue;
        [FieldOffset(8)] public uint uintValue;
        [FieldOffset(8)] public int intValue;
        [FieldOffset(8)] public IntPtr pwszValue;
    }

    // PKEY_Device_FriendlyName
    static readonly PropertyKey PKEY_Device_FriendlyName = new PropertyKey { fmtid = new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"), pid = 14 };

    [DllImport("ole32.dll")]
    static extern int CoInitialize(IntPtr pvReserved);

    static string GetProp(IPropertyStore store, PropertyKey key)
    {
        PropVariant pv;
        try
        {
            store.GetValue(ref key, out pv);
            if (pv.vt == 31 && pv.pwszValue != IntPtr.Zero) // VT_LPWSTR
                return Marshal.PtrToStringUni(pv.pwszValue);
            if (pv.vt == 8 && pv.pwszValue != IntPtr.Zero) // VT_BSTR
                return Marshal.PtrToStringBSTR(pv.pwszValue);
            return "(vt=" + pv.vt + ")";
        }
        catch { return "?"; }
    }

    public static void Main()
    {
        CoInitialize(IntPtr.Zero);
        var enumerator = (IMMDeviceEnumerator)new MMDeviceEnumeratorComObject();

        // 默认渲染端点 (eRender=0, eConsole=0)
        IMMDevice def;
        int hr = enumerator.GetDefaultAudioEndpoint(0, 0, out def);
        if (hr == 0)
        {
            IPropertyStore ps;
            def.OpenPropertyStore(0, out ps);
            Console.WriteLine("DEFAULT_OUTPUT=" + GetProp(ps, PKEY_Device_FriendlyName));
            IntPtr idPtr;
            def.GetId(out idPtr);
            Console.WriteLine("DEFAULT_ID=" + Marshal.PtrToStringUni(idPtr));
            Marshal.FreeCoTaskMem(idPtr);
        }
        else
        {
            Console.WriteLine("GetDefaultAudioEndpoint hr=0x" + hr.ToString("X8"));
        }

        // 列出所有活动渲染端点 (eRender=0, ACTIVE=1)
        IMMDeviceCollection coll;
        enumerator.EnumAudioEndpoints(0, 1, out coll);
        int count;
        coll.GetCount(out count);
        for (int i = 0; i < count; i++)
        {
            IMMDevice dev;
            coll.Item(i, out dev);
            IPropertyStore ps;
            dev.OpenPropertyStore(0, out ps);
            int state;
            dev.GetState(out state);
            IntPtr idPtr;
            dev.GetId(out idPtr);
            Console.WriteLine("ENDPOINT state=" + state + " id=" + Marshal.PtrToStringUni(idPtr) + " name=" + GetProp(ps, PKEY_Device_FriendlyName));
            Marshal.FreeCoTaskMem(idPtr);
        }
        Console.WriteLine("TOTAL=" + count);
    }
}
