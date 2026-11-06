# NestJS / Fastify Security Audit

> NestJS 和 Fastify 框架安全审计模块
> 适用于: NestJS, Fastify, Express (NestJS 默认), TypeScript 后端

## 识别特征

```typescript
// NestJS 项目识别
nest-cli.json, tsconfig.json
*.module.ts, *.controller.ts, *.service.ts

// Fastify 项目识别
fastify.register, fastify.route

// 文件结构 (NestJS)
├── src/
│   ├── app.module.ts
│   ├── main.ts
│   ├── auth/
│   ├── users/
│   └── common/
├── nest-cli.json
└── package.json
```

---

## 一键检测命令

### 认证授权

```bash
# Guard 使用
grep -rn "@UseGuards\|CanActivate\|AuthGuard" --include="*.ts"

# 公开端点
grep -rn "@Public\|@AllowAnonymous\|SetMetadata.*isPublic" --include="*.ts"

# JWT 配置
grep -rn "JwtModule\|JwtService\|sign\|verify" --include="*.ts"
```

### 输入验证

```bash
# ValidationPipe
grep -rn "ValidationPipe\|class-validator\|class-transformer" --include="*.ts"

# DTO 验证装饰器
grep -rn "@IsString\|@IsNumber\|@IsEmail\|@Matches" --include="*.ts"

# 缺失验证
grep -rn "@Body()\|@Query()\|@Param()" --include="*.ts"
```

### WebSocket/实时

```bash
# WebSocket Gateway
grep -rn "@WebSocketGateway\|@SubscribeMessage\|WsException" --include="*.ts"

# SSE
grep -rn "@Sse\|Observable\|interval" --include="*.ts"
```

### CORS/安全头

```bash
grep -rn "enableCors\|CorsOptions\|origin:" --include="*.ts"
grep -rn "helmet\|csp\|X-Frame-Options" --include="*.ts"
```

### 文件操作

```bash
grep -rn "FileInterceptor\|FilesInterceptor\|@UploadedFile" --include="*.ts"
grep -rn "createReadStream\|createWriteStream\|fs\." --include="*.ts"
```

---

## NestJS 特定漏洞

### 1. Guard 绕过

```typescript
// 🔴 全局 Guard 被局部 @Public() 绕过
// app.module.ts
@Module({
  providers: [{ provide: APP_GUARD, useClass: JwtAuthGuard }]
})
export class AppModule {}

// users.controller.ts
@Public()  // 绕过全局 Guard!
@Get('sensitive')
getSensitiveData() { ... }

// 🔴 Guard 顺序问题
@UseGuards(RolesGuard, JwtAuthGuard)  // RolesGuard 先执行，但 user 还未设置!

// 🟢 安全: 正确顺序
@UseGuards(JwtAuthGuard, RolesGuard)  // 先认证，再授权

// 🔴 Gateway 未使用 Guard
@WebSocketGateway()
export class ChatGateway {
  @SubscribeMessage('message')
  handleMessage(client: Socket, payload: any) {  // 无认证!
    return payload;
  }
}

// 🟢 安全
@WebSocketGateway()
@UseGuards(WsJwtGuard)
export class ChatGateway { ... }

// 搜索模式
@Public|@WebSocketGateway(?!.*@UseGuards)|@SubscribeMessage(?!.*Guard)
```

### 2. 输入验证缺失

```typescript
// 🔴 无 ValidationPipe
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);  // 未启用全局验证!
}

// 🔴 DTO 缺少验证
class CreateUserDto {
  name: string;  // 无 @IsString() 等装饰器
  email: string;
  isAdmin: boolean;  // Mass Assignment!
}

// 🔴 whitelist 未启用
app.useGlobalPipes(new ValidationPipe());  // 默认不过滤多余字段

// 🟢 安全: 完整配置
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,           // 过滤未定义字段
  forbidNonWhitelisted: true, // 有多余字段时报错
  transform: true,           // 自动转换类型
  transformOptions: {
    enableImplicitConversion: false  // 禁用隐式转换
  }
}));

// 🟢 安全: DTO 完整验证
import { IsString, IsEmail, Length, IsNotEmpty } from 'class-validator';

class CreateUserDto {
  @IsString()
  @IsNotEmpty()
  @Length(1, 50)
  name: string;

  @IsEmail()
  email: string;

  // 不包含 isAdmin - 防止 Mass Assignment
}

// 搜索模式
ValidationPipe\(\)|@Body\(\)(?!.*ValidationPipe)|class.*Dto(?!.*@Is)
```

### 3. SQL/NoSQL 注入

```typescript
// 🔴 TypeORM 原生查询
@Injectable()
export class UserService {
  async findByName(name: string) {
    return this.userRepository.query(
      `SELECT * FROM users WHERE name = '${name}'`  // SQL 注入!
    );
  }
}

// 🔴 MongoDB 注入
async findUser(query: any) {
  return this.userModel.find(query);  // NoSQL 注入: { "$gt": "" }
}

// 🟢 安全: 参数化查询
async findByName(name: string) {
  return this.userRepository.query(
    'SELECT * FROM users WHERE name = $1',
    [name]
  );
}

// 🟢 安全: 使用 QueryBuilder
async findByName(name: string) {
  return this.userRepository
    .createQueryBuilder('user')
    .where('user.name = :name', { name })
    .getOne();
}

// 🟢 安全: MongoDB 类型验证
async findUser(userId: string) {
  if (!Types.ObjectId.isValid(userId)) {
    throw new BadRequestException('Invalid ID');
  }
  return this.userModel.findById(userId);
}

// 搜索模式
\.query\s*\(.*\$\{|\.find\s*\(.*params|\.findOne\s*\(.*body
```

### 4. CORS 配置不当

```typescript
// 🔴 过宽的 CORS
app.enableCors();  // 默认允许所有源

app.enableCors({
  origin: true,  // 反射 Origin 头
  credentials: true
});

// 🔴 动态 origin 不验证
app.enableCors({
  origin: (origin, callback) => {
    callback(null, true);  // 允许所有!
  },
  credentials: true
});

// 🟢 安全: 明确白名单
app.enableCors({
  origin: ['https://app.example.com', 'https://admin.example.com'],
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  credentials: true,
  maxAge: 86400
});

// 搜索模式
enableCors\s*\(\s*\)|origin:\s*true|origin:.*callback.*true
```

### 5. 文件上传漏洞

```typescript
// 🔴 无类型限制
@Post('upload')
@UseInterceptors(FileInterceptor('file'))
uploadFile(@UploadedFile() file: Express.Multer.File) {
  // 任意类型都可上传!
  return this.saveFile(file);
}

// 🔴 路径遍历
@Post('upload')
uploadFile(@UploadedFile() file, @Body('path') path: string) {
  const fullPath = join('/uploads', path, file.originalname);
  // ../../../etc/cron.d/malicious
}

// 🟢 安全: 完整验证
@Post('upload')
@UseInterceptors(FileInterceptor('file', {
  limits: { fileSize: 5 * 1024 * 1024 },  // 5MB
  fileFilter: (req, file, cb) => {
    if (!file.mimetype.match(/^image\/(jpg|jpeg|png|gif)$/)) {
      return cb(new BadRequestException('Only images allowed'), false);
    }
    cb(null, true);
  },
  storage: diskStorage({
    destination: './uploads',
    filename: (req, file, cb) => {
      const uniqueName = `${uuid()}-${Date.now()}${extname(file.originalname)}`;
      cb(null, uniqueName);  // 使用安全文件名
    }
  })
}))
async uploadFile(@UploadedFile() file) {
  // 额外验证: 检查文件头
  const fileBuffer = await fs.readFile(file.path);
  const fileType = await fileTypeFromBuffer(fileBuffer);
  if (!fileType || !['image/jpeg', 'image/png'].includes(fileType.mime)) {
    await fs.unlink(file.path);
    throw new BadRequestException('Invalid file type');
  }
  return { filename: file.filename };
}

// 搜索模式
FileInterceptor(?!.*fileFilter)|@UploadedFile.*originalname
```

### 6. WebSocket 安全

```typescript
// 🔴 无认证的 Gateway
@WebSocketGateway()
export class EventsGateway {
  @SubscribeMessage('events')
  handleEvent(@MessageBody() data: string): string {
    return data;
  }
}

// 🔴 未验证房间订阅
@SubscribeMessage('joinRoom')
handleJoinRoom(client: Socket, room: string) {
  client.join(room);  // 任意房间!
}

// 🟢 安全: 完整认证
@WebSocketGateway({
  cors: { origin: ['https://app.example.com'] },
  namespace: '/events'
})
@UseGuards(WsJwtGuard)
export class EventsGateway implements OnGatewayConnection {

  async handleConnection(client: Socket) {
    try {
      const token = <REDACTED>;
      const user = await this.authService.verify(token);
      client.data.user = user;
    } catch {
      client.disconnect();
    }
  }

  @SubscribeMessage('joinRoom')
  async handleJoinRoom(client: Socket, roomId: string) {
    const user = client.data.user;
    const canJoin = await this.roomService.canUserJoin(user.id, roomId);
    if (!canJoin) {
      throw new WsException('Unauthorized');
    }
    client.join(`room:${roomId}`);
  }
}

// 搜索模式
@WebSocketGateway(?!.*@UseGuards)|handleConnection(?!.*verify)|client\.join\(.*params
```

### 7. JWT 安全问题

```typescript
// 🔴 弱密钥
JwtModule.register({
  secret: 'secret',  // 弱密钥!
  signOptions: { expiresIn: '60s' }
})

// 🔴 算法混淆
const payload = this.jwtService.verify(token);  // 可能接受 none 算法

// 🔴 无过期时间
const token = this.jwtService.sign(payload);  // 无 expiresIn

// 🟢 安全配置
JwtModule.registerAsync({
  useFactory: (config: ConfigService) => ({
    secret: config.get('JWT_SECRET'),  // 从环境变量
    signOptions: {
      expiresIn: '15m',
      algorithm: 'HS256'
    },
    verifyOptions: {
      algorithms: ['HS256'],  // 明确算法
      ignoreExpiration: false
    }
  }),
  inject: [ConfigService]
})

// 搜索模式
secret:\s*['"][^'"]{1,20}['"]|JwtModule\.register(?!Async)|sign\((?!.*expiresIn)
```

### 8. 敏感数据泄露

```typescript
// 🔴 返回完整实体
@Get(':id')
async getUser(@Param('id') id: string) {
  return this.userService.findOne(id);  // 包含 password hash!
}

// 🔴 错误信息泄露
@Get(':id')
async getUser(@Param('id') id: string) {
  try {
    return this.userService.findOne(id);
  } catch (error) {
    throw new InternalServerErrorException(error.stack);  // 泄露栈信息!
  }
}

// 🟢 安全: 使用 DTO/Serializer
@UseInterceptors(ClassSerializerInterceptor)
@Get(':id')
async getUser(@Param('id') id: string) {
  return this.userService.findOne(id);
}

// Entity
@Entity()
class User {
  @Column()
  name: string;

  @Exclude()  // 排除敏感字段
  @Column()
  password: string;
}

// 搜索模式
return.*findOne|throw.*error\.(message|stack)
```

---

## Fastify 特定漏洞

### 1. trustProxy 配置

```typescript
// 🔴 错误配置导致 IP 伪造
const app = Fastify({
  trustProxy: true  // 信任所有代理!
});

// 请求: X-Forwarded-For: 127.0.0.1
// request.ip 会是 127.0.0.1

// 🟢 安全: 指定信任的代理
const app = Fastify({
  trustProxy: ['127.0.0.1', '10.0.0.0/8']
});

// 搜索模式
trustProxy:\s*true(?!\s*,)
```

### 2. 路由安全

```typescript
// 🔴 路由顺序问题
fastify.get('/users/:id', getUser);
fastify.get('/users/me', getMe);  // 永远不会匹配!

// 🔴 通配符路由
fastify.get('/api/*', handler);  // 可能匹配过多

// 🟢 安全: 正确顺序
fastify.get('/users/me', getMe);
fastify.get('/users/:id', getUser);
```

### 3. 插件安全

```typescript
// 🔴 fastify-multipart 无限制
await fastify.register(multipart);

// 🟢 安全: 添加限制
await fastify.register(multipart, {
  limits: {
    fieldNameSize: 100,
    fieldSize: 1024 * 1024,  // 1MB
    fields: 10,
    fileSize: 5 * 1024 * 1024,  // 5MB
    files: 1,
    headerPairs: 50
  }
});

// 搜索模式
register\(multipart(?!.*limits)
```

### 4. 序列化安全

```typescript
// 🔴 无 schema 验证
fastify.post('/user', async (request) => {
  const user = request.body;  // 无验证!
  return db.createUser(user);
});

// 🟢 安全: 使用 JSON Schema
fastify.post('/user', {
  schema: {
    body: {
      type: 'object',
      required: ['name', 'email'],
      properties: {
        name: { type: 'string', maxLength: 50 },
        email: { type: 'string', format: 'email' }
      },
      additionalProperties: false  // 禁止额外字段
    }
  }
}, async (request) => {
  return db.createUser(request.body);
});

// 搜索模式
\.post\(.*async.*request(?!.*schema)
```

---

## 审计清单

```
认证授权:
- [ ] 检查全局 Guard 配置
- [ ] 验证 @Public() 使用位置
- [ ] 检查 Guard 执行顺序
- [ ] 验证 WebSocket Gateway 认证

输入验证:
- [ ] 确认全局 ValidationPipe
- [ ] 检查 whitelist/forbidNonWhitelisted
- [ ] 验证 DTO 装饰器完整性
- [ ] 检查 NoSQL 注入防护

CORS/安全:
- [ ] 验证 CORS origin 配置
- [ ] 检查 trustProxy 设置
- [ ] 验证安全头 (Helmet)

文件上传:
- [ ] 检查文件类型验证
- [ ] 验证文件大小限制
- [ ] 检查文件名处理
- [ ] 验证存储路径

JWT:
- [ ] 检查密钥强度
- [ ] 验证算法配置
- [ ] 检查过期时间

数据泄露:
- [ ] 检查实体序列化
- [ ] 验证错误处理
- [ ] 检查日志敏感信息
```

---

## 审计正则

```regex
# Guard 绕过
@Public|@WebSocketGateway(?!.*@UseGuards)

# 验证缺失
ValidationPipe\s*\(\s*\)|@Body\s*\(\s*\)(?!.*ValidationPipe)

# SQL/NoSQL 注入
\.query\s*\(.*\$\{|\.find\s*\(.*params

# CORS
enableCors\s*\(\s*\)|origin:\s*true

# 文件上传
FileInterceptor(?!.*fileFilter)

# JWT
secret:\s*['"][^'"]{1,20}['"]

# 敏感泄露
throw.*error\.(message|stack)|return.*findOne
```

---

**版本**: 1.0
**更新日期**: 2026-02-04
**覆盖漏洞类型**: 12+
