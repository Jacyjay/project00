# 成就系统设计方案

## 一、实现可行性分析

### ✅ 完全可行

基于现有的项目架构，成就系统完全可以实现：

1. **数据基础充足**
   - 已有 `checkins` 表（打卡记录）
   - 已有 `users` 表（用户信息）
   - 可以通过 SQL 查询统计用户行为数据

2. **技术栈支持**
   - 后端：FastAPI + SQLAlchemy（异步）
   - 前端：Vue 3 + Element Plus
   - 已有类似功能参考（足迹报告、关注系统）

3. **UI 集成点明确**
   - 用户主页（ProfilePage.vue）已有完善的布局
   - 打卡详情页可展示成就徽章
   - 可添加成就弹窗提示

## 二、成就系统架构设计

### 1. 数据库设计

#### 成就定义表（achievements）
```sql
CREATE TABLE achievements (
    id INTEGER PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,  -- 成就代码（如 first_trip）
    name VARCHAR(100) NOT NULL,         -- 成就名称
    description TEXT,                   -- 成就描述
    icon VARCHAR(10),                   -- emoji 图标
    category VARCHAR(50),               -- 分类（探索、社交、时间等）
    rarity VARCHAR(20),                 -- 稀有度（common/rare/epic/legendary）
    sort_order INTEGER DEFAULT 0,       -- 排序
    created_at TIMESTAMP
);
```

#### 用户成就表（user_achievements）
```sql
CREATE TABLE user_achievements (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    achievement_code VARCHAR(50) NOT NULL,
    unlocked_at TIMESTAMP NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE,    -- 是否对他人可见
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, achievement_code)
);
```

### 2. 成就类型设计

#### 探索类成就
- 🗺️ **首次出游** - 完成第一次打卡
- 🌍 **城市探索者** - 打卡 5 个不同城市
- 🌏 **旅行达人** - 打卡 20 个不同城市
- 🏔️ **省份收集家** - 打卡 10 个不同省份
- 🌟 **足迹大师** - 打卡 100 次
- 📍 **地标猎人** - 打卡 50 个不同地点

#### 时间类成就
- 🌙 **夜游达人** - 晚上 10 点后打卡 10 次
- 🌅 **早起鸟** - 早上 6 点前打卡 10 次
- 📅 **连续打卡王** - 连续 7 天打卡
- 🎉 **周末旅行家** - 周末打卡 20 次

#### 社交类成就
- 💬 **评论达人** - 发表 50 条评论
- ❤️ **点赞狂魔** - 点赞 100 次
- 👥 **社交达人** - 获得 50 个粉丝
- 🔥 **人气王** - 单条打卡获得 50 个赞

#### 内容类成就
- 📝 **文案高手** - 发布 20 条带文案的打卡
- 📸 **摄影师** - 上传 100 张照片
- 🎬 **视频创作者** - 发布 10 条视频打卡
- ✨ **AI 助手** - 使用 AI 生成文案 20 次

#### 特殊成就
- 🎂 **周年纪念** - 注册满一年
- 🏆 **创始会员** - 前 100 名注册用户
- 💎 **完美主义者** - 所有打卡都是公开的
- 🌈 **多彩旅程** - 在春夏秋冬四季都有打卡

### 3. 成就检测逻辑

#### 触发时机
1. **打卡发布后** - 检测探索类、时间类成就
2. **社交互动后** - 检测社交类成就
3. **定时任务** - 每日检测连续打卡、周年纪念等

#### 检测流程
```python
async def check_achievements(user_id: int, trigger_type: str):
    """检测并解锁成就"""
    # 1. 获取用户已解锁的成就
    unlocked = await get_user_achievements(user_id)
    
    # 2. 获取待检测的成就规则
    rules = get_achievement_rules(trigger_type)
    
    # 3. 逐个检测
    newly_unlocked = []
    for rule in rules:
        if rule.code not in unlocked:
            if await rule.check(user_id):
                await unlock_achievement(user_id, rule.code)
                newly_unlocked.append(rule)
    
    return newly_unlocked
```

## 三、前端设计

### 1. 成就徽章组件

#### 徽章样式
```
┌─────────────────┐
│   🗺️ 首次出游   │  ← 已解锁（彩色）
└─────────────────┘

┌─────────────────┐
│   🌍 城市探索者  │  ← 未解锁（灰色）
│   进度: 3/5      │
└─────────────────┘
```

#### 稀有度配色
- **普通（Common）**: 灰色边框
- **稀有（Rare）**: 蓝色边框 + 微光效果
- **史诗（Epic）**: 紫色边框 + 闪光效果
- **传奇（Legendary）**: 金色边框 + 光晕效果

### 2. 用户主页集成

在 ProfilePage.vue 中添加成就展示区：

```vue
<div class="achievements-section glass-card">
  <div class="section-header">
    <h3>🏆 成就徽章</h3>
    <span class="achievement-count">{{ unlockedCount }}/{{ totalCount }}</span>
  </div>
  
  <div class="achievements-grid">
    <AchievementBadge
      v-for="achievement in displayedAchievements"
      :key="achievement.code"
      :achievement="achievement"
      :unlocked="achievement.unlocked"
    />
  </div>
  
  <button v-if="isOwnProfile" @click="openAchievementSettings">
    ⚙️ 管理成就可见性
  </button>
</div>
```

### 3. 成就解锁弹窗

当用户解锁新成就时，显示庆祝动画：

```vue
<transition name="achievement-unlock">
  <div v-if="showUnlockModal" class="unlock-modal">
    <div class="unlock-card">
      <div class="unlock-icon">🎉</div>
      <h2>成就解锁！</h2>
      <div class="achievement-badge-large">
        {{ newAchievement.icon }} {{ newAchievement.name }}
      </div>
      <p class="achievement-desc">{{ newAchievement.description }}</p>
      <button @click="closeUnlock">太棒了！</button>
    </div>
  </div>
</transition>
```

### 4. 成就管理页面

用户可以设置每个成就的可见性：

```vue
<div class="achievement-settings">
  <div v-for="achievement in userAchievements" class="setting-row">
    <div class="achievement-info">
      <span class="icon">{{ achievement.icon }}</span>
      <span class="name">{{ achievement.name }}</span>
    </div>
    <label class="visibility-toggle">
      <input
        type="checkbox"
        v-model="achievement.is_visible"
        @change="updateVisibility(achievement)"
      />
      <span>{{ achievement.is_visible ? '公开' : '私密' }}</span>
    </label>
  </div>
</div>
```

## 四、API 设计

### 后端路由

```python
# 获取所有成就定义
GET /api/achievements

# 获取用户成就
GET /api/users/{user_id}/achievements

# 更新成就可见性
PUT /api/users/me/achievements/{achievement_code}/visibility

# 获取成就进度（未解锁的成就显示进度）
GET /api/users/me/achievement-progress
```

### 响应示例

```json
{
  "achievements": [
    {
      "code": "first_trip",
      "name": "首次出游",
      "description": "完成第一次打卡",
      "icon": "🗺️",
      "category": "探索",
      "rarity": "common",
      "unlocked": true,
      "unlocked_at": "2026-03-15T10:30:00Z",
      "is_visible": true
    },
    {
      "code": "city_explorer",
      "name": "城市探索者",
      "description": "打卡 5 个不同城市",
      "icon": "🌍",
      "category": "探索",
      "rarity": "rare",
      "unlocked": false,
      "progress": {
        "current": 3,
        "target": 5
      }
    }
  ]
}
```

## 五、实现优先级

### Phase 1: MVP（最小可行产品）
1. 数据库表创建
2. 5-10 个基础成就（首次出游、城市探索者等）
3. 成就检测逻辑
4. 用户主页展示
5. 基础可见性设置

### Phase 2: 增强
1. 成就解锁弹窗动画
2. 更多成就类型（20-30 个）
3. 成就进度显示
4. 稀有度系统和特效

### Phase 3: 高级功能
1. 成就统计页面
2. 成就排行榜
3. 限时成就
4. 成就分享功能

## 六、技术难点与解决方案

### 1. 性能优化
- **问题**: 每次打卡都检测所有成就会影响性能
- **方案**: 
  - 按触发类型分组成就规则
  - 使用缓存存储已解锁成就
  - 异步检测，不阻塞打卡发布

### 2. 数据一致性
- **问题**: 用户数据变化后成就状态可能不一致
- **方案**:
  - 提供成就重新计算接口
  - 定时任务校验成就状态

### 3. 扩展性
- **问题**: 新增成就需要修改代码
- **方案**:
  - 成就规则配置化
  - 使用策略模式设计检测逻辑

## 七、奖章设计（纯 CSS + Emoji）

我可以直接用 CSS 和 Emoji 设计出精美的成就徽章，无需图片资源：

### 徽章样式示例

```css
/* 基础徽章 */
.achievement-badge {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  position: relative;
  transition: all 0.3s ease;
}

/* 未解锁 */
.achievement-badge.locked {
  background: linear-gradient(135deg, #e0e0e0, #bdbdbd);
  filter: grayscale(100%);
  opacity: 0.5;
}

/* 普通 */
.achievement-badge.common {
  background: linear-gradient(135deg, #90caf9, #64b5f6);
  box-shadow: 0 4px 12px rgba(100, 181, 246, 0.4);
}

/* 稀有 */
.achievement-badge.rare {
  background: linear-gradient(135deg, #ce93d8, #ba68c8);
  box-shadow: 0 4px 12px rgba(186, 104, 200, 0.4);
  animation: pulse-rare 2s infinite;
}

/* 史诗 */
.achievement-badge.epic {
  background: linear-gradient(135deg, #ffb74d, #ffa726);
  box-shadow: 0 4px 12px rgba(255, 167, 38, 0.6);
  animation: glow-epic 2s infinite;
}

/* 传奇 */
.achievement-badge.legendary {
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.8);
  animation: shine-legendary 3s infinite;
}

@keyframes pulse-rare {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes glow-epic {
  0%, 100% { box-shadow: 0 4px 12px rgba(255, 167, 38, 0.6); }
  50% { box-shadow: 0 6px 20px rgba(255, 167, 38, 0.9); }
}

@keyframes shine-legendary {
  0% { box-shadow: 0 6px 20px rgba(255, 215, 0, 0.8); }
  50% { box-shadow: 0 8px 30px rgba(255, 215, 0, 1); }
  100% { box-shadow: 0 6px 20px rgba(255, 215, 0, 0.8); }
}
```

## 八、总结

### ✅ 完全可以实现

1. **数据层**: 新增 2 张表即可
2. **业务层**: 成就检测逻辑清晰，可复用现有查询
3. **展示层**: 基于现有 UI 组件扩展
4. **视觉设计**: 纯 CSS + Emoji，无需设计师

### 🎯 推荐实施步骤

1. 先实现 Phase 1 MVP（5-10 个基础成就）
2. 验证用户反馈
3. 逐步添加更多成就和特效
4. 最后实现高级功能（排行榜等）

### 💡 额外建议

- 成就系统可以提高用户粘性和活跃度
- 建议先上线基础版本，根据数据迭代
- 可以结合运营活动推出限时成就
- 考虑添加成就分享到社交媒体功能

**我可以立即开始实现这个系统，你觉得这个方案如何？需要调整哪些部分？**
