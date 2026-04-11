<template>
  <div
    :class="['achievement-badge', rarity, { locked: !unlocked }]"
    :title="achievement.description"
    @click="$emit('click', achievement)"
  >
    <div class="badge-icon">{{ achievement.icon }}</div>
    <div class="badge-name">{{ achievement.name }}</div>
    <div class="badge-condition">{{ getConditionText() }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  achievement: {
    type: Object,
    required: true,
  },
  unlocked: {
    type: Boolean,
    default: false,
  },
  progress: {
    type: Object,
    default: null,
  },
})

defineEmits(['click'])

const rarity = computed(() => props.achievement.rarity || 'common')

function getConditionText() {
  if (props.unlocked) {
    return '已解锁'
  }

  // 根据成就代码返回解锁条件
  const conditions = {
    'first_trip': '打卡1次',
    'city_explorer': '打卡5城市',
    'travel_master': '打卡20城市',
    'checkin_milestone_10': '打卡10次',
    'checkin_milestone_50': '打卡50次',
    'night_owl': '夜间打卡10次',
    'early_bird': '早晨打卡10次',
    'social_butterfly': '获得50粉丝',
    'content_creator': '发布20条文案',
    'photographer': '上传50张照片',
  }

  return conditions[props.achievement.code] || '未解锁'
}
</script>

<style scoped>
.achievement-badge {
  width: 100px;
  height: 120px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  border: 2px solid transparent;
}

.badge-icon {
  font-size: 36px;
  transition: transform 0.3s ease;
}

.badge-name {
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  line-height: 1.3;
  color: var(--ink-900);
}

.badge-condition {
  font-size: 10px;
  color: var(--ink-400);
  font-weight: 500;
  text-align: center;
}

.achievement-badge.locked .badge-condition {
  color: var(--ink-400);
}

.achievement-badge:not(.locked) .badge-condition {
  color: var(--brand);
  font-weight: 600;
}

/* 未解锁状态 */
.achievement-badge.locked {
  background: linear-gradient(135deg, #e0e0e0, #bdbdbd);
  filter: grayscale(100%);
  opacity: 0.5;
  border-color: #ccc;
}

.achievement-badge.locked .badge-name {
  color: var(--ink-500);
}

/* 普通 */
.achievement-badge.common {
  background: linear-gradient(135deg, #90caf9, #64b5f6);
  box-shadow: 0 4px 12px rgba(100, 181, 246, 0.4);
  border-color: #64b5f6;
}

/* 稀有 */
.achievement-badge.rare {
  background: linear-gradient(135deg, #ce93d8, #ba68c8);
  box-shadow: 0 4px 12px rgba(186, 104, 200, 0.4);
  border-color: #ba68c8;
  animation: pulse-rare 2s infinite;
}

/* 史诗 */
.achievement-badge.epic {
  background: linear-gradient(135deg, #ffb74d, #ffa726);
  box-shadow: 0 4px 12px rgba(255, 167, 38, 0.6);
  border-color: #ffa726;
  animation: glow-epic 2s infinite;
}

/* 传奇 */
.achievement-badge.legendary {
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.8);
  border-color: #ffd700;
  animation: shine-legendary 3s infinite;
}

.achievement-badge:hover:not(.locked) {
  transform: translateY(-4px) scale(1.05);
}

.achievement-badge:hover:not(.locked) .badge-icon {
  transform: scale(1.1);
}

@keyframes pulse-rare {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
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
</style>
