-- 可重复执行：使用 INSERT IGNORE
-- 新增工作流可用节点类型配置（json）
INSERT IGNORE INTO `core_system_config`
(`config_key`, `config_value`, `config_type`, `description`, `category`, `is_public`)
VALUES
(
  'workflow_enabled_node_types',
  '["start","llm","http","knowledge","intent","string","end"]',
  'json',
  '工作流可用节点类型列表',
  'ai',
  1
);
