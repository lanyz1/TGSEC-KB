## 云控平台(系统选择双应用)
- 架构: `/tgcloud_pc`(用户后台)+ `/customer`(客服系统);PHP 后端(index.php/.php 全 403);9000 端口 Swoole WS(HTTP 直连 400)
- `/api/common/config_init` 未授权 200 → 泄露 platform_name/websocket_url/cdn_url/auths/价格
- FOFA `domain="<目标>"` → 同平台多节点(不同 IP 同「系统选择」页同 OSS bucket)

