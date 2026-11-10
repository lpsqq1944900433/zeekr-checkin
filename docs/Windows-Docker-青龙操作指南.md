# Windows Docker 青龙：极氪签到本机部署

本机已部署完成，面板地址：<http://127.0.0.1:5700>。以下命令使用 **PowerShell**，不是 CMD。

## 1. 当前部署结果

- 容器名称：`qinglong`。
- 使用你已经下载、打好标签的镜像：`qinglong:latest`。本次检查实际青龙版本为 **2.17.11**，容器内 Node.js 为 **20.15.1**；镜像标签 `latest` 不代表镜像一定是最近发布的版本。
- 调度时区：`Asia/Shanghai`，即北京时间。
- 登录账号为 `admin`，随机生成的密码保存在项目的 `docker/qinglong/data/panel-login.txt`，没有写入本文或 Git。
- 六条任务已启用，使用当前本地 `qinglong/` 中的脚本，不需要安装 npm 依赖。
- Token 的唯一来源是原文件 `configs/极氪本人token.txt`。每次运行重新读取，不需要在面板「环境变量」中再复制一份。

首次实测于 **2026-11-10 22:48（北京时间）**：Token 鉴权成功、今日已签到、上报 22223 步成功；阅读文章和每周点赞已完成；查询时没有待领取奖励。减碳任务仍显示待完成，不能据此声称所有 App 任务都已完成。

## 2. 文件和容器怎样对应

项目根目录：`E:\dev\github\zeekr-checkin`。

| Windows 文件或目录 | 容器内位置 | 用途 |
|---|---|---|
| `docker\qinglong\data` | `/ql/data` | 可写；青龙数据库、定时任务、登录配置、日志等 |
| `configs` | `/zeekr/configs` | 只读；包含你原来的 Token 文件 |
| `qinglong` | `/zeekr/entries` | 只读；项目原有的六个独立任务脚本 |
| `docker\qinglong\scripts` | `/ql/data/scripts/zeekr-local` | 只读；读取 Token 后启动原脚本的运行入口 |

这里用的是 **bind mount（宿主机目录映射）**。容器里的数据实际上写在上表对应的 Windows 文件夹里。删除或重建容器后，保留这些文件夹即可保留配置；仅保存镜像不能保留配置。

映射的是整个 `configs` 文件夹，因此在 Windows 编辑器中保存或替换 `极氪本人token.txt` 后，下次任务会读取新文件。容器只读表示程序不能通过映射修改 Windows 配置，不影响你在 Windows 中编辑。

`.gitignore` 已排除原 Token 文件和整个 `docker/qinglong/data/`，避免将凭据、数据库和日志提交到仓库。

## 3. 本次部署使用的命令

先进入项目目录：

```powershell
Set-Location E:\dev\github\zeekr-checkin
```

你之前已完成镜像下载和打标签。重新搭建时，若本机没有该镜像，可使用原命令：

```powershell
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/whyour/qinglong:latest
docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/whyour/qinglong:latest qinglong:latest
```

创建数据目录，检查 Compose 配置，再启动容器：

```powershell
New-Item -ItemType Directory -Force -Path .\docker\qinglong\data
docker compose config --quiet
docker compose up -d
```

`docker-compose.yml` 描述镜像、端口、时区、重启策略和文件映射。`-d` 表示后台运行。`pull_policy: never` 表示使用本机镜像，避免启动时意外拉取别的镜像。

初始化面板，并通过面板 API 创建六条任务：

```powershell
python .\docker\qinglong\manage.py install
```

这个管理脚本只用 Python 标准库。首次初始化时生成管理员密码，随后通过 API 创建任务；重复执行会保留已有任务，包括你在面板改过的时间和启停状态，不会重复添加。它适配本次镜像中的青龙 API；将来跨版本升级后需要重新验证。

打开面板和本机登录信息：

```powershell
Start-Process 'http://127.0.0.1:5700'
notepad .\docker\qinglong\data\panel-login.txt
```

若以后在面板改了密码，以新密码为准；`panel-login.txt` 是首次部署的记录，不会自动同步。

端口绑定到 `127.0.0.1`，本机可访问；当前没有配置局域网或公网访问。

## 4. 六条定时任务

| 任务 | 北京时间 | cron | 原始入口 |
|---|---|---|---|
| 凌晨场，完整流程 | 00:01 | `1 0 * * *` | `zeekr_0001_all.js` |
| 凌晨补领 | 00:10 | `10 0 * * *` | `zeekr_0010_claim.js` |
| 早间场，完整流程 | 08:10 | `10 8 * * *` | `zeekr_0810_all.js` |
| 早间补领 | 08:20 | `20 8 * * *` | `zeekr_0820_claim.js` |
| 晚间场，完整流程 | 21:30 | `30 21 * * *` | `zeekr_2130_all.js` |
| 晚间补领 | 21:40 | `40 21 * * *` | `zeekr_2140_claim.js` |

cron 的五列依次是「分、时、日、月、星期」。例如 `30 21 * * *` 表示每天 21:30。

面板里的命令以晚间场为例：

```text
task zeekr-local/run.js -- zeekr_2130_all.js
```

`task` 是青龙的任务执行器，负责记录日志和任务状态；`--` 后面是传给运行入口的脚本名称。入口读取原 Token 文件，再启动 `/zeekr/entries/` 下对应的原脚本。三条补领仍然只执行领取。

可以在面板「定时任务」里单独修改时间。当前使用本地目录映射，无需额外添加 Git 仓库订阅；再次添加同一项目的六条订阅任务会导致重复执行。

## 5. 更换 Token

只编辑原文件：

```powershell
notepad .\configs\极氪本人token.txt
```

保存一个完整 Token，可使用 `Bearer <实际JWT>` 或裸 JWT；不要在同一文件中保留两个 Token。运行入口不会执行文件里的任何命令，只提取唯一的 JWT。

检查容器能否读取，不发起极氪请求，也不显示 Token：

```powershell
docker exec qinglong node /ql/data/scripts/zeekr-local/run.js --check
```

文件保存后下一次任务即生效，**无需重建或重启容器**。检查通过仅说明文件格式和 JWT 声明到期时间可用，服务器是否接受以实际任务日志为准。

## 6. 查看状态、手动运行和日志

查看容器和六条任务：

```powershell
docker compose ps
python .\docker\qinglong\manage.py status
docker exec qinglong crontab -l
docker exec qinglong date
```

手动运行一次晚间完整流程，实际执行签到、步数上报、任务和领取：

```powershell
python .\docker\qinglong\manage.py run zeekr_2130_all.js
```

只运行补领：

```powershell
python .\docker\qinglong\manage.py run zeekr_2140_claim.js
```

这两个命令通过 API 提交后台运行。打开面板「定时任务 → 对应任务 → 日志」查看结果。日志也保存在 Windows 的 `docker\qinglong\data\log\` 中，文件夹名称包含任务 ID。

容器启动日志和任务业务日志是两类日志。下面这个命令用于排查面板启动问题：

```powershell
docker compose logs --tail 80 qinglong
```

目前没有配置额外的手机推送渠道，业务结果以任务日志为准。

## 7. 重启、停止、重建与备份

```powershell
# 重启
docker compose restart

# 停止；后续可用 docker compose up -d 再启动
docker compose stop

# 重建容器；保留映射的 Windows 数据
docker compose up -d --force-recreate
```

本次已实际重建容器，确认六条任务、登录配置和首次运行日志仍在；再次运行 `install` 也没有重复添加任务。

`restart: unless-stopped` 让 Docker 引擎恢复时自动启动未被手动停止的容器。电脑关机、休眠或 Docker Desktop 未运行时，任务不会执行；需要日常自动签到，请让 Windows 和 Docker Desktop 保持运行，并按需在 Docker Desktop 中开启登录后启动。

备份时先停止容器，避免复制正在写入的数据库。以下将数据和原 Token 文件一起备份到项目外的新文件夹：

```powershell
Set-Location E:\dev\github\zeekr-checkin
$backupDir = Join-Path 'E:\dev\backups' ('zeekr-qinglong-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $backupDir
docker compose stop
try {
    Copy-Item -LiteralPath .\docker\qinglong\data -Destination (Join-Path $backupDir 'data') -Recurse
    Copy-Item -LiteralPath .\configs\极氪本人token.txt -Destination $backupDir
}
finally {
    docker compose up -d
}
```

备份包含你的登录密码和 Token，请保存在本人可控的位置。恢复时停止容器，将备份的 `data` 放回 `docker\qinglong\data`，Token 放回原路径，再运行 `docker compose up -d`。项目源码及 `docker-compose.yml` 也需要保留。

## 8. 参考

- [本项目常规青龙安装说明](../configs/qinglong.md)：面向仓库订阅部署，与本机文件映射方案不同。
- [青龙官方项目](https://github.com/whyour/qinglong)：官方容器示例同样将运行数据挂载到 `/ql/data`。
