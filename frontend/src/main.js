import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  ElConfigProvider,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElSwitch,
  ElUpload,
} from 'element-plus'
import 'element-plus/es/components/config-provider/style/css'
import 'element-plus/es/components/date-picker/style/css'
import 'element-plus/es/components/dialog/style/css'
import 'element-plus/es/components/form/style/css'
import 'element-plus/es/components/form-item/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/switch/style/css'
import 'element-plus/es/components/upload/style/css'
import './assets/styles/main.css'

import App from './App.vue'
import { preloadAmap } from './lib/amap'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
;[ElConfigProvider, ElDatePicker, ElDialog, ElForm, ElFormItem, ElInput, ElSwitch, ElUpload].forEach((component) => {
  app.component(component.name, component)
})

preloadAmap()
app.mount('#app')
