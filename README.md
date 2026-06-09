# UCloud Cleaner

批量清理 UCloud 项目资源的 macOS 桌面工具，支持按区域、资源类型和项目 ID 筛选删除。

## 功能

- 支持同时清理多个项目（逗号分隔项目 ID）
- 支持按区域和资源类型勾选过滤
- 正式环境 / 测试环境一键切换（自动加载对应区域列表）
- 实时日志输出，可随时停止
- 配置记忆：公钥、项目 ID、区域选择下次启动自动恢复（私钥出于安全考虑不持久化）

**支持的资源类型（按删除顺序）：**

UHost → UDisk → NATGW → UNI → ALB → NLB → EIP → UGN → UWAN → SecurityGroup → ACL → Subnet → VPC

## 环境要求

- macOS 11.0+，Apple Silicon（M 系列）
- Python 3.x（开发模式）
- 依赖：`ucloud-sdk-python3`、`pyinstaller`（打包）、`flask`（Web 版）

## 开发模式运行

```bash
pip3 install ucloud-sdk-python3
cd gui
python3 main.py
```

## 打包为 .app

```bash
./build.sh
open dist/UCloudCleaner.app
```

## 使用方法

1. **配置** 标签页：填写 API 公钥、私钥、项目 ID（多个用逗号分隔），选择环境
2. **资源选择** 标签页：勾选要清理的区域和资源类型
3. **清理日志** 标签页：点击「开始清理」，实时查看进度；点击「停止」可中断

## 维护区域列表

编辑 `gui/assets/region.json`（正式环境）或 `gui/assets/region_test.json`（测试环境），格式：

```json
{
  "北京": { "Region": "cn-bj2", "Zone": "cn-bj2-02" }
}
```

修改后无需重新打包（开发模式），打包版需执行 `./build.sh` 重新构建。

## Web 版（推荐：无需打包、跨平台）

适合不想 PyInstaller 打包、想跨平台或多人协作的场景。后端 Flask + 前端原生 HTML/CSS/JS。

### 启动

```bash
pip3 install -r web/requirements.txt
python3 -m web.app
# 默认监听 127.0.0.1:5000，浏览器打开 http://localhost:5000
```

### 特性

- 多浏览器 / 多 tab 可同时提交清理任务，后端**全局串行排队**逐个执行
- SSE 实时日志推送，刷新页面 / 换 tab 都能继续看到（最近 500 条会重放）
- 公钥 / 私钥仅在内存中存活；私钥不写浏览器 `localStorage`，也不写服务端磁盘；任务结束立刻擦除
- API 响应中所有凭证脱敏（`private_key` 不返回，`public_key` 仅前 4 位 + `***`）
- 默认仅监听 `127.0.0.1`，外部不可访问

### 内网部署提示

如需多人共用，请：

1. 修改 `web/config.json`（参考 `web/config.json.example`），将 `host` 改为 `0.0.0.0`
2. 自行接 Nginx + HTTPS（私钥经 HTTP 明文传不安全）
3. 单进程 Flask dev server 不适合生产；可用 `gunicorn -w 1 'web.app:create_app()[0]'`（**必须 `-w 1`** 才能维持单 worker 串行语义）

### 运行测试

```bash
pip3 install -r requirements-dev.txt
pytest -v
```

当前覆盖 50+ 单测，覆盖 `sdk/runner_core`、Task / TaskManager 队列与 worker、SSE 生成器、Flask 路由与校验。
