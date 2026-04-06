# 拾光坐标

> 基于地图聚合的旅行打卡与分享平台

一款以高德地图为核心的旅行记录应用，让你用坐标留住每一段时光。在地图上打卡、发现热门城市、生成专属足迹报告，与旅行者社区互动分享。

---

## 功能特性

### 地图打卡
- **定位打卡** — 一键获取当前位置，快速留下足迹
- **选点打卡** — 在地图上任意选点，手动确认坐标
- **地点搜索打卡** — 搜索景点、餐厅、商圈后直接发起打卡
- 打卡支持上传照片（含 HEIC 格式自动转换）

### AI 智能辅助
- **AI 文案生成** — 基于城市、地点和照片，由豆包 AI 生成旅行文案（支持清新风、文艺风等多种风格）
- **城市 AI 简介** — 每个城市详情页自动生成 AI 城市介绍
- **专属足迹报告** — 统计打卡数据，由豆包 AI 生成个性化旅行总结报告

### 社区互动
- **广场** — 浏览所有用户的公开打卡，支持点赞与评论
- **城市热榜** — 实时展示打卡数量最多的热门城市
- **城市详情页** — 查看某城市下的所有公开打卡，支持按时间/热度排序
- **私信** — 与其他用户一对一私信交流

### 个人中心
- **我的足迹** — 个人足迹地图，统计打卡数、城市数、省份数
- **用户主页** — 展示个人打卡记录与足迹统计
- **下载中心** — 打卡记录导出

---

## 技术栈

### 前端
| 技术 | 版本 |
|------|------|
| Vue 3 | ^3.5 |
| Vue Router | ^4.6 |
| Pinia | ^3.0 |
| Element Plus | ^2.13 |
| 高德地图 JS API | ^1.0 |
| Vite | ^6.4 |

### 后端
| 技术 | 版本 |
|------|------|
| Python | 3.10+ |
| FastAPI | 0.115 |
| SQLAlchemy (async) | 2.0 |
| SQLite / aiosqlite | — |
| Uvicorn | 0.30 |
| Pillow | 10.4 |
| python-jose (JWT) | 3.3 |

### 外部服务
- **高德地图开放平台** — 地图渲染、POI 搜索、逆地理编码
- **火山方舟（豆包 AI）** — 文案生成、城市简介、足迹报告
- **163 邮箱 SMTP** — 注册验证邮件（可选）

---

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.10+

### 1. 克隆项目

```bash
git clone <repo-url>
cd project00
```

### 2. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
# 数据库（默认 SQLite，可替换为 PostgreSQL）
DATABASE_URL=sqlite+aiosqlite:///./travel_checkins.db

# JWT 密钥（生产环境请替换为随机强密码）
SECRET_KEY=your-super-secret-key-change-in-production

# 高德地图
AMAP_KEY=your_amap_key

# 豆包 AI（火山方舟）
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_ENDPOINT_ID=your_doubao_endpoint_id

# 邮件（可选，不填则禁用邮件验证）
MAIL_USERNAME=your@163.com
MAIL_PASSWORD=your_auth_code
MAIL_FROM=your@163.com

# CORS（生产环境填写前端域名）
BACKEND_CORS_ORIGINS=http://localhost:5173
```

前端在 `frontend/` 目录下创建 `.env.local`（按需配置高德地图 Key）：

```env
VITE_AMAP_KEY=your_amap_key
```

### 3. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端启动后访问 `http://localhost:8000/docs` 查看 API 文档。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`。

---

## 项目结构

```
project00/
├── backend/
│   ├── app/
│   │   ├── api/          # 路由层（auth, checkins, users, social, ai_caption...）
│   │   ├── core/         # 配置、依赖注入、JWT
│   │   ├── crud/         # 数据库 CRUD 操作
│   │   ├── db/           # 数据库会话与 Base
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   └── services/     # 业务逻辑（AI 文案、足迹报告、城市简介）
│   ├── alembic/          # 数据库迁移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # Axios 接口封装
│   │   ├── components/   # 公共组件（AppHeader, CheckinCard...）
│   │   ├── views/        # 页面（HomePage, MyFootprintPage, ProfilePage...）
│   │   ├── stores/       # Pinia 状态管理
│   │   └── router/       # 路由配置
│   └── package.json
└── README.md
```

---

## API 概览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | `/api/auth` | 注册、登录、JWT |
| 打卡 | `/api/checkins` | 创建、查询、删除打卡 |
| 地点 | `/api/places` | 地点管理 |
| 用户 | `/api/users` | 用户信息、关注 |
| 社交 | `/api/social` | 点赞、评论 |
| 私信 | `/api/messages` | 私信会话 |
| AI 文案 | `/api/ai-caption` | 豆包 AI 文案生成 |
| 足迹报告 | `/api/footprint-report` | 个人足迹 AI 报告 |
| 上传 | `/api/uploads` | 图片上传 |

---

## License

MIT
