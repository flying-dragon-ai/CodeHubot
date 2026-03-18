<template>
  <div class="products-container">
    <div class="page-header">
      <h2>产品管理</h2>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-section">
      <!-- 第一行：搜索和操作 -->
      <el-row :gutter="16" style="margin-bottom: 12px;">
        <el-col :span="10">
          <el-input
            v-model="searchQuery"
            placeholder="搜索产品名称或编码"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="loadProducts" style="width: 100%;">
            <el-option label="激活" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
        </el-col>
        <el-col :span="8" style="text-align: right;">
          <el-button @click="resetFilters">重置筛选</el-button>
          <el-button type="primary" icon="Plus" @click="addProduct" v-if="canCreateProduct">添加产品</el-button>
        </el-col>
      </el-row>
      
      <!-- 第二行：产品类型筛选 -->
      <el-row :gutter="16">
        <el-col :span="24">
          <div style="display: flex; align-items: center;">
            <!-- 管理员：系统内建筛选 -->
            <div v-if="isAdmin" style="display: flex; align-items: center;">
              <span style="margin-right: 12px; color: #606266; font-size: 14px;">产品类型：</span>
              <el-radio-group v-model="systemProductFilter" @change="loadProducts" size="small">
                <el-radio-button label="system">仅系统内建</el-radio-button>
                <el-radio-button label="user">仅用户创建</el-radio-button>
                <el-radio-button label="all">全部产品</el-radio-button>
              </el-radio-group>
            </div>
            
            <!-- 普通用户：共享产品筛选 -->
            <div v-if="!isAdmin" style="display: flex; align-items: center;">
              <span style="margin-right: 12px; color: #606266; font-size: 14px;">显示范围：</span>
              <el-radio-group v-model="showSharedProducts" @change="loadProducts" size="small">
                <el-radio-button :label="false">仅我的产品</el-radio-button>
                <el-radio-button :label="true">包含共享产品</el-radio-button>
              </el-radio-group>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 产品列表 -->
    <el-table
      v-loading="loading"
      :data="products"
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="product_code" label="产品编码" width="180" sortable="custom" />
      <el-table-column prop="name" label="产品名称" min-width="200" />
      <el-table-column prop="manufacturer" label="制造商" width="150" />
      <el-table-column prop="version" label="版本" width="100" />
      <el-table-column label="状态" width="80">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'danger'">
            {{ scope.row.is_active ? '激活' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" sortable="custom">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="类型" width="120">
        <template #default="scope">
          <div style="display: flex; gap: 4px; flex-direction: column;">
            <el-tag :type="scope.row.is_system ? 'warning' : 'info'" size="small">
              {{ scope.row.is_system ? '系统内置' : '用户创建' }}
            </el-tag>
            <el-tag v-if="!scope.row.is_system && scope.row.is_shared" type="success" size="small">
              已共享
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="viewProduct(scope.row)">查看</el-button>
          <el-button
            v-if="canEditProduct(scope.row)"
            size="small"
            type="primary"
            @click="editProduct(scope.row)"
          >
            编辑
          </el-button>
          <el-button
            v-if="canDeleteProduct(scope.row)"
            size="small"
            type="danger"
            @click="deleteProduct(scope.row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 创建/编辑产品对话框 - 包含传感器和控制端口简单配置 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingProduct ? '编辑产品' : '新增产品'"
      width="800px"
      @close="resetForm"
    >
      <el-form
        ref="productFormRef"
        :model="productForm"
        :rules="productRules"
        label-width="100px"
      >
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        
        <el-form-item label="产品编码" prop="product_code">
          <el-input 
            v-model="productForm.product_code" 
            placeholder="请输入产品编码（如：ESP32-S3-Dev-01）" 
            :disabled="!!editingProduct"
            maxlength="64"
            show-word-limit
          />
          <div class="form-tip">
            <div>⚠️ 产品编码创建后不可修改</div>
            <div>📱 必须与固件端 DEVICE_PRODUCT_ID 完全一致（最长64字符）</div>
            <div>💡 建议格式：硬件型号-功能-版本（如：ESP32-S3-TempSensor-01）</div>
          </div>
        </el-form-item>
        
        <el-form-item label="产品名称" prop="name">
          <el-input v-model="productForm.name" placeholder="请输入产品名称（如：ESP32-S3 开发板）" />
        </el-form-item>
        
        <el-form-item label="制造商">
          <el-input v-model="productForm.manufacturer" placeholder="请输入制造商（如：Espressif）" />
        </el-form-item>
        
        <el-form-item label="版本">
          <el-input v-model="productForm.version" placeholder="请输入版本号（如：v1.0）" />
        </el-form-item>
        
        <el-form-item label="产品描述">
          <el-input
            v-model="productForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入产品描述"
          />
        </el-form-item>
        
        <!-- 传感器配置 -->
        <el-divider content-position="left">传感器配置</el-divider>
        <el-form-item label="传感器">
          <div class="sensor-config-list">
            <div v-for="(sensor, index) in sensorConfigs" :key="index" class="config-item">
              <el-select 
                v-model="sensor.type" 
                placeholder="选择传感器类型" 
                style="width: 160px; margin-right: 8px;"
                @change="onSensorTypeChange(sensor, index)"
              >
                <el-option label="DHT11" value="DHT11" />
                <el-option label="DHT22" value="DHT22" />
                <el-option label="DS18B20" value="DS18B20" />
                <el-option label="BMP280" value="BMP280" />
                <el-option label="雨水传感器" value="RAIN_SENSOR" />
              </el-select>
              <el-select 
                v-model="sensor.data_field" 
                placeholder="数据字段" 
                style="width: 140px; margin-right: 8px;"
              >
                <el-option 
                  v-for="field in getSensorDataFields(sensor.type)" 
                  :key="field.value" 
                  :label="field.label" 
                  :value="field.value"
                />
              </el-select>
              <el-input 
                v-model="sensor.name" 
                placeholder="自定义显示名称" 
                style="width: 160px; margin-right: 8px;"
              />
              <el-tag 
                :type="isDuplicateSensorKey(sensor.key, index) ? 'danger' : 'info'" 
                size="small" 
                style="margin-right: 8px;"
              >
                {{ sensor.key }}
                <span v-if="isDuplicateSensorKey(sensor.key, index)"> ⚠️重复</span>
              </el-tag>
              <el-button 
                type="danger" 
                size="small" 
                icon="Delete" 
                circle 
                @click="removeSensor(index)"
              />
            </div>
            <el-button 
              type="primary" 
              size="small" 
              icon="Plus" 
              @click="addSensor"
              style="margin-top: 8px;"
            >
              添加传感器数据字段
            </el-button>
          </div>
          <div class="form-tip">
            ✅ DHT11/DHT22包含温度和湿度两个字段，需分别添加。key格式：传感器_字段
          </div>
        </el-form-item>
        
        <!-- 控制端口配置 -->
        <el-divider content-position="left">控制端口配置</el-divider>
        <el-form-item label="控制端口">
          <div class="control-config-list">
            <div v-for="(control, index) in controlConfigs" :key="index" class="config-item">
              <el-select 
                v-model="control.type" 
                placeholder="控制类型" 
                style="width: 120px; margin-right: 8px;"
                @change="onControlTypeChange(control, index)"
              >
                <el-option label="LED" value="LED" />
                <el-option label="继电器" value="RELAY" />
                <el-option label="舵机" value="SERVO" />
                <el-option label="PWM输出" value="PWM" />
              </el-select>
              <el-select 
                v-model="control.device_id" 
                placeholder="设备编号" 
                style="width: 100px; margin-right: 8px;"
                @change="onControlDeviceIdChange(control, index)"
              >
                <el-option 
                  v-for="id in getDeviceIdRange(control.type)" 
                  :key="id" 
                  :label="`${control.type || ''}${id}`" 
                  :value="id"
                />
              </el-select>
              <el-input 
                v-model="control.name" 
                placeholder="自定义显示名称" 
                style="width: 150px; margin-right: 8px;"
              />
              <el-tag 
                :type="isDuplicateControlKey(control.key, index) ? 'danger' : 'info'" 
                size="small" 
                style="margin-right: 8px;"
              >
                {{ control.key }}
                <span v-if="isDuplicateControlKey(control.key, index)"> ⚠️重复</span>
              </el-tag>
              <el-button 
                type="danger" 
                size="small" 
                icon="Delete" 
                circle 
                @click="removeControl(index)"
              />
            </div>
            <el-button 
              type="primary" 
              size="small" 
              icon="Plus" 
              @click="addControl"
              style="margin-top: 8px;"
            >
              添加控制端口
            </el-button>
          </div>
          <div class="form-tip">
            ✅ 设备可能有多个相同类型的控制端口（如LED1-4），需分别添加。key格式：类型_设备号
          </div>
        </el-form-item>
        
        <el-form-item label="状态">
          <el-switch
            v-model="productForm.is_active"
            active-text="激活"
            inactive-text="停用"
          />
        </el-form-item>
        
        <!-- 管理员专用：系统内置产品选项 -->
        <el-divider content-position="left" v-if="isAdmin">产品类型</el-divider>
        <el-form-item label="系统内置" v-if="isAdmin">
          <el-switch
            v-model="productForm.is_system"
            active-text="是"
            inactive-text="否"
            @change="handleSystemProductChange"
          />
          <div class="form-tip">系统内置产品对所有用户可见，只有管理员可以修改</div>
        </el-form-item>
        
        <!-- 普通用户才显示共享选项，管理员创建的系统内置产品不需要共享 -->
        <el-form-item label="共享产品" v-if="!productForm.is_system && !isAdmin">
          <el-switch
            v-model="productForm.is_shared"
            active-text="共享"
            inactive-text="私有"
          />
          <div class="form-tip">共享后，其他用户可以查看此产品配置，但只有您可以修改</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveProduct">
            {{ editingProduct ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 查看产品详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="产品详情"
      width="850px"
    >
      <div v-if="selectedProduct" class="product-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="产品编码">
            {{ selectedProduct.product_code }}
          </el-descriptions-item>
          <el-descriptions-item label="产品名称" :span="2">
            {{ selectedProduct.name }}
          </el-descriptions-item>
          <el-descriptions-item label="制造商">
            {{ selectedProduct.manufacturer || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="版本">
            {{ selectedProduct.version || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedProduct.is_active ? 'success' : 'danger'">
              {{ selectedProduct.is_active ? '激活' : '停用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="类型">
            <div style="display: flex; gap: 8px;">
              <el-tag :type="selectedProduct.is_system ? 'warning' : 'info'">
                {{ selectedProduct.is_system ? '系统内置' : '用户创建' }}
              </el-tag>
              <el-tag v-if="!selectedProduct.is_system && selectedProduct.is_shared" type="success">
                已共享
              </el-tag>
              <el-tag v-if="!selectedProduct.is_system && !selectedProduct.is_shared" type="info">
                私有
            </el-tag>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(selectedProduct.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">
            {{ formatDate(selectedProduct.updated_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="产品描述" :span="2">
            {{ selectedProduct.description || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 传感器配置 -->
        <div style="margin-top: 24px;">
          <h4 style="margin-bottom: 12px; color: #303133; display: flex; align-items: center; gap: 8px;">
            <el-icon><Opportunity /></el-icon>
            <span>传感器配置</span>
          </h4>
          <el-table 
            :data="getFormattedSensors(selectedProduct.sensor_types)" 
            border 
            size="small"
            :empty-text="'未配置传感器'"
          >
            <el-table-column prop="key" label="配置键" min-width="150" />
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="scope">
                <el-tag size="small">{{ scope.row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="data_field" label="数据字段" width="100" />
            <el-table-column prop="enabled" label="状态" width="70" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.enabled ? 'success' : 'info'" size="small">
                  {{ scope.row.enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 控制端口配置 -->
        <div style="margin-top: 20px;">
          <h4 style="margin-bottom: 12px; color: #303133; display: flex; align-items: center; gap: 8px;">
            <el-icon><Operation /></el-icon>
            <span>控制端口配置</span>
          </h4>
          <el-table 
            :data="getFormattedControlPorts(selectedProduct.control_ports)" 
            border 
            size="small"
            :empty-text="'未配置控制端口'"
          >
            <el-table-column prop="key" label="配置键" min-width="120" />
            <el-table-column prop="name" label="名称" min-width="100" />
            <el-table-column prop="type" label="类型" width="80">
              <template #default="scope">
                <el-tag size="small" :type="getControlTypeColor(scope.row.type)">
                  {{ scope.row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="device_id" label="设备ID" width="80" align="center" />
            <el-table-column prop="enabled" label="状态" width="70" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.enabled ? 'success' : 'info'" size="small">
                  {{ scope.row.enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDetailDialog = false">关闭</el-button>
          <el-button 
            v-if="canEditProduct(selectedProduct)"
            type="primary" 
            @click="editProductFromDetail"
          >
            编辑
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Opportunity, Operation } from '@element-plus/icons-vue'
import { getProducts, createProduct, updateProduct, deleteProduct as deleteProductApi } from '@/api/product'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

// 数据
const products = ref([])
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const editingProduct = ref(null)
const selectedProduct = ref(null)

// 搜索和筛选
const searchQuery = ref('')
const filterStatus = ref(null)
const showSharedProducts = ref(false)  // 是否显示共享产品（默认不显示）
const systemProductFilter = ref('system')  // 管理员筛选：system=系统内建, user=用户创建, all=全部（默认系统内建）

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 表单数据
const productForm = reactive({
  product_code: '',
  name: '',
  manufacturer: '',
  version: '',
  description: '',
  is_active: true,
  is_shared: false,
  is_system: false,
  sensor_types: {},
  control_ports: {}
})

const productFormRef = ref(null)

// 传感器和控制端口配置列表
const sensorConfigs = ref([])
const controlConfigs = ref([])

// 表单验证规则
const productRules = {
  product_code: [
    { required: true, message: '请输入产品编码', trigger: 'blur' },
    { min: 2, max: 64, message: '产品编码长度在 2 到 64 个字符', trigger: 'blur' },
    { 
      pattern: /^[A-Za-z0-9\-_]+$/, 
      message: '产品编码只能包含字母、数字、连字符和下划线', 
      trigger: 'blur' 
    }
  ],
  name: [
    { required: true, message: '请输入产品名称', trigger: 'blur' },
    { min: 2, max: 100, message: '产品名称长度在 2 到 100 个字符', trigger: 'blur' }
  ]
}

// 权限判断
const isAdmin = computed(() => {
  // 使用store的isAdmin计算属性
  return userStore.isAdmin
})

// 所有登录用户都可以创建产品
const canCreateProduct = computed(() => {
  return true  // 普通用户可以创建普通产品，管理员可以创建所有产品
})

const canEditProduct = (product) => {
  if (!product) return false
  if (isAdmin.value) return true
  // 系统内置产品只有管理员可编辑
  if (product.is_system) return false
  // 用户创建的产品只有创建者可编辑
  return product.creator_id === userStore.user?.id
}

const canDeleteProduct = (product) => {
  if (!product) return false
  // 系统内置产品只有管理员可删除
  if (product.is_system) return isAdmin.value
  // 用户创建的产品只有创建者和管理员可删除
  return isAdmin.value || product.creator_id === userStore.user?.id
}

// 格式化日期（转换为中国大陆时区 UTC+8）
const formatDate = (date) => {
  if (!date) return '-'
  
  // 解析UTC时间并转换为中国时区
  let dateObj
  if (typeof date === 'string' && date.endsWith('Z')) {
    // UTC时间字符串
    dateObj = new Date(date)
  } else if (typeof date === 'string' && date.includes('T')) {
    // 没有Z后缀的ISO格式，添加Z表示UTC
    dateObj = new Date(date.endsWith('Z') ? date : date + 'Z')
  } else {
    dateObj = new Date(date)
  }
  
  // 转换为中国时区（UTC+8）并格式化
  return dateObj.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Asia/Shanghai'
  })
}

// 格式化传感器配置用于表格显示
const getFormattedSensors = (sensorTypes) => {
  if (!sensorTypes || typeof sensorTypes !== 'object') {
    return []
  }
  
  return Object.entries(sensorTypes).map(([key, config]) => ({
    key: key,
    name: config.name || '-',
    type: config.type || '-',
    data_field: config.data_field || '-',
    enabled: config.enabled !== false
  }))
}

// 格式化控制端口配置用于表格显示
const getFormattedControlPorts = (controlPorts) => {
  if (!controlPorts || typeof controlPorts !== 'object') {
    return []
  }
  
  return Object.entries(controlPorts).map(([key, config]) => ({
    key: key,
    name: config.name || '-',
    type: config.type || '-',
    device_id: config.device_id || '-',
    enabled: config.enabled !== false
  }))
}

// 获取控制端口类型的颜色
const getControlTypeColor = (type) => {
  const colorMap = {
    'LED': 'success',
    'RELAY': 'warning',
    'SERVO': 'primary',
    'PWM': 'danger'
  }
  return colorMap[type] || 'info'
}

// 加载产品列表
const loadProducts = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      search: searchQuery.value || undefined,
      is_active: filterStatus.value !== null ? filterStatus.value : undefined,
      include_shared: isAdmin.value ? true : showSharedProducts.value  // 管理员始终看到所有，普通用户根据开关决定
    }
    
    // 管理员的系统内建筛选
    if (isAdmin.value) {
      if (systemProductFilter.value === 'system') {
        params.is_system = true  // 只显示系统内建
      } else if (systemProductFilter.value === 'user') {
        params.is_system = false  // 只显示用户创建
      }
      // 'all' 时不添加 is_system 参数，显示全部
    }
    
    const response = await getProducts(params)
    
    // 后端直接返回数组，不是分页对象
    if (Array.isArray(response.data)) {
    products.value = response.data
      total.value = response.data.length
    } else {
      // 兼容分页对象格式
      products.value = response.data.items || []
      total.value = response.data.total || 0
    }
  } catch (error) {
    console.error('加载产品列表失败:', error)
    ElMessage.error('加载产品列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  loadProducts()
}

// 重置筛选
const resetFilters = () => {
  searchQuery.value = ''
  filterStatus.value = null
  showSharedProducts.value = false
  systemProductFilter.value = 'system'  // 管理员重置为默认只看系统内建
  currentPage.value = 1
  loadProducts()
}

// 排序处理
const handleSortChange = ({ prop, order }) => {
  // TODO: 实现后端排序
  loadProducts()
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  loadProducts()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadProducts()
}

// 查看产品
const viewProduct = (product) => {
  selectedProduct.value = product
  showDetailDialog.value = true
}

// 从详情编辑
const editProductFromDetail = () => {
  showDetailDialog.value = false
  editProduct(selectedProduct.value)
}

// 添加传感器
const addSensor = () => {
  sensorConfigs.value.push({
    key: '',
    name: '',
    type: 'DHT11'
  })
}

// 删除传感器
const removeSensor = (index) => {
  sensorConfigs.value.splice(index, 1)
}

// 添加控制端口
const addControl = () => {
  controlConfigs.value.push({
    key: '',
    name: '',
    type: 'LED'
  })
}

// 删除控制端口
const removeControl = (index) => {
  controlConfigs.value.splice(index, 1)
}

// 处理系统内置产品开关变化
const handleSystemProductChange = (value) => {
  // 如果设置为系统内置产品，自动取消共享状态（系统内置产品默认对所有人可见）
  if (value) {
    productForm.is_shared = false
  }
}

// 添加产品
const addProduct = () => {
  editingProduct.value = null
  resetForm()
  showCreateDialog.value = true
}

// 编辑产品
const editProduct = (product) => {
  editingProduct.value = product
  Object.assign(productForm, {
    product_code: product.product_code,
    name: product.name,
    manufacturer: product.manufacturer || '',
    version: product.version || '',
    description: product.description || '',
    is_active: product.is_active,
    is_shared: product.is_shared || false,
    is_system: product.is_system || false,
    sensor_types: product.sensor_types || {},
    control_ports: product.control_ports || {}
  })
  
  // 加载传感器配置
  sensorConfigs.value = []
  if (product.sensor_types && typeof product.sensor_types === 'object') {
    Object.keys(product.sensor_types).forEach(key => {
      const sensor = product.sensor_types[key]
      // key格式：传感器类型_数据字段，如：DHT11_temperature
      const parts = key.split('_')
      const sensorType = parts[0] || 'DHT11'
      const dataField = parts.slice(1).join('_') || 'temperature'
      
      const config = {
        key: key,
        name: sensor.name || '',
        type: sensorType,
        data_field: dataField
      }
      
      console.log('📊 加载传感器配置:', config)
      sensorConfigs.value.push(config)
    })
  }
  console.log('📦 所有传感器配置:', sensorConfigs.value)
  
  // 加载控制端口配置
  controlConfigs.value = []
  if (product.control_ports && typeof product.control_ports === 'object') {
    Object.keys(product.control_ports).forEach(key => {
      const control = product.control_ports[key]
      
      let controlType = 'LED'
      let deviceId = 1
      
      // 解析key格式
      if (key.startsWith('pwm_m')) {
        // PWM格式：pwm_m2
        controlType = 'PWM'
        deviceId = parseInt(key.replace('pwm_m', '')) || 2
      } else {
        // 支持多种格式：
        // 1. led_1, relay_2, servo_1 (带下划线)
        // 2. led1, relay2, servo1 (无下划线，末尾是数字)
        // 3. led, relay (无下划线，无数字，默认device_id=1)
        const parts = key.split('_')
        if (parts.length > 1) {
          // 格式1：led_1
          controlType = parts[0]?.toUpperCase() || 'LED'
          deviceId = parseInt(parts[parts.length - 1]) || 1
        } else {
          // 格式2或3：led1 或 led
          const keyLower = key.toLowerCase()
          // 提取类型前缀（led, relay, servo等）
          const typeMatch = keyLower.match(/^(led|relay|servo|pwm)/)
          if (typeMatch) {
            controlType = typeMatch[1].toUpperCase()
            // 提取末尾的数字
            const numMatch = keyLower.match(/(\d+)$/)
            deviceId = numMatch ? parseInt(numMatch[1]) : 1
          } else {
            // 无法识别类型，使用默认值
            controlType = 'LED'
            deviceId = 1
          }
        }
      }
      
      const config = {
        key: key,
        name: control.name || '',
        type: controlType,
        device_id: deviceId
      }
      
      console.log('🎛️ 加载控制端口配置:', config)
      controlConfigs.value.push(config)
    })
  }
  console.log('📦 所有控制端口配置:', controlConfigs.value)
  
  showCreateDialog.value = true
}

// 检测重复key
const checkDuplicateKeys = () => {
  // 检测传感器key重复
  const sensorKeys = sensorConfigs.value
    .filter(s => s.key)
    .map(s => s.key)
  const duplicateSensorKeys = sensorKeys.filter((key, index) => sensorKeys.indexOf(key) !== index)
  
  if (duplicateSensorKeys.length > 0) {
    ElMessage.error(`传感器配置存在重复的key: ${[...new Set(duplicateSensorKeys)].join(', ')}`)
    return false
  }
  
  // 检测控制端口key重复
  const controlKeys = controlConfigs.value
    .filter(c => c.key)
    .map(c => c.key)
  const duplicateControlKeys = controlKeys.filter((key, index) => controlKeys.indexOf(key) !== index)
  
  if (duplicateControlKeys.length > 0) {
    ElMessage.error(`控制端口配置存在重复的key: ${[...new Set(duplicateControlKeys)].join(', ')}`)
    return false
  }
  
  return true
}

// 保存产品
const saveProduct = async () => {
  if (!productFormRef.value) return

  try {
    await productFormRef.value.validate()
    
    // 检测重复key
    if (!checkDuplicateKeys()) {
      return
    }
    
    saving.value = true

    // 构建传感器配置对象
    const sensor_types = {}
    sensorConfigs.value.forEach(sensor => {
      if (sensor.key && sensor.name && sensor.type && sensor.data_field) {
        sensor_types[sensor.key] = {
          type: sensor.type,
          name: sensor.name,
          data_field: sensor.data_field,  // ✅ 添加 data_field
          enabled: true
        }
      }
    })

    // 构建控制端口配置对象
    const control_ports = {}
    controlConfigs.value.forEach(control => {
      if (control.key && control.name && control.type) {
        control_ports[control.key] = {
          type: control.type,
          name: control.name,
          device_id: control.device_id,
          enabled: true
        }
        
        // PWM类型需要额外的配置
        if (control.type === 'PWM') {
          // 根据device_id设置对应的GPIO引脚
          const pwmPins = {
            1: 48,  // M1对应GPIO48
            2: 40   // M2对应GPIO40
          }
          control_ports[control.key].pin = pwmPins[control.device_id] || 40
          control_ports[control.key].description = '可自定义频率和占空比的PWM输出'
          control_ports[control.key].frequency_range = { min: 1, max: 40000 }
          control_ports[control.key].duty_cycle_range = { min: 0.0, max: 100.0 }
        }
      }
    })

    const productData = {
      product_code: productForm.product_code,
      name: productForm.name,
      manufacturer: productForm.manufacturer,
      version: productForm.version,
      description: productForm.description,
      is_active: productForm.is_active,
      is_shared: productForm.is_shared,
      is_system: productForm.is_system,  // 系统内置标识
      sensor_types: sensor_types,
      control_ports: control_ports
    }

    if (editingProduct.value) {
      await updateProduct(editingProduct.value.id, productData)
      ElMessage.success('产品更新成功')
    } else {
      await createProduct(productData)
      ElMessage.success('产品创建成功')
    }

    showCreateDialog.value = false
    loadProducts()
  } catch (error) {
    console.error(editingProduct.value ? '更新产品失败:' : '创建产品失败:', error)
    ElMessage.error(editingProduct.value ? '更新产品失败' : '创建产品失败')
  } finally {
    saving.value = false
  }
}

// 删除产品
const deleteProduct = async (product) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除产品"${product.name}"吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteProductApi(product.id)
    ElMessage.success('产品删除成功')
    loadProducts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除产品失败:', error)
      ElMessage.error('删除产品失败')
    }
    }
  }

// 重置表单
const resetForm = () => {
  editingProduct.value = null
  if (productFormRef.value) {
    productFormRef.value.resetFields()
  }
  Object.assign(productForm, {
    product_code: '',
    name: '',
    manufacturer: '',
    version: '',
    description: '',
    is_active: true,
    is_shared: false,
    is_system: false,
    sensor_types: {},
    control_ports: {}
  })
  sensorConfigs.value = []
  controlConfigs.value = []
}

// 获取传感器的数据字段列表
const getSensorDataFields = (sensorType) => {
  const fieldMapping = {
    'DHT11': [
      { label: '温度 (temperature)', value: 'temperature' },
      { label: '湿度 (humidity)', value: 'humidity' }
    ],
    'DHT22': [
      { label: '温度 (temperature)', value: 'temperature' },
      { label: '湿度 (humidity)', value: 'humidity' }
    ],
    'DS18B20': [
      { label: '温度 (temperature)', value: 'temperature' }
    ],
    'BMP280': [
      { label: '气压 (pressure)', value: 'pressure' },
      { label: '温度 (temperature)', value: 'temperature' }
    ],
    'RAIN_SENSOR': [
      { label: '是否下雨 (is_raining)', value: 'is_raining' },
      { label: '雨量等级 (rain_level)', value: 'rain_level' }
    ]
  }
  return fieldMapping[sensorType] || []
}

// 获取控制类型的设备编号范围
const getDeviceIdRange = (controlType) => {
  const rangeMapping = {
    'LED': [1, 2, 3, 4],      // LED 1-4
    'RELAY': [1, 2],          // 继电器 1-2
    'SERVO': [1],             // 舵机 1（M1）
    'PWM': [1, 2]             // PWM输出 M1（通道1）和 M2（通道2）
  }
  return rangeMapping[controlType] || [1]
}

// 传感器类型改变时
const onSensorTypeChange = (sensor, index) => {
  // 清空数据字段选择
  sensor.data_field = ''
  sensor.key = ''
  sensor.name = ''
  
  // 如果类型选择后，尝试更新key
  updateSensorKey(sensor)
}

// 更新传感器key（当类型或数据字段改变时）
const updateSensorKey = (sensor) => {
  if (sensor.type && sensor.data_field) {
    // key格式：传感器类型_数据字段，如：DHT11_temperature
    sensor.key = `${sensor.type}_${sensor.data_field}`
    
    // 自动生成默认名称
    const fieldNames = {
      'temperature': '温度',
      'humidity': '湿度',
      'pressure': '气压'
    }
    const fieldName = fieldNames[sensor.data_field] || sensor.data_field
    if (!sensor.name) {
      sensor.name = `${sensor.type}${fieldName}`
    }
  }
}

// 监听传感器数据字段变化
watch(sensorConfigs, (newConfigs) => {
  newConfigs.forEach(sensor => {
    if (sensor.type && sensor.data_field) {
      updateSensorKey(sensor)
  }
  })
}, { deep: true })

// 控制类型改变时
const onControlTypeChange = (control, index) => {
  // 清空设备编号
  control.device_id = null
  control.key = ''
  control.name = ''
}

// 控制设备编号改变时
const onControlDeviceIdChange = (control, index) => {
  updateControlKey(control)
}

// 更新控制端口key（当类型或设备编号改变时）
const updateControlKey = (control) => {
  if (control.type && control.device_id) {
    // 固件命令映射
    const cmdMapping = {
      'LED': 'led',
      'RELAY': 'relay',
      'SERVO': 'servo',
      'PWM': 'pwm_m'
    }
    
    const cmd = cmdMapping[control.type] || control.type.toLowerCase()
    // key格式：命令类型_设备编号，如：led_1, relay_2, pwm_m2
    // 注意：使用下划线分隔，避免与无下划线格式混淆
    if (control.type === 'PWM') {
      control.key = `${cmd}${control.device_id}`
    } else {
      control.key = `${cmd}_${control.device_id}`
    }
    
    // 自动生成默认名称
    const typeNames = {
      'LED': 'LED',
      'RELAY': '继电器',
      'SERVO': '舵机',
      'PWM': 'PWM输出 (M'
    }
    if (!control.name) {
      if (control.type === 'PWM') {
        control.name = `${typeNames[control.type]}${control.device_id})`
      } else {
        control.name = `${typeNames[control.type] || control.type}${control.device_id}`
      }
    }
  }
}

// 监听控制端口配置变化
watch(controlConfigs, (newConfigs) => {
  newConfigs.forEach(control => {
    if (control.type && control.device_id) {
      updateControlKey(control)
    }
  })
}, { deep: true })

// 检测传感器key是否重复
const isDuplicateSensorKey = (key, currentIndex) => {
  if (!key) return false
  return sensorConfigs.value.filter((s, idx) => s.key === key && idx !== currentIndex).length > 0
}

// 检测控制端口key是否重复
const isDuplicateControlKey = (key, currentIndex) => {
  if (!key) return false
  return controlConfigs.value.filter((c, idx) => c.key === key && idx !== currentIndex).length > 0
}

// 初始化
onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
.products-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.filter-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.product-detail {
  padding: 10px 0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.sensor-config-list,
.control-config-list {
  width: 100%;
}

.config-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

:deep(.el-divider__text) {
  font-weight: 500;
  color: #303133;
}
</style>
