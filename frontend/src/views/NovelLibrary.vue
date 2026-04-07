<template>
  <div class="novel-library">
    <h2>📚 小说仓库</h2>
    
    <!-- 批量操作工具栏 -->
    <el-card class="batch-card" v-if="selectedNovels.length > 0">
      <div class="batch-toolbar">
        <span class="batch-info">已选择 {{ selectedNovels.length }} 本小说</span>
        <div class="batch-actions">
          <el-button type="warning" size="small" @click="batchDownload">📥 批量下载</el-button>
          <el-button type="danger" size="small" @click="batchDelete">🗑️ 批量删除</el-button>
          <el-button size="small" @click="clearSelection">❌ 取消选择</el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true">
        <el-form-item label="搜索">
          <el-input v-model="searchQuery" placeholder="搜索书名..." clearable style="width: 200px" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filterGenre" placeholder="全部类型" clearable style="width: 120px">
            <el-option label="玄幻" value="玄幻" />
            <el-option label="仙侠" value="仙侠" />
            <el-option label="都市" value="都市" />
            <el-option label="历史" value="历史" />
            <el-option label="科幻" value="科幻" />
            <el-option label="游戏" value="游戏" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="连载中" value="ongoing" />
            <el-option label="已完成" value="completed" />
            <el-option label="暂停" value="paused" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadNovels">🔄 刷新</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 小说列表 -->
    <el-row :gutter="20" v-show="!loadError && paginatedNovels.length > 0">
      <el-col :span="8" v-for="novel in paginatedNovels" :key="novel.id">
        <el-card class="novel-card" shadow="hover">
          <template #header>
            <div class="novel-header">
              <el-checkbox 
                :model-value="selectedNovels.includes(novel.id)"
                :label="novel.id"
                @change="toggleNovelSelection(novel.id, $event)"
                @click.stop
              />
              <span class="novel-title">{{ novel.title }}</span>
              <el-tag size="small" type="success">{{ novel.genre }}</el-tag>
            </div>
          </template>
          
          <div class="novel-content">
            <p class="novel-desc">{{ novel.description || '暂无简介' }}</p>
            
            <div class="novel-stats">
              <el-tag size="small" type="info">📖 {{ novel.total_chapters || 0 }}章</el-tag>
              <el-tag size="small" type="success">✍️ {{ novel.total_words || 0 }}字</el-tag>
            </div>
            
            <div class="novel-meta">
              <el-tag size="small" :type="getStatusType(novel.status)">
                {{ getStatusText(novel.status) }}
              </el-tag>
              <span class="create-time">创建：{{ formatDate(novel.created_at) }}</span>
            </div>
          </div>
          
          <template #footer>
            <div class="novel-actions">
              <el-button size="small" type="primary" @click="viewNovel(novel.id)">📖 查看</el-button>
              <el-button size="small" type="success" @click="editNovel(novel.id)">✏️ 编辑</el-button>
              <el-button size="small" type="warning" @click="continueWriting(novel.id)">✍️ 续写</el-button>
              <el-button size="small" type="info" @click="startDownload(novel.id)">📥 下载</el-button>
              <el-button size="small" type="danger" @click="deleteNovel(novel.id)">🗑️ 删除</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 分页 -->
    <el-pagination
      v-show="!loadError && totalPages > 1"
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="filteredNovels.length"
      layout="total, prev, pager, next"
      style="margin-top: 20px; justify-content: center; display: flex;"
    />
    
    <!-- 空状态 -->
    <el-empty
      v-show="loadError"
      :description="loadError"
    >
      <el-button type="primary" @click="loadNovels">🔄 重试加载</el-button>
    </el-empty>

    <el-empty v-show="!loadError && novels.length === 0" description="暂无小说，快去创作吧！">
      <el-button type="primary" @click="$router.push('/auto')">🚀 开始创作</el-button>
    </el-empty>
    
    <!-- 查看对话框 -->
    <el-dialog v-model="viewVisible" title="📖 查看小说" width="900px">
      <div v-if="selectedNovel">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="书名">{{ selectedNovel.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedNovel.genre }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ getStatusText(selectedNovel.status) }}</el-descriptions-item>
          <el-descriptions-item label="章节数">{{ selectedNovel.total_chapters || 0 }}章</el-descriptions-item>
          <el-descriptions-item label="总字数">{{ selectedNovel.total_words || 0 }}字</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(selectedNovel.created_at) }}</el-descriptions-item>
        </el-descriptions>
        
        <el-divider />
        
        <h4>📝 章节列表</h4>
          <el-table :data="chapters" stripe max-height="400">
            <el-table-column prop="chapter_num" label="章节" width="80" />
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="word_count" label="字数" width="80" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="viewChapter(row)">👁️ 查看</el-button>
                <el-button size="small" type="danger" @click="deleteChapter(row)">🗑️ 删除</el-button>
              </template>
            </el-table-column>
          </el-table>
      </div>
    </el-dialog>
    
    <!-- 章节查看对话框 -->
    <el-dialog v-model="chapterVisible" title="📖 查看章节" width="900px">
      <div v-if="currentChapter">
        <h3>{{ currentChapter.title }}</h3>
        <div class="chapter-content">{{ currentChapter.content || '暂无内容' }}</div>
      </div>
    </el-dialog>
    
    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" title="✏️ 编辑小说" width="600px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="书名" required>
          <el-input v-model="editForm.title" placeholder="请输入书名" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="editForm.genre" placeholder="选择类型" style="width: 100%">
            <el-option label="玄幻" value="玄幻" />
            <el-option label="仙侠" value="仙侠" />
            <el-option label="都市" value="都市" />
            <el-option label="历史" value="历史" />
            <el-option label="科幻" value="科幻" />
            <el-option label="游戏" value="游戏" />
          </el-select>
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="editForm.description" type="textarea" :rows="4" placeholder="小说简介" />
        </el-form-item>
        <el-form-item label="状态" required>
          <el-select v-model="editForm.status" placeholder="选择状态" style="width: 100%">
            <el-option label="连载中" value="ongoing" />
            <el-option label="已完成" value="completed" />
            <el-option label="暂停" value="paused" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">❌ 取消</el-button>
        <el-button type="primary" @click="confirmEdit">💾 保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 下载对话框 -->
    <el-dialog v-model="downloadVisible" title="📥 下载小说" width="500px">
      <el-form label-width="100px">
        <el-form-item label="下载格式" required>
          <el-radio-group v-model="downloadFormat">
            <el-radio label="txt">📄 TXT 文本</el-radio>
            <el-radio label="md">📝 Markdown</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="downloadVisible = false">❌ 取消</el-button>
        <el-button type="primary" @click="confirmDownload">⬇️ 下载</el-button>
      </template>
    </el-dialog>
    
    <!-- 批量下载对话框 -->
    <el-dialog v-model="batchDownloadVisible" title="📥 批量下载" width="500px">
      <el-form label-width="100px">
        <el-form-item label="下载格式" required>
          <el-radio-group v-model="downloadFormat">
            <el-radio label="txt">📄 TXT 文本</el-radio>
            <el-radio label="md">📝 Markdown</el-radio>
            <el-radio label="zip">📦 ZIP 压缩包</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-alert
          title="批量下载提示"
          type="info"
          :closable="false"
          show-icon
        >
          <p>将下载 {{ selectedNovels.length }} 本小说：</p>
          <ul>
            <li v-for="id in selectedNovels" :key="id">
              {{ novels.find(n => n.id === id)?.title }}
            </li>
          </ul>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="batchDownloadVisible = false">❌ 取消</el-button>
        <el-button type="primary" @click="confirmBatchDownload">⬇️ 开始下载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiClient } from '@/api/client'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const filterGenre = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(9)

// 数据
const novels = ref([])
const chapters = ref([])

// 批量选择
const selectedNovels = ref([])

// 对话框
const viewVisible = ref(false)
const editVisible = ref(false)
const chapterVisible = ref(false)
const downloadVisible = ref(false)
const batchDownloadVisible = ref(false)

// 当前选中
const selectedNovel = ref(null)
const currentChapter = ref(null)
const downloadNovelId = ref('')

// 编辑表单
const editForm = reactive({
  title: '',
  genre: '',
  description: '',
  status: 'ongoing'
})

// 下载选项
const downloadFormat = ref('txt')
const loadError = ref('')

// 计算属性
const filteredNovels = computed(() => {
  return novels.value.filter(novel => {
    const matchSearch = !searchQuery.value || novel.title.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchGenre = !filterGenre.value || novel.genre === filterGenre.value
    const matchStatus = !filterStatus.value || novel.status === filterStatus.value
    return matchSearch && matchGenre && matchStatus
  })
})

const totalPages = computed(() => {
  return Math.ceil(filteredNovels.value.length / pageSize.value)
})

const paginatedNovels = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredNovels.value.slice(start, end)
})

// 方法
const getStatusText = (status) => {
  const map = { 'ongoing': '连载中', 'completed': '已完成', 'paused': '暂停' }
  return map[status] || status
}

const getStatusType = (status) => {
  const map = { 'ongoing': 'success', 'completed': 'info', 'paused': 'warning' }
  return map[status] || 'info'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('zh-CN')
}

const loadNovels = async () => {
  try {
    loadError.value = ''
    const result = await apiClient.novels.list()
    if (result.data && result.data.novels) {
      novels.value = result.data.novels
      currentPage.value = 1
      ElMessage.success(`加载了 ${novels.value.length} 本小说`)
      return
    }

    novels.value = []
    loadError.value = '小说列表接口已返回，但未包含有效数据。请稍后重试。'
  } catch (error) {
    novels.value = []
    const status = error.response?.status
    loadError.value = status >= 500
      ? '小说仓库服务暂时异常，请检查后端服务或稍后重试。'
      : `加载小说列表失败：${error.message || '未知错误'}`
    ElMessage.error(loadError.value)
  }
}

const viewNovel = async (novelId) => {
  try {
    const result = await apiClient.novels.get(novelId)
    selectedNovel.value = result.data
    const chaptersResult = await apiClient.novels.getChapters(novelId)
    chapters.value = chaptersResult.data?.chapters || []
    viewVisible.value = true
  } catch (error) {
    const status = error.response?.status
    ElMessage.error(status >= 500
      ? '小说详情服务暂时异常，请先确认后端正常运行。'
      : '加载小说详情失败：' + error.message)
  }
}

const viewChapter = (chapter) => {
  currentChapter.value = chapter
  chapterVisible.value = true
}

const deleteChapter = async (chapter) => {
  if (!selectedNovel.value?.id) return

  try {
    await ElMessageBox.confirm(
      `确定删除第${chapter.chapter_num}章吗？删除后无法恢复。`,
      '确认删除章节',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await apiClient.novels.deleteChapter(selectedNovel.value.id, chapter.chapter_num)
    chapters.value = chapters.value.filter(item => item.chapter_num !== chapter.chapter_num)

    if (currentChapter.value?.chapter_num === chapter.chapter_num) {
      currentChapter.value = null
      chapterVisible.value = false
    }

    const latestNovel = await apiClient.novels.get(selectedNovel.value.id)
    selectedNovel.value = latestNovel.data
    await loadNovels()
    ElMessage.success('章节已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除章节失败：' + (error.message || '未知错误'))
    }
  }
}

const editNovel = async (novelId) => {
  try {
    const result = await apiClient.novels.get(novelId)
    const novel = result.data
    
    editForm.title = novel.title
    editForm.genre = novel.genre || '玄幻'
    editForm.description = novel.description || ''
    editForm.status = novel.status || 'ongoing'
    selectedNovel.value = novel
    
    editVisible.value = true
  } catch (error) {
    ElMessage.error('加载小说信息失败：' + error.message)
  }
}

const confirmEdit = async () => {
  try {
    await apiClient.novels.update(selectedNovel.value.id, {
      title: editForm.title,
      genre: editForm.genre,
      description: editForm.description,
      status: editForm.status
    })
    
    ElMessage.success('小说信息已更新')
    editVisible.value = false
    loadNovels()
  } catch (error) {
    ElMessage.error('更新失败：' + error.message)
  }
}

const continueWriting = (novelId) => {
  localStorage.setItem('writing_panel_state', JSON.stringify({ selectedNovelId: novelId }))
  router.push('/writing')
}

const startDownload = (novelId) => {
  downloadNovelId.value = novelId
  downloadVisible.value = true
}

const confirmDownload = async () => {
  try {
    const novelId = downloadNovelId.value
    const chaptersResult = await apiClient.novels.getChapters(novelId)
    const allChapters = chaptersResult.data?.chapters || []
    
    if (allChapters.length === 0) {
      ElMessage.warning('暂无章节可下载')
      return
    }
    
    const novel = novels.value.find(n => n.id === novelId)
    
    if (downloadFormat.value === 'txt') {
      const content = allChapters.map(ch => `第${ch.chapter_num}章 ${ch.title || ''}\n\n${ch.content || ''}\n\n`).join('---\n\n')
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${novel?.title || '小说'}.txt`
      a.click()
      URL.revokeObjectURL(url)
    } else if (downloadFormat.value === 'md') {
      const content = `# ${novel?.title || '小说'}\n\n**类型**: ${novel?.genre || ''}\n**简介**: ${novel?.description || ''}\n\n---\n\n` +
        allChapters.map(ch => `## 第${ch.chapter_num}章 ${ch.title || ''}\n\n${ch.content || ''}\n\n`).join('---\n\n')
      const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${novel?.title || '小说'}.md`
      a.click()
      URL.revokeObjectURL(url)
    }
    
    downloadVisible.value = false
    ElMessage.success(`下载成功！格式：${downloadFormat.value.toUpperCase()}`)
  } catch (error) {
    ElMessage.error('下载失败：' + error.message)
  }
}

const deleteNovel = async (novelId) => {
  try {
    await ElMessageBox.confirm('确定要删除这本小说吗？删除后无法恢复！', '确认删除', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await apiClient.novels.delete(novelId)
    ElMessage.success('小说已删除')
    loadNovels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

const batchDownload = () => {
  if (selectedNovels.value.length === 0) {
    ElMessage.warning('请先选择要下载的小说')
    return
  }
  batchDownloadVisible.value = true
}

const confirmBatchDownload = async () => {
  try {
    for (const novelId of selectedNovels.value) {
      const novel = novels.value.find(n => n.id === novelId)
      if (!novel) continue
      
      const chaptersResult = await apiClient.novels.getChapters(novelId)
      const allChapters = chaptersResult.data?.chapters || []
      
      if (allChapters.length === 0) continue
      
      if (downloadFormat.value === 'txt') {
        const content = allChapters.map(ch => `第${ch.chapter_num}章 ${ch.title || ''}\n\n${ch.content || ''}\n\n`).join('---\n\n')
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${novel.title}.txt`
        a.click()
        URL.revokeObjectURL(url)
      } else if (downloadFormat.value === 'md') {
        const content = `# ${novel.title}\n\n**类型**: ${novel.genre}\n**简介**: ${novel.description}\n\n---\n\n` +
          allChapters.map(ch => `## 第${ch.chapter_num}章 ${ch.title || ''}\n\n${ch.content || ''}\n\n`).join('---\n\n')
        const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${novel.title}.md`
        a.click()
        URL.revokeObjectURL(url)
      }
    }
    
    batchDownloadVisible.value = false
    ElMessage.success(`批量下载成功！共下载 ${selectedNovels.value.length} 本小说`)
    clearSelection()
  } catch (error) {
    ElMessage.error('批量下载失败：' + error.message)
  }
}

const batchDelete = async () => {
  if (selectedNovels.value.length === 0) {
    ElMessage.warning('请先选择要删除的小说')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedNovels.value.length} 本小说吗？删除后无法恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    for (const novelId of selectedNovels.value) {
      try {
        await apiClient.novels.delete(novelId)
      } catch (error) {
        console.error(`删除小说 ${novelId} 失败:`, error)
      }
    }
    
    ElMessage.success(`成功删除 ${selectedNovels.value.length} 本小说`)
    clearSelection()
    loadNovels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败：' + error.message)
    }
  }
}

const clearSelection = () => {
  selectedNovels.value = []
}

const toggleNovelSelection = (novelId, checked) => {
  if (checked) {
    if (!selectedNovels.value.includes(novelId)) {
      selectedNovels.value = [...selectedNovels.value, novelId]
    }
    return
  }

  selectedNovels.value = selectedNovels.value.filter(id => id !== novelId)
}

onMounted(() => {
  loadNovels()
})
</script>

<style scoped>
.novel-library { width: 100%; max-width: none; padding: 20px; }
.batch-card { margin-bottom: 20px; background: #fff7e6; border-color: #ffd591; }
.batch-toolbar { display: flex; justify-content: space-between; align-items: center; }
.batch-info { font-size: 14px; color: #d46b08; font-weight: bold; }
.batch-actions { display: flex; gap: 10px; }
.filter-card { margin-bottom: 20px; }
.novel-card { margin-bottom: 20px; transition: all 0.3s; }
.novel-card:hover { transform: translateY(-5px); }
.novel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 10px; }
.novel-title { font-weight: bold; font-size: 16px; color: #303133; flex: 1; }
.novel-content { min-height: 150px; }
.novel-desc { color: #666; font-size: 14px; line-height: 1.6; margin-bottom: 15px; height: 60px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.novel-stats { display: flex; gap: 10px; margin-bottom: 10px; }
.novel-meta { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #999; }
.create-time { margin-left: 10px; }
.novel-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.chapter-content { max-height: 500px; overflow-y: auto; padding: 20px; background: #f9f9f9; border-radius: 4px; line-height: 2; font-size: 15px; white-space: pre-wrap; }
</style>
