<template>
  <div class="firmware-flasher-page">
    <el-card class="flasher-card">
      <template #header>
        <div class="card-header">
          <h2>🔧 ESP32 固件烧录工具</h2>
          <p class="subtitle">通过浏览器一键烧录固件，无需安装任何软件</p>
        </div>
      </template>

      <!-- 警告提示 -->
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 20px;"
      >
        <template #title>
          <strong>重要提示</strong>
        </template>
        <div>
          <p style="margin: 0 0 8px 0;">
            <strong>🔒 必须使用 HTTPS 访问本页面</strong>
          </p>
          <p style="margin: 0 0 8px 0;">
            <strong>🌐 浏览器要求：</strong>Chrome (≥89)、Edge (≥89) 或 Opera
          </p>
          <p style="margin: 0;">
            <strong>🔌 连接要求：</strong>使用 USB 数据线（非充电线）连接设备
          </p>
        </div>
      </el-alert>

      <!-- 连接状态 -->
      <div class="status-section">
        <el-card :class="['status-card', { connected: isConnected }]">
          <div class="status-indicator">
            <div class="status-dot"></div>
            <span class="status-text">
              {{ isConnected ? `已连接 - ${chipInfo}` : '未连接设备' }}
            </span>
          </div>
        </el-card>
      </div>

      <!-- 连接控制 -->
      <div class="control-section">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-button 
              type="primary" 
              size="large"
              style="width: 100%;"
              :disabled="isConnected"
              @click="handleConnect"
            >
              <el-icon><Link /></el-icon>
              连接设备
            </el-button>
          </el-col>
          <el-col :span="12">
            <el-button 
              size="large"
              style="width: 100%;"
              :disabled="!isConnected"
              @click="handleDisconnect"
            >
              <el-icon><Close /></el-icon>
              断开连接
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 固件选择 -->
      <el-card class="firmware-selector-card" shadow="never">
        <template #header>
          <div class="section-title">
            <el-icon><FolderOpened /></el-icon>
            <span>选择固件版本</span>
          </div>
        </template>

        <div class="firmware-card-list">
          <div
            v-for="firmware in firmwareList"
            :key="firmware.id"
            class="firmware-card-item"
            :class="{ 'is-selected': selectedFirmwareId === firmware.id }"
            @click="selectedFirmwareId = firmware.id; handleSelectFirmware(firmware.id)"
          >
            <div class="firmware-card-radio">
              <el-radio :model-value="selectedFirmwareId" :label="firmware.id" @change="() => {}" />
            </div>
            <div class="firmware-card-body">
              <div class="firmware-card-header">
                <span class="firmware-card-name">{{ firmware.name }}</span>
                <el-tag size="small" type="primary">{{ firmware.version }}</el-tag>
              </div>
              <div class="firmware-card-desc">{{ firmware.description }}</div>
              <div class="firmware-card-meta">
                <span><el-icon><Calendar /></el-icon> {{ firmware.date }}</span>
                <span><el-icon><Files /></el-icon> {{ firmware.size }}</span>
              </div>
            </div>
          </div>
        </div>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 15px;"
        >
          💡 固件文件已部署在服务器上，选择一个版本后点击"开始烧录"即可
        </el-alert>
      </el-card>

      <!-- 操作按钮 -->
      <div class="action-section">
        <el-button 
          type="primary" 
          size="large"
          style="width: 100%;"
          :disabled="!isConnected || !selectedFirmware || isFlashing"
          :loading="isFlashing"
          @click="handleFlash"
        >
          <el-icon v-if="!isFlashing"><Upload /></el-icon>
          {{ isFlashing ? '烧录中...' : '开始烧录' }}
        </el-button>
      </div>

      <!-- 进度条 -->
      <div v-if="isFlashing" class="progress-section">
        <el-progress 
          :percentage="Math.round(flashProgress)" 
          :status="flashProgress === 100 ? 'success' : undefined"
          :stroke-width="20"
        />
      </div>

      <!-- 日志面板 -->
      <el-card class="log-panel" shadow="never">
        <template #header>
          <div class="section-title">
            <el-icon><Document /></el-icon>
            <span>操作日志</span>
            <el-button 
              size="small" 
              text 
              style="margin-left: auto;"
              @click="clearLogs"
            >
              清空日志
            </el-button>
          </div>
        </template>
        
        <div class="log-container" ref="logContainerRef">
          <div 
            v-for="(log, index) in logs" 
            :key="index"
            :class="['log-item', `log-${log.type}`]"
          >
            <span class="log-time">{{ log.timestamp }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          <div v-if="logs.length === 0" class="log-empty">
            暂无日志信息
          </div>
        </div>
      </el-card>

      <!-- 使用提示 -->
      <el-card class="tips-panel" shadow="never">
        <template #header>
          <div class="section-title">
            <el-icon><InfoFilled /></el-icon>
            <span>使用提示</span>
          </div>
        </template>
        
        <div class="tips-content">
          <div class="tip-item">
            <el-icon class="tip-icon" color="#F56C6C"><Check /></el-icon>
            <div>
              <strong>1. 安全协议要求（重要！）：</strong>
              <p>必须通过 <strong>HTTPS</strong> 访问本页面</p>
              <p style="margin-top: 5px; color: #f56c6c;">
                ⚠️ 如果使用 HTTP 协议，Web Serial API 将不可用
              </p>
            </div>
          </div>
          <div class="tip-item">
            <el-icon class="tip-icon" color="#409EFF"><Check /></el-icon>
            <div>
              <strong>2. 浏览器要求：</strong>
              <p>必须使用 Chrome (≥89)、Edge (≥89) 或 Opera 浏览器</p>
              <p style="margin-top: 5px; color: #909399;">
                Firefox、Safari 等浏览器暂不支持 Web Serial API
              </p>
            </div>
          </div>
          <div class="tip-item">
            <el-icon class="tip-icon" color="#67C23A"><Check /></el-icon>
            <div>
              <strong>3. 连接设备：</strong>
              <p>使用 USB 数据线（非充电线）连接 ESP32 设备到电脑，点击"连接设备"按钮</p>
            </div>
          </div>
          <div class="tip-item">
            <el-icon class="tip-icon" color="#E6A23C"><Check /></el-icon>
            <div>
              <strong>4. 选择固件：</strong>
              <p>从下拉列表中选择要烧录的固件版本</p>
            </div>
          </div>
          <div class="tip-item">
            <el-icon class="tip-icon" color="#9C27B0"><Check /></el-icon>
            <div>
              <strong>5. 开始烧录：</strong>
              <p>点击"开始烧录"按钮，等待烧录完成（约2-3分钟），设备会自动重启</p>
            </div>
          </div>
        </div>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Link, Close, FolderOpened, Upload,
  Document, InfoFilled, Check, Calendar, Files
} from '@element-plus/icons-vue'

// 状态
const isConnected = ref(false)
const chipInfo = ref(null)
const selectedFirmwareId = ref('')
const selectedFirmware = ref(null)
const isFlashing = ref(false)
const flashProgress = ref(0)
const logs = ref([])
const logContainerRef = ref(null)

// ESP烧录器相关
let esploader = null
let transport = null

// 固件列表配置
const firmwareList = ref([
  {
    id: 'esp32s3-lite-v1.7',
    name: 'ESP32-S3-Lite',
    version: 'v1.7',
    filename: '/firmware/ESP32-S3-Lite-01-v1.7.bin',
    size: '约 6.1 MB',
    date: '2025-12-23',
    description: '轻量版本，适用于基础传感器和控制场景',
    address: '0x0'
  },
  {
    id: 'esp32s3-rain-v1.7',
    name: 'ESP32-S3-Rain',
    version: 'v1.7',
    filename: '/firmware/ESP32-S3-Rain-01-v1.7.bin',
    size: '约 6.1 MB',
    date: '2025-03-18',
    description: '雨量传感器专用版本，支持雨量检测功能',
    address: '0x0'
  }
])

// 添加日志
const addLog = (message, type = 'info') => {
  const timestamp = new Date().toLocaleTimeString('zh-CN')
  logs.value.push({
    timestamp,
    message,
    type
  })
  // 自动滚动到底部
  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
    }
  })
}

// 清空日志
const clearLogs = () => {
  logs.value = []
}

// 动态加载 esptool-js
const loadESPTool = async () => {
  try {
    // 使用动态导入
    const module = await import('esptool-js')
    return module
  } catch (error) {
    addLog(`❌ 加载 esptool-js 失败: ${error.message}`, 'error')
    throw error
  }
}

// 连接设备
const handleConnect = async () => {
  try {
    addLog('🔍 正在请求串口访问权限...')
    
    const { ESPLoader, Transport } = await loadESPTool()
    
    // 请求串口访问
    const port = await navigator.serial.requestPort({
      filters: [
        { usbVendorId: 0x303a }, // Espressif
        { usbVendorId: 0x10c4 }, // Silicon Labs (CP210x)
        { usbVendorId: 0x1a86 }, // QinHeng Electronics (CH340)
      ]
    })
    
    transport = new Transport(port, true)
    
    // 创建ESPLoader实例
    esploader = new ESPLoader({
      transport: transport,
      baudrate: 115200,
      terminal: {
        clean() { },
        writeLine(data) { 
          if (data.trim()) console.log(data)
        },
        write(data) { 
          if (data.trim()) console.log(data)
        }
      }
    })

    const chip = await esploader.main()
    isConnected.value = true
    chipInfo.value = chip
    addLog(`✅ 连接成功！芯片: ${chip}`, 'success')
    ElMessage.success('设备连接成功')
  } catch (error) {
    addLog(`❌ 连接失败: ${error.message}`, 'error')
    ElMessage.error(`连接失败: ${error.message}`)
    console.error(error)
  }
}

// 断开连接
const handleDisconnect = async () => {
  try {
    if (transport) {
      await transport.disconnect()
      await transport.waitForUnlock(500)
      transport = null
      esploader = null
    }
    isConnected.value = false
    chipInfo.value = null
    addLog('🔌 已断开连接', 'success')
    ElMessage.success('已断开连接')
  } catch (error) {
    addLog(`⚠️ 断开连接时出错: ${error.message}`, 'error')
    ElMessage.warning('断开连接时出错')
  }
}

// 选择固件
const handleSelectFirmware = () => {
  const firmware = firmwareList.value.find(f => f.id === selectedFirmwareId.value)
  if (firmware) {
    selectedFirmware.value = firmware
    addLog(`📦 已选择固件: ${firmware.name}`)
  }
}

// 烧录固件
const handleFlash = async () => {
  if (!isConnected.value) {
    ElMessage.error('请先连接设备！')
    return
  }

  if (!selectedFirmware.value) {
    ElMessage.error('请选择固件版本！')
    return
  }

  try {
    isFlashing.value = true
    flashProgress.value = 0
    addLog(`⚡ 开始烧录固件: ${selectedFirmware.value.name}...`)
    
    // 从服务器下载固件文件
    const response = await fetch(selectedFirmware.value.filename)
    if (!response.ok) {
      throw new Error(`下载固件失败: ${response.status} ${response.statusText}`)
    }
    
    const firmwareData = await response.arrayBuffer()
    const address = parseInt(selectedFirmware.value.address, 16)
    
    // 将 ArrayBuffer 转换为字符串（esptool-js 需要）
    const uint8Array = new Uint8Array(firmwareData)
    let binaryString = ''
    for (let i = 0; i < uint8Array.length; i++) {
      binaryString += String.fromCharCode(uint8Array[i])
    }
    
    const fileArray = [{
      data: binaryString,
      address: address
    }]

    // 执行烧录
    await esploader.writeFlash({
      fileArray: fileArray,
      flashSize: 'keep',
      eraseAll: false,
      compress: true,
      reportProgress: (fileIndex, written, total) => {
        const percent = (written / total) * 100
        flashProgress.value = percent
        if (percent % 10 < 1) { // 每10%记录一次
          addLog(`💾 烧录进度: ${Math.round(percent)}%`)
        }
      }
    })
    
    flashProgress.value = 100
    addLog('🎉 固件烧录完成！', 'success')
    ElMessage.success('固件烧录完成！')
    
    // 尝试重启设备
    try {
      addLog('🔄 正在重启设备...')
      await esploader.hardReset()
      addLog('✅ 设备已重启！', 'success')
    } catch (resetError) {
      addLog('⚠️ 自动重启失败，请手动重启设备', 'error')
      console.error('Reset error:', resetError)
    }
    
    setTimeout(() => {
      isFlashing.value = false
      flashProgress.value = 0
    }, 3000)
  } catch (error) {
    addLog(`❌ 烧录失败: ${error.message}`, 'error')
    ElMessage.error(`烧录失败: ${error.message}`)
    console.error(error)
    isFlashing.value = false
    flashProgress.value = 0
  }
}


// 检查浏览器支持
onMounted(() => {
  // 检查是否为安全上下文（HTTPS 或 localhost）
  const isSecureContext = window.isSecureContext
  const protocol = window.location.protocol
  const hostname = window.location.hostname
  
  addLog(`🌐 当前协议: ${protocol}`, 'info')
  addLog(`🏠 当前主机: ${hostname}`, 'info')
  addLog(`🔒 安全上下文: ${isSecureContext ? '是' : '否'}`, isSecureContext ? 'success' : 'error')
  
  if (!('serial' in navigator)) {
    addLog('❌ 检测失败：浏览器不支持 Web Serial API', 'error')
    
    // 提供详细的诊断信息
    if (!isSecureContext) {
      addLog('⚠️ 原因：当前页面不是安全上下文（HTTPS）', 'error')
      addLog('💡 解决方案：', 'info')
      
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        addLog('   - 当前是 localhost，但使用了 HTTP 协议', 'info')
        addLog('   - 请确保服务器配置正确', 'info')
      } else {
        addLog('   - 必须通过 HTTPS 访问本页面', 'info')
        addLog(`   - 当前地址: ${window.location.href}`, 'info')
        addLog(`   - 建议地址: https://${hostname}${window.location.port ? ':' + window.location.port : ''}${window.location.pathname}`, 'info')
      }
      
      ElMessage({
        message: 'Web Serial API 需要 HTTPS 协议！请使用 HTTPS 访问。',
        type: 'error',
        duration: 8000,
        showClose: true
      })
    } else {
      addLog('⚠️ 请使用 Chrome (≥89)、Edge (≥89) 或 Opera 浏览器', 'error')
      addLog(`   当前浏览器: ${navigator.userAgent}`, 'info')
      
      ElMessage({
        message: '您的浏览器不支持 Web Serial API，请使用 Chrome 或 Edge 浏览器',
        type: 'error',
        duration: 5000,
        showClose: true
      })
    }
  } else {
    addLog('✅ Web Serial API 可用', 'success')
    addLog('✅ 准备就绪，请连接 ESP32 设备并点击"连接设备"', 'success')
    addLog(`📋 已加载 ${firmwareList.value.length} 个固件版本`, 'success')
  }
})
</script>

<style scoped lang="scss">
.firmware-flasher-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.flasher-card {
  .card-header {
    text-align: center;
    
    h2 {
      margin: 0 0 8px 0;
      font-size: 24px;
      color: #333;
    }
    
    .subtitle {
      margin: 0;
      font-size: 14px;
      color: #666;
    }
  }
}

.status-section {
  margin-bottom: 20px;
  
  .status-card {
    background: #f5f7fa;
    border: 2px solid #e4e7ed;
    transition: all 0.3s;
    
    &.connected {
      background: #f0f9ff;
      border-color: #67c23a;
    }
    
    :deep(.el-card__body) {
      padding: 15px;
    }
    
    .status-indicator {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .status-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #f56c6c;
        animation: pulse 2s infinite;
      }
      
      .status-text {
        font-size: 15px;
        font-weight: 500;
        color: #606266;
      }
    }
    
    &.connected .status-dot {
      background: #67c23a;
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.control-section {
  margin-bottom: 20px;
}

.firmware-selector-card {
  margin-bottom: 20px;
  
  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }
  
  .firmware-card-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .firmware-card-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    border: 2px solid #e4e7ed;
    border-radius: 8px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;

    &:hover {
      border-color: #a0cfff;
      background: #f5f9ff;
    }

    &.is-selected {
      border-color: #409eff;
      background: #ecf5ff;
    }

    .firmware-card-radio {
      padding-top: 2px;
      flex-shrink: 0;
    }

    .firmware-card-body {
      flex: 1;
      min-width: 0;
    }

    .firmware-card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }

    .firmware-card-name {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
    }

    .firmware-card-desc {
      font-size: 13px;
      color: #606266;
      margin-bottom: 8px;
    }

    .firmware-card-meta {
      display: flex;
      gap: 16px;
      font-size: 12px;
      color: #909399;

      span {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }
}

.action-section {
  margin-bottom: 20px;
}

.progress-section {
  margin-bottom: 20px;
}

.log-panel {
  margin-bottom: 20px;
  
  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }
  
  .log-container {
    max-height: 300px;
    overflow-y: auto;
    background: #f5f7fa;
    border-radius: 4px;
    padding: 10px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    
    .log-item {
      padding: 5px 0;
      border-bottom: 1px solid #e4e7ed;
      
      &:last-child {
        border-bottom: none;
      }
      
      .log-time {
        color: #909399;
        margin-right: 10px;
      }
      
      .log-message {
        color: #606266;
      }
      
      &.log-success .log-message {
        color: #67c23a;
      }
      
      &.log-error .log-message {
        color: #f56c6c;
      }
      
      &.log-warning .log-message {
        color: #e6a23c;
      }
    }
    
    .log-empty {
      text-align: center;
      color: #909399;
      padding: 20px;
    }
  }
}

.tips-panel {
  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }
  
  .tips-content {
    .tip-item {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .tip-icon {
        flex-shrink: 0;
        margin-top: 2px;
      }
      
      strong {
        display: block;
        margin-bottom: 5px;
        color: #303133;
      }
      
      p {
        margin: 0;
        color: #606266;
        font-size: 14px;
        line-height: 1.6;
      }
    }
  }
}
</style>

