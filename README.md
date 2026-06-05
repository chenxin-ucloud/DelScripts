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
- 依赖：`ucloud-python-sdk`、`pyinstaller`（打包）

## 开发模式运行

```bash
pip3 install ucloud-python-sdk
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
