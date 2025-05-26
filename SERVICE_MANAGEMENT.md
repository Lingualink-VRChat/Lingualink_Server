# Lingualink 服务管理 (开发阶段)

本文档提供在开发阶段管理 Lingualink FastAPI 应用的 systemd 服务的基本命令。

## 前提

确保 `lingualink.service` 文件已经：
1.  根据您的环境正确配置（特别是 `User` 和 `WorkingDirectory`）。
2.  被移动到 `/etc/systemd/system/lingualink.service`。
3.  `systemd` 已重新加载配置 (`sudo systemctl daemon-reload`)。

## 常用命令

所有命令通常需要 `sudo` 权限执行。

### 启动服务

```bash
sudo systemctl start lingualink.service
```

### 停止服务

```bash
sudo systemctl stop lingualink.service
```

### 重启服务

当您修改了代码并希望服务以新的代码运行时（注意：这不等同于 `uvicorn` 的 `--reload`，您需要确保服务配置中的 `ExecStart` 指向的是您期望运行的应用实例）：

```bash
sudo systemctl restart lingualink.service
```

### 查看服务状态

检查服务是否正在运行、上次活动时间、以及是否有错误信息。

```bash
sudo systemctl status lingualink.service
```
按 `q` 退出状态查看。

### 查看服务日志 (实时)

实时查看应用的输出日志（包括 `stdout` 和 `stderr`）。这对于调试非常有用。

```bash
sudo journalctl -u lingualink.service -f
```
按 `Ctrl+C` 停止查看日志。

### 查看全部服务日志

查看服务自启动以来所有的日志。

```bash
sudo journalctl -u lingualink.service
```
可以使用箭头键滚动，按 `q` 退出。

### 开机自启 (可选，生产环境推荐)

如果您希望服务在系统启动时自动运行：

```bash
sudo systemctl enable lingualink.service
```

### 禁止开机自启 (开发阶段可能更常用)

如果您不希望服务在系统启动时自动运行：

```bash
sudo systemctl disable lingualink.service
```

## 注意事项 (开发阶段)

*   **代码更新**: 如果您更新了应用代码，您需要**重启服务** (`sudo systemctl restart lingualink.service`) 才能让更改生效。`systemd` 本身不会像 `uvicorn --reload` 那样自动侦测代码变化。
*   **虚拟环境**: 服务配置 (`lingualink.service`) 中的 `ExecStart` 和 `Environment="PATH=..."` 已确保使用项目内的 `.venv` 虚拟环境。对虚拟环境的任何更改（如安装新包）后，可能需要重启服务。
*   **端口占用**: 确保端口 `5000` (或您在 `ExecStart` 中配置的端口) 没有被其他应用占用。 