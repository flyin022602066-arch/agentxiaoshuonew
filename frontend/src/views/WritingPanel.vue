<template>
  <div class="writing-panel">
    <h2>✍️ 写作面板</h2>
    
    <!-- 顶部：小说选择 -->
    <el-card class="novel-selector-card">
      <el-form :inline="true">
        <el-form-item label="选择小说">
          <el-select 
            v-model="selectedNovelId" 
            placeholder="选择要创作的小说"
            style="width: 300px"
            @change="loadNovelData"
          >
            <el-option
              v-for="novel in novels"
              :key="novel.id"
              :label="novel.title"
              :value="novel.id"
            >
              <span>{{ novel.title }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ novel.chapterCount }}章</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="createNewNovel">新建小说</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="editNovelSettings">小说设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-alert
      v-if="selectedNovelId && !blueprintSummary.length"
      title="当前小说没有全自动创作上下文"
      type="warning"
      :closable="false"
      show-icon
      style="margin-top: 20px"
    >
      <p>这本小说当前未保存世界观地图、宏观规划、人物体系、伏笔网络，所以不会走我测试成功时那条“全自动上下文续写”路线。</p>
      <p>如果你想要和测试一致的创作效果，请从“全自动创作”页新建小说，再进入写作面板续写。</p>
      <div style="margin-top: 10px;">
        <el-button type="primary" size="small" @click="$router.push('/auto')">去全自动创作</el-button>
      </div>
    </el-alert>
    
    <!-- AI 创作工具 -->
    <el-card class="ai-tools-card" v-if="selectedNovelId">
      <template #header>
        <div class="card-header">
          <span>🤖 AI 创作工具</span>
          <div>
            <el-button type="primary" size="small" @click="startWriting" :loading="writing">
              {{ writing ? '创作中...' : 'AI 创作本章' }}
            </el-button>
            <el-button type="success" size="small" @click="continueWriting" :loading="writing">
              {{ writing ? '创作中...' : '续写下一章' }}
            </el-button>
          </div>
        </div>
      </template>
      <el-alert
        title="AI 创作说明"
        type="info"
        :closable="false"
        show-icon
      >
        <p>点击"AI 创作本章"根据大纲生成当前章节正文</p>
        <p>点击"续写下一章"会自动创建新章节、生成大纲并直接开始 AI 创作</p>
        <p>创作过程在后台运行，可关闭弹窗后在日志中查看进度</p>
      </el-alert>
    </el-card>

    <el-card v-if="selectedNovelId && blueprintSummary.length" class="blueprint-card" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>🧭 全自动创作上下文</span>
          <el-tag type="success" size="small">续写会自动参考这些设定</el-tag>
        </div>
      </template>
      <el-row :gutter="12">
        <el-col :span="12" v-for="item in blueprintSummary" :key="item.title">
          <el-card shadow="never" class="blueprint-summary-card">
            <div class="blueprint-summary-title">{{ item.title }}</div>
            <div class="blueprint-summary-content">{{ item.content }}</div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
    
    <el-row :gutter="20" v-if="selectedNovelId">
      <!-- 左侧：章节列表 -->
      <el-col :span="6">
        <el-card class="chapters-card">
          <template #header>
            <div class="card-header">
              <span>📚 章节列表</span>
              <el-button type="primary" size="small" @click="createNewChapter">+ 新建</el-button>
            </div>
          </template>
          
          <el-input
            v-model="chapterSearch"
            placeholder="搜索章节..."
            size="small"
            clearable
            prefix-icon="Search"
            style="margin-bottom: 12px"
          />
          
          <div class="chapters-list">
            <div
              v-for="chapter in filteredChapters"
              :key="chapter.num"
              class="chapter-card"
              :class="{ 'chapter-active': currentChapterNum === chapter.num }"
              @click="handleChapterSelect(String(chapter.num))"
            >
              <div class="chapter-header">
                <span class="chapter-num">第{{ chapter.num }}章</span>
                <el-tag 
                  size="small" 
                  :type="chapter.status === 'published' ? 'success' : 'warning'"
                >
                  {{ chapter.status === 'published' ? '已发布' : '草稿' }}
                </el-tag>
              </div>
              <div class="chapter-title-text">{{ chapter.title || '未命名' }}</div>
              <div class="chapter-footer">
                <span class="chapter-words">{{ chapter.wordCount?.toLocaleString() || 0 }} 字</span>
                <span v-if="chapter.updatedAt" class="chapter-date">{{ formatDate(chapter.updatedAt) }}</span>
              </div>
              <el-button
                text
                type="danger"
                size="small"
                class="chapter-delete-btn"
                @click.stop="deleteChapter(chapter)"
              >
                删除
              </el-button>
            </div>
          </div>
          
          <el-empty v-if="filteredChapters.length === 0" description="暂无章节，点击新建创建第一章" />
        </el-card>
        
        <!-- 统计信息 -->
        <el-card class="stats-card" style="margin-top: 20px">
          <template #header>统计信息</template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="总章节数">{{ totalChapters }}</el-descriptions-item>
            <el-descriptions-item label="总字数">{{ totalWords.toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="已发布">{{ publishedChapters }}</el-descriptions-item>
            <el-descriptions-item label="草稿">{{ draftChapters }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <!-- 中间：创作区域 -->
      <el-col :span="12">
        <el-card class="editor-card">
          <template #header>
            <div class="card-header">
              <el-input
                v-model="chapterTitle"
                placeholder="章节标题"
                size="large"
                style="flex: 1; margin-right: 10px"
              />
              <el-button 
                type="primary" 
                @click="startWriting" 
                :loading="writing"
                size="large"
              >
                {{ writing ? '创作中...' : 'AI 创作' }}
              </el-button>
            </div>
          </template>
          
          <!-- 大纲编辑区 -->
          <div class="outline-section">
            <div class="section-header">
              <span>📋 本章大纲</span>
              <el-tag size="small" type="info">给 AI 的创作指令</el-tag>
            </div>
            <el-input
              v-model="chapterOutline"
              type="textarea"
              :rows="6"
              placeholder="请输入本章大纲，例如：主角首次遭遇反派，展现两人性格对比。需要包含冲突、对话和动作描写。"
              resize="vertical"
            />
          </div>
          
          <el-divider />
          
          <!-- 正文编辑区 -->
          <div class="content-section">
            <div class="section-header">
              <span>📝 正文内容</span>
              <div class="section-actions">
                <el-radio-group v-model="editorMode" size="small">
                  <el-radio-button label="edit">编辑</el-radio-button>
                  <el-radio-button label="preview">预览</el-radio-button>
                </el-radio-group>
              </div>
            </div>
            
            <el-input
              v-if="editorMode === 'edit'"
              v-model="chapterContent"
              type="textarea"
              :rows="20"
              placeholder="在此输入或编辑正文内容..."
              resize="vertical"
            />
            
            <div v-else class="preview-content" v-html="renderedContent"></div>
            
            <div class="content-footer">
              <span class="word-count">
                字数：{{ currentWordCount }} / 目标：{{ wordCountTarget }}
                <el-progress 
                  :percentage="Math.min(100, (currentWordCount / wordCountTarget) * 100)" 
                  :status="currentWordCount >= wordCountTarget ? 'success' : undefined"
                  style="width: 150px; margin-left: 10px"
                />
              </span>
              <div class="actions">
                <el-button @click="saveChapter" :disabled="!chapterContent">保存</el-button>
                <el-button @click="exportChapter">导出</el-button>
              </div>
            </div>
          </div>
        </el-card>
        
        <!-- 创作设置 -->
        <el-card class="settings-card" style="margin-top: 20px">
          <template #header>创作设置</template>
          <el-form label-width="100px" size="small">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="章节号">
                  <el-input-number v-model="currentChapterNum" :min="1" :max="10000" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="目标字数">
                  <el-input-number v-model="wordCountTarget" :min="500" :max="10000" :step="500" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="写作风格">
              <el-select v-model="selectedStyle" filterable placeholder="搜索或选择风格" style="width: 100%" @change="showStylePreview">
                <el-option-group
                  v-for="(styles, groupName) in groupedStyleOptions"
                  :key="groupName"
                  :label="groupName"
                >
                  <el-option
                    v-for="style in styles"
                    :key="style.id"
                    :label="style.name"
                    :value="style.id"
                  />
                </el-option-group>
              </el-select>
              <div v-if="stylePreview" class="style-preview">
                <el-alert :title="stylePreview.name" type="info" :closable="false" show-icon>
                  <p>{{ stylePreview.description }}</p>
                  <p><strong>特点：</strong>{{ stylePreview.features.join('、') }}</p>
                  <p v-if="stylePreview.forbidden?.length"><strong>避免：</strong>{{ stylePreview.forbidden.join('、') }}</p>
                  <p v-if="stylePreview.toneExample"><strong>示例：</strong>“{{ stylePreview.toneExample }}”</p>
                </el-alert>
                <div style="margin-top: 8px;">
                  <el-select
                    v-model="compareStyleIds"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    :multiple-limit="4"
                    placeholder="选择 2-4 个风格做对比"
                    style="width: 100%"
                  >
                    <el-option-group
                      v-for="(styles, groupName) in groupedStyleOptions"
                      :key="`compare-${groupName}`"
                      :label="groupName"
                    >
                      <el-option
                        v-for="style in styles"
                        :key="style.id"
                        :label="style.name"
                        :value="style.id"
                      />
                    </el-option-group>
                  </el-select>
                </div>
              </div>
            </el-form-item>

            <el-form-item label="风格强度">
              <el-radio-group v-model="selectedStyleStrength" size="small">
                <el-radio-button label="light">轻度</el-radio-button>
                <el-radio-button label="medium">中度</el-radio-button>
                <el-radio-button label="strong">强烈</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="常用组合">
              <div style="width: 100%;">
                <div style="margin-bottom: 8px;">
                  <el-button size="small" @click="saveCurrentStylePreset">保存当前组合</el-button>
                </div>
                <div v-if="stylePresets.length">
                  <el-tag
                    v-for="preset in stylePresets"
                    :key="preset.id"
                    closable
                    @click="applyStylePreset(preset)"
                    @close="removeStylePreset(preset.id)"
                    style="margin: 0 8px 8px 0; cursor: pointer;"
                  >
                    {{ preset.name }}
                  </el-tag>
                </div>
                <el-text v-else type="info">还没有保存的风格组合</el-text>
              </div>
            </el-form-item>
            
            <el-form-item label="应用技巧">
              <el-checkbox-group v-model="selectedTechniques">
                <el-checkbox 
                  v-for="tech in availableTechniques" 
                  :key="tech.id" 
                  :label="tech.id"
                >
                  <span>{{ tech.name }}</span>
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 右侧：辅助面板 -->
      <el-col :span="6">
        <!-- Agent 状态 -->
        <el-card class="agent-status-card">
          <template #header>Agent 状态</template>
          <div class="agent-item" v-for="agent in agentStatus" :key="agent.name">
            <el-tag size="small" :type="agent.status === 'idle' ? 'success' : 'warning'">
              {{ agent.status === 'idle' ? '空闲' : '工作中' }}
            </el-tag>
            <span>{{ agent.name }}</span>
          </div>
        </el-card>
        
        <!-- 人物提示 -->
        <el-card class="characters-card" style="margin-top: 20px">
          <template #header>本章人物</template>
          <el-tag
            v-for="char in chapterCharacters"
            :key="char.id"
            closable
            @close="removeCharacter(char.id)"
            style="margin: 3px"
          >
            {{ char.name }}
          </el-tag>
          <el-button size="small" text @click="addCharacter" style="margin-top: 5px">
            + 添加人物
          </el-button>
        </el-card>
        
        <!-- 伏笔提示 -->
        <el-card class="hooks-card" style="margin-top: 20px">
          <template #header>
            <span>伏笔提示</span>
            <el-badge :value="unresolvedHooks" :hidden="unresolvedHooks === 0" type="warning" />
          </template>
          <el-empty v-if="unresolvedHooks === 0" description="暂无未回收伏笔" />
          <div v-else class="hook-list">
            <div v-for="hook in unresolvedHookList" :key="hook.id" class="hook-item">
              <el-tag size="small" type="warning">{{ hook.type }}</el-tag>
              <p>{{ hook.description }}</p>
              <small>第{{ hook.chapterIntroduced }}章埋设</small>
            </div>
          </div>
        </el-card>
        
        <!-- Token 统计 -->
        <el-card class="token-stats-card" style="margin-top: 20px">
          <template #header>API 使用统计</template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="今日调用">{{ todayCalls }}</el-descriptions-item>
            <el-descriptions-item label="Token 消耗">{{ tokenUsed.toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="估算费用">¥{{ estimatedCost.toFixed(2) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 创作日志 -->
        <el-card class="log-card" style="margin-top: 20px">
          <template #header>
            <span>创作日志</span>
            <el-switch v-model="autoScroll" active-text="自动滚动" size="small" />
          </template>
          <div class="log-container" ref="logContainer">
            <div v-for="(log, index) in logs" :key="index" class="log-item">
              <span class="log-time">{{ log.time }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-empty v-else description="请先选择要创作的小说" :image-size="200" />
    
    <!-- 创作进度对话框 -->
    <el-dialog v-model="progressVisible" title="AI 创作中" width="600px" :close-on-click-modal="true" :close-on-press-escape="true" @close="handleProgressClose">
      <el-progress :percentage="progress" :status="progressStatus" />
      <p style="text-align: center; margin-top: 10px">{{ currentStage }}</p>
      <p style="text-align: center; color: #606266; font-size: 13px; margin-top: 6px">
        {{ getWritingStageHint(currentStage) }}
      </p>
      <p style="text-align: center; color: #909399; font-size: 12px; margin-top: 5px">
        任务在后台运行，关闭弹窗后仍会继续创作
      </p>
      <p v-if="latestTaskId" style="text-align: center; color: #909399; font-size: 12px; margin-top: 4px">
        任务编号：{{ latestTaskId }}
      </p>
      
      <el-steps direction="vertical" :active="currentStep" style="margin-top: 20px">
        <el-step title="AI 正在创作" :description="currentStage" />
      </el-steps>

      <template #footer>
        <el-button @click="progressVisible = false">关闭弹窗（后台继续）</el-button>
      </template>
    </el-dialog>
    
    <!-- 版本历史对话框 -->
    <el-dialog v-model="versionVisible" title="版本历史" width="700px">
      <el-timeline>
        <el-timeline-item
          v-for="version in versions"
          :key="version.id"
          :timestamp="version.createdAt"
          placement="top"
        >
          <el-card>
            <h4>版本 {{ version.version }}</h4>
            <p>字数：{{ version.wordCount }}</p>
            <p v-if="version.note">备注：{{ version.note }}</p>
            <el-button size="small" @click="previewVersion(version)">预览</el-button>
            <el-button size="small" type="primary" @click="restoreVersion(version)">恢复</el-button>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>

    <el-dialog v-model="exportDialogVisible" title="导出平台版本" width="860px">
      <div class="export-dialog-body">
        <el-alert
          title="选择要导出的平台版本"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        >
          <p>可以选择导出番茄版、七猫版，或同时导出双平台版本。</p>
        </el-alert>

        <el-radio-group v-model="exportTarget" size="large" class="export-target-group">
          <el-radio-button label="fanqiao">番茄版</el-radio-button>
          <el-radio-button label="qimao">七猫版</el-radio-button>
          <el-radio-button label="both">双平台</el-radio-button>
        </el-radio-group>

        <div class="export-meta" v-if="currentChapterNum">
          <el-tag type="info">第{{ currentChapterNum }}章</el-tag>
          <el-tag type="success" v-if="selectedNovelId">小说已选定</el-tag>
        </div>

        <div v-if="exportLoading" class="export-loading-state">
          <el-skeleton :rows="6" animated />
        </div>

        <el-empty
          v-else-if="!exportResults.length && !exportError"
          description="选择平台后点击“开始导出”，结果会显示在这里"
          :image-size="120"
        />

        <el-alert
          v-if="exportError"
          :title="exportError"
          type="error"
          :closable="false"
          show-icon
          style="margin-top: 16px"
        />

        <div v-if="exportResults.length" class="export-result-list">
          <el-card v-for="variant in exportResults" :key="variant.platform" class="export-result-card" shadow="never">
            <template #header>
              <div class="export-result-header">
                <div>
                  <span class="export-platform-title">{{ getExportPlatformLabel(variant.platform) }}</span>
                  <el-tag size="small" type="warning" style="margin-left: 8px">{{ variant.platform }}</el-tag>
                </div>
                <el-text type="info">{{ variant.title || chapterTitle || `第${currentChapterNum}章` }}</el-text>
              </div>
            </template>
            <el-input
              :model-value="variant.content"
              type="textarea"
              :rows="10"
              readonly
              resize="vertical"
            />
          </el-card>
        </div>
      </div>

      <template #footer>
        <el-button @click="exportDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="exportLoading" :disabled="!canExportCurrentChapter" @click="confirmExportChapter">
          {{ exportLoading ? '导出中...' : '开始导出' }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 新建小说对话框 -->
    <el-dialog v-model="newNovelVisible" title="新建小说" width="500px">
      <el-form :model="newNovelForm" label-width="80px">
        <el-form-item label="小说标题">
          <el-input v-model="newNovelForm.title" placeholder="请输入小说标题" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newNovelForm.genre" placeholder="选择类型" style="width: 100%">
            <el-option label="玄幻" value="fantasy" />
            <el-option label="武侠" value="wuxia" />
            <el-option label="言情" value="romance" />
            <el-option label="悬疑" value="mystery" />
            <el-option label="都市" value="urban" />
            <el-option label="历史" value="history" />
          </el-select>
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="newNovelForm.description" type="textarea" :rows="4" placeholder="小说简介" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newNovelVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreateNovel">创建</el-button>
      </template>
    </el-dialog>
    
    <!-- 小说设置对话框 -->
    <el-dialog v-model="settingsVisible" title="小说设置" width="500px">
      <el-form :model="novelSettings" label-width="80px">
        <el-form-item label="小说标题">
          <el-input v-model="novelSettings.title" placeholder="小说标题" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="novelSettings.genre" placeholder="选择类型" style="width: 100%">
            <el-option label="玄幻" value="fantasy" />
            <el-option label="武侠" value="wuxia" />
            <el-option label="言情" value="romance" />
            <el-option label="悬疑" value="mystery" />
            <el-option label="都市" value="urban" />
            <el-option label="历史" value="history" />
          </el-select>
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="novelSettings.description" type="textarea" :rows="4" placeholder="小说简介" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="novelSettings.status" style="width: 100%">
            <el-option label="连载中" value="ongoing" />
            <el-option label="已完成" value="completed" />
            <el-option label="暂停" value="paused" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpdateNovel">保存</el-button>
      </template>
    </el-dialog>

    <!-- 人物选择器对话框 -->
    <el-dialog v-model="characterSelectorVisible" title="选择人物" width="600px">
      <el-form :inline="true" style="margin-bottom: 15px">
        <el-form-item label="搜索">
          <el-input v-model="characterSearch" placeholder="搜索人物名称" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadNovelCharacters">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table
        :data="filteredNovelCharacters"
        style="width: 100%"
        max-height="300"
        @selection-change="handleCharacterSelection"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getRoleTagType(row.role)">
              {{ row.role || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" />
      </el-table>

      <template #footer>
        <el-button @click="characterSelectorVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddCharacters">添加所选</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { apiClient } from '@/api/client'
import { authorStyles, authorStyleMap, authorStyleGroups } from '@/constants/authorStyles'

// ========== 小说管理 ==========
const selectedNovelId = ref('')
const novels = ref([])
const newNovelVisible = ref(false)
const settingsVisible = ref(false)
const newNovelForm = reactive({
  title: '',
  genre: 'fantasy',
  description: ''
})
const novelSettings = reactive({
  title: '',
  genre: 'fantasy',
  description: '',
  status: 'ongoing'
})

// ========== 章节管理 ==========
const chapters = ref([])
const chapterSearch = ref('')
const currentChapterNum = ref(1)
const chapterTitle = ref('')
const chapterOutline = ref('')
const chapterContent = ref('')
const editorMode = ref('edit')

// ========== 创作设置 ==========
const wordCountTarget = ref(3000)
const selectedStyle = ref('default')
const selectedTechniques = ref([])
const stylePreview = ref(null)
const novelSettingsCache = ref(null)
const stylePreviewText = ref('')
const previewLoading = ref(false)
// 风格相关的本地状态（需要的引用/常量）
const STYLE_PRESETS_KEY = 'writing_panel_style_presets'
const stylePresets = ref([])
const groupedStyleOptions = computed(() => authorStyleGroups ?? {})
const selectedStyleStrength = ref('medium')
const compareStyleIds = ref([])

const buildCreativeSettingsPayload = () => ({
  style_id: selectedStyle.value,
  strength: selectedStyleStrength.value,
  techniques: [...selectedTechniques.value],
  updated_at: new Date().toISOString()
})

// ========== 状态显示 ==========
const agentStatus = ref([])
const chapterCharacters = ref([])
const unresolvedHooks = ref(0)
const unresolvedHookList = ref([])
const todayCalls = ref(0)
const tokenUsed = ref(0)
const estimatedCost = ref(0)

// ========== 人物选择器 ==========
const characterSelectorVisible = ref(false)
const characterSearch = ref('')
const novelCharacters = ref([])
const selectedCharactersForAdd = ref([])

// ========== 创作流程 ==========
const writing = ref(false)
const creatingNextChapter = ref(false)
const progressVisible = ref(false)
const progress = ref(0)
const progressStatus = ref(null)
const currentStage = ref('')
const currentStep = ref(0)
const latestTaskId = ref('')
const logs = ref([])
const autoScroll = ref(true)

// ========== 版本管理 ==========
const versionVisible = ref(false)
const versions = ref([])

// ========== 导出 ==========
const exportDialogVisible = ref(false)
const exportTarget = ref('both')
const exportLoading = ref(false)
const exportResults = ref([])
const exportError = ref('')

// ========== 计算属性 ==========
const filteredChapters = computed(() => {
  if (!chapterSearch.value) return chapters.value
  const query = chapterSearch.value.toLowerCase()
  return chapters.value.filter(ch => 
    ch.title.toLowerCase().includes(query) ||
    String(ch.num).includes(query)
  )
})

const currentWordCount = computed(() => chapterContent.value.length)
const canExportCurrentChapter = computed(() => Boolean(selectedNovelId.value && currentChapterNum.value))

const totalChapters = computed(() => chapters.value.length)

const totalWords = computed(() => 
  chapters.value.reduce((sum, ch) => sum + (ch.wordCount || 0), 0)
)

const publishedChapters = computed(() => 
  chapters.value.filter(ch => ch.status === 'published').length
)

const draftChapters = computed(() => 
  chapters.value.filter(ch => ch.status === 'draft').length
)

const normalizeTaskStage = (text = '') => {
  return String(text)
    .replace(/\uFFFD/g, '')
    .replace(/Step\s*(\d)\/6/g, '阶段 $1/6')
    .trim()
}

const getWritingStageHint = (stage = '') => {
  const text = normalizeTaskStage(stage)
  if (text.includes('细化大纲')) return '正在细化本章剧情推进与冲突重点…'
  if (text.includes('准备角色')) return '正在整理本章出场人物与关系张力…'
  if (text.includes('撰写初稿')) return '正在写出章节正文初稿…'
  if (text.includes('打磨对话')) return '正在润色对话与潜台词表达…'
  if (text.includes('一致性')) return '正在检查世界观、人物和前后文一致性…'
  if (text.includes('最终审核')) return '正在做最终校订与收束…'
  if (text.includes('完成')) return '章节已完成，准备刷新写作面板。'
  return text || 'AI 正在处理中…'
}

const blueprintSummary = computed(() => {
  const settings = novelSettingsCache.value?.settings || {}
  const blueprint = settings.blueprint || {}
  const worldMap = settings.world_map || blueprint.world_map || {}
  const macroPlot = settings.macro_plot || blueprint.macro_plot || {}
  const characterSystem = settings.character_system || blueprint.character_system || {}
  const hookNetwork = settings.hook_network || blueprint.hook_network || {}

  const result = []

  if (Object.keys(worldMap).length) {
    result.push({
      title: '世界观地图',
      content: worldMap.background || worldMap.world_name || JSON.stringify(worldMap).slice(0, 180)
    })
  }

  if (Object.keys(macroPlot).length) {
    const firstVolume = macroPlot.volumes?.[0]
    result.push({
      title: '宏观规划',
      content: firstVolume
        ? `${firstVolume.volume_title || '第一卷'}：${firstVolume.main_goal || ''}`
        : JSON.stringify(macroPlot).slice(0, 180)
    })
  }

  if (Object.keys(characterSystem).length) {
    const protagonist = characterSystem.protagonist
    result.push({
      title: '人物体系',
      content: protagonist
        ? `${protagonist.name || '主角'}｜目标：${protagonist.goal || '未设定'}｜性格：${(protagonist.personality || []).join('、')}`
        : JSON.stringify(characterSystem).slice(0, 180)
    })
  }

  if (Object.keys(hookNetwork).length) {
    const firstHook = Object.values(hookNetwork).flat().find(Boolean)
    result.push({
      title: '伏笔网络',
      content: firstHook?.description || JSON.stringify(hookNetwork).slice(0, 180)
    })
  }

  return result
})

const renderedContent = computed(() => {
  return marked(chapterContent.value || '')
})

const availableStyles = ref(authorStyles)

const defaultAutoStyle = authorStyleMap.default

const availableTechniques = ref([
  { id: 'multi_thread', name: '多线交织' },
  { id: 'suspense', name: '悬念设置' },
  { id: 'contrast', name: '反差塑造' },
  { id: 'foreshadowing', name: '伏笔千里' },
  { id: 'pacing', name: '节奏控制' }
])

// ========== 人物选择器计算属性 ==========
const filteredNovelCharacters = computed(() => {
  if (!characterSearch.value) return novelCharacters.value
  const search = characterSearch.value.toLowerCase()
  return novelCharacters.value.filter(char =>
    char.name.toLowerCase().includes(search) ||
    (char.role && char.role.toLowerCase().includes(search))
  )
})

// ========== 方法 ==========

const loadNovels = async () => {
  try {
    const result = await apiClient.novels.list()
    if (result.data && result.data.novels) {
      novels.value = result.data.novels.map(novel => ({
        ...novel,
        chapterCount: novel.total_chapters || 0
      }))
    }
  } catch (error) {
    console.error('加载小说列表失败:', error)
    ElMessage.error('加载小说列表失败：' + error.message)
  }
}

const loadStylePresets = () => {
  try {
    const saved = localStorage.getItem(STYLE_PRESETS_KEY)
    stylePresets.value = saved ? JSON.parse(saved) : []
  } catch (error) {
    console.error('加载风格预设失败:', error)
    stylePresets.value = []
  }
}

const persistStylePresets = () => {
  localStorage.setItem(STYLE_PRESETS_KEY, JSON.stringify(stylePresets.value))
}

const syncStylePresetsToNovel = async () => {
  if (!selectedNovelId.value) return

  try {
    const baseSettings = novelSettingsCache.value?.settings || {}
    await apiClient.novels.update(selectedNovelId.value, {
      settings: {
        ...baseSettings,
        style_presets: stylePresets.value
      }
    })

    if (novelSettingsCache.value) {
      novelSettingsCache.value = {
        ...novelSettingsCache.value,
        settings: {
          ...baseSettings,
          style_presets: stylePresets.value
        }
      }
    }
  } catch (error) {
    console.error('同步小说风格预设失败:', error)
  }
}

const saveCurrentStylePreset = async () => {
  const style = availableStyles.value.find(item => item.id === selectedStyle.value)
  try {
    const { value } = await ElMessageBox.prompt('输入预设名称', '保存常用风格组合', {
      inputValue: `${style?.name || selectedStyle.value}-${selectedStyleStrength.value}`,
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    })
    stylePresets.value = [
      {
        id: `preset_${Date.now()}`,
        name: value,
        styleId: selectedStyle.value,
        strength: selectedStyleStrength.value
      },
      ...stylePresets.value.filter(item => item.name !== value)
    ].slice(0, 12)
    persistStylePresets()
    await syncStylePresetsToNovel()
    ElMessage.success('风格组合已保存')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('保存风格组合失败')
  }
}

const applyStylePreset = (preset) => {
  selectedStyle.value = preset.styleId
  selectedStyleStrength.value = preset.strength || 'medium'
  if (!compareStyleIds.value.includes(preset.styleId)) {
    compareStyleIds.value = [preset.styleId, ...compareStyleIds.value].slice(0, 4)
  }
  showStylePreview()
  syncNovelActiveStyle()
  ElMessage.success(`已应用预设：${preset.name}`)
}

const removeStylePreset = (presetId) => {
  stylePresets.value = stylePresets.value.filter(item => item.id !== presetId)
  persistStylePresets()
  syncStylePresetsToNovel()
}

const createNewNovel = () => {
  newNovelVisible.value = true
}

const confirmCreateNovel = async () => {
  if (!newNovelForm.title) {
    ElMessage.warning('请输入小说标题')
    return
  }
  
  try {
    const result = await apiClient.novels.create({
      title: newNovelForm.title,
      genre: newNovelForm.genre,
      description: newNovelForm.description
    })
    
    ElMessage.success('小说创建成功')
    newNovelVisible.value = false
    // 重置表单
    newNovelForm.title = ''
    newNovelForm.genre = 'fantasy'
    newNovelForm.description = ''
    
    // 重新加载小说列表
    await loadNovels()
  } catch (error) {
    ElMessage.error('创建失败：' + error.message)
  }
}

const editNovelSettings = async () => {
  if (!selectedNovelId.value) {
    ElMessage.warning('请先选择小说')
    return
  }
  
  try {
    const result = await apiClient.novels.get(selectedNovelId.value)
    if (result.data) {
      const novel = result.data
      novelSettings.title = novel.title
      novelSettings.genre = novel.genre || 'fantasy'
      novelSettings.description = novel.description || ''
      novelSettings.status = novel.status || 'ongoing'
      settingsVisible.value = true
    }
  } catch (error) {
    ElMessage.error('获取小说信息失败：' + error.message)
  }
}

const confirmUpdateNovel = async () => {
  if (!novelSettings.title) {
    ElMessage.warning('请输入小说标题')
    return
  }
  
  try {
    await apiClient.novels.update(selectedNovelId.value, {
      title: novelSettings.title,
      genre: novelSettings.genre,
      description: novelSettings.description,
      status: novelSettings.status
    })
    
    ElMessage.success('小说信息已更新')
    settingsVisible.value = false
    await loadNovels()
  } catch (error) {
    ElMessage.error('更新失败：' + error.message)
  }
}

const loadNovelData = async () => {
  if (!selectedNovelId.value) return
  
  addLog(`加载小说：${selectedNovelId.value}`)
  await loadNovelSettings()
  await loadChapters()
  await loadCharacters()
  await loadHooks()
  await loadNovelStats()

   if (chapters.value.length > 0 && !chapters.value.some(ch => ch.num === currentChapterNum.value)) {
     currentChapterNum.value = chapters.value[0].num
   }

   if (chapters.value.length > 0 && !chapterContent.value) {
     await handleChapterSelect(String(currentChapterNum.value || chapters.value[0].num))
   }
  
  // 保存到 localStorage
  saveCurrentState()
}

const loadNovelSettings = async () => {
  try {
    const result = await apiClient.novels.get(selectedNovelId.value)
    if (result.data) {
      novelSettingsCache.value = result.data
      const creativeSettings = result.data.settings?.creative_settings
      const novelPresetList = result.data.settings?.style_presets
      if (Array.isArray(novelPresetList) && novelPresetList.length > 0) {
        stylePresets.value = novelPresetList
        persistStylePresets()
        const defaultPreset = novelPresetList.find(item => item.isDefault)
        if (defaultPreset) {
          applyStylePreset(defaultPreset)
        }
      }
      const activeStyle = result.data.settings?.active_style
      if (creativeSettings?.style_id) {
        selectedStyle.value = creativeSettings.style_id
        selectedStyleStrength.value = creativeSettings.strength || 'medium'
        selectedTechniques.value = Array.isArray(creativeSettings.techniques) ? creativeSettings.techniques : []
      } else if (activeStyle?.style_id) {
        selectedStyle.value = activeStyle.style_id
        selectedStyleStrength.value = activeStyle.strength || 'medium'
        selectedTechniques.value = []
        stylePreview.value = {
          name: activeStyle.name || defaultAutoStyle.name,
          description: activeStyle.description || defaultAutoStyle.description,
          features: activeStyle.features || defaultAutoStyle.features,
          forbidden: activeStyle.forbidden || defaultAutoStyle.forbidden || [],
          toneExample: activeStyle.tone_example || activeStyle.toneExample || defaultAutoStyle.toneExample
        }
      }
    }
  } catch (error) {
    console.error('加载小说设置失败:', error)
  }
}

const saveCurrentState = () => {
  const state = {
    selectedNovelId: selectedNovelId.value,
    currentChapterNum: currentChapterNum.value,
    chapterTitle: chapterTitle.value,
    chapterOutline: chapterOutline.value,
    chapterContent: chapterContent.value,
    wordCountTarget: wordCountTarget.value,
    selectedStyle: selectedStyle.value,
    selectedStyleStrength: selectedStyleStrength.value,
    selectedTechniques: [...selectedTechniques.value],
    timestamp: Date.now()
  }
  localStorage.setItem('writing_panel_state', JSON.stringify(state))
}

const restoreState = () => {
  const saved = localStorage.getItem('writing_panel_state')
  if (saved) {
    try {
      const state = JSON.parse(saved)
      // 检查是否是同一本小说
      if (state.selectedNovelId && novels.value.find(n => n.id === state.selectedNovelId)) {
        selectedNovelId.value = state.selectedNovelId
        currentChapterNum.value = state.currentChapterNum || 1
        chapterTitle.value = state.chapterTitle || ''
        chapterOutline.value = state.chapterOutline || ''
        chapterContent.value = state.chapterContent || ''
        wordCountTarget.value = state.wordCountTarget || 3000
        selectedStyle.value = state.selectedStyle || 'default'
        selectedStyleStrength.value = state.selectedStyleStrength || 'medium'
        selectedTechniques.value = state.selectedTechniques || []
        addLog(`已恢复上次创作状态`)
        
        // 加载小说数据
        loadNovelData().then(async () => {
          if (state.fromAutoCreation && state.selectedNovelId) {
            try {
              await handleChapterSelect(String(state.currentChapterNum || 1))
              addLog('已按全自动创作路线加载首章与蓝图上下文')
            } catch (error) {
              console.error('恢复全自动创作首章失败:', error)
            }
          }
        })
      }
    } catch (e) {
      console.error('恢复状态失败:', e)
    }
  }
}

const loadChapters = async () => {
  try {
    const result = await apiClient.novels.getChapters(selectedNovelId.value)
    if (result.data && result.data.chapters) {
      chapters.value = result.data.chapters.map(ch => ({
        num: ch.chapter_num,
        title: ch.title || `第${ch.chapter_num}章`,
        status: ch.status || 'draft',
        wordCount: ch.word_count || 0,
        updatedAt: ch.updated_at
      }))
    }
  } catch (error) {
    console.error('加载章节失败:', error)
    ElMessage.error('加载章节失败：' + error.message)
  }
}

const buildChapterContinuationSummary = (chapter = {}) => {
  const content = chapter.content || ''
  if (!content) return ''

  const start = content.slice(0, 160).trim()
  const end = content.slice(-220).trim()

  if (start && end && start !== end) {
    return `${start}\n……\n${end}`
  }

  return (start || end).trim()
}

const buildFallbackOutline = (newNum, recentChapters = []) => {
  const latest = recentChapters[recentChapters.length - 1]
  if (!latest) {
    return `第${newNum}章必须承接上一章结尾，推进新的冲突、发现或后果，不能重复上一章已经发生的主事件。`
  }

  const latestTitle = latest.title || `第${latest.chapter_num}章`
  const latestSummary = buildChapterContinuationSummary(latest)
  return [
    `第${newNum}章必须紧接${latestTitle}的结尾继续发展。`,
    '必须描写上一章事件带来的新后果、新目标或新冲突。',
    latestSummary ? `最近一章关键信息：${latestSummary}` : '',
    '禁止重复上一章已经发生的主事件，本章至少推进一个新的剧情节点。'
  ].filter(Boolean).join('\n')
}

const saveChapterSilently = async () => {
  if (!selectedNovelId.value || !currentChapterNum.value) return null
  if (!chapterContent.value && !chapterOutline.value && !chapterTitle.value) return null

  return await apiClient.novels.updateChapter(selectedNovelId.value, currentChapterNum.value, {
    content: chapterContent.value,
    title: chapterTitle.value,
    outline: chapterOutline.value,
    status: 'draft'
  })
}

const syncCurrentChapterToList = (overrides = {}) => {
  const targetNum = overrides.num || currentChapterNum.value
  if (!targetNum) return

  const existingIndex = chapters.value.findIndex(ch => ch.num === targetNum)
  const chapterItem = {
    num: targetNum,
    title: overrides.title ?? (chapterTitle.value || `第${targetNum}章`),
    status: overrides.status ?? 'draft',
    wordCount: overrides.wordCount ?? currentWordCount.value,
    updatedAt: overrides.updatedAt ?? new Date().toISOString()
  }

  if (existingIndex >= 0) {
    chapters.value[existingIndex] = {
      ...chapters.value[existingIndex],
      ...chapterItem
    }
  } else {
    chapters.value.push(chapterItem)
    chapters.value.sort((a, b) => a.num - b.num)
  }
}

const createNewChapter = async () => {
  try {
    const newNum = Math.max(0, ...chapters.value.map(c => c.num)) + 1
    
    // 调用 API 创建章节
    const result = await apiClient.novels.createChapter(selectedNovelId.value, {
      chapter_num: newNum,
      title: '',
      outline: ''
    })
    
    currentChapterNum.value = newNum
    chapterTitle.value = ''
    chapterOutline.value = ''
    chapterContent.value = ''
    
    // 刷新章节列表
    await loadChapters()
    addLog(`创建新章节：第${newNum}章`)
    ElMessage.success('章节创建成功')
  } catch (error) {
    ElMessage.error('创建章节失败：' + error.message)
  } finally {
    creatingNextChapter.value = false
  }
}

const deleteChapter = async (chapter) => {
  if (!selectedNovelId.value) return

  try {
    await ElMessageBox.confirm(
      `确定删除第${chapter.num}章吗？删除后无法恢复。`,
      '确认删除章节',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await apiClient.novels.deleteChapter(selectedNovelId.value, chapter.num)
    addLog(`删除章节：第${chapter.num}章`)

    if (currentChapterNum.value === chapter.num) {
      const fallback = chapters.value.filter(c => c.num !== chapter.num).slice(-1)[0]
      currentChapterNum.value = fallback?.num || 1
      chapterTitle.value = ''
      chapterOutline.value = ''
      chapterContent.value = ''
    }

    await loadChapters()
    if (chapters.value.length > 0 && chapters.value.some(c => c.num === currentChapterNum.value)) {
      await handleChapterSelect(String(currentChapterNum.value))
    }
    ElMessage.success('章节已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除章节失败：' + (error.message || '未知错误'))
    }
  }
}

const handleChapterSelect = async (index) => {
  const num = parseInt(index)
  currentChapterNum.value = num
  
  try {
    const result = await apiClient.novels.getChapter(selectedNovelId.value, num)
    if (result.data) {
      const chapter = result.data
      chapterTitle.value = chapter.title || `第${num}章`
      chapterOutline.value = chapter.outline || ''
      chapterContent.value = chapter.content || ''
      addLog(`加载章节：第${num}章 (${chapter.word_count || 0}字)`)
    }
  } catch (error) {
    console.error('加载章节失败:', error)
    ElMessage.error('加载章节失败：' + error.message)
  }
}

const startWriting = async (options = {}) => {
  const { skipOutlineValidation = false } = options

  if (!skipOutlineValidation && !chapterOutline.value) {
    ElMessage.warning('请先输入本章大纲')
    return false
  }
  
  if (!selectedNovelId.value) {
    ElMessage.warning('请先选择小说')
    return false
  }
  
  writing.value = true
  progressVisible.value = true
  progress.value = 0
  currentStep.value = 0
  currentStage.value = '提交创作任务...'
  latestTaskId.value = ''
  
  addLog(`开始创作第${currentChapterNum.value}章`)
  addLog(`目标字数：${wordCountTarget.value}`)
  
  try {
    // 提交创作任务，获取 task_id
      const result = await apiClient.writing.createChapter({
        novel_id: selectedNovelId.value,
        chapter_num: currentChapterNum.value,
        outline: chapterOutline.value,
        word_count_target: wordCountTarget.value,
        style: selectedStyle.value,
        style_context: {
          ...(authorStyleMap[selectedStyle.value] || defaultAutoStyle),
          strength: selectedStyleStrength.value,
          techniques: [...selectedTechniques.value]
        },
        creative_settings: buildCreativeSettingsPayload()
      })
    
    if (!result.data || !result.data.task_id) {
      throw new Error(result.message || '任务提交失败')
    }
    
    const taskId = result.data.task_id
    latestTaskId.value = taskId
    addLog(`任务已提交，task_id: ${taskId}`)
    currentStage.value = 'AI 正在创作中...'
    
    // 轮询任务进度
    const pollInterval = 3000 // 每3秒轮询一次
    const maxPolls = 2400 // 最多轮询2小时，写作以大模型写完为准
    
    for (let i = 0; i < maxPolls; i++) {
      await new Promise(resolve => setTimeout(resolve, pollInterval))
      
      const statusResult = await apiClient.writing.getTaskStatus(taskId)
      
      if (!statusResult.data) {
        continue
      }
      
      const taskData = statusResult.data
      const taskStatus = taskData.status
      const taskProgress = taskData.progress || 0
      const currentStageText = normalizeTaskStage(taskData.current_stage || '')
      
      // 更新进度
      progress.value = taskProgress
      if (currentStageText) {
        currentStage.value = currentStageText
      }
      
      if (taskStatus === 'completed') {
        // 任务完成
        progress.value = 100
        progressStatus.value = 'success'
        currentStage.value = '创作完成！'
        addLog('✅ 章节创作完成')
        ElMessage.success(`第${currentChapterNum.value}章创作完成，已自动保存并刷新列表。`)
        
        // 如果有内容预览，显示
        if (taskData.result && taskData.result.content) {
          chapterContent.value = taskData.result.content
          chapterTitle.value = chapterTitle.value || `第${currentChapterNum.value}章`
          syncCurrentChapterToList({
            title: chapterTitle.value,
            wordCount: taskData.result.word_count || chapterContent.value.length,
            updatedAt: new Date().toISOString()
          })
          addLog(`生成字数：${taskData.result.word_count || chapterContent.value.length}字`)
        }
        
        // 自动保存
        await saveChapter()
        await loadChapters()
        
        // 保存下一章交接棒到 localStorage
        if (taskData.result && taskData.result.next_chapter_baton) {
          const batonState = JSON.parse(localStorage.getItem('writing_panel_state') || '{}')
          batonState.next_chapter_baton = taskData.result.next_chapter_baton
          batonState.chapter_plan = taskData.result.chapter_plan
          batonState.review_packet = taskData.result.review_packet
          batonState.character_state_packet = taskData.result.character_state_packet
          localStorage.setItem('writing_panel_state', JSON.stringify(batonState))
          addLog('✓ 已保存下一章交接信息')
        }
        
        setTimeout(() => {
          progressVisible.value = false
        }, 2000)
        return true
      } else if (taskStatus === 'failed') {
        // 任务失败
        progressStatus.value = 'exception'
        currentStage.value = taskData.error || '创作失败'
        addLog('❌ 创作失败：' + (taskData.error || '未知错误'))
        ElMessage.error((taskData.error || '创作失败') + '。如需排查，可记录任务编号后到任务监控查看。')
        
        setTimeout(() => {
          progressVisible.value = false
        }, 2000)
        return false
      } else if (taskStatus === 'cancelled') {
        // 任务取消
        progressStatus.value = 'exception'
        currentStage.value = '创作已取消'
        addLog('❌ 创作已取消')
        ElMessage.warning('创作已取消')
        
        setTimeout(() => {
          progressVisible.value = false
        }, 2000)
        return false
      }
      // 否则继续轮询 (pending 或 running)
    }
    
    // 如果超过最大轮询次数
    if (progress.value < 100 && progressStatus.value !== 'exception') {
      progressStatus.value = 'exception'
      currentStage.value = '创作超时'
      addLog('❌ 创作超时，请稍后查看任务状态')
      ElMessage.warning('创作耗时较长，任务仍可能在后台继续。你可以关闭弹窗后稍后回来查看。')
      
      setTimeout(() => {
        progressVisible.value = false
      }, 2000)
      return false
    }
  } catch (error) {
    progressStatus.value = 'exception'
    currentStage.value = '创作失败'
    addLog('❌ 创作失败：' + error.message)
    ElMessage.error('创作失败：' + error.message + '。建议保留任务编号便于继续排查。')
    
    setTimeout(() => {
      progressVisible.value = false
    }, 2000)
    return false
  } finally {
    writing.value = false
  }
}

const continueWriting = async () => {
  // 自动创建下一章并自动生成大纲后直接开始创作
  creatingNextChapter.value = true
  try {
    const previousChapterNum = currentChapterNum.value
    if (chapterContent.value || chapterOutline.value || chapterTitle.value) {
      await saveChapterSilently()
      addLog(`续写前已保存第${previousChapterNum}章，确保使用最新上下文`)
    }

    await loadChapters()
    const newNum = Math.max(0, ...chapters.value.map(c => c.num)) + 1

    await apiClient.novels.createChapter(selectedNovelId.value, {
      chapter_num: newNum,
      title: '',
      outline: ''
    })
    
    currentChapterNum.value = newNum
    chapterTitle.value = `第${newNum}章`
    chapterOutline.value = ''
    chapterContent.value = ''

    await loadChapters()

    const recentChapterNums = chapters.value
      .filter(c => c.num < newNum)
      .slice(-3)
      .map(c => c.num)

    const recentChapterDetails = await Promise.all(
      recentChapterNums.map(async (num) => {
        try {
          const chapterResult = await apiClient.novels.getChapter(selectedNovelId.value, num)
          const data = chapterResult.data || {}
          return {
            chapter_num: num,
            title: data.title || `第${num}章`,
            outline: data.outline || '',
            content_summary: buildChapterContinuationSummary(data),
            content: data.content || ''
          }
        } catch {
          return null
        }
      })
    )
    const validRecentChapters = recentChapterDetails.filter(Boolean)
    
    // 读取上一章的交接棒
    const savedState = JSON.parse(localStorage.getItem('writing_panel_state') || '{}')
    const nextChapterBaton = savedState.next_chapter_baton || null
    const prevChapterPlan = savedState.chapter_plan || null
    const prevReviewPacket = savedState.review_packet || null
    const prevCharacterState = savedState.character_state_packet || null
    
    addLog(`正在为第${newNum}章自动生成大纲...`)
    const prevChaptersSummary = validRecentChapters
      .map(c => `第${c.chapter_num}章：${c.title || '无题'}\n${c.content_summary || '无摘要'}`)
      .join('\n\n')

    const activeStyle = availableStyles.value.find(s => s.id === selectedStyle.value)
      || novelSettingsCache.value?.settings?.active_style
      || defaultAutoStyle
    
    try {
      const result = await apiClient.ai.generateChapterOutline({
        novel_title: novels.value.find(n => n.id === selectedNovelId.value)?.title || '',
        chapter_num: newNum,
        overall_outline: novelSettingsCache.value?.description || prevChaptersSummary,
        next_chapter_baton: nextChapterBaton,
        context: {
          novel_description: novelSettingsCache.value?.description || '',
          recent_chapters: validRecentChapters,
          active_style: activeStyle || defaultAutoStyle,
          known_characters: chapterCharacters.value.map(char => ({ name: char.name, role: char.role })),
          unresolved_hooks: unresolvedHookList.value.map(hook => ({ description: hook.description, hook_type: hook.type })),
          prev_chapter_plan: prevChapterPlan,
          prev_review_packet: prevReviewPacket,
          prev_character_state: prevCharacterState
        }
      })
      if (result.data && result.data.outline) {
        chapterOutline.value = result.data.outline
        const titleMatch = result.data.outline.match(/(?:本章标题|标题)[：: ]+(.+)/)
        const extractedTitle = titleMatch?.[1]?.split('\n')[0]?.trim()
        if (extractedTitle) {
          chapterTitle.value = extractedTitle
          syncCurrentChapterToList({
            num: newNum,
            title: extractedTitle,
            wordCount: 0,
            updatedAt: new Date().toISOString()
          })
          addLog(`✅ 已自动提取第${newNum}章标题：${extractedTitle}`)
        }
        addLog(`✅ 已自动生成第${newNum}章大纲`)
      } else {
        chapterOutline.value = buildFallbackOutline(newNum, validRecentChapters)
        chapterTitle.value = `第${newNum}章`
        syncCurrentChapterToList({
          num: newNum,
          title: chapterTitle.value,
          wordCount: 0,
          updatedAt: new Date().toISOString()
        })
        addLog(`⚠️ 大纲生成失败，使用默认大纲`)
      }
    } catch (e) {
      chapterOutline.value = buildFallbackOutline(newNum, validRecentChapters)
      chapterTitle.value = `第${newNum}章`
      syncCurrentChapterToList({
        num: newNum,
        title: chapterTitle.value,
        wordCount: 0,
        updatedAt: new Date().toISOString()
      })
      addLog(`⚠️ 大纲自动生成失败，使用默认大纲`)
      addLog(`大纲生成失败原因：${e.message || '未知错误'}`)
    }
    
    addLog(`正在自动开始第${newNum}章创作...`)
    ElMessage.success(`第${newNum}章已创建，正在自动创作（已承接最新章节上下文）`) 
    await startWriting({ skipOutlineValidation: true })
  } catch (error) {
    ElMessage.error('创建章节失败：' + error.message)
  } finally {
    creatingNextChapter.value = false
  }
}

const handleProgressClose = () => {
  addLog('已关闭创作进度弹窗，任务继续在后台运行')
}

const saveChapter = async () => {
  try {
    const result = await apiClient.novels.updateChapter(selectedNovelId.value, currentChapterNum.value, {
      content: chapterContent.value,
      title: chapterTitle.value,
      outline: chapterOutline.value,
      status: 'draft'
    })
    if (result.data) {
      chapterTitle.value = result.data.title || chapterTitle.value
      chapterOutline.value = result.data.outline || chapterOutline.value
      chapterContent.value = result.data.content || chapterContent.value
      syncCurrentChapterToList({
        title: result.data.title || chapterTitle.value,
        wordCount: result.data.word_count || chapterContent.value.length,
        status: result.data.status || 'draft',
        updatedAt: result.data.updated_at || new Date().toISOString()
      })
    }
    addLog(`保存章节：第${currentChapterNum.value}章 (${currentWordCount.value}字)`)
    ElMessage.success('章节已保存')
    
    // 刷新章节列表
    await loadChapters()
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  }
}

const getExportPlatformLabel = (platform) => {
  if (platform === 'fanqiao') return '番茄导出版本'
  if (platform === 'qimao') return '七猫导出版本'
  return platform || '导出版本'
}

const exportChapter = () => {
  if (!canExportCurrentChapter.value) {
    ElMessage.warning('请先选择小说和章节')
    return
  }
  exportDialogVisible.value = true
  exportError.value = ''
  exportResults.value = []
}

const confirmExportChapter = async () => {
  if (!selectedNovelId.value || !currentChapterNum.value) {
    ElMessage.warning('请先选择小说和章节')
    return
  }

  exportLoading.value = true
  exportError.value = ''
  exportResults.value = []
  addLog(`开始导出第${currentChapterNum.value}章，目标：${exportTarget.value}`)

  try {
    const result = await apiClient.novels.exportChapter(selectedNovelId.value, currentChapterNum.value, {
      target: exportTarget.value
    })
    const variants = result.data?.variants || []
    exportResults.value = variants
    addLog(`导出完成：返回 ${variants.length} 个平台版本`)
    ElMessage.success('导出完成')
  } catch (error) {
    exportError.value = error.response?.data?.detail || error.message || '导出失败'
    addLog(`导出失败：${exportError.value}`)
    ElMessage.error(`导出失败：${exportError.value}`)
  } finally {
    exportLoading.value = false
  }
}

const showStylePreview = () => {
  const style = availableStyles.value.find(s => s.id === selectedStyle.value)
  if (style) {
    stylePreview.value = {
      name: style.name,
      description: style.description,
      features: style.features,
      forbidden: style.forbidden || [],
      toneExample: style.toneExample
    }
  } else {
    stylePreview.value = null
  }
}

const generateStylePreview = async () => {
  try {
    previewLoading.value = true
    const result = await apiClient.ai.generateStylePreview({
      style_id: selectedStyle.value,
      strength: selectedStyleStrength.value,
      prompt_seed: `${chapterTitle.value || '测试章节'}：${chapterOutline.value || '少年在雨夜独自踏上修炼之路，前方危机四伏。'}`
    })
    stylePreviewText.value = result.data?.preview || ''
    ElMessage.success('风格试写生成成功')
  } catch (error) {
    ElMessage.error('风格试写失败：' + (error.response?.data?.detail || error.message))
  } finally {
    previewLoading.value = false
  }
}

const generateComparePreviews = async () => {
  try {
    compareLoading.value = true
    const compareStyles = compareStyleIds.value
      .filter((value, index, arr) => arr.indexOf(value) === index)
      .slice(0, 4)

    if (compareStyles.length < 2) {
      ElMessage.warning('请至少选择 2 个风格进行对比')
      return
    }

    const results = await Promise.all(
      compareStyles.map(async (styleId) => {
        const result = await apiClient.ai.generateStylePreview({
          style_id: styleId,
          strength: selectedStyleStrength.value,
          prompt_seed: `${chapterTitle.value || '测试章节'}：${chapterOutline.value || '少年在雨夜独自踏上修炼之路，前方危机四伏。'}`
        })
        return {
          styleId,
          styleName: result.data?.style_name || styleId,
          preview: result.data?.preview || ''
        }
      })
    )

    comparePreviewCards.value = results
    ElMessage.success('多风格对比试写生成成功')
  } catch (error) {
    ElMessage.error('多风格对比试写失败：' + (error.response?.data?.detail || error.message))
  } finally {
    compareLoading.value = false
  }
}

const syncNovelActiveStyle = async () => {
  if (!selectedNovelId.value) return

  try {
    const baseSettings = novelSettingsCache.value?.settings || {}
    const styleConfig = availableStyles.value.find(s => s.id === selectedStyle.value)
      || defaultAutoStyle

    if (!styleConfig) return

    const resolvedStyleConfig = {
      ...(authorStyleMap[styleConfig.id] || defaultAutoStyle),
      strength: selectedStyleStrength.value
    }

    await apiClient.novels.update(selectedNovelId.value, {
      settings: {
        ...baseSettings,
        active_style: resolvedStyleConfig,
        creative_settings: buildCreativeSettingsPayload()
      }
    })

    if (novelSettingsCache.value) {
      novelSettingsCache.value = {
        ...novelSettingsCache.value,
        settings: {
          ...baseSettings,
          active_style: resolvedStyleConfig,
          creative_settings: buildCreativeSettingsPayload()
        }
      }
    }
  } catch (error) {
    console.error('同步小说风格失败:', error)
  }
}

const addCharacter = () => {
  if (!selectedNovelId.value) {
    ElMessage.warning('请先选择小说')
    return
  }
  characterSelectorVisible.value = true
  selectedCharactersForAdd.value = []
  loadNovelCharacters()
}

const loadNovelCharacters = async () => {
  try {
    const result = await apiClient.novels.getCharacters(selectedNovelId.value)
    if (result.data && result.data.characters) {
      novelCharacters.value = result.data.characters.map(c => ({
        id: c.id,
        name: c.name,
        role: c.role || 'unknown',
        description: c.description || ''
      }))
    }
  } catch (error) {
    console.error('加载小说人物列表失败:', error)
    ElMessage.error('加载人物列表失败')
  }
}

const handleCharacterSelection = (selection) => {
  selectedCharactersForAdd.value = selection
}

const confirmAddCharacters = () => {
  if (selectedCharactersForAdd.value.length === 0) {
    ElMessage.warning('请选择要添加的人物')
    return
  }

  for (const char of selectedCharactersForAdd.value) {
    const exists = chapterCharacters.value.find(c => c.id === char.id)
    if (!exists) {
      chapterCharacters.value.push({
        id: char.id,
        name: char.name,
        role: char.role
      })
    }
  }

  ElMessage.success(`已添加 ${selectedCharactersForAdd.value.length} 个人物`)
  characterSelectorVisible.value = false
}

const getRoleTagType = (role) => {
  if (!role) return 'info'
  const roleMap = {
    'protagonist': 'danger',
    'main': 'danger',
    'antagonist': 'warning',
    'villain': 'warning',
    'supporting': 'success',
    'secondary': 'success',
    'minor': 'info'
  }
  return roleMap[role.toLowerCase()] || 'info'
}

const removeCharacter = (id) => {
  chapterCharacters.value = chapterCharacters.value.filter(c => c.id !== id)
}

const loadCharacters = async () => {
  try {
    const result = await apiClient.novels.getCharacters(selectedNovelId.value)
    if (result.data && result.data.characters) {
      chapterCharacters.value = result.data.characters.map(c => ({
        id: c.id,
        name: c.name,
        role: c.role
      }))
    }
  } catch (error) {
    console.error('加载人物失败:', error)
  }
}

const loadHooks = async () => {
  try {
    const result = await apiClient.novels.getHooks(selectedNovelId.value)
    if (result.data && result.data.hooks) {
      unresolvedHooks.value = result.data.total
      unresolvedHookList.value = result.data.hooks.map(h => ({
        id: h.id,
        description: h.description,
        type: h.hook_type,
        chapterIntroduced: h.chapter_introduced
      }))
    }
  } catch (error) {
    console.error('加载伏笔失败:', error)
  }
}

const loadNovelStats = async () => {
  try {
    const result = await apiClient.novels.get(selectedNovelId.value)
    if (result.data && result.data.stats) {
      const stats = result.data.stats
      todayCalls.value = 15 // 这个需要后端实现 API 调用统计
      tokenUsed.value = stats.total_words || 0
      estimatedCost.value = (stats.total_words || 0) * 0.00001 // 估算
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const addLog = (message) => {
  logs.value.push({
    time: new Date().toLocaleTimeString(),
    message
  })
  
  if (logs.value.length > 100) {
    logs.value.shift()
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
}

// 自动保存 + 持久化
let autoSaveTimer = null
watch([selectedNovelId, currentChapterNum, chapterTitle, chapterOutline, chapterContent, wordCountTarget, selectedStyle, selectedStyleStrength, selectedTechniques], () => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    // 保存到 localStorage
    saveCurrentState()
    
    // 如果有内容，保存到数据库
    if (!writing.value && !creatingNextChapter.value && (chapterContent.value || chapterOutline.value)) {
      saveChapter()
      addLog('自动保存成功')
    }
  }, 5000) // 5 秒自动保存
}, { deep: true })

watch([selectedStyle, selectedStyleStrength], () => {
  showStylePreview()
  syncNovelActiveStyle()
})

watch(selectedTechniques, () => {
  syncNovelActiveStyle()
}, { deep: true })

watch(selectedStyle, () => {
  showStylePreview()
  syncNovelActiveStyle()
})

onMounted(() => {
  loadStylePresets()
  loadNovels()
  addLog('写作面板已就绪')
  
  // 恢复上次的状态
  setTimeout(() => {
    restoreState()
  }, 500)
  
  // 定时刷新 Agent 状态
  setInterval(async () => {
    try {
      const result = await apiClient.agents.getStatus()
      if (result.data && result.data.agents) {
        agentStatus.value = result.data.agents.map(a => ({
          name: a.agent_id.replace('_agent', ''),
          status: a.state
        }))
      }
    } catch (error) {
      console.error('加载 Agent 状态失败:', error)
    }
  }, 5000)
})
</script>

<style scoped>
.writing-panel {
  width: 100%;
  max-width: none;
}

.blueprint-card {
  margin-bottom: 20px;
}

.blueprint-summary-card {
  margin-bottom: 12px;
  min-height: 120px;
  background: #fafcff;
  border: 1px solid #e6f4ff;
}

.blueprint-summary-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}

.blueprint-summary-content {
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
}

.novel-selector-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chapters-card {
  height: fit-content;
  max-height: calc(100vh - 400px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.chapters-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.chapters-list {
  flex: 1;
  overflow-y: auto;
  margin: 0 -4px;
  padding: 0 4px;
}

.chapter-card {
  position: relative;
  padding: 12px;
  margin-bottom: 8px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chapter-card:hover {
  background: #f0f7ff;
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

.chapter-card.chapter-active {
  background: #e6f4ff;
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
}

.chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.chapter-num {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.chapter-title-text {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.chapter-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.chapter-words {
  font-weight: 500;
}

.chapter-date {
  font-size: 11px;
}

.chapter-delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 6px;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.chapter-card:hover .chapter-delete-btn {
  opacity: 1;
}

.outline-section, .content-section {
  margin-bottom: 15px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: bold;
}

.section-actions {
  display: flex;
  gap: 10px;
}

.content-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}

.word-count {
  display: flex;
  align-items: center;
  color: #666;
}

.actions {
  display: flex;
  gap: 10px;
}

.style-preview {
  margin-top: 10px;
}

.compare-preview-card {
  margin-top: 8px;
}

.compare-preview-title {
  font-weight: 600;
}

.compare-preview-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 13px;
  color: #303133;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.hook-item {
  margin-bottom: 10px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
}

.hook-item p {
  margin: 5px 0;
}

.log-container {
  max-height: 200px;
  overflow-y: auto;
  font-size: 12px;
  font-family: 'Courier New', monospace;
}

.log-item {
  margin-bottom: 5px;
  display: flex;
  gap: 10px;
}

.log-time {
  color: #909399;
  white-space: nowrap;
}

.log-message {
  color: #333;
}

.preview-content {
  min-height: 400px;
  padding: 15px;
  background: #fafafa;
  border: 1px solid #eee;
  border-radius: 4px;
  line-height: 1.8;
}

.stats-card, .agent-status-card, .characters-card, .hooks-card, .token-stats-card, .log-card {
  font-size: 13px;
}
</style>
