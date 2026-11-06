# 后台模块扩展模式(占位 → 真功能)

来源: 2026-08 区域管理模块实战(15483 条地区数据浏览/筛选/搜索/编辑/删除)。
后台 = 马总COD/长安COD重建版(PHP8 + SQLite + 原生模板,Ozon 风格 admin_layout)。

## 四件套清单

### 1. admin_layout.php(菜单 + 面包屑)

```php
// 菜单项: url 从 '#' 改为真实地址, 去掉 data-placeholder="1"
['id' => 'region', 'label' => '区域管理', 'url' => '/index.php?s=admin&c=region&m=index',
 'icon' => 'M12 2C8.13 2 5 5.13 5 8c0 5.25 7 13 7 13s7-7.75 7-13c0-2.87-3.13-6-7-6zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z'],
// crumbMap 加一行
'region' => '区域管理',
```

data-placeholder="1" 的菜单项会被 JS 拦截弹"功能开发中" toast——去掉该属性即恢复跳转。

### 2. admin.php(控制器)

```php
function region_index() {
    admin_require();
    $pdo = db();
    // 分组统计(筛选 tab 用)
    $groups = [];
    foreach ($pdo->query("SELECT group_code, COUNT(*) c FROM dr_linkage GROUP BY group_code ORDER BY c DESC")->fetchAll(PDO::FETCH_ASSOC) as $r)
        $groups[$r['group_code']] = (int)$r['c'];
    // 动态 WHERE + 参数
    $sql = "SELECT id, group_code, region_id, region_code, region_name, region_zipcod, parent_id FROM dr_linkage WHERE 1=1";
    $args = [];
    if ($code !== '' && isset($groups[$code])) { $sql .= " AND group_code=?"; $args[] = $code; }
    if ($kw !== '') { $sql .= " AND (region_name LIKE ? OR region_code LIKE ? OR region_zipcod LIKE ?)"; $args[] = "%$kw%"; $args[] = "%$kw%"; $args[] = "%$kw%"; }
    // COUNT(*) 双查询 + LIMIT/OFFSET(分页)
    $sql .= " ORDER BY group_code, parent_id, region_id LIMIT $perPage OFFSET $offset";
    // 父级名称: 同表 IN 预加载 map
    $pids = array_values(array_unique(array_filter(array_column($rows, 'parent_id'))));  // ← array_values 必须!
    $st = $pdo->prepare("SELECT region_id, region_name FROM dr_linkage WHERE region_id IN ($in)");
    $st->execute($pids);
    foreach ($st->fetchAll(PDO::FETCH_ASSOC) as $r) $parentNames[$r['region_id']] = $r['region_name'];
    view('admin_region', ['rows'=>$rows, 'groups'=>$groups, 'total'=>$total, 'code'=>$code, 'kw'=>$kw, 'page'=>$page, 'perPage'=>$perPage, 'parentNames'=>$parentNames]);
}
```

### 3. admin_<mod>.php(模板)

```php
require __DIR__ . '/admin_layout.php';
admin_head('区域管理', 'region');   // 第二参 = active 菜单 id
?>
<div class="stats" style="grid-template-columns:repeat(5,1fr)">
  <div class="stat c-blue"><div class="stat-icon">svg</div>
    <div class="stat-meta"><div class="stat-num">15,483</div><div class="stat-label">地区总数</div></div></div>
  <!-- c-blue/c-red/c-purple/c-green/c-cyan 五种配色 -->
</div>
<div class="card">筛选 tabs / 搜索表单(btn-primary / btn-ghost btn-sm)</div>
<div class="table-wrap"><table class="tbl">...</table></div>
<div>分页: 上一页 / x / y / 下一页</div>
<?php admin_foot(); ?>
```

编辑/删除 JS:

```js
function editRegion(id, rid, name){
    var nn = prompt('编辑地区名称 (ID: ' + rid + ')', name);
    if (nn === null || nn.trim() === '' || nn.trim() === name) return;
    var fd = new URLSearchParams(); fd.append('id', id); fd.append('name', nn.trim());
    fetch('/index.php?s=admin&c=region&m=edit', {method:'POST', body:fd})
        .then(r => r.json()).then(j => { alert(j.code === 1 ? '✓ 已更新' : (j.msg || '失败')); if (j.code === 1) location.reload(); });
}
```

### 4. 同步 + 验证

- 上传 admin.php + admin_layout.php + admin_<mod>.php 三个文件
- curl 登录(cookie jar)→ 访问 `?s=admin&c=region&m=index` 验证 200 + 关键元素 grep
- 分页/搜索/筛选各测一次; 500 时看 /var/log/php_errors.log

## 本模块踩的坑

1. **array_unique 非连续键 → PDO bind 失败**(详见 SKILL.md 第 8 节)——`$pids = array_values(array_unique(...))`
2. 验证脚本 grep 用 `grep -c '关键词'` 返回 0 时注意: 是"0 命中"还是"grep 没找到文件"(文件不存在会走 ERR 分支)——先确认 curl 落盘成功(HTTP code + size)
3. 分页/筛选 URL 的 `&` 在 shell 测试里必须整体引号包裹
