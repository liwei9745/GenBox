# GenBox v2.6.4 —— 发布包启动与生图数量修复

## 包含内容

- Windows 发布包首次启动设置和启动摘要现在提供中英双语提示，并统一使用
  UTF-8 输出。
- 生图数量以当前页面可见控件为准，不再被旧的模型缓存设置悄悄覆盖。
- 无效或超范围的生图数量会 fail safe，限制为 1 到 10 张。

## 安全与边界

- 本版本未修改生产 VPS、上游仓库或远程部署。
- 本版本不声称已完成浏览器生图或 clean deployment 验收。

## 验证

- 全量本地回归：`700 passed`。
- 启动/Provider/发布/设置 focused 套件：`57 passed`。
- JavaScript 语法、Python 编译及 `git diff --check` 均通过。
