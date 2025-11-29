# Pipeline快速参考 / Quick Reference

## 🎯 完整Pipeline三阶段

```
CSV输入 → [1] API查询 → [2] Playwright → [3] TXT验证 → 最终报告
          ↓              ↓                 ↓
        34个成功      25个成功          16个待验证
        41个失败      16个失败          (用户操作)
```

## 🚀 快速开始

```bash
cd backend
./RUN_COMPLETE_PIPELINE.sh
```

## 📁 结果位置

```
data/run_{run_id}/
├── input.csv                    # 输入
├── screenshots/                 # 截图 (阶段2)
├── intermediate/                # 中间产物
│   ├── stage1_*.json           # 阶段1结果
│   ├── stage2_*.json           # 阶段2结果
│   └── stage3_*.json           # 阶段3结果
└── results/
    ├── FINAL_REPORT.txt        # 👈 查看这个！
    ├── all_results_{id}.csv    # 所有结果
    └── TXT_VERIFICATION_INSTRUCTIONS.txt  # TXT验证指令
```

## 📊 查看结果

```bash
# 查看最终报告
cat data/run_*/results/FINAL_REPORT.txt

# 查看CSV
open data/run_*/results/all_results_*.csv

# 查看截图
open data/run_*/screenshots/
```

## 🔍 三个阶段详解

### 阶段1: API查询 (2分钟)
- **方法**: RDAP + WHOIS API
- **成功率**: ~45%
- **输出**: `intermediate/stage1_api_results.json`

### 阶段2: Playwright (3分钟)
- **方法**: 爬取who.is网站
- **成功率**: ~60% (失败域名的)
- **输出**: `intermediate/stage2_playwright_results.json` + 截图

### 阶段3: TXT验证 (用户操作)
- **方法**: DNS TXT记录验证
- **用户操作**: 添加DNS记录
- **输出**: `results/TXT_VERIFICATION_INSTRUCTIONS.txt`

## ⏱️ 时间估算

- **75个域名**: ~5-6分钟
- **阶段1**: ~2.5分钟 (75×2秒)
- **阶段2**: ~2-3分钟 (41×3秒)
- **阶段3**: 立即 (生成任务)

## 💡 关键点

1. ✅ **每次运行都有唯一ID** - 便于追溯
2. ✅ **所有数据都在data/目录** - 集中管理
3. ✅ **每个阶段独立保存** - 可恢复
4. ✅ **完整的中间产物** - 可审计
5. ✅ **所有截图保存** - 法律证据

## 🔑 重要文件

| 文件 | 用途 |
|------|------|
| `complete_domain_pipeline.py` | 主Pipeline脚本 |
| `RUN_COMPLETE_PIPELINE.sh` | 快速运行脚本 |
| `COMPLETE_PIPELINE_GUIDE.md` | 完整文档 |
| `PIPELINE_QUICK_REFERENCE.md` | 本文档 |

## 📋 示例运行

```bash
$ ./RUN_COMPLETE_PIPELINE.sh

🚀 Complete Domain Verification Pipeline
Run ID: 20251129_113205

Stage 1: API Lookup...
  ✅ 34 succeeded, ❌ 41 failed

Stage 2: Playwright...
  ✅ 25 succeeded, ❌ 16 failed
  📸 41 screenshots saved

Stage 3: TXT Verification...
  📝 16 tasks created

✅ Complete! Results in: data/run_20251129_113205/
```

## 🎯 记住这个

**完整Pipeline = 三个阶段 + 所有数据按run_id组织**

不要只运行一个阶段！要运行完整的Pipeline以获得最佳结果。

