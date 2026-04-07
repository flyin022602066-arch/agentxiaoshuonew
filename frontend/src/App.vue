<template>
  <div id="app">
    <el-container class="app-shell">
      <el-header class="app-header">
        <h1>📚 多 Agent 协作小说系统</h1>
        <span class="version">v1.0.0</span>
      </el-header>
      
      <el-container class="content-shell">
        <el-aside width="200px" class="app-sidebar">
          <el-menu
            :default-active="activeMenu"
            background-color="#304156"
            text-color="#bfcbd9"
            active-text-color="#409EFF"
            @select="handleMenuSelect"
          >
            <el-menu-item index="dashboard">
              <el-icon><HomeFilled /></el-icon>
              <span>首页</span>
            </el-menu-item>
            <el-menu-item index="auto">
              <el-icon><MagicStick /></el-icon>
              <span>全自动创作</span>
            </el-menu-item>
            <el-menu-item index="library">
              <el-icon><FolderOpened /></el-icon>
              <span>小说仓库</span>
            </el-menu-item>
            <el-menu-item index="config">
              <el-icon><Setting /></el-icon>
              <span>项目配置</span>
            </el-menu-item>
            <el-menu-item index="monitor">
              <el-icon><Monitor /></el-icon>
              <span>Agent 监控</span>
            </el-menu-item>
            <el-menu-item index="writing">
              <el-icon><Edit /></el-icon>
              <span>写作面板</span>
            </el-menu-item>
            <el-menu-item index="learning">
              <el-icon><Reading /></el-icon>
              <span>学习中心</span>
            </el-menu-item>
            <el-menu-item index="schools">
              <el-icon><Grid /></el-icon>
              <span>派系库</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        
        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HomeFilled, MagicStick, Setting, Monitor, Edit, Reading, Grid, FolderOpened } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.name || 'dashboard')

const handleMenuSelect = (index) => {
  router.push({ name: index })
}
</script>

<style>
html,
body,
#app {
  margin: 0;
  width: 100%;
  min-width: 100vw;
  min-height: 100vh;
}

body {
  overflow-y: auto;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif;
  height: 100vh;
}

.app-shell {
  width: 100%;
  min-width: 100vw;
  min-height: 100vh;
}

.content-shell {
  flex: 1;
  width: 100%;
  min-width: 0;
  overflow: auto;
}

.app-header {
  background-color: #304156;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  width: 100%;
  box-sizing: border-box;
}

.app-header h1 {
  margin: 0;
  font-size: 24px;
}

.version {
  font-size: 14px;
  opacity: 0.8;
}

.app-sidebar {
  background-color: #304156;
  color: white;
  overflow-y: auto;
  flex-shrink: 0;
}

.app-main {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
}

.app-sidebar .el-menu {
  border-right: none;
  width: 100%;
}
</style>
