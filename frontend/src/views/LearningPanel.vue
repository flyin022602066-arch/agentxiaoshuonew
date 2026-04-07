<template>
  <div class="learning-panel">
    <h2>📚 学习中心</h2>
    
    <el-row :gutter="20">
      <!-- 上传作品分析 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>上传作品分析</span>
              <el-button type="primary" @click="analyzeWork" :loading="analyzing">
                {{ analyzing ? '分析中...' : '开始分析' }}
              </el-button>
            </div>
          </template>
          
          <el-form label-width="80px">
            <el-form-item label="作者">
              <el-input v-model="uploadForm.author" placeholder="例如：金庸" />
            </el-form-item>
            
            <el-form-item label="作品名">
              <el-input v-model="uploadForm.title" placeholder="例如：天龙八部" />
            </el-form-item>
            
            <el-form-item label="小说内容">
              <el-input
                v-model="uploadForm.text"
                type="textarea"
                :rows="15"
                placeholder="粘贴小说内容，支持长文本（系统会自动分块处理）"
              />
            </el-form-item>
            
            <el-form-item>
              <el-alert
                title="分析说明"
                type="info"
                :closable="false"
                show-icon
              >
                <p>系统会自动分析作品的：</p>
                <ul>
                  <li>叙事风格（视角、节奏、结构）</li>
                  <li>描写风格（密度、手法、感官）</li>
                  <li>对话风格（比例、特点、潜台词）</li>
                  <li>情感风格（强度、表达方式）</li>
                </ul>
                <p>并提取可复用的写作模式和技巧。</p>
              </el-alert>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 已分析作品列表 -->
      <el-col :span="12">
        <el-card>
          <template #header>已分析作品</template>
          
          <el-table :data="analyzedWorks" style="width: 100%">
            <el-table-column prop="author" label="作者" width="80" />
            <el-table-column prop="title" label="作品" width="150" />
            <el-table-column prop="analyzed_at" label="分析时间" width="150" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="viewWorkDetail(row)">详情</el-button>
                <el-button size="small" type="primary" @click="applyStyle(row)">应用</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <!-- 学习报告 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>学习报告</span>
              <el-button @click="generateReport" :loading="reportLoading">刷新</el-button>
            </div>
          </template>
          
          <el-descriptions :column="2" border>
            <el-descriptions-item label="已分析作品">
              {{ report.analyzed_works }} 部
            </el-descriptions-item>
            <el-descriptions-item label="学习到的特征">
              {{ report.style_features_learned }} 个
            </el-descriptions-item>
            <el-descriptions-item label="已评估章节">
              {{ report.chapters_evaluated }} 章
            </el-descriptions-item>
            <el-descriptions-item label="平均评分">
              {{ report.average_score }}/10
            </el-descriptions-item>
          </el-descriptions>
          
          <el-divider />
          
          <h4>改进建议</h4>
          <ul>
            <li v-for="(rec, index) in report.recommendations" :key="index">
              {{ rec }}
            </li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 作品详情对话框 -->
    <el-dialog v-model="detailVisible" title="作品分析详情" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="作者">{{ selectedWork.author }}</el-descriptions-item>
        <el-descriptions-item label="作品">{{ selectedWork.title }}</el-descriptions-item>
        <el-descriptions-item label="分析时间" :span="2">
          {{ selectedWork.analyzed_at }}
        </el-descriptions-item>
      </el-descriptions>
      
      <el-divider>叙事风格</el-divider>
      <el-tag v-for="feature in selectedWork.analysis?.narrative_style" :key="feature">
        {{ feature }}
      </el-tag>
      
      <el-divider>描写风格</el-divider>
      <el-tag v-for="feature in selectedWork.analysis?.description_style" :key="feature">
        {{ feature }}
      </el-tag>
      
      <el-divider>对话风格</el-divider>
      <el-tag v-for="feature in selectedWork.analysis?.dialogue_style" :key="feature">
        {{ feature }}
      </el-tag>
      
      <el-divider>情感风格</el-divider>
      <el-tag v-for="feature in selectedWork.analysis?.emotional_style" :key="feature">
        {{ feature }}
      </el-tag>
      
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="applyStyle(selectedWork)">应用此风格</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { apiClient } from '@/api/client'

const analyzing = ref(false)
const reportLoading = ref(false)
const detailVisible = ref(false)

const uploadForm = reactive({
  author: '',
  title: '',
  text: ''
})

const analyzedWorks = ref([])

const selectedWork = ref({})

const report = reactive({
  analyzed_works: 0,
  style_features_learned: 0,
  chapters_evaluated: 0,
  average_score: 0,
  recommendations: []
})

const analyzeWork = async () => {
  if (!uploadForm.author || !uploadForm.title || !uploadForm.text) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  analyzing.value = true
  
  try {
    // 调用 API 分析作品
    const result = await apiClient.learning.analyze({
      author: uploadForm.author,
      title: uploadForm.title,
      text: uploadForm.text
    })
    
    analyzedWorks.value.push({
      author: uploadForm.author,
      title: uploadForm.title,
      analyzed_at: new Date().toLocaleString(),
      analysis: result.data?.analysis || {}
    })
    
    ElMessage.success('作品分析完成！')
    
    // 清空表单
    uploadForm.author = ''
    uploadForm.title = ''
    uploadForm.text = ''
    
  } catch (error) {
    ElMessage.error('分析失败：' + error.message)
  } finally {
    analyzing.value = false
  }
}

const viewWorkDetail = (work) => {
  selectedWork.value = work
  detailVisible.value = true
}

const applyStyle = (work) => {
  ElMessage.success(`已应用 ${work.author} - ${work.title} 的风格特征`)
  // 实际应该调用 API 应用风格
}

const generateReport = async () => {
  reportLoading.value = true
  
  try {
    const result = await apiClient.learning.getReport('default')
    if (result.data) {
      Object.assign(report, result.data)
    }
  } catch (error) {
    ElMessage.error('获取报告失败')
  } finally {
    reportLoading.value = false
  }
}

const loadAnalyzedWorks = async () => {
  try {
    const result = await apiClient.learning.getWorks()
    if (result.data && result.data.works) {
      analyzedWorks.value = result.data.works
    }
  } catch (error) {
    console.error('加载已分析作品失败:', error)
  }
}

onMounted(() => {
  generateReport()
  loadAnalyzedWorks()
})
</script>

<style scoped>
.learning-panel {
  width: 100%;
  max-width: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

ul {
  line-height: 2;
  padding-left: 20px;
}
</style>
