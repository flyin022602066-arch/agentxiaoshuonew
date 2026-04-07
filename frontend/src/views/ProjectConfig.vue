<template>
  <div class="project-config">
    <h2>⚙️ 项目配置</h2>
    
    <!-- LLM 配置 -->
    <el-card class="config-section">
      <template #header>
        <div class="card-header">
          <span>LLM 提供商配置</span>
          <el-button type="primary" @click="saveConfig" :loading="saving">保存配置</el-button>
        </div>
      </template>
      
      <!-- 快速切换模型 -->
      <el-alert type="info" :closable="false" style="margin-bottom: 20px">
        <template #title>🔄 快速切换模型</template>
        <div style="margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
          <el-select v-model="quickSwitchModel" placeholder="选择已保存的模型" style="width: 250px" @change="handleQuickSwitch">
            <el-option
              v-for="p in savedProviders"
              :key="p.name"
              :label="`${p.name} (${p.model || '未设置模型'})`"
              :value="p.name"
            />
          </el-select>
          <el-tag v-if="config.default_provider" type="success">当前默认：{{ config.default_provider }}</el-tag>
          <span style="color: #909399; font-size: 13px;">选择后点击"保存配置"生效</span>
        </div>
      </el-alert>

      <!-- 默认提供商 -->
      <el-form :model="config" label-width="120px">
        <el-form-item label="默认提供商">
          <el-select v-model="config.default_provider" placeholder="选择默认提供商" filterable allow-create default-first-option>
            <el-option
              v-for="name in Object.keys(config.providers)"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        
        <!-- 提供商列表 -->
        <div v-for="(provider, name) in config.providers" :key="name" class="provider-config">
          <el-divider>{{ name }}</el-divider>
          
          <el-form-item label="API 格式">
            <el-select v-model="provider.api_format">
              <el-option label="OpenAI 兼容" value="openai" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="API Key">
            <el-input
              v-model="provider.api_key"
              type="password"
              :placeholder="provider.has_api_key ? `已保存：${provider.masked_api_key || '***'}` : '填写你的 API Key'"
              show-password
              clearable
            >
              <template #prefix>
                <span v-if="provider.has_api_key" style="color: #67c23a">
                  ✓ 已保存
                </span>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item v-if="provider.has_api_key">
            <el-checkbox v-model="provider.clear_api_key"><span>清除已保存的 API Key</span></el-checkbox>
          </el-form-item>
          
          <el-form-item label="Base URL">
            <el-input v-model="provider.base_url" placeholder="https://api.example.com" />
          </el-form-item>
          
          <el-form-item label="模型名称">
            <el-input v-model="provider.model" placeholder="模型名称" />
          </el-form-item>
          
          <el-form-item>
            <el-button @click="testConnection(name)" :loading="testing === name">
              {{ testing === name ? '测试中...' : '测试连接' }}
            </el-button>
            
            <el-tag v-if="testResults[name]" :type="testResults[name].status === 'success' ? 'success' : 'danger'">
              {{ testResults[name].message }}
            </el-tag>
          </el-form-item>
        </div>
        
        <!-- 添加提供商 -->
        <el-form-item>
          <el-button @click="addProvider" icon="Plus">添加提供商</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 项目设置 -->
    <el-card class="config-section">
      <template #header>项目设置</template>
      
      <el-form :model="projectSettings" label-width="120px">
        <el-form-item label="项目名称">
          <el-input v-model="projectSettings.project_name" />
        </el-form-item>
        
        <el-form-item label="项目路径">
          <el-input v-model="projectSettings.project_path" />
        </el-form-item>
        
        <el-form-item label="自动保存">
          <el-switch v-model="projectSettings.auto_commit" />
        </el-form-item>
        
        <el-form-item label="备份间隔">
          <el-input-number v-model="projectSettings.backup_interval" :min="1" :max="24" /> 小时
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 系统信息 -->
    <el-card class="config-section">
      <template #header>系统信息</template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="API 状态">
          <el-tag :type="apiStatus === '正常' ? 'success' : 'danger'">
            {{ apiStatus }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="系统版本">v1.0.0</el-descriptions-item>
        <el-descriptions-item label="已配置提供商">
          {{ Object.keys(config.providers).length }}
        </el-descriptions-item>
        <el-descriptions-item label="最后更新">
          {{ lastUpdated }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { apiClient } from '@/api/client'

const saving = ref(false)
const testing = ref(null)
const apiStatus = ref('检查中...')
const lastUpdated = ref('')

const config = reactive({
  default_provider: '',
  providers: {}
})

const projectSettings = reactive({
  project_name: '我的小说',
  project_path: './projects/我的小说',
  auto_commit: true,
  backup_interval: 24
})

const testResults = ref({})
const quickSwitchModel = ref('')

// 从后端加载的提供商列表（用于快速切换）
const savedProviders = ref([])

const loadConfig = async () => {
  try {
    const result = await apiClient.config.get()
    console.log('加载配置结果:', result)
    
    if (result.data) {
      const configData = result.data
      
      // 清空现有提供商，完全从后端加载
      config.providers = {}
      
      // 获取默认提供商
      if (configData.default_provider) {
        config.default_provider = configData.default_provider
        quickSwitchModel.value = configData.default_provider
        console.log('设置默认提供商:', config.default_provider)
      }
      
      // 加载所有提供商配置
      if (configData.providers) {
        console.log('加载提供商配置:', Object.keys(configData.providers))
        
        Object.keys(configData.providers).forEach(key => {
          const providerData = configData.providers[key]
          config.providers[key] = {
            api_format: providerData.api_format || 'openai',
            api_key: '',
            has_api_key: providerData.has_api_key || false,
            masked_api_key: providerData.masked_api_key || '',
            clear_api_key: false,
            base_url: providerData.base_url || '',
            endpoint: providerData.endpoint || '/v1/chat/completions',
            model: providerData.model || '',
            enabled: providerData.enabled !== undefined ? providerData.enabled : true,
            auth_type: providerData.auth_type || 'bearer'
          }
          console.log(`加载提供商 ${key}:`, config.providers[key])
        })
        
        // 更新快速切换列表
        savedProviders.value = Object.keys(configData.providers).map(key => ({
          name: key,
          model: configData.providers[key].model || '',
          base_url: configData.providers[key].base_url || ''
        }))
      }
      
      ElMessage.success(`配置已加载，默认提供商：${config.default_provider || '未设置'}`)
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.warning('加载配置失败，将使用空配置')
  }
}

const handleQuickSwitch = (modelName) => {
  if (modelName && config.providers[modelName]) {
    config.default_provider = modelName
    ElMessage.info(`已选择 ${modelName} 为默认提供商，请点击"保存配置"生效`)
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    // 构建要保存的配置数据
    const configToSave = {
      default_provider: config.default_provider,
      providers: {}
    }
    
    // 保存所有提供商的配置
    Object.keys(config.providers).forEach(key => {
      const provider = config.providers[key]
      configToSave.providers[key] = {
        api_format: provider.api_format,
        api_key: provider.api_key || '',
        has_api_key: provider.has_api_key || false,
        masked_api_key: provider.masked_api_key || '',
        clear_api_key: provider.clear_api_key === true,
        base_url: provider.base_url,
        model: provider.model,
        enabled: provider.enabled !== undefined ? provider.enabled : true
      }
    })
    
    console.log('保存配置:', JSON.stringify(configToSave, null, 2))
    
    // 保存到后端
    await apiClient.config.update(configToSave)
    await loadConfig()
    ElMessage.success('配置保存成功，下次访问会自动加载')
    lastUpdated.value = new Date().toLocaleString()
  } catch (error) {
    console.error('保存配置失败:', error)
    const errorMsg = error.response?.data?.error?.message || error.message || '未知错误'
    ElMessage.error('配置保存失败：' + errorMsg)
  } finally {
    saving.value = false
  }
}

const testConnection = async (provider) => {
  testing.value = provider
  try {
    const result = await apiClient.config.testLLM(provider)
    testResults.value[provider] = result.data
    ElMessage.success(result.data.message)
  } catch (error) {
    testResults.value[provider] = {
      status: 'error',
      message: error.message
    }
    ElMessage.error('连接测试失败：' + error.message)
  } finally {
    testing.value = null
  }
}

const addProvider = () => {
  const name = `provider_${Date.now()}`
  config.providers[name] = {
    api_format: 'openai',
    api_key: '',
    has_api_key: false,
    masked_api_key: '',
    clear_api_key: false,
    base_url: '',
    model: '',
    enabled: true
  }
}

const checkApiStatus = async () => {
  try {
    const result = await apiClient.health.live()
    apiStatus.value = '正常'
  } catch (error) {
    apiStatus.value = '异常'
  }
}

onMounted(() => {
  loadConfig()
  checkApiStatus()
})
</script>

<style scoped>
.project-config {
  width: 100%;
  max-width: none;
}

.config-section {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.provider-config {
  margin-top: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>
