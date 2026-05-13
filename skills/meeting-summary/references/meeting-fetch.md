# Meeting Fetch Reference

## lark-vc — 历史会议列表

```bash
# 列出时间范围内的会议
lark-cli vc +meetings-list \
  --start-time "2026-05-12T00:00:00+08:00" \
  --end-time   "2026-05-13T12:00:00+08:00" \
  --format json --as user

# 响应字段
# meeting_id, topic, start_time, end_time, duration, host, participants[]
```

## lark-minutes — 妙记列表

```bash
# 列出妙记（按时间范围）
lark-cli minutes +list \
  --start-time "2026-05-12T00:00:00+08:00" \
  --end-time   "2026-05-13T12:00:00+08:00" \
  --format json --as user

# 响应字段
# token, title, duration, owner_id, create_time
```

## lark-minutes — 获取 AI 产物

```bash
# 总结（推荐先拉）
lark-cli minutes +get-summary   --token <minute_token> --as user

# 章节（结构化分段，带时间戳）
lark-cli minutes +get-chapters  --token <minute_token> --as user

# 待办
lark-cli minutes +get-todos     --token <minute_token> --as user

# 逐字稿（最详细，上下文最多，但 token 消耗大）
lark-cli minutes +get-transcript --token <minute_token> --as user
```

## 去重策略

VC meeting_id 和妙记 token 是不同系统，同一场会议两边都可能有记录。

匹配规则（按优先级）：
1. 时间窗口重叠（meeting start_time ± 5 min 与妙记 create_time 重叠）
2. 标题相似（edit distance < 3 或妙记标题包含 VC topic）
3. 参会人有交集（host / owner_id 相同）

匹配到则合并，以妙记内容为主（更结构化），VC 补充参会人列表。

## 错误处理

| 错误 | 原因 | 处理 |
|---|---|---|
| `403` on minutes | 无权访问该妙记 | 跳过妙记内容，用 VC 详情 |
| 空列表 | 时间范围内无会议 | 提示用户，正常结束 |
| 妙记总结为空 | AI 未生成或会议太短 | 改拉逐字稿，截取前 500 字 |
| VC list 无权限 | 非 admin 账号 | 只用妙记列表，不用 VC list |

## 参会人识别

从 VC participants 或妙记 transcript 中提取参会人：
- 内部人员（BytePlus）：`@bytedance.com` 邮箱域名
- 外部客户：其他域名 / 无邮箱 → 重点标注
- 对于只有 open_id 的参与者：尝试 `lark-cli contact +user-info --user-id <id>` 解析姓名

## 会议分类

根据参会人判断会议类型：
- **客户会议**：有外部参会人（≥1 个非 BytePlus 账号）
- **内部会议**：全员 BytePlus
- **1:1**：仅 2 人

内部会议和 1:1 也保留处理，但不写入客户 wiki 页面。
