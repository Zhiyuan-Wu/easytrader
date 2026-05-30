# EasyTrader HTTP 远程交易服务使用指南

## 架构概览

```
远程机器                     交易机器 (Windows)
┌──────────┐     HTTP      ┌──────────────────┐
│RemoteClient├─────────────►│  Flask Server    │
│(Python客户端)│  :1430     │  (server.py)     │
└──────────┘               │        │         │
                           │  ClientTrader     │
                           │  (操作券商客户端)   │
                           └──────────────────┘
```

Flask 服务运行在交易机器上，通过 `pywinauto` 操作本地券商客户端执行交易。远程机器通过 HTTP API 下发指令。

---

## 一、启动服务

### 1.1 服务器端（交易机器）

```python
from easytrader import server

# 方式一：无认证（不推荐生产环境）
server.run(port=1430)

# 方式二：通过参数指定 API Key
server.run(port=1430, api_key="your-secret-key")

# 方式三：通过环境变量指定 API Key
# export EASYTRADER_API_KEY="your-secret-key"
server.run(port=1430)
```

服务启动后监听 `0.0.0.0:1430`。

### 1.2 客户端（远程机器）

```python
import easytrader

# 无认证
user = easytrader.remote_client.use("yh_client", host="192.168.1.100", port=1430)

# API Key 认证
user = easytrader.remote_client.use(
    "yh_client",
    host="192.168.1.100",
    port=1430,
    api_key="your-secret-key",
)

# 使用 HTTPS（需反向代理）
user = easytrader.remote_client.use(
    "yh_client",
    host="192.168.1.100",
    port=443,
    ssl=True,
    api_key="your-secret-key",
)
```

---

## 二、认证方式

### 2.1 API Key（推荐）

服务端配置 `EASYTRADER_API_KEY` 环境变量或 `run()` 的 `api_key` 参数后，所有请求必须携带 API Key。

**传递方式（二选一）：**

- HTTP Header：`X-API-Key: your-secret-key`
- 查询参数：`?api_key=your-secret-key`

**认证失败响应：**

```json
HTTP/1.1 401 Unauthorized
{"error": "Unauthorized: invalid or missing API key"}
```

### 2.2 未配置 API Key

若未设置 API Key，服务以无认证模式运行，启动时会打印警告日志。任何可访问该端口的客户端均能执行交易操作。

---

## 三、接口详情

### 基础 URL

```
http://{host}:{port}
```

### 通用响应格式

**成功：** 各接口返回 JSON，状态码为 200 或 201。

**失败：**

```json
HTTP/1.1 400 Bad Request
{"error": "ExceptionClass: error message"}
```

---

### 3.1 `POST /prepare` — 初始化并登录券商客户端

调用此接口后会在服务端创建券商交易实例并完成登录。**必须最先调用**，后续所有接口依赖此步骤。

#### 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `broker` | string | 是 | 券商标识，见下方券商列表 |
| `config_path` | string | 否* | 登录配置文件路径，与 user/password 二选一 |
| `user` | string | 否* | 账号（与 config_path 二选一） |
| `password` | string | 否* | 明文密码（与 config_path 二选一） |
| `exe_path` | string | 否 | 客户端可执行文件路径，如 `C:\\银河证券\\xiadan.exe` |
| `comm_password` | string | 否 | 通讯密码（华泰、海通等需要） |

> `config_path` 指向一个 JSON 文件，格式为 `{"user": "账号", "password": "密码", "exe_path": "路径", "comm_password": "通讯密码"}`。
> 若配置文件中包含 `enc:` 前缀的加密字段，需设置 `EASYTRADER_MASTER_PASSWORD` 环境变量。

#### 支持的 broker 值

| broker 值 | 券商 |
|-----------|------|
| `yh_client` | 银河证券 |
| `ht_client` | 华泰证券 |
| `htzq_client` | 海通证券 |
| `gj_client` | 国金证券 |
| `gf_client` | 广发证券 |
| `wk_client` | 五矿证券 |
| `universal_client` | 通用同花顺客户端 |
| `ths` | 同花顺客户端 |
| `miniqmt` | QMT 量化接口 |
| `xq` | 雪球虚拟组合 |

#### 示例

**方式一：通过配置文件登录**

```bash
curl -X POST http://192.168.1.100:1430/prepare \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"broker": "yh_client", "config_path": "C:\\trader\\yh_client.json"}'
```

**方式二：通过参数直接登录**

```bash
curl -X POST http://192.168.1.100:1430/prepare \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"broker": "yh_client", "user": "账号", "password": "密码", "exe_path": "C:\\银河证券\\xiadan.exe"}'
```

#### 响应

```json
HTTP/1.1 201 Created
{"msg": "login success"}
```

---

### 3.2 `GET /balance` — 查询账户资金

#### 请求

无额外参数。

```bash
curl http://192.168.1.100:1430/balance \
  -H "X-API-Key: your-secret-key"
```

#### 响应

```json
HTTP/1.1 200 OK
{
  "总资产": 100000.00,
  "可用金额": 50000.00,
  "股票市值": 48000.00,
  "冻结金额": 2000.00
}
```

> 字段名因券商不同可能略有差异。

---

### 3.3 `GET /position` — 查询持仓

#### 请求

无额外参数。

```bash
curl http://192.168.1.100:1430/position \
  -H "X-API-Key: your-secret-key"
```

#### 响应

```json
HTTP/1.1 200 OK
[
  {
    "证券代码": "600000",
    "证券名称": "浦发银行",
    "股票余额": 1000,
    "可用余额": 1000,
    "成本价": 10.50,
    "市价": 11.20,
    "浮动盈亏": 700.00
  }
]
```

---

### 3.4 `POST /buy` — 限价买入

#### 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `security` | string | 是 | 证券代码，6 位数字，如 `"600000"` |
| `price` | float | 是 | 委托价格，如 `10.50` |
| `amount` | int | 是 | 委托数量（股），必须为 100 的整数倍 |

```bash
curl -X POST http://192.168.1.100:1430/buy \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"security": "600000", "price": 10.50, "amount": 100}'
```

#### 响应

```json
HTTP/1.1 201 Created
{"entrust_no": "12345"}
```

---

### 3.5 `POST /sell` — 限价卖出

#### 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `security` | string | 是 | 证券代码，6 位数字 |
| `price` | float | 是 | 委托价格 |
| `amount` | int | 是 | 委托数量（股），必须为 100 的整数倍 |

```bash
curl -X POST http://192.168.1.100:1430/sell \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"security": "600000", "price": 11.00, "amount": 100}'
```

#### 响应

```json
HTTP/1.1 201 Created
{"entrust_no": "12346"}
```

---

### 3.6 `POST /market_buy` — 市价买入

> 仅 GUI 客户端和 MiniQMT 支持，需客户端已登录。

#### 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `security` | string | 是 | 证券代码 |
| `amount` | int | 是 | 委托数量 |

```bash
curl -X POST http://192.168.1.100:1430/market_buy \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"security": "600000", "amount": 100}'
```

#### 响应

```json
HTTP/1.1 201 Created
{"entrust_no": "12347"}
```

---

### 3.7 `POST /market_sell` — 市价卖出

> 仅 GUI 客户端和 MiniQMT 支持。

#### 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `security` | string | 是 | 证券代码 |
| `amount` | int | 是 | 委托数量 |

```bash
curl -X POST http://192.168.1.100:1430/market_sell \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"security": "600000", "amount": 100}'
```

---

### 3.8 `GET /today_entrusts` — 查询当日委托

#### 请求

无额外参数。

```bash
curl http://192.168.1.100:1430/today_entrusts \
  -H "X-API-Key: your-secret-key"
```

#### 响应

```json
HTTP/1.1 200 OK
[
  {
    "委托编号": "12345",
    "证券代码": "600000",
    "证券名称": "浦发银行",
    "操作": "买入",
    "委托数量": 100,
    "委托价格": 10.50,
    "成交数量": 100,
    "成交价格": 10.50,
    "状态": "已成"
  }
]
```

---

### 3.9 `GET /today_trades` — 查询当日成交

#### 请求

无额外参数。

```bash
curl http://192.168.1.100:1430/today_trades \
  -H "X-API-Key: your-secret-key"
```

#### 响应

```json
HTTP/1.1 200 OK
[
  {
    "成交编号": "67890",
    "证券代码": "600000",
    "证券名称": "浦发银行",
    "操作": "买入",
    "成交数量": 100,
    "成交价格": 10.50,
    "成交时间": "10:30:05"
  }
]
```

---

### 3.10 `GET /cancel_entrusts` — 查询可撤委托

#### 请求

无额外参数。

```bash
curl http://192.168.1.100:1430/cancel_entrusts \
  -H "X-API-Key: your-secret-key"
```

#### 响应

返回当前可以撤销的委托列表，格式同 `/today_entrusts`。

---

### 3.11 `POST /cancel_entrust` — 撤销委托

#### 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `entrust_no` | string | 是 | 委托编号，从 `/today_entrusts` 或 `/cancel_entrusts` 获取 |

```bash
curl -X POST http://192.168.1.100:1430/cancel_entrust \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"entrust_no": "12345"}'
```

#### 响应

```json
HTTP/1.1 201 Created
{"message": "success"}
```

---

### 3.12 `GET /auto_ipo` — 自动打新

自动申购当日所有可申购的新股。

#### 请求

无额外参数。

```bash
curl http://192.168.1.100:1430/auto_ipo \
  -H "X-API-Key: your-secret-key"
```

#### 响应

```json
HTTP/1.1 200 OK
{"message": "success"}
```

若无新股可申购：

```json
HTTP/1.1 200 OK
{"message": "今日无新股"}
```

---

### 3.13 `GET /exit` — 退出服务

关闭券商客户端并清理资源。

#### 请求

无额外参数。

```bash
curl http://192.168.1.100:1430/exit \
  -H "X-API-Key: your-secret-key"
```

#### 响应

```json
HTTP/1.1 200 OK
{"msg": "exit success"}
```

---

## 四、接口总览

| 方法 | 路径 | 功能 | 需先调用 prepare |
|------|------|------|:---:|
| POST | `/prepare` | 登录券商客户端 | - |
| GET | `/balance` | 查询账户资金 | 是 |
| GET | `/position` | 查询持仓 | 是 |
| POST | `/buy` | 限价买入 | 是 |
| POST | `/sell` | 限价卖出 | 是 |
| POST | `/market_buy` | 市价买入 | 是 |
| POST | `/market_sell` | 市价卖出 | 是 |
| GET | `/today_entrusts` | 查询当日委托 | 是 |
| GET | `/today_trades` | 查询当日成交 | 是 |
| GET | `/cancel_entrusts` | 查询可撤委托 | 是 |
| POST | `/cancel_entrust` | 撤销指定委托 | 是 |
| GET | `/auto_ipo` | 自动打新 | 是 |
| GET | `/exit` | 退出并关闭客户端 | 是 |

---

## 五、Python SDK 调用示例

```python
import easytrader.remote_client as remote

# 1. 创建连接
user = remote.use(
    broker="yh_client",
    host="192.168.1.100",
    port=1430,
    api_key="your-secret-key",
)

# 2. 登录
user.prepare(config_path="yh_client.json")

# 3. 查询
print("资金:", user.balance)
print("持仓:", user.position)
print("委托:", user.today_entrusts)
print("成交:", user.today_trades)

# 4. 交易
result = user.buy(security="600000", price=10.50, amount=100)
print("买入结果:", result)

result = user.sell(security="600000", price=11.00, amount=100)
print("卖出结果:", result)

# 5. 撤单
user.cancel_entrust(entrust_no="12345")

# 6. 打新
print(user.auto_ipo())

# 7. 退出
user.exit()
```

---

## 六、典型部署架构

```
                     ┌──────────────────────────────┐
                     │       交易机器 (Windows)       │
                     │                              │
  局域网 / VPN       │  ┌────────────────────────┐  │
┌──────────┐   HTTP  │  │   Flask Server :1430   │  │
│ 策略服务器 ├────────►│  │   (EASYTRADER_API_KEY) │  │
│(Python)  │         │  └───────────┬────────────┘  │
└──────────┘         │              │ pywinauto      │
                     │  ┌───────────▼────────────┐  │
                     │  │   券商客户端 (GUI)      │  │
                     │  │   银河/华泰/国金/广发   │  │
                     │  └────────────────────────┘  │
                     └──────────────────────────────┘
```

### 安全建议

1. **务必配置 API Key**：设置 `EASYTRADER_API_KEY` 环境变量
2. **使用反向代理加 TLS**：在 Flask 前部署 Nginx/Caddy，启用 HTTPS
3. **网络隔离**：交易机器不应暴露在公网，仅局域网或 VPN 可达
4. **加密配置文件**：使用 `easytrader encrypt <config.json>` 加密账户密码
