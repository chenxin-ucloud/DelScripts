# UCloud Cleaner

批量清理 UCloud 项目资源的工具。

> **⚠️ 重要提示：macOS GUI（桌面 App）版本已停止迭代，推荐使用 Web 版本。**  
> Web 版无需打包、无需安装，浏览器打开即用，支持 macOS / Windows / Linux 跨平台。

---

## 一、Web 版（强烈推荐）

Web 版后端基于 Flask，前端纯 HTML/CSS/JS，所有计算在本地完成，数据不上传第三方服务器。

### 1. 环境准备

1. 确保电脑已安装 Python 3（macOS 自带，终端输入 `python3 --version` 有输出即可）
2. 打开终端，进入项目文件夹：
   ```bash
   cd /Users/user/Desktop/chenxin/DelScripts
   ```
3. 安装依赖（首次使用只需执行一次）：
   ```bash
   pip3 install ucloud-sdk-python3 flask
   ```

### 2. 启动 Web 服务

在终端执行：
```bash
python3 -m web.app
```

看到如下输出即启动成功：
```
UCloud Cleaner Web 已启动
本地访问: http://127.0.0.1:8080
按 Ctrl+C 退出
```

打开浏览器，访问 `http://127.0.0.1:8080` 即可使用。

> **停止服务**：回到终端，按 `Ctrl + C` 即可。

### 3. 使用步骤（小白教程）

#### 第 1 步：填写密钥
在左侧「任务配置」面板：
1. **环境**：选择「正式环境」或「测试环境」
2. **公钥**：填写你的 UCloud API 公钥（Public Key）
3. **私钥**：填写你的 UCloud API 私钥（Private Key）——**该字段不会被保存到任何地方**，刷新页面即消失
4. 点击「**获取项目**」按钮，系统会自动拉取该账号下的所有项目

#### 第 2 步：选择项目
在「项目」区域勾选要清理的项目（支持「全选」「取消选择」）。

#### 第 3 步：选择区域
在「区域」区域勾选要清理的地理区域（如北京、上海等），支持「全选」「取消选择」。

> 切换环境后区域列表会自动刷新。

#### 第 4 步：选择资源类型
在「资源类型」区域勾选要删除的资源，支持「全选」「取消选择」。

资源会按以下固定顺序删除（资源之间有依赖关系，顺序不可更改）：
```
UHost → UDisk → NATGW → UNI → ALB → NLB → EIP → UGN → UWAN → SecurityGroup → ACL → Subnet → VPC
```

#### 第 5 步：开始清理
点击「**开始清理**」按钮。右侧「运行日志」区域会实时显示删除进度：
- 绿色 = 正常 INFO
- 黄色 = 警告 WARNING
- 红色 = 错误 ERROR（失败会跳过，继续清理下一个）

右上角「队列」徽章显示当前排队任务数（含正在运行的）。

#### 第 6 步：停止或等待完成
- 任务运行中可点击「**停止**」按钮中断
- 任务结束后自动进入「历史」列表，可查看最终状态（成功 / 失败 / 已停止）

### 4. 安全说明

- **私钥仅存在于内存**：不写入浏览器 localStorage，不写入服务器磁盘，任务结束立即擦除
- **API 响应脱敏**：接口返回中不包含 `private_key`，`public_key` 仅显示前 4 位
- **默认仅本机访问**：服务监听 `127.0.0.1`，除非手动修改 `web/config.json` 中的 `host`

### 5. 常见问题

**Q：启动时报 `Port 8080 is in use`？**  
A：8080 端口被其他程序占用。编辑 `web/config.json`，将 `port` 改为 8081 等其他端口即可。

**Q：切换环境后项目列表没变化？**  
A：切换环境后需要重新点击「获取项目」按钮拉取对应环境的项目。

**Q：日志区没有输出？**  
A：先确认任务状态为「running」；若仍无日志，按 F12 打开浏览器开发者工具查看 Console 是否有红色报错。

---

## 二、macOS GUI 版（已停止迭代）

> **注意**：以下内容为旧版桌面 App 说明，不再新增功能，仅作存档。新项目请直接使用上方的 Web 版。

### 环境要求

- macOS 11.0+，Apple Silicon（M 系列）
- Python 3.x

### 开发模式运行

```bash
pip3 install ucloud-sdk-python3
cd gui
python3 main.py
```

### 打包为 .app

```bash
./build.sh
open dist/UCloudCleaner.app
```

### 使用方法

1. **配置** 标签页：填写 API 公钥、私钥、项目 ID（多个用逗号分隔），选择环境
2. **资源选择** 标签页：勾选要清理的区域和资源类型
3. **清理日志** 标签页：点击「开始清理」，实时查看进度；点击「停止」可中断

---

## 三、维护区域列表

编辑以下 JSON 文件可增加/删除区域：

- `gui/assets/region.json` — 正式环境区域
- `gui/assets/region_test.json` — 测试环境区域

格式：
```json
{
  "北京": { "Region": "cn-bj2", "Zone": "cn-bj2-02" }
}
```

修改后 Web 版即时生效；GUI 打包版需重新执行 `./build.sh`。

---

## 四、开发测试

```bash
pip3 install -r requirements-dev.txt
pytest -v
```

当前覆盖 50+ 单测，覆盖 SDK 核心、Task / TaskManager 队列与 worker、SSE 生成器、Flask 路由与校验。
