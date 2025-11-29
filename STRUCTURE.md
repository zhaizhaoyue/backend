# 后端项目结构说明 / Backend Project Structure

## 完整目录树 / Complete Directory Tree

```
backend/
│
├── config/                          # 配置管理 / Configuration Management
│   ├── __init__.py                  # 导出settings / Export settings
│   └── settings.py                  # 🔑 所有API密钥和配置 / All API keys and config
│
├── data/                            # 数据存储目录 / Data Storage Directory
│   ├── screenshots/                 # 网页截图 / Website screenshots
│   ├── exports/                     # CSV导出文件 / CSV export files
│   ├── evidence/                    # 证据文件 / Evidence files
│   └── txt_verification.db          # TXT验证数据库 / TXT verification database
│
├── src/                             # 源代码 / Source Code
│   ├── __init__.py
│   │
│   ├── api/                         # API层 / API Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py          # 依赖注入 / Dependency Injection
│   │   │                            # - get_rdap_client()
│   │   │                            # - get_txt_manager()
│   │   │                            # - get_results_storage()
│   │   │
│   │   └── routes/                  # API路由 / API Routes
│   │       ├── __init__.py          # 导出所有路由 / Export all routes
│   │       ├── health.py            # GET  / - 根端点
│   │       │                        # GET  /api/health - 健康检查
│   │       ├── domains.py           # POST /api/domains/lookup - 域名查询
│   │       │                        # GET  /api/domains/results/{id}/csv - 下载CSV
│   │       └── txt_verification.py  # GET  /api/txt-verification/{task_id}
│   │                                # GET  /api/txt-verification/results/{run_id}/tasks
│   │
│   ├── core/                        # 核心业务逻辑 / Core Business Logic
│   │   ├── __init__.py
│   │   ├── rdap_client.py           # RDAP/WHOIS客户端
│   │   │                            # - RDAPClient类
│   │   │                            # - lookup_domain()
│   │   │                            # - parse_rdap_response()
│   │   ├── legal_intel.py           # 法律风险智能分类
│   │   │                            # - LegalIntelligence类
│   │   │                            # - classify()
│   │   │                            # - _is_natural_person()
│   │   └── txt_verification.py      # TXT记录验证管理
│   │                                # - TXTVerificationManager类
│   │                                # - create_txt_task()
│   │                                # - assess_ownership()
│   │
│   ├── database/                    # 数据库层 / Database Layer
│   │   ├── __init__.py
│   │   └── txt_database.py          # TXT验证SQLite数据库
│   │                                # - TXTDatabase类
│   │                                # - create_txt_task()
│   │                                # - get_txt_task()
│   │
│   ├── models/                      # 数据模型 / Data Models (Pydantic)
│   │   ├── __init__.py
│   │   └── domain.py                # - DomainResult
│   │                                # - LookupRequest
│   │                                # - LookupResponse
│   │                                # - TXTVerificationTask
│   │                                # - TXTVerificationStatus
│   │
│   └── utils/                       # 工具函数 / Utility Functions
│       ├── __init__.py
│       ├── csv_exporter.py          # CSV导出工具
│       │                            # - CSVExporter.export_to_csv()
│       └── evidence_generator.py    # 证据生成工具
│                                    # - EvidenceGenerator类
│
├── scripts/                         # 实用脚本 / Utility Scripts
│   ├── check_config.py              # 检查配置 / Check configuration
│   ├── start.sh                     # 启动脚本 / Start script
│   └── process_csv.py               # CSV处理 / CSV processing
│
├── tests/                           # 测试文件 / Test Files
│   ├── test_rdap_client.py
│   ├── test_legal_intel.py
│   └── ...
│
├── venv/                            # Python虚拟环境 / Virtual environment
│
├── main_refactored.py              # 🚀 新的应用入口 / New app entry point
├── main.py                         # 旧的入口(保留) / Old entry (kept)
│
├── .env                            # 🔑 你的API密钥 (不提交到Git) / Your keys (DON'T commit)
├── .env.example                    # 环境变量模板 / Env template
├── .gitignore                      # Git忽略文件 / Git ignore
│
├── requirements.txt                # Python依赖 / Python dependencies
├── runtime.txt                     # Python版本 / Python version
│
├── REFACTORING_GUIDE.md           # 📖 重构指南 / Refactoring guide
├── API_KEY_GUIDE.md               # 🔑 API密钥指南 / API key guide
├── STRUCTURE.md                   # 📁 本文件 / This file
├── README.md                      # 项目说明 / Project readme
│
├── Dockerfile                     # Docker配置 / Docker config
├── Procfile                       # Heroku配置 / Heroku config
├── railway.json                   # Railway配置 / Railway config
└── render.yaml                    # Render配置 / Render config
```

## 核心文件说明 / Core Files Explanation

### 🔑 配置文件 / Configuration Files

| 文件 / File | 用途 / Purpose | 重要性 / Importance |
|------------|--------------|-------------------|
| `.env` | 存储API密钥和环境变量 | ⭐⭐⭐⭐⭐ |
| `config/settings.py` | 配置管理代码 | ⭐⭐⭐⭐⭐ |
| `.env.example` | 环境变量模板 | ⭐⭐⭐ |

### 🚀 应用入口 / Application Entry

| 文件 / File | 用途 / Purpose | 使用 / Usage |
|------------|--------------|------------|
| `main_refactored.py` | 新的重构版本 | `python main_refactored.py` |
| `main.py` | 旧版本(保留) | `python main.py` |

### 📋 API路由 / API Routes

| 文件 / File | 路由 / Routes | 功能 / Function |
|------------|--------------|----------------|
| `src/api/routes/health.py` | `/`, `/api/health` | 健康检查 |
| `src/api/routes/domains.py` | `/api/domains/*` | 域名查询 |
| `src/api/routes/txt_verification.py` | `/api/txt-verification/*` | TXT验证 |

### 🧠 核心逻辑 / Core Logic

| 文件 / File | 类 / Class | 功能 / Function |
|------------|-----------|----------------|
| `src/core/rdap_client.py` | `RDAPClient` | RDAP/WHOIS查询 |
| `src/core/legal_intel.py` | `LegalIntelligence` | 法律风险分类 |
| `src/core/txt_verification.py` | `TXTVerificationManager` | TXT验证管理 |

### 💾 数据层 / Data Layer

| 文件 / File | 类 / Class | 功能 / Function |
|------------|-----------|----------------|
| `src/database/txt_database.py` | `TXTDatabase` | SQLite数据库操作 |
| `src/utils/csv_exporter.py` | `CSVExporter` | CSV导出 |

## 数据流 / Data Flow

```
前端请求 / Frontend Request
    ↓
main_refactored.py (FastAPI App)
    ↓
src/api/routes/*.py (API Routes)
    ↓
src/api/dependencies.py (Dependency Injection)
    ↓
src/core/*.py (Business Logic)
    ↓
src/database/*.py (Data Layer)
    ↓
data/ (File Storage)
```

## 配置流 / Configuration Flow

```
.env 文件 / .env file
    ↓
config/settings.py (读取 / Read)
    ↓
Settings 类实例 / Settings instance
    ↓
依赖注入 / Dependency Injection
    ↓
API路由和核心逻辑 / API routes and core logic
```

## API端点映射 / API Endpoint Mapping

```
根端点 / Root Endpoints
├── GET  /                              → health.py:root()
└── GET  /api/health                    → health.py:health_check()

域名查询 / Domain Lookups
├── POST /api/domains/lookup            → domains.py:lookup_domains()
└── GET  /api/domains/results/{id}/csv  → domains.py:get_results_csv()

TXT验证 / TXT Verification
├── GET  /api/txt-verification/{task_id}           → txt_verification.py:get_txt_verification_status()
└── GET  /api/txt-verification/results/{id}/tasks  → txt_verification.py:get_run_txt_tasks()
```

## 模块依赖关系 / Module Dependencies

```
main_refactored.py
├── config.settings
├── src.api.routes.health
├── src.api.routes.domains
└── src.api.routes.txt_verification

src.api.routes.domains
├── src.models.domain
├── src.core.rdap_client
├── src.core.txt_verification
├── src.utils.csv_exporter
└── src.api.dependencies

src.core.rdap_client
└── httpx (external)

src.core.txt_verification
└── src.database.txt_database

src.database.txt_database
└── sqlite3 (stdlib)
```

## 快速查找 / Quick Reference

### 我想修改.../ I want to modify...

| 需求 / Need | 文件位置 / File Location |
|-----------|------------------------|
| 添加API密钥 | `.env` + `config/settings.py` |
| 添加新的API端点 | `src/api/routes/` 新建文件 |
| 修改RDAP查询逻辑 | `src/core/rdap_client.py` |
| 修改风险分类规则 | `src/core/legal_intel.py` |
| 修改数据模型 | `src/models/domain.py` |
| 修改CSV导出格式 | `src/utils/csv_exporter.py` |
| 修改数据库结构 | `src/database/txt_database.py` |

### 我想查看.../ I want to check...

| 需求 / Need | 命令 / Command |
|-----------|---------------|
| 查看当前配置 | `python scripts/check_config.py` |
| 测试RDAP客户端 | `python -m pytest tests/test_rdap_client.py` |
| 查看API文档 | 访问 `http://localhost:8000/docs` |
| 查看数据库 | `sqlite3 data/txt_verification.db` |

## 文件大小参考 / File Size Reference

| 类型 / Type | 大小范围 / Size Range |
|-----------|---------------------|
| 配置文件 / Config | 50-200 行 |
| API路由文件 / API Routes | 50-150 行 |
| 核心逻辑文件 / Core Logic | 100-300 行 |
| 工具文件 / Utilities | 50-150 行 |
| 测试文件 / Tests | 100-500 行 |

## 代码风格 / Code Style

- **Python版本 / Python Version**: 3.14+
- **格式化 / Formatting**: PEP 8
- **类型提示 / Type Hints**: ✓ 使用 / Used
- **文档字符串 / Docstrings**: Google style
- **导入顺序 / Import Order**: stdlib → external → internal

## 环境要求 / Environment Requirements

```
Python 3.14+
FastAPI 0.115.0+
Pydantic 2.10.0+
HTTPX 0.28.0+
Playwright 1.49.0+
```

## 下一步 / Next Steps

1. ✅ 复制 `.env.example` 到 `.env`
2. ✅ 填写API密钥到 `.env`
3. ✅ 运行 `python scripts/check_config.py` 检查配置
4. ✅ 运行 `python main_refactored.py` 启动服务
5. ✅ 访问 `http://localhost:8000/docs` 查看API文档

## 帮助文档 / Help Documentation

- **重构指南** / Refactoring Guide: `REFACTORING_GUIDE.md`
- **API密钥指南** / API Key Guide: `API_KEY_GUIDE.md`
- **项目结构** / Project Structure: `STRUCTURE.md` (本文件)
- **系统总结** / System Summary: `SYSTEM_SUMMARY.txt`
- **WHOIS指南** / WHOIS Guide: `OFFICIAL_WHOIS_GUIDE.txt`

