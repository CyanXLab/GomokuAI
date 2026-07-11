<template>
  <div id="app" style="height: 100%">
    <drawer :show.sync="drawerOpen" show-mode="overlay" placement="right" :drawer-style="{
      'background-color': 'var(--color-bg-elevated)',
      width: 'min(75%, 600px)',
      height: '100%',
    }">
      <!-- drawer content -->
      <div ref="drawer" slot="drawer" class="drawer">
        <div style="padding: 10px">
          <p v-for="(msg, index) in messages" :key="index">{{ msg }}<br /></p>
        </div>
      </div>

      <view-box ref="viewBox" :body-padding-top="showHeader ? '48px' : '0'" body-padding-bottom="0">
        <!-- header content with nav icons -->
        <x-header v-if="showHeader" slot="header" class="header-bar" :left-options="{ showBack: false }"
          :right-options="{ showMore: false }">
          {{ $t('appName') }}
          <div slot="right" class="header-nav">
            <a class="nav-icon" :class="{active: route.path === '/'}" @click="$router.push('/')" :title="$t('tabbar.game')">
              <i class="fa fa-th-large" aria-hidden="true"></i>
            </a>
            <a class="nav-icon" :class="{active: route.path === '/settings'}" @click="$router.push('/settings')" :title="$t('tabbar.settings')">
              <i class="fa fa-cog" aria-hidden="true"></i>
            </a>
            <a class="nav-icon" :class="{active: route.path === '/about'}" @click="$router.push('/about')" :title="$t('tabbar.about')">
              <i class="fa fa-info-circle" aria-hidden="true"></i>
            </a>
            <a v-if="route.path === '/'" class="nav-icon" @click="showMessages" :title="'Messages'">
              <i class="fa fa-list" aria-hidden="true"></i>
            </a>
          </div>
        </x-header>

        <!-- main content -->
        <keep-alive>
          <router-view class="router-view"></router-view>
        </keep-alive>
      </view-box>
    </drawer>
  </div>
</template>

<script>
import { ViewBox, XHeader, Tabbar, TabbarItem, Drawer } from 'vux'
import { mapState, mapMutations, mapActions } from 'vuex'
import { register } from 'register-service-worker'
import { initTheme } from '@/theme.js'

function canShowInstallPrompt() {
  const installData = JSON.parse(localStorage.getItem('pwaInstallPromptData'));
  if (!installData)
    return true;

  const { lastShown, count } = installData;
  const today = new Date().toDateString();

  if (count >= 5) {
    // 已经显示超过5次
    return false;
  }

  if (lastShown === today) {
    // 今天已经显示过
    return false;
  }

  return true;
}

function updateInstallPromptData() {
  const today = new Date().toDateString();
  const installData = JSON.parse(localStorage.getItem('pwaInstallPromptData')) || { lastShown: null, count: 0 };

  if (installData.lastShown !== today) {
    installData.lastShown = today;
    installData.count += 1;
    localStorage.setItem('pwaInstallPromptData', JSON.stringify(installData));
  }
}

export default {
  components: {
    ViewBox,
    XHeader,
    Tabbar,
    TabbarItem,
    Drawer,
  },
  data: function () {
    return {
      showHeader: true,
      drawerOpen: false,
    }
  },
  computed: {
    ...mapState('settings', ['language', 'theme', 'configIndex']),
    ...mapState('ai', ['messages']),
    route() {
      return this.$route
    },
  },
  methods: {
    ...mapMutations('settings', ['setValue']),
    ...mapActions('ai', ['initEngine']),
    ...mapActions('settings', ['readCookies']),
    ...mapActions(['getBrowserCapabilities']),
    showMessages: function () {
      this.drawerOpen = !this.drawerOpen
    },
  },
  watch: {
    language(newValue) {
      this.$i18n.locale = newValue
    },
    theme(newValue) {
      const { setTheme } = require('@/theme.js')
      setTheme(newValue)
    },
  },
  created() {
    initTheme()
    this.getBrowserCapabilities()
    this.readCookies()
    if (!this.language) {
      this.setValue({ key: 'language', value: this.$i18n.locale })
    } else {
      this.$i18n.locale = this.language
    }
  },
  mounted() {
    const _this = this
    // 加入 i18n 版本的 $vux.alert, $vux.confirm
    this.$vux.alert.show_i18n = function (options) {
      options.buttonText = _this.$t('common.ok')
      _this.$vux.alert.show(options)
    }
    this.$vux.confirm.show_i18n = function (options) {
      options.confirmText = _this.$t('common.confirm')
      options.cancelText = _this.$t('common.cancel')
      _this.$vux.confirm.show(options)
    }
    this.$vux.confirm.prompt_i18n = function (value, options) {
      options.confirmText = _this.$t('common.confirm')
      options.cancelText = _this.$t('common.cancel')
      _this.$vux.confirm.prompt(value, options)
    }

    window.onresize = function () {
      // 定义窗口大小变更通知事件
      _this.$store.commit('setScreenSize', {
        width: document.documentElement.clientWidth,
        height: document.documentElement.clientHeight,
      })
    }

    const loadEngine = (loadFullEngine) => {
      _this.initEngine(loadFullEngine).catch((err) => {
        console.error('Engine loading error:', err)
      })
    }

    // 直接加载引擎,不注册 Service Worker (SW 导致弹窗/白屏问题)
    loadEngine(true)
  },
}
</script>

<style lang="less">
@import '~vux/src/styles/index.less';
@import './styles/modern.less';

html,
body {
  height: 100%;
  width: 100%;
  overflow-x: hidden;
  overflow-y: hidden;
  margin: 0px;
}

body {
  background-color: @background-color;
  // 文字均不可选
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -khtml-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.header-bar {
  width: 100%;
  position: fixed !important;
  top: 0;
  z-index: 100;
}

.tabber-icon-active {
  fill: @tabber-icon-active-color;
}

.drawer {
  height: 100%;
  -webkit-user-select: text;
  -khtml-user-select: text;
  -moz-user-select: text;
  -ms-user-select: text;
  user-select: text;
  word-wrap: break-word;
  overflow-y: auto;
}

.vux-pop-out-enter-active,
.vux-pop-out-leave-active,
.vux-pop-in-enter-active,
.vux-pop-in-leave-active {
  will-change: transform;
  transition: all 500ms;
  height: 100%;
  top: 46px;
  position: absolute;
  backface-visibility: hidden;
  perspective: 1000;
}

.vux-pop-out-enter {
  opacity: 0;
  transform: translate3d(-100%, 0, 0);
}

.vux-pop-out-leave-active {
  opacity: 0;
  transform: translate3d(100%, 0, 0);
}

.vux-pop-in-enter {
  opacity: 0;
  transform: translate3d(100%, 0, 0);
}

.vux-pop-in-leave-active {
  opacity: 0;
  transform: translate3d(-100%, 0, 0);
}
</style>
