# 第二账号 Codex CLI

这套目录只供第二账号的 CLI 使用，不会读取或覆盖默认的 `~/.codex`。

## 填入认证

用第二账号已有的完整认证缓存替换 `home/auth.json` 中的 `{}`。不要把认证内容粘贴到聊天、日志或 Git。

占位内容未被替换时，`run.sh` 会拒绝启动，避免 CLI 把空 JSON 误报为已登录。

填入后收紧权限：

```bash
chmod 600 /home/galbot/lizekai/RSI/codex-account-2/home/auth.json
```

## 验证和启动

```bash
/home/galbot/lizekai/RSI/codex-account-2/run.sh login status
/home/galbot/lizekai/RSI/codex-account-2/run.sh
```

启动脚本默认进入独立的 `workspace/`，因此不会与当前账号同时修改 RSI 主目录。需要测试某份代码时，先把该次测试所需文件放到这个目录。

## 从其他进程调用

不要调用裸的 `codex`；始终调用这个启动器。指定工作目录并执行非交互任务：

```bash
/home/galbot/lizekai/RSI/codex-account-2/run.sh \
  -C /home/galbot/lizekai/RSI/codex-account-2/workspace \
  exec --json "任务内容"
```

Python 父进程应把启动器作为可执行文件：

```python
import subprocess

subprocess.run(
    [
        "/home/galbot/lizekai/RSI/codex-account-2/run.sh",
        "-C",
        "/home/galbot/lizekai/RSI/codex-account-2/workspace",
        "exec",
        "--json",
        "任务内容",
    ],
    check=True,
)
```

启动器会固定第二账号的 `CODEX_HOME`，并清除可能覆盖认证来源的 `CODEX_ACCESS_TOKEN`、`CODEX_API_KEY`、`OPENAI_API_KEY` 和 `OPENAI_ADMIN_KEY`。

长任务应在 tmux 中运行，并将输出写入 `logs/`；不要在日志中输出 `auth.json`。
