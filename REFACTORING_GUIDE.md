# Backend Refactoring Guide

## 项目结构重构说明 / Project Structure Overview

这个后端项目已经重构为标准的Python应用程序结构，使配置管理、API路由和核心逻辑更加清晰。

This backend has been refactored into a standard Python application structure with clear separation of concerns for configuration, API routes, and core logic.

## 新的目录结构 / New Directory Structure

```
backend/
├── config/                      # 配置管理 / Configuration Management
│   ├── __init__.py
│   ├── settings.py              # 所有配置和API密钥 / All settings and API keys
│   └── .env.example             # 环境变量示例 / Environment variables example
│
├── data/                        # 数据存储 / Data Storage
│   ├── screenshots/             # 截图文件 / Screenshot files
│   ├── exports/                 # 导出的CSV文件 / Exported CSV files
│   ├── evidence/                # 证据文件 / Evidence files
│   └── txt_verification.db      # TXT验证数据库 / TXT verification database
│
├── src/                         # 源代码 / Source Code
│   ├── __init__.py
│   │
│   ├── api/                     # API层 / API Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py      # 依赖注入 / Dependency injection
│   │   └── routes/              # API路由 / API Routes
│   │       ├── __init__.py
│   │       ├── health.py        # 健康检查 / Health checks
│   │       ├── domains.py       # 域名查询 / Domain lookups
│   │       └── txt_verification.py  # TXT验证 / TXT verification
│   │
│   ├── core/                    # 核心业务逻辑 / Core Business Logic
│   │   ├── __init__.py
│   │   ├── rdap_client.py       # RDAP/WHOIS客户端 / RDAP/WHOIS client
│   │   ├── legal_intel.py       # 法律风险分类 / Legal risk classification
│   │   └── txt_verification.py  # TXT验证管理 / TXT verification management
│   │
│   ├── database/                # 数据库层 / Database Layer
│   │   ├── __init__.py
│   │   └── txt_database.py      # TXT验证数据库 / TXT verification database
│   │
│   ├── models/                  # 数据模型 / Data Models
│   │   ├── __init__.py
│   │   └── domain.py            # Pydantic模型 / Pydantic models
│   │
│   └── utils/                   # 工具函数 / Utility Functions
│       ├── __init__.py
│       ├── csv_exporter.py      # CSV导出 / CSV export
│       └── evidence_generator.py # 证据生成 / Evidence generation
│
├── scripts/                     # 脚本文件 / Utility Scripts
│   ├── start.sh
│   └── process_csv.py
│
├── tests/                       # 测试文件 / Test Files
│   └── ...
│
├── main_refactored.py          # 新的应用入口 / New application entry point
├── main.py                     # 旧的入口(保留) / Old entry point (kept)
├── requirements.txt            # Python依赖 / Python dependencies
├── .env.example               # 环境变量模板 / Environment variables template
└── README.md

```

## 如何配置API密钥 / How to Configure API Keys

### 1. 创建环境变量文件 / Create Environment File

```bash
cd backend
cp .env.example .env
```

### 2. 编辑 .env 文件 / Edit .env File

在 `.env` 文件中设置你的API密钥 / Set your API keys in the `.env` file:

```bash
# DeepSeek API Key (用于LLM解析 / For LLM parsing)
DEEPSEEK_API_KEY=sk-your-actual-deepseek-api-key-here

# API Ninjas Key (用于WHOIS备用 / For WHOIS fallback)
API_NINJAS_KEY=your-api-ninjas-key-here

# 其他配置 / Other settings
DEBUG=true
PORT=8000
```

### 3. API密钥使用位置 / Where API Keys Are Used

所有API密钥都在 `config/settings.py` 中统一管理：

All API keys are centrally managed in `config/settings.py`:

```python
from config.settings import settings

# 在代码中使用 / Use in your code:
deepseek_key = settings.deepseek_api_key
api_ninjas_key = settings.api_ninjas_key
```

## 如何运行重构后的应用 / How to Run the Refactored Application

### 方法1：直接运行 / Method 1: Direct Run

```bash
cd backend
python main_refactored.py
```

### 方法2：使用uvicorn / Method 2: Use Uvicorn

```bash
cd backend
uvicorn main_refactored:app --host 0.0.0.0 --port 8000 --reload
```

### 方法3：切换到新版本 / Method 3: Switch to New Version

```bash
cd backend
# 备份旧版本 / Backup old version
mv main.py main_old.py

# 使用新版本 / Use new version
mv main_refactored.py main.py

# 运行 / Run
python main.py
```

## 配置说明 / Configuration Details

### config/settings.py

这个文件包含所有应用配置：

This file contains all application settings:

- **API密钥 / API Keys**: `deepseek_api_key`, `api_ninjas_key`, `openai_api_key`
- **数据库路径 / Database Path**: `database_path`
- **文件存储路径 / File Storage Paths**: `data_dir`, `screenshots_dir`, `exports_dir`
- **服务器配置 / Server Configuration**: `host`, `port`, `debug`
- **CORS设置 / CORS Settings**: `cors_origins`

### 环境变量优先级 / Environment Variable Priority

1. `.env` 文件中的值 / Values in `.env` file
2. 系统环境变量 / System environment variables  
3. `settings.py` 中的默认值 / Default values in `settings.py`

## 添加新的API端点 / Adding New API Endpoints

### 步骤 / Steps:

1. 在 `src/api/routes/` 中创建新文件 / Create new file in `src/api/routes/`
2. 定义路由器 / Define router:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/your-endpoint", tags=["your-tag"])

@router.get("/")
async def your_endpoint():
    return {"message": "Hello"}
```

3. 在 `src/api/routes/__init__.py` 中导出 / Export in `src/api/routes/__init__.py`:

```python
from .your_new_route import router as your_router

__all__ = [..., "your_router"]
```

4. 在 `main_refactored.py` 中注册 / Register in `main_refactored.py`:

```python
from src.api.routes import ..., your_router

app.include_router(your_router)
```

## 添加新的配置项 / Adding New Configuration

在 `config/settings.py` 的 `Settings` 类中添加：

Add to the `Settings` class in `config/settings.py`:

```python
class Settings(BaseSettings):
    # 新的配置项 / New configuration
    your_new_setting: str = "default_value"
    your_api_key: Optional[str] = None
```

然后在 `.env.example` 和 `.env` 中添加对应的环境变量。

Then add corresponding environment variables in `.env.example` and `.env`.

## 数据库和文件存储 / Database and File Storage

所有数据文件都存储在 `data/` 目录下：

All data files are stored in the `data/` directory:

- **TXT验证数据库 / TXT Verification DB**: `data/txt_verification.db`
- **截图 / Screenshots**: `data/screenshots/`
- **导出文件 / Exports**: `data/exports/`
- **证据文件 / Evidence**: `data/evidence/`

配置路径在 `config/settings.py` 中设置。

Paths are configured in `config/settings.py`.

## 依赖注入 / Dependency Injection

使用 FastAPI 的依赖注入系统，在 `src/api/dependencies.py` 中定义：

Use FastAPI's dependency injection system, defined in `src/api/dependencies.py`:

```python
from fastapi import Depends
from src.api.dependencies import get_rdap_client

@router.get("/example")
async def example(rdap_client = Depends(get_rdap_client)):
    # 使用 rdap_client / Use rdap_client
    pass
```

## 迁移检查清单 / Migration Checklist

- [x] 创建新目录结构 / Create new directory structure
- [x] 配置管理系统 / Configuration management system
- [x] 移动核心业务逻辑 / Move core business logic
- [x] 重组API路由 / Reorganize API routes
- [x] 移动模型和工具 / Move models and utilities
- [x] 更新依赖 / Update dependencies
- [ ] 更新部署脚本 / Update deployment scripts
- [ ] 更新测试文件 / Update test files
- [ ] 更新前端API调用 / Update frontend API calls

## 常见问题 / FAQ

### Q: 如何查看当前配置？/ How to view current configuration?

```python
from config.settings import settings
print(settings.model_dump())
```

### Q: 如何在生产环境中使用？/ How to use in production?

1. 设置 `DEBUG=false` in `.env`
2. 配置正确的 `CORS_ORIGINS`
3. 使用安全的数据库连接
4. 不要在代码中硬编码密钥

### Q: 旧代码还能用吗？/ Can I still use the old code?

是的，旧的 `main.py` 仍然保留并可以使用。新结构是可选的升级。

Yes, the old `main.py` is still kept and functional. The new structure is an optional upgrade.

## 技术栈 / Tech Stack

- **FastAPI**: Web framework
- **Pydantic**: Data validation and settings management
- **HTTPX**: Async HTTP client
- **Playwright**: Browser automation
- **SQLite**: TXT verification database

## 支持 / Support

如有问题，请查看：

For issues, please check:

- `SYSTEM_SUMMARY.txt` - 系统整体说明
- `LLM_PARSING_GUIDE.txt` - LLM解析指南
- `OFFICIAL_WHOIS_GUIDE.txt` - WHOIS使用指南

