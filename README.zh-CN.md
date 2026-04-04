# Portable Project Bootstrap

Portable Project Bootstrap 是一套可移植的 workspace suite，用来校验 workspace、初始化 brand-new project，以及进入 existing-project，而不把某一台机器的路径规则硬编码进运行时。

## 快速开始

推荐的公开入口是：

```powershell
python -m portable_project_bootstrap --help
```

先做 workspace 校验：

```powershell
python -m portable_project_bootstrap.validator `
  --workspace-root <workspace_root> `
  --profile-name <profile_name>
```

对 brand-new project 做 dry-run：

```powershell
python -m portable_project_bootstrap `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>" `
  --project-slug <project_slug> `
  --project-summary "<project_summary>" `
  --tech-stack Python `
  --dry-run
```

进入 existing-project：

```powershell
python -m portable_project_bootstrap.router `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-slug <project_slug>
```

## 这个项目是什么

这个仓库提供一套分工清晰的 workspace suite：

- `workspace-validator`
  判断当前 workspace 和 profile 是否可用。
- bootstrap runtime
  负责 brand-new project 初始化和安全的 fill-missing repair。
- `workspace-router`
  负责 existing-project 路由，不会误触发 bootstrap。
- live wrapper
  负责 bootstrap 的 `new`、`legacy`、`shadow` mode 选择。

对于以 Python 为主的项目，bootstrap 现在默认会生成一个开发就绪的起步仓库。除了 repo / memory 骨架之外，它还可以初始化 git、生成 `.gitignore`、写入人类可读 `README.md`、创建最小 `pyproject.toml`，并补齐 `tests/`、`examples/`、`LICENSE`、`CONTRIBUTING.md`。

整套实现建立在几条硬规则上：

- 路径来自 profile，而不是写死在代码里
- repo 内容和 repo-external memory 必须分离
- 缺少必要上下文时要 fail closed
- 对不安全的结构化更新，只报告 manual patch，不自动应用
- `new` 失败时不能 silent fallback 到 `legacy`

## 推荐公开入口

对于公开用户，优先使用 repo-local Python 模块入口：

- bootstrap:
  - `python -m portable_project_bootstrap ...`
- validator:
  - `python -m portable_project_bootstrap.validator ...`
- router:
  - `python -m portable_project_bootstrap.router ...`

外部 skill wrapper 仍可以作为集成方式存在，但那属于已有本地 skill 环境的高级接入方式，不是本仓库默认假设的公开入口。

## Suite 工作流

### Brand-New Project Workflow

1. 先加载 profile 和 workspace context。
2. 先运行 `workspace-validator`。
3. 用 bootstrap 跑 `--dry-run`。
4. 检查 `status`、`project_index_result`、manual patch 信号、`project_index_status`、`bootstrap_log_status`。
5. dry-run 正常后，再用 `--execute`。
6. 如果行为可疑，使用 `--mode shadow`。
7. 只有在需要显式回退或隔离时，才用 `--mode legacy`。

### Existing Project Workflow

1. 先加载 profile 和 workspace context。
2. 先运行 `workspace-validator`。
3. 用 `workspace-router` 传入精确 slug、精确项目名，或其他强路由输入。
4. 先读返回的 `read_first_files`。
5. 只有在路由结果明确后，再继续项目工作。

## CLI 用法

### Bootstrap

查看帮助：

```powershell
python -m portable_project_bootstrap --help
```

brand-new project dry-run：

```powershell
python -m portable_project_bootstrap `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>" `
  --project-slug <project_slug> `
  --project-summary "<project_summary>" `
  --tech-stack Python `
  --tech-stack Markdown `
  --dry-run
```

真实执行：

```powershell
python -m portable_project_bootstrap `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>" `
  --project-slug <project_slug> `
  --project-summary "<project_summary>" `
  --tech-stack Python `
  --execute
```

默认的 Python 向 repo 输出现在包括：

- `.gitignore`
- `README.md`
- 在启用 Python metadata 时生成 `pyproject.toml`
- `tests/test_smoke.py`
- `examples/README.md`
- `LICENSE`
- `CONTRIBUTING.md`
- 默认执行 git 初始化，除非显式关闭

### Validator

```powershell
python -m portable_project_bootstrap.validator `
  --workspace-root <workspace_root> `
  --profile-name <profile_name>
```

行为约定：

- 返回 `status: ok`、`status: partial` 或 `status: error`
- `ok` / `partial` 的退出码是 `0`
- fail-closed 校验错误的退出码是 `1`

### Router

精确 slug 路由：

```powershell
python -m portable_project_bootstrap.router `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-slug <project_slug>
```

精确项目名路由：

```powershell
python -m portable_project_bootstrap.router `
  --workspace-root <workspace_root> `
  --profile-name <profile_name> `
  --project-name "<project_name>"
```

行为约定：

- 单一安全命中时返回 `status: ok`
- 有多个安全候选时返回 `status: partial`
- 无法安全路由时返回 `status: error`
- `ok` / `partial` 的退出码是 `0`
- fail-closed 路由错误的退出码是 `1`

## 模式说明

### `new`

- 默认 bootstrap 路径
- 适合正常日常使用
- 出错时显式失败
- 不会 silent fallback 到 `legacy`

### `legacy`

- 显式回退与隔离路径
- 只用于应急，不是常规默认路径

### `shadow`

- compare-only 的 bootstrap 验证路径
- 用于不写入前提下的语义对照
- 不允许真实写入

## 必填输入

bootstrap 通常需要：

- `--workspace-root`
- `--profile-name`
- `--project-name`
- `--project-slug`
- `--project-summary`
- `--tech-stack`

router 通常需要：

- `--workspace-root`
- `--profile-name`
- 一条路由查询，例如 `--project-slug`、`--project-name`、`--route-signal`、`--repo-path` 或 `--memory-path`

常用的 bootstrap 开关包括：

- `--no-init-git`
- `--no-create-license`
- `--no-create-contributing`
- `--no-create-tests`
- `--no-create-examples`
- `--no-create-stack-metadata`

## Profile 协议

官方协议：

- 主路径：
  - `<workspace_root>/.agent-memory/machine-profiles/<profile_name>.json`
- 兼容回退路径：
  - `<workspace_root>/.codex/workspace-profile/PROFILE.json`

发现顺序：

1. 显式 `--profile-path`
2. 主 profile 路径
3. 兼容回退路径

规则如下：

- `schema_version` 是必填项
- 当前只支持 `schema_version = 1`
- 必填字段：
  - `schema_version`
  - `profile_name`
  - `repo_root`
  - `memory_root`
  - `backup_root`
- 不支持的 schema version 要 fail closed
- 缺必填字段要 fail closed
- 非法或非绝对路径形态要 fail closed
- 缺少必需 workspace 文件要 fail closed

可参考公开样例 [examples/default.profile.json](examples/default.profile.json)。

## 示例 Workspace 布局

通用 workspace 布局和 standard workflow 见 [examples/workspace-layout.md](examples/workspace-layout.md)。

## 开发说明

这个仓库自身现在也按“开发就绪”仓库来组织：

- 预期运行在独立的 git repository 中
- Python 项目元数据位于 [pyproject.toml](pyproject.toml)
- 测试位于 [tests](tests)
- 公开示例位于 [examples](examples)

继续开发时建议从这里开始：

1. 先读本 README 和 [docs/workspace-suite-overview.md](docs/workspace-suite-overview.md)
2. 如有需要，用 `python -m pip install -e .` 做本地 editable install
3. 运行测试：`python -m unittest discover -s tests -v`
4. 查看 [examples/default.profile.json](examples/default.profile.json) 和 [examples/workspace-layout.md](examples/workspace-layout.md)

## 可选的外部 Skill 集成

如果你已经有本地 skill 环境，可以让一个外部 wrapper 转发到本仓库。但这是可选的高级集成方式，不是公共文档默认假设的入口。

例如，一个本地 wrapper 可能暴露这样的脚本：

```text
<skill_path>/scripts/bootstrap_project.py
```

这个 wrapper 应该转发到本仓库的 guarded bootstrap wrapper，而不是自己重新实现 bootstrap 逻辑。

## 安全规则

- 非空文件不能自动覆盖
- manual patch 只报告，不自动应用
- `new` 不能 silent fallback 到 `legacy`
- `shadow` 不允许真实写入
- validator 和 router 不能误变成 bootstrap
- 只要 profile 或 workspace 状态不足以安全继续，就必须 fail closed

## 切流后的观察点

当前项目处于 long-run observation 和 legacy deprecation-readiness assessment 阶段。

建议按 suite surface 观察这些字段：

- validator:
  - `status`
  - `profile_source`
  - `problems`
  - `warnings`
  - `return_code`
- router:
  - `status`
  - `matched_project_slug`
  - `candidate_projects`
  - `ambiguity_reason`
  - `return_code`
- bootstrap:
  - `status`
  - `project_index_result`
  - `manual_follow_up`
  - `manual_patch_output`
  - `project_index_status`
  - `bootstrap_log_status`
  - `return_code`

如果这些字段出现异常漂移，建议顺序是：

1. 先判断问题起点在 profile loading、validator、router 还是 bootstrap
2. 只有怀疑 bootstrap 语义有问题时，再用 `--mode shadow`
3. 只有需要显式 bootstrap 回退或隔离时，才用 `--mode legacy`

## Deprecation Readiness

`legacy` 仍然保留为显式应急回退路径。

当前目标不是立刻删除它，而是判断它是否可以进入正式的弃用准备窗口。简化理解如下：

- 必须先完成一个长期观察窗口
- 只有真实 operator 样本才计入窗口
- bootstrap execute-path 证据至少要有 3 条且不能都来自相同输入
- 如果 `legacy` 仍在真实 incident 中解决问题，就继续保留
- 如果窗口完整且 `legacy` 没有真实依赖，就进入弃用准备
- 如果证据仍然偏薄或混杂，就继续积累证据

完整的 Phase 14 exit criteria 见 [docs/workspace-suite-overview.md](docs/workspace-suite-overview.md)。

## Operational Classification

先把 suite 问题归到下面几类之一：

- profile/config issues
- validator issues
- router issues
- bootstrap issues

更细的分类和 response playbooks 见 [docs/workspace-suite-overview.md](docs/workspace-suite-overview.md)。

## 架构一览

- `profile_loader`
  读取并校验 workspace profile。
- `workspace-validator`
  在 bootstrap 或 routing 前做 readiness check。
- `bridge`
  把运行时输入映射到 bootstrap request model。
- `planner`
  决定“做什么”。
- `executor`
  决定“怎么执行已经规划好的动作”。
- `workspace-router`
  基于 `PROJECT_INDEX.md` 解析 existing-project 的 repo 与 memory surface。
- `live_wrapper`
  集中处理 `new`、`legacy`、`shadow` 的 mode 选择。

关键边界是：

- planner 决定做什么
- executor 决定怎么做

## 如何用 Agents 驱动这个项目

任何 coding agent 或 automation agent，只要具备下面三类能力，就可以按同样流程驱动本项目：

- 仓库访问能力
- 文件读取或编辑能力
- shell / 命令执行能力

如果 agent 没有本地仓库访问或命令执行能力，它仍可以帮助阅读和起草，但不能安全地完成完整部署或运行流程。

### 工具无关的通用流程

1. 打开仓库并先读 `README.md` 或 `README.zh-CN.md`。
2. 先读这些关键入口文件：
   - `src/portable_project_bootstrap/live_wrapper.py`
   - `src/portable_project_bootstrap/profile_loader.py`
   - `src/portable_project_bootstrap/validator.py`
   - `src/portable_project_bootstrap/router.py`
3. 检查目标 profile 是否存在。
4. 先运行 `workspace-validator`。
5. 做 bootstrap 时先跑 `--dry-run`。
6. 检查关键状态字段。
7. 只有确认安全时，再决定是否 `--execute`。
8. 如需 bootstrap 对照验证，用 `--mode shadow`。
9. 只有显式回退时才用 `--mode legacy`。

### 通用 Agent Prompt 模板

```text
Open the repository at <repo_root>/portable-project-bootstrap.
Read README.md plus these files first:
- src/portable_project_bootstrap/live_wrapper.py
- src/portable_project_bootstrap/profile_loader.py
- src/portable_project_bootstrap/validator.py
- src/portable_project_bootstrap/router.py

Check whether the profile exists at <workspace_root>/.agent-memory/machine-profiles/<profile_name>.json.
Run workspace validation first.
Then run a bootstrap dry-run through the repo-local entrypoint.
Report these fields exactly:
- status
- project_index_result
- manual_follow_up or manual_patch_output
- project_index_status
- bootstrap_log_status
- return code

If the dry-run looks unsafe or inconsistent, do not execute.
If needed, rerun with --mode shadow for compare-only validation.
If rollback is required, rerun explicitly with --mode legacy.
For an existing project entry task, use workspace-router instead of bootstrap.
```

### 让 Agent 做 Dry-Run 的示例

```text
Use python -m portable_project_bootstrap.
Run workspace validation first for workspace-root <workspace_root> and profile-name <profile_name>.
Then run a dry-run for a brand-new project with:
- project-name "<project_name>"
- project-slug <project_slug>
- project-summary "<project_summary>"
- tech-stack Python and Markdown

Do not execute writes. Report:
- status
- project_index_result
- manual_follow_up or manual_patch_output
- project_index_status
- bootstrap_log_status
- return code
```

### 让 Agent 做显式 Legacy 回退的示例

```text
Use the same bootstrap input with --mode legacy.
Treat this as rollback or containment, not as the default path.
After the run, report:
- why rollback was used
- status
- project_index_result
- manual patch signals
- return code
- whether further shadow comparison is needed
```

### 让 Agent 做 Shadow 对照的示例

```text
Use the same bootstrap input with --mode shadow.
Do not allow writes.
Report:
- shadow_matched
- any shadow_differences
- status
- project_index_result
- manual_patch_output
- return code
If shadow_differences appear, stop and recommend whether to stay on new, investigate further, or temporarily use legacy.
```

### Codex / Codex CLI

```text
Open <repo_root>/portable-project-bootstrap, read README.md and the wrapper/profile-loader/validator/router files, confirm the target profile exists, run workspace validation, then run a bootstrap dry-run and report status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code.
If anything looks suspicious, use --mode shadow before suggesting --execute.
If rollback is needed, use --mode legacy explicitly and explain why.
For existing-project entry, use workspace-router and report repo path, memory path, and read-first files.
```

### Claude Code

```text
In this repo, first read README.md plus src/portable_project_bootstrap/live_wrapper.py, profile_loader.py, validator.py, and router.py.
Check the target profile under <workspace_root>/.agent-memory/machine-profiles/<profile_name>.json.
Run workspace validation first.
Run a bootstrap dry-run only after validation passes.
Do not execute writes until you summarize status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code.
Use --mode shadow for compare-only checks if needed.
Use --mode legacy only for explicit rollback.
Use workspace-router for existing-project entry work.
```

### Cursor

```text
Read README.md and the wrapper, validator, and router entrypoints first.
Verify the profile file exists.
Run workspace-validator in the integrated terminal.
Run a bootstrap dry-run only after validation succeeds.
Summarize status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code before proposing execute.
If results are unclear, run --mode shadow.
If rollback is needed, run --mode legacy and explain the trigger.
For existing projects, run workspace-router instead of guessing paths.
```

### OpenClaw 或其他通用 Agent

对于 OpenClaw 或其他通用 agent，只有在它已经具备下面这些能力时，才适合按同样流程驱动：

- 本地 repo 访问
- 文件读取或编辑
- 本地命令执行

```text
Use the local repository at <repo_root>/portable-project-bootstrap.
Read README.md first, verify the profile exists, run workspace validation, run a bootstrap dry-run, and report status, project_index_result, manual patch signals, project_index_status, bootstrap_log_status, and return code.
If the dry-run looks suspicious, switch to --mode shadow.
If rollback is required, use --mode legacy explicitly and record why.
For existing-project entry, use workspace-router and report the resolved repo path, memory path, and read-first files.
```

## 示例与公开材料

- [examples/default.profile.json](examples/default.profile.json)
  带占位路径的公开 profile 样例。
- [examples/workspace-layout.md](examples/workspace-layout.md)
  通用 workspace 布局与流程说明。
- [examples/README.md](examples/README.md)
  如何把示例改成自己的环境。
- [CONTRIBUTING.md](CONTRIBUTING.md)
  最小贡献说明。
- [LICENSE](LICENSE)
  本仓库的开源许可证。

## 当前状态

- bootstrap 默认 mode 是 `new`
- `legacy` 仍保留为显式应急回退路径
- `shadow` 仍是 compare-only
- `workspace-validator` 和 `workspace-router` 已经纳入 suite
- 当前项目处于 long-run observation 和 legacy deprecation-readiness assessment 阶段
