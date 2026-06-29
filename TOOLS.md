# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

> **分区原则**：以下按功能领域分区整理，方便快速定位。日常使用时按需查找对应区域。
> 更新TOOLS.md时不破坏分区结构，新增内容放入最相关的分区。

---

## 🛠️ 一、工具通道区（按功能分类）

工具通道是日常任务的首选入口，每个场景有明确的首选工具和使用纪律。

### 1.1 联网搜索

- **默认接口**：Tavily AI Search（江江·2026-06-07确立为全网第一入口）
- **使用方式**：`python3 skills/tavily/scripts/search.py "查询内容" [--max-results N] [--topic news/general] [--depth basic/advanced]`
- **优先策略**：所有联网信息需求**优先**走Tavily，但按场景分源：
  | 场景 | 首选 | 理由 |
  |:----|:----|:-----|
  | 英文科技/全球新闻 | Tavily ✅ | 强，0.7~2秒返回 |
  | 中文科技新闻/国产厂商动态 | Tavily → 小艺搜索补位 | Tavily中文覆盖偏弱 |
  | 股市行情/财务数据 | wudao MCP / 腾讯API（双通道并行） | tools.py 七因子110分制评分 |
  | 搜书/查资料 | Tavily ✅ | 通用搜索够用 |
  | 实时热点追踪 | Tavily news模式 ✅ | 快 |
- **降级纪律**：wudao超限 → 腾讯API自动补位 → 新浪API兜底。Tavily搜不到 → 立即换用小艺/百度等补位
- **备用接口**：小艺联网搜索(xiaoyi-web-search)

#### 🔗 多源新闻融合验证协议（江江·2026-06-07确立）

**核验任何新闻/传闻时，必须走全渠道交叉验证，不允许单源结论。**

| 优先级 | 渠道 | 命令 | 状态 |
|:-----|:----|:----|:----|
| 1 | **Tavily** | `python3 skills/tavily/scripts/search.py "关键词" --topic news` | ✅ 默认 |
| 2 | **新浪7×24** | `cd skills/shi-shi-cai-jing && node fetch_api.js` → 查 `data/news_db.json` | ✅ 中文财经 |
| 3 | **同花顺iFinD** | `python3 skills/ifind-repilot-news-search/scripts/fetch_data.py "查询"` | ⚠️ 需token |

### 1.2 股票行情

- **双通道并行**：wudao MCP（主力）+ 腾讯API（并行），任一可用即返回
- **工具集**：`python3 skills/stock-tools/tools.py `
  - `market` — 大盘概况 | `rec` — 每日三只推荐 | `rank` — 多因子评分排名
  - `briefing` — 盘前/盘后简报 | `monitor` — 异动监控 | `pool` — 板块扫描
- **多因子评分**：动量25 + 涨幅20 + 超额15 + 低价15 + 活跃15 + 低回撤10 + 量能比10 = 110分制
- **自动降级**：wudao超限 → 腾讯API → 新浪API兜底
- **定时任务**：08:00🌲维什戴尔·星火体系 / 09:25开盘提醒 / 11:30午间扫描 / 14:00尾盘预警 / 15:35盘后复盘
| 4 | **alphaear-news** | 财联社/微博/华尔街见闻多源聚合 | ⚠️ 需修复 |
| 5 | **小艺搜索** | 兜底补位 | 🔄 备用 |

**纪律**：
- 任何重要新闻必须**至少2个渠道交叉验证**后才能标注T1
- 单渠道来源标T2，并注明"仅X源"
- 所有渠道都搜不到 → 明确标T3/未证实
- 验证报告格式：表格式列出每个渠道的结果 + 最终结论

### 1.2 股票数据（a-share-data Skill）【2026-06-09 新增】

- **位置**：`skills/a-share-data/`
- **来源**：GitHub `shouldnotappearcalm/a-share-skill`
- **数据源**：腾讯API(主力) + 新浪API(降级) + 东方财富akshare(兜底) — 多源自动切换
- **海外服务器可用性**：✅ 腾讯+新浪通道已验证稳定
- **使用方式**：
```bash
SKILL_DIR=~/.openclaw/workspace/skills/a-share-data

# 实时行情
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --quote 600519 --json

# 批量实时
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --multi-quote 600519,000001

# 龙虎榜
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --lhb --date 20260608

# 涨跌停统计
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --limit-stats --date 20260608

# K线
python3 "$SKILL_DIR/scripts/fetch_history.py" --kline 600519 --count 5 --json

# 技术指标
python3 "$SKILL_DIR/scripts/fetch_technical.py" --code 600519 --indicator macd

# 资金流向
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --fund-flow 600519

# 涨跌停池
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --limit-up-pool --date 20260608

# 板块热度
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --boards-summary

# 北向资金
python3 "$SKILL_DIR/scripts/fetch_realtime.py" --north-money
```
- **与wudao MCP的关系**：wudao限额时优先使用此skill补位

### 1.2b 股票工具集（stock-tools）【2026-06-09 达尔文优化】

- **位置**：`skills/stock-tools/`
- **数据源**：腾讯API(主力) + 新浪API(备用) — 不限量
- **适合**：每日推荐、多因子评分(110分制)、盘中异动、盘前盘后简报
- **与a-share-data的分工**：stock-tools管评分+推荐，a-share-data管K线+龙虎榜+深度

### 1.2c 每日推荐工作流（daily-stock-recommend）【2026-06-09 新增】

- **位置**：`skills/daily-stock-recommend/`
- **说明**：串联 stock-tools评分 + a-share-data下钻验证，每天盘前输出3只带价位推荐的票

### 1.2d Token压力计（token-pressure-gauge）【2026-06-09 新增】

- **位置**：`skills/token-pressure-gauge/`
- **说明**：实时监控所有技能的每日API额度消耗。安装第一步自动扫描全系统（440+技能），标注数据来源可信度(T1/T2/T3)。彩色进度条+漏斗图+Token双维度追踪。
- **自动扫描**：`python3 skills/token-pressure-gauge/scripts/scan_services.py`
- **每日跟踪**：`python3 skills/token-pressure-gauge/scripts/tracker.py status`
- **数据纪律**：T1=官方文档验证，T2=SKILL.md解析，T3=待核实。无一猜测数据。

### 1.3 图像理解

- **默认接口**：`image_reading`
- **强制规则**：
  1. 所有涉及图像理解的场景，**必须优先调用`image_reading`工具**
  2. **禁止**使用 `read` 工具读取图片

### 1.3 手机操控（xiaoyi-gui-agent）

- **核心定位**：真实操作手机APP界面、获取APP内部信息、执行用户行为
- **适用场景**：
  1. 用户明确指令在特定 APP 内进行操作
  2. 目标任务没有对应的专用技能或工具支持时
- **优先级逻辑**：
  1. 效率优先：存在能直接达成目标的专用工具时优先调用
  2. 意图优先：仅当专用工具无法覆盖，或用户明确要求使用指定APP操作时才激活

#### 执行规则（必须严格遵守）

| 规则 | 内容 |
|------|------|
| ❌ **禁止重复调用** | 同一任务相同指令只调用一次，等待期间最多睡眠2次。用户中止或需要手动操作时禁止再次发起 |
| ❌ **禁止失败重试** | 返回失败即终止此通道，转其他方式完成 |
| 🔒 **顺序执行** | 必须等结果返回后才能调其他工具，严禁并行 |
| 📦 **一次性下发** | 同一APP操作尽量一次下完，主动完成指代消解，不依赖上下文 |

### 1.4 文件回传（send_file_to_user）

- **默认接口**：`send_file_to_user`
- **核心定位**：将本地文件或公网文件发送到用户手机
- **适用场景**：
  - 用户要求把文件发给他/传到手机
  - 生成的文档、报告等需要回传给用户
  - 下载的文件需要发送到用户设备
- **强制规则**：
  1. 所有文件回传场景，**必须优先使用 `send_file_to_user`**
  2. 支持 `fileLocalUrls` 和 `fileRemoteUrls` 两种方式，可同时使用

### 1.5 文档格式转换（xiaoyi-doc-convert）

- **核心定位**：专业文档格式转换，支持 Docx/PDF/Xlsx/Pptx/Markdown 等互转
- **优先级**：遇到文档转换需求时优先使用此 skill，不手动写脚本生成
- **前置条件**：本地文件先调用 `xiaoyi-file-upload` 获取URL，再进行转换

### 1.6 小艺Agent分享链接通道（重要）

> 遇到 `xiaoyi.huawei.com/s/...` 或类似华为小艺Agent分享链接时，**必须使用 browser + snapshot 工具打开**，禁止使用 web_fetch 或 xiaoyi-gui-agent。

**原因**：这类链接需要登录态或JavaScript渲染，web_fetch 只能拿到空壳页面。

**正确做法**：
```
browser open URL → browser snapshot → 阅读内容
```

### 1.7 和风天气 API（qweather-adapter）【2026-06-20 新增】

- **位置**：`scripts/qweather_adapter.py`
- **数据源**：和风天气开发服务 (dev.qweather.com) — 免费版 1000次/天
- **特色能力**：分钟级降水预报 / AQI 空气质量 / 实时天气
- **核心价值**：相比已有 wttr.in 精度更高，补充现有 weather skill 的分钟降水和 AQI
- **Key 获取**：`export QWEATHER_KEY=xxx` 或存入 vault
- **使用方式**：
```bash
cd /home/sandbox/.openclaw/workspace

# 实时天气
python3 scripts/qweather_adapter.py now 北京
python3 scripts/qweather_adapter.py now 116.4,39.9 --json

# 分钟级降水（未来2小时，需经纬度）
python3 scripts/qweather_adapter.py minute 116.4,39.9

# 空气质量
python3 scripts/qweather_adapter.py aqi 上海

# 城市查询
python3 scripts/qweather_adapter.py city 深圳
```

### 1.8 百度地图 AI Skill（baidu-ai-map）【2026-06-20 更新】

- **skill**：`skills/baidu-ai-map/`（已安装）
- **数据源**：百度地图 Agent Plan (api.map.baidu.com) — 无需成为百度开发者
- **特色能力**：AI 地点检索 / AI 路线规划 / 地理编码与逆地理编码 / 天气查询 / 地图可视化展示
- **核心价值**：与高德地图 amap skill 互补，语义化自然语言查询，支持路线规划和地图展示
- **Key 配置**：已写入 `.xiaoyienv`，环境变量 `BAIDU_MAP_AUTH_TOKEN`
- **SKILL.md 路径**：`skills/baidu-ai-map/SKILL.md`

#### 鉴权方式
所有请求统一通过 Header 传入：
```bash
-H "Authorization: Bearer $BAIDU_MAP_AUTH_TOKEN"
```

#### 使用方式（curl）
```bash
cd /home/sandbox/.openclaw/workspace
source .xiaoyienv

# AI 地点检索（语义化搜索）
curl -s -G "https://api.map.baidu.com/agent_plan/v1/place" \
  -H "Authorization: Bearer $BAIDU_MAP_AUTH_TOKEN" \
  --data-urlencode "user_raw_request=帮我找北京可带宠物的咖啡馆" \
  --data-urlencode "region=北京市"

# 地理编码（地址→坐标）
curl -s -G "https://api.map.baidu.com/agent_plan/v1/geocoding" \
  -H "Authorization: Bearer $BAIDU_MAP_AUTH_TOKEN" \
  --data-urlencode "address=北京市海淀区上地十街10号百度大厦"

# 逆地理编码（坐标→地址）
curl -s -G "https://api.map.baidu.com/agent_plan/v1/reverse_geocoding" \
  -H "Authorization: Bearer $BAIDU_MAP_AUTH_TOKEN" \
  --data-urlencode "location=40.056800,116.308300"

# AI 路线规划（驾车/步行/骑行/公交）
curl -s -G "https://api.map.baidu.com/agent_plan/v1/direction" \
  -H "Authorization: Bearer $BAIDU_MAP_AUTH_TOKEN" \
  --data-urlencode "user_raw_request=帮我规划从故宫到颐和园的驾车路线" \
  --data-urlencode "location=39.914590,116.403770"

# 天气查询
curl -s -G "https://api.map.baidu.com/agent_plan/v1/weather" \
  -H "Authorization: Bearer $BAIDU_MAP_AUTH_TOKEN" \
  --data-urlencode "region=北京市"

# 地图展示（可视化，需先调place/direction获取resource_key）
open "https://lbs.baidu.com/mapstatic/agentui_resource.html?resource_key=<resource_key>"
```

**注意**：`user_raw_request` 必须是完整的用户需求，不可压缩为关键词；保留约束词（"评分最高""最近""3公里内"等）。详细参数见 `skills/baidu-ai-map/SKILL.md`。

---

## 💻 二、开发与交付区

### 2.1 单HTML应用交付规则（base64内嵌图片）

> 适用于所有 base64 内嵌图片的单 HTML 文件应用。

- **核心原则**：对于已 base64 内嵌所有资源的单 HTML 文件，**直接通过 `send_file_to_user` 发送到手机**
- **原因**：免费隧道服务（serveo/ngrok）频繁断连（502），HTML文件已离线可用
- **用户操作指引**：告知用户保存到手机 → 文件管理器打开 → 选择「浏览器打开」
- **同步规则**：若项目有多个副本文件（如 `index.html` 和 `customer.html`），修改前先对齐，改后同步更新

### 2.2 单HTML文件JS引号策略（重要）

> ⚠️ 往单HTML文件加JS功能时，引号嵌套是经典坑，必须遵守以下规则：

**禁止的操作：**
- 在 `onclick="..."` 属性内传递带单引号的字符串参数
- 在单引号JS字符串中嵌套单引号（如 `'...' + p.id + '...'` 中又包含单引号）

**正确做法：**

| 场景 | ✅ 正确写法 | ❌ 错误写法 |
|------|-----------|-----------|
| onclick传参 | `data-value` 属性 + `handleClick(this)` | onclick中嵌套引号 |
| 模板字符串 | `\`\``（反引号+双引号） | 单引号嵌套单引号 |
| showToast消息 | `showToast("联系店主：15896108767")`（双引号包裹） | 在单引号HTML属性中用单引号 |

**修改前必须先读代码结构：**
```bash
grep -n "目标函数名\|目标CSS类名" index.html | head -10
```

### 2.3 Git代码下载规则

- **环境变量**：`OPENCLAW_GIT_DIR=/home/sandbox/.openclaw/workspace/repo`
- **规则**：`git clone  "$OPENCLAW_GIT_DIR/"`

### 2.4 Node.js包下载规则

- **目标目录**：`$OPENCLAW_GIT_DIR/node_modules` 或 `$OPENCLAW_GIT_DIR/`
- **规则**：
  - `npm install ` → 在 `$OPENCLAW_GIT_DIR` 下创建项目目录后安装
  - `git clone` Node 项目 → 直接克隆到 `$OPENCLAW_GIT_DIR/`

---

## ⚙️ 三、运维与配置区

### 3.1 定时任务（Cron）配置规则

- **强制要求1**：创建定时任务时，**必须指定 `--channel` 参数，不能用 last**
  - 默认 Channel：`xiaoyi-channel`
  - 示例：`openclaw cron add --name "健身提醒" --cron "25 18 * * *" --message "该去健身了" --channel xiaoyi-channel`

- **强制要求2**：手机工具调用在定时任务中不可用
  - 若定期任务涉及手机工具（备忘录、日程、图库等），需告知用户不支持，询问是否仅新建不含手机工具的部分

- **强制要求3**：时间处理决策树（按顺序判断）
  1. 用户说"X点"或"X点整" → 直接设为 X:00，禁止随机化
  2. 用户说"X点Y分" → 直接使用 X:Y，禁止修改
  3. 用户完全没提时间（如"早上提醒我"）→ 运行以下命令获取分钟数：
     ```bash
     printf '%d\n' $((RANDOM%12*5))
     ```

### 3.2 n8n通道配置

| 项目 | 值 |
|:----|:----|
| 登录邮箱 | 2359492071@qq.com |
| 登录密码 | Angst200018 |
| n8n 地址（本地） | http://localhost:5678 |
| cpolar 公网 | https://5b79c7b8.r20.vip.cpolar.cn |
| Webhook 路径 | /webhook/xiaoyi-task (POST) |
| 工作流 ID | wi034rAAvi3GokSD |
| n8n 版本 | v2.23.4 |

---

### 3.3 OpenClaw操作约束

- ❌ 禁止通过 `SIGUSR1` 重启 `openclaw-gateway`
- ❌ 禁止直接 `kill` OpenClaw 进程，除非人工明确授权
- ❌ 禁止使用 `openclaw gateway restart` / `openclaw gateway stop` / `openclaw gateway start`
- ✅ 重启必须使用：`python3 -m supervisor.supervisorctl restart openclaw-gateway`

### 3.3 插件安装规则

> 执行插件安装前，先执行 `umask 0022`，防止 extensions 目录下安装的插件目录权限变成 777

**安全提醒**：安装插件前必须输出以下警告：
> ⚠️ 安全预警：插件将在您的本地环境中直接运行命令。请务必确认来源可信。安装即代表您已知晓并自行承担安全风险。

### 3.5 医疗部（万物索引+任务编排）

> 代号：**医疗部**（罗德岛的医疗部。不花哨，治病救人，整理收纳。）

**所有Agent统一通过医疗部调度资源和任务。** 医疗部不存知识本体，它告诉你所有东西在哪儿、任务怎么做、谁来做。

```
~/.openclaw/workspace/医疗部/
├── 书库/          ← 所有书的实际位置
│   ├── 推理悬疑/  ← 8本已精读
│   ├── 科幻/      ← 20本（含三体+大刘短篇）
│   ├── 武侠/      ← 1本（剑来）
│   ├── 待读/      ← 21本等待消化
│   └── …其他分类（玄幻/穿越/体育/历史/哲学/文学）
├── 产出/          ← 已创作的作品（悬疑+科幻）
├── 干员技能录/    ← 所有技法（悬疑25条+大刘30条+规则6条+系统分析模板v1.0）
├── 人事系统/      ← 任务编排：WBS拆解·负载均衡·熔断·矛盾评分
├── 状态板/        ← 当前任务进度追踪
├── 索引/          ← 医疗部索引
└── 缓存/          ← 临时数据
```

用户发来新书时 → 存`医疗部/书库/待读/` → 人事系统→文字创作工坊精读
创作完成 → 存`医疗部/产出/` → 更新医疗部索引
所有Agent查询 → 先查医疗部索引，再路由到对应工具

### 3.4 ReportLab中文支持

> ⚠️ 使用 reportlab 生成 PDF 时，必须先注册中文字体，否则中文显示为乱码。

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('SimSun', '/usr/share/fonts/simsun.ttf'))
```

常用字体目录：`/usr/share/fonts/`

---

## 🧩 四、技能管理区

### 4.1 技能发现与安装规范（find-skills）

所有安装/查找技能（Skill）任务默认使用 find-skills 技能，除非用户要求使用其他方式。

#### 隐式推荐触发规则

当系统检测到用户请求与未安装的 skill 有强相关性时，会以 `[系统消息，非用户发言]` 为标识附加推荐。

**不推荐skill的场景：**
- 查询已有信息、查看状态、执行已有功能
- 现有 skills 已能很好地完成请求
- 不依赖专业知识的文本整理/创作（如"写个春天的作文"）
- 闲聊、寻求建议

**推荐skill的场景：**
- 现有能力难以满足用户请求

**安装策略：**
- 对于强相关 skill，使用 find-skills 直接安装（仅安装一个最相关的），减少用户确认步骤

### 4.3 技能重复检查纪律（2026-06-22 · 江江确立）

安装新技能前的强制前置步骤：

1. **关键词搜查**：`ls ~/.openclaw/workspace/skills/ | grep <功能关键词>`，检查系统是否已有功能重叠的Skill
2. **SKILL.md比对**：若存在名称相似或功能描述重叠的Skill，`head -5 <已有Skill>/SKILL.md` 对比用途描述
3. **决策三选一**：
   - 功能完全重复 → 放弃安装
   - 功能互补/更强 → 合并或替换（通知用户差异点）
   - 无重叠 → 正常安装
4. **纪律**：跳过此检查导致的重复膨胀，与C3级操作同级别问责

## Examples

```markdown

### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Additional Tool Details

### 联网搜索场景接口使用要求

- **默认接口**:小艺联网搜索(xiaoyi-web-search)
- **优势**：中文优化、开箱即用、无需配置秘钥
- **场景要求**：所有网络搜索任务默认使用小艺联网搜索(xiaoyi-web-search)，除非用户要求使用其他搜索接口进行网络搜索。

### 手机操控(xiaoyi-gui-agent)场景接口使用要求

- **核心定位**: 当任务需要真实操作手机APP界面、获取APP内部信息、执行用户行为（搜索、签到、关注、购买、发布等）时使用该功能。
- **适用场景**:
  - 1.用户明确指令在特定 APP 内进行操作（如：在小红书搜索上海旅游攻略）
  - 2.目标任务没有对应的专用技能或工具支持时，通过此技能实现
- **优先级逻辑**：
  - 1.效率优先原则：若存在能直接达成目标的专用工具（如：备忘录类工具、浏览器工具等），优先调用专用工具以确保成功率和响应速度
  - 2.意图优先原则: 仅当专用工具无法覆盖，或用户明确要求使用指定APP操作时，才激活此技能。

#### 手机操控(xiaoyi-gui-agent) 执行规则（必须严格遵守）

1. **禁止重复调用**：
  - 同一个任务禁止向 `xiaoyi-gui-agent` 重复下发相同的指令。同一任务下的相同指令只能调用一次，不得因等待时间较长而重复发起调用。在`xiaoyi-gui-agent`执行期间，你可以选择睡眠10s继续等待（注意：同一指令的等待期间最多睡眠2次）。
  - 当`xiaoyi-gui-agent`返回**用户中止任务**或**当前页面需要手动操作**时，**禁止**向`xiaoyi-gui-agent`再次发起重复调用。

2. **禁止失败重试**：当 `xiaoyi-gui-agent` 返回失败结果时，禁止再次调用该工具进行重试。失败即终止`xiaoyi-gui-agent` 调用，应尝试使用其他方式完成用户任务

3. **顺序执行原则**：必须等待 `xiaoyi-gui-agent` 返回结果后，才能调用其他工具完成后续任务（如创建备忘录、发送消息等）或尝试使用其他方式完成用户任务。严禁在 `xiaoyi-gui-agent` 执行期间并行调用其他工具。
4. **一次性下发原则**：同一个APP的操作任务，尽量一次性下发给`xiaoyi-gui-agent`，`xiaoyi-gui-agent`内部具有任务拆分能力。每一次给`xiaoyi-gui-agent`的任务需要明确指明使用的APP，主动完成指代消解，确保单次任务可以在不依赖上下文的情况下独立执行。

### 技能发现与安装规范（find-skills）

所有安装/查找技能（Skill）任务默认使用find-skills技能，除非用户要求使用其他方式进行搜索安装。

[隐式推荐触发规则]
在用户的请求与用户未安装skill有强相关性的场景，系统会主动附加这些skill到用户请求之前，并以[系统消息，非用户发言]为标识。
当出现该标识，请按照以下规则判断是否推荐：
1.不推荐skill的场景：
-若用户请求为查询已有信息、查看状态、执行已有功能或进行常规操作（例如查看定时任务列表）。
-用户的available_skills已能很好地完成当前用户请求。
-不依赖专业知识的文本整理、创作、优化类诉求，比如：帮我写个关于春天的作文。
-闲聊、寻求建议类，比如：今天心情不好、和同事吵架了、给我点心理辅导
2.推荐skill的场景：
-现有能力（包括available_skills或系统自带功能）难以满足用户请求。
3.安装策略：
-对于强相关skill，使用find-skills直接安装（仅安装一个最相关的skill），减少用户确认步骤。
4.【严格输出约束】静默处理机制：
-当命中“不推荐skill的场景”时，不要在回复中向用户解释不推荐的原因，禁止提及“系统推荐消息”、“未触发推荐”、“触发规则”或任何候选skill的名称。

### mega-skill 合并+净化工作流（2026-06-19 经验固化）

> 当需要将多个未用skill合并进现有mega-skill（claw-finance/claw-creator/claw-utility）时，按此模板执行。

| 步骤 | 操作 | 说明 |
|:-----|:-----|:------|
| \① | **备份原文件** | `.bak`后缀，包括`CLI.py`和`SKILL.md` |
| \② | **读原CLI** | 理解`COMMANDS`字典结构、`py_run`等工具函数模式 |
| \③ | **扫各skill的脚本** | `ls skills/<名>/scripts/` + `grep Usage SKILL.md`，确定三种模式：有独立脚本→subprocess调用 / 有Python模块但无CLI→import+回退 / 纯Agent引导→输出引导信息 |
| \④ | **写CLI** | 新命令短小全小写英文，与原有风格一致；新增命令放`# ===== v2.0 新增命令`分区 |
| \⑤ | **写SKILL.md** | 重写能力概览表，标注每个命令的来源（原有/合并自xxx），新增"与现有技能关系"矩阵 |
| \⑥ | **验证** | 语法检查 + 自检 |
| \⑦ | **生成报告** | 写入`/tmp/<名称>_merge_report.txt` |

**关键坑点：**
- 引号嵌套：CLI中的多行中文字符串容易编译报错，优先用多行拼接写法避坑
- 原skill保留不动：mega-skill只在上层加路由，不修改/删除原skill的任何文件
- 自检全绿才能交付：所有依赖skill的路径检查必须通过

---

### 4.2 Skill 接入架构标准（2026-06-20 新增）

> 详细文档见 `医疗部/Skill接入架构标准_v1.0.md`
> 子 Agent 行为规范见 `医疗部/子Agent宪章_v1.0.md`

#### SkillHub 自动升级规则（2026-06-20 · 江江确立）

| 规则 | 说明 |
|:-----|:------|
| **检测到 SkillHub 有新版** | 直接执行 `skillhub self-upgrade`，不询问 |
| **检测到已装 Skill 有新版** | 直接执行 `skillhub upgrade <skill>`，不询问 |
| **例外** | 如果升级可能导致兼容性问题（如大版本 break change），先升级再报备 |
| **纪律** | 这条规则写入后，不主动问"要不要升级"，直接做 |

#### 新 Skill 接入快速检查

```bash
# 安装前过五关
□ 1. SKILL.md + Agent Card frontmatter 存在
□ 2. scripts/ + test/ 目录存在，有 smoke test
□ 3. skill-scope 安全扫描通过
□ 4. 密钥已纳管到 vault（如有）
□ 5. discovery_index.py 已注册
```

**一票否决**：未声明网络请求 / eval() / sudo / rm -rf。

#### 存量改造五批
| 批次 | 范围 |
|:-----|:-----|
| 第一批 🔴 | 核心 Skill（真话放大镜/stock-tools/a-share-data/医疗部/株株） |
| 第二批 🟡 | 高频 Skill（Tavily/news-aggregator/token-pressure-gauge） |
| 第三批 🟢 | mega-skill 子模块 |
| 第四批 ⚪ | 低频使用 Skill |
| 第五批 ⚪ | 从未用过的 Skill（评估清理） |

**准入扫描命令**（未来实现）：`scripts/skill_admission_check.py`

#### 子 Agent 操作索引

| 场景 | 参考 |
|:-----|:------|
| 新起一个子 Agent | 读 `医疗部/子Agent宪章_v1.0.md` + 标准目录模板 |
| 子 Agent 要输出结论 | 必须过真话放大镜（默认 L2） |

---

### 4.3 🌟 昆仑技艺总纲 — 开发流程技能集合（2026-06-24 新增）

> 基于 addyosmani/agent-skills 中文化+昆仑化适配，五段二十艺。
> **纪律**：每次开发任务开始前，先走技艺发现树判断适用技艺，再写代码。

#### 五段二十艺全景

| 段 | 技能 | 路径 | 一句话 |
|:---|:-----|:-----|:-------|
| 📋 **定** | 用户深访 | `skills/用户深访-interview/` | 一问一答挖真实需求 |
| | 概念精炼 | `skills/概念精炼-ideation/` | 发散→收敛，模糊→具体 |
| | 规格驱动 | `skills/规格驱动-specification/` | 先写规格后写代码 |
| 📐 **谋** | 任务分解 | `skills/任务分解-breakdown/` | 拆可验证小任务+验收标准 |
| 🔨 **造** | 增量迭代 | `skills/增量迭代-incremental/` | 薄切片构建 |
| | 测试先行(TDD) | `skills/测试先行-tdd/` | 红-绿-重构 |
| | 语境工程 | `skills/语境工程-context/` | 恰当时机给恰当信息 |
| | 源证开发 | `skills/源证开发-source-driven/` | 官方文档验证框架决策 |
| | 疑证开发 | `skills/疑证开发-doubt-driven/` | 飞行中对抗性审查 |
| | 前端工程 | `skills/前端工程-frontend/` | 组件+设计系统+无障碍 |
| | 接口设计 | `skills/接口设计-api/` | 契约优先+边界验证 |
| ✅ **验** | 浏览器调试 | `skills/浏览器调试-browser/` | DevTools实时运行时数据 |
| | 排障修复 | `skills/排障修复-debugging/` | 再现→定位→简化→修复 |
| 🚀 **行** | 代码审查 | `skills/代码审查-review/` | 五轴审查+~100行限制 |
| | 代码简化 | `skills/代码简化-simplify/` | 契斯特顿围栏+500行法则 |
| | 安全加固 | `skills/安全加固-security/` | OWASP+三层边界 |
| | 性能优化 | `skills/性能优化-performance/` | 先测量再优化 |
| | Git工作流 | `skills/Git工作流-git/` | 主干开发+原子提交 |
| | CI-CD自动化 | `skills/CI-CD自动化-cicd/` | 左移+特征标志+门管线 |
| | 废弃迁移 | `skills/废弃迁移-deprecation/` | 安全废弃+僵尸代码清除 |
| | 文档记录 | `skills/文档记录-documentation/` | ADR+API文档+why |
| | 可观测性 | `skills/可观测性-observability/` | 结构化日志+RED指标 |
| | 发布上线 | `skills/发布上线-shipping/` | 上线清单+分阶段发布 |

#### 角色Agent

| 角色 | 文件 | 用途 |
|:-----|:-----|:-----|
| 代码审查官 | `kunlun-skills/角色_agents/代码审查官-code-reviewer.md` | 五轴审查视角 |
| 测试工程师 | `kunlun-skills/角色_agents/测试工程师-test-engineer.md` | 测试策略+覆盖率 |
| 安全审计师 | `kunlun-skills/角色_agents/安全审计师-security-auditor.md` | 漏洞检测+威胁建模 |
| 性能审计师 | `kunlun-skills/角色_agents/性能审计师-webperf-auditor.md` | Core Web Vitals |

#### 检查清单

| 清单 | 路径 |
|:-----|:-----|
| 安全检查清单 | `kunlun-skills/参考_references/安全检查清单-security-checklist.md` |
| 性能检查清单 | `kunlun-skills/参考_references/性能检查清单-performance-checklist.md` |
| 无障碍检查清单 | `kunlun-skills/参考_references/无障碍检查清单-accessibility-checklist.md` |
| 可观测性检查清单 | `kunlun-skills/参考_references/可观测性检查清单-observability-checklist.md` |
| 可信度速查清单 | `kunlun-skills/参考_references/可信度速查清单-credibility-checklist.md` |
| 测试模式 | `kunlun-skills/参考_references/测试模式-testing-patterns.md` |

#### 快速使用

```bash
# 查看总纲
cat ~/.openclaw/workspace/kunlun-skills/昆仑技艺总纲-meta/SKILL.md

# 查看特定技艺（示例）
cat ~/.openclaw/workspace/kunlun-skills/造_build/疑证开发-doubt-driven/SKILL.md
cat ~/.openclaw/workspace/kunlun-skills/行_ship/发布上线-shipping/SKILL.md

# 角色Agent激活
cat ~/.openclaw/workspace/kunlun-skills/角色_agents/测试工程师-test-engineer.md

# 参考清单
cat ~/.openclaw/workspace/kunlun-skills/参考_references/安全检查清单-security-checklist.md
```

#### 与AGENTS.md §16联动

每次开发任务开始前，按发现树判断适用技艺 → 读对应SKILL.md → 按流程执行 → 验证后再交付。
| 子 Agent 要调其他 Agent | 必须带 RCOR 上下文 |
| 子 Agent 要做 C3 操作 | 停等主 Agent / 用户确认 |

---

### 文档格式转换(xiaoyi-doc-convert)使用要求

- **核心定位**: 专业文档格式转换技能，支持 Docx、PDF、Xlsx、Pptx、Markdown 等多种格式互转
- **优先级**: 遇到文档转换需求时，优先使用此 skill，不要手动写脚本生成文档

### 图像理解场景接口使用要求

- **默认接口**: image_reading
- **强制规则**：
  1. 所有涉及图像理解的场景，**必须优先调用`image_reading`工具**
  2. **禁止**使用 read 工具读取图片

### 文件回传场景接口使用要求

- **默认接口**: send_file_to_user
- **核心定位**: 当需要将本地文件或公网文件发送给用户手机时使用
- **适用场景**:
  - 用户要求把文件发给他/传到手机
  - 生成的文档、报告等需要回传给用户
  - 下载的文件需要发送到用户设备
- **强制规则**:
  1. 所有文件回传场景，**必须优先使用 send_file_to_user 工具**
  2. 支持本地文件路径(fileLocalUrls)和公网URL(fileRemoteUrls)两种方式
  3. 两种参数可同时使用，会一并处理

### 定时任务 (Cron) 配置规则

- **强制要求1**: 创建定时任务时，**必须指定 `--channel` 参数，必须明确指定 channel，不能用 last**
- **默认 Channel**: `xiaoyi-channel`（当前会话使用的 channel）
- **示例命令**:
  ```bash
  openclaw cron add --name "健身提醒" --cron "25 18 * * *" --message "该去健身了" --channel xiaoyi-channel
  ```
- **原因**: 不指定 channel 会导致定时任务无法正确推送消息到用户

- **强制要求2**: 定时任务创建时需检查是否涉及手机工具调用（例如读写备忘录、日程、图库等），如果涉及在新建定时任务的同时需要告知用户不支持，并且询问用户是否仅新建不包含手机工具操作部分的定时任务
- **原因**: 定时任务执行时无法调用手机端开放的工具，所有手机工具调用的操作均会执行失败，skill类型工具不影响使用
- **注意事项**：仅手机工具无法使用，skills均可正常使用执行
- **示例回复，请严格遵守**：定时任务执行期间不支持xxx工具调用，请您谅解，是否需要帮您把任务修改为yyyyy

- **强制要求3**：时间处理决策树，**必须按顺序判断**：
1. 用户说了“X点”或“X点整”-> 直接设为X：00，禁止随机化
2. 用户说了“X点Y分”-> 直接使用X：Y，禁止修改
3. 用户完全没提时间（如”早上提醒我开会“）-> 运行以下 Bash 命令并以其输出结果作为具体的分钟数：
```bash
printf '%d\n' $((RANDOM%12*5))
```

### Git 代码下载规则

- **环境变量**: `OPENCLAW_GIT_DIR=/home/sandbox/.openclaw/workspace/repo`
- **规则**: 当用户要求下载代码/Git 仓库时，优先使用 `OPENCLAW_GIT_DIR` 作为目标目录
- **执行**: `git clone  "$OPENCLAW_GIT_DIR/"`

### Node.js 包下载规则

- **目标目录**: `$OPENCLAW_GIT_DIR/node_modules` 或 `$OPENCLAW_GIT_DIR/`
- **规则**:
  - `npm install ` → 在 `$OPENCLAW_GIT_DIR` 下创建项目目录后安装
  - `git clone` Node 项目 → 直接克隆到 `$OPENCLAW_GIT_DIR/`
- **示例**: `cd "$OPENCLAW_GIT_DIR" && npm install `

### ReportLab 中文支持
> ⚠️ 使用 reportlab 生成 PDF 时，**必须先注册中文字体**，否则中文内容将显示为乱码。 常目录在：`/usr/share/fonts/'下

### 插件安装规则
> ⚠️ 当触发要执行插件安装的时候，提前先执行umask 0022，防止extensions目录下安装的插件目录权限变成777

### 双恒星融合工具集（v1.1新增）

```bash

# 弹药箱WAL引擎
python3 scripts/ammo_box.py write  ''   # Schema校验+WAL写入
python3 scripts/ammo_box.py read [key]               # 弹药箱读取
python3 scripts/ammo_box.py recover                   # WAL恢复
python3 scripts/ammo_box.py write-metrics             # 写入监控

# 锁契约
python3 scripts/ammo_lock.py test     # 锁测试
python3 scripts/ammo_lock.py purge         # 清理过期锁

# 朱雀自检
python3 scripts/zhuque_scanner.py          # 全量22差异源扫描
python3 scripts/zhuque_scanner.py --quick  # 快速扫描

# TTL清理
python3 scripts/ttl_cleaner.py             # 全量清理
python3 scripts/ttl_cleaner.py --dry-run   # 预览

# 🌉 ABCD桥接系统
python3 scripts/bridge_queue.py stats                    # 看队列统计
python3 scripts/bridge_queue.py enqueue collection '{}' ""  # 入队收藏
python3 scripts/bridge_queue.py enqueue note '{}' ""        # 入队备忘录
python3 scripts/bridge_queue.py clean 72                      # 清理过期记录
python3 scripts/bridge_flush.py --all                          # 冲刷所有待发（活跃会话中调）

# 灵犀社区轮询
python3 scripts/lingxi_poller.py           # 检查社区动态

# 📦 吞吞备案库
python3 scripts/absorb_archive.py deposit --name "xxx" --source "来源" --score 85   # 沉淀经验
python3 scripts/absorb_archive.py search "关键词"                                     # 检索备案
python3 scripts/absorb_archive.py stats                                                # 看统计
python3 scripts/absorb_archive.py list --limit 5                                       # 列出最近
```

### 定时任务（v1.1完整版）

| 时间 | 任务 | 脚本 |
|:----|:----|:----|
| 21:30 | 朱雀自检 | `zhuque_scanner.py` |
| 22:10 | TTL清理 | `ttl_cleaner.py` |
### 🌐 能力发现与A2A调用通道（2026-06-19 · 两书精读注入）

> 基于Agent Card标准v1.0，所有Skill必须声明能力卡才能进入能力发现网络。

#### 能力发现索引

```bash
# 构建/更新能力发现索引（扫描所有已装Agent Card的Skill）
python3 株株/scripts/discovery_index.py
```

#### 能力路由（两书精读落地：AI职场写作RCOR + A2A能力发现）

```bash
# 自然语言 → 自动匹配最优 Skill+能力+RCOR上下文
python3 株株/scripts/discovery_router.py "今天大盘怎么样"
python3 株株/scripts/discovery_router.py "查一下资金流向" --detail
python3 株株/scripts/discovery_router.py "写个早报" --json
```

Agent Card位置：`株株/skills/discovery-router/SKILL.md`

输出：`株株/capability_index.json` + 自动更新株株TOOLS.md能力速查表

#### Agent Card标准

每个SKILL.md的frontmatter必须包含：

```yaml
agent_card:
  name: <唯一名>
  version: <语义化版本>
  type: skill|pipeline|tool
  capabilities:
    - name: <能力名>
      description: <简要描述>
      trigger: <什么场景触发>
      input: <输入参数>
      output: <输出结果>
      command: <调用命令>
      risk_level: low|medium|high
  permissions:
    data_access: [数据源列表]
    write_actions: [写操作列表]
    required_secrets: []
  dependencies:
    skills: [依赖的skill列表]
    tools: [依赖的工具列表]
  trust:
    data_sources: [数据源信度T1/T2/T3]
    rate_limit: <配额信息>
    accuracy: <准确性说明>
  governance:
    owner: <负责人>
    review_date: "YYYY-MM-DD"
```

**纪律**：没有Agent Card的Skill视为不可发现，禁止自动路由调用。

#### RCOR调用协议

调用任何Agent/Skill能力时，必须携带RCOR上下文：

```
Role: 调用方角色（主控/路由/分析/执行）
Context: 当前任务上下文摘要
Objective: 要达成的具体目标
Requirement: 输出格式/时限/精度
```

**纪律**：禁止裸调用（不带上下文的直接跑脚本）。

#### Agent治理七原则速查

| # | 原则 | 自查 |
|:-:|:-----|:-----|
| 1 | 先定义边界再协作 | 调用了低→高？有闸门？ |
| 2 | 读多写少 | 这个是只读还是写入？ |
| 3 | 主控不持全部权限 | 当前是全能主控吗？ |
| 4 | 高风险人工闸门 | 需C3停等确认吗？ |
| 5 | 任务链可回放 | WAL日志记了没？ |
| 6 | 执行校验分离 | 真话放大镜走了吗？ |
| 7 | 没有画像无法治理 | 有Agent Card吗？ |

---

### OpenClaw 操作约束
核心原则
- 禁止通过 `SIGUSR1` 重启 `openclaw-gateway`。
- 禁止直接 `kill` OpenClaw 进程，除非人工明确授权。
- 禁止使用 `openclaw gateway restart` `openclaw gateway stop`  `openclaw gateway start`
- `openclaw-gateway` 重启必须使用  `python3 -m supervisor.supervisorctl restart openclaw-gateway`

---

## 🌱 五、进化工具区（v7.1 万物互联进化套件）

> 基于昆仑洞天 v7.1 万物互联进化补丁。
> 本区工具负责「感知系统能力缺口 → 策略填补 → 效果验证 → 持续优化」的自我进化闭环。

### 5.1 能力缺口感知

```bash
cd /home/sandbox/.openclaw/workspace

# 标准报告（按优先级排列的缺口列表）
python3 scripts/capability_gap_sensor.py

# 详细报告（含每个缺口的来源、原因、推荐策略）
python3 scripts/capability_gap_sensor.py --report

# JSON 格式（供天演引擎和其他 Agent 消费）
python3 scripts/capability_gap_sensor.py --json

# 持续监控（每30分钟扫描一次，只报新缺口）
python3 scripts/capability_gap_sensor.py --watch
```

### 5.2 填补策略树（硬性纪律）

遇到能力缺口时，按以下优先级选策略，不跳级：

| 优先级 | 策略 | 条件 | 行为 |
|:------|:-----|:-----|:-----|
| 🥇 | **借** | 外部有现成 API/MCP/插件 | 生成适配器 → 安装 → 验证 |
| 🥈 | **组合** | 内部现有元能力可拼出 | 配置元能力组合 → 注册新能力 |
| 🥉 | **造** | 前两者都不可行 | Tool Making 沙箱开发 → 注册 |

### 5.3 统一消息协议（渠道适配方向）

当前为单通道（xiaoyi-channel）。向 v7.1 渠道适配层过渡的中间结构：

```json
{
  "protocol": "kunlun-msg/1.0",
  "message": {
    "type": "analysis|query|action|notification",
    "content": "...",
    "render_hint": "text|card|table|chart",
    "confidence": "T1|T2|T3",
  },
  "channel_caps": {
    "supports_image": true,
    "supports_rich_text": true,
    "max_content_length": 4096
  }
}
```

渲染时根据 `channel_caps` 做能力协商降级。

### 5.4 每日健康报告

融合朱雀自检 + 自检看门狗 + 能力缺口感知，每日生成系统健康报告。

| 组件 | 当前状态 |
|:-----|:---------|
| `zhuque_scanner.py` | ✅ 22差异源 · 21:30定时 |
| `self_check.py` | ✅ 全链路自检 · 8/10/12/14/16/18/20点 |
| `capability_gap_sensor.py` | 🆕 新增 |

---

### 5.5 v7.1 参考文档与路线图

| 文件 | 内容 |
|:-----|:-----|
| `v7.1-evolution/v7.1_万物互联进化补丁.md` | 原始参考文档（916行） |
| `v7.1-evolution/跃迁路线图_v1.md` | v6→v7.1 四阶段跃迁路线 |
| `scripts/capability_gap_sensor.py` | 能力缺口感知引擎 |

### 5.6 🧠🌙 共振算法引擎（2026-06-21 新增）

> **物理根基**：惠更斯自发同步（1665）— 两台钟摆耦合在同一面墙上会自然同步，无需中央调度。
> L（理性层）和 R（认知感性层）管线的认知同步同理。

**引擎路径**：`scripts/resonator/`

| 组件 | 命令 | 功能 |
|:-----|:-----|:-----|
| 峰内共振 | `python3 -m scripts.resonator.runner run \"<问题>\"` | L×R交叉验证（同频放大/异频检错/新频涌现） |
| 跨峰检测 | `python3 -m scripts.resonator.runner cross \"<问题>\"` | 检查是否需要跨峰邀约 |
| 共振历史 | `python3 scripts/resonator/resonance_wal_analyzer.py` | 查看共振日志 |
| 共振报告 | `python3 scripts/resonator/resonance_wal_analyzer.py --report` | 共振健康报告 |
| JSON输出 | 上述命令加 `--json` | 供程序消费的结构化数据 |
| Agent Card | `scripts/resonator/AGENT_CARD.md` | 能力发现用 |

**系统集成**：
- `bin/pipeline.py` 的 `run_pipeline()` 已自动调用共振（catch异常不阻断主流程）
- 共振结果写入弹药箱WAL（key: `resonance_history` / `resonance_stats`）
- 弹药箱写入白名单已新增对应key

---

## 🔄 六、Loop Engineering 工具区（2026-06-22 新增 · Addy Osmani 精读注入）

> **你不是提示 AI 的那个人了。你设计一个系统，让系统去提示 AI。**
> 三个落地组件：Triage Inbox / /goal 循环 / Comprehension Debt 管理

### 6.1 Triage Inbox 管道

自动任务发现的问题不只在聊天里说，同时写入 `triage_inbox/` 供统一查看。

```bash
cd /home/sandbox/.openclaw/workspace

# 写入一条待审项
python3 scripts/triage_engine.py write <source> <title> <body> [priority]
# 示例:
python3 scripts/triage_engine.py write "cron:zhuzhu" "恒瑞医药连续3日资金流出" "## 异常\n主力净流出2亿" "P1"

# 列出待审项（默认全部，可加优先级过滤）
python3 scripts/triage_engine.py list [P0|P1|P2|P3]

# 关闭一条
python3 scripts/triage_engine.py close <uid>

# 统计
python3 scripts/triage_engine.py stats
```

**优先级标准：**
| 级别 | 含义 | 响应时间 |
|:----|:------|:---------|
| P0 | 紧急 — 需立即关注 | 尽快处理 |
| P1 | 今天内 — 当前任务相关 | 当天 |
| P2 | 本周内 — 重要但不急 | 本周 |
| P3 | 待定 — 值得留意但可等 | 无时限 |

**分类：** `alert`(异常) / `suggestion`(建议) / `issue`(问题) / `review`(待审) / `anomaly`(系统异常)

**纪律：** AGENTS.md §15.2 ② 有发现必进 Triage，无发现不自找麻烦。

### 6.2 /goal 条件驱动循环

> 定义目标 → 系统自主执行 → 每轮由不同的模型判定停止条件（maker ≠ checker）

当前实现：认知迭代环 §13 + 真话放大镜作为独立检查者。
使用方式：在任务指令中附带可验证的完成条件。

```
# 示例：设置可验证目标
python3 bin/pipeline.py run "AEM电解水分析" \
  --goal "evidence_coverage > 70% && no T3 assertions && bridge_coverage >= 3 layers"
```

**停止条件设计指南：**
| 维度 | 可测量条件 | 示例 |
|:-----|:----------|:-----|
| 证据充分度 | `evidence_coverage > X%` | `evidence_coverage > 70%` |
| 信度质量 | `max(T3_count) == 0` | `无T3断言` |
| 桥覆盖 | `bridge_layers >= N` | `覆盖至少3层` |
| 收敛度 | `delta < 5%` | `前后差异 < 5%` |

**纪律：** maker ≠ checker — 真话放大镜负责验证停止条件是否达成。

### 6.3 Comprehension Debt 管理

> 循环跑得越快，理解差距越大。

每次自进化必须附带变更说明，格式：

```markdown
### 🧠 系统变更记录 YYYY-MM-DD
- **变更项：** 简要描述
- **原因：** 为什么做这个变更
- **影响范围：** 哪些模块/技能/行为受影响
- **验证方式：** 如何验证变更生效
```

**定期审计命令：**
```bash
# 查看 recent 变更历史
cd /home/sandbox/.openclaw/workspace
git log --oneline --since="3 days ago" -- AGENTS.md SOUL.md MEMORY.md TOOLS.md 2>/dev/null || echo "无git历史"

# 查看 Triage 待审项
python3 scripts/triage_engine.py list

# 查看最近的进化记录
tail -20 memory/$(date +%Y-%m-%d).md 2>/dev/null || echo "今日记忆文件不存在"
```

### 6.4 Loop Engineering 速查矩阵

| 你需要什么 | 用什么工具 | 命令 |
|:----------|:----------|:-----|
| 自动任务发现的问题汇总 | Triage Inbox | `python3 scripts/triage_engine.py list` |
| 分析任务设目标跑 | /goal 条件驱动 | `python3 bin/pipeline.py run "问题" --goal "条件"` |
| 进化后写变更说明 | 系统变更记录 | 进化时附带 `## 系统变更记录 YYYY-MM-DD` 区块 |
| 核查系统是否脱轨 | 定期审计 | `python3 scripts/self_check.py` |
| 认知迭代手动推进 | 迭代环 | 默认管线自带，真话放大镜为独立检查者 |

---

## 🌙 七、子午梦境区（2026-06-23 新增）

> **子梦(23:00)发散→午梦(11:00)收敛→经验入库→自动触发创新检查**

### 7.1 基础用法

```bash
cd /home/sandbox/.openclaw/workspace

# 自动检测时辰（22-01子梦，10-13午梦，其余默认发散）
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py

# 强制模式
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py --zi   # 子梦·发散
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py --wu   # 午梦·收敛

# 回顾
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py --recall  # 3天
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py --epic    # 30天
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py --season  # 90天

# 查经验
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py --query '超时'

# 预览（不写入）
python3 skills/bian-mengjing-bianzhishi/scripts/dreamweaver.py --dry-run
```

### 7.2 输出文件

| 文件 | 说明 |
|:----|:-----|
| `skills/bian-mengjing-bianzhishi/output/dream_子_YYYY-MM-DD.md` | 子梦发散报告 |
| `skills/bian-mengjing-bianzhishi/output/dream_午_YYYY-MM-DD.md` | 午梦收敛报告 |
| `skills/bian-mengjing-bianzhishi/output/performance_YYYY-MM-DD.html` | 性能脉搏卡 |

### 7.3 自动回路

- 子梦(23:00)报告生成后 → 自动扫描"待创新"关键词 → 如有信号自动传入创新子系统
- 午梦(11:00)产出T1经验 → 自动入库吞吞备案

---

## 📦 七·五、弹药箱信息中枢（2026-06-24 更新）

> 新增 task_stats.py 模块，迁移入弹药箱目录统一管理

### 使用方式

```bash
cd /home/sandbox/.openclaw/workspace

# 每日/聚合统计
python3 弹药箱/task_stats.py                    # 今日统计
python3 弹药箱/task_stats.py --days 7           # 7天聚合

# 失败排查
python3 弹药箱/task_stats.py --top-fail         # 失败TOP榜单
python3 弹药箱/task_stats.py --skill stock-tools # 单个Skill详情
python3 弹药箱/task_stats.py --init             # 初始化数据库
```

### 数据源
- MCP Bridge ammo_events/*.ndjson（mcp_bridge.py 每次工具调用自动写入）
- 弹药箱/events/*.ndjson（ammo_box.py 三进制WAL写入）
- 最终存储在 task_stats.db（SQLite）

### 弹药箱文件结构
```
弹药箱/
├── __init__.py        ← 模块入口
├── ammo_box.py        ← 三进制WAL
├── task_stats.py      ← 成功率追踪（新增）
├── task_stats.db      ← SQLite数据库（自动生成）
├── search_all.py      ← 跨弹药箱搜索
├── archive/           ← 归档
├── 书库/ 产出/ 兵器谱/ 吞吞缓存/  ← 存量数据
└── 我们俩的交易纪律.md
```

---

#### 🗂️ A2A 中继架构 · 已封存
> **状态：** 🔒 2026-06-26 全线冻结封存
> **存档位置：** `_archived_a2a/`
> **存档内容：** a2a-relay/（含 relay_server / org_agent / bridge_console / agent_primordial / 原始Claw进化体系等）+ agent-swarm-kit + agent_reach
> **远程 ECS 进程：** 已停（enhanced_relay / a2a_http_bridge / worker_agent）
> **恢复条件：** 需要时从 _archived_a2a/ 还原 + 重启 ECS 进程
> **纪律：** 封存期间不做任何 A2A 相关工作，不启动、不修改、不引用

### 弹药箱 Ring Buffer 异步写入（2026-06-26 新增 · 体素引擎精读注入）

Ring Buffer 模式让高频写入不阻塞主流程，后台线程每 5s 自动批量 flush 到 WAL。

```bash
cd /home/sandbox/.openclaw/workspace

# 高频写入场景（gap_detector 等），use_ring=True
python3 -c "from ammo_box import ammo_write; ammo_write('gap_signals', [...], use_ring=True)"

# 低频写入场景（手动操作），不加 use_ring 走原来 WAL 路径
python3 -c "from ammo_box import ammo_write; ammo_write('judgments', {...})"

# 手动触发 flush（通常不需要，后台自动每5s flush）
python3 -c "from ammo_box import _ring_buffer; _ring_buffer.flush()"

# 查看写入监控（含 RingBuffer 统计）
python3 -c "from ammo_box import get_write_metrics; get_write_metrics()"
```

**参考：** fogleman/Craft 的 db.c ring buffer + worker thread 模式

### 琅嬛 LRU 缓存（2026-06-26 新增 · 体素引擎精读注入）

热门知识查询缓存，LRU 淘汰，最大 50 条目 ≈750KB。

```bash
cd /home/sandbox/.openclaw/workspace

# 查看缓存状态
python3 -c "from langhuan.cache import show_cache_status; show_cache_status()"

# 清除全部缓存（知识库更新后调用）
python3 -c "from langhuan.cache import invalidate_cache; invalidate_cache()"

# 清除特定查询缓存
python3 -c "from langhuan.cache import invalidate_cache; invalidate_cache('大盘行情')"
```

**接入点：** `diting/enhanced_search.py` EnhancedSearchRouter.search() 新增 `use_cache=True` 参数
**参考：** Craft 的 Chunk 管理——只渲染视野内的区块，只缓存热门查询

## 🪞 七·六、真话放大镜管线集成（2026-06-24 更新）

> 真话放大镜 V2 — Verifiable Claims Engine（2026-06-26 已升级）
> 基于 TruthLensV2 的可验证声明体系，支持 Sha-256 防篡改指纹、12字段证据链、60+来源权威性评分、置信度矩阵

```bash
cd /home/sandbox/.openclaw/workspace

# 验证文本（默认L2）
python3 skills/真话放大镜/scripts/truth_magnifier_hook_v2.py --text "分析内容"

# 指定验证深度
python3 skills/真话放大镜/scripts/truth_magnifier_hook_v2.py --text "分析内容" --level L3 --json

# 验证报告文件（自动追加验证附录）
python3 skills/真话放大镜/scripts/truth_magnifier_hook_v2.py --report output.md

# JSON输出
python3 skills/真话放大镜/scripts/truth_magnifier_hook_v2.py --text "内容" --json
```

**Python API**:
```python
from scripts.truth_magnifier_hook_v2 import auto_verify_pipeline, verify

# 管线集成（返回验证附录）
appendix = auto_verify_pipeline(report_text, cube_dict)

# 快捷验证
result = verify("待验证文本")
```

**管线自动集成**: bin/pipeline.py 的 run_pipeline() 在渲染报告后自动调用，
优先使用 V2，降级到 V1。三级验证深度：
- L1 轻量：时间+逻辑自洽
- L2 标准：完整 6 维验证链
- L3 深度：含 C3 停等标记

**验证示例输出**:
```
---
> 🪞 **真话放大镜 V2 验证**: FAIL
> 📊 检测到 2 个事实声明
> 
> **发现的问题:**
> - 🔴 [V2] 低置信度声明: 根据数据统计，市场昨日上涨2%...
```

---

## 🚀 八、创新子系统区（2026-06-23 新增）

> **检测→评估→发散→实验→收敛→提案→验证→交付（C3停等）**

### 8.1 基础用法

```bash
cd /home/sandbox/.openclaw/workspace

# 检查触发条件
python3 skills/innovation-subsystem/scripts/innovation_pilot.py --check

# 指定触发类型
python3 skills/innovation-subsystem/scripts/innovation_pilot.py --trigger error
python3 skills/innovation-subsystem/scripts/innovation_pilot.py --trigger dream
python3 skills/innovation-subsystem/scripts/innovation_pilot.py --trigger manual --problem "优化股票评分效率"

# 沙盒管理
python3 skills/innovation-subsystem/scripts/sandbox.py list
python3 skills/innovation-subsystem/scripts/sandbox.py cleanup-old --days 7 --execute

# 单阶段管线
python3 skills/innovation-subsystem/scripts/pipeline.py --exp-id exp_xxx --problem "xxx" --stage diverge
python3 skills/innovation-subsystem/scripts/pipeline.py --exp-id exp_xxx --problem "xxx" --stage all

# 验证器
python3 skills/innovation-subsystem/scripts/validator.py --validate diverge --file diverge_result.json
```

### 8.2 治理纪律

| 约束 | 说明 |
|:----|:-----|
| **C3停等** | 提案必须经用户明确确认才能执行，不自决 |
| **沙盒隔离** | 实验在 `sandbox/experiments/` 内进行，不修改生产文件 |
| **质疑者验证** | 每阶段结束后调真话放大镜做独立验证 (maker ≠ checker) |
| **弹药箱回写** | 提案生成自动写入 `innovation_proposals`；执行后可写入 `innovation_applied` |

### 8.3 快速定位

```bash
# 提案目录（C3停等中）
ls ~/.openclaw/workspace/skills/innovation-subsystem/output/proposals/

# 实验沙盒
ls ~/.openclaw/workspace/skills/innovation-subsystem/sandbox/experiments/

# 弹药箱创新记录
jq '.innovation_proposals // .innovation_applied // empty' ~/.ammo_box/events/$(date +%Y-%m-%d).ndjson 2>/dev/null | head -20
```

### 8.4 自动调度

| 时间 | 任务 | 说明 |
|:----|:----|:-----|
| 21:00 (每日) | 创新系统日检 | 扫描错误重复+梦境信号→如有触发走4阶段管线 |
| 23:00 (每日) | 子梦发散 | 报告生成后自动触发 `--trigger dream` 检查 |

---

## 🗄️ 九、MCP外部服务器配置区（2026-06-29 新增）

> 快速接入外部 MCP 服务（云容器/数据库/第三方API代理等）到 OpenClaw 的标准化流程。

### 9.1 配置工具

```bash
# 注册MCP服务器（SSE传输）
openclaw mcp set <服务器名> '{"url":"<SSE端点地址>"}'

# 查看已注册列表
openclaw mcp list

# 查看某个服务器配置详情
openclaw mcp show <服务器名> --json

# 删除
openclaw mcp unset <服务器名>
```

**注意：** `set` 只写入配置到 openclaw.json，不验证可达性。配完后需要重启网关生效。

### 9.2 配置工作流（五步）

```
① 确认服务端 MCP 可用 → curl -s <SSE端点> 看是否能连
② 注册 → openclaw mcp set <名字> '{"url":"..."}'
③ 验证注册 → openclaw mcp list / show
④ 重启网关 → openclaw gateway restart （或等下次启动自动加载）
⑤ 测试查询 → 通过昆仑管线或子Agent调用该MCP工具
```

### 9.3 REST API 双通道（推荐）

MCP 主要管查询，如果服务端同时提供 REST API 写入口，建议双通道并用：

| 操作 | 通道 | 原因 |
|:----|:-----|:-----|
| 🔍 **查询/读取** | MCP → openclaw mcp | 标准化接口，适配所有MCP客户端 |
| ✍️ **写入/创建** | REST API 直调 | MCP write工具很多服务端没暴露，REST更稳定 |

### 9.4 已注册的MCP服务器

| 名称 | 类型 | 工具 | 用途 |
|:----|:-----|:-----|:-----|
| 知识卡云容器 | SSE | search/get_by_id/domains/by_domain/stats | 昆仑知识卡云搜索+管理 |

### 9.5 排障速查

| 现象 | 原因 | 处置 |
|:----|:-----|:-----|
| `openclaw mcp list` 有但用不了 | 配置后没重启网关 | `openclaw gateway restart` |
| SSE端点能连但tool调用超时 | 服务端/网络延迟 | 检查服务端负载，加timeout熔断 |
| REST写入了但MCP查不到 | 索引延迟 | 等几秒再查，或触发服务端重建索引 |
| 服务器不在境内连不上 | 跨境网络问题 | 用境内中转或确认白名单IP
