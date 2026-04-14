import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMapStore = defineStore('map', () => {
  // true = 显示详情(照片), false = 显示坐标(小点)
  const storedMode = localStorage.getItem('map-detail-mode')
  const mapDetailMode = ref(storedMode === null ? true : storedMode === 'true')
  const pendingPlaceSearchQuery = ref('')
  const pendingPlaceSearchNonce = ref(0)

  function setMapDetailMode(value) {
    mapDetailMode.value = value
    localStorage.setItem('map-detail-mode', String(value))
  }

  function toggleMapDetailMode() {
    setMapDetailMode(!mapDetailMode.value)
  }

  function requestPlaceSearch(query) {
    pendingPlaceSearchQuery.value = query.trim()
    pendingPlaceSearchNonce.value += 1
  }

  function clearPlaceSearchRequest() {
    pendingPlaceSearchQuery.value = ''
  }

  return {
    mapDetailMode,
    setMapDetailMode,
    toggleMapDetailMode,
    pendingPlaceSearchQuery,
    pendingPlaceSearchNonce,
    requestPlaceSearch,
    clearPlaceSearchRequest,
  }
})
