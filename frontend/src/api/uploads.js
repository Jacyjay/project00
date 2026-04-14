import api from './index'

export const normalizeImageUpload = (file) => {
  const formData = new FormData()
  formData.append('file', file)

  return api.post('/api/uploads/normalize-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
    timeout: 60000,
  })
}
