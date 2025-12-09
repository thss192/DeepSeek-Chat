<a id="chinese"></a>
# DeepSeek Chat 桌面应用
[English](#english) | [中文](#chinese)
一个功能强大的 DeepSeek AI 聊天桌面应用，集成了文件管理、多对话管理、代码编辑等实用功能。

## 🚀 功能特性

### 🤖 AI 聊天功能
- 支持 DeepSeek Chat/Coder/Reasoner 模型
- 流式响应输出，实时显示生成内容
- 支持消息队列，可连续对话
- 对话历史自动保存与加载
- 自定义系统提示词
- 可调节的温度、top_p 等参数

### 📁 文件管理功能
- **三面板布局**：文件浏览器 | 只读查看器 | 可编辑编辑器
- **智能文件监控**：实时检测文件变化
- **代码高亮**：支持多种编程语言的语法高亮
- **文件操作**：创建、重命名、删除文件和文件夹
- **拖拽调整**：可调整面板宽度
- **修改标记**：显示未保存的文件修改状态

### 💬 多对话管理
- 独立的对话标签页管理
- 每个对话可单独配置参数
- 独立的对话历史存储
- 一键切换不同对话
- 对话名称智能生成

### ⚙️ 设置管理
- API 配置管理
- 模型参数调节
- 网络连接测试
- API 余额查询
- 快捷键自定义（Enter/Ctrl+Enter）

### 📜 历史管理
- 对话历史记录查看
- 一键加载历史对话
- 对话预览功能
- 批量删除管理

## 🛠️ 安装使用

### 环境要求
- Python 3.8+
- Flet 框架
- DeepSeek API Key

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/thss192/DeepSeek-Chat
cd DeepSeek-Chat
```
2. 安装依赖
```bash
pip install flet requests watchdog
```
3. 配置 API Key
   - 运行应用：python main.py
   - 进入"设置"标签页
   - 输入您的 DeepSeek API Key
   - 保存配置

4. 启动应用
```bash
python main.py
```
## 📁 项目结构
```txt
deepseek-chat-app/
├── main.py                    # 主应用入口
├── deepseek_config.json      # 配置文件
├── src/
│   ├── client.py            # DeepSeek 客户端
│   ├── chat_view.py         # 聊天界面
│   ├── settings_manager.py  # 设置管理
│   ├── history_manager.py   # 历史管理
│   ├── file_manager.py      # 文件管理器主类
│   ├── file_explorer.py     # 文件浏览器组件
│   ├── file_editor.py       # 文件编辑器组件
│   └── concurrent_manager/
│       └── conversation_manager.py  # 多对话管理器
├── conversations/           # 对话历史存储目录
└── independent_conversations/ # 独立对话存储目录
```
## 🎯 快速开始指南

### 基本聊天
1. 在聊天标签页输入消息
2. 按 Enter 或 Ctrl+Enter 发送（可在设置中配置）
3. AI 助手会实时回复

### 文件管理
1. 切换到"文件管理"标签页
2. 左侧：浏览文件和目录
3. 中间：查看文件内容（只读）
4. 右侧：编辑文件内容
5. 使用顶部按钮切换面板显示

### 文件操作
1. 浏览文件：
   - 左侧文件浏览器显示当前目录结构
   - 点击文件夹图标可展开/收起子目录
   - 点击文件会同时在查看器和编辑器中打开

2. 文件查看：
   - 中间面板以 Markdown 代码块形式显示文件内容
   - 支持语法高亮和代码格式化
   - 实时同步编辑器中的修改

3. 文件编辑：
   - 右侧面板提供完整的文本编辑功能
   - 修改后文件会标记为"已修改"
   - 点击保存按钮（💾）保存文件

4. 文件操作：
   - 点击顶部设置图标（⚙️）进入文件管理模式
   - 新建文件/文件夹：点击对应目录下的"新建..."按钮
   - 重命名：点击文件/文件夹后的编辑图标
   - 删除：点击删除图标，需二次确认
   - 切换目录：点击文件夹后的文件夹图标

## 💭 多对话管理

### 创建和管理对话
1. 进入多对话界面：切换到"多对话"标签页
2. 新建对话：点击左侧"新建对话"按钮
3. 切换对话：点击左侧对话列表中的对话名称
4. 删除对话：点击对话卡片上的删除图标（非当前对话可见）

### 对话设置
每个对话可独立配置：
- 对话名称：自定义对话名称
- 模型选择：为当前对话选择模型
- 系统提示词：自定义 AI 角色设定
- 参数调节：温度、top_p、最大令牌数等

### 聊天界面
- 左侧：对话列表和当前对话标题
- 右侧：聊天界面和设置
- 三个子标签页：
  - 聊天：与 AI 对话
  - 对话设置：配置当前对话参数
  - API 配置：设置全局 API（所有对话共享）

## ⚙️ 设置配置

### API 设置
- API Key：必需，从 DeepSeek 官网获取
- API 基础 URL：默认 https://api.deepseek.com/v1

### 模型参数
- 模型选择：DeepSeek Chat/Coder/Reasoner
- 最大生成长度：限制单次回复长度
- 温度：0-2，值越高回复越随机
- Top P：0-1，核采样参数
- 频率/存在惩罚：-2到2，控制重复性

### 连接测试
1. 网络连接测试：测试互联网连通性
2. API 端点测试：测试 DeepSeek API 服务器可达性
3. 完整连接测试：包含 API Key 验证的完整测试
4. 余额查询：查询 API 账户剩余额度

### 输入设置
- 发送快捷键：可选择 Enter 或 Ctrl+Enter
- 应用设置：点击"应用快捷键设置"使设置生效

## 📜 历史管理

### 查看历史对话
1. 切换到"历史"标签页
2. 显示所有保存的对话记录
3. 每张卡片显示：
   - 对话名称和消息数量
   - 最后一条用户消息预览
   - 更新时间

### 操作历史对话
- 加载对话：点击"加载"按钮，切换到聊天标签页并加载历史
- 删除对话：点击"删除"按钮，删除单个对话记录
- 一键删除：点击"一键删除所有对话"批量清理

### 自动保存
- 新对话会在首次回复后自动保存
- 现有对话会在每次交互后自动更新
- 对话名称由 AI 自动生成（基于对话内容）

## 🎮 快捷键说明

### 全局快捷键
- Tab 切换：使用鼠标点击标签页切换
- 页面调整：拖拽窗口边缘调整大小

### 聊天快捷键
- 发送消息：Enter 或 Ctrl+Enter（根据设置）
- 换行：与发送快捷键相反的操作（如设置为 Ctrl+Enter，则 Enter 换行）

### 文件编辑快捷键
- 标准编辑：支持常见的复制（Ctrl+C）、粘贴（Ctrl+V）、撤销（Ctrl+Z）等
- 保存文件：点击保存按钮，暂无全局快捷键

## 💡 实用技巧

### 高效使用
1. 多任务处理：
   - 可在文件管理器中查看代码
   - 同时在聊天窗口询问 AI 相关代码问题
   - 将代码片段直接复制到聊天窗口

2. 代码调试：
   - 在编辑器中修改代码
   - 实时查看器显示修改效果
   - 向 AI 描述错误并寻求解决方案

3. 对话管理：
   - 为不同主题创建独立对话
   - 使用系统提示词定制 AI 角色
   - 定期清理不需要的对话记录

### 故障处理
- 连接问题：使用设置中的连接测试功能
- 文件不刷新：点击文件管理器刷新按钮或等待自动刷新
- 界面卡顿：减少同时打开的面板数量
- API 错误：检查 API Key 和网络连接

## 🔄 数据管理

### 数据位置
- 配置文件：deepseek_config.json（应用根目录）
- 对话历史：conversations/ 目录（JSON 格式）
- 独立对话：independent_conversations/ 目录
- 临时缓存：应用运行时内存缓存，重启后清除

### 备份与迁移
1. 备份对话：复制 conversations/ 目录内容
2. 迁移设置：复制 deepseek_config.json 文件
3. 恢复数据：将备份文件放回对应位置

提示：建议定期备份重要对话记录，特别是包含有价值内容的对话。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---



<a id="english"></a>
# DeepSeek Chat Desktop Application
 [中文](#chinese) | [English](#english)
A powerful DeepSeek AI chat desktop application that integrates file management, multi-conversation management, code editing and other practical features.

## 🚀 Features

### 🤖 AI Chat Features
- Supports DeepSeek Chat/Coder/Reasoner models
- Streaming response output, real-time display of generated content
- Supports message queues for continuous conversations
- Automatic conversation history saving and loading
- Custom system prompts
- Adjustable temperature, top_p and other parameters

### 📁 File Management Features
- **Three-panel layout**: File Browser | Read-only Viewer | Editable Editor
- **Smart file monitoring**: Real-time detection of file changes
- **Code highlighting**: Syntax highlighting for multiple programming languages
- **File operations**: Create, rename, delete files and folders
- **Drag adjustment**: Adjustable panel widths
- **Modification markers**: Display unsaved file changes

### 💬 Multi-Conversation Management
- Independent conversation tab management
- Each conversation can be configured separately
- Independent conversation history storage
- One-click switching between conversations
- Intelligent conversation name generation

### ⚙️ Settings Management
- API configuration management
- Model parameter adjustment
- Network connection testing
- API balance query
- Shortcut customization (Enter/Ctrl+Enter)

### 📜 History Management
- Conversation history viewing
- One-click loading of historical conversations
- Conversation preview function
- Batch deletion management

## 🛠️ Installation & Usage

### Requirements
- Python 3.8+
- Flet framework
- DeepSeek API Key

### Installation Steps

1. Clone the repository
```bash
git clone https://github.com/thss192/DeepSeek-Chat
cd DeepSeek-Chat
```
2. Install dependencies
```bash
pip install flet requests watchdog
```
3. Configure API Key
   - Run the application: python main.py
   - Go to the "Settings" tab
   - Enter your DeepSeek API Key
   - Save the configuration

4. Launch the application
```bash
python main.py
```
## 📁 Project Structure
```txt
deepseek-chat-app/
├── main.py                    # Main application entry
├── deepseek_config.json      # Configuration file
├── src/
│   ├── client.py            # DeepSeek client
│   ├── chat_view.py         # Chat interface
│   ├── settings_manager.py  # Settings management
│   ├── history_manager.py   # History management
│   ├── file_manager.py      # File manager main class
│   ├── file_explorer.py     # File explorer component
│   ├── file_editor.py       # File editor component
│   └── concurrent_manager/
│       └── conversation_manager.py  # Multi-conversation manager
├── conversations/           # Conversation history directory
└── independent_conversations/ # Independent conversations directory
```
## 🎯 Quick Start Guide

### Basic Chat
1. Enter your message in the chat tab
2. Press Enter or Ctrl+Enter to send (configurable in settings)
3. AI assistant will respond in real-time

### File Management
1. Switch to the "File Management" tab
2. Left panel: Browse files and directories
3. Middle panel: View file content (read-only)
4. Right panel: Edit file content
5. Use top buttons to toggle panel display

### File Operations
1. Browse Files:
   - Left file browser shows current directory structure
   - Click folder icons to expand/collapse subdirectories
   - Click files to open in both viewer and editor

2. File Viewing:
   - Middle panel displays file content in Markdown code blocks
   - Supports syntax highlighting and code formatting
   - Real-time synchronization with editor modifications

3. File Editing:
   - Right panel provides full text editing functionality
   - Modified files are marked as "Modified"
   - Click save button (💾) to save files

4. File Operations:
   - Click settings icon (⚙️) to enter file management mode
   - New File/Folder: Click "New..." button in corresponding directory
   - Rename: Click edit icon after file/folder
   - Delete: Click delete icon, requires confirmation
   - Change Directory: Click folder icon after folder

## 💭 Multi-Conversation Management

### Create and Manage Conversations
1. Enter Multi-Conversation Interface: Switch to "Multi-Conversation" tab
2. New Conversation: Click "New Conversation" button on left
3. Switch Conversation: Click conversation name in left list
4. Delete Conversation: Click delete icon on conversation card (visible for non-current conversations)

### Conversation Settings
Each conversation can be independently configured:
- Conversation Name: Custom conversation name
- Model Selection: Choose model for current conversation
- System Prompt: Custom AI role settings
- Parameter Adjustment: Temperature, top_p, max tokens, etc.

### Chat Interface
- Left: Conversation list and current conversation title
- Right: Chat interface and settings
- Three Sub-tabs:
  - Chat: Conversation with AI
  - Conversation Settings: Configure current conversation parameters
  - API Configuration: Set global API (shared by all conversations)

## ⚙️ Settings Configuration

### API Settings
- API Key: Required, obtain from DeepSeek official website
- API Base URL: Default https://api.deepseek.com/v1

### Model Parameters
- Model Selection: DeepSeek Chat/Coder/Reasoner
- Max Generation Length: Limit single response length
- Temperature: 0-2, higher values make responses more random
- Top P: 0-1, nucleus sampling parameter
- Frequency/Presence Penalty: -2 to 2, controls repetitiveness

### Connection Tests
1. Network Connection Test: Test internet connectivity
2. API Endpoint Test: Test DeepSeek API server reachability
3. Full Connection Test: Complete test including API Key verification
4. Balance Query: Query API account remaining balance

### Input Settings
- Send Shortcut: Choose Enter or Ctrl+Enter
- Apply Settings: Click "Apply Shortcut Settings" to make settings effective

## 📜 History Management

### View Historical Conversations
1. Switch to "History" tab
2. Display all saved conversation records
3. Each card shows:
   - Conversation name and message count
   - Last user message preview
   - Update time

### Manage Historical Conversations
- Load Conversation: Click "Load" button, switch to chat tab and load history
- Delete Conversation: Click "Delete" button, delete single conversation record
- Delete All: Click "Delete All Conversations" for batch cleanup

### Auto-save
- New conversations are automatically saved after first response
- Existing conversations are automatically updated after each interaction
- Conversation names are automatically generated by AI (based on conversation content)

## 🎮 Shortcut Guide

### Global Shortcuts
- Tab Switching: Click tab with mouse
- Window Adjustment: Drag window edges to resize

### Chat Shortcuts
- Send Message: Enter or Ctrl+Enter (depending on settings)
- New Line: Opposite operation of send shortcut (e.g., if set to Ctrl+Enter, then Enter creates new line)

### File Editing Shortcuts
- Standard Editing: Supports common copy (Ctrl+C), paste (Ctrl+V), undo (Ctrl+Z), etc.
- Save File: Click save button, no global shortcut currently

## 💡 Tips & Tricks

### Efficient Usage
1. Multi-tasking:
   - View code in file manager
   - Simultaneously ask AI about code issues in chat window
   - Copy code snippets directly to chat window

2. Code Debugging:
   - Modify code in editor
   - Real-time viewer shows modification effects
   - Describe errors to AI and seek solutions

3. Conversation Management:
   - Create separate conversations for different topics
   - Customize AI role using system prompts
   - Regularly clean up unnecessary conversation records

### Troubleshooting
- Connection Issues: Use connection test function in settings
- Files Not Refreshing: Click file manager refresh button or wait for auto-refresh
- Interface Lag: Reduce number of simultaneously open panels
- API Errors: Check API Key and network connection

## 🔄 Data Management

### Data Locations
- Configuration File: deepseek_config.json (application root directory)
- Conversation History: conversations/ directory (JSON format)
- Independent Conversations: independent_conversations/ directory
- Temporary Cache: Application runtime memory cache, cleared after restart

### Backup & Migration
1. Backup Conversations: Copy conversations/ directory contents
2. Migrate Settings: Copy deepseek_config.json file
3. Restore Data: Place backup files back to corresponding locations

Tip: It is recommended to regularly backup important conversation records, especially those containing valuable content.

## 🤝 Contributing

Welcome to submit Issues and Pull Requests!

## 📄 License

MIT License
