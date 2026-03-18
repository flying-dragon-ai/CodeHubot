"""
AIOT 插件后端服务
专门为外部插件提供设备操作服务
直接访问数据库和MQTT，不依赖主backend服务
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import logging
import asyncio
from datetime import datetime
import json
from sqlalchemy import create_engine, desc, Column, Integer, String, DateTime, Boolean, Text, JSON, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# 加载环境变量
# ============================================================

# 加载 .env 文件
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
    logger.info(f"✅ 已加载配置文件: {env_file}")
else:
    logger.warning(f"⚠️  配置文件不存在: {env_file}")
    logger.warning(f"⚠️  将使用默认配置，请复制 env.example 为 .env 并修改配置")

# ============================================================
# 配置
# ============================================================

# 数据库配置（支持两种方式）
# 方式1：使用完整的 DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 方式2：使用单独的配置项（如果 DATABASE_URL 未设置）
if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "aiot")
    DB_USER = os.getenv("DB_USER", "aiot_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    
    # 检查是否使用默认密码
    if DB_PASSWORD == "password":
        logger.warning("⚠️  警告：正在使用默认密码 'password'，这不安全！")
        logger.warning("⚠️  请在 .env 文件中设置正确的 DB_PASSWORD")
    
    # 构建 DATABASE_URL
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# MQTT配置
MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# 服务配置
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "9002"))  # 默认 9002（9001 被 MQTT WebSocket 占用）
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")

# 显示配置信息
logger.info("=" * 60)
logger.info("  AIOT 插件后端服务配置")
logger.info("=" * 60)
logger.info(f"  服务地址: http://{SERVICE_HOST}:{SERVICE_PORT}")
logger.info("")

# 详细的数据库配置信息
logger.info("  📊 数据库配置:")
if os.getenv("DATABASE_URL"):
    logger.info("    配置方式: DATABASE_URL（完整连接字符串）")
else:
    logger.info("    配置方式: 单独配置项")
    
    # 检查是否从 .env 读取到了配置
    db_password_from_env = os.getenv('DB_PASSWORD')
    if db_password_from_env:
        logger.info(f"    DB_HOST = {os.getenv('DB_HOST', 'localhost')}")
        logger.info(f"    DB_PORT = {os.getenv('DB_PORT', '3306')}")
        logger.info(f"    DB_NAME = {os.getenv('DB_NAME', 'aiot')}")
        logger.info(f"    DB_USER = {os.getenv('DB_USER', 'aiot_user')}")
        password = db_password_from_env
        logger.info(f"    DB_PASSWORD = {'*' * len(password)} ({len(password)}字符)")
    else:
        logger.warning("    ⚠️  未从 .env 读取到数据库配置，使用默认值")
        logger.warning(f"    DB_HOST = {os.getenv('DB_HOST', 'localhost')} (默认)")
        logger.warning(f"    DB_PORT = {os.getenv('DB_PORT', '3306')} (默认)")
        logger.warning(f"    DB_NAME = {os.getenv('DB_NAME', 'aiot')} (默认)")
        logger.warning(f"    DB_USER = {os.getenv('DB_USER', 'aiot_user')} (默认)")
        password = 'password'
        logger.warning(f"    DB_PASSWORD = {'*' * len(password)} ({len(password)}字符) (默认 - 不安全！)")

# 显示最终的连接信息（隐藏密码）
if '@' in DATABASE_URL:
    db_info = DATABASE_URL.split('@')[1]  # 显示 host:port/db
    db_user = DATABASE_URL.split('://')[1].split(':')[0]  # 提取用户名
    logger.info(f"    连接地址: {db_user}@{db_info}")
else:
    logger.info("    状态: 未配置")

logger.info("")
logger.info(f"  📡 MQTT配置: {MQTT_BROKER}:{MQTT_PORT}")
if MQTT_USERNAME:
    logger.info(f"    认证模式: 用户名密码")
else:
    logger.info(f"    认证模式: 匿名访问")
logger.info("=" * 60 + "\n")

# ============================================================
# 数据库模型（简化版，只包含必要字段）
# ============================================================

Base = declarative_base()

class Device(Base):
    __tablename__ = "device_main"
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    device_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(100))
    device_status = Column(String(50))
    is_online = Column(Boolean)
    is_active = Column(Boolean)
    device_settings = Column(JSON)  # 设备配置，包含预设指令
    last_report_data = Column(JSON)  # 最后上报数据，包含所有传感器数据
    last_seen = Column(DateTime)  # 最后在线时间

class DeviceSensor(Base):
    """设备传感器数据表（新）"""
    __tablename__ = "device_sensors"
    
    id = Column(Integer, primary_key=True)
    device_uuid = Column(String(36), nullable=False)  # 使用 device_uuid
    sensor_name = Column(String(50), nullable=False)
    sensor_value = Column(String(255), nullable=False)
    sensor_unit = Column(String(20))
    sensor_type = Column(String(50))
    timestamp = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

# ============================================================
# 数据库连接
# ============================================================

logger.info("🔄 正在连接数据库...")
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 测试连接
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    
    logger.info("✅ 数据库连接成功")
except Exception as e:
    logger.error("=" * 60)
    logger.error("❌ 数据库连接失败")
    logger.error("=" * 60)
    logger.error(f"错误类型: {type(e).__name__}")
    logger.error(f"错误信息: {str(e)}")
    logger.error("")
    logger.error("💡 常见原因和解决方案：")
    logger.error("  1. 密码错误 → 检查 .env 中的 DB_PASSWORD")
    logger.error("  2. 数据库不存在 → 检查 DB_NAME 是否正确")
    logger.error("  3. 用户不存在 → 检查 DB_USER 是否正确")
    logger.error("  4. MySQL未运行 → 执行: sudo systemctl start mysql")
    logger.error("  5. 主机错误 → 检查 DB_HOST (Docker环境用容器名)")
    logger.error("")
    logger.error("🔍 快速诊断命令：")
    if not os.getenv("DATABASE_URL"):
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '3306')
        db_user = os.getenv('DB_USER', 'aiot_user')
        db_name = os.getenv('DB_NAME', 'aiot')
        logger.error(f"  mysql -h {db_host} -P {db_port} -u {db_user} -p {db_name}")
    logger.error("=" * 60)
    SessionLocal = None

def get_db():
    """获取数据库会话"""
    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="数据库未连接")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================
# MQTT 客户端
# ============================================================

class MQTTClient:
    def __init__(self):
        self.client = None
        self.connected = False
        
    def connect(self):
        """连接到MQTT服务器"""
        try:
            self.client = mqtt.Client()
            
            # 如果配置了用户名和密码，则使用认证；否则使用匿名访问
            if MQTT_USERNAME and MQTT_PASSWORD:
                self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
                logger.info("🔐 MQTT使用用户名密码认证")
            else:
                logger.info("🔓 MQTT使用匿名访问")
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            logger.info("✅ MQTT连接成功")
        except Exception as e:
            logger.error(f"❌ MQTT连接失败: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("MQTT已连接")
        else:
            logger.error(f"MQTT连接失败，代码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning("MQTT连接断开")
    
    def publish(self, topic: str, payload: dict):
        """发布MQTT消息"""
        if not self.connected:
            raise Exception("MQTT未连接")
        
        message = json.dumps(payload)
        result = self.client.publish(topic, message, qos=1)
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise Exception(f"MQTT发布失败: {result.rc}")
        
        logger.info(f"📤 MQTT发布成功: {topic}")
        return True

mqtt_client = MQTTClient()

# ============================================================
# 生命周期管理
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 启动服务，连接 MQTT...")
    mqtt_client.connect()
    yield
    # 关闭时
    logger.info("👋 关闭服务，断开 MQTT...")
    if mqtt_client.client:
        mqtt_client.client.loop_stop()
        mqtt_client.client.disconnect()

# ============================================================
# FastAPI 应用
# ============================================================

app = FastAPI(
    title="AIOT 插件后端服务",
    description="为外部插件提供设备操作服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 数据模型
# ============================================================

class SensorDataRequest(BaseModel):
    device_uuid: str
    sensor: str

class ControlRequest(BaseModel):
    device_uuid: str
    port_type: str
    port_id: int
    action: str
    value: Optional[int] = None

class PresetRequest(BaseModel):
    """预设指令请求"""
    device_uuid: str
    preset_key: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

class StandardResponse(BaseModel):
    code: int
    msg: str
    data: Any

# ============================================================
# API 接口
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "AIOT 插件后端服务",
        "version": "1.0.0",
        "status": "running",
        "mqtt_connected": mqtt_client.connected
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": SessionLocal is not None,
        "mqtt": mqtt_client.connected
    }

@app.get("/api/sensor-data")
async def get_sensor_data(device_uuid: str, sensor: str):
    """获取传感器数据（从 device_sensors 表查询，简单高效）
    
    Args:
        device_uuid: 设备UUID
        sensor: 传感器名称（中文或英文，如 "温度" 或 "temperature"）
    """
    logger.info(f"📊 查询传感器数据: device_uuid={device_uuid}, sensor={sensor}")
    
    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="数据库未连接")
    
    db = SessionLocal()
    try:
        # 映射传感器名称（支持中文和英文）
        sensor_map = {
            "温度": "temperature",
            "湿度": "humidity",
            "DS18B20": "ds18b20",
            "雨水": "is_raining",
            "雨滴": "is_raining",
            "是否下雨": "is_raining",
            "rain": "is_raining",
            "雨水级别": "rain_level",
        }
        
        # 获取实际的传感器键名
        actual_sensor_name = sensor_map.get(sensor, sensor.lower())
        logger.info(f"🔍 传感器名称映射: {sensor} → {actual_sensor_name}")
        
        # 直接从 device_sensors 表查询（使用 device_uuid，无需JOIN）
        sensor_data = db.query(DeviceSensor).filter(
            DeviceSensor.device_uuid == device_uuid,
            DeviceSensor.sensor_name == actual_sensor_name
        ).first()
        
        if not sensor_data:
            # 查询该设备的所有传感器
            all_sensors = db.query(DeviceSensor).filter(
                DeviceSensor.device_uuid == device_uuid
            ).all()
            
            available_sensors = [s.sensor_name for s in all_sensors]
            if available_sensors:
                available = ", ".join(available_sensors)
                raise HTTPException(
                    status_code=404,
                    detail=f"未找到传感器 '{sensor}' 的数据。可用传感器: {available}"
                )
            else:
                raise HTTPException(status_code=404, detail="设备尚未上报任何传感器数据")
        
        # 查询设备信息（用于返回设备名称）
        device = db.query(Device).filter(Device.uuid == device_uuid).first()
        device_name = device.name if device else "未知设备"
        last_seen = device.last_seen if device else None
        
        # 转换 value 为数字类型（Coze要求返回number类型）
        try:
            numeric_value = float(sensor_data.sensor_value)
        except (ValueError, TypeError):
            # 如果无法转换为数字，保留原值（可能是布尔值或其他类型）
            numeric_value = sensor_data.sensor_value
            logger.warning(f"⚠️  传感器值无法转换为数字: {sensor_data.sensor_value}")
        
        # 🔧 如果数据库中 sensor_unit 为空，根据传感器类型给出默认单位
        sensor_unit = sensor_data.sensor_unit
        if not sensor_unit or sensor_unit.strip() == "":
            # 默认单位映射
            default_units = {
                "temperature": "°C",      # 温度
                "humidity": "%",          # 湿度
                "ds18b20": "°C",         # DS18B20温度
                "is_raining": "",        # 雨水（布尔值，无单位）
                "rain_level": "级",      # 雨水级别
                "light": "lx",           # 光照
                "pressure": "Pa",        # 气压
                "altitude": "m",         # 海拔
                "distance": "cm",        # 距离
                "gas": "ppm",            # 气体浓度
                "soil_moisture": "%",    # 土壤湿度
                "voltage": "V",          # 电压
                "current": "A",          # 电流
                "power": "W"             # 功率
            }
            sensor_unit = default_units.get(actual_sensor_name, "")
            if sensor_unit:
                logger.info(f"💡 使用默认单位: {actual_sensor_name} → {sensor_unit}")
        
        logger.info(f"✅ 传感器数据: {sensor_data.sensor_name} = {numeric_value} {sensor_unit}")
        
        return StandardResponse(
            code=200,
            msg="成功",
            data={
                "value": numeric_value,  # 转换为数字类型
                "unit": sensor_unit,     # 使用默认单位（如果数据库为空）
                "sensor_name": sensor_data.sensor_name,
                "sensor_type": sensor_data.sensor_type or "",
                "timestamp": sensor_data.timestamp.isoformat() if sensor_data.timestamp else None,
                "device_name": device_name,
                "last_seen": last_seen.isoformat() if last_seen else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 查询传感器数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/control")
async def control_device(request: ControlRequest):
    """控制设备
    
    通过MQTT发送控制命令到设备
    """
    logger.info(f"🎮 控制设备: uuid={request.device_uuid}, "
                f"port={request.port_type}{request.port_id}, action={request.action}")
    
    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="数据库未连接")
    
    if not mqtt_client.connected:
        raise HTTPException(status_code=500, detail="MQTT未连接")
    
    db = SessionLocal()
    try:
        # 查询设备
        device = db.query(Device).filter(Device.uuid == request.device_uuid).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")
        
        # 打印设备信息
        logger.info(f"📱 查询到设备信息:")
        logger.info(f"   UUID: {device.uuid}")
        logger.info(f"   Device ID: {device.device_id}")
        logger.info(f"   名称: {device.name}")
        logger.info(f"   在线状态: {device.is_online}")
        
        # 构造控制命令
        port_type_lower = request.port_type.lower()
        
        # 生成portKey（与Web页面格式保持一致）
        if port_type_lower == "pwm":
            # PWM格式：pwm_m1, pwm_m2
            port_key = f"pwm_m{request.port_id}"
        else:
            # 其他格式：led_1, relay_2, servo_1
            port_key = f"{port_type_lower}_{request.port_id}"
        
        if port_type_lower == "led":
            control_cmd = {
                "portKey": port_key,
                "cmd": "led",
                "device_id": request.port_id,
                "action": request.action
            }
        elif port_type_lower == "relay":
            control_cmd = {
                "portKey": port_key,
                "cmd": "relay",
                "device_id": request.port_id,
                "action": request.action
            }
        elif port_type_lower == "servo":
            if request.action == "set" and request.value is not None:
                control_cmd = {
                    "portKey": port_key,
                    "cmd": "servo",
                    "device_id": request.port_id,
                    "action": "set",
                    "angle": request.value
                }
            else:
                raise HTTPException(status_code=400, detail="舵机控制需要指定angle值")
        elif port_type_lower == "pwm":
            if request.action == "set" and request.value is not None:
                control_cmd = {
                    "portKey": port_key,
                    "cmd": "pwm",
                    "device_id": request.port_id,
                    "action": "set",
                    "duty_cycle": request.value,
                    "frequency": 5000
                }
            else:
                raise HTTPException(status_code=400, detail="PWM控制需要指定duty_cycle值")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的端口类型: {request.port_type}")
        
        # 发送MQTT命令（使用 UUID）
        topic = f"devices/{device.uuid}/control"
        mqtt_client.publish(topic, control_cmd)
        
        logger.info(f"📤 MQTT主题: {topic}")
        logger.info(f"✅ 控制成功: {request.port_type}{request.port_id} -> {request.action}")
        
        return StandardResponse(
            code=200,
            msg="成功",
            data={"result": "success"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 控制设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/preset")
async def execute_preset(request: PresetRequest):
    """执行预设指令
    
    通过 preset_key 查找并执行设备配置中的预设指令
    支持序列指令（多步骤、延时）
    """
    logger.info(f"🎯 执行预设: uuid={request.device_uuid}, preset_key={request.preset_key}")
    
    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="数据库未连接")
    
    if not mqtt_client.connected:
        raise HTTPException(status_code=500, detail="MQTT未连接")
    
    db = SessionLocal()
    try:
        # 查询设备
        device = db.query(Device).filter(Device.uuid == request.device_uuid).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")
        
        logger.info(f"📱 设备: {device.name} ({device.device_id})")
        
        # 检查设备是否在线
        if not device.is_online:
            raise HTTPException(status_code=400, detail="设备离线，无法执行预设")
        
        # 从设备配置中查找预设
        device_settings = device.device_settings or {}
        preset_commands = device_settings.get("preset_commands", [])
        
        logger.info(f"📋 设备共有 {len(preset_commands)} 个预设指令")
        
        # 查找匹配的预设
        target_preset = None
        for preset in preset_commands:
            if preset.get("preset_key") == request.preset_key:
                target_preset = preset
                break
        
        if not target_preset:
            raise HTTPException(
                status_code=404,
                detail=f"未找到预设指令: {request.preset_key}"
            )
        
        preset_name = target_preset.get("name", request.preset_key)
        preset_type = target_preset.get("type", "single")
        
        logger.info(f"✅ 找到预设: {preset_name} (类型: {preset_type})")
        
        # 执行预设指令
        if preset_type == "sequence":
            # 序列指令：多步骤，支持延时
            steps = target_preset.get("steps", [])
            if not steps:
                raise HTTPException(status_code=400, detail="预设序列为空")
            
            logger.info(f"📝 序列包含 {len(steps)} 个步骤")
            
            executed_steps = []
            errors = []
            
            for index, step in enumerate(steps, 1):
                command = step.get("command")
                if not command:
                    error_msg = f"步骤 {index} 缺少 command 字段"
                    logger.error(error_msg)
                    errors.append({"step": index, "error": error_msg})
                    continue
                
                # 转换命令格式（将 value 转为 action）
                converted_command = command.copy()
                cmd_type = converted_command.get("cmd")
                
                # 确保包含portKey（如果命令中没有，则根据cmd和device_id生成）
                if "portKey" not in converted_command:
                    device_id = converted_command.get("device_id")
                    if device_id is not None:
                        if cmd_type == "pwm":
                            # PWM格式：pwm_m1, pwm_m2
                            converted_command["portKey"] = f"pwm_m{device_id}"
                        elif cmd_type in ["led", "relay", "servo"]:
                            # 其他格式：led_1, relay_2, servo_1
                            converted_command["portKey"] = f"{cmd_type}_{device_id}"
                
                if cmd_type in ["led", "relay"]:
                    if "value" in converted_command:
                        value = converted_command.pop("value")
                        converted_command["action"] = "on" if value in [1, True] else "off"
                    converted_command.pop("device_type", None)
                elif cmd_type == "servo":
                    converted_command.pop("device_type", None)
                elif cmd_type == "pwm":
                    if "device_id" in converted_command:
                        converted_command["channel"] = converted_command.pop("device_id")
                    if "duty" in converted_command:
                        converted_command["duty_cycle"] = converted_command.pop("duty")
                    converted_command.pop("device_type", None)
                
                # 发送MQTT消息
                try:
                    topic = f"devices/{device.uuid}/control"
                    mqtt_client.publish(topic, converted_command)
                    
                    delay = step.get("delay", 0)
                    
                    logger.info(f"✅ 步骤 {index}/{len(steps)} 执行成功 - 命令: {converted_command}")
                    
                    executed_steps.append({
                        "step": index,
                        "command": converted_command,
                        "delay": delay,
                        "status": "success"
                    })
                    
                    # 如果不是最后一步，执行延迟
                    if index < len(steps) and delay > 0:
                        logger.info(f"⏳ 等待 {delay} 秒...")
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    error_msg = f"步骤 {index} 执行失败: {str(e)}"
                    logger.error(error_msg)
                    errors.append({"step": index, "error": error_msg})
                    executed_steps.append({
                        "step": index,
                        "command": converted_command,
                        "delay": step.get("delay", 0),
                        "status": "failed",
                        "error": error_msg
                    })
            
            # 返回执行结果
            success_count = sum(1 for s in executed_steps if s.get("status") == "success")
            failed_count = len(executed_steps) - success_count
            
            logger.info(f"🎉 序列执行完成: {success_count} 成功, {failed_count} 失败")
            
            return StandardResponse(
                code=200,
                msg="成功",
                data={
                    "success": failed_count == 0,
                    "message": f"序列执行完成: {success_count} 成功, {failed_count} 失败",
                    "preset_name": preset_name,
                    "total_steps": len(steps),
                    "executed_steps": executed_steps,
                    "errors": errors if errors else None
                }
            )
        else:
            # 单次指令
            command = target_preset.get("command")
            if not command:
                raise HTTPException(status_code=400, detail="预设指令缺少 command 字段")
            
            # 确保包含portKey（如果命令中没有，则根据cmd和device_id生成）
            if "portKey" not in command:
                cmd_type = command.get("cmd")
                device_id = command.get("device_id")
                if cmd_type and device_id is not None:
                    if cmd_type == "pwm":
                        # PWM格式：pwm_m1, pwm_m2
                        command["portKey"] = f"pwm_m{device_id}"
                    elif cmd_type in ["led", "relay", "servo"]:
                        # 其他格式：led_1, relay_2, servo_1
                        command["portKey"] = f"{cmd_type}_{device_id}"
            
            # 发送MQTT命令
            topic = f"devices/{device.uuid}/control"
            mqtt_client.publish(topic, command)
            
            logger.info(f"✅ 单次预设执行成功: {preset_name}")
            
            return StandardResponse(
                code=200,
                msg="成功",
                data={
                    "success": True,
                    "message": f"预设 {preset_name} 执行成功",
                    "preset_name": preset_name
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 执行预设失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)

