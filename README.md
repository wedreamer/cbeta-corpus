# cbeta-corpus

管理 [CBETA](https://www.cbeta.org/) 原始经论的仓库。本仓库 **不直接托管全量 XML**（约 2GB+，且受 CC BY-NC-SA 4.0 与部分非 CC 文献约束），而是：

1. 锁定官方发行标签（如 `cbeta-org/xml-p5@2026R2`）
2. 用 scope 文件选择藏经 / 部类 / 作译者 / 经号范围
3. 下载、校验、生成可重现的 lockfile
4. 把干净目录与元数据交给 [cbeta-mcp](https://github.com/wedreamer/cbeta-mcp) 构建索引

配套引擎仓库：[wedreamer/cbeta-mcp](https://github.com/wedreamer/cbeta-mcp)

## 为什么要拆成两个仓库

| 仓库 | 职责 |
|---|---|
| **cbeta-corpus** | 数据来源、版本锁、范围筛选、完整性校验、版权允许清单 |
| **cbeta-mcp** | 解析、归一化、索引、搜索、引文校验、MCP 服务 |

范围一改，必须重新 `fetch → catalog → index`。两仓库用 **content-addressed artifact id** 对齐：

```text
{cbeta_tag}+{scope_hash}
# 例: 2026R2+a3f91c2e
```

## 官方数据源

| 资源 | 用途 |
|---|---|
| [cbeta-org/xml-p5](https://github.com/cbeta-org/xml-p5) | 正式 TEI P5 XML，标签 `2019Q1` … `2026R2` |
| [cbeta-org/BM_u8](https://github.com/cbeta-org/BM_u8) | 简单标记 UTF-8 经文（可选，解析更快） |
| [cbeta-org/cbeta_gaiji](https://github.com/cbeta-org/cbeta_gaiji) | 缺字 / 梵字 |
| [DILA-edu/cbeta-metadata](https://github.com/DILA-edu/cbeta-metadata) | 经名、作译者、朝代、部类、异体字 |
| [DILA-edu/cbeta-documentation](https://github.com/DILA-edu/cbeta-documentation) | 文件结构与藏经代码 |

**不使用** [cbeta-git/xml-p5a](https://github.com/cbeta-git/xml-p5a)（内部校订版）作为公开产物基线。

最新发行标签（截止 2026-09）：`2026R2`（2026-09-05）。历史标签为 `YYYYnQn` / `YYYYnRn`。

## 快速开始

```bash
git clone https://github.com/wedreamer/cbeta-corpus.git
cd cbeta-corpus

# 1. 按 lockfile 拉取官方仓库的指定 tag（默认 2026R2）
./scripts/fetch.sh

# 2. 按 scope 筛选经文并写出目录
python3 scripts/select_scope.py --scope scopes/taisho.yaml

# 3. 校验 SHA / 文件数 / 缺字表
python3 scripts/verify_lock.py
```

数据默认落在 `~/.cbeta/corpus/<tag>/`，不会进 git。

## 目录结构

```text
cbeta-corpus/
  sources.lock.yaml          # 锁定官方 repo + tag + 预期 SHA
  manifests/releases/        # 每个 CBETA 发行的人可读说明
  scopes/                    # 可选范围，改范围必须重建
  schemas/                   # YAML JSON Schema
  scripts/                   # fetch / select / verify
  catalog/                   # 由脚本生成，不提交全量
  fixtures/                  # 极小公开样例（仅 teiHeader 摘要）
  docs/
```

## Scope 语义

Scope 决定「这次构建纳入哪些经论」。常见预设：

| 文件 | 范围 |
|---|---|
| `scopes/taisho.yaml` | 仅大正藏 T |
| `scopes/taisho-xuzang.yaml` | 大正藏 T + 新纂卍续藏 X |
| `scopes/cc-open.yaml` | 全部 CC BY-NC-SA 可用藏经（排除 Category B） |
| `scopes/yoga-vijnana.yaml` | 瑜伽 / 唯识部类示例 |

改 scope 会改变 `scope_hash`，[cbeta-mcp](https://github.com/wedreamer/cbeta-mcp) 必须重建索引。

过滤维度：

- `canons`：T X A K S F C U P J L G M D N ZS I ZW B GA GB CC …
- `works` / `work_globs`：`T0235`、`T15*`
- `categories`：部类（阿含、般若、法相、瑜伽、论集…）
- `creators` / `dynasties`：鸠摩罗什、玄奘、唐
- `div_types`：jing / lun / lü / xu / w / commentary
- `license`：`cc-by-nc-sa` 或 `all`（`all` 才包含 Y / TX / LC / YP）

## 版权

- **本仓库代码**：MIT（见 [LICENSE](LICENSE)）
- **CBETA 经文数据**：默論 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)，限非营利使用；再发布必须附上 CBETA 说明与版本信息。详见 [NOTICE](NOTICE) 与 [https://cbeta.org/copyright](https://cbeta.org/copyright)
- **Category B**（印順 Y、太虛 TX、吕澄 LC、演培 YP）**不是** CC，默认 scope 排除

本仓库不提供商业授权。若需超出 CC 范围，请直接联系 CBETA 或原出版方。

## 与 cbeta-mcp 的接口

`select_scope.py` 会写出：

```text
~/.cbeta/corpus/2026R2/scopes/taisho/
  MANIFEST.json      # tag, scope_hash, work_count, license
  catalog.jsonl      # 每经一行：title / author / dynasty / category
  files.txt          # 相对 xml-p5 的文件列表
  NOTICE             # 必须随产物走的版权声明
```

cbeta-mcp 只读这个目录，不直接 clone 全量 xml-p5。
