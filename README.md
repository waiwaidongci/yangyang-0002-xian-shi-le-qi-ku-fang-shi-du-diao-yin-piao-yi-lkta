# 弦室 · 乐器库房湿度与调音漂移

林间艺术中心弦乐组用同琴同时窗的湿度与调音记录调查音高漂移，并在处置复测达标后恢复借用。

## 业务场景

林间艺术中心是模拟客户，弦乐组有 14 人，库管和调音师轮班维护三列琴柜。湿度计读数原先记在各柜纸簿上，调音仪另记音分，借用台再用白板更新琴的状态。纸簿与调音记录容易错配，个别高漂移掩藏在多琴汇总里，白板恢复借用常漏记复测证据。弦室把输入统一为同琴同窗的两种记录、后台相关分析和处置签审，排练领队从借用台账查看当前可借琴。

| 模块 | 页面 | 业务动作 |
|---|---|---|
| 借用 | 借用台账 | 按柜位对照参考 A 音、最后实测漂移和借用状态 |
| 测量 | 测量簿 | 分别录入湿度计和调音仪；同琴同窗补齐配对 |
| 统计 | 漂移分析 | 提交后台 Spearman 计算、读配对散点和历史统计 |
| 维护 | 停借与复测 | 登记停借处置、完成调湿、提交恢复借用签审 |

| 角色 | 邮箱 | 权限 |
|---|---|---|
| 库管 operator | `operator@demo.local` | 录入来源数据、发起分析、登记停借和处置完成 |
| 复核 reviewer | `reviewer@demo.local` | 发起分析、依据复测数据签审恢复借用 |
| 查阅 viewer | `viewer@demo.local` | 读借用状态、配对数据、计算历史和处置证据 |

演示密码均为 `Demo2026!`。

## 演示工作日

1. 2026-11-23 08:00 调音师记录北柜 B2 的 VA-017 云杉中提琴偏高 31 音分。该时窗已有相对湿度 61%。
2. 08:15 库管核对《北柜-B2-调音记录》。11-22 15:00 的 54% 湿度读数缺调音记录，测量簿将该窗标为待补录。
3. 08:30 发起 VA-017 的相关计算。演示数据含 6 个完整配对、1 个缺测窗，两个湿度读数均为 47%，其平均秩为 2.5。
4. 08:45 为 VA-017 登记柜内调湿并停借。南柜 C3 的 VN-041 只有 +1 音分漂移，达不到停借门槛。
5. 09:15 库管登记调湿完成。
6. 10:00 补录 VA-017 的 51% RH 和 +2 音分。
7. 14:00 VA-017 补录 50% RH。即使 VN-041 的同一时刻已有音分记录，VA-017 仍缺调音数据，签审被拒。
8. 14:15 库管补齐 VA-017 14:00 的 −4 音分。复核员完成签审，记录锁定这两个复测窗，台账恢复可借。

## 统计口径

每次后台任务取同琴最新 12 个观测窗，仅在湿度和调音均有数据时保留该窗。以平均秩替代并列名次，计算两列名次值的 Pearson 相关系数。少于 5 对时标为样本不足；常量列无法计算时标为测值秩恒定。任务保存本次实际配对点、配对数、缺测数与系数，便于重复核对。初始 VA-017 结果为约 0.986，无随机性。

处置以最近调音读数达到绝对值 15 音分触发；登记完成后取同琴最近两个时窗，要求间隔至少 4 小时、湿度均在 45%–55%，音高漂移均在 ±5 音分内。阈值为演示客户的工作规则。

## 本地运行

```sh
cp .env.example .env
docker compose up --build -d --wait
docker compose exec -T backend python -m scripts.seed_demo
```

前端 http://localhost:18281 ，API 文档 http://localhost:19281/docs ，PostgreSQL 宿主端口 17781。重跑种子可查看数据计数。清理容器与卷使用 `docker compose down -v --remove-orphans`。

本地调试可以保留 Compose 的 DB 和 Redis，配置 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET` 后，在 `backend/` 安装 `requirements.txt`，运行 `uvicorn app:app --reload --port 8000` 与 `python worker.py`。前端使用 Nginx 静态托管，通过同源 `/api/` 访问后端。

| 服务 | 技术 | 职责 |
|---|---|---|
| frontend | Nginx、HTML/CSS/JS | 登录、测量簿、散点、处置工作台 |
| backend | Python、FastAPI、psycopg | 角色校验、测量写入、业务约束、审计 |
| worker | Python | 处理持久化的相关分析任务 |
| db | PostgreSQL | 业务状态、原始记录和计算快照 |
| redis | Redis | 登录限流和运行协作 |

端口通过 `FRONTEND_PORT`、`BACKEND_PORT`、`DB_PORT` 配置。容器环境配置参见 `.env.example` 和 `docker-compose.yml`。 `SEED_DEMO` 控制启动种子，`DEMO_PASSWORD` 可配置演示密码。

- `backend/schema.sql` 定义领域关系和约束，`domain.py` 管理 HTTP 输入和授权。
- `backend/drift.py` 负责配对计算，`treatment.py` 负责停借与恢复。
- `backend/seed_strings.py` 定义业务样本，`scripts/seed_demo.py` 提供幂等入口。
- `frontend/studio.js` 渲染台账、测量、散点与处置，复用会话和请求模块 `base.js`。

共享枚举：角色及后台任务状态见 `backend/core.py` 和 `frontend/base.js`；借用状态、处置状态和处置方式见 `backend/schema.sql`、`backend/domain.py` 及 `frontend/studio.js`；分析状态见 `backend/schema.sql`、`backend/drift.py` 及 `frontend/studio.js`。

MIT License，见 `LICENSE`。

## 候补、平衡柜与领还签证

- **借琴候补**登记排练时间、琴号和组名。复核时检查最新音分、停借状态和重叠时窗；前一借琴单交回前，冲突申请保留候补。
- **平衡柜**按 45%–55% RH 与可用柜位安排调湿处置。柜位保留入柜读数，原处置复测通过后由复核员退柜。
- **领还签证**记录琴桥、琴盒和两次实测音分。领出须三项合格；归还漂移变化超过 8 音分或发现外观异常时隔离。复验结果独立留痕，合格后解除隔离。

`backend/migrations/` 的三个增量脚本由 API 启动加载，已有账簿和原处置记录保留。源记录和扩展签证各自留档，见业务追踪表。
