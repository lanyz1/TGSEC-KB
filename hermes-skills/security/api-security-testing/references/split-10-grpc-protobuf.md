## 九、gRPC/Protobuf测试

```bash
# 反射发现
grpcurl -plaintext target:443 list
grpcurl -plaintext target:443 list package.Service
grpcurl -plaintext target:443 describe package.Service.Method

# 调用
grpcurl -plaintext -d '{"field":"value"}' target:443 package.Service/Method

# Protobuf逆向
# 从APK/二进制提取.proto
protoc --decode_raw < message.bin
# pbtk / protobuf-inspector 猜测字段
# gRPC-metadata认证： -H "authorization: Bearer xxx"
# TLS场景：grpcurl -insecure
# 注意gRPC网关（gRPC-web/grpc-gateway REST代理）→ 两种入口鉴权可能不一致
```

