# 前端框架安全 (Frontend Framework Security)

> React / Vue / Angular / Svelte 安全审计指南
> XSS 防护、状态管理安全、CSP 配置、依赖安全

---

## 核心风险

| 风险类型 | 描述 | CWE |
|----------|------|-----|
| XSS (DOM-based) | 前端渲染不当导致脚本执行 | CWE-79 |
| 原型污染 | 通过对象操作污染原型链 | CWE-1321 |
| 敏感数据泄露 | 前端存储/暴露敏感信息 | CWE-200 |
| CSRF | 跨站请求伪造 | CWE-352 |
| 开放重定向 | 不安全的 URL 跳转 | CWE-601 |
| 依赖漏洞 | 第三方库安全问题 | CWE-1395 |

---

## 一键检测命令

### React XSS 风险

```bash
# dangerouslySetInnerHTML
grep -rn "dangerouslySetInnerHTML" --include="*.jsx" --include="*.tsx" --include="*.js"

# href javascript:
grep -rn "href.*javascript:" --include="*.jsx" --include="*.tsx"

# eval/Function
grep -rn "eval\|new Function" --include="*.jsx" --include="*.tsx" --include="*.js"

# innerHTML (原生 DOM)
grep -rn "\.innerHTML\s*=" --include="*.jsx" --include="*.tsx" --include="*.js"
```

### Vue XSS 风险

```bash
# v-html 指令
grep -rn "v-html" --include="*.vue"

# 模板中的 {{{ }}} (Vue 1.x)
grep -rn "{{{.*}}}" --include="*.vue"

# domProps innerHTML
grep -rn "domProps.*innerHTML" --include="*.vue" --include="*.js"

# $el.innerHTML
grep -rn "\$el\.innerHTML" --include="*.vue" --include="*.js"
```

### Angular XSS 风险

```bash
# bypassSecurityTrust*
grep -rn "bypassSecurityTrust" --include="*.ts" --include="*.html"

# innerHTML 绑定
grep -rn "\[innerHTML\]" --include="*.html"

# ElementRef.nativeElement
grep -rn "nativeElement\.innerHTML" --include="*.ts"
```

### 通用检测

```bash
# localStorage/sessionStorage 敏感数据
grep -rn "localStorage\|sessionStorage" --include="*.js" --include="*.ts" --include="*.jsx" --include="*.tsx" --include="*.vue"

# 硬编码密钥
grep -rn "apiKey\|api_key\|secret\|password" --include="*.js" --include="*.ts" --include="*.jsx" --include="*.tsx"

# eval 类危险函数
grep -rn "eval\|setTimeout.*string\|setInterval.*string\|new Function" --include="*.js" --include="*.ts"
```

---

## React 安全

### 1. XSS 漏洞

```jsx
// 🔴 dangerouslySetInnerHTML - 最常见的 React XSS
function Comment({ content }) {
    return <div dangerouslySetInnerHTML={{ __html: content }} />;
}

// 攻击: content = '<img src=x onerror=alert(1)>'

// 🟢 安全: 使用文本节点或 DOMPurify
import DOMPurify from 'dompurify';

function Comment({ content }) {
    // 方案1: 纯文本
    return <div>{content}</div>;

    // 方案2: 需要 HTML 时使用 DOMPurify
    return <div dangerouslySetInnerHTML={{
        __html: DOMPurify.sanitize(content)
    }} />;
}
```

```jsx
// 🔴 href="javascript:" XSS
function Link({ url, text }) {
    return <a href={url}>{text}</a>;
}
// 攻击: url = 'javascript:alert(1)'

// 🟢 安全: 验证 URL 协议
function Link({ url, text }) {
    const isValidUrl = (url) => {
        try {
            const parsed = new URL(url);
            return ['http:', 'https:', 'mailto:'].includes(parsed.protocol);
        } catch {
            return false;
        }
    };

    return isValidUrl(url)
        ? <a href={url}>{text}</a>
        : <span>{text}</span>;
}
```

```jsx
// 🔴 动态属性注入
function UserProfile({ data }) {
    return <div {...data}>Profile</div>;  // 可注入 dangerouslySetInnerHTML
}

// 攻击: data = { dangerouslySetInnerHTML: { __html: '<script>alert(1)</script>' } }

// 🟢 安全: 白名单属性
function UserProfile({ data }) {
    const safeProps = {
        className: data.className,
        id: data.id,
        style: data.style
    };
    return <div {...safeProps}>Profile</div>;
}
```

### 2. 状态管理安全

```jsx
// 🔴 Redux 中存储敏感数据
const userSlice = createSlice({
    name: 'user',
    initialState: {
        token: localStorage.getItem('token'),  // 暴露在 Redux DevTools
        creditCard: ''  // 敏感数据
    }
});

// 🟢 安全: 敏感数据不存入 Redux
// 使用 httpOnly cookie 存储 token
// 或使用加密的 sessionStorage
```

### 3. 服务端渲染 (SSR) 安全

```jsx
// 🔴 Next.js getServerSideProps 泄露
export async function getServerSideProps() {
    const apiKey = <REDACTED>;
    const data = await fetchData(apiKey);

    return {
        props: {
            data,
            apiKey  // 🔴 泄露到客户端!
        }
    };
}

// 🟢 安全: 只传递必要数据
export async function getServerSideProps() {
    const apiKey = <REDACTED>;
    const data = await fetchData(apiKey);

    return {
        props: {
            data  // 不包含 apiKey
        }
    };
}
```

---

## Vue 安全

### 1. XSS 漏洞

```vue
<!-- 🔴 v-html 指令 -->
<template>
    <div v-html="userContent"></div>
</template>

<!-- 攻击: userContent = '<img src=x onerror=alert(1)>' -->

<!-- 🟢 安全: 使用 DOMPurify -->
<template>
    <div v-html="sanitizedContent"></div>
</template>

<script>
import DOMPurify from 'dompurify';

export default {
    computed: {
        sanitizedContent() {
            return DOMPurify.sanitize(this.userContent);
        }
    }
}
</script>
```

```vue
<!-- 🔴 动态组件名 -->
<component :is="userInput" />
<!-- 攻击: userInput = 'script' 可能导致问题 -->

<!-- 🟢 安全: 白名单验证 -->
<script>
const allowedComponents = ['UserCard', 'ProductCard', 'CommentCard'];

export default {
    computed: {
        safeComponent() {
            return allowedComponents.includes(this.userInput)
                ? this.userInput
                : 'DefaultCard';
        }
    }
}
</script>
```

```vue
<!-- 🔴 :href 绑定 -->
<a :href="userUrl">Link</a>
<!-- 攻击: userUrl = 'javascript:alert(1)' -->

<!-- 🟢 安全: 验证 URL -->
<template>
    <a :href="safeUrl">Link</a>
</template>

<script>
export default {
    computed: {
        safeUrl() {
            try {
                const url = new URL(this.userUrl);
                if (['http:', 'https:'].includes(url.protocol)) {
                    return this.userUrl;
                }
            } catch {}
            return '#';
        }
    }
}
</script>
```

### 2. Vue 3 特定问题

```javascript
// 🔴 Composition API 响应式数据泄露
import { reactive } from 'vue';

const state = reactive({
    user: {
        password: 'secret'  // 可通过 Vue DevTools 看到
    }
});

// 🟢 安全: 使用 shallowRef 或不存储敏感数据
import { shallowRef } from 'vue';
const sensitiveData = shallowRef(null);  // 不会深度追踪
```

### 3. Nuxt.js 安全

```javascript
// 🔴 nuxt.config.js 暴露敏感配置
export default {
    publicRuntimeConfig: {
        apiKey: <REDACTED>  // 🔴 会暴露到客户端
    }
};

// 🟢 安全: 使用 privateRuntimeConfig
export default {
    privateRuntimeConfig: {
        apiKey: <REDACTED>  // 只在服务端可用
    },
    publicRuntimeConfig: {
        apiUrl: process.env.API_URL  // 公开信息
    }
};
```

---

## Angular 安全

### 1. XSS 漏洞

```typescript
// 🔴 bypassSecurityTrust* 方法
import { DomSanitizer } from '@angular/platform-browser';

@Component({...})
export class UnsafeComponent {
    constructor(private sanitizer: DomSanitizer) {}

    getHtml(content: string) {
        // 🔴 完全绕过安全检查
        return this.sanitizer.bypassSecurityTrustHtml(content);
    }
}

// 🟢 安全: 仅对可信内容使用，或使用 DOMPurify
import DOMPurify from 'dompurify';

getHtml(content: string) {
    const clean = DOMPurify.sanitize(content);
    return this.sanitizer.bypassSecurityTrustHtml(clean);
}
```

```html
<!-- 🔴 [innerHTML] 绑定 -->
<div [innerHTML]="userContent"></div>

<!-- Angular 会自动净化，但某些情况下可能被绕过 -->
<!-- 🟢 更安全: 使用插值 -->
<div>{{ userContent }}</div>

<!-- 如果需要 HTML，使用 DOMPurify -->
<div [innerHTML]="sanitize(userContent)"></div>
```

```typescript
// 🔴 ElementRef 直接 DOM 操作
@Component({...})
export class DangerousComponent {
    constructor(private el: ElementRef) {}

    ngOnInit() {
        // 🔴 绕过 Angular 安全机制
        this.el.nativeElement.innerHTML = this.userContent;
    }
}

// 🟢 安全: 使用 Renderer2
import { Renderer2 } from '@angular/core';

@Component({...})
export class SafeComponent {
    constructor(private renderer: Renderer2, private el: ElementRef) {}

    setContent(text: string) {
        const textNode = this.renderer.createText(text);
        this.renderer.appendChild(this.el.nativeElement, textNode);
    }
}
```

### 2. 模板注入

```typescript
// 🔴 动态模板编译 (AOT 模式下不可用，但 JIT 模式危险)
@Component({
    template: userTemplate  // 🔴 用户控制模板
})
export class DynamicComponent {}

// 🟢 安全: 使用预定义模板
```

### 3. 路由安全

```typescript
// 🔴 开放重定向
@Component({...})
export class LoginComponent {
    constructor(private router: Router) {}

    onLogin() {
        const returnUrl = this.route.snapshot.queryParams['returnUrl'];
        this.router.navigateByUrl(returnUrl);  // 🔴 可能重定向到恶意站点
    }
}

// 🟢 安全: 验证 URL
onLogin() {
    const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
    if (returnUrl.startsWith('/') && !returnUrl.startsWith('//')) {
        this.router.navigateByUrl(returnUrl);
    } else {
        this.router.navigateByUrl('/');
    }
}
```

---

## 通用安全问题

### 1. 本地存储安全

```javascript
// 🔴 在 localStorage 存储敏感数据
localStorage.setItem('authToken', token);
localStorage.setItem('user', JSON.stringify({ password: 'secret' }));

// 风险:
// - XSS 可以读取 localStorage
// - 没有过期机制
// - 跨标签页共享

// 🟢 安全替代方案
// 1. 使用 httpOnly cookie (后端设置)
// 2. 使用 sessionStorage (会话级别)
// 3. 内存中存储 (刷新丢失，但更安全)

// 如果必须使用 localStorage，加密存储
import CryptoJS from 'crypto-js';

const encryptedToken = CryptoJS.AES.encrypt(token, SECRET_KEY).toString();
localStorage.setItem('authToken', encryptedToken);
```

### 2. CSP (内容安全策略)

```html
<!-- 🟢 推荐的 CSP 配置 -->
<meta http-equiv="Content-Security-Policy" content="
    default-src 'self';
    script-src 'self' 'nonce-RANDOM_NONCE';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    font-src 'self';
    connect-src 'self' https://api.example.com;
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
">

<!-- React/Vue/Angular 需要的调整 -->
<!-- 开发环境可能需要 'unsafe-eval' 但生产环境应移除 -->
```

```javascript
// Next.js CSP 配置 (next.config.js)
const securityHeaders = [
    {
        key: 'Content-Security-Policy',
        value: `
            default-src 'self';
            script-src 'self' 'unsafe-inline' 'unsafe-eval';
            style-src 'self' 'unsafe-inline';
        `.replace(/\s{2,}/g, ' ').trim()
    }
];

module.exports = {
    async headers() {
        return [{
            source: '/:path*',
            headers: securityHeaders
        }];
    }
};
```

### 3. 第三方脚本安全

```html
<!-- 🔴 直接加载第三方脚本 -->
<script src="https://cdn.example.com/library.js"></script>

<!-- 🟢 安全: 使用 SRI (Subresource Integrity) -->
<script
    src="https://cdn.example.com/library.js"
    integrity="sha384-HASH_VALUE"
    crossorigin="anonymous"
></script>
```

```javascript
// 检查依赖安全
// package.json 审计
npm audit
yarn audit

// 检查已知漏洞
npx snyk test
```

### 4. postMessage 安全

```javascript
// 🔴 不验证来源的 postMessage
window.addEventListener('message', (event) => {
    // 🔴 没有验证 origin
    const data = event.data;
    document.getElementById('content').innerHTML = data;  // XSS!
});

// 🟢 安全: 验证 origin
window.addEventListener('message', (event) => {
    // 验证来源
    if (event.origin !== 'https://trusted-site.com') {
        return;
    }

    // 验证数据类型
    if (typeof event.data !== 'object' || !event.data.type) {
        return;
    }

    // 安全处理
    if (event.data.type === 'updateContent') {
        document.getElementById('content').textContent = event.data.value;
    }
});
```

### 5. WebSocket 安全

```javascript
// 🔴 不验证的 WebSocket 消息
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    element.innerHTML = data.content;  // XSS!
};

// 🟢 安全
socket.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);

        // 验证消息类型
        if (!['chat', 'notification'].includes(data.type)) {
            return;
        }

        // 安全渲染
        element.textContent = data.content;
    } catch (e) {
        console.error('Invalid message');
    }
};
```

---

## 构建与部署安全

### 1. 环境变量

```javascript
// 🔴 暴露敏感环境变量
// .env
REACT_APP_API_KEY=secret_key  // REACT_APP_ 前缀会暴露到客户端
NEXT_PUBLIC_SECRET=xxx        // NEXT_PUBLIC_ 前缀会暴露

// 🟢 安全: 敏感变量不使用公开前缀
// .env
API_KEY=<REDACTED>            // 不会暴露
NEXT_PUBLIC_API_URL=https://api.example.com  // 公开信息可以
```

### 2. Source Map

```javascript
// 🔴 生产环境暴露 Source Map
// webpack.config.js
module.exports = {
    devtool: 'source-map'  // 🔴 生产环境应禁用
};

// 🟢 安全: 生产环境禁用或使用隐藏 Source Map
module.exports = {
    devtool: process.env.NODE_ENV === 'production'
        ? false  // 或 'hidden-source-map'
        : 'eval-source-map'
};
```

### 3. 依赖锁定

```bash
# 🟢 使用锁定文件
package-lock.json  # npm
yarn.lock          # yarn
pnpm-lock.yaml     # pnpm

# 检查依赖漏洞
npm audit --production
yarn audit --groups dependencies

# 自动修复
npm audit fix
```

---

## 审计清单

```
XSS 防护:
- [ ] 检查 dangerouslySetInnerHTML (React)
- [ ] 检查 v-html (Vue)
- [ ] 检查 bypassSecurityTrust* (Angular)
- [ ] 检查 innerHTML 直接操作
- [ ] 验证 href/src 动态绑定

数据安全:
- [ ] 检查 localStorage 敏感数据
- [ ] 检查环境变量暴露
- [ ] 验证 SSR 数据泄露
- [ ] 检查 Redux/Vuex DevTools 暴露

安全配置:
- [ ] 验证 CSP 配置
- [ ] 检查 Source Map 配置
- [ ] 验证 SRI 使用
- [ ] 检查 postMessage origin 验证

依赖安全:
- [ ] 运行 npm/yarn audit
- [ ] 检查已知漏洞组件
- [ ] 验证依赖锁定文件
```

---

## 审计正则

```regex
# React XSS
dangerouslySetInnerHTML|href.*javascript:

# Vue XSS
v-html|{{{.*}}}|domProps.*innerHTML

# Angular XSS
bypassSecurityTrust|\[innerHTML\]|nativeElement\.innerHTML

# 通用
innerHTML\s*=|eval\s*\(|new\s+Function
localStorage\.setItem.*token|sessionStorage.*password
REACT_APP_.*KEY|NEXT_PUBLIC_.*SECRET|VUE_APP_.*KEY
```

---

**版本**: 1.0
**更新日期**: 2026-02-04
**覆盖框架**: React, Vue, Angular, Svelte, Next.js, Nuxt.js
