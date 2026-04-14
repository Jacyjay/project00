function isHeicLikeType(type = '') {
  const normalizedType = type.toLowerCase()
  return normalizedType.includes('heic') || normalizedType.includes('heif')
}

export function isHeicLikeFile(file) {
  if (!file) return false
  return isHeicLikeType(file.type) || /\.(heic|heif)$/i.test(file.name || '')
}

export function canPreviewFileInBrowser(file) {
  return !isHeicLikeFile(file)
}

export async function normalizeImageFileForBrowser(file) {
  if (!isHeicLikeFile(file)) return file

  const { default: heic2any } = await import('heic2any')
  const converted = await heic2any({
    blob: file,
    toType: 'image/jpeg',
    quality: 0.92,
    multiple: false,
  })

  const convertedBlob = Array.isArray(converted) ? converted[0] : converted
  if (!(convertedBlob instanceof Blob)) {
    throw new Error('HEIC conversion failed')
  }

  const baseName = (file.name || 'photo').replace(/\.(heic|heif)$/i, '')
  return new File([convertedBlob], `${baseName || 'photo'}.jpg`, {
    type: 'image/jpeg',
    lastModified: file.lastModified || Date.now(),
  })
}

/**
 * Compress an image file using Canvas, resizing to at most maxDimension on the
 * longest side and re-encoding as JPEG at the given quality.
 * Modern browsers automatically apply EXIF orientation when drawing to canvas.
 * Falls back to the original file on any error.
 */
export async function compressImageFile(file, { maxDimension = 800, quality = 0.55 } = {}) {
  // GIF compression would break animation; leave it as-is
  if (file.type === 'image/gif') return file

  return new Promise((resolve) => {
    const img = new Image()
    const objectUrl = URL.createObjectURL(file)

    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      let { width, height } = img

      if (width > maxDimension || height > maxDimension) {
        if (width >= height) {
          height = Math.round((height * maxDimension) / width)
          width = maxDimension
        } else {
          width = Math.round((width * maxDimension) / height)
          height = maxDimension
        }
      }

      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d').drawImage(img, 0, 0, width, height)

      canvas.toBlob(
        (blob) => {
          if (!blob) {
            resolve(file)
            return
          }
          const baseName = (file.name || 'photo').replace(/\.[^.]+$/, '')
          resolve(
            new File([blob], `${baseName}.jpg`, {
              type: 'image/jpeg',
              lastModified: file.lastModified || Date.now(),
            }),
          )
        },
        'image/jpeg',
        quality,
      )
    }

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      resolve(file) // fallback to original
    }

    img.src = objectUrl
  })
}

export function formatImagePreparationError(error) {
  const rawMessage = String(error?.message || error || '').trim()
  if (!rawMessage) return '照片处理失败'

  if (rawMessage.includes('ERR_LIBHEIF')) {
    return '当前浏览器无法本地解析这张 HEIC 照片'
  }
  if (rawMessage.includes('ERR_CANVAS')) {
    return '当前浏览器无法生成这张照片的本地预览'
  }
  if (rawMessage.includes('ERR_USER')) {
    return '照片格式处理失败'
  }

  return rawMessage
}
