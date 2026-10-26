---
name: github-escaped-file-push
description: Safely push code files containing escape-sensitive content to GitHub via MCP. Use when the user asks to push or update files that may contain real tabs, backslashes, or multiline string literals to a GitHub repo. Do not use for plain text markdown or small config files with no escape-sensitive content.
---

# GitHub 转义敏感字符安全推送

## 问题

GitHub MCP 的 `push_files`（批量推送）有 JSON 转义 bug：content 里的 `\t`、`\n`、`\\` 等会被双重转义。例如 Python 三引号字符串里的真实 tab 会变成文本 `\` + `t` 两个字符，导致：

- `python -c 'print("\\t".replace("\\\\t", "\\t"))'` 输出的是字面 `\t` 而不是缩进
- PowerShell here-string 里的反斜杠路径变成错误的转义序列
- bash heredoc 里的 tab 缩进全部丢失

## 解法

**一律用 `create_or_update_file` 单文件推送，不要用 `push_files`。**

`create_or_update_file` 对每个文件独立构造 JSON，MCP 内部正确处理转义，不会双重编码。

## 推送流程

### 1. 获取目标文件 SHA

```
run_mcp(
  server_name="mcp_plugin_github_github",
  tool_name="get_file_contents",
  args={"owner": "...", "repo": "...", "path": "..."}
)
```

从响应里提取 `"sha": "..."` 字段。如果仓库是新的（文件还不存在），跳过这步。

### 2. 组装 content

- 源文件用本地 Read 工具读取（UTF-8）
- content 直接粘贴 Read 输出的完整正文，不要 paraphrase 或压缩
- 关注正文里的真实 tab、反斜杠、`\uXXXX`、heredoc 标记——这些不能丢

### 3. 推送

```
run_mcp(
  server_name="mcp_plugin_github_github",
  tool_name="create_or_update_file",
  args={
    "owner": "qigedashen",
    "repo": "some-repo",
    "branch": "main",
    "path": "scripts/patch_ofgui.py",
    "sha": "<from step 1>",
    "message": "fix: re-upload with correct escape sequences",
    "content": "<verbatim content from Read>"
  }
)
```

### 4. 处理 409 冲突

并行推送多个文件时，如果某个返回：

```
409 is at <new_sha> but expected <old_sha>
```

说明同一次有别的推送改了仓库。重取 SHA（回到 step 1），用新 SHA 重试。

### 5. 验证（敏感文件必做）

push 完后立即 `get_file_contents` 拉回来核对：

- Python 文件：搜 `\t` 看是 JSON 转义的 tab（正确）还是 `\\t` 文本（错误）
- 关键三引号字符串：HELPER / OLD_A / OLD_C 等锚点必须含真实 tab 缩进
- PowerShell：反斜杠路径 `\\` 不能变成 `\`

## 敏感文件清单

以下类型的文件**必须**用 `create_or_update_file`，不能用 `push_files`：

| 类型 | 为什么敏感 |
|---|---|
| `*.py`（含三引号多行字符串） | `HELPER = """...\t..."""` 里的真实 tab |
| `*.sh` / `*.bash`（heredoc） | `cat <<'EOF'\n\t...` 里的 tab 缩进 |
| `*.ps1`（PowerShell here-string） | 反斜杠路径 `D:\\tools\\ofgui` |
| `*.sql`（含 `\n` 换行占位） | `INSERT INTO VALUES ('line1\nline2')` |
| `*.json`（含 `\\` 转义反斜杠） | `"path": "C:\\\\Users"` |
| `*.proto` / `*.thrift`（字符串字面量） | 同上 |

`*.md`、`*.yaml`、`*.toml`、小型 `*.json`（不含转义反斜杠）可以用 `push_files`。

## 检查清单（push 前过一遍）

- [ ] 源文件已 Read，确认有真实 tab / `\\` / `\uXXXX`
- [ ] 目标 SHA 已通过 `get_file_contents` 获取
- [ ] content 是 **Read 输出的完整正文**，不是改写/压缩版
- [ ] commit message 说明"escape fix / re-upload"意图
- [ ] 敏感文件 push 后立即拉回验证

## 反模式（不要这样做）

❌ **不要用 `push_files` 推 Python / shell 脚本** — 已证实双重转义
❌ **不要先 base64 编码再让 GitHub MCP 解码** — MCP 不自动处理，反而丢字节
❌ **不要压缩内容长度** — paraphrase 会丢注释、docstring、关键空行
❌ **不要忽略 409 冲突直接重试旧 SHA** — 冲突会持续存在
