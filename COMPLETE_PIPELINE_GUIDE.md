# 完整域名验证Pipeline指南 / Complete Domain Verification Pipeline Guide

## 🎯 Pipeline概述 / Pipeline Overview

完整的三阶段域名验证系统：

```
输入CSV → [阶段1] API查询 → [阶段2] Playwright爬取 → [阶段3] TXT验证 → 最终报告
```

## 📁 数据组织结构 / Data Organization

每次运行都会生成唯一的 `run_id`，所有数据按以下结构组织：

```
backend/
└── data/
    └── run_{run_id}/                    # 每次运行的独立目录
        ├── input.csv                     # 输入文件副本
        ├── txt_verification.db           # TXT验证数据库
        │
        ├── intermediate/                 # 中间产物
        │   ├── stage1_api_results.json           # 阶段1: API结果
        │   ├── stage1_failed_domains.txt         # 阶段1: 失败域名列表
        │   ├── stage1_metadata.json              # 阶段1: 元数据
        │   │
        │   ├── stage2_playwright_results.json    # 阶段2: Playwright结果
        │   ├── stage2_need_txt_verification.txt  # 阶段2: 需要TXT验证的域名
        │   ├── stage2_metadata.json              # 阶段2: 元数据
        │   │
        │   ├── stage3_txt_tasks.json             # 阶段3: TXT任务
        │   └── stage3_metadata.json              # 阶段3: 元数据
        │
        ├── screenshots/                  # Playwright截图
        │   ├── 001_delhaize_be.png
        │   ├── 002_aholddelhaize_be.png
        │   └── ...
        │
        └── results/                      # 最终结果
            ├── FINAL_REPORT.txt               # 文本报告
            ├── FINAL_REPORT.json              # JSON报告
            ├── TXT_VERIFICATION_INSTRUCTIONS.txt  # TXT验证指令
            └── all_results_{run_id}.csv       # 所有结果CSV
```

## 🔄 Pipeline三个阶段 / Three Pipeline Stages

### 阶段1: RDAP/WHOIS API查询 / Stage 1: API Lookup

**目标**: 使用官方RDAP和WHOIS API获取域名信息

**输入**: 
- `input.csv` - 域名列表

**处理**:
```python
for domain in domains:
    1. 尝试RDAP查询 (官方注册局API)
    2. 如果失败，尝试WHOIS API (API Ninjas)
    3. 记录成功/失败
```

**输出**:
- `intermediate/stage1_api_results.json` - 成功获取的域名数据
- `intermediate/stage1_failed_domains.txt` - 需要进入阶段2的域名
- `intermediate/stage1_metadata.json` - 统计信息

**成功率**: ~45-60% (取决于域名后缀)

---

### 阶段2: Playwright网页爬取 / Stage 2: Playwright Scraping

**目标**: 爬取who.is网站获取API不支持的域名信息

**输入**:
- `intermediate/stage1_failed_domains.txt` - 阶段1失败的域名

**处理**:
```python
for domain in failed_domains:
    1. 启动Playwright浏览器
    2. 访问 https://who.is/whois/{domain}
    3. 截图保存
    4. 提取WHOIS数据 (registrant, registrar, dates)
    5. 保存结果
```

**输出**:
- `intermediate/stage2_playwright_results.json` - Playwright爬取结果
- `screenshots/*.png` - 每个域名的截图
- `intermediate/stage2_need_txt_verification.txt` - 仍无法确定的域名
- `intermediate/stage2_metadata.json` - 统计信息

**成功率**: ~40-70% (取决于who.is数据可用性)

---

### 阶段3: TXT记录验证 / Stage 3: TXT Verification

**目标**: 为无法确定所有权的域名创建TXT验证任务

**输入**:
- `intermediate/stage2_need_txt_verification.txt` - 仍需验证的域名

**处理**:
```python
for domain in uncertain_domains:
    1. 生成唯一验证token
    2. 创建TXT验证任务
    3. 保存到数据库
    4. 生成用户指令
```

**输出**:
- `intermediate/stage3_txt_tasks.json` - TXT任务列表
- `results/TXT_VERIFICATION_INSTRUCTIONS.txt` - 用户操作指令
- `txt_verification.db` - TXT验证数据库
- `intermediate/stage3_metadata.json` - 统计信息

**用户操作**:
```
为域名 example.com 添加DNS TXT记录：
  Host: @
  Type: TXT
  Value: momen-verify-abc123def456
```

系统将自动轮询检查TXT记录，验证域名控制权。

---

## 📊 最终报告 / Final Report

### `results/FINAL_REPORT.txt`

```
================================================================================
COMPLETE DOMAIN VERIFICATION PIPELINE - FINAL REPORT
================================================================================

Run ID: 20251129_113205
Timestamp: 2025-11-29T11:32:05
Total Processing Time: 250.5 seconds (4.2 minutes)
Total Domains: 75

--------------------------------------------------------------------------------
STAGE 1: RDAP/WHOIS API LOOKUP
--------------------------------------------------------------------------------
Successful: 34
Failed: 41
Success Rate: 45.3%

--------------------------------------------------------------------------------
STAGE 2: PLAYWRIGHT SCRAPING
--------------------------------------------------------------------------------
Processed: 41
Successful: 25
Screenshots Captured: 41

--------------------------------------------------------------------------------
STAGE 3: TXT VERIFICATION
--------------------------------------------------------------------------------
Tasks Created: 16
Status: Waiting for DNS records

--------------------------------------------------------------------------------
OVERALL SUMMARY
--------------------------------------------------------------------------------
Resolved (Stage 1 + 2): 59/75 (78.7%)
Pending TXT Verification: 16
Total Success Rate: 78.7%
```

### `results/FINAL_REPORT.json`

完整的JSON格式报告，方便程序处理。

---

## 🚀 如何运行完整Pipeline / How to Run

### 方法1: 运行完整Pipeline

```bash
cd backend
source venv/bin/activate
PYTHONPATH=$PWD python complete_domain_pipeline.py
```

### 方法2: 使用特定输入文件

```python
# 修改 complete_domain_pipeline.py 中的 main() 函数
input_csv = "path/to/your/domains.csv"
```

### 方法3: 查看特定运行结果

```bash
# 列出所有运行
ls -lh data/

# 查看特定运行
cd data/run_20251129_113205/
cat results/FINAL_REPORT.txt
```

---

## 📋 运行示例 / Example Run

### 输入: Houthoff-Challenge_Domain-Names.csv (75个域名)

**运行ID**: `20251129_113205`

#### 阶段1结果:
- ✅ 成功: 34 个域名 (RDAP/WHOIS API)
- ❌ 失败: 41 个域名 → 进入阶段2

#### 阶段2结果:
- ✅ 成功: 25 个域名 (Playwright)
- ❌ 失败: 16 个域名 → 进入阶段3
- 📸 截图: 41 张

#### 阶段3结果:
- 📝 创建: 16 个TXT验证任务
- 🔐 等待用户添加DNS记录

#### 最终统计:
- **总解析率**: 59/75 = 78.7%
- **待验证**: 16 个域名
- **总耗时**: ~4.2 分钟

---

## 🔍 查看结果 / View Results

### 查看最终报告

```bash
cd data/run_20251129_113205/
cat results/FINAL_REPORT.txt
```

### 查看截图

```bash
ls screenshots/
open screenshots/001_delhaize_be.png
```

### 查看中间产物

```bash
# 阶段1: API结果
cat intermediate/stage1_api_results.json | python -m json.tool | head -50

# 阶段2: Playwright结果
cat intermediate/stage2_playwright_results.json | python -m json.tool

# 阶段3: TXT任务
cat intermediate/stage3_txt_tasks.json | python -m json.tool
```

### 查看CSV结果

```bash
open results/all_results_20251129_113205.csv
```

---

## 🔐 TXT验证流程 / TXT Verification Flow

### 1. 查看TXT验证指令

```bash
cat results/TXT_VERIFICATION_INSTRUCTIONS.txt
```

### 2. 添加DNS TXT记录

为每个域名添加相应的TXT记录（在域名注册商处操作）

### 3. 系统自动验证

后台worker会每60秒检查一次DNS TXT记录：

```bash
# 启动TXT验证worker
python txt_worker.py
```

### 4. 查看验证状态

```python
from src.core.txt_verification import TXTVerificationManager

txt_manager = TXTVerificationManager(
    db_path="data/run_20251129_113205/txt_verification.db"
)

# 获取所有任务
tasks = txt_manager.get_tasks_by_case("20251129_113205")

for task in tasks:
    print(f"{task['domain']}: {task['status']}")
```

---

## 📈 Pipeline优势 / Pipeline Advantages

### 1. 完整性
- ✅ 三层验证机制，最大化数据获取
- ✅ API失败 → Playwright备用
- ✅ 数据不足 → TXT主动验证

### 2. 可追溯性
- ✅ 每次运行独立目录
- ✅ 完整的中间产物
- ✅ 详细的元数据

### 3. 可恢复性
- ✅ 每阶段独立保存
- ✅ 可以单独重跑某个阶段
- ✅ 中断后可以继续

### 4. 可视化
- ✅ 每个域名都有截图
- ✅ 完整的JSON和CSV报告
- ✅ 清晰的TXT验证指令

---

## 🛠️ 维护和扩展 / Maintenance

### 添加新的数据源

在 `src/core/` 中添加新的客户端，然后在pipeline中添加新阶段。

### 修改截图设置

在 `complete_domain_pipeline.py` 的 `scrape_with_playwright()` 方法中修改。

### 自定义报告格式

修改 `generate_final_report()` 方法。

---

## ❓ 常见问题 / FAQ

### Q1: 为什么需要三个阶段？
**A**: 不同域名后缀的数据可用性不同。多层机制确保最大覆盖率。

### Q2: 截图用途是什么？
**A**: 作为证据，证明在特定时间点域名的WHOIS信息。

### Q3: TXT验证需要多久？
**A**: DNS传播通常需要几分钟到几小时。系统会自动轮询检查。

### Q4: 如何合并所有阶段的结果？
**A**: 查看 `results/all_results_{run_id}.csv` 和 `FINAL_REPORT.json`

### Q5: 可以只运行某一阶段吗？
**A**: 可以，但建议运行完整pipeline以获得最佳结果。

---

## 🎯 最佳实践 / Best Practices

1. **定期备份** data/ 目录
2. **保留运行历史** 以便追溯
3. **监控TXT验证** 确保及时完成
4. **检查截图** 验证数据准确性
5. **导出报告** 用于法律文档

---

## 📞 支持 / Support

如有问题，查看：
- `SYSTEM_SUMMARY.txt` - 系统总览
- `API_USAGE_EXPLANATION.md` - API使用说明
- `REFACTORING_GUIDE.md` - 代码结构说明

---

**完整Pipeline = API查询 + Playwright爬取 + TXT验证** ✅

每次运行都会生成独立的 `data/run_{run_id}/` 目录，包含所有输入、输出和中间产物！

