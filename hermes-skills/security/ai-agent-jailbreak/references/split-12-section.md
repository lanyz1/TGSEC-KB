## 十、多域名横向移动

### 10.1 关联域名发现

通过首页 HTML 提取所有外链域名（博彩网络通常共享同一个用户数据库）：
```python
domains = set(re.findall(r'https?://([^/"\'\]\s]+)', homepage_html))
```

### 10.2 凭证复用

同一套用户系统可能运行在多个域名上：
- 一个域名注册账号 → 其他域名也可登录
- 登录 API 格式相同（同一个后端）
- 验证码机制一致（固定值或相同算法）

### 10.3 不同域名不同系统

| 域名类型 | 技术栈 | 典型路径 | 登录方式 |
|:---------|:-------|:---------|:---------|
| 主站 (desktop) | 老版 PHP + module/method | /cl/index.php | 传统表单 + 验证码 |
| 移动版 (mobile) | React SPA + API | /m/login | API + client_id |
| 红包/活动站 | 独立 PHP | /redbag/ | 无登录或第三方 |
| 重构版 (ThinkPHP) | ThinkPHP 5 | /index/user/login | API + 固定验证码 |

### 10.4 数据聚合

从不同域名收集的信息可以组合利用：
```
域名A: 找到 API 端点 (/api/Public/main/index.php)
域名B: 发现 JS 配置 (website = location.host)  
域名C: 获得可用账号 (固定验证码 1111)
域名D: 找到 ThinkPHP Debug 信息 (框架版本、文件路径)
→ 组合后对主站进行更精准的渗透
```

---

