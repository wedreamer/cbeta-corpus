# cbeta-corpus

管理 [CBETA](https://www.cbeta.org/) 原始经论的仓库。本仓库 **不直接托管全量 XML**（约 2GB+，且受 CC BY-NC-SA 4.0 与部分非 CC 文献约束），而是：

1. 锁定官方发行标签（如 `cbeta-org/xml-p5@2026R2`）
2. 用 scope 文件选择藏经 / 部类 / 作译者 / 经号范围
3. 下载、校验、生成可重现的 lockfile
4. 把干净目录与元数据交给 [cbeta-cli](https://github.com/wedreamer/cbeta-cli) 构建索引

人用的搜索、校验、引用与 MCP 都在 **cbeta-cli**。这里只管数据来源。

## 为什么要拆成两个仓库

| 仓库 | 职责 |
|---|---|
| **[cbeta-corpus](https://github.com/wedreamer/cbeta-corpus)** | 数据来源、版本锁、范围筛选、完整性校验、版权允许清单 |
| **[cbeta-cli](https://github.com/wedreamer/cbeta-cli)** | 解析、归一化、索引、搜索、引文校验、人用 CLI、MCP 服务 |

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

最新发行标签（截止 2026-09）：`2026R2`（2026-09-05）。

一部典籍一个 XML 文件（跨册除外）：

```text
T/T08/T08n0235.xml   金剛般若波羅蜜經
T/T19/T19n0945.xml   大佛頂首楞嚴經
T/T30/T30n1578.xml   大乘掌珍論
T/T31/T31n1585.xml   成唯識論
```

## 快速开始

```bash
git clone https://github.com/wedreamer/cbeta-corpus.git
cd cbeta-corpus

# 1. 按 lockfile 拉取官方仓库的指定 tag（默认 2026R2）
./scripts/fetch.sh

# 2. 按 scope 筛选经文并写出目录（稍后）
python3 scripts/select_scope.py --scope scopes/taisho.yaml

# 3. 校验 SHA / 文件数 / Category B（稍后）
python3 scripts/verify_lock.py
```

数据默认落在 `~/.cbeta/corpus/<tag>/`，**不会进 git**。

当前进度：[`scripts/fetch.sh`](scripts/fetch.sh) 已可用；`select_scope.py` 与 `verify_lock.py` 尚未落地。跟踪：[#1](https://github.com/wedreamer/cbeta-corpus/issues/1)。

## 目录结构

```text
cbeta-corpus/
  sources.lock.yaml          # 锁定官方 repo + tag + 预期 SHA
  scripts/fetch.sh           # 按 lock 拉取，写 FETCHED.yaml
  scopes/                    # 可选范围，改范围必须重建
  fixtures/                  # 极小公开样例（仅 teiHeader 摘要）
  docs/
```

`fetch.sh` 产物：

```text
~/.cbeta/corpus/2026R2/
  FETCHED.yaml               # tag + 各源 commit
  src/xml-p5/                # sparse checkout，默认 T/ X/
  src/metadata/
  src/gaiji/
```

## Scope 语义

Scope 决定「这次构建纳入哪些经论」。常见预设：

| 文件 | 范围 |
|---|---|
| `scopes/taisho.yaml` | 仅大正藏 T |
| `scopes/taisho-xuzang.yaml` | 大正藏 T + 新纂卍续藏 X |
| `scopes/cc-open.yaml` | 全部 CC BY-NC-SA 可用藏经（排除 Category B） |
| `scopes/ci-minimal.yaml` | T0235 / T0945 / T1578 / T1585，给 CI 与解析测试 |

改 scope 会改变 `scope_hash`，[cbeta-cli](https://github.com/wedreamer/cbeta-cli) 必须重建索引。

过滤维度：`canons` / `works` / `categories` / `creators` / `dynasties` / `div_types` / `license`。
`license: all` 才包含 Category B（Y / TX / LC / YP）。

## 交给 cbeta-cli 的接口

`select_scope.py` 会写出：

```text
~/.cbeta/corpus/2026R2/scopes/taisho/
  MANIFEST.json      # tag, scope_hash, work_count, license
  catalog.jsonl      # title / author / dynasty / category / work_id
  files.txt          # 相对 xml-p5 的文件列表
  NOTICE             # 必须随产物走的版权声明
```

cbeta-cli 只读这个目录：

```bash
cbeta build --scope taisho
cbeta search '真性有为空' --canon T
```

## 版权

- **本仓库代码**：MIT（见 [LICENSE](LICENSE)）
- **CBETA 经文数据**：默认 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)，限非营利使用；再发布必须附上 CBETA 说明与版本信息。详见 [NOTICE](NOTICE) 与 [https://cbeta.org/copyright](https://cbeta.org/copyright)
- **Category B**（Y / TX / LC / YP）**不是** CC，默认 scope 排除

## 相关

- 引擎：[wedreamer/cbeta-cli](https://github.com/wedreamer/cbeta-cli)
- 跟踪：[#1](https://github.com/wedreamer/cbeta-corpus/issues/1)
