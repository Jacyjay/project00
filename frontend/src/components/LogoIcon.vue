<template>
  <svg
    :width="size"
    :height="size * 1.2"
    viewBox="0 0 40 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    :style="{ display: 'block' }"
    aria-hidden="true"
  >
    <defs>
      <!-- Pin gradient: top bright gold → mid amber → bottom deep brown -->
      <linearGradient :id="uid('pin')" x1="20" y1="2" x2="20" y2="46" gradientUnits="userSpaceOnUse">
        <stop offset="0%"   stop-color="#FDE68A"/>
        <stop offset="45%"  stop-color="#F59E0B"/>
        <stop offset="100%" stop-color="#92400E"/>
      </linearGradient>
      <!-- Inner circle radial: warm ivory center -->
      <radialGradient :id="uid('inner')" cx="50%" cy="42%" r="55%">
        <stop offset="0%"   stop-color="#FFFBEB"/>
        <stop offset="100%" stop-color="#FEF3C7"/>
      </radialGradient>
      <!-- Soft drop shadow -->
      <filter :id="uid('shadow')" x="-30%" y="-10%" width="160%" height="140%">
        <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#92400E" flood-opacity="0.25"/>
      </filter>
    </defs>

    <!-- Ground shadow ellipse -->
    <ellipse cx="20" cy="46.5" rx="5" ry="1.5" fill="rgba(0,0,0,0.12)"/>

    <!-- Pin body -->
    <path
      :d="`M20 2C11.163 2 4 9.163 4 18C4 29 12 39.5 20 46C28 39.5 36 29 36 18C36 9.163 28.837 2 20 2Z`"
      :fill="`url(#${uid('pin')})`"
      :filter="`url(#${uid('shadow')})`"
    />

    <!-- Subtle pin highlight (top-left sheen) -->
    <path
      d="M20 3.5C13.1 3.5 7.5 9.1 7.5 16C7.5 17.5 7.8 18.9 8.3 20.2C9.4 13.2 14.2 8 20 7C23.2 7 26 8.3 28 10.4C25.7 6.3 23 3.5 20 3.5Z"
      fill="white"
      opacity="0.18"
    />

    <!-- Inner white circle -->
    <circle cx="20" cy="18" r="10.5" :fill="`url(#${uid('inner')})`"/>

    <!-- === Compass cross (坐标 coordinates) ===
         4 cardinal arms: bold, deep color -->
    <!-- North -->
    <path d="M20 8.5 L21.1 15.5 L20 16.5 L18.9 15.5 Z" fill="#B45309"/>
    <!-- South -->
    <path d="M20 27.5 L21.1 20.5 L20 19.5 L18.9 20.5 Z" fill="#B45309"/>
    <!-- West -->
    <path d="M10.5 18 L17.5 16.9 L18.5 18 L17.5 19.1 Z" fill="#B45309"/>
    <!-- East -->
    <path d="M29.5 18 L22.5 16.9 L21.5 18 L22.5 19.1 Z" fill="#B45309"/>

    <!-- === Light rays (拾光 gathering light) ===
         4 diagonal shorter rays, softer amber -->
    <!-- NW -->
    <path d="M12.8 10.8 L17.0 15.0 L16.0 16.0 L11.8 11.8 Z" fill="#F59E0B" opacity="0.75"/>
    <!-- SE -->
    <path d="M27.2 25.2 L23.0 21.0 L24.0 20.0 L28.2 24.2 Z" fill="#F59E0B" opacity="0.75"/>
    <!-- NE -->
    <path d="M27.2 10.8 L23.0 15.0 L24.0 16.0 L28.2 11.8 Z" fill="#F59E0B" opacity="0.75"/>
    <!-- SW -->
    <path d="M12.8 25.2 L17.0 21.0 L16.0 20.0 L11.8 24.2 Z" fill="#F59E0B" opacity="0.75"/>

    <!-- Center ring -->
    <circle cx="20" cy="18" r="3.2" fill="#D97706"/>
    <!-- Center bright core -->
    <circle cx="20" cy="18" r="1.5" fill="#FFFBEB"/>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: Number,
    default: 28
  }
})

// Generate unique IDs to avoid gradient/filter conflicts when multiple icons appear
let _counter = Math.random().toString(36).slice(2, 6)
const uid = (name) => `sgc-${name}-${_counter}`
</script>
