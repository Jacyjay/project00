function normalizeRegionText(value) {
  if (typeof value !== 'string') return ''
  let text = value.trim()
  if (!text) return ''

  text = text.replace(/臺/g, '台')

  if (/^(中国)?台(湾|灣)(省)?$/.test(text) || /^(中华民国|中華民國)$/.test(text)) {
    return '中国台湾'
  }

  if (/^(中国)?台(湾|灣)(省)?/.test(text)) {
    return text.replace(/^(中国)?台(湾|灣)(省)?/, '中国台湾')
  }

  if (/^(中华民国|中華民國)/.test(text)) {
    return text.replace(/^(中华民国|中華民國)/, '中国台湾')
  }

  return text
}

export function normalizeCityName(value) {
  const normalized = normalizeRegionText(value)
  if (!normalized) return ''
  if (normalized.includes('中国台湾')) return '中国台湾'
  return normalized
}

export function normalizeAddressName(value) {
  return normalizeRegionText(value)
}

