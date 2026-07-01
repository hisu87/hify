import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index'
import VueVirtualScroller from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

import './index.css'

const app = createApp(App)
app.use(router)
app.use(VueVirtualScroller)
app.mount('#app')
