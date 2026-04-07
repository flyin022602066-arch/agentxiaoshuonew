<template>
  <div class="auto-creation">
    <h2>🤖 全自动 AI 创作</h2>
    
    <el-alert
      title="一键创作完整小说"
      type="success"
      :closable="false"
      show-icon
      style="margin-bottom: 20px"
    >
      <p>你只需要提供：</p>
      <ul>
        <li>✅ 书名</li>
        <li>✅ 类型</li>
        <li>✅ 一句话简介</li>
      </ul>
      <p>AI 会自动生成：</p>
      <ul>
        <li>✅ 完整世界观地图（大地图包小地图）</li>
        <li>✅ 3000 章宏观规划（节奏/爽点/伏笔）</li>
        <li>✅ 人物体系（主角 + 配角 + 反派）</li>
        <li>✅ 伏笔网络（短/中/长/终极）</li>
        <li>✅ 第一章正文（3000 字）</li>
      </ul>
    </el-alert>
    
    <!-- 创作表单 -->
    <el-card class="creation-form-card">
      <template #header>
        <div class="card-header">
          <span>📝 基本信息</span>
        </div>
      </template>
      
      <el-form :model="form" label-width="100px" size="large">
        <el-form-item label="书名" required>
          <el-input 
            v-model="form.title" 
            placeholder="例如：都市修仙、绝世武神"
            clearable
          />
        </el-form-item>
        
        <el-form-item label="类型" required>
          <el-select v-model="form.genre" placeholder="选择类型" style="width: 100%">
            <el-option label="玄幻" value="玄幻" />
            <el-option label="仙侠" value="仙侠" />
            <el-option label="都市" value="都市" />
            <el-option label="历史" value="历史" />
            <el-option label="科幻" value="科幻" />
            <el-option label="游戏" value="游戏" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="简介" required>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="用一句话描述小说核心设定，例如：一个普通大学生意外获得修仙传承，在都市中修炼成长，最终登临巅峰"
          />
        </el-form-item>

        <el-form-item label="创作风格">
          <el-select v-model="form.auto_style_mode" filterable placeholder="搜索作家风格" style="width: 100%">
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
          <div style="margin-top: 8px; color: #909399; font-size: 13px; line-height: 1.6;">
            这里选择的是作家写作风格，会和写作面板里的风格保持一致。
          </div>
          <div style="margin-top: 8px;">
            <el-button size="small" @click="generateStylePreview" :loading="previewLoading">试写这个风格</el-button>
            <el-button size="small" @click="generateComparePreviews" :loading="compareLoading" style="margin-left: 8px;">多风格对比试写</el-button>
            <el-button size="small" @click="saveCurrentStylePreset" style="margin-left: 8px;">保存当前组合</el-button>
          </div>
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

          <div v-if="stylePresets.length" style="margin-top: 8px;">
            <div
              v-for="preset in stylePresets"
              :key="preset.id"
              style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;"
            >
              <el-tag
                :type="preset.isDefault ? 'success' : 'info'"
                @click="applyStylePreset(preset)"
                style="cursor: pointer;"
              >
                {{ preset.name }}
              </el-tag>
              <el-button size="small" text @click="renameStylePreset(preset)">重命名</el-button>
              <el-button size="small" text type="success" @click="setDefaultStylePreset(preset.id)">
                {{ preset.isDefault ? '默认中' : '设为默认' }}
              </el-button>
              <el-button size="small" text type="danger" @click="removeStylePreset(preset.id)">删除</el-button>
            </div>
          </div>
          <el-card v-if="selectedStyleOption" shadow="never" class="style-detail-card">
            <div class="style-detail-title">{{ selectedStyleOption.name }}</div>
            <div class="style-detail-desc">{{ selectedStyleOption.description }}</div>
            <div class="style-detail-row"><strong>特点：</strong>{{ selectedStyleOption.features.join('、') }}</div>
            <div class="style-detail-row"><strong>避免：</strong>{{ selectedStyleOption.forbidden.join('、') }}</div>
            <div class="style-detail-example">“{{ selectedStyleOption.toneExample }}”</div>
          </el-card>
        </el-form-item>

        <el-form-item label="风格强度">
          <el-segmented
            v-model="form.auto_style_strength"
            :options="styleStrengthOptions.map(item => ({ label: item.name, value: item.id }))"
          />
          <div style="margin-top: 8px; color: #909399; font-size: 13px; line-height: 1.6;">
            轻度更自然，中度更均衡，强烈会更明显贴近所选作家笔法。
          </div>
        </el-form-item>
        
        <el-form-item label="预计篇幅">
          <el-select v-model="form.chapter_count" style="width: 100%">
            <el-option label="1000 章 (短篇)" :value="1000" />
            <el-option label="2000 章 (中篇)" :value="2000" />
            <el-option label="3000 章 (长篇)" :value="3000" />
            <el-option label="5000 章 (超长篇)" :value="5000" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.chapter_count === 'custom'" label="自定义章节数" required>
          <el-input-number
            v-model="form.custom_chapter_count"
            :min="1"
            :max="10000"
            :step="100"
            controls-position="right"
            placeholder="请输入章节数"
            style="width: 100%"
          />
          <div style="margin-top: 8px; color: #909399; font-size: 13px;">
            请输入计划创作的总章节数，建议范围 100 ~ 5000 章。
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            size="large"
            @click="startCreation" 
            :loading="creating"
            style="width: 100%"
          >
            {{ creating ? 'AI 创作中...' : '🚀 开始全自动创作' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 创作进度 -->
    <el-dialog 
      v-model="progressVisible" 
      title="AI 创作中" 
      width="700px"
      :close-on-click-modal="false"
      :show-close="false"
    >
      <el-progress 
        :percentage="overallProgress" 
        :status="progressStatus"
        :stroke-width="20"
      />
      
      <el-steps direction="vertical" :active="currentStep" style="margin-top: 30px">
        <el-step 
          title="🌍 生成世界观地图" 
          :description="worldMapDesc"
        />
        <el-step 
          :title="`📋 生成 ${displayChapterCount} 章规划`" 
          :description="macroPlotDesc"
        />
        <el-step 
          title="👥 生成人物体系" 
          :description="characterDesc"
        />
        <el-step 
          title="🎣 生成伏笔网络" 
          :description="hookDesc"
        />
        <el-step 
          title="✍️ 创作第一章" 
          :description="chapterDesc"
        />
      </el-steps>
      
      <div class="progress-tips">
        <el-alert
          title="创作提示"
          type="info"
          :closable="false"
          show-icon
        >
          <p>• AI 正在使用专业模板进行创作</p>
          <p>• 整个过程约需 2-5 分钟</p>
          <p>• 请勿关闭页面</p>
        </el-alert>
      </div>
    </el-dialog>
    
    <!-- 创作结果 -->
    <el-dialog 
      v-model="resultVisible" 
      title="🎉 创作完成" 
      width="900px"
    >
      <el-result
        icon="success"
        title="创作成功"
        :sub-title="`小说《${resultData.novel?.title || form.title}》已创作完成！`"
      >
        <template #extra>
          <el-button type="primary" @click="viewNovel">查看小说</el-button>
          <el-button @click="viewBlueprint">查看蓝图</el-button>
        </template>
      </el-result>
      
      <el-divider />

      <el-alert
        title="下一步怎么做？"
        type="success"
        :closable="false"
        show-icon
      >
        <p><strong>推荐下一步：</strong>点击“查看小说”进入写作面板。</p>
        <p>进入后你会看到“全自动创作上下文”，然后可以直接点“续写下一章”。</p>
        <p>如果你想先核对设定，再看下方的世界观概览、章节规划和第一章预览。</p>
      </el-alert>

      <el-steps :active="3" finish-status="success" align-center style="margin: 20px 0 8px;">
        <el-step title="已生成蓝图" description="世界观、规划、人物、伏笔已生成" />
        <el-step title="已写完第一章" description="第一章正文已自动写入小说" />
        <el-step title="进入写作面板" description="查看小说后可继续续写第二章" />
      </el-steps>

      <el-row :gutter="12" style="margin: 16px 0 4px;">
        <el-col :span="8">
          <el-card shadow="hover" class="next-step-card">
            <div class="next-step-title">1. 查看小说</div>
            <div class="next-step-desc">进入写作面板，确认第一章和全自动上下文已接入。</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="next-step-card">
            <div class="next-step-title">2. 续写下一章</div>
            <div class="next-step-desc">系统会自动创建第二章、大纲，并参考蓝图继续创作。</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="next-step-card">
            <div class="next-step-title">3. 检查连贯性</div>
            <div class="next-step-desc">重点看第二章是否延续世界观、人物目标和伏笔。</div>
          </el-card>
        </el-col>
      </el-row>

      <h3>🎭 风格试写</h3>
      <el-input
        v-model="stylePreviewText"
        type="textarea"
        :rows="8"
        readonly
        placeholder="点击“试写这个风格”生成示例文本"
      />

      <el-row v-if="comparePreviewCards.length" :gutter="12" style="margin-top: 16px;">
        <el-col v-for="card in comparePreviewCards" :key="card.styleId" :span="8">
          <el-card shadow="hover" class="compare-preview-card">
            <template #header>
              <div class="compare-preview-title">{{ card.styleName }}</div>
            </template>
            <div class="compare-preview-content">{{ card.preview }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-divider />

      <h3>📊 生成统计</h3>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="小说 ID">
          {{ resultData.novel_id }}
        </el-descriptions-item>
        <el-descriptions-item label="类型">
          {{ form.genre }}
        </el-descriptions-item>
        <el-descriptions-item label="预计篇幅">
          {{ form.chapter_count === 'custom' ? `自定义：${form.custom_chapter_count}` : form.chapter_count }}章
        </el-descriptions-item>
        <el-descriptions-item label="创作时间">
          {{ creationTime }}秒
        </el-descriptions-item>
      </el-descriptions>
      
      <h3>🌍 世界观概览</h3>
      <el-input
        v-model="worldMapSummary"
        type="textarea"
        :rows="6"
        readonly
      />
      
      <h3>📋 章节规划</h3>
      <el-input
        v-model="macroPlotSummary"
        type="textarea"
        :rows="6"
        readonly
      />
      
      <h3>✍️ 第一章预览</h3>
      <el-input
        v-model="firstChapterPreview"
        type="textarea"
        :rows="10"
        readonly
      />
    </el-dialog>
    
    <!-- 蓝图查看对话框 -->
    <el-dialog 
      v-model="blueprintVisible" 
      title="📋 创作蓝图" 
      width="95%"
      top="5vh"
    >
      <div v-if="blueprintLoading" style="text-align: center; padding: 40px;">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <p style="margin-top: 16px; color: #909399;">加载蓝图数据...</p>
      </div>
      
      <div v-else-if="blueprintData" class="blueprint-container">
        <!-- 小说基本信息 -->
        <el-card class="blueprint-section" shadow="hover">
          <template #header>
            <div class="section-header">
              <span class="section-title">📚 小说信息</span>
            </div>
          </template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="书名">{{ blueprintData.novel?.title }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ blueprintData.novel?.genre }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ blueprintData.novel?.status }}</el-descriptions-item>
            <el-descriptions-item label="简介" :span="3">{{ blueprintData.novel?.description }}</el-descriptions-item>
            <el-descriptions-item label="章节数">{{ blueprintData.stats?.total_chapters || 0 }} 章</el-descriptions-item>
            <el-descriptions-item label="总字数">{{ blueprintData.stats?.total_words || 0 }} 字</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ blueprintData.novel?.created_at }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 世界观地图 -->
        <el-card v-if="blueprintData.novel?.settings?.world_map" class="blueprint-section" shadow="hover">
          <template #header>
            <div class="section-header">
              <span class="section-title">🌍 世界观地图</span>
            </div>
          </template>
          <div class="world-map-content">
            <h4>{{ blueprintData.novel.settings.world_map.world_name || '未命名世界' }}</h4>
            
            <div v-if="blueprintData.novel.settings.world_map.power_system" class="power-system">
              <strong>力量体系：</strong>{{ blueprintData.novel.settings.world_map.power_system.name }}
              <div class="power-levels">
                <el-tag v-for="(level, idx) in blueprintData.novel.settings.world_map.power_system.levels" :key="idx" size="small" style="margin-right: 8px;">
                  {{ level }}
                </el-tag>
              </div>
            </div>
            
            <div v-if="blueprintData.novel.settings.world_map.main_factions?.length" class="factions">
              <strong>主要势力：</strong>
              <el-tag v-for="faction in blueprintData.novel.settings.world_map.main_factions" :key="faction.name" style="margin-right: 8px; margin-bottom: 8px;">
                {{ faction.name }}
              </el-tag>
            </div>
            
            <div v-if="blueprintData.novel.settings.world_map.background" class="world-background">
              <strong>世界背景：</strong>
              <p>{{ blueprintData.novel.settings.world_map.background }}</p>
            </div>
          </div>
        </el-card>
        
        <!-- 人物体系 -->
        <el-card v-if="blueprintData.novel?.settings?.character_system" class="blueprint-section" shadow="hover">
          <template #header>
            <div class="section-header">
              <span class="section-title">👥 人物体系</span>
            </div>
          </template>
          <div class="character-content">
            <div v-if="blueprintData.novel.settings.character_system.protagonist" class="protagonist-info">
              <h4>🎯 主角：{{ blueprintData.novel.settings.character_system.protagonist.name }}</h4>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="年龄">{{ blueprintData.novel.settings.character_system.protagonist.age || '未知' }}</el-descriptions-item>
                <el-descriptions-item label="核心目标">{{ blueprintData.novel.settings.character_system.protagonist.goal || '未知' }}</el-descriptions-item>
                <el-descriptions-item label="性格" :span="2">
                  <el-tag v-for="p in blueprintData.novel.settings.character_system.protagonist.personality" :key="p" size="small" style="margin-right: 8px;">
                    {{ p }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="背景故事" :span="2">
                  {{ blueprintData.novel.settings.character_system.protagonist.background }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
            
            <div v-if="blueprintData.novel.settings.character_system.key_characters?.length" class="key-characters">
              <h4>重要配角</h4>
              <el-table :data="blueprintData.novel.settings.character_system.key_characters" stripe>
                <el-table-column prop="name" label="姓名" width="120" />
                <el-table-column prop="role" label="定位" width="120" />
                <el-table-column prop="description" label="描述" />
              </el-table>
            </div>
          </div>
        </el-card>
        
        <!-- 宏观规划 -->
        <el-card v-if="blueprintData.novel?.settings?.macro_plot" class="blueprint-section" shadow="hover">
          <template #header>
            <div class="section-header">
              <span class="section-title">📖 宏观规划</span>
              <el-tag size="small">共 {{ blueprintData.novel.settings.macro_plot.total_chapters }} 章</el-tag>
            </div>
          </template>
          <div class="macro-plot-content">
            <div v-if="blueprintData.novel.settings.macro_plot.rhythm_control" class="rhythm-control">
              <el-tag type="success" size="small">小高潮：{{ blueprintData.novel.settings.macro_plot.rhythm_control.small_climax }}</el-tag>
              <el-tag type="warning" size="small" style="margin-left: 8px;">中高峰：{{ blueprintData.novel.settings.macro_plot.rhythm_control.medium_climax }}</el-tag>
              <el-tag type="danger" size="small" style="margin-left: 8px;">大高潮：{{ blueprintData.novel.settings.macro_plot.rhythm_control.big_climax }}</el-tag>
            </div>
            
            <div v-if="blueprintData.novel.settings.macro_plot.volumes?.length" class="volumes-list">
              <h4>卷级规划（共 {{ blueprintData.novel.settings.macro_plot.volumes.length }} 卷）</h4>
              <el-collapse accordion>
                <el-collapse-item v-for="volume in blueprintData.novel.settings.macro_plot.volumes.slice(0, 12)" :key="volume.volume_num" :name="volume.volume_num">
                  <template #title>
                    <strong>{{ volume.volume_title }}</strong>
                    <span style="margin-left: 12px; color: #909399;">第 {{ volume.chapters }} 章</span>
                  </template>
                  <el-descriptions :column="2" border size="small">
                    <el-descriptions-item label="本卷目标">{{ volume.main_goal }}</el-descriptions-item>
                    <el-descriptions-item label="核心冲突">{{ volume.conflict }}</el-descriptions-item>
                  </el-descriptions>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </el-card>
        
        <!-- 伏笔网络 -->
        <el-card v-if="blueprintData.novel?.settings?.hook_network" class="blueprint-section" shadow="hover">
          <template #header>
            <div class="section-header">
              <span class="section-title">🎣 伏笔网络</span>
            </div>
          </template>
          <div class="hook-network-content">
            <el-row :gutter="16">
              <el-col v-if="blueprintData.novel.settings.hook_network.short_term?.length" :span="6">
                <el-statistic title="短期伏笔" :value="blueprintData.novel.settings.hook_network.short_term.length">
                  <template #suffix>个</template>
                </el-statistic>
              </el-col>
              <el-col v-if="blueprintData.novel.settings.hook_network.medium_term?.length" :span="6">
                <el-statistic title="中期伏笔" :value="blueprintData.novel.settings.hook_network.medium_term.length">
                  <template #suffix>个</template>
                </el-statistic>
              </el-col>
              <el-col v-if="blueprintData.novel.settings.hook_network.long_term?.length" :span="6">
                <el-statistic title="长期伏笔" :value="blueprintData.novel.settings.hook_network.long_term.length">
                  <template #suffix>个</template>
                </el-statistic>
              </el-col>
              <el-col v-if="blueprintData.novel.settings.hook_network.ultimate?.length" :span="6">
                <el-statistic title="终极谜团" :value="blueprintData.novel.settings.hook_network.ultimate.length">
                  <template #suffix>个</template>
                </el-statistic>
              </el-col>
            </el-row>
            
            <el-divider />
            
            <el-tabs>
              <el-tab-pane v-if="blueprintData.novel.settings.hook_network.short_term?.length" label="短期伏笔">
                <el-timeline>
                  <el-timeline-item v-for="(hook, idx) in blueprintData.novel.settings.hook_network.short_term" :key="idx" :timestamp="`第 ${hook.reveal_chapter} 章`" placement="top">
                    {{ hook.description }}
                  </el-timeline-item>
                </el-timeline>
              </el-tab-pane>
              <el-tab-pane v-if="blueprintData.novel.settings.hook_network.medium_term?.length" label="中期伏笔">
                <el-timeline>
                  <el-timeline-item v-for="(hook, idx) in blueprintData.novel.settings.hook_network.medium_term" :key="idx" :timestamp="`第 ${hook.reveal_chapter} 章`" placement="top">
                    {{ hook.description }}
                  </el-timeline-item>
                </el-timeline>
              </el-tab-pane>
              <el-tab-pane v-if="blueprintData.novel.settings.hook_network.long_term?.length" label="长期伏笔">
                <el-timeline>
                  <el-timeline-item v-for="(hook, idx) in blueprintData.novel.settings.hook_network.long_term" :key="idx" :timestamp="`第 ${hook.reveal_chapter} 章`" placement="top">
                    {{ hook.description }}
                  </el-timeline-item>
                </el-timeline>
              </el-tab-pane>
              <el-tab-pane v-if="blueprintData.novel.settings.hook_network.ultimate?.length" label="终极谜团">
                <el-timeline>
                  <el-timeline-item v-for="(hook, idx) in blueprintData.novel.settings.hook_network.ultimate" :key="idx" placement="top">
                    {{ hook.description }}
                  </el-timeline-item>
                </el-timeline>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
      </div>
      
      <div v-else style="text-align: center; padding: 40px; color: #909399;">
        暂无蓝图数据
      </div>
      
      <template #footer>
        <el-button @click="blueprintVisible = false">关闭</el-button>
        <el-button type="primary" @click="viewNovel">进入写作面板</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { apiClient } from '@/api/client'
import { authorStyles, authorStyleGroups, authorStyleMap, styleStrengthOptions } from '@/constants/authorStyles'

const router = useRouter()

const form = reactive({
  title: '',
  genre: '玄幻',
  description: '',
  chapter_count: 3000,
  custom_chapter_count: 3000,
  auto_style_mode: 'default',
  auto_style_strength: 'medium'
})

const styleOptions = authorStyles
const groupedStyleOptions = authorStyleGroups
const autoStyleMap = authorStyleMap

const creating = ref(false)
const progressVisible = ref(false)
const resultVisible = ref(false)
const overallProgress = ref(0)
const progressStatus = ref(null)
const currentStep = ref(0)
const autoTaskId = ref('')

const worldMapDesc = ref('等待开始...')
const macroPlotDesc = ref('等待开始...')
const characterDesc = ref('等待开始...')
const hookDesc = ref('等待开始...')
const chapterDesc = ref('等待开始...')

const resultData = ref({})
const blueprintVisible = ref(false)
const blueprintLoading = ref(false)
const blueprintData = ref(null)
const creationTime = ref(0)
const worldMapSummary = ref('')
const macroPlotSummary = ref('')
const firstChapterPreview = ref('')
const stylePreviewText = ref('')
const previewLoading = ref(false)
const compareLoading = ref(false)
const comparePreviewCards = ref([])
const stylePresets = ref([])
// Initialize with existing style IDs to avoid invalid selections
const compareStyleIds = ref(['default', 'wuxia_jinyong', 'wuxia_gulong'])

const startTime = ref(0)
const STYLE_PRESETS_KEY = 'author_style_presets'

const normalizeStageText = (text = '') => {
  return String(text)
    .replace(/\uFFFD/g, '')
    .replace(/Step\s*(\d)\/6/g, '阶段 $1/6')
    .trim()
}

const getAutoStageHint = (stage = '') => {
  const text = normalizeStageText(stage)
  if (text.includes('世界观')) return '正在搭建世界观与力量体系…'
  if (text.includes('蓝图') || text.includes('规划')) return '正在生成整书蓝图与卷级规划…'
  if (text.includes('人物')) return '正在梳理主角与关键人物关系…'
  if (text.includes('伏笔')) return '正在整理伏笔网络与后续悬念…'
  if (text.includes('第一章')) return '正在打磨第一章，请耐心等待…'
  if (text.includes('完成')) return '全自动创作已完成，可以进入写作面板继续续写。'
  return text || '任务已提交，正在排队执行…'
}

const displayChapterCount = computed(() => {
  return form.chapter_count === 'custom' ? form.custom_chapter_count : form.chapter_count
})

const selectedStyleOption = computed(() => {
  return styleOptions.find(style => style.id === form.auto_style_mode) || styleOptions[0]
})

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

const syncStylePresetsToNovel = async (novelId) => {
  if (!novelId) return

  try {
    const result = await apiClient.novels.get(novelId)
    const baseSettings = result.data?.settings || {}
    await apiClient.novels.update(novelId, {
      settings: {
        ...baseSettings,
        style_presets: stylePresets.value
      }
    })
  } catch (error) {
    console.error('自动创作页同步小说风格预设失败:', error)
  }
}

const loadPresetsFromNovel = async (novelId) => {
  if (!novelId) return
  try {
    const result = await apiClient.novels.get(novelId)
    const presetList = result.data?.settings?.style_presets
    if (Array.isArray(presetList) && presetList.length > 0) {
      stylePresets.value = presetList
      persistStylePresets()
      const defaultPreset = presetList.find(item => item.isDefault)
      if (defaultPreset) {
        applyStylePreset(defaultPreset)
      }
    }
  } catch (error) {
    console.error('加载小说级风格预设失败:', error)
    const status = error.response?.status
    ElMessage.warning(status >= 500
      ? '读取小说级风格预设失败，已回退为当前浏览器保存的本地预设。'
      : '读取小说级风格预设失败，已继续使用本地预设。')
  }
}

const saveCurrentStylePreset = async () => {
  const style = styleOptions.find(item => item.id === form.auto_style_mode)
  try {
    const { value } = await ElMessageBox.prompt('输入预设名称', '保存常用风格组合', {
      inputValue: `${style?.name || form.auto_style_mode}-${form.auto_style_strength}`,
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    })
    stylePresets.value = [
      {
        id: `preset_${Date.now()}`,
        name: value,
        styleId: form.auto_style_mode,
        strength: form.auto_style_strength
      },
      ...stylePresets.value.filter(item => item.name !== value)
    ].slice(0, 12)
    persistStylePresets()
    const savedState = localStorage.getItem('writing_panel_state')
    if (savedState) {
      const state = JSON.parse(savedState)
      if (state?.selectedNovelId) {
        await syncStylePresetsToNovel(state.selectedNovelId)
      }
    }
    ElMessage.success('风格组合已保存')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('保存风格组合失败')
  }
}

const applyStylePreset = (preset) => {
  form.auto_style_mode = preset.styleId
  form.auto_style_strength = preset.strength || 'medium'
  if (!compareStyleIds.value.includes(preset.styleId)) {
    compareStyleIds.value = [preset.styleId, ...compareStyleIds.value].slice(0, 4)
  }
  ElMessage.success(`已应用预设：${preset.name}`)
}

const removeStylePreset = (presetId) => {
  stylePresets.value = stylePresets.value.filter(item => item.id !== presetId)
  persistStylePresets()

  const savedState = localStorage.getItem('writing_panel_state')
  if (savedState) {
    try {
      const state = JSON.parse(savedState)
      if (state?.selectedNovelId) {
        syncStylePresetsToNovel(state.selectedNovelId)
      }
    } catch (error) {
      console.error('删除预设时读取最近小说失败:', error)
    }
  }
}

const renameStylePreset = async (preset) => {
  try {
    const { value } = await ElMessageBox.prompt('输入新的预设名称', '重命名风格预设', {
      inputValue: preset.name,
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    })
    stylePresets.value = stylePresets.value.map(item => item.id === preset.id ? { ...item, name: value } : item)
    persistStylePresets()
    const savedState = localStorage.getItem('writing_panel_state')
    if (savedState) {
      const state = JSON.parse(savedState)
      if (state?.selectedNovelId) {
        await syncStylePresetsToNovel(state.selectedNovelId)
      }
    }
    ElMessage.success('预设已重命名')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('重命名失败')
  }
}

const setDefaultStylePreset = (presetId) => {
  stylePresets.value = stylePresets.value.map(item => ({
    ...item,
    isDefault: item.id === presetId
  }))
  persistStylePresets()
  const savedState = localStorage.getItem('writing_panel_state')
  if (savedState) {
    try {
      const state = JSON.parse(savedState)
      if (state?.selectedNovelId) {
        syncStylePresetsToNovel(state.selectedNovelId)
      }
    } catch (error) {
      console.error('设置默认预设时读取最近小说失败:', error)
    }
  }
  ElMessage.success('已设为默认预设')
}

const generateStylePreview = async () => {
  try {
    previewLoading.value = true
    const result = await apiClient.ai.generateStylePreview({
      style_id: form.auto_style_mode,
      strength: form.auto_style_strength,
      prompt_seed: `${form.title || '未命名小说'}：${form.description || '少年在雨夜独自踏上修炼之路，前方危机四伏。'}`
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
          strength: form.auto_style_strength,
          prompt_seed: `${form.title || '未命名小说'}：${form.description || '少年在雨夜独自踏上修炼之路，前方危机四伏。'}`
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

const startCreation = async () => {
  // 验证输入
  if (!form.title) {
    ElMessage.warning('请输入书名')
    return
  }
  if (!form.description) {
    ElMessage.warning('请输入简介')
    return
  }
  if (form.chapter_count === 'custom' && (!form.custom_chapter_count || form.custom_chapter_count < 1)) {
    ElMessage.warning('请输入有效的自定义章节数')
    return
  }
  if (form.chapter_count === 'custom' && form.custom_chapter_count > 10000) {
    ElMessage.warning('自定义章节数不能超过 10000 章')
    return
  }
  
  creating.value = true
  progressVisible.value = true
  startTime.value = Date.now()
  overallProgress.value = 0
  progressStatus.value = null
  currentStep.value = 0
    worldMapDesc.value = '等待开始…'
    macroPlotDesc.value = '等待开始…'
    characterDesc.value = '等待开始…'
    hookDesc.value = '等待开始…'
    chapterDesc.value = '等待开始…'
  
  try {
    // 调用全自动创作 API
    const payload = {
      ...form,
      chapter_count: form.chapter_count === 'custom' ? form.custom_chapter_count : form.chapter_count,
      auto_style: {
        ...(autoStyleMap[form.auto_style_mode] || autoStyleMap.default),
        strength: form.auto_style_strength
      }
    }
    const result = await apiClient.auto.create(payload)

    if (!result.data?.task_id) {
      throw new Error(result.message || '创作任务提交失败')
    }

    autoTaskId.value = result.data.task_id
    overallProgress.value = 5
    worldMapDesc.value = '任务已提交，正在排队执行…'

    const pollInterval = 3000
    const maxPolls = 800

    for (let i = 0; i < maxPolls; i++) {
      await new Promise(resolve => setTimeout(resolve, pollInterval))
      const statusResult = await apiClient.auto.getTaskStatus(autoTaskId.value)
      const task = statusResult.data
      if (!task) continue

      overallProgress.value = task.progress || 0
      const stage = normalizeStageText(task.current_stage || '')
      const stageHint = getAutoStageHint(stage)

      if (stage.includes('世界观')) {
        currentStep.value = 0
        worldMapDesc.value = stageHint
      } else if (stage.includes('蓝图') || stage.includes('规划')) {
        currentStep.value = 1
        macroPlotDesc.value = stageHint
      } else if (stage.includes('人物')) {
        currentStep.value = 2
        characterDesc.value = stageHint
      } else if (stage.includes('伏笔')) {
        currentStep.value = 3
        hookDesc.value = stageHint
      } else if (stage.includes('第一章')) {
        currentStep.value = 4
        chapterDesc.value = stageHint
      }

      if (task.status === 'completed') {
        creationTime.value = Math.round((Date.now() - startTime.value) / 1000)
        resultData.value = task.result || {}

        if (task.result?.blueprint) {
          worldMapSummary.value = JSON.stringify(task.result.blueprint.world_map, null, 2).substring(0, 500) + '...'
          macroPlotSummary.value = JSON.stringify(task.result.blueprint.macro_plot, null, 2).substring(0, 500) + '...'
        }

        if (task.result?.first_chapter?.content) {
          firstChapterPreview.value = task.result.first_chapter.content.substring(0, 500) + '...'
        }

        overallProgress.value = 100
        progressStatus.value = 'success'
        chapterDesc.value = '第一章已完成，准备进入写作面板'

        setTimeout(() => {
          progressVisible.value = false
          resultVisible.value = true
          ElMessage.success('创作完成！建议立即点击“查看小说”，继续续写第二章。')
        }, 1000)
        return
      }

      if (task.status === 'failed') {
        throw new Error(task.error || '全自动创作失败')
      }
    }

    throw new Error('全自动创作超时，请稍后到任务监控查看进度')
    } catch (error) {
      console.error('创作失败:', error)
      progressStatus.value = 'exception'
      const backendMessage = error.response?.data?.error?.message || error.response?.data?.error?.details?.error || error.response?.data?.detail
      ElMessage.error('创作失败：' + (backendMessage || error.message) + '。可前往任务监控查看具体阶段。')
    
    setTimeout(() => {
      progressVisible.value = false
    }, 2000)
  } finally {
    creating.value = false
  }
}

const viewNovel = () => {
  const novelId = resultData.value?.novel_id
  if (novelId) {
    const existingState = JSON.parse(localStorage.getItem('writing_panel_state') || '{}')
    localStorage.setItem('writing_panel_state', JSON.stringify({
      ...existingState,
      selectedNovelId: novelId,
      currentChapterNum: 1,
      chapterTitle: '第一章',
      chapterOutline: '',
      chapterContent: resultData.value?.first_chapter?.content || '',
      selectedStyle: form.auto_style_mode,
      selectedStyleStrength: form.auto_style_strength,
      selectedTechniques: [],
      fromAutoCreation: true,
      autoBlueprintReady: true,
      timestamp: Date.now()
    }))
  }

  // 跳转到写作面板并自动选中刚创建的小说
  router.push('/writing')
}

const viewBlueprint = async () => {
  if (!resultData.value.novel_id) {
    ElMessage.warning('小说 ID 不存在，无法查看蓝图')
    return
  }
  
  blueprintLoading.value = true
  blueprintVisible.value = true
  
  try {
    const result = await apiClient.auto.getBlueprint(resultData.value.novel_id)
    if (result.success && result.data) {
      blueprintData.value = result.data
    } else {
      ElMessage.error('加载蓝图失败：' + (result.message || '未知错误'))
      blueprintVisible.value = false
    }
  } catch (error) {
    console.error('加载蓝图失败:', error)
    ElMessage.error('加载蓝图失败：' + error.message)
    blueprintVisible.value = false
  } finally {
    blueprintLoading.value = false
  }
}

loadStylePresets()

const lastNovelId = localStorage.getItem('writing_panel_state')
if (lastNovelId) {
  try {
    const state = JSON.parse(lastNovelId)
    if (state?.selectedNovelId) {
      loadPresetsFromNovel(state.selectedNovelId)
    }
  } catch (error) {
    console.error('读取最近小说失败:', error)
  }
}
</script>

<style scoped>
.auto-creation {
  width: 100%;
  max-width: none;
}

.creation-form-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-tips {
  margin-top: 20px;
}

.next-step-card {
  min-height: 110px;
  border-color: #d9ecff;
  background: #f8fbff;
}

.next-step-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.next-step-desc {
  color: #606266;
  line-height: 1.7;
  font-size: 13px;
}

.style-detail-card {
  margin-top: 12px;
  background: #fafafa;
  border-color: #ebeef5;
}

.style-detail-title {
  font-weight: 600;
  margin-bottom: 6px;
}

.style-detail-desc,
.style-detail-row,
.style-detail-example {
  font-size: 13px;
  line-height: 1.7;
  color: #606266;
  margin-top: 4px;
}

.style-detail-example {
  color: #303133;
  font-style: italic;
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

.progress-tips ul {
  margin: 10px 0;
  padding-left: 20px;
}

:deep(.el-step__description) {
  font-size: 13px;
  line-height: 1.6;
}

:deep(.el-result__title) {
  font-size: 20px;
}

:deep(.el-result__sub-title) {
  font-size: 14px;
}

.blueprint-container {
  max-height: 75vh;
  overflow-y: auto;
  padding-right: 8px;
}

.blueprint-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.world-map-content h4 {
  font-size: 18px;
  color: #409EFF;
  margin-bottom: 16px;
}

.power-system,
.factions,
.world-background {
  margin-bottom: 16px;
}

.power-levels {
  margin-top: 8px;
}

.world-background p {
  margin-top: 8px;
  line-height: 1.8;
  color: #606266;
}

.character-content h4 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 12px;
}

.protagonist-info {
  margin-bottom: 24px;
}

.key-characters h4 {
  margin-bottom: 12px;
}

.macro-plot-content {
  line-height: 1.8;
}

.rhythm-control {
  margin-bottom: 16px;
}

.volumes-list h4 {
  margin-bottom: 12px;
}

.hook-network-content {
  line-height: 1.8;
}
</style>
