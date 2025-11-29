# API密钥使用说明 / API Key Usage Explanation

## 🔑 项目中的API密钥用途

### 1. API Ninjas Key - **必需 / REQUIRED** ✅

**用途 / Purpose**:
- WHOIS查询备用服务
- 当RDAP API不可用时使用
- 返回结构化的JSON数据

**在哪里使用 / Used in**:
- ✅ `main_refactored.py` (核心API)
- ✅ `src/core/rdap_client.py`
- ✅ `enhanced_domain_monitor.py`

**获取方式 / How to get**:
```
https://api-ninjas.com
```

---

### 2. DeepSeek API Key - **可选 / OPTIONAL** ⚠️

**用途 / Purpose**:
- 只用于解析**原始WHOIS文本**（非JSON）
- 从who.is网站爬取的HTML文本需要LLM解析
- **核心API不需要** - RDAP和API Ninjas返回的是JSON

**在哪里使用 / Used in**:
- ❌ **不在** `main_refactored.py` 中使用
- ❌ **不在** `src/core/rdap_client.py` 中使用
- ✅ **仅在** `enhanced_domain_monitor.py` 中使用

**什么时候需要 / When needed**:
```bash
# 如果你使用增强监控工具（爬取who.is网站）
python enhanced_domain_monitor.py example_input.csv --deepseek-key sk-xxx

# 如果你只使用核心API（RDAP/WHOIS JSON）- 不需要DeepSeek
python main_refactored.py
```

**获取方式 / How to get**:
```
https://platform.deepseek.com
```

---

## 📊 数据流对比

### 方案A：核心API（不需要DeepSeek）

```
用户请求
    ↓
FastAPI (main_refactored.py)
    ↓
RDAPClient (src/core/rdap_client.py)
    ↓
┌─────────────────────────────────┐
│ RDAP API → JSON 返回            │
│ {                                │
│   "registrant": "...",          │
│   "registrar": "...",           │
│   "creation_date": "..."        │
│ }                               │
└─────────────────────────────────┘
    ↓
直接解析JSON字段（parse_rdap_response）
    ↓
返回结构化数据

❌ 不需要LLM / No LLM needed
```

### 方案B：增强监控（需要DeepSeek）

```
CSV输入
    ↓
EnhancedDomainMonitor (enhanced_domain_monitor.py)
    ↓
Playwright 爬取 who.is 网站
    ↓
┌─────────────────────────────────┐
│ HTML页面文本                     │
│ "Registrant: John Doe           │
│  Created: 2020-01-01            │
│  Registrar: GoDaddy             │
│  ..."                           │
└─────────────────────────────────┘
    ↓
提取原始WHOIS文本（非结构化）
    ↓
✅ DeepSeek LLM 解析
    ↓
返回结构化JSON

✅ 需要LLM / LLM needed
```

---

## 🎯 推荐配置

### 场景1：只使用核心API

**`.env` 文件**:
```bash
# 只需要这个！
API_NINJAS_KEY=your-api-ninjas-key

# 不需要这个
# DEEPSEEK_API_KEY=...
```

**启动**:
```bash
python main_refactored.py
```

---

### 场景2：使用增强监控工具

**`.env` 文件**:
```bash
# 需要两个
API_NINJAS_KEY=your-api-ninjas-key
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

**启动**:
```bash
python enhanced_domain_monitor.py domains.csv --deepseek-key $DEEPSEEK_API_KEY
```

---

### 场景3：同时使用两者

**`.env` 文件**:
```bash
# 都配置上
API_NINJAS_KEY=your-api-ninjas-key
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

---

## 💡 常见问题 / FAQ

### Q1: 我的核心API需要DeepSeek吗？
**A**: ❌ **不需要**！RDAP和API Ninjas返回的是JSON，不需要LLM解析。

### Q2: 什么时候需要DeepSeek？
**A**: ✅ 只有在使用 `enhanced_domain_monitor.py` 爬取who.is网站时需要。

### Q3: 为什么有两种方式？
**A**: 
- **核心API**: 快速、可靠、使用官方RDAP API（推荐）
- **增强监控**: 可以获取更多信息，但需要爬取网站（备用方案）

### Q4: RDAP和WHOIS API返回什么格式？
**A**: 两者都返回 **JSON格式**，例如：

```json
{
  "registrant_organization": "Google LLC",
  "registrar": "MarkMonitor Inc.",
  "creation_date": "1997-09-15T04:00:00Z",
  "expiry_date": "2028-09-14T04:00:00Z",
  "nameservers": ["ns1.google.com", "ns2.google.com"]
}
```

这是结构化数据，不需要LLM解析！

### Q5: 我应该删除DeepSeek配置吗？
**A**: 
- 如果你**只用核心API** → 可以删除
- 如果你可能用增强监控 → 保留（但不是必需的）

---

## 🔧 配置建议

### 最小配置（核心API）

**`backend/.env`**:
```bash
# 核心API最小配置
API_NINJAS_KEY=your-api-ninjas-key
DEBUG=true
PORT=8000
```

### 完整配置（包括增强功能）

**`backend/.env`**:
```bash
# API密钥
API_NINJAS_KEY=your-api-ninjas-key
DEEPSEEK_API_KEY=sk-your-deepseek-key  # 可选

# 应用配置
DEBUG=true
PORT=8000
HOST=0.0.0.0
```

---

## 📊 性能对比

| 特性 | 核心API (RDAP/JSON) | 增强监控 (who.is爬取) |
|------|-------------------|---------------------|
| 速度 | ⚡ 快速 (API调用) | 🐌 较慢 (爬取+LLM) |
| 可靠性 | ✅ 高 | ⚠️ 中等 |
| 需要DeepSeek | ❌ 不需要 | ✅ 需要 |
| 数据格式 | JSON | 原始文本 |
| 推荐使用 | ✅ 推荐 | 备用方案 |

---

## 🎯 总结

### 核心API (`main_refactored.py`)
```
RDAP/WHOIS API → JSON → 直接解析
❌ 不需要DeepSeek
✅ 只需要API Ninjas Key
```

### 增强监控 (`enhanced_domain_monitor.py`)
```
who.is网站 → HTML文本 → LLM解析
✅ 需要DeepSeek
✅ 需要API Ninjas Key（备用）
```

**你的理解完全正确！** 核心API不需要DeepSeek处理WHOIS数据，因为返回的已经是JSON格式。🎉

