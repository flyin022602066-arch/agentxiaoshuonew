<template>
  <div class="agent-monitor">
    <h2>🤖 Agent 监控</h2>
    
    <!-- Agent 状态概览 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="agent in agents" :key="agent.agent_id">
        <el-card :class="['agent-card', 'status-' + agent.state]">
          <div class="agent-icon">
            <el-icon :size="40">
              <component :is="agentIcons[agent.agent_id]" />
            </el-icon>
          </div>
          <h3>{{ agentNames[agent.agent_id] || agent.agent_id }}</h3>
          <el-tag :type="agentStateTypes[agent.state]">
            {{ agentStateTexts[agent.state] }}
          </el-tag>
          <p class="last-active">
            {{ agent.last_active ? formatTime(agent.last_active) : '从未活动' }}
          </p>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 工作流状态 -->
    <el-card class="workflow-section">
      <template #header>
        <div class="card-header">
          <span>当前工作流</span>
          <el-button @click="refreshStatus" icon="Refresh" :loading="refreshing" />
        </div>
      </template>
      
      <el-table :data="workflows" style="width: 100%">
        <el-table-column prop="workflow_id" label="工作流 ID" width="200" />
        <el-table-column prop="chapter_num" label="章节" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="workflowStatusTypes[row.status]">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="200">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="row.status === 'completed' ? 'success' : undefined" />
          </template>
        </el-table-column>
        <el-table-column prop="current_stage" label="当前阶段" min-width="260">
          <template #default="{ row }">
            <div class="stage-cell">
              <div class="stage-title">{{ formatStageTitle(row) }}</div>
              <div class="stage-desc">{{ formatStageDescription(row) }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="viewWorkflowDetail(row.workflow_id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 系统资源 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>系统资源</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="内存使用">
              <el-progress :percentage="memoryUsage" :format="format => format + '%'" />
            </el-descriptions-item>
            <el-descriptions-item label="CPU 使用">
              <el-progress :percentage="cpuUsage" :format="format => format + '%'" />
            </el-descriptions-item>
            <el-descriptions-item label="磁盘空间">
              <el-progress :percentage="diskUsage" :format="format => format + '%'" />
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>任务统计</template>
          <el-statistic title="总任务数" :value="totalTasks" />
          <el-statistic title="成功任务" :value="successTasks" />
          <el-statistic title="失败任务" :value="failedTasks" />
          <el-statistic title="平均响应时间" :value="avgResponseTime" suffix="ms" />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 实时日志 -->
    <el-card class="log-section">
      <template #header>
        <div class="card-header">
          <span>实时日志</span>
          <el-switch v-model="autoScroll" active-text="自动滚动" />
        </div>
      </template>
      
      <div class="log-container" ref="logContainer">
        <div v-for="(log, index) in logs" :key="index" :class="['log-item', 'level-' + log.level]">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-agent">[{{ log.agent }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </el-card>
    
    <!-- 工作流详情对话框 -->
    <el-dialog
      v-model="workflowDetailVisible"
      title="工作流详情"
      width="600px"
    >
      <div v-if="currentWorkflow">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="工作流 ID">{{ currentWorkflow.workflow_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="workflowStatusTypes[currentWorkflow.status]">
              {{ currentWorkflow.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="进度">{{ currentWorkflow.progress }}%</el-descriptions-item>
          <el-descriptions-item label="当前阶段">
            <div class="stage-detail">
              <div class="stage-title">{{ formatStageTitle(currentWorkflow) }}</div>
              <div class="stage-desc">{{ formatStageDescription(currentWorkflow) }}</div>
            </div>
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider />
        
        <h4>工作流阶段</h4>
        <el-steps direction="vertical" :active="Math.floor(currentWorkflow.progress / 20)">
          <el-step title="剧情架构师" description="细化大纲" />
          <el-step title="人物设计师" description="准备角色" />
          <el-step title="章节写手" description="撰写初稿" />
          <el-step title="对话专家" description="打磨对话" />
          <el-step title="审核编辑" description="一致性检查" />
          <el-step title="主编" description="最终审核" />
        </el-steps>
      </div>
      <div v-else>
        <el-empty description="暂无工作流详情" />
      </div>
      
      <template #footer>
        <el-button @click="workflowDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { apiClient } from '@/api/client'
import { 
  User, Edit, Reading, Search, Check, Document, ChatDotRound 
} from '@element-plus/icons-vue'

const refreshing = ref(false)
const autoScroll = ref(true)

const agents = ref([])
const workflows = ref([])
const logs = ref([])

const memoryUsage = ref(0)
const cpuUsage = ref(0)
const diskUsage = ref(0)

const totalTasks = ref(0)
const successTasks = ref(0)
const failedTasks = ref(0)
const avgResponseTime = ref(0)

const workflowDetailVisible = ref(false)
const currentWorkflow = ref(null)

const agentNames = {
  'editor_agent': '主编',
  'plot_agent': '剧情架构师',
  'character_agent': '人物设计师',
  'writer_agent': '章节写手',
  'dialogue_agent': '对话专家',
  'reviewer_agent': '审核编辑',
  'learning_agent': '学习分析师'
}

const agentIcons = {
  'editor_agent': Check,
  'plot_agent': Document,
  'character_agent': User,
  'writer_agent': Edit,
  'dialogue_agent': ChatDotRound,
  'reviewer_agent': Search,
  'learning_agent': Reading
}

const agentStateTypes = {
  'idle': 'info',
  'working': 'warning',
  'error': 'danger'
}

const agentStateTexts = {
  'idle': '空闲',
  'working': '工作中',
  'error': '错误'
}

const workflowStatusTypes = {
  'pending': 'info',
  'started': 'warning',
  'in_progress': 'warning',
  'completed': 'success',
  'failed': 'danger'
}

const stageDescriptionMap = {
  auto_creation: [
    { match: ['开始创建蓝图'], title: '全自动创作：初始化蓝图', description: '系统正在创建世界观、主线结构与章节规划，为整本小说建立统一创作骨架。' },
    { match: ['世界观'], title: '全自动创作：构建世界观', description: '正在整理时代背景、规则体系与核心冲突，确保后续剧情有稳定的世界设定支撑。' },
    { match: ['蓝图', '规划'], title: '全自动创作：规划主线', description: '正在拆解主线节奏、阶段目标与关键转折点，形成可持续推进的长篇蓝图。' },
    { match: ['人物'], title: '全自动创作：生成人物设定', description: '正在补充角色定位、关系网络与成长路线，让主要人物具备持续发展的动机与张力。' },
    { match: ['伏笔'], title: '全自动创作：埋设伏笔', description: '正在安排前期线索与后续回收点，增强故事连贯性与阅读期待感。' },
    { match: ['第一章'], title: '全自动创作：生成首章', description: '正在根据蓝图完成第一章落地写作，输出可直接继续续写的开篇内容。' },
    { match: ['完成'], title: '全自动创作：已完成', description: '蓝图与首章已生成完成，可以进入写作面板继续扩写后续章节。' },
    { match: ['失败'], title: '全自动创作：执行失败', description: '自动创作流程中断，请结合错误信息和日志定位具体失败阶段。' }
  ],
  chapter_creation: [
    { match: ['开始创作'], title: '章节续写：准备生成', description: '系统正在整理当前章节大纲、上下文与风格要求，准备开始本章续写。' },
    { match: ['细化大纲'], title: '章节续写：细化大纲', description: '正在把章节目标拆成更细的场景与冲突节点，确保后续正文推进更稳定。' },
    { match: ['准备角色'], title: '章节续写：准备角色', description: '正在确认本章出场角色、关系状态与行为动机，避免人物表现失真。' },
    { match: ['撰写初稿'], title: '章节续写：生成初稿', description: '正在根据既有设定与章节目标撰写正文初稿，形成本章主要内容。' },
    { match: ['打磨对话'], title: '章节续写：润色对话', description: '正在优化角色对白与互动节奏，让对话更符合人物身份与场景情绪。' },
    { match: ['一致性检查'], title: '章节续写：一致性校验', description: '正在核对设定、剧情逻辑与上下文连续性，减少前后矛盾和信息遗漏。' },
    { match: ['最终审核'], title: '章节续写：最终审核', description: '正在做收尾审校与质量把关，确保本章可直接保存进入下一步创作。' },
    { match: ['创作完成', '完成'], title: '章节续写：已完成', description: '本章内容已生成并通过流程审核，可以保存结果或继续下一章节。' },
    { match: ['创作失败', '失败'], title: '章节续写：执行失败', description: '章节续写流程中断，请查看任务错误信息并结合日志继续排查。' }
  ]
}

const getStageMeta = (workflow) => {
  const taskType = workflow?.task_type || 'chapter_creation'
  const stage = workflow?.current_stage || ''
  const candidates = stageDescriptionMap[taskType] || stageDescriptionMap.chapter_creation
  const matched = candidates.find(item => item.match.some(keyword => stage.includes(keyword)))

  if (matched) {
    return matched
  }

  return {
    title: stage || '暂无阶段信息',
    description: stage ? '该阶段暂无预设说明，建议结合任务进度与日志一起判断执行状态。' : '任务暂未开始或后端尚未返回阶段信息。'
  }
}

const formatStageTitle = (workflow) => getStageMeta(workflow).title
const formatStageDescription = (workflow) => getStageMeta(workflow).description

const loadAgentStatus = async () => {
  try {
    const result = await apiClient.agents.getStatus()
    if (result.data && result.data.agents) {
      agents.value = result.data.agents
      // 更新任务统计
      if (result.data.total) {
        totalTasks.value = result.data.total
      }
    }
  } catch (error) {
    console.error('加载 Agent 状态失败:', error)
  }
}

const loadWorkflows = async () => {
  try {
    const result = await apiClient.agents.listTasks({ limit: 20 })
    const tasks = result.data?.tasks || []

    workflows.value = tasks
      .filter(task => ['chapter_creation', 'auto_creation'].includes(task.task_type))
      .map(task => ({
        workflow_id: task.task_id,
        task_id: task.task_id,
        task_type: task.task_type,
        chapter_num: task.metadata?.chapter_num || '-',
        status: task.status,
        progress: task.progress || 0,
        current_stage: task.current_stage || '',
        created_at: task.created_at,
        updated_at: task.updated_at,
        result: task.result,
        error: task.error,
        metadata: task.metadata || {}
      }))
  } catch (error) {
    workflows.value = []
  }
}

const loadSystemStats = async () => {
  try {
    // 获取系统统计信息
    const healthResult = await apiClient.health.check(true)
    if (healthResult.data) {
      // 从健康检查结果中提取资源使用情况
      const checks = healthResult.data.checks || {}
      if (checks.memory) {
        memoryUsage.value = checks.memory.memory_percent || 0
      }
      if (checks.disk_space) {
        diskUsage.value = checks.disk_space.usage_percent || 0
      }
    }
  } catch (error) {
    console.log('加载系统统计失败')
  }
}

const viewWorkflowDetail = async (workflowId) => {
  try {
    const result = await apiClient.agents.getTaskStatus(workflowId)
    currentWorkflow.value = {
      ...result.data,
      workflow_id: result.data?.workflow_id || result.data?.task_id || workflowId
    }
    workflowDetailVisible.value = true
  } catch (error) {
    ElMessage.error('获取工作流详情失败：' + error.message)
  }
}

const refreshStatus = async () => {
  refreshing.value = true
  await Promise.all([loadAgentStatus(), loadWorkflows(), loadSystemStats()])
  refreshing.value = false
}

const formatTime = (isoString) => {
  if (!isoString) return '从未活动'
  const date = new Date(isoString)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
}

// 实时日志
const addLog = (level, agent, message) => {
  logs.value.push({
    time: new Date().toLocaleTimeString(),
    level,
    agent,
    message
  })
  
  if (logs.value.length > 100) {
    logs.value.shift()
  }
}

onMounted(() => {
  loadAgentStatus()
  loadWorkflows()
  loadSystemStats()
  
  // 定时刷新
  const interval = setInterval(refreshStatus, 5000)
  
  onUnmounted(() => {
    clearInterval(interval)
  })
})
</script>

<style scoped>
.agent-monitor {
  width: 100%;
  max-width: none;
}

.agent-card {
  margin-bottom: 20px;
  text-align: center;
  transition: all 0.3s;
}

.agent-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.agent-card.status-working {
  border-left: 4px solid #e6a23c;
}

.stage-cell,
.stage-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stage-title {
  color: #303133;
  font-weight: 600;
  line-height: 1.5;
}

.stage-desc {
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}

.agent-card.status-idle {
  border-left: 4px solid #909399;
}

.agent-card.status-error {
  border-left: 4px solid #f56c6c;
}

.agent-icon {
  margin-bottom: 10px;
}

.last-active {
  color: #909399;
  font-size: 12px;
  margin-top: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-section {
  margin-top: 20px;
}

.log-container {
  height: 300px;
  overflow-y: auto;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 10px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.log-item {
  margin-bottom: 5px;
}

.log-time {
  color: #569cd6;
  margin-right: 10px;
}

.log-agent {
  color: #4ec9b0;
  margin-right: 10px;
}

.log-message {
  color: #d4d4d4;
}

.level-info .log-message {
  color: #d4d4d4;
}

.level-warning .log-message {
  color: #dcdcaa;
}

.level-error .log-message {
  color: #f48771;
}
</style>
