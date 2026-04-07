import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 可以在这里添加 token
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('响应错误:', error)
    
    if (error.response) {
      // 服务器返回错误响应
      const { status, data } = error.response
      console.error(`错误 ${status}:`, data)
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('无响应，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

// API 方法
export const apiClient = {
  // 健康检查
  health: {
    check: (detailed = false) => api.get(`/health?detailed=${detailed}`),
    ready: () => api.get('/health/ready'),
    live: () => api.get('/health/live'),
    metrics: () => api.get('/health/metrics')
  },
  
  // 配置管理
  config: {
    get: () => api.get('/config'),
    update: (data) => api.post('/config', data),
    reload: () => api.post('/config/reload'),
    testLLM: (provider) => api.post('/llm/test', { provider }),
    validateLLM: (provider, config) => api.post('/llm/validate', { provider, config })
  },
  
  // Agent 管理
  agents: {
    getStatus: () => api.get('/agents/status'),
    execute: (agentId, task) => api.post(`/agents/${agentId}/execute`, task),
    getTaskStatus: (taskId) => api.get(`/tasks/${taskId}`),
    listTasks: (params = {}) => api.get('/tasks', { params })
  },
  
  // 写作流程
  writing: {
    createChapter: (data) => api.post('/writing/chapter', data, { timeout: 0 }),
    getTaskStatus: (taskId) => api.get(`/writing/task/${taskId}`),
    getWorkflow: (workflowId) => api.get(`/writing/workflow/${workflowId}`),
    getChapter: (projectId, chapterNum) => api.get(`/writing/chapter/${projectId}/${chapterNum}`),
    updateChapter: (projectId, chapterNum, data) => api.put(`/writing/chapter/${projectId}/${chapterNum}`, data)
  },
  
  // 学习系统
  learning: {
    analyze: (data) => api.post('/learning/analyze', data, { timeout: 0 }),
    getAnalysisStatus: (analysisId) => api.get(`/learning/analysis/${analysisId}`),
    getWorks: () => api.get('/learning/works'),
    getWorkDetail: (analysisId) => api.get(`/learning/works/${analysisId}`),
    getReport: (projectId) => api.get(`/learning/report?project_id=${projectId}`)
  },
  
  // 派系管理
  schools: {
    list: (category) => api.get(`/schools${category ? `?category=${category}` : ''}`),
    getDetail: (schoolId) => api.get(`/schools/${schoolId}`),
    checkFusion: (schoolIds) => api.post('/schools/check-fusion', { school_ids: schoolIds }),
    fuse: (schoolIds, fusionName, weights) => api.post('/schools/fuse', {
      school_ids: schoolIds,
      fusion_name: fusionName,
      weights
    }),
    applyStyle: (styleId) => api.post('/schools/apply-style', { style_id: styleId })
  },
  
  // 小说管理
  novels: {
    list: () => api.get('/novels'),
    create: (data) => api.post('/novels', data),
    get: (novelId) => api.get(`/novels/${novelId}`),
    update: (novelId, data) => api.put(`/novels/${novelId}`, data),
    delete: (novelId) => api.delete(`/novels/${novelId}`),
    getChapters: (novelId) => api.get(`/novels/${novelId}/chapters`),
    createChapter: (novelId, data) => api.post(`/novels/${novelId}/chapters`, data),
    getChapter: (novelId, chapterNum) => api.get(`/novels/${novelId}/chapters/${chapterNum}`),
    updateChapter: (novelId, chapterNum, data) => api.put(`/novels/${novelId}/chapters/${chapterNum}`, data),
    exportChapter: (novelId, chapterNum, data) => api.post(`/novels/${novelId}/chapters/${chapterNum}/export`, data, { timeout: 0 }),
    deleteChapter: (novelId, chapterNum) => api.delete(`/novels/${novelId}/chapters/${chapterNum}`),
    getCharacters: (novelId) => api.get(`/novels/${novelId}/characters`),
    addCharacter: (novelId, data) => api.post(`/novels/${novelId}/characters`, data),
    getHooks: (novelId) => api.get(`/novels/${novelId}/hooks`)
  },
  
  // AI 创作
  ai: {
    generateOutline: (data) => api.post('/ai/generate-outline', data),
    generateCharacters: (data) => api.post('/ai/generate-characters', data),
    generateChapterOutline: (data) => api.post('/ai/generate-chapter-outline', data, { timeout: 0 }),
    generateStylePreview: (data) => api.post('/ai/generate-style-preview', data, { timeout: 0 }),
    generatePlot: (data) => api.post('/ai/generate-plot', data),
    getTemplates: () => api.get('/ai/templates')
  },
  
  // 全自动创作
  auto: {
    create: (data) => api.post('/auto/create', data, { timeout: 0 }),
    getBlueprint: (novelId) => api.get(`/auto/blueprint/${novelId}`),
    getTaskStatus: (taskId) => api.get(`/auto/task/${taskId}`)
  }
}

export default api
