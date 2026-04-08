import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const root = path.resolve(process.cwd(), 'frontend', 'src', 'views')

function readView(name) {
  return fs.readFileSync(path.join(root, name), 'utf8')
}

test('Dashboard does not bind el-statistic value directly to string apiStatus', () => {
  const content = readView('Dashboard.vue')
  assert.ok(!content.includes('<el-statistic title="API 状态" :value="apiStatus">'))
})

test('NovelLibrary checkbox does not use array v-model on single el-checkbox', () => {
  const content = readView('NovelLibrary.vue')
  assert.ok(!content.includes('<el-checkbox \n                v-model="selectedNovels"'))
  assert.ok(!content.includes('<el-checkbox\r\n                v-model="selectedNovels"'))
})

test('WritingPanel defines handleProgressClose when dialog close handler is used', () => {
  const content = readView('WritingPanel.vue')
  assert.ok(content.includes('@close="handleProgressClose"'))
  assert.ok(content.includes('const handleProgressClose = ('))
})

test('WritingPanel blocks continuing when current chapter content is empty', () => {
  const content = readView('WritingPanel.vue')
  assert.ok(content.includes(':disabled="cannotContinueToNextChapter"'))
  assert.ok(content.includes('const cannotContinueToNextChapter = computed('))
  assert.match(content, /ElMessage\.warning\(['"]请先完成当前章节内容，再续写下一章['"]\)/)
})
