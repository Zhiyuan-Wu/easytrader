# EasyTrader 项目分析报告

> 版本: 0.23.7 | 作者: shidenggui | 协议: BSD
> 生成日期: 2026-05-30

---

## 一、技术原理

### 1.1 项目定位

EasyTrader 是一个 **中国 A 股自动化交易框架**，提供统一的 Python API，支持多种券商客户端和交易模式。

### 1.2 核心架构

项目采用 **抽象工厂 + 策略模式**，通过 `api.py` 中的 `use()` 和 `follower()` 工厂函数创建不同类型的交易实例：

```
                    ┌──────────────────┐
                    │    api.use()     │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼──────────────────┐
           ▼                 ▼                  ▼
   ClientTrader        WebTrader          MiniqmtTrader
   (GUI 自动化)       (HTTP API)         (SDK API)
       │                 │                    │
  ┌────┼────┐      XueQiuTrader         xtquant SDK
  ▼    ▼    ▼     (雪球虚拟组合)
 YH   HT   GJ ...
 银河 华泰  国金

                    ┌──────────────────┐
                    │  api.follower()  │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼──────────────────┐
           ▼                 ▼                  ▼
    JoinQuant          RiceQuant          XueQiuFollower
    (聚宽跟单)         (米筐跟单)          (雪球跟单)
```

### 1.3 三种交易范式

| 范式 | 实现方式 | 平台要求 | 原理 |
|------|---------|---------|------|
| **GUI 自动化** | `pywinauto` 操作 Windows 控件 | 仅 Windows | 模拟用户在券商客户端上的点击、输入、读取操作 |
| **Web API 交易** | `requests` HTTP 请求 | 跨平台 | 调用雪球 Web API 进行虚拟组合调仓 |
| **SDK API 交易** | `xtquant` QMT 接口 | 仅 Windows | 调用券商官方量化接口直接下单 |

#### GUI 自动化原理

```
用户调用 buy("600000", 10.0, 100)
        │
        ▼
  切换到"买入"菜单 (F1)
        │
        ▼
  填写股票代码/价格/数量 (写入 Edit 控件)
        │
        ▼
  点击"买入"按钮
        │
        ▼
  TradePopDialogHandler 自动确认弹窗
        │
        ▼
  从成功提示中提取委托编号
```

GUI 自动化的关键组件：
- **Grid 策略** (`grid_strategies.py`): 从表格控件提取持仓/委托/成交数据，支持剪贴板复制(Copy)、消息复制(WMCopy)、XLS 导出三种方式
- **弹窗处理器** (`pop_dialog_handler.py`): 自动处理券商客户端的确认、错误、成功弹窗
- **刷新策略** (`refresh_strategies.py`): 刷新页面数据，支持 F5 快捷键和工具栏按钮两种方式

#### 跟单系统原理

```
量化平台策略 ───产生信号───> JoinQuant/RiceQuant/XueQiu
                                    │
                        Follower 定时轮询 (1~10秒)
                                    │
                              ┌─────▼─────┐
                              │ 去重/过期检查 │
                              └─────┬─────┘
                                    │
                              放入 trade_queue
                                    │
                              trade_worker 线程
                                    │
                              对每个 user 执行 buy/sell
```

### 1.4 远程交易架构

```
  远程机器                     交易机器 (Windows)
┌──────────┐     HTTP      ┌──────────────────┐
│RemoteClient├─────────────►│  Flask Server    │
│           │  :1430        │  (server.py)     │
└──────────┘               │        │         │
                           │  ClientTrader     │
                           │  (操作券商客户端)   │
                           └──────────────────┘
```

### 1.5 依赖关系

**核心依赖**: `pywinauto`(GUI自动化), `requests`(HTTP), `flask`(远程服务), `pandas`(数据处理), `pillow`(验证码图像), `pytesseract`(OCR)

**可选依赖**: `xtquant`(MiniQMT 量化接口), `rqopen_client`(米筐 SDK)

---

## 二、主要功能

### 2.1 交易功能

| 功能 | GUI 客户端 | 雪球 | MiniQMT | 远程 |
|------|:---------:|:----:|:-------:|:----:|
| 买入 | ✅ | ✅ | ✅ | ✅ |
| 卖出 | ✅ | ✅ | ✅ | ✅ |
| 市价买入 | ✅ | - | ✅ | ✅ |
| 市价卖出 | ✅ | - | ✅ | ✅ |
| 撤单 | ✅ | ✅ | ✅ | ✅ |
| 全部撤单 | ✅ | - | ✅ | ✅ |
| 查询余额 | ✅ | ✅ | ✅ | ✅ |
| 查询持仓 | ✅ | ✅ | ✅ | ✅ |
| 今日委托 | ✅ | - | ✅ | ✅ |
| 今日成交 | ✅ | - | ✅ | ✅ |
| 国债逆回购 | ✅ | - | - | - |
| 自动打新 | ✅ | - | - | ✅ |
| 调仓(权重) | - | ✅ | - | - |

### 2.2 支持的券商

| 券商 | 代码 | 备注 |
|------|------|------|
| 银河证券 | `yh_client` | 支持验证码识别 |
| 华泰证券 | `ht_client` | 需要通讯密码 |
| 海通证券 | `htzq_client` | 需要通讯密码 |
| 国金证券 | `gj_client` | 字母数字验证码 |
| 广发证券 | `gf_client` | 支持验证码识别 |
| 五矿证券 | `wk_client` | 继承华泰 |
| 通用同花顺 | `universal_client` / `ths` | 通用客户端 |
| QMT 量化 | `miniqmt` | SDK 直连 |
| 雪球虚拟组合 | `xq` | 虚拟交易 |

### 2.3 跟单平台

| 平台 | 代码 | 轮询间隔 | 认证方式 |
|------|------|---------|---------|
| 聚宽 (JoinQuant) | `jq` / `joinquant` | ~1s | 用户名+密码 |
| 米筐 (RiceQuant) | `rq` / `ricequant` | ~1s | RQOpenClient SDK |
| 雪球 (XueQiu) | `xq` / `xueqiu` | ~10s | 用户名+密码 |

---

## 三、安全审查

### 3.1 对外通信清单

#### 与外部平台的通信

| 目标 | 协议 | 数据内容 | 文件位置 |
|------|------|---------|---------|
| `xueqiu.com` | HTTPS (SSL 验证已禁用) | 股票查询/组合调仓/登录(Cookie) | `xqtrader.py`, `xq_follower.py`, `utils/stock.py` |
| `joinquant.com` | HTTPS (SSL 验证已禁用) | 登录(用户名+密码)/策略交易数据 | `joinquant_follower.py` |
| RiceQuant | HTTPS (SSL 验证已禁用) | 登录/策略交易数据 | `ricequant_follower.py` |
| `yh.ez.shidenggui.com:5000` | **HTTP 明文** | 验证码图片(银河客户端截图) | `utils/captcha.py` |

#### 本地/内部通信

| 目标 | 协议 | 数据内容 | 文件位置 |
|------|------|---------|---------|
| `0.0.0.0:1430` (Flask 服务) | HTTP 明文 | 完整交易指令(买卖/撤单/账户密码) | `server.py`, `remoteclient.py` |
| 券商客户端 GUI | Windows 消息 | 交易操作(模拟键盘/鼠标) | `clienttrader.py` 及子类 |
| QMT 本地进程 | SDK IPC | 交易指令 | `miniqmt/miniqmt_trader.py` |

### 3.2 安全风险分析

#### 高危风险

**1. SSL 验证全局禁用**

```python
# easytrader/__init__.py
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# easytrader/xqtrader.py
self.s.verify = False

# easytrader/follower.py
self.s.verify = False
```

所有 HTTPS 请求均不验证服务器证书，存在 **中间人攻击** 风险。攻击者可在网络层截获交易请求、Cookie、甚至注入伪造的交易响应。

**2. Flask 远程服务无任何认证**

```python
# easytrader/server.py
app.run(host="0.0.0.0", port=1430)
# 无 API Key、无 Token、无 IP 白名单
```

服务绑定 `0.0.0.0:1430`，局域网内任何人可调用 `/buy`、`/sell` 接口执行真实交易。`RemoteClient` 虽支持 HTTP Basic Auth，但服务端并未校验。

**3. 明文传输账户密码**

- 远程模式: 密码通过 HTTP 明文传输 (`remoteclient.py` → `server.py`)
- 验证码识别: 客户端截图发送至 `http://yh.ez.shidenggui.com:5000`，暴露券商界面信息
- 跟单登录: JoinQuant/雪球的用户名密码通过 POST 表单发送(虽为 HTTPS，但 SSL 验证已禁用)

**4. 凭证明文存储**

```json
// yh_client.json (项目根目录)
{"user": "银河用户名", "password": "银河明文密码"}

// xq.json
{"cookies": "雪球Cookie字符串", "portfolio_code": "组合代码"}
```

账户密码以明文 JSON 存储在项目根目录，无加密、无 `.gitignore` 排除。

#### 中危风险

**5. Pickle 反序列化任意代码执行**

```python
# easytrader/follower.py
CMD_CACHE_FILE = "cmd_cache.pk"
pickle.load(open(self.CMD_CACHE_FILE, "rb"))  # 不安全的反序列化
```

`cmd_cache.pk` 文件被 pickle 反序列化加载，若该文件被篡改，可执行任意 Python 代码。

**6. `tempfile.mktemp()` 竞态条件**

`grid_strategies.py`、`yh_clienttrader.py` 等多处使用 `tempfile.mktemp()`（已弃用），应改用 `tempfile.mkstemp()` 避免竞态条件。

### 3.4 安全建议

1. **启用 SSL 证书验证**: 移除 `verify=False`，使用系统 CA 证书或配置自定义证书
2. **为 Flask 服务增加认证**: 实现 API Key、JWT Token 或至少 HTTP Basic Auth 服务端校验
3. **加密存储凭证**: 使用 keyring 或加密配置文件存储密码，将 JSON 配置文件加入 `.gitignore`
4. **添加交易限额**: 实现单笔最大金额、单日最大交易次数、最大持仓比例等可配置限制
5. **增加价格偏离检查**: 下单前校验委托价与当前市价的偏离幅度，超过阈值(如 ±5%)时拒绝或报警
6. **引入人工确认选项**: 为关键操作提供可选的人工确认步骤，而非总是自动确认弹窗
7. **替换 Pickle**: 使用 JSON 或其他安全的序列化格式存储命令缓存
8. **持久化审计日志**: 将交易记录写入独立的日志文件或数据库，便于事后审计
9. **验证码服务改用 HTTPS**: 避免通过明文 HTTP 传输券商客户端截图
10. **修复 tempfile 用法**: 将 `tempfile.mktemp()` 替换为 `tempfile.mkstemp()`

### 3.5 补充发现

#### 广发证券验证码识别逻辑失效 (Bug)

`gf_clienttrader.py:81` 调用 `recognize_verify_code(file_path, "gf_client")`，但 `captcha.py:34` 的分发逻辑检查的是 `broker == "gf"`。由于 `"gf_client" != "gf"`，广发证券实际走的是 `default_verify_code_detect()`（简单本地 OCR），而非为其专门优化的 `detect_gf_result()`（带像素级噪声过滤的预处理）。这导致广发验证码识别率低于预期。

#### 外部通信完整清单

| 域名 | 协议 | SSL 验证 | 涉及模块 | 传输内容 |
|------|------|----------|---------|---------|
| `xueqiu.com` | HTTPS | **已禁用** | `xqtrader.py`, `xq_follower.py` | 股票查询/组合调仓/Cookie |
| `xueqiu.com` | HTTPS | 默认启用 | `utils/stock.py` | IPO 新股查询（独立 session） |
| `joinquant.com` | HTTPS | **已禁用** | `joinquant_follower.py` | 登录(用户名+密码)/交易数据 |
| RiceQuant 服务器 | HTTPS | SDK 内部 | `ricequant_follower.py` | 登录/交易数据 |
| `yh.ez.shidenggui.com:5000` | HTTP 明文 | 无 TLS | `utils/captcha.py` | 仅验证码截图图片 |
| `0.0.0.0:1430` (本地) | HTTP 明文 | 无 TLS | `server.py` | 完整交易指令 |

**不存在 WebSocket、邮件、短信、Socket 直连等其他通信方式。**

#### 验证码发送确认：仅发送图片

外部验证码服务 `detect_yh_client_result()` 发送的请求中，`requests.post()` 仅包含 `files={"image": f}` 参数。**不附带** Cookie、账户名、密码、Session Token、券商标识或任何自定义 Header。触发该服务的场景仅有银河 (`yh_clienttrader.py`) 和国金 (`gj_clienttrader.py`) 的登录流程。

---

## 四、安全修复计划

> 基于风险评估和实施成本综合考量，按优先级排列

### 4.1 P0：Flask 远程服务增加 API Key 认证

**风险**：`server.py` 绑定 `0.0.0.0:1430`，无任何鉴权，局域网内任何人可执行交易。

**修复方案**：

```
改动文件: server.py, remoteclient.py
```

**server.py 端**：
- 增加配置项 `api_key`（从环境变量 `EASYTRADER_API_KEY` 或启动参数读取）
- 新增 `before_request` 钩子，校验请求 Header `X-API-Key` 或查询参数 `api_key`
- 未配置 api_key 时保持向后兼容（打印警告日志）
- `/prepare` 接口的 `prepare` 参数中可传入 api_key 供初始化校验

**remoteclient.py 端**：
- 构造函数新增 `api_key` 参数
- 所有请求自动附加 `X-API-Key` Header

**兼容性**：未配置 api_key 时服务仍可启动（打印 WARNING），保持向后兼容。

### 4.2 P1：验证码识别改用本地 OCR，移除外部通信

**风险**：验证码图片通过明文 HTTP 发送至第三方服务器 `yh.ez.shidenggui.com:5000`。

**修复方案**：

```
改动文件: easytrader/utils/captcha.py, yh_clienttrader.py, gj_clienttrader.py
```

- 移除 `detect_yh_client_result()` 函数及其对外部 API 的调用
- 修改 `recognize_verify_code()` 的分发逻辑：银河和国金也使用本地 OCR
- 为银河/国金验证码增加类似 `detect_gf_result()` 的图像预处理（灰度化、二值化、噪声过滤），提升本地识别率
- **附带修复** `gf_clienttrader.py:81` 的 broker 字符串 Bug：`"gf_client"` → `"gf"`，使广发证券能正确使用 `detect_gf_result()`
- 移除 `captcha.py` 中已废弃的 `input_verify_code_manual()` 函数

**影响**：银河/国金验证码本地识别率可能低于外部服务，需实测后调优预处理参数。

### 4.3 P1：凭证加密存储

**风险**：账户密码以明文 JSON 存储在项目根目录，无加密、无 `.gitignore` 排除。

**修复方案**：

```
改动文件: 新增 easytrader/utils/crypto.py, 改动 clienttrader.py 及各 *_clienttrader.py 的配置读取逻辑
```

- 使用 `cryptography` 库的 Fernet 对称加密（AES-128-CBC + HMAC）
- JSON 配置文件中的 `password` 和 `comm_password` 字段存储为加密密文（前缀 `enc:` 标识）
- 新增 CLI 命令 `easytrader encrypt <config_file>`：交互式输入主密码，加密配置文件中的敏感字段
- 配置读取时：检测到 `enc:` 前缀则提示输入主密码解密，否则按明文处理（向后兼容）
- 主密码可通过环境变量 `EASYTRADER_MASTER_PASSWORD` 预设，避免每次手动输入
- 将 `*_client.json`、`xq.json` 等配置文件加入 `.gitignore`

**兼容性**：已有的明文配置文件无需修改，仍可直接使用。

### 4.4 P2：修复 Pickle 反序列化

**风险**：`follower.py` 使用 `pickle.load()` 加载 `cmd_cache.pk`，文件被篡改可执行任意代码。

**修复方案**：

```
改动文件: easytrader/follower.py
```

- 将 `cmd_cache.pk` 替换为 `cmd_cache.json`
- 序列化改用 `json.dump()` / `json.load()`
- 对已有 `.pk` 文件做一次性迁移：检测到 `.pk` 存在时读取并转存为 `.json`

### 4.5 P2：修复 tempfile.mktemp() 竞态条件

**风险**：多处使用已弃用的 `tempfile.mktemp()`，存在 TOCTOU 竞态。

**修复方案**：

```
改动文件: grid_strategies.py, yh_clienttrader.py, gj_clienttrader.py, gf_clienttrader.py
```

- `tempfile.mktemp() + ".jpg"` → `tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)`
- 使用完毕后显式关闭并删除临时文件
- 统一封装为 `utils/misc.py` 中的 `safe_temp_file(suffix)` 辅助函数

### 4.6 P3（暂不修复）：SSL 验证全局禁用

**风险**：所有 HTTPS 请求禁用证书验证，存在中间人攻击可能。

**处理方式**：标记为已知风险，在文档中明确标注。当前项目主要在受控内网或本地 Windows 机器上运行，实际中间人攻击场景有限。后续版本可考虑引入可配置的证书路径（`EASYTRADER_SSL_CERT` 环境变量），允许用户按需启用验证。

### 4.7 修复优先级总览

| 优先级 | 问题 | 方案 | 改动范围 |
|--------|------|------|---------|
| **P0** | Flask 无认证 | API Key 校验 | server.py, remoteclient.py |
| **P1** | 验证码明文 HTTP | 改用本地 OCR + 修复 gf bug | captcha.py, yh/gj/gf_clienttrader.py |
| **P1** | 凭证明文存储 | Fernet 加密 + .gitignore | 新增 crypto.py, 改动配置读取逻辑 |
| **P2** | Pickle 反序列化 | 替换为 JSON | follower.py |
| **P2** | tempfile 竞态 | 改用 NamedTemporaryFile | grid_strategies.py, 各 *_clienttrader.py |
| **P3** | SSL 禁用 | 暂不修复，标记已知风险 | 无代码改动 |

```
easytrader/
├── easytrader/                    # 主包
│   ├── __init__.py               # 包入口，禁用 SSL 警告
│   ├── api.py                    # 工厂函数 use() / follower()
│   ├── clienttrader.py           # GUI 客户端交易基类
│   ├── webtrader.py              # Web 交易基类
│   ├── xqtrader.py               # 雪球虚拟组合交易
│   ├── follower.py               # 跟单基类
│   ├── xq_follower.py            # 雪球跟单
│   ├── joinquant_follower.py     # 聚宽跟单
│   ├── ricequant_follower.py     # 米筐跟单
│   ├── server.py                 # Flask 远程交易服务
│   ├── remoteclient.py           # 远程交易客户端
│   ├── *_clienttrader.py         # 各券商 GUI 交易实现
│   ├── grid_strategies.py        # 表格数据提取策略
│   ├── refresh_strategies.py     # 刷新策略
│   ├── pop_dialog_handler.py     # 弹窗处理器
│   ├── exceptions.py             # 自定义异常
│   ├── log.py                    # 日志配置
│   ├── config/                   # 配置文件
│   │   ├── client.py            # 券商 GUI 控件 ID 配置
│   │   ├── global.json          # 全局响应格式
│   │   └── xq.json              # 雪球 API 端点
│   ├── utils/                    # 工具函数
│   │   ├── misc.py              # Cookie 解析/文件读取
│   │   ├── stock.py             # 股票代码/打新工具
│   │   ├── captcha.py           # 验证码 OCR 识别
│   │   ├── perf.py              # 性能计时装饰器
│   │   └── win_gui.py           # Windows GUI 辅助
│   └── miniqmt/                  # MiniQMT 量化接口
│       ├── __init__.py
│       └── miniqmt_trader.py    # QMT 交易实现
├── tests/                        # 测试
├── docs/                         # 文档
└── setup.py                      # 包配置
```
