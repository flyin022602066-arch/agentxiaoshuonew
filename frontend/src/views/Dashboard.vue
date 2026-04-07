<template>
  <el-card>
    <h2>欢迎使用多 Agent 协作小说系统</h2>
    <p>这是一个会学习、会进化、越写越好的 AI 小说创作系统。</p>
    
    <h3>核心特性</h3>
    <ul>
      <li>🤖 7 大 Agent 协作：主编、剧情、人物、写手、对话、审核、学习</li>
      <li>🧠 三层记忆系统：短期 + 中期 + 长期记忆</li>
      <li>📖 四层学习记忆：原始→模式→技巧→风格</li>
      <li>🏛️ 派系分类系统：按类型/文笔/节奏分类，支持融合</li>
      <li>🔌 可配置 LLM：火山/阿里云/eggfans 完全可配置</li>
      <li>💾 本地保存：自动保存 + Git 版本控制</li>
    </ul>
    
    <h3>快速开始</h3>
    <ol>
      <li>前往 <strong>项目配置</strong> 页面配置 LLM API 密钥</li>
      <li>在 <strong>学习中心</strong> 上传喜欢的小说进行学习</li>
      <li>在 <strong>派系库</strong> 选择或融合写作风格</li>
      <li>在 <strong>写作面板</strong> 开始创作你的小说</li>
    </ol>
    
    <el-divider />
    
    <h3>系统状态</h3>
    <el-row :gutter="20">
      <el-col :span="6">
        <div class="status-statistic">
          <div class="status-statistic__label">API 状态</div>
          <div class="status-statistic__value">
            <el-tag :type="apiStatusType">{{ apiStatus }}</el-tag>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <el-statistic title="Agent 数量" :value="7" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="项目数量" :value="0" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="章节总数" :value="0" />
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const apiStatus = ref('检查中...')

const apiStatusType = computed(() => {
  if (apiStatus.value === '正常') return 'success'
  if (apiStatus.value === '检查中...') return 'info'
  return 'danger'
})

const checkApiStatus = async () => {
  try {
    const response = await fetch('/api/ping')
    if (response.ok) {
      apiStatus.value = '正常'
    } else {
      apiStatus.value = '异常'
    }
  } catch (error) {
    apiStatus.value = '不可达'
  }
}

onMounted(() => {
  checkApiStatus()
})
</script>

<style scoped>
ul, ol {
  line-height: 2;
}

h3 {
  margin-top: 20px;
  margin-bottom: 10px;
}

.status-statistic__label {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin-bottom: 8px;
}

.status-statistic__value {
  min-height: 32px;
  display: flex;
  align-items: center;
}
</style>
