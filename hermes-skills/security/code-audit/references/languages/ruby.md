# Ruby/Rails Security Audit

> Ruby/Rails 代码安全审计模块 | **双轨并行完整覆盖**
> 适用于: Ruby on Rails, Sinatra, Hanami, Ruby 脚本

---

## 审计方法论

### 双轨并行框架

```
                    Ruby/Rails 代码安全审计
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  轨道A (50%)    │ │  轨道B (40%)    │ │  补充 (10%)     │
│  控制建模法     │ │  数据流分析法   │ │  配置+依赖审计  │
│                 │ │                 │ │                 │
│ 缺失类漏洞:     │ │ 注入类漏洞:     │ │ • 硬编码凭据    │
│ • 认证缺失      │ │ • SQL注入       │ │ • Brakeman     │
│ • 授权缺失      │ │ • 命令注入      │ │ • Bundler CVE  │
│ • IDOR          │ │ • 反序列化      │ │                 │
│ • 竞态条件      │ │ • ERB注入       │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 两轨核心公式

```
轨道A: 缺失类漏洞 = 敏感操作 - 应有控制
轨道B: 注入类漏洞 = Source → [无净化] → Sink
```

**参考文档**: `references/core/security_controls_methodology.md`, `references/core/data_flow_methodology.md`
**推荐工具**: Brakeman (Rails静态分析)

---

# 轨道A: 控制建模法 (缺失类漏洞)

## A1. 敏感操作枚举

### 1.1 快速识别命令

```bash
# Rails路由 - 数据修改操作
grep -rn "post\|put\|patch\|delete" config/routes.rb

# Rails控制器方法
grep -rn "def create\|def update\|def destroy" --include="*_controller.rb"

# 数据访问操作
grep -rn "def show\|def index" --include="*_controller.rb"

# 批量操作
grep -rn "def export\|def download\|def batch\|def import" --include="*.rb"

# 资金操作
grep -rn "transfer\|payment\|refund\|balance" --include="*.rb"

# 外部HTTP请求
grep -rn "HTTParty\|Faraday\|Net::HTTP\|RestClient" --include="*.rb"

# 文件操作
grep -rn "File\.open\|File\.read\|send_file\|send_data" --include="*.rb"

# 命令执行
grep -rn "system\|exec\|spawn\|popen\|\`" --include="*.rb"
```

### 1.2 输出模板

```markdown
## Rails敏感操作清单

| # | 端点/方法 | HTTP方法 | 敏感类型 | 位置 | 风险等级 |
|---|-----------|----------|----------|------|----------|
| 1 | /users/:id | DELETE | 数据修改 | users_controller.rb:45 | 高 |
| 2 | /users/:id | GET | 数据访问 | users_controller.rb:32 | 中 |
| 3 | /transfers | POST | 资金操作 | payments_controller.rb:56 | 严重 |
```

---

## A2. 安全控制建模

### 2.1 Rails安全控制实现方式

| 控制类型 | Rails实现 | 检查方法 |
|----------|-----------|----------|
| **认证控制** | `before_action :authenticate_user!` (Devise) | 检查before_action |
| **授权控制** | Pundit, CanCanCan, `authorize` | 检查Policy/Ability |
| **资源所有权** | `current_user.posts.find(params[:id])` | 检查关联查询 |
| **输入验证** | Strong Parameters, ActiveModel Validations | 检查permit和validates |
| **并发控制** | `lock!`, `with_lock`, Optimistic Locking | 检查锁方法 |
| **审计日志** | paper_trail, audited | 检查gem和回调 |

### 2.2 控制矩阵模板 (Rails)

```yaml
敏感操作: DELETE /users/:id
位置: users_controller.rb:45
类型: 数据修改

应有控制:
  认证控制:
    要求: 必须登录
    实现: before_action :authenticate_user!

  授权控制:
    要求: 管理员或本人
    Pundit: authorize @user, :destroy?
    CanCanCan: authorize! :destroy, @user

  资源所有权:
    要求: 非管理员只能删除自己的数据
    验证: current_user.id == @user.id
```

---

## A3. 控制存在性验证

### 3.1 数据修改操作验证清单

```markdown
## 控制验证: [端点名称]

| 控制项 | 应有 | Rails实现 | 结果 |
|--------|------|-----------|------|
| 认证控制 | 必须 | before_action :authenticate_user! | ✅/❌ |
| 授权控制 | 必须 | Pundit/CanCanCan | ✅/❌ |
| 资源所有权 | 必须 | current_user关联查询 | ✅/❌ |
| 输入验证 | 必须 | Strong Parameters | ✅/❌ |

### 验证命令
```bash
# 检查认证
grep -A 5 "class.*Controller" [Controller文件] | grep "before_action.*authenticate"

# 检查授权
grep -A 20 "def destroy\|def update" [Controller文件] | grep "authorize\|can?\|cannot?"

# 检查资源所有权
grep -A 10 "def destroy" [Controller文件] | grep "current_user\.\|@current_user\."
```
```

### 3.2 常见缺失模式 → 漏洞映射

| 缺失控制 | 漏洞类型 | CWE | Rails检测方法 |
|----------|----------|-----|---------------|
| 无authenticate | 认证缺失 | CWE-306 | 检查before_action |
| 无authorize | 授权缺失 | CWE-862 | 检查Pundit/CanCanCan |
| 无current_user关联 | IDOR | CWE-639 | 检查查询方式 |
| 无with_lock | 竞态条件 | CWE-362 | 检查资金操作锁 |

---

# 轨道B: 数据流分析法 (注入类漏洞)

> **核心公式**: Source → [无净化] → Sink = 注入类漏洞
> **推荐工具**: Brakeman

## B1. Rails Source

```ruby
params[:name]
params.permit(:name)
request.headers['X-Header']
cookies[:session]
request.body.read
```

## B2. Rails Sink

| Sink类型 | 漏洞 | CWE | 危险函数 |
|----------|------|-----|----------|
| 反序列化 | RCE | 502 | Marshal.load, YAML.load |
| SQL执行 | SQL注入 | 89 | where("...#{x}"), find_by_sql |
| 命令执行 | 命令注入 | 78 | system, exec, `` |
| 代码执行 | 代码注入 | 94 | eval, instance_eval |
| 文件操作 | 路径遍历 | 22 | File.read, send_file |

## B3. Sink检测命令 (Brakeman + grep)

## 识别特征

```ruby
# Ruby/Rails 项目识别
Gemfile, Gemfile.lock
*.rb, *.erb, *.haml, *.slim

# Rails 结构
├── app/
│   ├── controllers/
│   ├── models/
│   ├── views/
│   └── channels/  # ActionCable
├── config/
├── db/
└── Gemfile
```

---

## 一键检测命令

### 反序列化

```bash
# Marshal (高危)
grep -rn "Marshal\.load\|Marshal\.restore" --include="*.rb"

# YAML 不安全加载
grep -rn "YAML\.load\|Psych\.load" --include="*.rb"
# 注意: YAML.safe_load 是安全的

# JSON 多态
grep -rn "JSON\.load\|Oj\.load" --include="*.rb"
```

### 代码执行

```bash
# eval 系列
grep -rn "eval\|instance_eval\|class_eval\|module_eval" --include="*.rb"

# send/public_send
grep -rn "\.send\|\.public_send\|__send__" --include="*.rb"

# system/exec
grep -rn "system\|exec\|spawn\|popen\|backtick\|\`" --include="*.rb"
```

### SQL 注入

```bash
# 危险的 where 用法
grep -rn "where\s*(\s*[\"'].*#\{" --include="*.rb"
grep -rn "\.where\s*(\s*params\[" --include="*.rb"

# find_by_sql
grep -rn "find_by_sql\|execute\|select_all" --include="*.rb"

# order/group 注入
grep -rn "\.order\s*(\s*params\|\.group\s*(\s*params" --include="*.rb"
```

### 文件操作

```bash
grep -rn "File\.open\|File\.read\|File\.write\|IO\.read" --include="*.rb"
grep -rn "send_file\|send_data" --include="*.rb"
grep -rn "Pathname\.new\|Dir\.glob" --include="*.rb"
```

---

## Ruby 特定漏洞

### 1. Marshal 反序列化 RCE (严重)

```ruby
# 🔴 极度危险 - 可执行任意代码
data = Marshal.load(user_input)  # RCE!
data = Marshal.restore(cookies[:data])

# Gadget Chain 示例
# ERB template execution
payload = "\x04\bo:\bERB\x06:\t@srcI\"\x0f`id`\x06:\x06ET"

# 搜索模式
Marshal\.load|Marshal\.restore|Marshal\.dump.*用户输入
```

### 2. YAML 反序列化

```ruby
# 🔴 危险 (Ruby < 2.7 默认不安全)
data = YAML.load(user_input)  # RCE!
data = Psych.load(user_input)

# Payload 示例
# --- !ruby/object:Gem::Installer
# i: x
# --- !ruby/object:Gem::SpecFetcher
# i: y
# --- !ruby/object:Gem::Requirement
# requirements:
#   !ruby/object:Gem::Package::TarReader
#   io: &1 !ruby/object:Net::BufferedIO
#     io: &1 !ruby/object:Gem::Package::TarReader::Entry
#        read: 0
#        header: "abc"
#     debug_output: &1 !ruby/object:Net::WriteAdapter
#        socket: &1 !ruby/object:Gem::RequestSet
#            sets: !ruby/object:Net::WriteAdapter
#                socket: !ruby/module 'Kernel'
#                method_id: :system
#            git_set: id
#        method_id: :resolve

# 🟢 安全: 使用 safe_load
data = YAML.safe_load(user_input)
data = YAML.safe_load(user_input, permitted_classes: [Date, Time])

# 搜索模式
YAML\.load(?!_file)|Psych\.load(?!_file)
```

### 3. ERB 模板注入

```ruby
# 🔴 危险
template = ERB.new(user_input)
template.result(binding)  # RCE!

# 🔴 render 中的模板注入
render inline: params[:template]  # RCE!
render file: params[:file]  # 任意文件读取

# 🟢 安全: 不要使用用户输入作为模板
render template: "fixed_template"

# 搜索模式
ERB\.new.*params|render\s+inline:|render\s+file:.*params
```

### 4. 命令执行

```ruby
# 🔴 system/exec
system(user_command)
system("ls #{user_input}")  # 命令注入
exec(user_command)

# 🔴 反引号
output = `#{user_command}`
output = %x(#{user_command})

# 🔴 open 管道
file = open("|#{user_command}")  # 管道命令执行!
# open("| ls") 会执行 ls 命令

# 🔴 popen
IO.popen(user_command)
Open3.capture3(user_command)

# 🟢 安全: 使用数组参数（避免 shell 解析）
system("ls", "-la", user_path)  # 安全

# 搜索模式
system\s*\(|exec\s*\(|\`.*#\{|%x\(.*#\{|open\s*\(\s*[\"']\|
```

### 5. eval 代码执行

```ruby
# 🔴 eval
eval(user_input)  # RCE!

# 🔴 instance_eval/class_eval
obj.instance_eval(user_code)
klass.class_eval(user_code)

# 🔴 send/public_send (动态方法调用)
obj.send(user_method, *user_args)
obj.public_send(params[:method])

# 搜索模式
eval\s*\(|instance_eval|class_eval|module_eval
\.send\s*\(.*params|\.public_send\s*\(.*params
```

### 6. SQL 注入

```ruby
# 🔴 字符串插值
User.where("name = '#{params[:name]}'")
User.where("role = #{params[:role]}")

# 🔴 find_by_sql
User.find_by_sql("SELECT * FROM users WHERE name = '#{name}'")

# 🔴 order/group 注入
User.order(params[:sort])  # 可注入: "name; DROP TABLE users--"
User.group(params[:field])

# 🔴 pluck 列名注入
User.pluck(params[:column])  # 可注入任意表达式

# 🟢 安全: 使用占位符
User.where("name = ?", params[:name])
User.where(name: params[:name])  # Hash 形式

# 🟢 安全: order 白名单
allowed_sorts = %w[name created_at]
sort_col = allowed_sorts.include?(params[:sort]) ? params[:sort] : 'id'
User.order(sort_col)

# 搜索模式
where\s*\(\s*[\"'].*#\{|find_by_sql.*#\{
\.order\s*\(\s*params|\.group\s*\(\s*params|\.pluck\s*\(\s*params
```

### 7. 路径遍历

```ruby
# 🔴 危险
File.read(params[:file])  # ../../../etc/passwd
File.open(user_path, 'r')
send_file(params[:path])

# 🔴 拼接路径
path = "#{Rails.root}/uploads/#{params[:filename]}"
File.read(path)  # 路径遍历!

# 🟢 安全: 规范化并验证
filename = File.basename(params[:filename])  # 去除路径
full_path = File.expand_path(filename, upload_dir)
unless full_path.start_with?(upload_dir)
  raise SecurityError, "Path traversal detected"
end

# 搜索模式
File\.(read|open|write).*params|send_file.*params
```

### 8. 开放重定向

```ruby
# 🔴 危险
redirect_to params[:url]
redirect_to params[:return_to]

# 🟢 安全: 验证 URL
if params[:url].start_with?('/')  # 仅允许相对路径
  redirect_to params[:url]
end

# 或使用 URI 解析
uri = URI.parse(params[:url])
if uri.host.nil? || uri.host == request.host
  redirect_to params[:url]
end

# 搜索模式
redirect_to.*params
```

### 9. XSS

```ruby
# 🔴 raw/html_safe
<%= raw user_input %>
<%= user_input.html_safe %>

# 🔴 ERB 中的 JavaScript
<script>var data = '<%= params[:data] %>';</script>

# 🟢 安全: 默认转义
<%= user_input %>  # 自动转义

# 🟢 安全: 内容标签
<%= content_tag :div, user_input %>

# 搜索模式
raw\s+|\.html_safe|<%==
```

### 10. 不安全的随机数

```ruby
# 🔴 危险: 可预测
token = rand(1000000)
token = [*'a'..'z'].sample(8).join

# 🟢 安全: SecureRandom
token = SecureRandom.hex(32)
token = SecureRandom.urlsafe_base64(32)

# 搜索模式
rand\(|\.sample(?!.*SecureRandom)
```

---

## Rails 特定漏洞

### 1. Mass Assignment

```ruby
# 🔴 permit! 允许所有字段
params.require(:user).permit!

# 🔴 缺少 Strong Parameters
User.new(params[:user])  # Rails 4+ 会报错，但旧版本危险

# 🔴 漏掉敏感字段
params.require(:user).permit(:name, :email)  # 漏掉了 :admin

# 🟢 安全: 显式白名单
params.require(:user).permit(:name, :email)
# 并确保 :admin, :role 等敏感字段不在列表中

# 搜索模式
\.permit!|params\[:[a-z_]+\]\.permit(?!\()
```

### 2. CSRF 保护绕过

```ruby
# 🔴 禁用 CSRF 保护
class ApiController < ApplicationController
  skip_before_action :verify_authenticity_token  # 危险!
end

# 🔴 protect_from_forgery 配置错误
protect_from_forgery with: :null_session  # API 可能需要，但要小心

# 搜索模式
skip_before_action\s+:verify_authenticity_token|protect_from_forgery.*:null_session
```

### 3. ActionCable 安全

```ruby
# 🔴 未验证连接
module ApplicationCable
  class Connection < ActionCable::Connection::Base
    # 没有 identified_by 和验证
  end
end

# 🔴 频道订阅未鉴权
class ChatChannel < ApplicationCable::Channel
  def subscribed
    stream_from params[:room]  # room 可控!
  end
end

# 🟢 安全: 验证连接和订阅
module ApplicationCable
  class Connection < ActionCable::Connection::Base
    identified_by :current_user

    def connect
      self.current_user = find_verified_user
      reject_unauthorized_connection unless current_user
    end
  end
end

class ChatChannel < ApplicationCable::Channel
  def subscribed
    reject unless current_user.rooms.exists?(params[:room_id])
    stream_from "room_#{params[:room_id]}"
  end
end

# 搜索模式
stream_from.*params|ActionCable.*Connection(?!.*identified_by)
```

### 4. 不安全的 render

```ruby
# 🔴 render 任意文件
render file: params[:template]  # 任意文件读取!

# 🔴 render 模板注入
render inline: "<%= #{params[:code]} %>"  # RCE!

# 🔴 render JSON 中的敏感数据
render json: @user  # 可能包含 password_digest 等

# 🟢 安全
render json: @user.as_json(only: [:id, :name, :email])
render json: UserSerializer.new(@user)

# 搜索模式
render\s+file:.*params|render\s+inline:.*params
```

### 5. 会话安全

```ruby
# 🔴 会话固定
# 登录后未重置会话
session[:user_id] = user.id
# 应该先调用 reset_session

# 🔴 敏感数据存储在会话
session[:credit_card] = params[:cc_number]  # 不应存储敏感数据

# 🔴 CookieStore 泄露
# config/initializers/session_store.rb
Rails.application.config.session_store :cookie_store
# Cookie 中的数据可被解码（虽然签名）

# 🟢 安全: 登录时重置会话
reset_session
session[:user_id] = user.id

# 搜索模式
session\[:.+\]\s*=(?!.*reset_session)
```

### 6. 不安全的正则

```ruby
# 🔴 ReDoS
validates :email, format: { with: /^([a-zA-Z0-9]+)+@/ }  # 灾难性回溯

# 🔴 多行模式问题
content =~ /^admin$/  # ^ 和 $ 匹配每行，不是整个字符串
# "user\nadmin" 会匹配!

# 🟢 安全: 使用 \A 和 \z
content =~ /\Aadmin\z/

# 搜索模式
/\^.*\$/ # 可能需要改为 \A \z
```

---

## Sinatra 特定漏洞

```ruby
# 🔴 CSRF 默认不启用
# Sinatra 不像 Rails 默认有 CSRF 保护

# 🔴 erb 模板注入
erb params[:template].to_sym  # 任意模板!

# 🔴 send_file 路径遍历
get '/download' do
  send_file params[:file]  # 路径遍历!
end

# 🟢 安全: 使用 rack-csrf
use Rack::Csrf, :raise => true
```

---

## 审计清单

```
反序列化:
- [ ] 搜索 Marshal.load/restore
- [ ] 搜索 YAML.load (非 safe_load)
- [ ] 检查 cookie 中的序列化数据

代码执行:
- [ ] 搜索 eval/instance_eval
- [ ] 搜索 system/exec/popen
- [ ] 搜索 send/public_send + 用户输入
- [ ] 检查 open() 管道用法

SQL 注入:
- [ ] 搜索 where 字符串插值
- [ ] 搜索 find_by_sql
- [ ] 检查 order/group/pluck 参数

Rails 特定:
- [ ] 检查 permit! 使用
- [ ] 验证 CSRF 保护
- [ ] 检查 ActionCable 授权
- [ ] 验证 render 用法

文件操作:
- [ ] 检查 File.read/open
- [ ] 检查 send_file
- [ ] 验证路径处理
```

---

## 审计正则

```regex
# 反序列化
Marshal\.(load|restore)|YAML\.load(?!_file)|Psych\.load(?!_file)

# 代码执行
eval\s*\(|instance_eval|class_eval|module_eval
\.send\s*\(.*params|\.public_send\s*\(
system\s*\(.*#\{|exec\s*\(|popen\s*\(|\`.*#\{
open\s*\(\s*[\"']\|

# SQL 注入
where\s*\(\s*[\"'].*#\{|find_by_sql.*#\{
\.order\s*\(\s*params|\.group\s*\(\s*params

# XSS
raw\s+|\.html_safe|<%==

# 文件操作
File\.(read|open|write).*params|send_file.*params

# Rails 特定
\.permit!|skip_before_action\s+:verify_authenticity_token
render\s+(file|inline):.*params
```

---

## 工具推荐

```bash
# Brakeman (Rails 静态分析)
gem install brakeman
brakeman /path/to/rails/app

# bundler-audit (依赖漏洞)
gem install bundler-audit
bundle audit check --update

# RuboCop 安全规则
# .rubocop.yml
require:
  - rubocop-rails
Rails/OutputSafety:
  Enabled: true
```

---

## SSRF 安全 (CWE-918)

### 危险模式

```ruby
# 🔴 直接使用用户输入的 URL
def fetch_url
  url = params[:url]
  response = Net::HTTP.get(URI(url))  # 可访问内网
  render plain: response
end

# 🔴 Open-URI
require 'open-uri'
def download
  content = URI.open(params[:url]).read  # SSRF
  render plain: content
end

# 🔴 RestClient
def proxy
  response = RestClient.get(params[:target])  # SSRF
  render json: response.body
end
```

### 安全配置

```ruby
require 'ipaddr'
require 'resolv'

ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com'].freeze
BLOCKED_NETWORKS = [
  IPAddr.new('10.0.0.0/8'),
  IPAddr.new('172.16.0.0/12'),
  IPAddr.new('192.168.0.0/16'),
  IPAddr.new('127.0.0.0/8'),
  IPAddr.new('169.254.0.0/16'),
  IPAddr.new('::1/128'),
  IPAddr.new('fc00::/7'),
].freeze

def safe_fetch(url)
  uri = URI.parse(url)

  # 1. 协议白名单
  unless %w[http https].include?(uri.scheme)
    raise SecurityError, 'Invalid scheme'
  end

  # 2. 主机白名单
  unless ALLOWED_HOSTS.include?(uri.host)
    # 3. 解析 IP 并检查
    ip = Resolv.getaddress(uri.host)
    ip_addr = IPAddr.new(ip)

    if BLOCKED_NETWORKS.any? { |net| net.include?(ip_addr) }
      raise SecurityError, 'Internal network access denied'
    end
  end

  # 4. 禁止重定向或限制重定向次数
  response = Net::HTTP.get_response(uri)
  if response.is_a?(Net::HTTPRedirection)
    raise SecurityError, 'Redirects not allowed'
  end

  response.body
end
```

### 检测命令

```bash
# 查找 HTTP 请求
rg -n "Net::HTTP|RestClient|HTTParty|Faraday|URI\.open|open-uri" --glob "*.rb"

# 查找用户输入作为 URL
rg -n "params\[:url\]|params\[:target\]|params\[:endpoint\]" --glob "*.rb"
```

---

## 硬编码凭据 (CWE-798)

### 危险模式

```ruby
# 🔴 硬编码密钥
class ApplicationController < ActionController::Base
  SECRET_KEY = 'my-super-secret-key-12345'  # 🔴

  def encrypt(data)
    cipher = OpenSSL::Cipher.new('AES-256-CBC')
    cipher.encrypt
    cipher.key = Digest::SHA256.digest(SECRET_KEY)  # 🔴
    # ...
  end
end

# 🔴 数据库密码
database.yml:
production:
  password: admin123  # 🔴 硬编码

# 🔴 API 密钥
class PaymentService
  API_KEY = 'sk_live_xxxxxxxxxxxx'  # 🔴
end
```

### 安全配置

```ruby
# config/credentials.yml.enc (Rails 5.2+)
# 使用 rails credentials:edit 编辑

# 读取凭据
Rails.application.credentials.secret_key_base
Rails.application.credentials.dig(:aws, :access_key_id)

# 或使用环境变量
class PaymentService
  def api_key
    ENV.fetch('PAYMENT_API_KEY') { raise 'PAYMENT_API_KEY not set' }
  end
end

# database.yml 使用 ERB
production:
  password: <%= ENV['DATABASE_PASSWORD'] %>

# 使用 dotenv (开发环境)
# Gemfile
gem 'dotenv-rails', groups: [:development, :test]

# .env (不提交到版本控制)
DATABASE_PASSWORD=xxx
API_KEY=xxx
```

### 检测命令

```bash
# 查找硬编码密钥
rg -n "password\s*[:=]|secret\s*[:=]|api_key\s*[:=]|token\s*[:=]" --glob "*.rb" --glob "*.yml" | grep -v "ENV\|credentials\|<%= "

# 查找常量定义的密钥
rg -n "[A-Z_]+\s*=\s*['\"][^'\"]{8,}['\"]" --glob "*.rb"

# 查找配置文件中的硬编码
rg -n "password:<REDACTED>" --glob "*.yml" | grep -v "<%= "
```

---

## 文件上传安全 (CWE-434)

### 危险模式

```ruby
# 🔴 无验证上传
def upload
  uploaded = params[:file]
  File.open(Rails.root.join('uploads', uploaded.original_filename), 'wb') do |f|
    f.write(uploaded.read)  # 🔴 任意文件名 + 任意类型
  end
end
```

### 安全配置 (ActiveStorage)

```ruby
# config/initializers/active_storage.rb
Rails.application.config.active_storage.content_types_allowed_inline = %w[
  image/png image/gif image/jpeg image/webp
]

# Model 验证
class User < ApplicationRecord
  has_one_attached :avatar

  validate :acceptable_avatar

  def acceptable_avatar
    return unless avatar.attached?

    # 大小限制
    if avatar.blob.byte_size > 5.megabytes
      errors.add(:avatar, 'is too big (max 5MB)')
    end

    # 类型限制
    acceptable_types = %w[image/jpeg image/png image/gif]
    unless acceptable_types.include?(avatar.content_type)
      errors.add(:avatar, 'must be JPEG, PNG or GIF')
    end
  end
end

# Controller
def update
  if current_user.update(user_params)
    redirect_to current_user
  else
    render :edit
  end
end

private

def user_params
  params.require(:user).permit(:name, :avatar)
end
```

---

## 竞态条件 (CWE-362)

### 危险模式

```ruby
# 1. Check-Then-Act (TOCTOU) - 数据库操作
# 危险: 检查与操作之间存在竞态窗口
class OrdersController < ApplicationController
  def create
    product = Product.find(params[:product_id])

    if product.stock > 0  # 检查
      # 竞态窗口: 另一请求可能同时减库存
      product.update(stock: product.stock - 1)  # 操作
      Order.create(user: current_user, product: product)
    else
      render json: { error: 'Out of stock' }, status: 422
    end
  end
end

# 安全: 使用数据库原子操作
class OrdersController < ApplicationController
  def create
    product = Product.find(params[:product_id])

    # 原子减库存，返回受影响行数
    updated = Product.where(id: product.id)
                     .where('stock > 0')
                     .update_all('stock = stock - 1')

    if updated > 0
      Order.create(user: current_user, product: product)
    else
      render json: { error: 'Out of stock' }, status: 422
    end
  end
end


# 2. 悲观锁定
# 安全: 使用 with_lock
class TransfersController < ApplicationController
  def create
    ActiveRecord::Base.transaction do
      from_account = Account.lock.find(params[:from_id])  # SELECT ... FOR UPDATE
      to_account = Account.lock.find(params[:to_id])

      if from_account.balance >= params[:amount].to_d
        from_account.update!(balance: from_account.balance - params[:amount].to_d)
        to_account.update!(balance: to_account.balance + params[:amount].to_d)
      else
        raise ActiveRecord::Rollback
      end
    end
  end
end

# 或使用 with_lock 块
Account.transaction do
  account = Account.find(id)
  account.with_lock do
    account.balance -= amount
    account.save!
  end
end


# 3. 乐观锁定
# Model 配置
class Product < ApplicationRecord
  # 需要 lock_version 列 (integer, default: 0)
end

# 使用乐观锁
def update
  product = Product.find(params[:id])
  product.update!(product_params)
rescue ActiveRecord::StaleObjectError
  # 数据已被其他请求修改
  render json: { error: 'Record was modified by another user' }, status: 409
end


# 4. 唯一性验证竞态
# 危险: 应用层验证存在竞态
class User < ApplicationRecord
  validates :email, uniqueness: true  # 仅应用层检查
end

# 安全: 数据库唯一约束 + 异常处理
# migration
add_index :users, :email, unique: true

# model
class User < ApplicationRecord
  validates :email, uniqueness: true

  def self.create_with_retry(attrs)
    create!(attrs)
  rescue ActiveRecord::RecordNotUnique
    # 处理并发创建
    find_by(email: attrs[:email])
  end
end


# 5. 文件操作竞态
# 危险
def save_file(filename, content)
  unless File.exist?(filename)  # 检查
    # 竞态窗口
    File.write(filename, content)  # 操作
  end
end

# 安全: 使用原子操作
require 'tempfile'

def safe_save_file(filename, content)
  dir = File.dirname(filename)
  Tempfile.create('upload', dir) do |temp|
    temp.write(content)
    temp.close
    File.rename(temp.path, filename)  # 原子操作
  end
end

# 安全: 使用排他锁
def exclusive_write(filename, content)
  File.open(filename, File::CREAT | File::EXCL | File::WRONLY) do |f|
    f.write(content)
  end
rescue Errno::EEXIST
  # 文件已存在
end


# 6. Redis 分布式锁
# 使用 redlock gem
require 'redlock'

lock_manager = Redlock::Client.new([redis_url])

def with_distributed_lock(key, &block)
  lock_info = lock_manager.lock("lock:#{key}", 10_000)  # 10秒超时
  raise 'Could not acquire lock' unless lock_info

  begin
    yield
  ensure
    lock_manager.unlock(lock_info)
  end
end

# 使用
with_distributed_lock("order:#{product_id}") do
  # 临界区代码
end
```

### 检测命令

```bash
# 查找 check-then-act 模式
grep -rn "if.*\.present?\|if.*\.exists?\|if.*\.any?\|if.*> 0" --include="*.rb" -A 3

# 查找非原子更新
grep -rn "\.update.*\.count\|\.update.*\.size\|\.update.*\+\|\.update.*-" --include="*.rb"

# 查找文件存在检查
grep -rn "File\.exist?\|File\.exists?" --include="*.rb"

# 查找缺少锁的事务
grep -rn "ActiveRecord::Base\.transaction" --include="*.rb" | grep -v "lock"
```

---

## 权限管理 (CWE-269/276)

### 默认权限问题

```ruby
# 危险: 缺少授权检查
class AdminController < ApplicationController
  def users
    @users = User.all  # 任何登录用户都能访问
  end
end

# 安全: 使用 Pundit
class AdminController < ApplicationController
  before_action :authorize_admin

  def users
    @users = policy_scope(User)
  end

  private

  def authorize_admin
    authorize :admin, :access?
  end
end

# Pundit Policy
class AdminPolicy < ApplicationPolicy
  def access?
    user.admin? || user.super_admin?
  end
end


# 危险: 权限提升漏洞
class UsersController < ApplicationController
  def update
    @user = User.find(params[:id])
    @user.update(user_params)  # 可能包含 role 参数
  end

  private

  def user_params
    params.require(:user).permit(:name, :email, :role)  # 危险: 允许修改角色
  end
end

# 安全: 分离权限参数
class UsersController < ApplicationController
  def update
    @user = User.find(params[:id])
    authorize @user
    @user.update(user_params)
  end

  def promote
    @user = User.find(params[:id])
    authorize @user, :promote?

    # 验证不能提升到比自己更高的角色
    if role_level(params[:role]) >= role_level(current_user.role)
      render json: { error: 'Cannot grant higher role' }, status: 403
      return
    end

    @user.update(role: params[:role])
    AuditLog.create(action: 'promote', target: @user, actor: current_user)
  end

  private

  def user_params
    params.require(:user).permit(:name, :email)  # 不包含 role
  end
end

# Pundit Policy
class UserPolicy < ApplicationPolicy
  def promote?
    user.super_admin?
  end
end


# 危险: 默认公开资源
class Document < ApplicationRecord
  # 没有默认权限设置
end

# 安全: 默认私有
class Document < ApplicationRecord
  enum visibility: { private_doc: 0, internal: 1, public_doc: 2 }

  after_initialize :set_defaults, if: :new_record?

  private

  def set_defaults
    self.visibility ||= :private_doc  # 默认私有
  end
end


# CanCanCan 权限配置
class Ability
  include CanCan::Ability

  def initialize(user)
    user ||= User.new  # 游客

    # 默认无权限
    cannot :manage, :all

    if user.persisted?
      # 登录用户基础权限
      can :read, Document, visibility: 'public_doc'
      can :manage, Document, user_id: user.id  # 自己的文档

      if user.admin?
        can :manage, Document
        can :read, User
      end

      if user.super_admin?
        can :manage, :all
      end
    else
      # 游客只能看公开文档
      can :read, Document, visibility: 'public_doc'
    end
  end
end
```

### 敏感操作审计

```ruby
# 审计日志
class AuditLog < ApplicationRecord
  belongs_to :actor, class_name: 'User'
  belongs_to :target, polymorphic: true, optional: true

  validates :action, presence: true

  scope :recent, -> { order(created_at: :desc).limit(100) }
  scope :by_actor, ->(user) { where(actor: user) }
  scope :sensitive, -> { where(action: %w[promote delete export]) }
end

# 在敏感操作中使用
class UsersController < ApplicationController
  def destroy
    @user = User.find(params[:id])
    authorize @user

    ActiveRecord::Base.transaction do
      AuditLog.create!(
        action: 'delete_user',
        actor: current_user,
        target: @user,
        metadata: { email: @user.email, role: @user.role }
      )
      @user.destroy!
    end

    redirect_to users_path, notice: 'User deleted'
  end
end
```

### 检测命令

```bash
# 查找缺少授权的控制器
grep -rn "class.*Controller" --include="*.rb" -A 10 | grep -v "authorize\|before_action.*:authenticate"

# 查找 permit 中的敏感字段
grep -rn "permit.*:role\|permit.*:admin\|permit.*:password" --include="*.rb"

# 查找直接角色赋值
grep -rn "\.role\s*=\|update.*role:" --include="*.rb"

# 查找缺少 policy 的模型
find app/models -name "*.rb" -exec basename {} .rb \; | while read model; do
  [ ! -f "app/policies/${model}_policy.rb" ] && echo "Missing policy: $model"
done
```

---

**版本**: 2.1
**更新日期**: 2026-02-04
**覆盖漏洞类型**: 24+ (含CWE-362/269/276)
