<template>
  <div class="school-registry">
    <h2>🏛️ 派系库</h2>
    
    <!-- 派系分类导航 -->
    <el-tabs v-model="selectedCategory" @tab-change="filterSchools">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="武侠派" name="wuxia" />
      <el-tab-pane label="言情派" name="romance" />
      <el-tab-pane label="悬疑派" name="mystery" />
      <el-tab-pane label="玄幻派" name="fantasy" />
      <el-tab-pane label="文笔派" name="style" />
    </el-tabs>
    
    <el-row :gutter="20">
      <!-- 派系列表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>派系列表</span>
              <el-input
                v-model="searchQuery"
                placeholder="搜索派系..."
                style="width: 200px"
                clearable
              />
            </div>
          </template>
          
          <el-table :data="filteredSchools" style="width: 100%">
            <el-table-column prop="name" label="派系名称" width="150" />
            <el-table-column prop="category" label="分类" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ getCategoryName(row.category) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button size="small" @click="viewSchoolDetail(row)">详情</el-button>
                <el-button
                  size="small"
                  :type="selectedForFusion.includes(row.school_id) ? 'primary' : ''"
                  @click="toggleFusionSelection(row)"
                >
                  {{ selectedForFusion.includes(row.school_id) ? '已选' : '选入融合' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <!-- 融合面板 -->
      <el-col :span="8">
        <el-card v-if="selectedForFusion.length > 0">
          <template #header>
            <div class="card-header">
              <span>🔀 派系融合</span>
              <el-button size="small" @click="clearSelection">清空</el-button>
            </div>
          </template>
          
          <div class="selected-schools">
            <el-tag
              v-for="sid in selectedForFusion"
              :key="sid"
              closable
              @close="removeFromFusion(sid)"
            >
              {{ getSchoolName(sid) }}
            </el-tag>
          </div>
          
          <el-divider />
          
          <el-form label-width="80px">
            <el-form-item label="新风格名">
              <el-input v-model="fusionName" placeholder="例如：历史悬疑武侠" />
            </el-form-item>
            
            <el-form-item>
              <el-button @click="checkCompatibility" :loading="checking">
                检查兼容性
              </el-button>
            </el-form-item>
          </el-form>
          
          <!-- 兼容性结果 -->
          <el-alert
            v-if="compatibility"
            :title="compatibility.compatible ? '兼容性好' : '存在冲突'"
            :type="compatibility.compatible ? 'success' : 'warning'"
            :closable="false"
            show-icon
          >
            <p>兼容性评分：{{ (compatibility.score * 100).toFixed(0) }}%</p>
            <ul v-if="compatibility.conflicts.length">
              <li v-for="(c, index) in compatibility.conflicts" :key="index">
                {{ c.reason }}
              </li>
            </ul>
            <ul v-if="compatibility.suggestions.length">
              <li v-for="(s, index) in compatibility.suggestions" :key="index">
                {{ s }}
              </li>
            </ul>
          </el-alert>
          
          <el-divider />
          
          <el-button
            type="primary"
            style="width: 100%"
            :disabled="!compatibility?.compatible"
            @click="performFusion"
          >
            开始融合
          </el-button>
        </el-card>
        
        <!-- 融合历史 -->
        <el-card style="margin-top: 20px">
          <template #header>融合历史</template>
          
          <el-empty v-if="fusedStyles.length === 0" description="暂无融合历史" />
          
          <el-timeline v-else>
            <el-timeline-item
              v-for="(style, index) in fusedStyles"
              :key="index"
              :timestamp="style.created_at"
              placement="top"
            >
              <el-card>
                <h4>{{ style.style_name }}</h4>
                <p>来源：{{ style.source_schools.join(' + ') }}</p>
                <el-button size="small" type="primary" @click="applyStyle(style.style_id)">
                  应用此风格
                </el-button>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 派系详情对话框 -->
    <el-dialog v-model="detailVisible" title="派系详情" width="700px">
      <el-descriptions v-if="selectedSchool" :column="2" border>
        <el-descriptions-item label="派系名称">{{ selectedSchool.name }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ getCategoryName(selectedSchool.category) }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ selectedSchool.description }}</el-descriptions-item>
      </el-descriptions>
      
      <el-divider>核心特征</el-divider>
      <el-tag v-for="feature in selectedSchool?.key_features" :key="feature" style="margin: 5px">
        {{ feature }}
      </el-tag>
      
      <el-divider>风格维度</el-divider>
      <el-progress
        v-for="(value, dim) in selectedSchool?.style_dimensions"
        :key="dim"
        :percentage="value * 10"
        :format="() => `${dimName(dim)}: ${value}/10`"
      />
      
      <el-divider>代表作品</el-divider>
      <ul v-if="selectedSchool?.representative_works">
        <li v-for="work in selectedSchool.representative_works" :key="work">
          {{ work }}
        </li>
      </ul>
      
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { apiClient } from '@/api/client'

const selectedCategory = ref('all')
const searchQuery = ref('')
const detailVisible = ref(false)
const checking = ref(false)

const selectedForFusion = ref([])
const fusionName = ref('')
const compatibility = ref(null)

const schools = ref([])
const fusedStyles = ref([])
const selectedSchool = ref(null)

const filteredSchools = computed(() => {
  let result = schools.value
  
  if (selectedCategory.value !== 'all') {
    result = result.filter(s => s.category === selectedCategory.value)
  }
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(s =>
      s.name.toLowerCase().includes(query) ||
      s.description.toLowerCase().includes(query)
    )
  }
  
  return result
})

const getCategoryName = (category) => {
  const names = {
    'wuxia': '武侠',
    'romance': '言情',
    'mystery': '悬疑',
    'fantasy': '玄幻',
    'style': '文笔'
  }
  return names[category] || category
}

const dimName = (dim) => {
  const names = {
    'narrative_pace': '叙事节奏',
    'description_density': '描写密度',
    'dialogue_ratio': '对话比例',
    'emotional_intensity': '情感强度'
  }
  return names[dim] || dim
}

const getSchoolName = (schoolId) => {
  const school = schools.value.find(s => s.school_id === schoolId)
  return school?.name || schoolId
}

const viewSchoolDetail = (school) => {
  selectedSchool.value = school
  detailVisible.value = true
}

const toggleFusionSelection = (school) => {
  const index = selectedForFusion.value.indexOf(school.school_id)
  if (index > -1) {
    selectedForFusion.value.splice(index, 1)
  } else {
    selectedForFusion.value.push(school.school_id)
  }
}

const removeFromFusion = (schoolId) => {
  const index = selectedForFusion.value.indexOf(schoolId)
  if (index > -1) {
    selectedForFusion.value.splice(index, 1)
  }
}

const clearSelection = () => {
  selectedForFusion.value = []
  compatibility.value = null
  fusionName.value = ''
}

const checkCompatibility = async () => {
  if (selectedForFusion.value.length < 2) {
    ElMessage.warning('请至少选择 2 个派系')
    return
  }
  
  checking.value = true
  
  try {
    const result = await apiClient.schools.checkFusion(selectedForFusion.value)
    compatibility.value = result.data
    
    if (result.data.compatible) {
      ElMessage.success('派系兼容性好，可以融合')
    } else {
      ElMessage.warning('派系存在冲突，请查看建议')
    }
  } catch (error) {
    ElMessage.error('兼容性检查失败')
  } finally {
    checking.value = false
  }
}

const performFusion = async () => {
  if (!fusionName.value) {
    ElMessage.warning('请输入新风格名称')
    return
  }
  
  try {
    const result = await apiClient.schools.fuse(
      selectedForFusion.value,
      fusionName.value,
      {}
    )
    
    fusedStyles.value.unshift({
      style_id: result.data.style_id,
      style_name: result.data.style_name,
      source_schools: selectedForFusion.value.map(sid => getSchoolName(sid)),
      created_at: new Date().toLocaleString()
    })
    
    ElMessage.success(`融合成功！新风格：${fusionName.value}`)
    
    clearSelection()
    
  } catch (error) {
    ElMessage.error('融合失败：' + error.message)
  }
}

const applyStyle = (styleId) => {
  ElMessage.success('风格已应用')
}

const filterSchools = () => {}

const loadSchools = async () => {
  try {
    const result = await apiClient.schools.list()
    if (result.data && result.data.schools) {
      schools.value = result.data.schools
    }
  } catch (error) {
    console.error('加载派系失败:', error)
  }
}

const loadFusedStyles = async () => {
  fusedStyles.value = []
}

onMounted(() => {
  loadSchools()
  loadFusedStyles()
})
</script>

<style scoped>
.school-registry {
  width: 100%;
  max-width: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selected-schools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 40px;
}

ul {
  line-height: 2;
  padding-left: 20px;
}
</style>
