<template>
  <div class="device-realtime-data-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack" type="text" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回设备列表
        </el-button>
        <div class="page-title">
          <h2>{{ device?.name || '设备' }} - 实时数据</h2>
          <div class="device-tags" v-if="device">
            <el-tag :type="device.is_online ? 'success' : 'danger'" size="small">
              {{ device.is_online ? '在线' : '离线' }}
            </el-tag>
            <el-tag type="info" size="small">UUID: {{ device.uuid }}</el-tag>
            <el-tag type="warning" size="small" v-if="lastRefreshTime">
              {{ lastRefreshTime }} 更新
            </el-tag>
          </div>
        </div>
      </div>
      <div class="header-right">
        <el-button :loading="loading" size="small" @click="loadRealtimeData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="page-content" v-if="device">
      <!-- 加载中 -->
      <div v-if="loading && !latestData" class="loading-placeholder">
        <el-skeleton :rows="2" animated />
      </div>

      <!-- 传感器数据卡片 -->
      <div class="sensor-cards" v-if="sensorDisplayItems.length > 0">
        <el-card
          v-for="item in sensorDisplayItems"
          :key="item.key"
          class="sensor-card"
          shadow="hover"
        >
          <div class="sensor-name">{{ item.displayName }}</div>
          <div class="sensor-value" :class="item.valueClass">{{ item.displayValue }}</div>
          <div class="sensor-time" v-if="latestTimestamp">
            {{ formatTime(latestTimestamp) }}
          </div>
        </el-card>
      </div>

      <!-- 无数据提示 -->
      <el-empty
        v-if="!loading && sensorDisplayItems.length === 0"
        description="暂无传感器数据"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { getDeviceRealtimeData, getDeviceProductConfig } from '@/api/device'
import { getDevicesWithProductInfo } from '@/api/device'
import logger from '../utils/logger'

const route = useRoute()
const router = useRouter()

const device = ref(null)
const productConfig = ref(null)
const loading = ref(false)
const latestData = ref(null)
const latestSensors = ref([])   // 原始 sensors 元数据数组
const latestTimestamp = ref(null)
const lastRefreshTime = ref('')

let refreshTimer = null

const deviceUuid = computed(() => route.params.uuid)

// 加载设备信息
const loadDeviceInfo = async () => {
  try {
    const response = await getDevicesWithProductInfo()
    if (response.data) {
      device.value = response.data.find(d => d.uuid === deviceUuid.value)
      if (!device.value) {
        ElMessage.error('设备不存在')
        goBack()
        return
      }
      await loadProductConfig(device.value.uuid)
    }
  } catch (error) {
    logger.error('加载设备信息失败:', error)
    ElMessage.error('加载设备信息失败')
  }
}

// 加载产品配置
const loadProductConfig = async (uuid) => {
  try {
    const response = await getDeviceProductConfig(uuid)
    if (response.data) {
      productConfig.value = response.data
      logger.info('产品配置加载成功:', response.data)
    }
  } catch (error) {
    logger.error('加载产品配置失败:', error)
    productConfig.value = { sensor_types: {}, control_ports: {} }
  }
}

// 加载实时数据
const loadRealtimeData = async () => {
  if (!deviceUuid.value) return
  loading.value = true
  try {
    const response = await getDeviceRealtimeData(deviceUuid.value, 1)
    if (response.data?.latest) {
      latestData.value = response.data.latest.data || {}
      latestSensors.value = response.data.latest.sensors || []
      latestTimestamp.value = response.data.latest.timestamp
      lastRefreshTime.value = new Date().toLocaleTimeString('zh-CN')
    } else {
      latestData.value = {}
      latestSensors.value = []
    }
  } catch (error) {
    logger.error('加载实时数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 格式化单个传感器值（用于产品配置和原始数据两种场景）
const formatSensorValue = (value, sensorType, unit) => {
  if (value === undefined || value === null) return '无数据'

  // 雨水传感器布尔值
  if ((sensorType || '').toUpperCase() === 'RAIN_SENSOR' && typeof value === 'boolean') {
    return value ? '有雨水 🌧️' : '无雨水 ☀️'
  }

  // 通用布尔值
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }

  // 数值
  if (typeof value === 'number') {
    const str = Number.isInteger(value) ? String(value) : value.toFixed(1)
    return unit ? `${str} ${unit}` : str
  }

  return unit ? `${value} ${unit}` : String(value)
}

// 计算要展示的传感器列表（产品配置优先，否则回退到原始数据）
const sensorDisplayItems = computed(() => {
  const hasProductSensors = productConfig.value?.sensor_types &&
    Object.keys(productConfig.value.sensor_types).length > 0

  if (hasProductSensors) {
    // 有产品配置：按产品配置渲染，优先使用 data_field 从 raw data 中取值
    return Object.entries(productConfig.value.sensor_types)
      .filter(([, cfg]) => cfg.enabled !== false)
      .map(([key, cfg]) => {
        // 取值策略：1) 产品配置key直接命中  2) data_field命中  3) 模糊匹配
        let value = latestData.value?.[key]
        if (value === undefined && cfg.data_field) {
          value = latestData.value?.[cfg.data_field]
        }
        if (value === undefined) {
          const lk = key.toLowerCase()
          for (const dk in (latestData.value || {})) {
            if (dk.toLowerCase().includes(lk) || lk.includes(dk.toLowerCase())) {
              value = latestData.value[dk]
              break
            }
          }
        }

        // 获取自定义显示名称
        const customName = device.value?.device_sensor_config?.[key]?.custom_name
        const displayName = customName || cfg.name || key

        return {
          key,
          displayName,
          displayValue: value === undefined
            ? (latestData.value ? '无数据' : '暂无数据')
            : formatSensorValue(value, cfg.type, cfg.unit),
          valueClass: getValueClass(value, cfg.type)
        }
      })
  }

  // 无产品配置：直接用 sensors 元数据数组（后端返回的完整信息）
  if (latestSensors.value.length > 0) {
    return latestSensors.value.map(s => ({
      key: s.sensor_name,
      displayName: s.sensor_name,
      displayValue: formatSensorValue(s.value, s.sensor_type, s.unit),
      valueClass: getValueClass(s.value, s.sensor_type)
    }))
  }

  // 降级兜底：直接读 latestData 的 key
  if (latestData.value && Object.keys(latestData.value).length > 0) {
    return Object.entries(latestData.value).map(([key, value]) => ({
      key,
      displayName: key,
      displayValue: formatSensorValue(value, '', ''),
      valueClass: getValueClass(value, '')
    }))
  }

  return []
})

const getValueClass = (value, sensorType) => {
  if (value === undefined || value === null) return 'value-empty'
  if ((sensorType || '').toUpperCase() === 'RAIN_SENSOR') {
    return value ? 'value-rain' : 'value-dry'
  }
  return 'value-normal'
}

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

const goBack = () => {
  router.push('/device/devices')
}

onMounted(async () => {
  await loadDeviceInfo()
  await loadRealtimeData()
  // 30 秒自动刷新
  refreshTimer = setInterval(loadRealtimeData, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.device-realtime-data-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  flex-shrink: 0;
}

.back-btn {
  font-size: 14px;
}

.page-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.device-tags {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.page-content {
  padding-top: 8px;
}

.loading-placeholder {
  padding: 20px 0;
}

.sensor-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.sensor-card {
  text-align: center;
}

.sensor-name {
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}

.sensor-value {
  font-size: 32px;
  font-weight: 700;
  margin: 12px 0;
}

.value-normal { color: #409eff; }
.value-dry    { color: #67c23a; }
.value-rain   { color: #e6a23c; }
.value-empty  { color: #c0c4cc; font-size: 16px; }

.sensor-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 8px;
}
</style>

