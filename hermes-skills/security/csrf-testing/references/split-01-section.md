## 作业入口（先跑这个）

```bash
python3 tools/ops/cors_csrf_probe.py csrf --url https://授权/ --case <案>
python3 tools/ops/cors_csrf_probe.py csrf --url https://授权/ --post https://授权/api/profile --cookie 'sid=1' --case <案>
```

作业手法：`docs/playbooks/测绘引擎CSRF作业手法.md`。L2 必须打状态改变接口。

