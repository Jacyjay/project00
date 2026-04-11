const TAIWAN_CITY_VARIANTS = new Set([
  '台北市',
  '新北市',
  '桃园市',
  '桃園市',
  '台中市',
  '台南市',
  '高雄市',
  '基隆市',
  '新竹市',
  '嘉义市',
  '嘉義市',
  '新竹县',
  '新竹縣',
  '苗栗县',
  '苗栗縣',
  '彰化县',
  '彰化縣',
  '彰化市',
  '南投县',
  '南投縣',
  '云林县',
  '雲林縣',
  '嘉义县',
  '嘉義縣',
  '屏东县',
  '屏東縣',
  '宜兰县',
  '宜蘭縣',
  '花莲县',
  '花蓮縣',
  '台东县',
  '台東縣',
  '澎湖县',
  '澎湖縣',
  '金门县',
  '金門縣',
  '连江县',
  '連江縣',
])

function withTaiwanProvincePrefix(value) {
  const text = value.trim()
  if (!text) return ''
  if (text === '台湾省') return '台湾省'
  if (text.startsWith('台湾省')) return text
  if (TAIWAN_CITY_VARIANTS.has(text)) return `台湾省${text}`
  return text
}

function normalizeRegionText(value) {
  if (typeof value !== 'string') return ''
  let text = value.trim()
  if (!text) return ''

  // Convert common Traditional Chinese characters used in Taiwan place names
  text = text.replace(/臺/g, '台').replace(/灣/g, '湾').replace(/區/g, '区').replace(/縣/g, '县')

  if (/^(中国)?台(湾|灣)(省)?$/.test(text) || /^(中华民国|中華民國)$/.test(text)) {
    return '台湾省'
  }

  if (/^(中国)?台(湾|灣)(省)?/.test(text)) {
    return withTaiwanProvincePrefix(text.replace(/^(中国)?台(湾|灣)(省)?/, '台湾省'))
  }

  if (/^(中华民国|中華民國)/.test(text)) {
    return withTaiwanProvincePrefix(text.replace(/^(中华民国|中華民國)/, '台湾省'))
  }

  text = text.replace(/\bTaiwan(?:,?\s*China)?\b/gi, '台湾省')
  text = text.replace(/\bRepublic of China\b/gi, '台湾省')

  // Handle Nominatim-style addresses where 台湾 appears at the end:
  // e.g. "潭子区, 台中市, 台湾" → "台湾省台中市潭子区"
  const twSuffix = text.match(/,?\s*台(湾|灣)(省)?$/)
  if (twSuffix) {
    const inner = text.slice(0, twSuffix.index).trim().replace(/,$/, '').trim()
    if (inner) {
      const parts = inner.split(',').map((p) => p.trim()).filter(Boolean)
      parts.reverse() // Nominatim is small→large; reverse to Chinese large→small
      return `台湾省${parts.join('')}`
    }
    return '台湾省'
  }

  return withTaiwanProvincePrefix(text)
}

export function normalizeCityName(value) {
  const normalized = normalizeRegionText(value)
  if (!normalized) return ''
  return normalized
}

export function normalizeAddressName(value) {
  return normalizeRegionText(value)
}
