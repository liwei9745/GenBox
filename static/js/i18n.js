(function (global) {
  'use strict';

  var MESSAGES = {
    "common.reset":{"zh-CN":"重置","en":"Reset"},
    "common.close":{"zh-CN":"关闭","en":"Close"},
    "common.close_icon":{"zh-CN":"✕ 关闭","en":"✕ Close"},
    "common.copy":{"zh-CN":"复制","en":"Copy"},
    "common.copy_icon":{"zh-CN":"📋 复制","en":"📋 Copy"},
    "common.compare":{"zh-CN":"🔀 对比","en":"🔀 Compare"},
    "common.cancel":{"zh-CN":"取消","en":"Cancel"},
    "common.done":{"zh-CN":"完成","en":"Done"},
    "common.add":{"zh-CN":"+ 添加","en":"+ Add"},
    "common.reload":{"zh-CN":"🔄 重载","en":"🔄 Reload"},
    "common.refresh":{"zh-CN":"刷新","en":"Refresh"},
    "common.refresh_icon":{"zh-CN":"🔄 刷新","en":"🔄 Refresh"},
    "common.clear":{"zh-CN":"清空","en":"Clear"},
    "common.clear_icon":{"zh-CN":"🗑 清空","en":"🗑 Clear"},
    "common.delete":{"zh-CN":"删除","en":"Delete"},
    "common.save":{"zh-CN":"保存","en":"Save"},
    "common.skip":{"zh-CN":"跳过","en":"Skip"},
    "common.previous":{"zh-CN":"上一步","en":"Back"},
    "common.next":{"zh-CN":"下一步","en":"Next"},
    "common.loading":{"zh-CN":"加载中...","en":"Loading..."},
    "common.loading_ellipsis":{"zh-CN":"正在加载…","en":"Loading…"},
    "common.ready":{"zh-CN":"就绪","en":"Ready"},
    "common.waiting":{"zh-CN":"等待开始","en":"Waiting to start"},
    "common.not_configured":{"zh-CN":"未配置","en":"Not configured"},
    "common.not_entered":{"zh-CN":"未填写","en":"Not entered"},
    "common.not_deployed":{"zh-CN":"未部署","en":"Not deployed"},
    "common.all":{"zh-CN":"全部","en":"All"},
    "common.auto":{"zh-CN":"自动","en":"Auto"},
    "common.low":{"zh-CN":"低","en":"Low"},
    "common.medium":{"zh-CN":"中","en":"Medium"},
    "common.high":{"zh-CN":"高","en":"High"},
    "common.default":{"zh-CN":"默认","en":"Default"},
    "common.random":{"zh-CN":"随机","en":"Random"},
    "common.custom":{"zh-CN":"自定义...","en":"Custom..."},
    "common.show":{"zh-CN":"显示","en":"Show"},
    "common.install":{"zh-CN":"安装","en":"Install"},
    "common.open_console":{"zh-CN":"打开控制台","en":"Open console"},
    "common.load_failed":{"zh-CN":"加载失败","en":"Load failed"},
    "common.error":{"zh-CN":"⚠ 错误","en":"⚠ Errors"},
    "common.system":{"zh-CN":"💻 系统","en":"💻 System"},
    "common.delete_icon":{"zh-CN":"🗑 删除","en":"🗑 Delete"},
    "common.download_original":{"zh-CN":"⬇ 下载原图","en":"⬇ Download original"},
    "common.image_to_image":{"zh-CN":"🎯 图生图","en":"🎯 Image to image"},
    "common.create_video":{"zh-CN":"🎬 生视频","en":"🎬 Create video"},
    "common.insert":{"zh-CN":"📥 插入","en":"📥 Insert"},
    "common.search_prompt":{"zh-CN":"搜索提示词..","en":"Search prompts..."},
    "common.search_prompt_icon":{"zh-CN":"🔍 搜索提示词..","en":"🔍 Search prompts..."},
    "nav.dashboard":{"zh-CN":"系统看板","en":"Dashboard"},
    "nav.images":{"zh-CN":"生图","en":"Images"},
    "nav.video":{"zh-CN":"生视频","en":"Video"},
    "nav.library":{"zh-CN":"媒体库","en":"Media Library"},
    "nav.history":{"zh-CN":"历史","en":"History"},
    "nav.extensions":{"zh-CN":"扩展功能","en":"Extensions"},
    "nav.models":{"zh-CN":"模型设置","en":"Model settings"},
    "nav.prompt_settings":{"zh-CN":"提示词优化设置","en":"Prompt optimization"},
    "nav.appearance":{"zh-CN":"主题设置","en":"Appearance"},
    "nav.logs":{"zh-CN":"查看日志","en":"View logs"},
    "nav.refresh":{"zh-CN":"刷新页面","en":"Refresh page"},
    "nav.guide":{"zh-CN":"新手引导","en":"Getting Started"},
    "lightbox.image_prompt":{"zh-CN":"📝 生图提示词","en":"📝 Image prompt"},
    "lightbox.compare_title":{"zh-CN":"🔀 多模型结果对比","en":"🔀 Multi-model comparison"},
    "provider.title":{"zh-CN":"Provider 管理","en":"Provider management"},
    "provider.choose_type":{"zh-CN":"选择 Provider 类型","en":"Choose Provider type"},
    "provider.image":{"zh-CN":"🎨 生图模型","en":"🎨 Image models"},
    "provider.video":{"zh-CN":"🎬 生视频模型","en":"🎬 Video models"},
    "provider.llm":{"zh-CN":"🤖 LLM 提示词优化","en":"🤖 LLM prompt optimization"},
    "appearance.title":{"zh-CN":"🎨 主题设置","en":"🎨 Appearance"},
    "appearance.nav_title":{"zh-CN":"导航图标与 Logo","en":"Navigation icons and logo"},
    "appearance.nav_hint":{"zh-CN":"默认方案 C · 可单独切换","en":"Default: C · Change independently"},
    "appearance.font_title":{"zh-CN":"界面文字大小","en":"Interface text size"},
    "appearance.font_hint":{"zh-CN":"使用安全档位放大文字，控件会同步增高，避免文字挤出卡片。","en":"Choose a preset text size. Controls grow with it so labels stay inside their containers."},
    "appearance.workspace_title":{"zh-CN":"工作区布局","en":"Workspace layout"},
    "appearance.workspace_hint":{"zh-CN":"选择常用工作区，或在自定义模式中隐藏暂时不用的功能。系统看板和主题设置始终保留。","en":"Choose a workspace preset or hide unused features in Custom mode. Dashboard and Appearance always remain available."},
    "appearance.saved_hint":{"zh-CN":"主题保存在浏览器本地，刷新不丢失","en":"Appearance is saved in this browser"},
    "logs.title":{"zh-CN":"📋 系统日志","en":"📋 System logs"},
    "prompt.settings_title":{"zh-CN":"🤖 提示词优化设置","en":"🤖 Prompt optimization settings"},
    "prompt.settings_hint":{"zh-CN":"选择用于优化提示词的 LLM Provider","en":"Choose the LLM Provider used to optimize prompts"},
    "update.status":{"zh-CN":"更新状态","en":"Update status"},
    "update.ignore":{"zh-CN":"忽略此版本","en":"Ignore this version"},
    "update.later":{"zh-CN":"稍后","en":"Later"},
    "update.download":{"zh-CN":"前往下载","en":"Go to download"},
    "update.apply":{"zh-CN":"立即更新","en":"Update now"},
    "update.checking":{"zh-CN":"检查更新...","en":"Checking for updates..."},
    "update.open_status":{"zh-CN":"点击查看更新状态","en":"View update status"},
    "auth.required":{"zh-CN":"需要认证","en":"Authentication required"},
    "auth.enter_admin":{"zh-CN":"请输入管理员密钥以继续","en":"Enter the administrator key to continue"},
    "auth.admin_placeholder":{"zh-CN":"输入 Admin Key...","en":"Enter Admin Key..."},
    "auth.login":{"zh-CN":"登录","en":"Sign in"},
    "auth.invalid":{"zh-CN":"密钥无效，请重试","en":"Invalid key. Try again."},
    "welcome.title":{"zh-CN":"欢迎使用 GenBox!","en":"Welcome to GenBox!"},
    "welcome.key_hint":{"zh-CN":"你的管理员密钥已生成，请妥善保存","en":"Your administrator key has been generated. Store it safely."},
    "welcome.copy_key":{"zh-CN":"点击复制密钥","en":"Click to copy the key"},
    "welcome.continue":{"zh-CN":"我已保存，继续设置","en":"I saved it, continue setup"},
    "setup.title":{"zh-CN":"🚀 快速配置","en":"🚀 Quick setup"},
    "setup.hint":{"zh-CN":"填写 API Key 即可开始使用，其余配置可在设置中修改","en":"Enter an API Key to begin. Other settings can be changed later."},
    "setup.openai_default":{"zh-CN":"URL (默认 OpenAI)","en":"URL (OpenAI by default)"},
    "setup.llm_optional":{"zh-CN":"🤖 提示词优化 (可选)","en":"🤖 Prompt optimization (optional)"},
    "setup.save":{"zh-CN":"保存配置","en":"Save settings"},
    "dashboard.subtitle":{"zh-CN":"系统状态一览","en":"System status at a glance"},
    "language.switch_title":{"zh-CN":"切换界面语言","en":"Switch interface language"},
    "language.select_label":{"zh-CN":"界面语言","en":"Interface language"},
    "language.chinese":{"zh-CN":"中文","en":"Chinese"},
    "community.open":{"zh-CN":"打开 QQ 并申请加入交流群","en":"Open QQ and request to join the community"},
    "community.label":{"zh-CN":"GenBox | ChatGPT2API QQ交流群","en":"GenBox | ChatGPT2API QQ community"},
    "github.title":{"zh-CN":"GitHub 项目地址","en":"GitHub project"},
    "dashboard.restart":{"zh-CN":"重启","en":"Restart"},
    "dashboard.stop":{"zh-CN":"停止","en":"Stop"},
    "creator.image_multi_title":{"zh-CN":"多模型生图对比","en":"Multi-model image comparison"},
    "creator.image_multi_hint":{"zh-CN":"同一提示词同时调用多个模型，快速比较结果。","en":"Run the same prompt across multiple models and compare the results."},
    "creator.current_model":{"zh-CN":"当前模型","en":"Current model"},
    "creator.multi_mode":{"zh-CN":"多模型对比","en":"Multi-model"},
    "creator.single_mode":{"zh-CN":"单模型工作台","en":"Single model"},
    "creator.selected":{"zh-CN":"已选","en":"Selected"},
    "creator.unit_count":{"zh-CN":"个","en":"items"},
    "creator.image_settings":{"zh-CN":"📐 图像设置","en":"📐 Image settings"},
    "creator.model":{"zh-CN":"模型","en":"Model"},
    "creator.global_settings":{"zh-CN":"全局设置","en":"Global settings"},
    "creator.quality":{"zh-CN":"质量","en":"Quality"},
    "creator.size":{"zh-CN":"尺寸","en":"Size"},
    "creator.aspect_ratio":{"zh-CN":"宽高比","en":"Aspect ratio"},
    "creator.quantity":{"zh-CN":"生成数量","en":"Quantity"},
    "creator.save_settings":{"zh-CN":"💾 保存设置","en":"💾 Save settings"},
    "creator.strength":{"zh-CN":"变换强度","en":"Variation strength"},
    "creator.live_preview":{"zh-CN":"🎯 实时预览","en":"🎯 Live preview"},
    "creator.clear_preview_title":{"zh-CN":"清空所有预览","en":"Clear all previews"},
    "creator.empty_preview_1":{"zh-CN":"🖼 选择模型 + 输入提示词","en":"🖼 Choose a model and enter a prompt"},
    "creator.empty_preview_2":{"zh-CN":"生成后图片将在此处实时展示","en":"Generated images appear here in real time"},
    "creator.live_log":{"zh-CN":"📋 实时日志","en":"📋 Live log"},
    "creator.generating":{"zh-CN":"正在生成...","en":"Generating..."},
    "creator.t2i":{"zh-CN":"📝 文生图","en":"📝 Text to image"},
    "creator.i2i":{"zh-CN":"🖼 图生图","en":"🖼 Image to image"},
    "creator.variation":{"zh-CN":"🔄 变形","en":"🔄 Variation"},
    "creator.generate_image":{"zh-CN":"🚀 生成图片","en":"🚀 Generate image"},
    "creator.newbie_mode":{"zh-CN":"📝 新手模式","en":"📝 Beginner mode"},
    "creator.pro_mode":{"zh-CN":"🎯 专业模式","en":"🎯 Pro mode"},
    "creator.prompt_label":{"zh-CN":"提示词 Prompt","en":"Prompt"},
    "creator.prompt_placeholder":{"zh-CN":"描述你想要生成的图片...","en":"Describe the image you want to create..."},
    "creator.system_prompt":{"zh-CN":"系统提示词 System Prompt","en":"System Prompt"},
    "creator.system_prompt_placeholder":{"zh-CN":"定义整体风格、画质...","en":"Define the overall style and quality..."},
    "creator.user_prompt":{"zh-CN":"用户提示词 User Prompt","en":"User Prompt"},
    "creator.user_prompt_placeholder":{"zh-CN":"描述具体画面内容...","en":"Describe the scene content..."},
    "creator.optimized_prompt":{"zh-CN":"✨ 优化后提示词","en":"✨ Optimized prompt"},
    "creator.prompt_optimization":{"zh-CN":"提示词优化","en":"Prompt optimization"},
    "creator.optimize":{"zh-CN":"⚡ 点击优化","en":"⚡ Optimize"},
    "creator.undo":{"zh-CN":"↩ 撤销回退","en":"↩ Undo"},
    "creator.independent":{"zh-CN":"每次独立生成","en":"Independent generations"},
    "creator.record_hint":{"zh-CN":"默认关闭时，每次只处理当前提示词。开启后只会把最近 3 条提示词和 12 张图片归入同一创作记录，不会自动反复生图，也不会把旧内容再次发送给模型。","en":"When off, each run uses only the current prompt. When on, the latest 3 prompts and 12 images are grouped in one creation record. It does not repeat generation or resend older content to a model."},
    "creator.local_upscale":{"zh-CN":"⤢ 本地放大","en":"⤢ Local upscale"},
    "creator.upscale_hint":{"zh-CN":"生成后自动放大图片到更高分辨率，可选尺寸和算法","en":"Upscale generated images locally with a chosen size and algorithm"},
    "creator.max_1024":{"zh-CN":"最大边 1024","en":"Longest edge 1024"},
    "creator.max_1536":{"zh-CN":"最大边 1536","en":"Longest edge 1536"},
    "creator.max_2048":{"zh-CN":"最大边 2048","en":"Longest edge 2048"},
    "creator.max_3072":{"zh-CN":"最大边 3072","en":"Longest edge 3072"},
    "creator.max_4096":{"zh-CN":"最大边 4096","en":"Longest edge 4096"},
    "creator.square":{"zh-CN":"1:1 正方形","en":"1:1 Square"},
    "creator.landscape_169":{"zh-CN":"16:9 横屏","en":"16:9 Landscape"},
    "creator.ultrawide":{"zh-CN":"21:9 超宽","en":"21:9 Ultrawide"},
    "creator.landscape_43":{"zh-CN":"4:3 横屏","en":"4:3 Landscape"},
    "creator.landscape_32":{"zh-CN":"3:2 横屏","en":"3:2 Landscape"},
    "creator.portrait_916":{"zh-CN":"9:16 竖屏","en":"9:16 Portrait"},
    "creator.portrait_34":{"zh-CN":"3:4 竖屏","en":"3:4 Portrait"},
    "creator.original_ratio":{"zh-CN":"保持原图比例","en":"Keep original ratio"},
    "creator.optimization_compare":{"zh-CN":"📝 优化对比","en":"📝 Optimization comparison"},
    "creator.optimized_below":{"zh-CN":"⬇ 优化后 ⬇","en":"⬇ Optimized ⬇"},
    "creator.insert_optimized":{"zh-CN":"📥 插入优化结果","en":"📥 Insert optimized result"},
    "creator.reference_image":{"zh-CN":"参考图片","en":"Reference image"},
    "creator.upload_reference":{"zh-CN":"点击或拖拽上传","en":"Click or drag to upload"},
    "creator.edit_prompt_optional":{"zh-CN":"修改提示词 (可选)","en":"Edit prompt (optional)"},
    "creator.edit_prompt_placeholder":{"zh-CN":"描述你希望如何修改这张图片...","en":"Describe how you want to change this image..."},
    "creator.source_image":{"zh-CN":"源图片","en":"Source image"},
    "creator.upload_source":{"zh-CN":"点击或拖拽上传源图片","en":"Click or drag to upload a source image"},
    "creator.output_size":{"zh-CN":"输出尺寸","en":"Output size"},
    "creator.count":{"zh-CN":"数量","en":"Count"},
    "creator.quick_prompts":{"zh-CN":"💡 快捷提示词","en":"💡 Quick prompts"},
    "library.subtitle":{"zh-CN":"本地保存的图片与视频","en":"Images and videos saved locally"},
    "library.images":{"zh-CN":"🖼 图片","en":"🖼 Images"},
    "library.videos":{"zh-CN":"🎬 视频","en":"🎬 Videos"},
    "library.time_desc":{"zh-CN":"时间 ↓","en":"Time ↓"},
    "library.time_asc":{"zh-CN":"时间 ↑","en":"Time ↑"},
    "library.prompt_az":{"zh-CN":"提示词 A-Z","en":"Prompt A-Z"},
    "library.all_providers":{"zh-CN":"所有 Provider","en":"All Providers"},
    "library.flat":{"zh-CN":"平铺展示","en":"Flat view"},
    "library.grouped":{"zh-CN":"按模型分组","en":"Group by model"},
    "library.select_mode":{"zh-CN":"☑ 选择模式","en":"☑ Select"},
    "library.select_all":{"zh-CN":"全选","en":"Select all"},
    "library.select_none":{"zh-CN":"取消全选","en":"Clear selection"},
    "library.rename":{"zh-CN":"✏️ 重命名","en":"✏️ Rename"},
    "library.send_i2i":{"zh-CN":"➡️ 推送图生图","en":"➡️ Send to image-to-image"},
    "library.download_selected":{"zh-CN":"📥 下载 (","en":"📥 Download ("},
    "library.delete_selected":{"zh-CN":"🗑 删除 (","en":"🗑 Delete ("},
    "library.remote_sync":{"zh-CN":"☁ 从远程同步","en":"☁ Sync from remote"},
    "history.title":{"zh-CN":"历史记录","en":"History"},
    "history.subtitle":{"zh-CN":"记录每次生图","en":"Every image generation run"},
    "history.all_modes":{"zh-CN":"所有模式","en":"All modes"},
    "history.t2i":{"zh-CN":"文生图","en":"Text to image"},
    "history.i2i":{"zh-CN":"图生图","en":"Image to image"},
    "video.multi_title":{"zh-CN":"多模型视频对比","en":"Multi-model video comparison"},
    "video.multi_hint":{"zh-CN":"同时提交多个视频模型，集中比较生成结果。","en":"Submit to multiple video models and compare the results together."},
    "video.settings":{"zh-CN":"🎬 视频参数","en":"🎬 Video settings"},
    "video.size":{"zh-CN":"视频尺寸","en":"Video size"},
    "video.size_32_landscape":{"zh-CN":"1152×768 (横版 3:2)","en":"1152×768 (Landscape 3:2)"},
    "video.size_23_portrait":{"zh-CN":"768×1152 (竖版 2:3)","en":"768×1152 (Portrait 2:3)"},
    "video.size_hd_portrait":{"zh-CN":"720×1280 (HD 竖版)","en":"720×1280 (HD portrait)"},
    "video.duration_preset":{"zh-CN":"时长预设","en":"Duration preset"},
    "video.seconds_5":{"zh-CN":"5秒","en":"5 seconds"},
    "video.seconds_10":{"zh-CN":"10秒","en":"10 seconds"},
    "video.seconds_15":{"zh-CN":"15秒","en":"15 seconds"},
    "video.frames":{"zh-CN":"帧数","en":"Frames"},
    "video.advanced":{"zh-CN":"高级选项","en":"Advanced options"},
    "video.steps":{"zh-CN":"推理步数","en":"Inference steps"},
    "video.negative_prompt":{"zh-CN":"负面提示词","en":"Negative prompt"},
    "video.negative_placeholder":{"zh-CN":"不希望出现的内容...","en":"Content to avoid..."},
    "video.t2v":{"zh-CN":"文生视频","en":"Text to video"},
    "video.i2v":{"zh-CN":"图生视频","en":"Image to video"},
    "video.keyframes":{"zh-CN":"关键帧","en":"Keyframes"},
    "video.preview":{"zh-CN":"🎥 视频预览","en":"🎥 Video preview"},
    "video.empty_1":{"zh-CN":"🎬 选择模型 + 输入提示词","en":"🎬 Choose a model and enter a prompt"},
    "video.empty_2":{"zh-CN":"生成后视频将在此处分组展示","en":"Generated videos appear here grouped by model"},
    "video.session":{"zh-CN":"📋 本次会话","en":"📋 This session"},
    "video.none":{"zh-CN":"暂无视频","en":"No videos yet"},
    "video.prompt":{"zh-CN":"📝 视频提示词","en":"📝 Video prompt"},
    "video.prompt_placeholder":{"zh-CN":"描述你想生成的视频内容...","en":"Describe the video you want to create..."},
    "video.reference":{"zh-CN":"📷 参考图片","en":"📷 Reference image"},
    "video.first_frame":{"zh-CN":"⬅️ 首帧","en":"⬅️ First frame"},
    "video.reference_short":{"zh-CN":"🖼 参考","en":"🖼 Reference"},
    "video.first_last":{"zh-CN":"🔗 首尾帧","en":"🔗 First and last frames"},
    "video.last_frame":{"zh-CN":"➡️ 尾帧","en":"➡️ Last frame"},
    "video.upload":{"zh-CN":"拖拽图片或点击上传","en":"Drag an image or click to upload"},
    "video.pick_gallery":{"zh-CN":"🎯 从图库取图","en":"🎯 Choose from library"},
    "video.keyframe_images":{"zh-CN":"🖼 关键帧图片","en":"🖼 Keyframe images"},
    "video.keyframe_upload":{"zh-CN":"拖拽多张关键帧图片或点击上传","en":"Drag keyframe images or click to upload"},
    "video.choose_provider":{"zh-CN":"🚀 选择 Provider 后生成","en":"🚀 Choose a provider to generate"},
    "video.generate":{"zh-CN":"🚀 生成视频","en":"🚀 Generate video"},
    "video.submit_multi_prefix":{"zh-CN":"🚀 同时向 ","en":"🚀 Submit to "},
    "video.submit_multi_suffix":{"zh-CN":" 个 Provider 提交","en":" providers"},
    "video.elapsed_zero":{"zh-CN":"已用时 0s","en":"Elapsed 0s"},
    "logs.images":{"zh-CN":"🎨 生图","en":"🎨 Images"},
    "common.width":{"zh-CN":"宽","en":"Width"},
    "extensions.title":{"zh-CN":"扩展功能服务管理控制台","en":"Extension Service Management Console"},
    "extensions.subtitle":{"zh-CN":"统一部署 AI 服务、连接远程 VPS，并管理安全私网链路","en":"Deploy AI services, connect remote VPS hosts, and manage secure private-network links"},
    "extensions.drawer_hint":{"zh-CN":"服务面板已收纳至右侧，可随时查看运行状态、访问地址与密钥管理","en":"The service panel is available on the right for status, access URLs, and credential management"},
    "extensions.open_services_label":{"zh-CN":"查看已部署服务","en":"View deployed services"},
    "extensions.service_center":{"zh-CN":"服务控制中心","en":"Service control center"},
    "extensions.steps_label":{"zh-CN":"部署步骤","en":"Deployment steps"},
    "extensions.step_vps":{"zh-CN":"VPS 信息","en":"VPS details"},
    "extensions.step_deploy":{"zh-CN":"部署服务","en":"Deploy service"},
    "extensions.step_choose_network":{"zh-CN":"选择链路","en":"Choose network"},
    "extensions.step_configure":{"zh-CN":"配置连接","en":"Configure connection"},
    "extensions.step_verify":{"zh-CN":"验证完成","en":"Verify and finish"},
    "extensions.connect_vps":{"zh-CN":"连接 VPS","en":"Connect to VPS"},
    "extensions.saved_vps":{"zh-CN":"已保存 VPS","en":"Saved VPS hosts"},
    "extensions.current_unsaved":{"zh-CN":"当前未保存","en":"Current target is not saved"},
    "extensions.new_vps":{"zh-CN":"新增 VPS","en":"New VPS"},
    "extensions.name":{"zh-CN":"名称","en":"Name"},
    "extensions.target_role":{"zh-CN":"这台服务器的用途","en":"Server purpose"},
    "extensions.target_role_isolated":{"zh-CN":"隔离开发机（推荐）","en":"Isolated development (recommended)"},
    "extensions.target_role_production":{"zh-CN":"生产机，只读检查","en":"Production, read-only checks"},
    "extensions.target_role_help":{"zh-CN":"请按服务器实际用途选择。生产机只允许读取检查，不会用于部署。","en":"Choose the real purpose. Production targets allow read-only checks and cannot be deployed to."},
    "extensions.host":{"zh-CN":"IP 地址或域名","en":"IP address or hostname"},
    "extensions.ssh_port":{"zh-CN":"SSH 端口","en":"SSH port"},
    "extensions.ssh_username":{"zh-CN":"SSH 用户名","en":"SSH username"},
    "extensions.auth_method":{"zh-CN":"鉴权方式","en":"Authentication method"},
    "extensions.password":{"zh-CN":"密码","en":"Password"},
    "extensions.private_key":{"zh-CN":"SSH 私钥","en":"SSH private key"},
    "extensions.ssh_password":{"zh-CN":"SSH 密码","en":"SSH password"},
    "extensions.sudo_password":{"zh-CN":"sudo 密码（默认不复用 SSH 密码）","en":"sudo password (SSH password reuse is off by default)"},
    "extensions.sudo_placeholder":{"zh-CN":"仅密码 sudo 时使用","en":"Use only with password sudo"},
    "extensions.elevation_mode":{"zh-CN":"提权方式","en":"Elevation mode"},
    "extensions.elevation_none":{"zh-CN":"不使用 sudo","en":"No sudo"},
    "extensions.elevation_passwordless":{"zh-CN":"免密 sudo","en":"Passwordless sudo"},
    "extensions.elevation_password":{"zh-CN":"密码 sudo","en":"Password sudo"},
    "extensions.reuse_ssh_password":{"zh-CN":"本次请求显式使用 SSH 密码作为 sudo 密码","en":"Explicitly reuse the SSH password for sudo in this request"},
    "extensions.test_connection":{"zh-CN":"测试连接","en":"Test connection"},
    "extensions.deploy_chatgpt2api":{"zh-CN":"部署 chatgpt2api","en":"Deploy chatgpt2api"},
    "extensions.choose_deploy_targets":{"zh-CN":"选择本次部署的 VPS","en":"Choose VPS deployment targets"},
    "extensions.batch_hint":{"zh-CN":"可规划多台服务器；真正部署时仍会逐台确认 SSH 凭据和安全计划。","en":"You can plan for multiple servers. SSH credentials and the safety plan are still confirmed for each deployment."},
    "extensions.save_selection":{"zh-CN":"保存选择","en":"Save selection"},
    "extensions.no_server_selected":{"zh-CN":"尚未选择服务器","en":"No servers selected"},
    "extensions.catalog":{"zh-CN":"应用目录","en":"Service catalog"},
    "extensions.catalog_hint":{"zh-CN":"当前仅 chatgpt2api 可部署，其余模板为规划占位","en":"Only chatgpt2api is deployable. Other templates are planning placeholders."},
    "extensions.discover_first":{"zh-CN":"先检测，再决定","en":"Discover before deciding"},
    "extensions.readonly_hint":{"zh-CN":"仅执行只读命令，不修改已有服务","en":"Runs read-only commands and does not modify existing services"},
    "extensions.discover":{"zh-CN":"检测 VPS 环境","en":"Discover VPS environment"},
    "extensions.discovered_instances":{"zh-CN":"发现的实例","en":"Discovered instances"},
    "extensions.intent_title":{"zh-CN":"你这次要做什么","en":"What do you want to do?"},
    "extensions.intent_existing":{"zh-CN":"继续使用当前服务","en":"Keep using an existing service"},
    "extensions.intent_existing_hint":{"zh-CN":"推荐接入已有实例，不改变现有部署","en":"Connect an existing instance without changing its deployment"},
    "extensions.intent_development":{"zh-CN":"开发或测试新功能 · 当前场景","en":"Develop or test new features · Current scenario"},
    "extensions.intent_development_hint":{"zh-CN":"推荐从现有实例创建安全隔离副本","en":"Create a safely isolated copy of an existing instance"},
    "extensions.intent_production":{"zh-CN":"首次部署正式服务","en":"Deploy a new production service"},
    "extensions.intent_production_hint":{"zh-CN":"推荐新建生产实例","en":"Create a new production instance"},
    "extensions.strategy":{"zh-CN":"实例策略","en":"Instance strategy"},
    "extensions.strategy_existing":{"zh-CN":"确认并在 GenBox 本地登记","en":"Confirm and register locally in GenBox"},
    "extensions.strategy_existing_hint":{"zh-CN":"远程实例保持不变；GenBox 会在本地登记容器、状态、数据目录和所有权","en":"The remote instance stays unchanged; GenBox records its container, status, data directory, and ownership locally."},
    "extensions.strategy_isolated":{"zh-CN":"创建隔离测试实例","en":"Create an isolated test instance"},
    "extensions.strategy_isolated_hint":{"zh-CN":"独立端口、目录和 Compose 项目，推荐开发验收","en":"Uses a separate port, directory, and Compose project. Recommended for development acceptance."},
    "extensions.strategy_new":{"zh-CN":"新建生产实例","en":"Create a production instance"},
    "extensions.strategy_new_hint":{"zh-CN":"没有可用实例时使用，部署前仍会预览全部变更","en":"Use when no suitable instance exists. All changes are previewed before deployment."},
    "extensions.clone_data":{"zh-CN":"隔离实例初始数据","en":"Initial data for isolated instance"},
    "extensions.clone_empty":{"zh-CN":"空白实例","en":"Empty instance"},
    "extensions.clone_empty_hint":{"zh-CN":"不复制任何业务数据，风险最低","en":"Copies no business data and has the lowest risk"},
    "extensions.clone_media":{"zh-CN":"仅复制历史媒体","en":"Copy historical media only"},
    "extensions.clone_media_hint":{"zh-CN":"复制图片和索引，不复制账号及项目设置","en":"Copies images and indexes, but not accounts or project settings"},
    "extensions.clone_working":{"zh-CN":"安全工作副本 · 当前推荐","en":"Safe working copy · Recommended"},
    "extensions.clone_working_hint":{"zh-CN":"复制数据和设置；保留账号凭据，但移除 GenBox 密钥、回执与调度状态，并关闭自动备份","en":"Copies data and settings, preserves account credentials, removes GenBox keys, receipts, and schedule state, and disables automatic backup"},
    "extensions.source_instance":{"zh-CN":"源实例","en":"Source instance"},
    "extensions.choose_after_discovery":{"zh-CN":"检测环境后选择","en":"Choose after discovery"},
    "extensions.working_copy_warning":{"zh-CN":"工作副本含账号等敏感业务配置，仅用于独立开发验收。源实例保持运行且不会被写入。","en":"A working copy contains sensitive account and business settings. Use it only for isolated development acceptance. The source stays online and is not written to."},
    "extensions.deploy_method":{"zh-CN":"部署方式","en":"Deployment method"},
    "extensions.method_after_discovery":{"zh-CN":"检测环境后显示推荐方式","en":"The recommended method appears after discovery"},
    "extensions.instance_name":{"zh-CN":"实例名称","en":"Instance name"},
    "extensions.service_port":{"zh-CN":"服务端口","en":"Service port"},
    "extensions.container_image":{"zh-CN":"容器镜像","en":"Container image"},
    "extensions.create_plan":{"zh-CN":"生成安全计划","en":"Generate safety plan"},
    "extensions.confirm_deploy":{"zh-CN":"确认并部署","en":"Confirm and deploy"},
    "extensions.continue_network":{"zh-CN":"继续配置链路","en":"Continue to network setup"},
    "extensions.choose_primary_network":{"zh-CN":"选择主连接方式","en":"Choose the primary connection"},
    "extensions.this_computer":{"zh-CN":"这台电脑","en":"This computer"},
    "extensions.local_endpoint":{"zh-CN":"GenBox 本机端","en":"Local GenBox"},
    "extensions.waiting_detection":{"zh-CN":"等待检测","en":"Waiting for detection"},
    "extensions.local_network_hint":{"zh-CN":"检查网络工具，并开放 GenBox 私网入口。","en":"Check the network tool and expose the private GenBox entry point."},
    "extensions.genbox_page":{"zh-CN":"GenBox 页面","en":"GenBox page"},
    "extensions.private_entry":{"zh-CN":"私网入口","en":"Private entry"},
    "extensions.detect_again":{"zh-CN":"重新检测","en":"Detect again"},
    "extensions.enable_private_entry":{"zh-CN":"启用私网入口","en":"Enable private entry"},
    "extensions.remote_server":{"zh-CN":"远程服务器","en":"Remote server"},
    "extensions.vps_endpoint":{"zh-CN":"VPS 端","en":"VPS endpoint"},
    "extensions.waiting_configuration":{"zh-CN":"等待配置","en":"Waiting for configuration"},
    "extensions.remote_auto_hint":{"zh-CN":"GenBox 会先检查 VPS，再按真实状态安装、启动或加入网络，不会重复处理已经完成的步骤。","en":"GenBox checks the VPS first, then installs, starts, or enrolls only what is actually missing."},
    "extensions.operation_mode":{"zh-CN":"处理方式","en":"Operation mode"},
    "extensions.auto_connect":{"zh-CN":"自动检查、安装并加入","en":"Check, install, and join automatically"},
    "extensions.existing_connect":{"zh-CN":"已有工具，只连接和检测","en":"Tool already installed; connect and verify only"},
    "extensions.manual_later":{"zh-CN":"我手动配置，稍后检测（后续开放）","en":"I will configure it manually and verify later (coming later)"},
    "extensions.primary_network":{"zh-CN":"当前主链路","en":"Current primary network"},
    "extensions.backup_network":{"zh-CN":"备用链路","en":"Backup network"},
    "extensions.switch_later":{"zh-CN":"以后可添加并一键切换","en":"Add and switch with one click later"},
    "extensions.no_auth_key":{"zh-CN":"还没有一次性 Auth Key？","en":"Need a one-time Auth Key?"},
    "extensions.auth_key_intro":{"zh-CN":"打开官方密钥页面，创建后回到下一步粘贴即可。","en":"Open the official key page, create a key, then return and paste it in the next step."},
    "extensions.open_tailscale_keys":{"zh-CN":"打开 Tailscale 密钥页面","en":"Open Tailscale Keys"},
    "extensions.key_step_1":{"zh-CN":"找到 Auth keys，点击 Generate auth key","en":"Find Auth keys and click Generate auth key"},
    "extensions.key_step_2":{"zh-CN":"Reusable 关闭，Ephemeral 关闭，Pre-approved 开启","en":"Turn Reusable off, Ephemeral off, and Pre-approved on"},
    "extensions.key_step_3":{"zh-CN":"有效期选 1 天，Tags 留空，然后生成","en":"Choose a 1-day expiry, leave Tags empty, then generate the key"},
    "extensions.tailscale_hint":{"zh-CN":"推荐，个人免费，安装和维护最简单","en":"Recommended. Free for personal use and easiest to install and maintain."},
    "extensions.netbird_hint":{"zh-CN":"开源，可使用云服务或自托管控制面","en":"Open source with a cloud or self-hosted control plane"},
    "extensions.cloudflare_hint":{"zh-CN":"适合已有 Cloudflare 域名的用户","en":"For users who already have a Cloudflare domain"},
    "extensions.configure_option":{"zh-CN":"配置此方案","en":"Configure this option"},
    "extensions.admin_console_hint":{"zh-CN":"需要查看设备是否在线？可直接打开官方管理控制台。","en":"Need to check whether devices are online? Open the official admin console."},
    "extensions.open_tailscale_admin":{"zh-CN":"打开 Tailscale 管理控制台","en":"Open Tailscale admin console"},
    "extensions.choose_operation_first":{"zh-CN":"请先选择这次要执行的操作。","en":"Choose the operation to run first."},
    "extensions.operation_question":{"zh-CN":"这次要做什么？","en":"What should happen this time?"},
    "extensions.first_connect":{"zh-CN":"自动准备 VPS","en":"Prepare the VPS automatically"},
    "extensions.first_connect_hint":{"zh-CN":"系统先检测；缺什么才处理什么，不会重复安装。","en":"The system checks first and handles only what is missing, without reinstalling."},
    "extensions.recheck_existing":{"zh-CN":"已安装，重新检测连接","en":"Already installed; recheck the connection"},
    "extensions.recheck_existing_hint":{"zh-CN":"不重复安装，不需要 Auth Key，只检查互通和 GenBox 访问。","en":"Does not reinstall and needs no Auth Key. It only checks peer connectivity and GenBox access."},
    "extensions.key_page_link":{"zh-CN":"没有 Key？点击打开官方生成页面","en":"No Key? Open the official generation page"},
    "extensions.paste_prefix":{"zh-CN":"生成后，把以","en":"After generation, paste the value beginning with"},
    "extensions.paste_suffix":{"zh-CN":"开头的内容粘贴到下面。","en":"below."},
    "extensions.auth_key_label":{"zh-CN":"一次性 Auth Key","en":"One-time Auth Key"},
    "extensions.auth_key_placeholder":{"zh-CN":"粘贴一次性 Auth Key","en":"Paste a one-time Auth Key"},
    "extensions.auth_key_ticket_title":{"zh-CN":"给 VPS 一张一次性入网票据","en":"Give the VPS a one-time network ticket"},
    "extensions.auth_key_safe_help":{"zh-CN":"这不是账号密码。GenBox 只在本次任务中使用，任务创建后立即从页面清除，不写入浏览器存储、任务记录或日志。","en":"This is not your account password. GenBox uses it only for this task, clears it from the page after task creation, and never stores it in browser storage, task records, or logs."},
    "extensions.auth_key_options_help":{"zh-CN":"建议：Reusable 关闭、Ephemeral 关闭；需要设备审批时开启 Pre-approved。","en":"Recommended: Reusable off, Ephemeral off, and Pre-approved on when device approval is enabled."},
    "extensions.auth_key_required":{"zh-CN":"自动准备 VPS 需要粘贴一个新的一次性 Auth Key。","en":"Automatic VPS preparation needs a new one-time Auth Key."},
    "extensions.enter_auth_key":{"zh-CN":"输入 Auth Key","en":"Enter Auth Key"},
    "extensions.new_auth_key":{"zh-CN":"生成新的 Auth Key","en":"Generate a new Auth Key"},
    "extensions.read_address_again":{"zh-CN":"重新读取地址","en":"Read the address again"},
    "extensions.recheck_peer":{"zh-CN":"重新检测互通","en":"Recheck connectivity"},
    "extensions.check_local_entry":{"zh-CN":"检查本机私网入口","en":"Check the local private entry"},
    "extensions.manual_check_required":{"zh-CN":"查看人工处理说明","en":"View manual recovery guidance"},
    "extensions.network_context_changed":{"zh-CN":"VPS 或 SSH 信息已变化，旧任务结果不会覆盖当前页面。请使用当前信息重新开始。","en":"The VPS or SSH details changed. The old task result will not overwrite this page. Start again with the current details."},
    "extensions.network_waiting_user":{"zh-CN":"检测已完成，现在只等你做一件事。","en":"Detection is complete and is waiting for one action from you."},
    "extensions.guide_step4_waiting_user":{"zh-CN":"系统已经检查清楚","en":"The check is complete"},
    "extensions.guide_step4_action_ready":{"zh-CN":"现在只需要完成系统提示的这一项","en":"Complete the one action shown below"},
    "extensions.network_recovery_os_unsupported":{"zh-CN":"这个系统暂不在自动安装支持范围内。现有服务没有被修改。","en":"This operating system is not supported for automatic installation. Existing services were not changed."},
    "extensions.network_recovery_repository_conflict":{"zh-CN":"VPS 已有不同的软件源配置，GenBox 已停止并且没有覆盖它。","en":"The VPS already has a different repository configuration. GenBox stopped without overwriting it."},
    "extensions.network_recovery_repository_setup":{"zh-CN":"SSH 正常，但官方 Tailscale 软件源没有准备完成。请检查 VPS 网络和 sudo 权限。","en":"SSH works, but the official Tailscale repository could not be prepared. Check VPS networking and sudo access."},
    "extensions.network_recovery_install":{"zh-CN":"SSH 正常，但 Tailscale 软件包没有安装完成。现有应用服务没有被修改。","en":"SSH works, but the Tailscale package was not installed. Existing application services were not changed."},
    "extensions.network_recovery_service":{"zh-CN":"Tailscale 已安装，但后台服务没有成功运行。","en":"Tailscale is installed, but its background service is not running."},
    "extensions.network_recovery_auth_key":{"zh-CN":"现在只差一次性 Auth Key。这不是 SSH 密码错误。","en":"Only a one-time Auth Key is needed now. This is not an SSH password error."},
    "extensions.network_recovery_auth_file":{"zh-CN":"GenBox 无法以安全权限创建一次性密钥文件，已停止加入网络。","en":"GenBox could not create the one-time key file with safe permissions, so enrollment stopped."},
    "extensions.network_recovery_auth_rejected":{"zh-CN":"这个 Auth Key 可能已使用、过期，或不属于同一个 Tailnet。请生成一个新的。","en":"This Auth Key may be used, expired, or from a different Tailnet. Generate a new one."},
    "extensions.network_recovery_auth_cleanup":{"zh-CN":"一次性密钥临时文件未确认删除。请立即按提示人工清理后再继续。","en":"Deletion of the temporary Auth Key file was not confirmed. Follow the cleanup guidance before continuing."},
    "extensions.network_recovery_no_ipv4":{"zh-CN":"VPS 已加入 Tailnet，但私网地址仍在同步。稍后重新读取即可，不会重复安装。","en":"The VPS joined the Tailnet, but its private address is still syncing. Read it again later; installation will not repeat."},
    "extensions.network_recovery_peer":{"zh-CN":"电脑和 VPS 都已加入私网，但目前不能互相访问。请在 Tailscale 控制台确认两台设备在线。","en":"The computer and VPS joined the private network but cannot reach each other. Confirm both devices are online in the Tailscale console."},
    "extensions.network_recovery_genbox":{"zh-CN":"私网已经连通，但 VPS 打不开 GenBox。通常是本机私网入口未启用或端口不一致。","en":"The private network works, but the VPS cannot open GenBox. Usually the local private entry is disabled or the ports do not match."},
    "extensions.device_name":{"zh-CN":"设备名称","en":"Device name"},
    "extensions.management_url":{"zh-CN":"Management URL（自托管 NetBird 可选）","en":"Management URL (optional for self-hosted NetBird)"},
    "extensions.mobile_optional":{"zh-CN":"可选 · 手机也要访问 GenBox 时使用","en":"Optional · Use when a phone also needs GenBox access"},
    "extensions.mobile_title":{"zh-CN":"用手机扫码安装 Tailscale","en":"Scan to install Tailscale on a phone"},
    "extensions.mobile_step_1":{"zh-CN":"手机扫描右侧二维码，安装 Tailscale。","en":"Scan the QR code with your phone and install Tailscale."},
    "extensions.mobile_step_2":{"zh-CN":"使用与这台电脑相同的 Tailscale 账号登录。","en":"Sign in with the same Tailscale account as this computer."},
    "extensions.mobile_step_3":{"zh-CN":"连接完成后，手机即可通过私网地址访问 GenBox。","en":"After connecting, the phone can access GenBox through its private URL."},
    "extensions.mobile_privacy":{"zh-CN":"二维码只打开 Tailscale 官方下载页，不包含 Auth Key、密码或其他私密信息。","en":"The QR code only opens the official Tailscale download page. It contains no Auth Key, password, or other secret."},
    "extensions.mobile_download_label":{"zh-CN":"打开 Tailscale 官方下载页","en":"Open the official Tailscale download page"},
    "extensions.scan_download":{"zh-CN":"扫码打开官方下载页","en":"Scan to open the official download page"},
    "extensions.waiting_connection":{"zh-CN":"等待连接","en":"Waiting for connection"},
    "extensions.recheck_note":{"zh-CN":"已经安装并加入网络？无需新 Key，可只重新检查。","en":"Already installed and joined? Recheck without a new Key."},
    "extensions.recheck_link":{"zh-CN":"重新检查链路","en":"Recheck network"},
    "extensions.install_connect":{"zh-CN":"安装并连接","en":"Install and connect"},
    "extensions.verify_finish":{"zh-CN":"验证并完成","en":"Verify and finish"},
    "extensions.local_tailscale":{"zh-CN":"本机 Tailscale","en":"Local Tailscale"},
    "extensions.waiting_verification":{"zh-CN":"等待验证","en":"Waiting for verification"},
    "extensions.local_to_vps":{"zh-CN":"本机到 VPS","en":"Local to VPS"},
    "extensions.vps_to_genbox":{"zh-CN":"VPS 到 GenBox","en":"VPS to GenBox"},
    "extensions.private_url":{"zh-CN":"GenBox 私网 URL","en":"Private GenBox URL"},
    "extensions.waiting_generation":{"zh-CN":"等待生成","en":"Waiting to be generated"},
    "extensions.instance_ready":{"zh-CN":"实例已就绪","en":"Instance ready"},
    "extensions.console_url":{"zh-CN":"控制台地址","en":"Console URL"},
    "extensions.api_url":{"zh-CN":"API 地址","en":"API URL"},
    "extensions.admin_key":{"zh-CN":"管理密钥","en":"Management key"},
    "extensions.console_login_kicker":{"zh-CN":"下一步","en":"Next step"},
    "extensions.console_login_title":{"zh-CN":"登录 chatgpt2api 控制台","en":"Sign in to the chatgpt2api console"},
    "extensions.console_login_help":{"zh-CN":"已将本次交付的管理密钥带入下方输入框。你也可以手动替换它；点击后会复制密钥并打开私网控制台。","en":"The management key delivered in this session is prefilled below. You can replace it manually; the action copies it and opens the private console."},
    "extensions.console_login_key_placeholder":{"zh-CN":"粘贴或修改管理密钥","en":"Paste or replace management key"},
    "extensions.use_delivered_admin_key":{"zh-CN":"使用本次交付的管理密钥","en":"Use the management key delivered in this session"},
    "extensions.console_login_key_delivered":{"zh-CN":"已自动带入本次交付的管理密钥。","en":"The management key delivered in this session is prefilled."},
    "extensions.console_login_key_manual":{"zh-CN":"将使用你手动输入的管理密钥。","en":"Your manually entered management key will be used."},
    "extensions.console_login_key_missing":{"zh-CN":"请粘贴管理密钥，或在本次页面中使用已交付的密钥。","en":"Paste a management key, or use the one delivered on this page."},
    "extensions.console_login_key_cleared":{"zh-CN":"密钥已复制并从当前页面清除。","en":"The key was copied and cleared from this page."},
    "extensions.console_login_delivery_unavailable":{"zh-CN":"本次交付的管理密钥已不在页面中，请手动粘贴或重置此实例的管理密钥。","en":"The management key delivered in this session is no longer on this page. Paste it manually or reset this instance's management key."},
    "extensions.open_console_only":{"zh-CN":"仅打开控制台","en":"Open console only"},
    "extensions.copy_key_open_console":{"zh-CN":"复制密钥并打开控制台","en":"Copy key and open console"},
    "extensions.console_login_url_required":{"zh-CN":"控制台地址尚未准备好，请从已部署服务中打开控制台。","en":"The console address is not ready. Open the console from Deployed Services."},
    "extensions.console_login_key_required":{"zh-CN":"请先粘贴管理密钥。","en":"Paste the management key first."},
    "extensions.console_login_opened":{"zh-CN":"已复制管理密钥并打开控制台，请在新页面粘贴登录。","en":"The management key was copied and the console opened. Paste it on the new page to sign in."},
    "extensions.start_new_isolated":{"zh-CN":"新建隔离实例","en":"Create new isolated instance"},
    "extensions.new_isolated_started":{"zh-CN":"已开始新的隔离部署准备；现有受管实例不会被修改。","en":"A new isolated deployment is ready to plan. The existing managed instance will not be changed."},
    "extensions.push_source_kicker":{"zh-CN":"图片 Push 配置","en":"Image Push setup"},
    "extensions.push_source_title":{"zh-CN":"连接 chatgpt2api 与 GenBox","en":"Connect chatgpt2api to GenBox"},
    "extensions.push_source_help":{"zh-CN":"为这个隔离实例创建独立的 GenBox Push 凭据。密钥只会在创建或轮换后显示一次。","en":"Create an independent GenBox Push credential for this isolated instance. The key is shown only after creation or rotation."},
    "extensions.push_destination_url":{"zh-CN":"GenBox Push 地址","en":"GenBox Push URL"},
    "extensions.push_source_id":{"zh-CN":"来源 ID","en":"Source ID"},
    "extensions.push_key":{"zh-CN":"Push 密钥","en":"Push key"},
    "extensions.push_key_hidden":{"zh-CN":"仅创建或轮换后显示","en":"Shown only after create or rotate"},
    "extensions.push_create":{"zh-CN":"创建 Push 凭据","en":"Create Push credentials"},
    "extensions.push_copy_configuration":{"zh-CN":"复制配置","en":"Copy configuration"},
    "extensions.push_rotate":{"zh-CN":"轮换密钥","en":"Rotate key"},
    "extensions.push_revoke":{"zh-CN":"撤销来源","en":"Revoke source"},
    "extensions.push_source_not_configured":{"zh-CN":"尚未创建 Push 凭据。创建后，将把地址、来源 ID 和一次性密钥填入 chatgpt2api。","en":"Push credentials have not been created. Create them, then enter the URL, source ID, and one-time key in chatgpt2api."},
    "extensions.push_source_ready":{"zh-CN":"Push 凭据已启用。密钥不会再次显示；需要更换时请轮换。","en":"Push credentials are enabled. The key will not be shown again; rotate it when replacement is needed."},
    "extensions.push_source_created":{"zh-CN":"Push 凭据已创建。请立即复制配置到 chatgpt2api。","en":"Push credentials were created. Copy the configuration to chatgpt2api now."},
    "extensions.push_source_rotated":{"zh-CN":"Push 密钥已轮换，旧密钥已失效。请立即复制新配置。","en":"The Push key was rotated and the old key is invalid. Copy the new configuration now."},
    "extensions.push_rotated_save_pending":{"zh-CN":"Push 密钥已轮换，旧密钥已失效；本机加密保存尚未完成。请解锁凭证库后点击“保存到本机凭证库”重试。","en":"The Push key was rotated and the old key is invalid, but local vault saving is pending. Unlock the vault, then choose Save to local vault to retry."},
    "extensions.push_source_revoked":{"zh-CN":"Push 来源已撤销，chatgpt2api 将无法继续推送。","en":"The Push source was revoked and chatgpt2api can no longer push."},
    "extensions.push_source_handle_missing":{"zh-CN":"当前没有可配置的受管 chatgpt2api 实例。","en":"There is no managed chatgpt2api instance available to configure."},
    "extensions.push_copy_required":{"zh-CN":"请先创建或轮换 Push 密钥。","en":"Create or rotate the Push key first."},
    "extensions.push_configuration_copied":{"zh-CN":"Push 配置已复制。","en":"Push configuration copied."},
    "extensions.push_save_locally":{"zh-CN":"加密保存这个新 Push 密钥到本机凭证库","en":"Save this new Push key in the encrypted local vault"},
    "extensions.push_save_warning":{"zh-CN":"仅在本机凭证库已解锁时保存。取消或未勾选时，密钥只显示一次。","en":"Only save while the local vault is unlocked. If unchecked, the key is shown once only."},
    "extensions.push_save_confirm":{"zh-CN":"确认将这个新 Push 密钥加密保存到本机凭证库？之后仍需凭证库解锁密码才能读取。","en":"Confirm saving this new Push key in the encrypted local vault?"},
    "extensions.push_save_opt_in_required":{"zh-CN":"请先勾选本地保存并确认风险。","en":"Check local save and confirm the warning first."},
    "extensions.push_saved_locally":{"zh-CN":"Push 密钥已加密保存到本机；远端来源未改变。","en":"The Push key was encrypted and saved locally; the remote source was unchanged."},
    "extensions.manage_push_configuration":{"zh-CN":"管理 Push 配置","en":"Manage Push configuration"},
    "extensions.push_existing_opened":{"zh-CN":"已打开这个实例的 GenBox Push 配置。","en":"Opened this instance's GenBox Push configuration."},
    "extensions.push_rotate_confirm":{"zh-CN":"轮换后，chatgpt2api 当前保存的 Push 密钥会立即失效。继续轮换吗？","en":"Rotation immediately invalidates the Push key currently stored in chatgpt2api. Continue?"},
    "extensions.push_revoke_confirm":{"zh-CN":"撤销后，该 chatgpt2api 实例将不能再向 GenBox Push 图片。继续撤销吗？","en":"After revocation, this chatgpt2api instance cannot push images to GenBox. Continue?"},
    "status.interrupted":{"zh-CN":"已中断","en":"Interrupted"},
    "status.skipped":{"zh-CN":"无需处理","en":"No action needed"},
    "status.needs_action":{"zh-CN":"等你操作","en":"Waiting for you"},
    "extensions.task_interrupted":{"zh-CN":"部署任务因 GenBox 重启而中断。","en":"The deployment task was interrupted by a GenBox restart."},
    "extensions.recovery_required":{"zh-CN":"需要恢复操作。","en":"Recovery action is required."},
    "extensions.recovery_regenerate_plan":{"zh-CN":"请重新生成计划并重新提供凭证；不会自动重放远程部署。","en":"Regenerate the plan and provide credentials again; remote deployment will not be replayed automatically."},
    "extensions.recovery_rotate_admin_key":{"zh-CN":"一次性管理密钥无法在重启后读取；请重新验证所有权后轮换密钥。","en":"The one-time management key cannot be read after restart; reverify ownership and rotate it."},
    "extensions.deploy_failure_stage_prefix":{"zh-CN":"失败阶段：","en":"Failed stage: "},
    "extensions.deploy_failure_reason_prefix":{"zh-CN":"原因：","en":"Reason: "},
    "extensions.deploy_failure_recovery_prefix":{"zh-CN":"下一步：","en":"Next: "},
    "extensions.deploy_failure_unknown_stage":{"zh-CN":"部署流程","en":"deployment process"},
    "extensions.deploy_failure_unknown_reason":{"zh-CN":"部署未能安全完成。","en":"The deployment could not be completed safely."},
    "extensions.deploy_failure_unknown_recovery":{"zh-CN":"请检查此 GenBox 管理的实例状态，并重新生成部署计划。","en":"Inspect the GenBox-managed instance state and regenerate the deployment plan."},
    "extensions.deploy_error_host_key_confirmation_required":{"zh-CN":"继续前必须确认 SSH 主机指纹。","en":"The SSH host key must be confirmed before continuing."},
    "extensions.deploy_error_connection_failed":{"zh-CN":"无法建立安全的 SSH 连接。","en":"The secure SSH connection could not be established."},
    "extensions.deploy_error_docker_unavailable":{"zh-CN":"部署用户无法使用 Docker。","en":"Docker is unavailable to the deployment user."},
    "extensions.deploy_error_preparation_failed":{"zh-CN":"无法安全准备托管部署目录或配置。","en":"The managed deployment directory or configuration could not be prepared safely."},
    "extensions.deploy_error_image_prepare_failed":{"zh-CN":"无法准备指定的容器镜像。","en":"The approved container image could not be prepared."},
    "extensions.deploy_error_service_start_failed":{"zh-CN":"托管服务未能启动。","en":"The managed service could not be started."},
    "extensions.deploy_error_service_verification_failed":{"zh-CN":"服务没有通过就绪检查。","en":"The service did not pass its readiness check."},
    "extensions.deploy_error_instance_registration_failed":{"zh-CN":"远程服务已成功，但 GenBox 未能在本地登记实例。","en":"The remote service succeeded, but GenBox could not register the instance locally."},
    "extensions.deploy_recovery_confirm_host_key":{"zh-CN":"核对并确认主机指纹后，重新生成计划。","en":"Verify and confirm the host fingerprint, then regenerate the plan."},
    "extensions.deploy_recovery_check_ssh_connection_and_credentials":{"zh-CN":"检查 SSH 网络、端口和凭据，然后重新生成计划。","en":"Check SSH networking, port, and credentials, then regenerate the plan."},
    "extensions.deploy_recovery_fix_docker_access_and_regenerate_plan":{"zh-CN":"修复 Docker 或 sudo 权限后重新生成计划。","en":"Fix Docker or sudo access, then regenerate the plan."},
    "extensions.deploy_recovery_inspect_owned_partial_deployment_and_regenerate_plan":{"zh-CN":"只检查 GenBox 所有的未完成目录，确认状态后重新生成计划。","en":"Inspect only the GenBox-owned partial deployment, confirm its state, then regenerate the plan."},
    "extensions.deploy_recovery_check_image_access_and_regenerate_plan":{"zh-CN":"检查镜像名称和访问权限后重新生成计划。","en":"Check the image name and access, then regenerate the plan."},
    "extensions.deploy_recovery_inspect_owned_instance_and_regenerate_plan":{"zh-CN":"检查 GenBox 所有的实例和容器状态后重新生成计划。","en":"Inspect the GenBox-owned instance and container state, then regenerate the plan."},
    "extensions.deploy_recovery_verify_owned_instance_stopped_before_retry":{"zh-CN":"重试前先人工确认 GenBox 所有的实例已经停止。","en":"Before retrying, manually confirm that the GenBox-owned instance is stopped."},
    "extensions.deploy_recovery_reconcile_owned_instance_registration":{"zh-CN":"核对远程 GenBox 所有权标记，再修复本地实例登记；不要重复部署。","en":"Reconcile the local registration against the remote GenBox ownership markers; do not redeploy."},
    "extensions.delivery_choice":{"zh-CN":"交付后如何处理","en":"After delivery"},
    "extensions.show_once":{"zh-CN":"仅本次显示","en":"Show this time only"},
    "extensions.save_encrypted":{"zh-CN":"加密保存在本机","en":"Save encrypted locally"},
    "extensions.save_warning":{"zh-CN":"本地保存便于以后查看，但任何能访问此 GenBox 和解锁密码的人都可能读取凭证。解锁密码不会保存。","en":"Local saving allows later access, but anyone who can access this GenBox and knows the unlock password may read the credential. The unlock password is not saved."},
    "extensions.vault_password_first":{"zh-CN":"凭证库解锁密码（首次至少 8 位）","en":"Vault unlock password (at least 8 characters initially)"},
    "extensions.save_to_vault":{"zh-CN":"保存到本机凭证库","en":"Save to local credential vault"},
    "extensions.checklist_login":{"zh-CN":"打开控制台并粘贴管理密钥登录","en":"Open the console and paste the management key to sign in"},
    "extensions.checklist_accounts":{"zh-CN":"检查账号池和代理出口","en":"Check the account pool and proxy egress"},
    "extensions.checklist_push":{"zh-CN":"配置 GenBox Push 并先测试连接","en":"Configure GenBox Push and test the connection first"},
    "extensions.checklist_delete":{"zh-CN":"完成多轮验证前不要开启源图片删除","en":"Do not enable source-image deletion before repeated verification"},
    "extensions.lost_key":{"zh-CN":"管理密钥丢失？重置此实例","en":"Lost the management key? Reset this instance"},
    "extensions.success_title":{"zh-CN":"恭喜你，GenBox 私有链路已经打通","en":"Your private GenBox link is connected"},
    "extensions.success_copy":{"zh-CN":"接下来，你可以让远程 AI 服务安全地把图片送入 GenBox 媒体库，享受自动归档、统一管理与跨设备访问的流畅体验。","en":"Remote AI services can now deliver images safely to the GenBox media library for automatic organization, central management, and cross-device access."},
    "extensions.summary":{"zh-CN":"部署摘要","en":"Deployment summary"},
    "extensions.service":{"zh-CN":"服务","en":"Service"},
    "extensions.target_name":{"zh-CN":"VPS 名称","en":"VPS name"},
    "extensions.vps_host":{"zh-CN":"VPS 地址 / SSH 端口","en":"VPS address / SSH port"},
    "extensions.deployed_at":{"zh-CN":"部署时间","en":"Deployed"},
    "extensions.credential_saved_at":{"zh-CN":"凭证保存时间","en":"Credential saved"},
    "extensions.view_details":{"zh-CN":"查看连接详情","en":"View connection details"},
    "extensions.primary_link":{"zh-CN":"主链路","en":"Primary network"},
    "extensions.credential":{"zh-CN":"凭证","en":"Credential"},
    "extensions.credential_session":{"zh-CN":"仅在当前任务中使用","en":"Used only for the current task"},
    "extensions.deployed_services_label":{"zh-CN":"已部署服务","en":"Deployed services"},
    "extensions.vault":{"zh-CN":"本机凭证库","en":"Local credential vault"},
    "extensions.checking":{"zh-CN":"正在检查…","en":"Checking…"},
    "extensions.vault_password":{"zh-CN":"解锁密码（至少 8 位）","en":"Unlock password (at least 8 characters)"},
    "extensions.setup_unlock":{"zh-CN":"设置 / 解锁","en":"Set up / Unlock"},
    "extensions.lock":{"zh-CN":"锁定","en":"Lock"},
    "extensions.reset_key_label":{"zh-CN":"重置管理密钥","en":"Reset management key"},
    "extensions.reset_warning":{"zh-CN":"为安全起见，重置需要重新验证该实例所属 VPS 的所有权。密钥仅在本机显示一次；旧密钥立即失效。","en":"For security, resetting requires ownership verification of the instance's VPS. The new key is shown locally once and the old key is invalidated immediately."},
    "extensions.or_private_key":{"zh-CN":"或 SSH 私钥","en":"or SSH private key"},
    "extensions.new_key_once":{"zh-CN":"新管理密钥（仅本次显示）","en":"New management key (shown once)"},
    "extensions.vault_password_locked":{"zh-CN":"凭证库解锁密码（如已锁定）","en":"Vault unlock password (if locked)"},
    "extensions.save_local_copy":{"zh-CN":"保存 / 更新本地副本","en":"Save / Update local copy"},
    "extensions.confirm_reset":{"zh-CN":"确认重置","en":"Confirm reset"},
    "extensions.saved_credential_label":{"zh-CN":"本机保存的凭证","en":"Locally saved credential"},
    "extensions.vps_password":{"zh-CN":"VPS SSH 密码","en":"VPS SSH password"},
    "extensions.vps_private_key":{"zh-CN":"VPS SSH 私钥","en":"VPS SSH private key"},
    "extensions.key_passphrase":{"zh-CN":"SSH 私钥口令","en":"SSH key passphrase"},
    "extensions.vps_sudo":{"zh-CN":"VPS sudo 密码","en":"VPS sudo password"},
    "extensions.username":{"zh-CN":"用户名","en":"Username"},
    "extensions.note":{"zh-CN":"备注","en":"Note"},
    "extensions.reveal":{"zh-CN":"显示 / 隐藏","en":"Show / Hide"},
    "extensions.copy_admin_key":{"zh-CN":"复制管理密钥","en":"Copy management key"},
    "extensions.delete_local":{"zh-CN":"删除本地副本","en":"Delete local copy"},
    "extensions.save_changes":{"zh-CN":"保存修改","en":"Save changes"},
    "footer.local_service":{"zh-CN":"GenBox · 本地服务","en":"GenBox · Local service"},
    "runtime.online":{"zh-CN":"在线","en":"Online"},
    "runtime.offline":{"zh-CN":"后端离线","en":"Backend offline"},
    "runtime.offline_title":{"zh-CN":"GenBox 后端未运行","en":"GenBox backend is not running"},
    "runtime.offline_detail":{"zh-CN":"当前只是浏览器保留的旧页面，连接和部署操作已暂停。","en":"This is only a browser-retained page. Connection and deployment actions are paused."},
    "runtime.recheck":{"zh-CN":"重新检测","en":"Check again"},
    "dock.expand":{"zh-CN":"展开底部导航","en":"Expand bottom navigation"},
    "sync.title":{"zh-CN":"☁ 从远程 chatgpt2api 同步图片","en":"☁ Sync images from remote chatgpt2api"},
    "sync.close_label":{"zh-CN":"关闭远程同步窗口","en":"Close remote sync"},
    "sync.step_1":{"zh-CN":"填写并保存远程部署","en":"Enter and save a remote deployment"},
    "sync.step_2":{"zh-CN":"选择部署 → 点「扫描预览」","en":"Choose a deployment → Select Scan preview"},
    "sync.step_3":{"zh-CN":"勾选图片 → 点「同步选中」","en":"Select images → Select Sync selected"},
    "sync.add_deployment":{"zh-CN":"① 添加远程部署（chatgpt2api）","en":"① Add remote deployment (chatgpt2api)"},
    "sync.name_placeholder":{"zh-CN":"名称（如 我的VPS）","en":"Name (for example, My VPS)"},
    "sync.url_placeholder":{"zh-CN":"Base URL（如 http://host:3000）","en":"Base URL (for example, http://host:3000)"},
    "sync.save_deployment":{"zh-CN":"保存部署","en":"Save deployment"},
    "sync.endpoint_prefix":{"zh-CN":"：填写 chatgpt2api「接口信息」页的","en":": Enter the value from chatgpt2api's API Information page:"},
    "sync.base_endpoint":{"zh-CN":"基础端点","en":"Base endpoint"},
    "sync.endpoint_example":{"zh-CN":"（例如 http://host:3000）","en":"(for example, http://host:3000)"},
    "sync.current_key":{"zh-CN":"当前调用密钥","en":"Current API key"},
    "sync.preview_title":{"zh-CN":"② 扫描预览并选择图片","en":"② Scan, preview, and select images"},
    "sync.choose_deployment":{"zh-CN":"— 选择部署 —","en":"— Choose deployment —"},
    "sync.all_time":{"zh-CN":"全部时间","en":"All time"},
    "sync.today":{"zh-CN":"今天","en":"Today"},
    "sync.this_month":{"zh-CN":"本月","en":"This month"},
    "sync.custom_range":{"zh-CN":"自定义范围","en":"Custom range"},
    "sync.any_ratio":{"zh-CN":"比例不限","en":"Any ratio"},
    "sync.square":{"zh-CN":"正方形","en":"Square"},
    "sync.portrait":{"zh-CN":"竖图","en":"Portrait"},
    "sync.landscape":{"zh-CN":"横图","en":"Landscape"},
    "sync.any_size":{"zh-CN":"大小不限","en":"Any size"},
    "sync.scan_preview":{"zh-CN":"扫描预览","en":"Scan preview"},
    "sync.instructions":{"zh-CN":"先在上方的部署列表中选择一个部署，再点「扫描预览」拉取远端图片（自动按内容去重）。预览图加载完成后，勾选要同步的图片，最后点「同步选中」。","en":"Choose a deployment above, then select Scan preview to load remote images with content deduplication. After previews load, select the images and choose Sync selected."},
    "sync.selected_zero":{"zh-CN":"已选 0","en":"0 selected"},
    "sync.sync_selected":{"zh-CN":"⬇️ 同步选中 (","en":"⬇️ Sync selected ("},
    "sync.empty_hint":{"zh-CN":"选择部署后点击「预览」以拉取远端图片并去重。","en":"Choose a deployment and select Preview to load and deduplicate remote images."},
    "sync.preparing":{"zh-CN":"准备中…","en":"Preparing…"},
    "error.http_prefix":{"zh-CN":"服务返回 HTTP ","en":"Service returned HTTP "},
    "error.check_logs":{"zh-CN":"，请查看 GenBox 日志","en":". Check the GenBox logs."},
    "error.invalid_response":{"zh-CN":"服务返回了无法识别的数据","en":"The service returned unrecognized data"},
    "error.request_failed":{"zh-CN":"请求失败","en":"Request failed"},
    "extensions.unsaved_option":{"zh-CN":"<option value=\"\">当前未保存</option>","en":"<option value=\"\">Current target is not saved</option>"},
    "extensions.save_vps_first":{"zh-CN":"<div class=\"extension-placeholder\">请先在第 1 步保存至少一台 VPS。</div>","en":"<div class=\"extension-placeholder\">Save at least one VPS in step 1 first.</div>"},
    "extensions.network_verified":{"zh-CN":"私网已验证","en":"Private network verified"},
    "extensions.batch_selected_prefix":{"zh-CN":"当前已选中 ","en":"Selected "},
    "extensions.batch_servers":{"zh-CN":" 台服务器：","en":" servers: "},
    "extensions.batch_suffix":{"zh-CN":"。你将为这些服务器规划 chatgpt2api 部署。","en":". A chatgpt2api deployment will be planned for these servers."},
    "extensions.available":{"zh-CN":"可部署","en":"Available"},
    "extensions.repo_unconfirmed":{"zh-CN":"仓库待确认","en":"Repository unconfirmed"},
    "extensions.planned":{"zh-CN":"规划中","en":"Planned"},
    "extensions.load_config_failed":{"zh-CN":"无法读取扩展配置：","en":"Could not load extension settings: "},
    "extensions.group_gateways":{"zh-CN":"API 代理与模型网关","en":"API proxies and model gateways"},
    "extensions.group_accounts":{"zh-CN":"账号注册与 Token 管理","en":"Account registration and token management"},
    "extensions.group_networks":{"zh-CN":"代理网络与节点工具","en":"Proxy networks and node tools"},
    "extensions.deployed":{"zh-CN":"已部署","en":"Deployed"},
    "extensions.loading_html":{"zh-CN":"<span class=\"extension-placeholder\">正在加载…</span>","en":"<span class=\"extension-placeholder\">Loading…</span>"},
    "extensions.no_deployments_html":{"zh-CN":"<span class=\"extension-placeholder\">还没有已部署的服务。完成一次部署后会出现在这里。</span>","en":"<span class=\"extension-placeholder\">No deployed services yet. Services appear here after deployment.</span>"},
    "extensions.managed_badge":{"zh-CN":"<span class=\"ext-badge-managed\">GenBox 托管</span>","en":"<span class=\"ext-badge-managed\">Managed by GenBox</span>"},
    "extensions.service_meta_html":{"zh-CN":"</span><dl class=\"ext-service-meta\"><div><dt>类型</dt><dd>","en":"</span><dl class=\"ext-service-meta\"><div><dt>Type</dt><dd>"},
    "extensions.service_port_html":{"zh-CN":"</dd></div><div><dt>端口</dt><dd>","en":"</dd></div><div><dt>Port</dt><dd>"},
    "extensions.service_time_html":{"zh-CN":"</dd></div><div><dt>部署时间</dt><dd>","en":"</dd></div><div><dt>Deployed</dt><dd>"},
    "extensions.open_console_html":{"zh-CN":"\" target=\"_blank\" rel=\"noopener noreferrer\">打开控制台</a>","en":"\" target=\"_blank\" rel=\"noopener noreferrer\">Open console</a>"},
    "extensions.copy_api_html":{"zh-CN":">复制 API 地址</button>","en":">Copy API URL</button>"},
    "extensions.reset_key_html":{"zh-CN":"\\')\">重置密钥</button>","en":"\\')\">Reset key</button>"},
    "extensions.planned_html":{"zh-CN":"<span class=\"extension-placeholder\">规划中（尚未部署）</span>","en":"<span class=\"extension-placeholder\">Planned (not deployed)</span>"},
    "extensions.load_services_failed_html":{"zh-CN":"<span class=\"extension-placeholder\">无法读取已部署服务：","en":"<span class=\"extension-placeholder\">Could not load deployed services: "},
    "extensions.planned_status_html":{"zh-CN":"</span><span class=\"ext-status-tag ext-status-planned\">规划中</span></div>","en":"</span><span class=\"ext-status-tag ext-status-planned\">Planned</span></div>"},
    "extensions.accounts_short":{"zh-CN":"账号与 Token","en":"Accounts and tokens"},
    "extensions.network_short":{"zh-CN":"代理网络","en":"Proxy networks"},
    "vault.not_configured":{"zh-CN":"尚未设置","en":"Not set up"},
    "vault.unlocked_prefix":{"zh-CN":"已解锁 · ","en":"Unlocked · "},
    "vault.entry_suffix":{"zh-CN":" 项","en":" entries"},
    "vault.locked_prefix":{"zh-CN":"已锁定 · ","en":"Locked · "},
    "vault.saved":{"zh-CN":"凭证已保存","en":"Credential saved"},
    "vault.not_saved":{"zh-CN":"凭证未保存","en":"Credential not saved"},
    "vault.view":{"zh-CN":"查看凭证","en":"View credential"},
    "vault.unlock_to_view":{"zh-CN":"解锁后查看","en":"Unlock to view"},
    "vault.save_login":{"zh-CN":"保存登录信息","en":"Save sign-in details"},
    "common.copied":{"zh-CN":"已复制。","en":"Copied."},
    "common.copy_failed_manual":{"zh-CN":"复制失败，请手动选择复制。","en":"Copy failed. Select and copy manually."},
    "vault.setup_success":{"zh-CN":"本机凭证库已设置并解锁。","en":"Local credential vault set up and unlocked."},
    "vault.unlock_success":{"zh-CN":"本机凭证库已解锁。","en":"Local credential vault unlocked."},
    "vault.operation_failed":{"zh-CN":"凭证库操作失败：","en":"Credential vault operation failed: "},
    "vault.lock_success":{"zh-CN":"本机凭证库已锁定。","en":"Local credential vault locked."},
    "vault.no_admin_key":{"zh-CN":"没有可保存的管理密钥","en":"No management key to save"},
    "vault.admin_saved":{"zh-CN":"管理密钥已加密保存到本机。","en":"Management key encrypted and saved locally."},
    "common.save_failed_prefix":{"zh-CN":"保存失败：","en":"Save failed: "},
    "vault.reset_saved":{"zh-CN":"新的管理密钥已更新到本机凭证库。","en":"The new management key was updated in the local vault."},
    "vault.unlock_first":{"zh-CN":"请先在凭证库栏输入解锁密码；首次使用可直接设置。","en":"Enter the vault password first. On first use, this sets up the vault."},
    "extensions.instance_prefix":{"zh-CN":"实例：","en":"Instance: "},
    "vault.read_failed":{"zh-CN":"读取凭证失败：","en":"Could not read credential: "},
    "vault.update_success":{"zh-CN":"本机凭证已更新。","en":"Local credential updated."},
    "common.update_failed_prefix":{"zh-CN":"更新失败：","en":"Update failed: "},
    "vault.delete_confirm":{"zh-CN":"仅删除此实例的本机凭证副本？远端凭证不会改变。","en":"Delete only the local credential copy for this instance? The remote credential will not change."},
    "vault.delete_success":{"zh-CN":"本机凭证副本已删除；远端凭证未改变。","en":"Local credential copy deleted. The remote credential was not changed."},
    "common.delete_failed_prefix":{"zh-CN":"删除失败：","en":"Delete failed: "},
    "extensions.owner_credential_required":{"zh-CN":"请填写 SSH 密码或私钥以验证所有权。","en":"Enter an SSH password or private key to verify ownership."},
    "extensions.reset_success_once":{"zh-CN":"管理密钥已重置并验证，新密钥仅在此显示一次。","en":"Management key reset and verified. The new key is shown here once."},
    "extensions.reset_failed_prefix":{"zh-CN":"重置失败：","en":"Reset failed: "},
    "extensions.target_loaded_prefix":{"zh-CN":"已载入 ","en":"Loaded "},
    "extensions.target_loaded_suffix":{"zh-CN":"。请重新输入 SSH 凭证后测试连接。","en":". Re-enter SSH credentials and test the connection."},
    "extensions.new_vps_name":{"zh-CN":"新 VPS","en":"New VPS"},
    "extensions.new_target_success":{"zh-CN":"已创建空白 VPS 配置。","en":"Created a blank VPS configuration."},
    "extensions.target_required":{"zh-CN":"请填写名称、VPS 地址、SSH 用户名，并选择服务器用途。","en":"Enter a name, VPS address, SSH username, and server purpose."},
    "extensions.target_saved":{"zh-CN":"VPS 配置保存成功。SSH 密码、私钥和 sudo 密码未保存。","en":"VPS configuration saved. SSH password, private key, and sudo password were not saved."},
    "extensions.target_delete_confirm":{"zh-CN":"删除这台 VPS 的已保存配置？","en":"Delete the saved configuration for this VPS?"},
    "extensions.target_deleted":{"zh-CN":"VPS 配置已删除。","en":"VPS configuration deleted."},
    "extensions.setup_key":{"zh-CN":"一次性 Setup Key","en":"One-time Setup Key"},
    "extensions.tailscale_enroll":{"zh-CN":"使用一次性 Auth Key 注册 VPS。","en":"Enroll the VPS with a one-time Auth Key."},
    "extensions.netbird_enroll":{"zh-CN":"使用一次性 Setup Key 注册 VPS；自托管用户可填写 Management URL。","en":"Enroll the VPS with a one-time Setup Key. Self-hosted users may enter a Management URL."},
    "extensions.cloudflare_enroll":{"zh-CN":"使用 Cloudflare 控制台生成的 Tunnel Token 安装系统服务。","en":"Install the service with a Tunnel Token generated in the Cloudflare dashboard."},
    "extensions.tunnel_endpoint":{"zh-CN":"GenBox 隧道端","en":"GenBox tunnel endpoint"},
    "extensions.secret_not_saved_suffix":{"zh-CN":" 授权信息不会写入浏览器存储或任务日志。","en":" Authorization data is not written to browser storage or task logs."},
    "extensions.tailscale_key_help_html":{"zh-CN":"<a href=\"https://login.tailscale.com/admin/settings/keys\" target=\"_blank\" rel=\"noopener noreferrer\">没有 Key？点击打开官方生成页面</a><span>生成后，把完整的一次性 Auth Key 粘贴到下面。</span>","en":"<a href=\"https://login.tailscale.com/admin/settings/keys\" target=\"_blank\" rel=\"noopener noreferrer\">No Key? Open the official generation page</a><span>Paste the complete one-time Auth Key below.</span>"},
    "extensions.other_key_help_html":{"zh-CN":"<span>请从所选网络服务的控制台生成一次性授权信息，再粘贴到下面。</span>","en":"<span>Generate one-time authorization data in the selected network service, then paste it below.</span>"},
    "extensions.token_placeholder":{"zh-CN":"粘贴一次性授权信息","en":"Paste one-time authorization data"},
    "extensions.cloudflare_remote_hint":{"zh-CN":"GenBox 会建立安全隧道，VPS 只做访问检测。","en":"GenBox creates the secure tunnel; the VPS only verifies access."},
    "extensions.testing_ssh":{"zh-CN":"正在测试 SSH 连接…","en":"Testing SSH connection…"},
    "extensions.fingerprint_prefix":{"zh-CN":"首次连接主机指纹：<code>","en":"First connection host fingerprint: <code>"},
    "extensions.fingerprint_confirm_html":{"zh-CN":"</code><br><button class=\"btn-secondary\" id=\"extHostKeyConfirmBtn\" onclick=\"extensionTestSSH(true)\">确认指纹并认证</button>","en":"</code><br><button class=\"btn-secondary\" id=\"extHostKeyConfirmBtn\" onclick=\"extensionTestSSH(true)\">Confirm fingerprint and authenticate</button>"},
    "extensions.verify_fingerprint":{"zh-CN":"请核对并确认 VPS 主机指纹","en":"Verify and confirm the VPS host fingerprint"},
    "extensions.root_user":{"zh-CN":"root 用户","en":"root user"},
    "extensions.docker_access":{"zh-CN":"Docker 可直接使用","en":"Direct Docker access"},
    "extensions.use_sudo":{"zh-CN":"将使用 sudo 提权","en":"Will elevate with sudo"},
    "extensions.no_deploy_access":{"zh-CN":"没有可用的部署权限","en":"No usable deployment permission"},
    "extensions.ssh_success_prefix":{"zh-CN":"SSH 连接成功，主机指纹已确认；","en":"SSH connected and host fingerprint confirmed; "},
    "extensions.system":{"zh-CN":"系统","en":"System"},
    "extensions.cpu_suffix":{"zh-CN":" 核","en":" cores"},
    "extensions.memory":{"zh-CN":"内存","en":"Memory"},
    "extensions.disk":{"zh-CN":"磁盘","en":"Disk"},
    "extensions.not_installed":{"zh-CN":"未安装","en":"Not installed"},
    "extensions.used_ports":{"zh-CN":"已用端口","en":"Ports in use"},
    "extensions.no_instances_html":{"zh-CN":"<span class=\"extension-placeholder\">未发现 chatgpt2api 实例</span>","en":"<span class=\"extension-placeholder\">No chatgpt2api instances found</span>"},
    "extensions.choose_existing_html":{"zh-CN":"<option value=\"\">选择现有主应用实例</option>","en":"<option value=\"\">Choose an existing primary app instance</option>"},
    "extensions.recommended_suffix":{"zh-CN":" · 推荐","en":" · Recommended"},
    "extensions.unavailable_suffix":{"zh-CN":" 当前环境不可用","en":" Unavailable in this environment"},
    "extensions.instances_found":{"zh-CN":"检测到已有应用实例。当前开发场景推荐创建安全隔离副本，源服务不会被修改。","en":"Existing app instances found. For development, create a safely isolated copy. The source service will not be modified."},
    "extensions.no_clone_source":{"zh-CN":"环境检测完成，未发现可克隆的应用实例。","en":"Discovery completed. No cloneable app instance was found."},
    "extensions.existing_selected":{"zh-CN":"已选择已有实例。接入计划不会执行远程变更。","en":"Existing instance selected. The connection plan will make no remote changes."},
    "extensions.baseline_selected":{"zh-CN":"已选择生产镜像基线。请重新生成安全计划。","en":"Production image baseline selected. Regenerate the safety plan."},
    "extensions.verify_ssh_first":{"zh-CN":"请先返回第一步测试 SSH 并确认主机指纹。","en":"Return to step 1, test SSH, and confirm the host fingerprint first."},
    "extensions.ssh_not_saved_notice":{"zh-CN":"保存 VPS 连接信息，但不保存 SSH 密码、私钥或 sudo 密码；关闭页面或重启后需要重新输入。","en":"VPS connection details are saved, but SSH passwords, private keys, and sudo passwords are not. Re-enter them after closing or restarting."},
    "extensions.save_target_before_test":{"zh-CN":"请先保存当前 VPS 信息，再输入本次会话的 SSH 凭据。","en":"Save the current VPS details before entering SSH credentials for this session."},
    "extensions.enter_ssh_password":{"zh-CN":"请输入本次会话使用的 SSH 密码；密码不会随 VPS 信息保存。","en":"Enter the SSH password for this session. It is not saved with the VPS details."},
    "extensions.enter_ssh_private_key":{"zh-CN":"请粘贴本次会话使用的 SSH 私钥；私钥不会随 VPS 信息保存。","en":"Paste the SSH private key for this session. It is not saved with the VPS details."},
    "extensions.ssh_ready_notice":{"zh-CN":"凭据已填写，可以进行一次 SSH 测试。测试期间按钮会锁定，避免重复请求。","en":"Credentials are ready for one SSH test. The button is locked while the request is running."},
    "extensions.ssh_verified_notice":{"zh-CN":"本次会话的 SSH 已验证。修改地址、账号、端口或凭据后需要重新验证。","en":"SSH is verified for this session. Changing the address, account, port, or credentials requires verification again."},
    "extensions.deploy_ready_network_pending":{"zh-CN":"服务已经部署完成，私网链路尚未完成。现在从“选择链路”继续，不会重复部署。","en":"The service is deployed, but the private network is not complete. Continue from Choose Network without redeploying."},
    "extensions.start_network_check":{"zh-CN":"开始检测私网链路","en":"Start private-network check"},
    "extensions.return_network_check":{"zh-CN":"返回链路检测","en":"Return to network check"},
    "extensions.ssh_diag_password_requested":{"zh-CN":"诊断阶段：客户端已取得会话凭据，但认证尚未完成；请勿连续重试。","en":"Diagnostic stage: the client obtained the session credential, but authentication did not complete. Do not retry repeatedly."},
    "extensions.ssh_diag_auth_started":{"zh-CN":"诊断阶段：SSH 认证已开始，但客户端尚未取得密码。","en":"Diagnostic stage: SSH authentication started before the client obtained a password."},
    "extensions.ssh_diag_host_verified":{"zh-CN":"诊断阶段：主机指纹已确认，连接在认证开始前结束。","en":"Diagnostic stage: the host key was verified, but the connection ended before authentication started."},
    "extensions.ssh_diag_transport":{"zh-CN":"诊断阶段：SSH 传输已建立，连接在主机确认或认证前结束。","en":"Diagnostic stage: SSH transport was established, but the connection ended before host verification or authentication."},
    "extensions.ssh_safe_failure":{"zh-CN":"SSH 客户端认证未完成，原始错误已隐藏。不能据此判断密码错误，请勿连续重试。","en":"SSH client authentication did not complete. Raw details were hidden; do not retry repeatedly."},
    "extensions.ssh_no_repair_loop":{"zh-CN":"请保留当前服务器身份记录和凭据页面；这不是重新配对步骤。","en":"Keep the current server identity and credential view; this is not a pairing step."},
    "extensions.ssh_diagnostic_optional":{"zh-CN":"诊断 SSH（可选）","en":"Diagnose SSH (optional)"},
    "extensions.ssh_deploy_diagnostic":{"zh-CN":"测试 SSH 与部署权限","en":"Test SSH and deployment access"},
    "extensions.ssh_optional_notice":{"zh-CN":"凭据已填写。SSH 诊断是可选项，不是私网检测的前置条件。","en":"Credentials are ready. SSH diagnosis is optional and not a private-link prerequisite."},
    "extensions.ssh_deploy_notice":{"zh-CN":"主机指纹已确认。现在测试 SSH 与部署权限，通过后即可继续部署。","en":"The host key is confirmed. Test SSH and deployment access before continuing."},
    "extensions.read_confirm_host_key":{"zh-CN":"读取并确认主机指纹","en":"Read and confirm host key"},
    "extensions.host_key_setup_notice":{"zh-CN":"请在步骤 1 读取主机身份，并通过服务商控制台或既有可信记录独立核对算法和完整指纹。","en":"In Step 1, read the host identity and independently verify both the algorithm and full fingerprint against the provider console or an existing trusted record."},
    "extensions.host_key_pairing_kicker":{"zh-CN":"当前只做一件事","en":"ONE THING NOW"},
    "extensions.host_key_pairing_title":{"zh-CN":"确认这台服务器","en":"Confirm this server"},
    "extensions.host_key_pairing_help":{"zh-CN":"在你平时用来登录这台服务器的终端中完成确认。GenBox 不会要求你输入密码或私钥。","en":"Complete this in the terminal you normally use for this server. GenBox will not ask for your password or private key."},
    "extensions.host_key_pairing_start":{"zh-CN":"开始确认服务器","en":"Start server confirmation"},
    "extensions.host_key_pairing_help_button":{"zh-CN":"没有已登录终端？","en":"No signed-in terminal?"},
    "extensions.host_key_pairing_help_hide":{"zh-CN":"收起帮助","en":"Hide help"},
    "extensions.host_key_pairing_help_title":{"zh-CN":"没有已登录终端时怎么办","en":"No signed-in terminal?"},
    "extensions.host_key_pairing_help_body":{"zh-CN":"先不要开始确认。请使用服务商控制台、已有的 known_hosts 记录，或向管理员索取可信的服务器公开身份。","en":"Do not start confirmation yet. Use your provider console, an existing known_hosts record, or ask an administrator for a trusted public server identity."},
    "extensions.host_key_pairing_help_safety":{"zh-CN":"打开高级核对只会显示下一步，不会连接服务器，也不会读取或保存密码、私钥。","en":"Opening advanced verification only shows the next step. It does not connect to the server or read or save a password or private key."},
    "extensions.host_key_pairing_open_advanced":{"zh-CN":"打开高级核对","en":"Open advanced verification"},
    "extensions.host_key_pairing_manual":{"zh-CN":"改用手动核对","en":"Use manual verification"},
    "extensions.host_key_pairing_starting":{"zh-CN":"正在准备一次性确认。","en":"Preparing one-time confirmation."},
    "extensions.host_key_pairing_started":{"zh-CN":"复制确认工具到你已信任的终端运行，然后粘贴确认码。","en":"Copy the confirmation tool to your trusted terminal, run it, then paste the confirmation code."},
    "extensions.host_key_pairing_command":{"zh-CN":"第 2 步：复制确认工具到终端","en":"Step 2: Copy the confirmation tool to your terminal"},
    "extensions.host_key_pairing_response":{"zh-CN":"第 3 步：粘贴确认码","en":"Step 3: Paste the confirmation code"},
    "extensions.host_key_pairing_copy":{"zh-CN":"复制","en":"Copy"},
    "extensions.host_key_pairing_copied":{"zh-CN":"已复制。现在粘贴到已信任的终端运行。","en":"Copied. Paste it into your trusted terminal and run it."},
    "extensions.host_key_pairing_copy_manual":{"zh-CN":"复制失败，请选中确认工具后手动复制。","en":"Copy failed. Select the confirmation tool and copy it manually."},
    "extensions.host_key_pairing_response_placeholder":{"zh-CN":"从终端粘贴确认码","en":"Paste the confirmation code from your terminal"},
    "extensions.host_key_pairing_step_start":{"zh-CN":"生成确认码","en":"Generate a confirmation code"},
    "extensions.host_key_pairing_step_start_help":{"zh-CN":"一次确认只在短时间内有效","en":"Each confirmation is valid only briefly"},
    "extensions.host_key_pairing_step_command":{"zh-CN":"复制确认工具并运行","en":"Copy and run the confirmation tool"},
    "extensions.host_key_pairing_step_command_help":{"zh-CN":"只在你已信任的终端运行这一行","en":"Run this line only in a terminal you trust"},
    "extensions.host_key_pairing_step_response":{"zh-CN":"粘贴确认码","en":"Paste the confirmation code"},
    "extensions.host_key_pairing_step_response_help":{"zh-CN":"粘贴后会立即隐藏内容","en":"The content is hidden immediately after pasting"},
    "extensions.host_key_pairing_received":{"zh-CN":"确认码已接收，可以确认这台服务器。","en":"Confirmation code received. You can confirm this server."},
    "extensions.host_key_pairing_clear":{"zh-CN":"重新粘贴","en":"Paste again"},
    "extensions.host_key_pairing_complete":{"zh-CN":"确认这台服务器","en":"Confirm this server"},
    "extensions.host_key_pairing_restart":{"zh-CN":"重新开始","en":"Start over"},
    "extensions.ssh_host_key_mismatch":{"zh-CN":"服务器身份发生变化，已停止 SSH 连接。请重新确认这台服务器；不会自动覆盖原记录。","en":"The server identity changed, so SSH stopped. Confirm this server again; the saved record will not be overwritten automatically."},
    "extensions.identity_reconfirm_credential_title":{"zh-CN":"先确认服务器身份","en":"Confirm the server identity first"},
    "extensions.identity_reconfirm_credential_body":{"zh-CN":"本次 SSH 凭据已清除。完成服务器身份确认后，才需要重新输入密码或私钥。","en":"The SSH credentials for this session were cleared. Enter a password or private key only after confirming the server identity."},
    "extensions.identity_reset_action":{"zh-CN":"清除旧记录并重新确认","en":"Clear the old record and confirm again"},
    "extensions.identity_reset_confirm":{"zh-CN":"这会仅清除本机保存的旧服务器身份记录，并使未完成的确认失效。不会连接服务器、不会保存密码，也不会自动接受新身份。是否继续？","en":"This only clears the locally saved old server identity and invalidates unfinished confirmations. It will not connect to the server, save credentials, or accept a new identity automatically. Continue?"},
    "extensions.identity_reset_complete":{"zh-CN":"旧服务器身份记录已清除。请重新确认这台服务器。","en":"The old server identity record was cleared. Confirm this server again."},
    "extensions.identity_reset_failed":{"zh-CN":"无法重置旧服务器身份记录。请重新载入页面后再试。","en":"The old server identity record could not be reset. Reload the page and try again."},
    "extensions.identity_reset_guide_after":{"zh-CN":"清除后仍需你亲自确认新的服务器身份；不会自动连接或恢复密码。","en":"After clearing it, you still confirm the new server identity yourself; no connection or credential is restored automatically."},
    "extensions.guide_step1_identity_changed":{"zh-CN":"服务器身份与之前记录不一致。","en":"The server identity does not match the previous record."},
    "extensions.guide_step1_reconfirm_action":{"zh-CN":"请重新确认这台服务器。不要继续输入密码。","en":"Confirm this server again before entering a password."},
    "extensions.host_key_pairing_expiry":{"zh-CN":"请尽快完成；配对信息不会保存到浏览器或 VPS 配置。","en":"Complete soon; pairing data is not saved in browser storage or VPS configuration."},
    "extensions.host_key_pairing_expires_in":{"zh-CN":"此验证将在约","en":"This verification expires in about"},
    "extensions.host_key_pairing_submitting":{"zh-CN":"正在提交验证结果，请稍候。","en":"Submitting the verification result. Please wait."},
    "extensions.host_key_pairing_expired":{"zh-CN":"确认已过期，临时信息已清除。请重新开始确认。","en":"The confirmation expired and temporary data was cleared. Start again."},
    "extensions.host_key_pairing_complete_success":{"zh-CN":"这台服务器已确认。现在可以输入 SSH 密码或私钥继续。","en":"This server is confirmed. You can now enter an SSH password or private key to continue."},
    "extensions.host_key_pairing_cancelled":{"zh-CN":"配对已取消，未保存任何身份信息。","en":"Pairing cancelled; no identity information was saved."},
    "extensions.host_key_pairing_cancel_cleanup_pending":{"zh-CN":"页面已清除配对信息；本机清理尚未确认，请稍后重新开始。","en":"Pairing data was cleared from this page, but local cleanup was not confirmed. Start again shortly."},
    "extensions.host_key_pairing_invalid":{"zh-CN":"配对回执无效，请重新开始。","en":"The pairing response was invalid. Start again."},
    "extensions.host_key_title":{"zh-CN":"确认 VPS 的 SSH 主机指纹","en":"Confirm the VPS SSH host key"},
    "extensions.host_key_probe_help":{"zh-CN":"这里只读取服务器公开身份，不验证密码、不执行命令。","en":"This reads only the server public identity. It does not verify a password or run commands."},
    "extensions.host_key_candidate_title":{"zh-CN":"待核对的 SSH 主机身份","en":"Candidate SSH host identity"},
    "extensions.host_key_independent_check":{"zh-CN":"请通过服务商控制台或既有可信记录，独立核对下面的算法和完整指纹。","en":"Independently verify the algorithm and full fingerprint below against the provider console or an existing trusted record."},
    "extensions.host_key_algorithm":{"zh-CN":"算法","en":"Algorithm"},
    "extensions.host_key_fingerprint":{"zh-CN":"完整 SHA-256 指纹","en":"Full SHA-256 fingerprint"},
    "extensions.host_key_confirmation_scope":{"zh-CN":"确认只保存服务器公开身份，不代表 SSH 认证、部署或网络连接已经完成。","en":"Confirmation saves only the server public identity; it does not mean SSH authentication, deployment, or networking is complete."},
    "extensions.confirm_host_key_pair":{"zh-CN":"算法和指纹均已独立核对","en":"I independently verified both values"},
    "extensions.read_again":{"zh-CN":"重新读取","en":"Read again"},
    "extensions.host_key_return_title":{"zh-CN":"请先完成步骤 1 的主机身份确认","en":"Complete host identity confirmation in Step 1"},
    "extensions.host_key_return_help":{"zh-CN":"请返回步骤 1，独立核对算法和完整指纹；步骤 2 部署与步骤 3 本机网络准备仍需按顺序完成。","en":"Return to Step 1 and independently verify the algorithm and full fingerprint. Step 2 deployment and Step 3 local network setup still remain in order."},
    "extensions.return_step1_host_key":{"zh-CN":"返回步骤 1 核对主机身份","en":"Return to Step 1"},
    "extensions.read_host_key":{"zh-CN":"读取主机指纹","en":"Read host key"},
    "extensions.confirm_host_key":{"zh-CN":"我已核对并确认","en":"I reviewed and confirm"},
    "extensions.host_key_not_read":{"zh-CN":"尚未读取主机指纹","en":"Host key not read yet"},
    "extensions.reading_host_key":{"zh-CN":"正在读取 VPS 的公开 SSH 主机指纹，不会提交密码。","en":"Reading the public SSH host key without sending a password."},
    "extensions.host_key_invalid_response":{"zh-CN":"VPS 没有返回受支持的主机密钥算法和规范 SHA-256 指纹。","en":"The VPS did not return a supported host-key algorithm and canonical SHA-256 fingerprint."},
    "extensions.host_key_review":{"zh-CN":"候选主机身份已留在步骤 1。请独立核对算法和完整指纹；确认不代表 SSH 认证、部署或网络完成。","en":"The candidate host identity remains in Step 1. Independently verify the algorithm and full fingerprint; confirmation does not complete SSH authentication, deployment, or networking."},
    "extensions.host_key_confirmed":{"zh-CN":"SSH 主机指纹已独立确认并保存。现在可以开始检测私网链路。","en":"The SSH host key was confirmed and saved independently. You can now check the private link."},
    "extensions.host_key_confirmed_for_deploy":{"zh-CN":"SSH 主机指纹已保存。现在请测试 SSH 与部署权限。","en":"The SSH host key was saved. Now test SSH and deployment access."},
    "extensions.host_key_confirm_in_network":{"zh-CN":"请返回步骤 1，独立核对主机密钥算法和完整指纹。","en":"Return to Step 1 and independently verify the host-key algorithm and full fingerprint."},
    "extensions.deployment_target_mismatch":{"zh-CN":"该服务部署在另一台 VPS，请选择对应的服务器后继续。","en":"This service is deployed on another VPS. Select its server before continuing."},
    "extensions.host_key_required_here":{"zh-CN":"开始私网检测前，请返回步骤 1 完成主机身份确认。","en":"Before checking the private link, return to Step 1 and complete host identity confirmation."},
    "extensions.discovery_failed_prefix":{"zh-CN":"环境检测失败：","en":"Environment discovery failed: "},
    "extensions.confirm_fingerprint_first":{"zh-CN":"请先确认 SSH 主机指纹。","en":"Confirm the SSH host fingerprint first."},
    "extensions.source_container":{"zh-CN":"源容器","en":"Source container"},
    "extensions.container_id":{"zh-CN":"容器 ID","en":"Container ID"},
    "extensions.status":{"zh-CN":"状态","en":"Status"},
    "extensions.source_image":{"zh-CN":"源镜像","en":"Source image"},
    "extensions.compose_project":{"zh-CN":"Compose 项目","en":"Compose project"},
    "extensions.source_data_dir":{"zh-CN":"源数据目录","en":"Source data directory"},
    "extensions.source_config":{"zh-CN":"源配置文件","en":"Source configuration"},
    "extensions.source_data_size":{"zh-CN":"源数据大小","en":"Source data size"},
    "extensions.target_instance_port":{"zh-CN":"目标实例/端口","en":"Target instance/port"},
    "extensions.readonly_baseline_html":{"zh-CN":"<b>执行前只读基线</b><ul>","en":"<b>Read-only preflight baseline</b><ul>"},
    "extensions.operations_html":{"zh-CN":"<b>即将执行</b><ul>","en":"<b>Planned operations</b><ul>"},
    "extensions.safety_html":{"zh-CN":"</ul><b>安全保证</b><ul>","en":"</ul><b>Safety guarantees</b><ul>"},
    "extensions.copy_estimate_html":{"zh-CN":"<b>预计复制数据</b><p>","en":"<b>Estimated data copy</b><p>"},
    "extensions.copy_estimate_suffix":{"zh-CN":" MB；源实例保持在线且只读。</p>","en":" MB; the source instance stays online and read-only.</p>"},
    "extensions.plan_ready":{"zh-CN":"安全计划已生成，10 分钟内确认有效。","en":"Safety plan generated and valid for 10 minutes."},
    "extensions.plan_failed_prefix":{"zh-CN":"无法生成计划：","en":"Could not generate plan: "},
    "extensions.image_source_help":{"zh-CN":"请填写隔离开发机能拉取的不可变镜像地址。本机 Docker 标签和 latest 不能直接部署。","en":"Enter an immutable image address the isolated development machine can pull. Local Docker tags and latest cannot be deployed."},
    "extensions.image_source_required":{"zh-CN":"请先准备可部署镜像：填写可由隔离开发机访问的 registry/name@sha256:<64 位摘要>。本机构建的镜像需要先通过可复现的交付流程提供给服务器。","en":"Prepare a deployable image first: enter registry/name@sha256:<64 hex digest> that the isolated development machine can access. A locally built image needs a reproducible delivery path before deployment."},
    "extensions.image_source_mode":{"zh-CN":"镜像方案","en":"Image option"},
    "extensions.image_source_select_help":{"zh-CN":"只有选择“自定义不可变镜像”后，才可以手动填写摘要。","en":"Manual digest entry is available only for the custom immutable image option."},
    "extensions.image_preset_project":{"zh-CN":"GenBox 集成构建镜像（推荐）","en":"GenBox integration build (recommended)"},
    "extensions.image_preset_project_hint":{"zh-CN":"当前项目维护，已包含 GenBox Push 联动代码；优先使用。","en":"Maintained by this project with GenBox Push integration; preferred."},
    "extensions.image_preset_project_status":{"zh-CN":"已选择 GenBox 集成构建镜像。","en":"GenBox integration build selected."},
    "extensions.image_preset_upstream":{"zh-CN":"yukkcat 镜像（未集成 GenBox）","en":"yukkcat image (no GenBox integration)"},
    "extensions.image_preset_upstream_hint":{"zh-CN":"yukkcat/chatgpt2api 上游镜像不包含 GenBox Push 联动；是否继续部署由你决定。","en":"The yukkcat/chatgpt2api upstream image has no GenBox Push integration; you decide whether to deploy it."},
    "extensions.image_preset_upstream_status":{"zh-CN":"该 yukkcat 镜像未集成 GenBox Push；你仍可继续部署，但不会自动联动。","en":"This yukkcat image has no GenBox Push integration. You may continue deployment, but it will not link to GenBox automatically."},
    "extensions.image_preset_custom":{"zh-CN":"自定义不可变镜像","en":"Custom immutable image"},
    "extensions.image_preset_custom_hint":{"zh-CN":"适用于你已核验的其他不可变镜像摘要。","en":"Use another immutable image digest that you have verified."},
    "extensions.image_preset_custom_status":{"zh-CN":"请输入可由隔离开发机拉取的不可变镜像摘要。","en":"Enter an immutable image digest the isolated development machine can pull."},
    "extensions.image_custom_placeholder":{"zh-CN":"registry/name@sha256:64 位摘要","en":"registry/name@sha256:64-hex-digest"},
    "extensions.image_check_action":{"zh-CN":"检查 GenBox 联动","en":"Check GenBox integration"},
    "extensions.image_check_idle":{"zh-CN":"未检查。此操作不会拉取、启动或部署镜像。","en":"Not checked. This does not pull, start, or deploy the image."},
    "extensions.image_check_running":{"zh-CN":"正在核对本地集成目录，不会连接 VPS。","en":"Checking the local integration catalog; no VPS connection is made."},
    "extensions.image_check_integrated":{"zh-CN":"已确认：该已登记镜像包含 GenBox Push v1 联动。","en":"Confirmed: this registered image includes GenBox Push v1 integration."},
    "extensions.image_check_unknown":{"zh-CN":"无法确认：该自定义镜像不在本地集成目录。不会拉取或运行它；请仅部署已核验的镜像。","en":"Cannot confirm: this custom image is not in the local integration catalog. It was not pulled or run; deploy only an image you have verified."},
    "extensions.image_check_not_integrated":{"zh-CN":"已确认：这是 yukkcat 上游镜像，但未集成 GenBox Push。是否继续部署由你决定。","en":"Confirmed: this is the yukkcat upstream image, but it has no GenBox Push integration. You decide whether to continue."},
    "extensions.image_check_invalid":{"zh-CN":"请先填写不可变镜像摘要，再检查 GenBox 联动。","en":"Enter an immutable image digest before checking GenBox integration."},
    "extensions.image_check_failed":{"zh-CN":"镜像联动检查暂时不可用。请检查摘要后重试。","en":"Image integration check is unavailable. Verify the digest and try again."},
    "extensions.connected_existing":{"zh-CN":"已接入","en":"Connected"},
    "extensions.delivery_failed_prefix":{"zh-CN":"实例已部署，但一次性密钥交付失败：","en":"Instance deployed, but one-time key delivery failed: "},
    "extensions.existing_key_placeholder":{"zh-CN":"请输入该实例现有管理密钥","en":"Enter the existing management key for this instance"},
    "extensions.deploy_complete":{"zh-CN":"chatgpt2api 部署完成。请先保存一次性管理密钥，再配置主链路。","en":"chatgpt2api deployment completed. Save the one-time management key before configuring the primary network."},
    "extensions.registration_complete":{"zh-CN":"已有实例已登记，未执行任何远程变更。","en":"Existing instance registered with no remote changes."},
    "extensions.deploy_failed":{"zh-CN":"部署失败","en":"Deployment failed"},
    "extensions.plan_required":{"zh-CN":"请先生成并检查安全计划。","en":"Generate and review the safety plan first."},
    "extensions.creating_task":{"zh-CN":"正在创建部署任务…","en":"Creating deployment task…"},
    "status.completed":{"zh-CN":"已完成","en":"Completed"},
    "status.needs_attention":{"zh-CN":"需要处理","en":"Needs attention"},
    "status.processing":{"zh-CN":"正在处理","en":"Processing"},
    "status.pending":{"zh-CN":"等待","en":"Waiting"},
    "status.running":{"zh-CN":"进行中","en":"In progress"},
    "status.failed":{"zh-CN":"失败","en":"Failed"},
    "extensions.processing_note":{"zh-CN":"GenBox 正在自动处理，请不要关闭页面。","en":"GenBox is processing automatically. Keep this page open."},
    "extensions.network_connected":{"zh-CN":"链路已连接","en":"Network connected"},
    "extensions.connected":{"zh-CN":"已连接","en":"Connected"},
    "extensions.network_saved":{"zh-CN":"VPS 已能通过私网访问 GenBox，结果已保存。","en":"The VPS can access GenBox over the private network. The result was saved."},
    "extensions.reachable_prefix":{"zh-CN":"已连通 ","en":"Reachable "},
    "extensions.not_reachable":{"zh-CN":"未连通","en":"Not reachable"},
    "extensions.vps_can_access":{"zh-CN":"VPS 可访问","en":"VPS can access"},
    "extensions.cannot_access":{"zh-CN":"不可访问","en":"Not accessible"},
    "extensions.not_generated":{"zh-CN":"未生成","en":"Not generated"},
    "extensions.network_complete":{"zh-CN":"网络连接和检查都已完成。","en":"Network connection and checks completed."},
    "extensions.connection_failed":{"zh-CN":"连接失败","en":"Connection failed"},
    "extensions.network_not_ready":{"zh-CN":"尚未完成端到端验证，暂不可用","en":"Not ready: end-to-end verification is incomplete."},
    "extensions.failed_phase_prefix":{"zh-CN":"失败阶段：","en":"Failed phase: "},
    "extensions.retry_credential_help":{"zh-CN":"不用新的 Tailscale Key。请回到第 1 步重新输入 SSH 密码或私钥，然后再点“重新检查链路”。","en":"No new Tailscale Key is needed. Return to step 1, re-enter the SSH password or private key, then select Recheck network."},
    "extensions.recheck_connection":{"zh-CN":"重新检测连接","en":"Recheck connection"},
    "extensions.recheck_help":{"zh-CN":"脚本会自动检查 VPS 是否在线、两台设备是否互通，以及 VPS 能否访问 GenBox。","en":"The workflow checks whether the VPS is online, whether both devices can reach each other, and whether the VPS can access GenBox."},
    "extensions.auto_connect_help":{"zh-CN":"使用一次性 Auth Key 将 VPS 加入私有网络。授权信息不会写入浏览器存储或任务日志。","en":"Join the VPS to the private network with a one-time Auth Key. Authorization data is not written to browser storage or task logs."},
    "extensions.existing_mode_help":{"zh-CN":"不会重复安装，也不需要新的 Auth Key，只检查现有连接。","en":"Does not reinstall and needs no new Auth Key. Only the existing connection is checked."},
    "extensions.valid_token_required":{"zh-CN":"请输入有效的一次性授权信息。","en":"Enter valid one-time authorization data."},
    "extensions.waiting_login":{"zh-CN":"等待登录","en":"Waiting for sign-in"},
    "extensions.tool_connected":{"zh-CN":"网络工具已连接。","en":"Network tool connected."},
    "extensions.login_same_tailnet":{"zh-CN":"安装后登录与 VPS 相同的 Tailnet。","en":"After installation, sign in to the same Tailnet as the VPS."},
    "extensions.enabled_prefix":{"zh-CN":"已启用：","en":"Enabled: "},
    "extensions.planned_prefix":{"zh-CN":"计划使用：","en":"Planned: "},
    "extensions.private_entry_enabled":{"zh-CN":"私网入口已启用","en":"Private entry enabled"},
    "extensions.enable_entry_next":{"zh-CN":"下一步：启用私网入口","en":"Next: enable the private entry"},
    "extensions.install_first":{"zh-CN":"请先安装","en":"Install first"},
    "extensions.login_first":{"zh-CN":"请先登录","en":"Sign in first"},
    "extensions.local_check_failed":{"zh-CN":"本机检测失败：","en":"Local check failed: "},
    "extensions.installing_tailscale":{"zh-CN":"正在安装 Tailscale，Windows 可能请求权限确认。","en":"Installing Tailscale. Windows may ask for permission."},
    "extensions.tailscale_installed":{"zh-CN":"Tailscale 安装完成，请登录 Tailnet。","en":"Tailscale installed. Sign in to the Tailnet."},
    "extensions.install_failed":{"zh-CN":"安装失败","en":"Installation failed"},
    "extensions.tailnet_signed_in":{"zh-CN":"本机已登录 Tailnet。","en":"This computer is signed in to the Tailnet."},
    "extensions.finish_login":{"zh-CN":"请在 Tailscale 窗口或浏览器完成登录，然后点击重新检测。","en":"Finish signing in through Tailscale or the browser, then select Detect again."},
    "extensions.private_entry_url_prefix":{"zh-CN":"GenBox 私网入口已启用：","en":"Private GenBox entry enabled: "},
    "extensions.no_managed_instance":{"zh-CN":"没有可重置的托管实例。","en":"No managed instance is available to reset."},
    "extensions.reset_needs_owner":{"zh-CN":"重置需要重新验证 VPS 所有权。请返回第一步重新输入 SSH 凭据后再操作。","en":"Resetting requires VPS ownership verification. Return to step 1 and re-enter SSH credentials."},
    "extensions.reset_confirm_prefix":{"zh-CN":"为实例 ","en":"Generate a new management key for instance "},
    "extensions.reset_confirm_suffix":{"zh-CN":" 生成新管理密钥？旧主管理密钥将立即失效。","en":"? The old management key will be invalidated immediately."},
    "extensions.reset_success_page":{"zh-CN":"管理密钥已重置并验证。新密钥仅在本页显示。","en":"Management key reset and verified. The new key is shown only on this page."},
    "sync.instructions_html":{"zh-CN":"<div class=\"sync-empty\">按上方 3 步操作：<br>① 在「远程部署」处保存 chatgpt2api 部署<br>② 在下方选择该部署并点「扫描预览」<br>③ 预览图出现后勾选图片，再点「同步选中」</div>","en":"<div class=\"sync-empty\">Follow the three steps above:<br>① Save a chatgpt2api deployment under Remote deployments<br>② Choose it below and select Scan preview<br>③ Select images after previews appear, then select Sync selected</div>"},
    "sync.no_deployment_html":{"zh-CN":"<div class=\"sync-empty\">尚未配置远程部署。</div>","en":"<div class=\"sync-empty\">No remote deployment configured.</div>"},
    "sync.load_failed_html":{"zh-CN":"<div class=\"sync-empty\">部署加载失败</div>","en":"<div class=\"sync-empty\">Deployment loading failed</div>"},
    "common.load_failed_prefix":{"zh-CN":"加载失败: ","en":"Load failed: "},
    "sync.url_required":{"zh-CN":"请填写 Base URL","en":"Enter a Base URL"},
    "sync.saving":{"zh-CN":"正在保存…","en":"Saving…"},
    "sync.saved":{"zh-CN":"保存成功，可测试连接或扫描预览。","en":"Saved. You can test the connection or scan previews."},
    "common.save_failed_colon":{"zh-CN":"保存失败: ","en":"Save failed: "},
    "sync.delete_confirm":{"zh-CN":"确认删除该远程部署？","en":"Delete this remote deployment?"},
    "common.delete_failed_colon":{"zh-CN":"删除失败: ","en":"Delete failed: "},
    "common.test":{"zh-CN":"测试","en":"Test"},
    "sync.testing":{"zh-CN":"测试中…","en":"Testing…"},
    "sync.connection_success":{"zh-CN":"连接成功\\n版本: ","en":"Connected\\nVersion: "},
    "sync.unknown":{"zh-CN":"未知","en":"Unknown"},
    "sync.role_prefix":{"zh-CN":"\\n角色: ","en":"\\nRole: "},
    "sync.connection_failed_prefix":{"zh-CN":"连接失败: ","en":"Connection failed: "},
    "sync.unknown_error":{"zh-CN":"未知错误","en":"Unknown error"},
    "sync.test_error_prefix":{"zh-CN":"测试出错: ","en":"Test error: "},
    "sync.choose_first_html":{"zh-CN":"<div class=\"sync-empty\">请先选择一个远程部署。</div>","en":"<div class=\"sync-empty\">Choose a remote deployment first.</div>"},
    "sync.loading_remote_html":{"zh-CN":"<div class=\"sync-empty\">正在拉取远端图片并去重，请稍候…</div>","en":"<div class=\"sync-empty\">Loading and deduplicating remote images…</div>"},
    "sync.preview_failed_html":{"zh-CN":"<div class=\"sync-empty\">预览失败: ","en":"<div class=\"sync-empty\">Preview failed: "},
    "sync.no_new_html":{"zh-CN":"<div class=\"sync-empty\">没有需要同步的新图片（已同步或与本地重复均已排除）。</div>","en":"<div class=\"sync-empty\">No new images to sync. Previously synced and local duplicates were excluded.</div>"},
    "sync.local_duplicate_html":{"zh-CN":"<span class=\"sync-badge dup\">本地重复</span>","en":"<span class=\"sync-badge dup\">Local duplicate</span>"},
    "sync.error_html":{"zh-CN":"<span class=\"sync-badge err\">错误</span>","en":"<span class=\"sync-badge err\">Error</span>"},
    "sync.synced_html":{"zh-CN":"<span class=\"sync-badge ok\">已同步</span>","en":"<span class=\"sync-badge ok\">Synced</span>"},
    "sync.image":{"zh-CN":"图片","en":"Image"},
    "sync.remote_image":{"zh-CN":"远端图片","en":"Remote image"},
    "sync.no_image_html":{"zh-CN":"<div class=\"sync-thumb sync-thumb-empty\">无图</div>","en":"<div class=\"sync-thumb sync-thumb-empty\">No image</div>"},
    "sync.selected_prefix":{"zh-CN":"已选 ","en":"Selected "},
    "sync.start_failed_prefix":{"zh-CN":"同步启动失败: ","en":"Sync start failed: "},
    "sync.processed_prefix":{"zh-CN":"已处理 ","en":"Processed "},
    "sync.error_count_prefix":{"zh-CN":"（错误 ","en":" (errors "},
    "sync.complete":{"zh-CN":"同步完成 ✓ 已导入到媒体库","en":"Sync complete ✓ Imported into Media Library"},
    "task.deploy.connect":{"zh-CN":"连接 VPS","en":"Connect to VPS"},
    "task.deploy.docker":{"zh-CN":"检查 Docker","en":"Check Docker"},
    "task.deploy.prepare":{"zh-CN":"创建部署目录","en":"Create deployment directory"},
    "task.deploy.pull":{"zh-CN":"拉取 chatgpt2api 镜像","en":"Pull chatgpt2api image"},
    "task.deploy.start":{"zh-CN":"启动服务","en":"Start service"},
    "task.deploy.verify":{"zh-CN":"等待服务就绪","en":"Wait for service readiness"},
    "task.network.local_detect":{"zh-CN":"检查这台电脑","en":"Check this computer"},
    "task.network.remote_connect":{"zh-CN":"连接远程 VPS","en":"Connect to remote VPS"},
    "task.network.remote_detect":{"zh-CN":"检查 VPS 环境","en":"Check VPS environment"},
    "task.network.remote_install":{"zh-CN":"安装网络工具","en":"Install network tool"},
    "task.network.remote_enroll":{"zh-CN":"加入同一个网络","en":"Join the same network"},
    "task.network.remote_network_detect":{"zh-CN":"确认 VPS Tailscale 地址","en":"Confirm VPS Tailscale address"},
    "task.network.peer_verify":{"zh-CN":"检查两台设备互通","en":"Check peer connectivity"},
    "task.network.http_probe":{"zh-CN":"检查 VPS 能否访问 GenBox","en":"Check VPS access to GenBox"},
    "task.network.destination_ready":{"zh-CN":"保存可用访问地址","en":"Save reachable URL"},
    "status.cancelled":{"zh-CN":"已取消","en":"Cancelled"},
    "sync.zoom_title":{"zh-CN":"点击放大","en":"Click to enlarge"},
    "sync.zoom_aria_prefix":{"zh-CN":"放大预览 ","en":"Enlarge preview "},
    "prompt.category_style":{"zh-CN":"🎬 风格","en":"🎬 Style"},
    "prompt.cinematic":{"zh-CN":"电影感画面","en":"Cinematic scene"},
    "prompt.cyberpunk":{"zh-CN":"赛博朋克城市","en":"Cyberpunk city"},
    "prompt.product":{"zh-CN":"商业产品摄影","en":"Commercial product photography"},
    "prompt.oil":{"zh-CN":"油画风格","en":"Oil painting"},
    "prompt.watercolor":{"zh-CN":"水彩插画","en":"Watercolor illustration"},
    "prompt.anime":{"zh-CN":"动漫风格","en":"Anime style"},
    "prompt.pixel":{"zh-CN":"像素艺术","en":"Pixel art"},
    "prompt.lowpoly":{"zh-CN":"低多边形3D","en":"Low-poly 3D"},
    "prompt.category_ancient":{"zh-CN":"👘 古风","en":"👘 Historical"},
    "prompt.xianxia":{"zh-CN":"仙侠古风","en":"Xianxia fantasy"},
    "prompt.tang":{"zh-CN":"大唐宫廷","en":"Tang dynasty court"},
    "prompt.ink_landscape":{"zh-CN":"水墨山水","en":"Ink-wash landscape"},
    "prompt.qing":{"zh-CN":"清朝宫廷","en":"Qing dynasty court"},
    "prompt.warrior":{"zh-CN":"古风战士","en":"Historical warrior"},
    "prompt.category_nature":{"zh-CN":"🌿 自然","en":"🌿 Nature"},
    "prompt.sunrise":{"zh-CN":"日出山景","en":"Mountain sunrise"},
    "prompt.beach":{"zh-CN":"热带海滩日落","en":"Tropical beach sunset"},
    "prompt.cherry":{"zh-CN":"樱花满开","en":"Cherry blossoms in full bloom"},
    "prompt.aurora":{"zh-CN":"极光雪山","en":"Aurora over snowy mountains"},
    "prompt.autumn":{"zh-CN":"秋日森林","en":"Autumn forest"},
    "prompt.category_architecture":{"zh-CN":"🏙 建筑","en":"🏙 Architecture"},
    "prompt.future_city":{"zh-CN":"未来城市","en":"Future city"},
    "prompt.castle":{"zh-CN":"中世纪城堡","en":"Medieval castle"},
    "prompt.minimal_architecture":{"zh-CN":"现代极简建筑","en":"Modern minimalist architecture"},
    "prompt.ruins":{"zh-CN":"古代遗迹","en":"Ancient ruins"},
    "prompt.night_market":{"zh-CN":"夜市街景","en":"Night market street"},
    "prompt.category_portrait":{"zh-CN":"🎭 人像","en":"🎭 Portrait"},
    "prompt.pro_portrait":{"zh-CN":"专业人像摄影","en":"Professional portrait photography"},
    "prompt.fashion":{"zh-CN":"时尚大片","en":"Fashion editorial"},
    "prompt.street":{"zh-CN":"街拍风格","en":"Street photography"},
    "prompt.film":{"zh-CN":"复古胶片","en":"Vintage film"},
    "prompt.face_closeup":{"zh-CN":"精致五官特写","en":"Detailed facial close-up"},
    "prompt.category_scifi":{"zh-CN":"🚀 科幻","en":"🚀 Sci-fi"},
    "prompt.cockpit":{"zh-CN":"飞船驾驶舱","en":"Spacecraft cockpit"},
    "prompt.android":{"zh-CN":"仿生人","en":"Android"},
    "prompt.alien":{"zh-CN":"外星地表","en":"Alien landscape"},
    "prompt.space_station":{"zh-CN":"深空站","en":"Deep-space station"},
    "prompt.retro_future":{"zh-CN":"复古未来主义","en":"Retrofuturism"},
    "dock.collapse":{"zh-CN":"收起底部导航","en":"Collapse bottom navigation"},
    "creator.global":{"zh-CN":"全局","en":"Global"},
    "creator.global_all":{"zh-CN":"🌐 全局（对所有模型生效）","en":"🌐 Global (applies to all models)"},
    "creator.saved_prefix":{"zh-CN":"✅ 已保存「","en":"✅ Saved image settings for “"},
    "creator.saved_suffix":{"zh-CN":"」的图像设置","en":"”"},
    "common.save_failed":{"zh-CN":"❌ 保存失败","en":"❌ Save failed"},
    "provider.loaded_prefix":{"zh-CN":"Provider 已加载 · ","en":"Providers loaded · "},
    "provider.image_count":{"zh-CN":" 个生图模型","en":" image models"},
    "provider.load_failed":{"zh-CN":"Provider 加载失败","en":"Provider loading failed"},
    "provider.no_models_html":{"zh-CN":"<option value=\"\">无可用模型</option>","en":"<option value=\"\">No models available</option>"},
    "provider.no_models_add_html":{"zh-CN":"<div style=\"color:var(--text-muted);font-size:12px;padding:8px 0;\">暂无模型，<a href=\"#\" onclick=\"openProviderModal();return false;\" style=\"color:var(--accent);\">去添加</a></div>","en":"<div style=\"color:var(--text-muted);font-size:12px;padding:8px 0;\">No models. <a href=\"#\" onclick=\"openProviderModal();return false;\" style=\"color:var(--accent);\">Add one</a></div>"},
    "provider.settings_saved":{"zh-CN":"✅ 模型设置已保存","en":"✅ Model settings saved"},
    "upload.image_required":{"zh-CN":"请选择图片文件","en":"Choose an image file"},
    "upload.image_too_large":{"zh-CN":"图片不能超过 10MB","en":"Image must be 10 MB or smaller"},
    "ratio.landscape":{"zh-CN":"横屏","en":"Landscape"},
    "ratio.widescreen":{"zh-CN":"宽屏","en":"Widescreen"},
    "ratio.cinematic":{"zh-CN":"电影感","en":"Cinematic"},
    "ratio.panorama":{"zh-CN":"全景","en":"Panorama"},
    "ratio.portrait":{"zh-CN":"竖屏","en":"Portrait"},
    "ratio.poster":{"zh-CN":"海报","en":"Poster"},
    "ratio.person":{"zh-CN":"人像","en":"Portrait"},
    "ratio.avatar":{"zh-CN":"头像","en":"Avatar"},
    "ratio.closeup":{"zh-CN":"特写","en":"Close-up"},
    "status.failure_suffix_html":{"zh-CN":" 失败</span>","en":" failed</span>"},
    "status.done":{"zh-CN":"完成","en":"Done"},
    "status.generating":{"zh-CN":"生成中","en":"Generating"},
    "status.failed_plain":{"zh-CN":"失败","en":"Failed"},
    "status.queued":{"zh-CN":"排队","en":"Queued"},
    "status.queuing":{"zh-CN":"排队中","en":"Queued"},
    "status.queuing_dots":{"zh-CN":"排队中...","en":"Queued..."},
    "status.failed_icon":{"zh-CN":"✗ 失败","en":"✗ Failed"},
    "status.queued_html":{"zh-CN":"\">排队中</span>","en":"\">Queued</span>"},
    "result.success_count":{"zh-CN":" 张成功","en":" succeeded"},
    "result.failure_html":{"zh-CN":"<div style=\"font-size:20px;\">⚠</div><div class=\"ph-text\" style=\"color:#ef4444;\">失败</div>","en":"<div style=\"font-size:20px;\">⚠</div><div class=\"ph-text\" style=\"color:#ef4444;\">Failed</div>"},
    "result.retry":{"zh-CN":"🔄 重试","en":"🔄 Retry"},
    "result.retry_one":{"zh-CN":"仅重试此模型","en":"Retry this model only"},
    "result.retry_missing":{"zh-CN":"没有可重试的上下文，请重新生成","en":"No retry context is available. Generate again."},
    "result.retry_prefix":{"zh-CN":"仅重试「","en":"Retry only “"},
    "result.retrying":{"zh-CN":"🔄 重试中...","en":"🔄 Retrying..."},
    "result.retry_submitted":{"zh-CN":"重试已提交: ","en":"Retry submitted: "},
    "result.retry_failed":{"zh-CN":"重试失败: ","en":"Retry failed: "},
    "creator.generate_image_sparkle":{"zh-CN":"✨ 生成图片","en":"✨ Generate image"},
    "status.generating_prefix":{"zh-CN":" 生成中... (","en":" generating... ("},
    "status.complete_paren":{"zh-CN":" 完成)","en":" complete)"},
    "status.queued_prefix":{"zh-CN":"排队中... (","en":"Queued... ("},
    "result.complete_prefix":{"zh-CN":"生成完成! ","en":"Generation complete! "},
    "result.success_suffix":{"zh-CN":" 成功","en":" succeeded"},
    "result.complete_middle":{"zh-CN":"生成完成 · ","en":"Generation complete · "},
    "result.success_middle":{"zh-CN":" 成功 · ","en":" succeeded · "},
    "creator.reference_or_prompt":{"zh-CN":"请上传参考图片或输入修改提示词","en":"Upload a reference image or enter an edit prompt"},
    "creator.reference_required":{"zh-CN":"请先上传参考图片","en":"Upload a reference image first"},
    "creator.prompt_required":{"zh-CN":"请输入提示词","en":"Enter a prompt"},
    "creator.model_required":{"zh-CN":"请至少选择一个模型","en":"Choose at least one model"},
    "status.submitting_html":{"zh-CN":"<span class=\"spin\" style=\"display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;vertical-align:middle;margin-right:4px;\"></span>提交中...","en":"<span class=\"spin\" style=\"display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;vertical-align:middle;margin-right:4px;\"></span>Submitting..."},
    "status.submitting":{"zh-CN":"正在提交...","en":"Submitting..."},
    "status.task_queued":{"zh-CN":"任务已提交，队列处理中...","en":"Task submitted and queued..."},
    "status.submit_failed":{"zh-CN":"提交失败: ","en":"Submission failed: "},
    "creator.source_required":{"zh-CN":"请先上传源图片","en":"Upload a source image first"},
    "creator.image_model_required":{"zh-CN":"请至少选择一个生图模型","en":"Choose at least one image model"},
    "variation.generating":{"zh-CN":"正在生成变形...","en":"Generating variation..."},
    "variation.complete_prefix":{"zh-CN":"变形完成！共 ","en":"Variation complete! "},
    "result.image_count_suffix":{"zh-CN":" 张","en":" images"},
    "variation.variant":{"zh-CN":"变形变体","en":"Variation"},
    "variation.complete":{"zh-CN":"变形完成","en":"Variation complete"},
    "variation.failed":{"zh-CN":"变形失败: ","en":"Variation failed: "},
    "common.copied_clipboard":{"zh-CN":"已复制到剪贴板","en":"Copied to clipboard"},
    "result.failed_count":{"zh-CN":" 张失败","en":" failed"},
    "lightbox.prompt_copied":{"zh-CN":"已复制提示词到剪贴板","en":"Prompt copied to clipboard"},
    "image.unavailable":{"zh-CN":"无法获取图片","en":"Could not retrieve image"},
    "image.data_failed":{"zh-CN":"获取图片数据失败","en":"Could not load image data"},
    "image.sent_i2i":{"zh-CN":"已发送到图生图模式","en":"Sent to image-to-image"},
    "image.load_failed":{"zh-CN":"加载图片失败: ","en":"Image loading failed: "},
    "image.sent_i2v":{"zh-CN":"已发送到图生视频模式","en":"Sent to image-to-video"},
    "image.load_failed_compact":{"zh-CN":"加载图片失败:","en":"Image loading failed: "},
    "compare.need_two":{"zh-CN":"至少需要 2 个成功结果才能对比","en":"At least two successful results are required for comparison"},
    "provider.all_option_html":{"zh-CN":"<option value=\"\">所有 Provider</option>","en":"<option value=\"\">All Providers</option>"},
    "library.cloud_badge_html":{"zh-CN":"<div class=\"gallery-cloud-badge\" title=\"从云端同步\">☁ 云端</div>","en":"<div class=\"gallery-cloud-badge\" title=\"Synced from cloud\">☁ Cloud</div>"},
    "video.unnamed":{"zh-CN":"未命名视频","en":"Untitled video"},
    "video.cannot_play":{"zh-CN":"无法播放视频","en":"Could not play video"},
    "video.download":{"zh-CN":"⬇ 下载视频","en":"⬇ Download video"},
    "video.prompt_lightbox":{"zh-CN":"📝 生视频提示词","en":"📝 Video prompt"},
    "image.open_missing":{"zh-CN":"无法打开图片：未找到数据","en":"Could not open image: data not found"},
    "image.open_invalid":{"zh-CN":"无法打开图片：路径无效","en":"Could not open image: invalid path"}
   ,"proxy.disabled":{"zh-CN":"已禁用","en":"Disabled"},
    "proxy.saved":{"zh-CN":"✅ 代理配置已保存","en":"? Proxy configuration saved"},
    "proxy.testing":{"zh-CN":"⏳ 测试中...","en":"? Testing..."},
    "proxy.testing_status":{"zh-CN":"正在测试代理连通性...","en":"Testing proxy connectivity..."},
    "proxy.partial_failure":{"zh-CN":"⚠ 部分可达","en":"? Partially reachable"},
    "proxy.ok":{"zh-CN":"✅ 代理连通正常","en":"? Proxy connectivity is healthy"},
    "proxy.test_failed_prefix":{"zh-CN":"测试失败: ","en":"Test failed: "},
    "update.type_source":{"zh-CN":"源码","en":"Source"},
    "update.type_exe":{"zh-CN":"可执行文件","en":"Executable"},
    "update.current_prefix":{"zh-CN":"当前: ","en":"Current: "},
    "update.info_unavailable":{"zh-CN":"无法加载更新信息","en":"Could not load update info"},
    "update.checking_short":{"zh-CN":"检查中...","en":"Checking..."},
    "update.checking_progress":{"zh-CN":"正在检查更新...","en":"Checking for updates..."},
    "update.available_badge":{"zh-CN":"可更新","en":"Update available"},
    "update.available_suffix":{"zh-CN":"可用","en":"available"},
    "update.speed_test":{"zh-CN":"测速","en":"Test speed"},
    "update.up_to_date_badge":{"zh-CN":"已是最新","en":"Up to date"},
    "update.up_to_date":{"zh-CN":"当前已是最新版本","en":"Already up to date"},
    "update.recheck":{"zh-CN":"重新检查","en":"Check again"},
    "update.check_failed_badge":{"zh-CN":"检查失败","en":"Check failed"},
    "update.check_failed_prefix":{"zh-CN":"检查失败: ","en":"Check failed: "},
    "update.testing_mirrors":{"zh-CN":"正在测试 GitHub 镜像线路...","en":"Testing GitHub mirror routes..."},
    "update.mirror_results":{"zh-CN":"GitHub 镜像测速","en":"GitHub mirror speed test"},
    "update.unavailable":{"zh-CN":"不可用","en":"Unavailable"},
    "update.use_mirror":{"zh-CN":"使用此线路更新","en":"Update with this route"},
    "update.speed_test_failed_prefix":{"zh-CN":"测速失败: ","en":"Speed test failed: "},
    "update.auto_check_off":{"zh-CN":"自动检查已关闭","en":"Automatic checking is off"},
    "update.check_failed":{"zh-CN":"更新检查失败","en":"Update check failed"},
    "update.ignored_suffix":{"zh-CN":"已忽略","en":"ignored"},
    "update.service_unavailable":{"zh-CN":"更新服务暂时不可用","en":"Update service is temporarily unavailable"},
    "update.found_new":{"zh-CN":"发现新版本","en":"New version found"},
    "update.no_notes":{"zh-CN":"暂无更新说明","en":"No release notes"},
    "update.none_available":{"zh-CN":"当前没有可用更新","en":"No updates are available right now."},
    "update.updating":{"zh-CN":"更新中...","en":"Updating..."},
    "update.updating_message":{"zh-CN":"正在更新，请保持此页面打开...","en":"Updating, please keep this page open..."},
    "update.success":{"zh-CN":"更新成功","en":"Update succeeded"},
    "update.restart_soon":{"zh-CN":"服务将在 3 秒后重启...","en":"The service will restart in 3 seconds..."},
    "update.failed":{"zh-CN":"更新失败","en":"Update failed"},
    "update.failed_prefix":{"zh-CN":"更新失败: ","en":"Update failed: "},
    "update.retry":{"zh-CN":"重试更新","en":"Retry update"},
    "provider.empty_hint":{"zh-CN":"还没有 Provider。点击上方 [+ 添加] 创建一个。","en":"No providers yet. Click [+ Add] above to create one."},
    "provider.saved_prefix":{"zh-CN":"Provider \"","en":"Provider \""},
    "provider.saved_suffix":{"zh-CN":"” 已保存","en":"\" saved"},
    "provider.delete_confirm_prefix":{"zh-CN":"删除 “","en":"Delete \""},
    "provider.deleted_prefix":{"zh-CN":"已删除: ","en":"Deleted: "},
    "provider.testing":{"zh-CN":"测试中...","en":"Testing..."},
    "provider.test_some_success":{"zh-CN":"⚠ 至少有一个端点可用","en":"? At least one endpoint is available"},
    "provider.test_all_failed":{"zh-CN":"❌ 全部端点失败","en":"? All endpoints failed"},
    "provider.test_success":{"zh-CN":"✅ 测试通过！","en":"? Test passed!"},
    "provider.test_failed_prefix":{"zh-CN":"测试失败: ","en":"Test failed: "},
    "provider.connecting":{"zh-CN":"连接中...","en":"Connecting..."},
    "provider.fetch_success_prefix":{"zh-CN":"✅ 已拉取 ","en":"? Fetched "},
    "provider.fetch_success_suffix":{"zh-CN":" 个模型","en":" models"},
    "provider.fetch_failed":{"zh-CN":"拉取失败","en":"Fetch failed"},
    "provider.video_model_hint":{"zh-CN":"💡 提示：视频模型通常需要手动填写","en":"Tip: video models often need to be entered manually"},
    "provider.fetch_models":{"zh-CN":"↻ 拉取","en":"? Fetch"},
    "provider.reloaded":{"zh-CN":"配置已重新加载","en":"Configuration reloaded"},
    "llm.no_provider":{"zh-CN":"还没有 LLM Provider。请先到 Provider 设置中添加。","en":"No LLM provider yet. Add one in Provider settings first."},
    "llm.selected":{"zh-CN":"✅ 已选择","en":"? Selected"},
    "llm.click_to_select":{"zh-CN":"点击选择","en":"Click to select"},
    "llm.selected_prefix":{"zh-CN":"已选择 LLM Provider: ","en":"Selected LLM provider: "},
    "llm.prompt_required":{"zh-CN":"请先输入提示词","en":"Enter a prompt first"},
    "llm.optimizing":{"zh-CN":"⏳ 优化中...","en":"? Optimizing..."},
    "llm.reoptimize":{"zh-CN":"↻ 再优化一次","en":"? Optimize again"},
    "llm.request_failed_prefix":{"zh-CN":"请求失败: ","en":"Request failed: "},
    "llm.inserted":{"zh-CN":"已插入优化后的提示词","en":"Inserted the optimized prompt"},
    "llm.undo_done":{"zh-CN":"已撤销优化并恢复原始提示词","en":"Optimization undone and original prompt restored"},
    "gallery.rename_select":{"zh-CN":"请先选择要重命名的图片","en":"Choose an image to rename first"},
    "gallery.rename_single":{"zh-CN":"重命名一次只能处理一张图片","en":"Rename supports only one image at a time"},
    "gallery.rename_prompt":{"zh-CN":"请输入新名称（支持字母、数字、下划线或中文）：","en":"Enter a new name (letters, numbers, underscores, or Chinese):"},
    "gallery.rename_failed":{"zh-CN":"重命名失败","en":"Rename failed"},
    "gallery.renamed_prefix":{"zh-CN":"已重命名: ","en":"Renamed: "},
    "gallery.rename_failed_prefix":{"zh-CN":"重命名失败: ","en":"Rename failed: "},
    "gallery.push_select":{"zh-CN":"请先选择要推送的图片","en":"Choose an image to push first"},
    "gallery.push_single":{"zh-CN":"一次只能推送一张图片","en":"Push supports only one image at a time"},
    "gallery.file_name_missing":{"zh-CN":"无法获取图片文件名","en":"Could not get the image filename"},
    "gallery.loading_reference":{"zh-CN":"正在加载参考图...","en":"Loading reference image..."},
    "gallery.pushed_to_reference":{"zh-CN":"已推送到参考图片区，你现在可以输入修改提示词并开始生成。","en":"Sent to the reference image area. You can now enter an edit prompt and generate."},
    "gallery.push_failed_prefix":{"zh-CN":"推送失败: ","en":"Push failed: "},
    "video.unsupported_i2v":{"zh-CN":"⚠ 部分已选 Provider 不支持图生视频","en":"? Some selected providers do not support image-to-video"},
    "video.unsupported_keyframes":{"zh-CN":"⚠ 部分已选 Provider 不支持关键帧","en":"? Some selected providers do not support keyframes"},
    "video.first_short":{"zh-CN":"首","en":"First"},
    "video.last_short":{"zh-CN":"尾","en":"Last"},
    "video.image_short_prefix":{"zh-CN":"图","en":"Img "},
    "video.frame_prefix":{"zh-CN":"帧","en":"Frame "},
    "video.loading_gallery_images":{"zh-CN":"正在加载图库图片...","en":"Loading gallery images..."},
    "video.gallery_empty":{"zh-CN":"图库里还没有图片，请先生成一张。","en":"The gallery has no images yet. Generate one first."},
    "video.pick_image_title":{"zh-CN":"选择图片","en":"Choose image"},
    "video.image_added":{"zh-CN":"图片已添加","en":"Image added"},
    "video.prompt_required":{"zh-CN":"请输入视频提示词","en":"Enter a video prompt"},
    "video.provider_required":{"zh-CN":"请先选择至少一个视频 Provider","en":"Choose at least one video provider first"},
    "video.model_required":{"zh-CN":"请为每个已选 Provider 选择视频模型","en":"Choose a video model for each selected provider"},
    "video.no_downloadable":{"zh-CN":"没有可下载的视频","en":"No video is available to download"},
    "video.first_frame_pushed":{"zh-CN":"已推送视频首帧","en":"The video's first frame was pushed"},
    "video.result_count_unit":{"zh-CN":"个结果","en":"results"},
    "video.no_completed":{"zh-CN":"还没有完成的视频","en":"No completed videos"},
    "video.missing_url":{"zh-CN":"⚠ 视频 URL 为空，可能还在处理中或下载失败。","en":"? Video URL is empty. It may still be processing or the download may have failed."},
    "video.generation_failed":{"zh-CN":"生成失败","en":"Generation failed"},
    "video.waiting":{"zh-CN":"等待中...","en":"Waiting..."},
    "video.waiting_submit":{"zh-CN":"等待提交...","en":"Waiting for submission..."}

   ,"provider.endpoint_name_placeholder":{"zh-CN":"端点名称（例如主用、备用）","en":"Endpoint name (e.g. primary, backup)"},
    "provider.endpoint_toggle_title":{"zh-CN":"启用或禁用此端点","en":"Enable or disable this endpoint"},
    "provider.endpoint_remove_title":{"zh-CN":"移除此端点","en":"Remove this endpoint"},
    "provider.endpoint_url_placeholder":{"zh-CN":"URL（例如 https://api.example.com/v1）","en":"URL (for example https://api.example.com/v1)"},
    "provider.endpoint_count_unit":{"zh-CN":"个端点","en":"endpoints"},
    "video.frames_adjust_confirm_prefix":{"zh-CN":"帧数 ","en":"Frame count "},
    "video.frames_adjust_confirm_middle":{"zh-CN":" 不满足 8n+1 规则，已自动调整为 ","en":" does not satisfy the 8n+1 rule. It was adjusted to "},
    "video.frames_adjust_confirm_suffix":{"zh-CN":"。继续吗？","en":". Continue?"}

   ,"server.confirm_stop":{"zh-CN":"确定要停止服务吗？","en":"Are you sure you want to stop the server?"},
    "server.confirm_restart":{"zh-CN":"确定要重启服务吗？","en":"Are you sure you want to restart the server?"},
    "server.use_lab_launcher":{"zh-CN":"为防止误停其他程序，请在项目目录运行 start-lab.ps1 stop 或 start-lab.ps1 restart。","en":"To avoid stopping another process, run start-lab.ps1 stop or start-lab.ps1 restart from the project directory."},
    "welcome.key_copied":{"zh-CN":"密钥已复制到剪贴板","en":"Key copied to clipboard"},
    "proxy.enable":{"zh-CN":"启用代理","en":"Enable proxy"},
    "proxy.host_placeholder":{"zh-CN":"主机 IP","en":"Host IP"},
    "proxy.port_placeholder":{"zh-CN":"端口","en":"Port"},
    "proxy.user_placeholder":{"zh-CN":"用户名（可选）","en":"Username (optional)"},
    "proxy.pass_placeholder":{"zh-CN":"密码（可选）","en":"Password (optional)"},
    "provider.api_key_rotation":{"zh-CN":"API Key 轮换","en":"API keys in rotation"},
    "provider.display_name_placeholder":{"zh-CN":"显示名称","en":"Display name"},
    "provider.board_name":{"zh-CN":"看板名","en":"Board name"},
    "provider.board_name_placeholder":{"zh-CN":"留空则使用上方名称","en":"Leave blank to use the name above"},
    "provider.id_placeholder":{"zh-CN":"Provider ID（唯一标识）","en":"Provider ID (unique identifier)"},
    "provider.multi_key_hint":{"zh-CN":"多 Key 轮换（可选，每行一个 Key）","en":"Multi-key rotation (optional, one key per line)"},
    "provider.available":{"zh-CN":"可用","en":"available"},
    "provider.multi_key_placeholder_html":{"zh-CN":"sk-xxx1&#10;sk-xxx2&#10;sk-xxx3&#10;（留空则使用上方单个 API Key）","en":"sk-xxx1&#10;sk-xxx2&#10;sk-xxx3&#10;(leave empty to use the single API key above)"},
    "provider.fail_count_prefix":{"zh-CN":"连续失败: ","en":"Consecutive failures: "},
    "provider.success_count_prefix":{"zh-CN":"成功次数: ","en":"Successes: "},
    "gallery.exit_select":{"zh-CN":"退出选择","en":"Exit selection"},
    "gallery.delete_select":{"zh-CN":"请先选择要删除的图片","en":"Choose images to delete first"},
    "gallery.delete_confirm_prefix":{"zh-CN":"确定删除选中的 ","en":"Delete the selected "},
    "gallery.delete_confirm_suffix":{"zh-CN":" 张图片吗？此操作不可撤销。","en":" images? This action cannot be undone."},
    "gallery.deleted_prefix":{"zh-CN":"已删除 ","en":"Deleted "},
    "gallery.deleted_suffix":{"zh-CN":" 张图片","en":" images"},
    "logs.empty":{"zh-CN":"暂无日志","en":"No logs yet"},
    "logs.clear_confirm":{"zh-CN":"确定清空所有日志吗？","en":"Clear all logs?"},
    "logs.cleared":{"zh-CN":"日志已清空","en":"Logs cleared"},
    "workspace.scheme_prefix":{"zh-CN":"方案","en":"Scheme"},
    "creator.tools":{"zh-CN":"创作工具","en":"Creation tools"},
    "creator.collapse_tools":{"zh-CN":"收起工具","en":"Collapse tools"},
    "creator.expand_tools":{"zh-CN":"展开创作工具","en":"Expand creation tools"},
    "creator.collapse":{"zh-CN":"收起","en":"Collapse"},
    "creator.expand":{"zh-CN":"展开","en":"Expand"},
    "creator.i2i_settings":{"zh-CN":"图生图设置","en":"Image-to-image settings"},
    "creator.i2i_hint":{"zh-CN":"上传参考图并描述想要的修改方向","en":"Upload a reference image and describe the edit direction"},
    "creator.variation_settings":{"zh-CN":"变体设置","en":"Variation settings"},
    "creator.variation_hint":{"zh-CN":"基于源图生成新的变化版本","en":"Generate new variations from the source image"},
    "creator.generate_variation":{"zh-CN":"生成变体","en":"Generate variation"},
    "creator.prompt_title":{"zh-CN":"提示词 PROMPT","en":"Prompt"},
    "creator.prompt_hint":{"zh-CN":"输入画面描述后直接生成","en":"Enter a scene description and generate directly"},
    "creator.tools_hint":{"zh-CN":"低频工具收纳在这里","en":"Less frequently used tools live here"},
    "creator.creation_mode":{"zh-CN":"创作模式","en":"Creation mode"},
    "creator.assist_tools":{"zh-CN":"辅助工具","en":"Assist tools"},
    "creator.task_monitor":{"zh-CN":"任务监视器","en":"Task monitor"},
    "creator.task_summary":{"zh-CN":"生成时会自动展开进度和日志","en":"Progress and logs expand automatically during generation"},
    "creator.model_tasks":{"zh-CN":"模型任务","en":"Model tasks"},
    "creator.runtime_logs":{"zh-CN":"运行日志","en":"Runtime logs"},
    "creator.keep_recent":{"zh-CN":"保留最近创作记录","en":"Keep recent creation history"},
    "creator.keep_recent_status":{"zh-CN":"已保留最近创作记录，仅用于整理，不会自动循环或把旧内容再次发送给模型。","en":"Recent creation history is kept for organization. It will not auto-loop or resend older content to models."},
    "creator.independent_status":{"zh-CN":"已启用独立生成：每次只发送当前内容，流程更简单。","en":"Independent generation is enabled: each run sends only current content for a simpler default flow."},
    "workspace.reset_default":{"zh-CN":"恢复默认","en":"Restore defaults"},
    "theme.switched_prefix":{"zh-CN":"主题已切换: ","en":"Theme switched: "},
    "video.models_load_failed_hint":{"zh-CN":"视频模型加载失败，请检查模型设置后重试。","en":"Failed to load video models. Check model settings and try again."},
    "video.models_load_failed_prefix":{"zh-CN":"视频模型加载失败: ","en":"Video model loading failed: "},
    "video.unlimited":{"zh-CN":"不限","en":"Unlimited"},
    "video.seconds_unit":{"zh-CN":"秒","en":"s"},
    "common.other":{"zh-CN":"其他","en":"Other"},
    "quick.category.style":{"zh-CN":"🎬 风格","en":"🎬 Styles"},
    "quick.category.oriental":{"zh-CN":"👘 古风","en":"👘 Classical Chinese"},
    "quick.category.nature":{"zh-CN":"🌿 自然","en":"🌿 Nature"},
    "quick.category.architecture":{"zh-CN":"🏙 建筑","en":"🏙 Architecture"},
    "quick.category.portrait":{"zh-CN":"🎭 人像","en":"🎭 Portraits"},
    "quick.category.scifi":{"zh-CN":"🚀 科幻","en":"🚀 Sci-fi"},
    "creator.single_image_title":{"zh-CN":"单模型生图工作台","en":"Single-model image workspace"},
    "creator.single_image_hint":{"zh-CN":"聚焦一个模型，大提示词、少干扰、单屏完成。","en":"One model, a larger prompt, fewer distractions, one screen."},
    "video.single_title":{"zh-CN":"单模型视频工作台","en":"Single-model video workspace"},
    "video.single_hint":{"zh-CN":"聚焦一个模型，核心参数与大输入区集中在一屏。","en":"One model with core controls and a large input area on one screen."},
    "video.no_provider":{"zh-CN":"请先在设置中添加视频 Provider","en":"Add a video provider in settings first."},
    "video.recommended":{"zh-CN":"推荐","en":"Recommended"},
    "video.multi_submit_hint":{"zh-CN":"可同时选择多个 Provider，一次提交到多个模型进行对比。","en":"Select multiple providers to submit once and compare across models."},
    "video.category.upsample":{"zh-CN":"视频放大 (Upsample)","en":"Video upsample"},
    "video.category.veo3_i2v":{"zh-CN":"Veo 3.x 图生视频 (I2V)","en":"Veo 3.x image-to-video (I2V)"},
    "video.category.veo2_i2v":{"zh-CN":"Veo 2.x 图生视频 (I2V)","en":"Veo 2.x image-to-video (I2V)"},
    "video.category.i2v":{"zh-CN":"图生视频 (I2V)","en":"Image-to-video (I2V)"},
    "video.category.veo3_r2v":{"zh-CN":"Veo 3.x 多图视频 (R2V)","en":"Veo 3.x multi-image video (R2V)"},
    "video.category.interpolation":{"zh-CN":"插帧 (Interpolation)","en":"Interpolation"},
    "video.category.veo3_t2v":{"zh-CN":"Veo 3.x 文生视频 (T2V)","en":"Veo 3.x text-to-video (T2V)"},
    "video.category.veo2_t2v":{"zh-CN":"Veo 2.x 文生视频 (T2V)","en":"Veo 2.x text-to-video (T2V)"},
    "video.category.t2v":{"zh-CN":"文生视频 (T2V)","en":"Text-to-video (T2V)"},
    "video.category.seedance":{"zh-CN":"豆包 Seedance (火山方舟)","en":"Doubao Seedance (Volcengine Ark)"},
    "video.category.kling":{"zh-CN":"可灵 Kling","en":"Kling"},
    "video.category.hailuo":{"zh-CN":"海螺 Hailuo (MiniMax)","en":"Hailuo (MiniMax)"},
    "video.category.wan":{"zh-CN":"通义万相 Wan","en":"Wan"},
    "video.category.hunyuan":{"zh-CN":"混元 Hunyuan","en":"Hunyuan"},
    "video.category.sora":{"zh-CN":"OpenAI Sora","en":"OpenAI Sora"},
    "provider.group_image_hint":{"zh-CN":"用于生成图片的模型，如 Stable Diffusion、Midjourney、Flux 等","en":"Models used for image generation, such as Stable Diffusion, Midjourney, and Flux."},
    "provider.group_video_hint":{"zh-CN":"用于生成视频的模型，如 Gemini Veo、Sora 等","en":"Models used for video generation, such as Gemini Veo and Sora."},
    "provider.group_llm_hint":{"zh-CN":"用于优化提示词的大语言模型，如 GPT-4o、Claude 等","en":"Large language models used to improve prompts, such as GPT-4o and Claude."},
    "provider.type_image":{"zh-CN":"🎨 生图","en":"🎨 Image"},
    "provider.type_video":{"zh-CN":"🎬 生视频","en":"🎬 Video"},
    "provider.type_llm":{"zh-CN":"🤖 LLM","en":"🤖 LLM"},
    "provider.type_model_none":{"zh-CN":"无匹配当前类型的模型","en":"No models match the current type"},
    "provider.load_models_first":{"zh-CN":"请先拉取模型","en":"Fetch models first"},
    "provider.manual_model_suffix":{"zh-CN":"手动","en":"manual"},
    "provider.masked_configured":{"zh-CN":"•••••••••• (已配置)","en":"•••••••••• (configured)"},
    "provider.api_key_placeholder":{"zh-CN":"留空使用 .env 或手动输入","en":"Leave blank to use .env or enter manually"},
    "provider.api_key":{"zh-CN":"API Key","en":"API Key"},
    "provider.endpoint_type_hint":{"zh-CN":"端点协议类型（auto = 按 URL 自动识别）","en":"Endpoint protocol type (auto = detect from the URL)"},
    "provider.endpoint_auto":{"zh-CN":"🔄 自动识别 (auto)","en":"🔄 Auto detect (auto)"},
    "provider.endpoint_openai":{"zh-CN":"OpenAI 兼容 (openai)","en":"OpenAI-compatible (openai)"},
    "provider.endpoint_gemini":{"zh-CN":"Google Gemini","en":"Google Gemini"},
    "provider.endpoint_qwen":{"zh-CN":"阿里通义 Qwen","en":"Alibaba Qwen"},
    "provider.endpoint_agnes":{"zh-CN":"Agnes AI","en":"Agnes AI"},
    "provider.endpoint_volc_plan":{"zh-CN":"火山方舟 Agent Plan","en":"Volcengine Ark Agent Plan"},
    "provider.endpoint_volc_ark":{"zh-CN":"火山方舟 标准 Ark","en":"Volcengine Ark Standard"},
    "provider.video_plan_warning":{"zh-CN":"⚠️ Small 套餐不支持视频生成，需在 Medium 及以上套餐才能实际出视频","en":"⚠️ The Small plan does not support video generation. Use Medium or above to generate actual videos."},
    "provider.endpoint_pool":{"zh-CN":"🌐 多端点容灾（可选，端点失效自动切换）","en":"🌐 Multi-endpoint failover (optional, switches automatically when one endpoint fails)"},
    "provider.add_endpoint":{"zh-CN":"+ 添加端点","en":"+ Add endpoint"},
    "provider.default_model":{"zh-CN":"默认模型","en":"Default model"},
    "provider.fetch_from_upstream":{"zh-CN":"↻ 从上游拉取","en":"↻ Fetch from upstream"},
    "provider.match_count_suffix":{"zh-CN":"匹配","en":"matching"},
    "provider.capability_hint":{"zh-CN":"🎯 模型能力（勾选此项支持的功能）","en":"🎯 Model capabilities (check the features this model supports)"},
    "provider.capability_auto_hint":{"zh-CN":"留空则自动根据模型名称和协议推断","en":"If left unset, capabilities are inferred automatically from the model name and protocol."},
    "dashboard.overall_score":{"zh-CN":"综合评分","en":"Overall score"},
    "dashboard.score_excellent":{"zh-CN":"优秀","en":"Excellent"},
    "dashboard.score_good":{"zh-CN":"良好","en":"Good"},
    "dashboard.score_needs_work":{"zh-CN":"待改进","en":"Needs work"},
    "dashboard.image_generation":{"zh-CN":"生图总量","en":"Image generation"},
    "dashboard.video_generation":{"zh-CN":"生视频总量","en":"Video generation"},
    "dashboard.success":{"zh-CN":"成功","en":"Success"},
    "dashboard.failed":{"zh-CN":"失败","en":"Failed"},
    "dashboard.avg_time":{"zh-CN":"平均耗时","en":"Average time"},
    "dashboard.image_generation_plain":{"zh-CN":"图片生成","en":"Image generation"},
    "dashboard.score_details":{"zh-CN":"评分详情","en":"Score details"},
    "dashboard.connectivity":{"zh-CN":"连通性","en":"Connectivity"},
    "dashboard.config_complete":{"zh-CN":"配置完整度","en":"Configuration completeness"},
    "dashboard.dependencies":{"zh-CN":"依赖环境","en":"Dependencies"},
    "dashboard.overall_score_plain":{"zh-CN":"综合评分","en":"Overall score"},
    "dashboard.system_info":{"zh-CN":"系统信息","en":"System info"},
    "dashboard.os":{"zh-CN":"操作系统","en":"OS"},
    "dashboard.architecture":{"zh-CN":"架构","en":"Architecture"},
    "dashboard.hostname":{"zh-CN":"主机名","en":"Hostname"},
    "dashboard.available":{"zh-CN":"可用","en":"available"},
    "dashboard.gallery":{"zh-CN":"图库","en":"Gallery"},
    "dashboard.images_unit":{"zh-CN":"张图片","en":"images"},
    "dashboard.video_library":{"zh-CN":"视频库","en":"Video library"},
    "dashboard.videos_unit":{"zh-CN":"个视频","en":"videos"},
    "dashboard.recent_activity":{"zh-CN":"最近活动","en":"Recent activity"},
    "dashboard.host_resources":{"zh-CN":"宿主机资源","en":"Host resources"},
    "dashboard.ip_basic_profile":{"zh-CN":"基础物理画像","en":"Basic physical profile"},
    "dashboard.ip_origin":{"zh-CN":"IP 原生性","en":"IP origin"},
    "dashboard.business_flag":{"zh-CN":"业务标记","en":"Business flag"},
    "dashboard.operator_type":{"zh-CN":"运营类型","en":"Operator type"},
    "dashboard.organization":{"zh-CN":"归属机构","en":"Organization"},
    "dashboard.isp_network_layer":{"zh-CN":"ISP 网络底层","en":"ISP network layer"},
    "dashboard.resolved_timezone":{"zh-CN":"解析时区","en":"Resolved timezone"},
    "dashboard.drift":{"zh-CN":"偏移量 (Drift)","en":"Drift"},
    "dashboard.reverse_dns":{"zh-CN":"反向 DNS (rDNS)","en":"Reverse DNS (rDNS)"},
    "dashboard.risk_scan":{"zh-CN":"风险深度检测","en":"Risk scan"},
    "dashboard.spamhaus_intel":{"zh-CN":"Spamhaus 情报","en":"Spamhaus intel"},
    "dashboard.spamhaus_listed":{"zh-CN":"⚠ 已入库 (危险)","en":"⚠ Listed (risky)"},
    "dashboard.spamhaus_clean":{"zh-CN":"✅ 纯净无异常","en":"✅ Clean"},
    "dashboard.datacenter_traits":{"zh-CN":"数据中心特征","en":"Datacenter traits"},
    "dashboard.no_rdns_traits":{"zh-CN":"未配置 rDNS (骨干网/基站中性特征)","en":"No rDNS configured (neutral backbone/mobile traits)"},
    "dashboard.data_source":{"zh-CN":"数据源","en":"Data source"},
    "dashboard.tip_hosting":{"zh-CN":"⚠️ 数据中心 IP 特征识别 · 部分 AI 服务可能限制请求","en":"⚠️ Datacenter IP traits detected · some AI services may limit requests"},
    "dashboard.tip_spamhaus":{"zh-CN":"🚨 Spamhaus 黑名单命中 · 高风险操作建议更换 IP","en":"🚨 Spamhaus match · switch IPs for high-risk operations"},
    "dashboard.tip_drift_prefix":{"zh-CN":"🌍 地理偏移 ","en":"🌍 Geographic drift "},
    "dashboard.tip_drift_suffix":{"zh-CN":" · 时区差异影响服务匹配","en":" · timezone differences may affect service matching"},
    "dashboard.tip_no_rdns":{"zh-CN":"🔍 无 rDNS 记录 · 反垃圾系统信任评分降低","en":"🔍 No rDNS record · lower trust with anti-abuse systems"},
    "dashboard.tip_assessment_prefix":{"zh-CN":"📊 网络环境综合评估：","en":"📊 Network assessment: "},
    "dashboard.tip_advice":{"zh-CN":"🛡️ 建议：定期检测 IP 信誉 · 独享代理避免污染","en":"🛡️ Advice: check IP reputation regularly · prefer dedicated proxies"},
    "dashboard.tip_latency_prefix":{"zh-CN":"⚡ TCP 延迟 ","en":"⚡ TCP latency "},
    "dashboard.tip_source_prefix":{"zh-CN":"🔐 数据源：","en":"🔐 Data source: "},
    "dashboard.tip_source_suffix":{"zh-CN":" · 时效性 24h","en":" · freshness 24h"},
    "dashboard.needs_work":{"zh-CN":"需优化","en":"Needs work"},
    "dashboard.good":{"zh-CN":"良好","en":"Good"},
    "dashboard.not_tested":{"zh-CN":"未检测","en":"Not tested"},
    "dashboard.link_excellent":{"zh-CN":"链路质量优秀","en":"Excellent link quality"},
    "dashboard.link_fair":{"zh-CN":"链路质量一般","en":"Fair link quality"},
    "dashboard.link_pending":{"zh-CN":"待评估","en":"Pending review"},
    "dashboard.edge_native":{"zh-CN":"边缘 Native 计算直出","en":"Edge native compute"},
    "dashboard.excellent":{"zh-CN":"优秀","en":"Excellent"},
    "dashboard.average":{"zh-CN":"一般","en":"Average"},
    "dashboard.poor":{"zh-CN":"较差","en":"Poor"},
    "dashboard.network_brief":{"zh-CN":"🌐 网络体检简报","en":"🌐 Network brief"},
    "dashboard.points_unit":{"zh-CN":"分","en":" pts"},
    "dashboard.listed_short":{"zh-CN":"已入库","en":"Listed"},
    "dashboard.clean_short":{"zh-CN":"纯净","en":"Clean"},

    "dashboard.proxy_traits":{"zh-CN":"代理 / 机房特征","en":"Proxy / hosting traits"}
   ,"dashboard.network_checking":{"zh-CN":"检查中...","en":"Checking..."}
   ,"dashboard.network_check_failed":{"zh-CN":"网络检查失败","en":"Network check failed"}
   ,"dashboard.network_connectivity":{"zh-CN":"网络连通性","en":"Network connectivity"}
    ,"dashboard.network_latency_title":{"zh-CN":"TCP 连接延迟（不是 API 响应时间），用于估计网络可达性","en":"TCP connect latency (not API response time), used to estimate reachability"}
   ,"dashboard.connectivity_checking":{"zh-CN":"⏳ 检查中...","en":"Checking..."}
   ,"dashboard.connectivity_check":{"zh-CN":"🔍 运行连通性检查","en":"Run connectivity check"}
   ,"dashboard.connectivity_failed":{"zh-CN":"❌ 检查失败","en":"Check failed"}
   ,"dashboard.connectivity_done":{"zh-CN":"✅ 检查完成","en":"Check complete"}
    ,"dashboard.network_tcp_prefix":{"zh-CN":"TCP ","en":"TCP "}
    ,"dashboard.unreachable":{"zh-CN":"不可达","en":"Unreachable"}
    ,"dashboard.no_address":{"zh-CN":"无地址","en":"No address"}
    ,"dashboard.unreachable_short":{"zh-CN":"异常","en":"Down"}
    ,"dashboard.ip_toggle":{"zh-CN":"显示/隐藏 IP","en":"Show/hide IP"}
    ,"dashboard.ip_load_failed":{"zh-CN":"IP 信息加载失败","en":"Failed to load IP info"}
   ,"dashboard.resources_load_failed":{"zh-CN":"资源信息加载失败","en":"Failed to load resource info"}
   ,"dashboard.model_provider":{"zh-CN":"模型 Provider","en":"Model providers"}
   ,"dashboard.local_ip_info":{"zh-CN":"本地 IP 信息","en":"Local IP info"}
   ,"dashboard.enabled":{"zh-CN":"已启用","en":"Enabled"}
   ,"dashboard.disabled":{"zh-CN":"已禁用","en":"Disabled"}
   ,"dashboard.disk_space":{"zh-CN":"磁盘空间","en":"Disk space"}
   ,"dashboard.disk_usage":{"zh-CN":"磁盘占用","en":"Disk usage"}
   ,"dashboard.uptime":{"zh-CN":"运行时间","en":"Uptime"}
   ,"dashboard.network_io":{"zh-CN":"网络流量","en":"Network I/O"}
   ,"dashboard.sent":{"zh-CN":"发送","en":"Sent"}
   ,"dashboard.received":{"zh-CN":"接收","en":"Received"}
   ,"dashboard.cpu_cores":{"zh-CN":" 线程","en":" threads"}
   ,"dashboard.cpu_physical":{"zh-CN":" 物理核","en":" physical"}
   ,"dashboard.days_unit":{"zh-CN":"天 ","en":"d "}
   ,"dashboard.hours_unit":{"zh-CN":"h ","en":"h "}
   ,"dashboard.minutes_unit":{"zh-CN":"m","en":"m"}
   ,"dashboard.top_processes":{"zh-CN":"Top 进程","en":"Top processes"}
   ,"dashboard.free":{"zh-CN":"空闲","en":"Free"}
  };

  MESSAGES['library.provider_az'] = {"zh-CN":"Provider A-Z","en":"Provider A-Z"};
  MESSAGES['library.provider_za'] = {"zh-CN":"Provider Z-A","en":"Provider Z-A"};
  MESSAGES['workspace.font_compact'] = {"zh-CN":"紧凑","en":"Compact"};
  MESSAGES['workspace.font_standard'] = {"zh-CN":"标准","en":"Standard"};
  MESSAGES['workspace.font_comfortable'] = {"zh-CN":"舒适","en":"Comfortable"};
  MESSAGES['workspace.mode_full'] = {"zh-CN":"完整","en":"Full"};
  MESSAGES['workspace.mode_create'] = {"zh-CN":"创作","en":"Create"};
  MESSAGES['workspace.mode_media'] = {"zh-CN":"媒体","en":"Media"};
  MESSAGES['workspace.mode_simple'] = {"zh-CN":"简洁","en":"Simple"};
  MESSAGES['workspace.mode_custom'] = {"zh-CN":"自定义","en":"Custom"};
  MESSAGES['appearance.current'] = {"zh-CN":"当前使用","en":"Current"};
  MESSAGES['onboarding.title'] = {"zh-CN":"3 分钟完成 GenBox 上手","en":"Get started with GenBox in 3 minutes"};
  MESSAGES['onboarding.subtitle'] = {"zh-CN":"先了解最短路径，再按需补 API Key。模型名称、提示词和密钥内容不会被翻译。","en":"Start with the shortest path, then add API keys only when needed. Model names, prompts, and key contents are never translated."};
  MESSAGES['onboarding.badge_beginner'] = {"zh-CN":"适合第一次打开 GenBox","en":"Best for your first time in GenBox"};
  MESSAGES['onboarding.badge_bilingual'] = {"zh-CN":"中英文同步可用","en":"Available in Chinese and English"};
  MESSAGES['onboarding.path_title'] = {"zh-CN":"推荐上手路径","en":"Recommended first-run path"};
  MESSAGES['onboarding.path_step_1'] = {"zh-CN":"先配置 1 个生图模型，确认可以正常生成。","en":"Set up one image model first and confirm generation works."};
  MESSAGES['onboarding.path_step_2'] = {"zh-CN":"再试多模型对比，熟悉图像 / 视频 / 历史 / 媒体库。","en":"Then try multi-model comparison and learn Images / Video / History / Media Library."};
  MESSAGES['onboarding.path_step_3'] = {"zh-CN":"最后再进入扩展功能和私网部署，不和首次创作混在一起。","en":"Leave Extensions and private-network deployment for later so first creation stays simple."};
  MESSAGES['onboarding.step_1_title'] = {"zh-CN":"步骤 1：先把创作跑起来","en":"Step 1: get creation working first"};
  MESSAGES['onboarding.step_1_desc'] = {"zh-CN":"如果你只想尽快出图，优先添加一个能用的生图 Provider，然后直接进入生图页。","en":"If your goal is fast image output, add one working image provider first and jump straight to Images."};
  MESSAGES['onboarding.step_2_title'] = {"zh-CN":"步骤 2：理解结果会去哪里","en":"Step 2: know where results go"};
  MESSAGES['onboarding.step_2_desc'] = {"zh-CN":"生成后的图片和视频会进入媒体库；每次调用过程会保存在历史页，方便回看和筛选。","en":"Generated images and videos go to Media Library, while each run is saved in History for review and filtering."};
  MESSAGES['onboarding.step_3_title'] = {"zh-CN":"步骤 3：进阶功能后面再开","en":"Step 3: open advanced features later"};
  MESSAGES['onboarding.step_3_desc'] = {"zh-CN":"扩展功能、私网连接、远程同步和 chatgpt2api 联动更适合在基础创作确认后再配置。","en":"Extensions, private networking, remote sync, and chatgpt2api integration are best configured after core creation is confirmed."};
  MESSAGES['onboarding.action_models'] = {"zh-CN":"配置模型","en":"Configure models"};
  MESSAGES['onboarding.action_generate'] = {"zh-CN":"打开生图页","en":"Open Images"};
  MESSAGES['onboarding.action_gallery'] = {"zh-CN":"查看媒体库","en":"Open Media Library"};
  MESSAGES['onboarding.action_history'] = {"zh-CN":"查看历史","en":"Open History"};
  MESSAGES['onboarding.action_extensions'] = {"zh-CN":"查看扩展功能","en":"Open Extensions"};
  MESSAGES['onboarding.action_sync'] = {"zh-CN":"了解远程同步","en":"Explore remote sync"};
  MESSAGES['onboarding.quick_setup_title'] = {"zh-CN":"可选：现在就补常用 Key","en":"Optional: add common keys now"};
  MESSAGES['onboarding.quick_setup_desc'] = {"zh-CN":"这里保留快速配置入口，适合已经有 API Key 的用户。后续也可以随时在模型设置里再改。","en":"Quick setup stays here for users who already have API keys. You can still edit everything later in Model settings."};
  MESSAGES['onboarding.manage_all'] = {"zh-CN":"打开完整模型设置","en":"Open full model settings"};
  MESSAGES['onboarding.action_dashboard'] = {"zh-CN":"先看系统看板","en":"Open Dashboard first"};
  MESSAGES['onboarding.models_title'] = {"zh-CN":"模型名称由你定义","en":"Model names are yours to define"};
  MESSAGES['onboarding.models_desc'] = {"zh-CN":"这里展示当前模型设置中的名称，不再写死端点。名称、URL、Key 和默认模型都在模型设置中统一维护。","en":"Names shown here come from Model settings. Manage names, URLs, keys, and default models in one place instead of using fixed endpoints."};
  MESSAGES['onboarding.providers_empty'] = {"zh-CN":"尚未配置生图或视频 Provider","en":"No image or video providers configured yet"};
  MESSAGES['onboarding.action_deploy'] = {"zh-CN":"开始部署引导","en":"Start deployment guide"};
  MESSAGES['onboarding.footer_hint'] = {"zh-CN":"完成后会用一个简短导览介绍主要标签页。","en":"A short tour of the main tabs starts when you finish."};
  MESSAGES['onboarding.finish'] = {"zh-CN":"完成并开始导览","en":"Finish and start tour"};
  MESSAGES['onboarding.brand_kicker'] = {"zh-CN":"GENBOX GETTING STARTED","en":"GENBOX GETTING STARTED"};
  MESSAGES['onboarding.capability_title'] = {"zh-CN":"先看 GenBox 现在能帮你完成什么","en":"What GenBox can help you do right now"};
  MESSAGES['onboarding.capability_desc'] = {"zh-CN":"这里介绍创作、整理和扩展能力，不展示 Provider 名称、端点或密钥。真正的模型配置仍在模型设置中统一维护。","en":"This section explains creation, organization, and extension capabilities without showing provider names, endpoints, or keys. Actual model configuration still lives in Model settings."};
  MESSAGES['onboarding.capability_ready'] = {"zh-CN":"当前可用","en":"Available now"};
  MESSAGES['onboarding.capability_planned'] = {"zh-CN":"开发中","en":"In development"};
  MESSAGES['onboarding.capability_image_title'] = {"zh-CN":"图片创作","en":"Image creation"};
  MESSAGES['onboarding.capability_image_desc'] = {"zh-CN":"支持文生图、图生图、超分辨率、多模型并排对比，以及单模型或多模型批量出图。","en":"Supports text-to-image, image-to-image, super resolution, side-by-side multi-model comparison, and one-to-many or multi-model generation."};
  MESSAGES['onboarding.capability_editing_title'] = {"zh-CN":"图片编辑","en":"Image editing"};
  MESSAGES['onboarding.capability_editing_desc'] = {"zh-CN":"本地局部重绘仍在开发中；在正式完成前，不会被描述为可直接使用。","en":"Local inpainting is still in development and is not presented as ready before it is actually complete."};
  MESSAGES['onboarding.capability_video_title'] = {"zh-CN":"视频创作","en":"Video creation"};
  MESSAGES['onboarding.capability_video_desc'] = {"zh-CN":"当前工作台覆盖文生视频、图生视频和关键帧流程，并保持统一的提示词与任务视图。","en":"The current workspace covers text-to-video, image-to-video, and keyframe flows with one unified prompt and task view."};
  MESSAGES['onboarding.capability_media_title'] = {"zh-CN":"媒体整理","en":"Media organization"};
  MESSAGES['onboarding.capability_media_desc'] = {"zh-CN":"集中管理图片和视频，按历史、模型、提示词和时间回看内容，并继续复用已有提示词。","en":"Manage images and videos in one place, review them by history, model, prompt, or time, and reuse previous prompts."};
  MESSAGES['onboarding.capability_prompt_title'] = {"zh-CN":"提示词辅助","en":"Prompt assistance"};
  MESSAGES['onboarding.capability_prompt_desc'] = {"zh-CN":"把自然语言意图整理成更专业的提示词，帮助第一次使用时更快得到稳定结果。","en":"Turn natural-language intent into a more production-ready prompt so first-time users can reach stable results faster."};
  MESSAGES['onboarding.capability_extensions_title'] = {"zh-CN":"扩展中心","en":"Extension center"};
  MESSAGES['onboarding.capability_extensions_desc'] = {"zh-CN":"通过图形界面完成服务部署、实例管理和网络准备，不需要自己写部署命令。","en":"Use guided UI flows for service deployment, instance management, and network preparation without writing deployment commands yourself."};
  MESSAGES['onboarding.chatgpt_intro_title'] = {"zh-CN":"chatgpt2api 是什么","en":"What is chatgpt2api?"};
  MESSAGES['onboarding.chatgpt_intro_desc'] = {"zh-CN":"它是一个可自己部署的第三方网关，把 ChatGPT 官网已经实现的文本、搜索、图片生成与图片编辑能力，整理成常见软件更容易连接的 OpenAI 兼容接口。","en":"It is a self-hosted third-party gateway that packages implemented ChatGPT web capabilities for text, search, image generation, and image editing behind OpenAI-compatible APIs that common tools can connect to."};
  MESSAGES['onboarding.chatgpt_intro_api_title'] = {"zh-CN":"兼容常见 AI 工具","en":"Works with familiar AI tools"};
  MESSAGES['onboarding.chatgpt_intro_api_desc'] = {"zh-CN":"提供 OpenAI 兼容接口，可连接常见客户端、SDK 或网关，不必让每个工具都理解 ChatGPT 官网协议。","en":"OpenAI-compatible endpoints let common clients, SDKs, and gateways connect without each tool understanding ChatGPT web protocols."};
  MESSAGES['onboarding.chatgpt_intro_studio_title'] = {"zh-CN":"聊天、搜索和画图","en":"Chat, search, and image creation"};
  MESSAGES['onboarding.chatgpt_intro_studio_desc'] = {"zh-CN":"内置对话画图工作台，覆盖文本对话、网页搜索、文生图、图生图、多图参考和任务进度。","en":"Its built-in workspace combines chat, web search, text-to-image, image-to-image, multiple references, and task progress."};
  MESSAGES['onboarding.chatgpt_intro_ops_title'] = {"zh-CN":"账号、代理和排障","en":"Accounts, proxies, and diagnostics"};
  MESSAGES['onboarding.chatgpt_intro_ops_desc'] = {"zh-CN":"提供多账号管理、代理出口、调用日志和实时监控，方便查看请求是否成功以及问题出在哪里。","en":"Multi-account management, proxy routing, call logs, and live monitoring help show whether requests worked and where failures occurred."};
  MESSAGES['onboarding.chatgpt_intro_host_title'] = {"zh-CN":"自己部署和保存","en":"Self-hosting and storage"};
  MESSAGES['onboarding.chatgpt_intro_host_desc'] = {"zh-CN":"支持 Docker 部署，并可使用本地或 WebDAV 图片存储，适合需要自己掌控运行环境和数据的人。","en":"Docker deployment plus local or WebDAV image storage suits users who want control over their runtime and data."};
  MESSAGES['onboarding.chatgpt_intro_source'] = {"zh-CN":"内容根据 yukkcat/chatgpt2api 公开 README 提炼。该项目属于第三方逆向研究实现，存在账号受限风险，不要使用重要或高价值账号测试。","en":"Summarized from the public yukkcat/chatgpt2api README. This third-party reverse-engineering project can put accounts at risk; do not test with important or high-value accounts."};
  MESSAGES['onboarding.chatgpt_intro_project'] = {"zh-CN":"查看 chatgpt2api 项目","en":"View the chatgpt2api project"};
  MESSAGES['onboarding.chat_title'] = {"zh-CN":"为什么把 chatgpt2api 接入 GenBox","en":"Why connect chatgpt2api to GenBox?"};
  MESSAGES['onboarding.chat_desc'] = {"zh-CN":"可以把 chatgpt2api 理解为放在远程服务器上的创作站，把 GenBox 理解为你自己的作品仓库。当前可以先由 GenBox 引导部署、建立私网并主动拉取图片；后续自动 Push 完成后，新作品将能更省心地回到电脑或 NAS，减少手动下载、反复整理和 VPS 空间压力。","en":"Think of chatgpt2api as a creation station on a remote server and GenBox as your own media library. Today GenBox can guide deployment, establish a private link, and pull images. Once automatic Push is completed later, new work can return to your computer or NAS with less manual downloading, repetitive organization, and VPS storage pressure."};
  MESSAGES['onboarding.chat_meta'] = {"zh-CN":"当前先把安全连接和手动同步打好基础；自动发送、批量搬运、定时同步和确认后清理仍是后续阶段。","en":"The current foundation covers secure connection and manual sync; automatic sending, batch transfer, scheduling, and verified cleanup remain later phases."};
  MESSAGES['onboarding.chat_available_label'] = {"zh-CN":"现在已经能做","en":"Available now"};
  MESSAGES['onboarding.chat_available_title'] = {"zh-CN":"先安全地连起来","en":"Connect the two services safely"};
  MESSAGES['onboarding.chat_available_1'] = {"zh-CN":"按页面引导，在 VPS 上部署一个独立的 chatgpt2api 实例。","en":"Use the guided UI to deploy an isolated chatgpt2api instance on a VPS."};
  MESSAGES['onboarding.chat_available_2'] = {"zh-CN":"建立私网连接，让远程服务和这台 GenBox 安全互通。","en":"Create a private link so the remote service and this GenBox can communicate safely."};
  MESSAGES['onboarding.chat_available_3'] = {"zh-CN":"由 GenBox 主动拉取远程图片，统一放进本地媒体库。","en":"Let GenBox pull remote images into one local media library."};
  MESSAGES['onboarding.chat_available_4'] = {"zh-CN":"GenBox 已准备好带身份验证、避免重复导入的图片接收接口。","en":"GenBox already provides an authenticated image receiver that avoids duplicate imports."};
  MESSAGES['onboarding.chat_available_5'] = {"zh-CN":"需要时可以保存和规划多台 VPS 的部署目标。","en":"Save and plan deployment targets across multiple VPS nodes when needed."};
  MESSAGES['onboarding.chat_planned_label'] = {"zh-CN":"接下来逐步补齐","en":"Coming later"};
  MESSAGES['onboarding.chat_planned_title'] = {"zh-CN":"让图片搬运越来越省心","en":"Make image transfer increasingly hands-off"};
  MESSAGES['onboarding.chat_planned_1'] = {"zh-CN":"在 chatgpt2api 生成图片后，选择自动发送到 GenBox。","en":"Choose to send an image to GenBox after it is generated in chatgpt2api."};
  MESSAGES['onboarding.chat_planned_2'] = {"zh-CN":"批量搬运旧图片，并按计划定时同步新增内容。","en":"Move older images in batches and sync new content on a schedule."};
  MESSAGES['onboarding.chat_planned_3'] = {"zh-CN":"确认 GenBox 已完整收到后，再安全清理远端源图并统计释放空间。","en":"After GenBox confirms a complete receipt, safely clean remote source images and report reclaimed space."};
  MESSAGES['onboarding.chat_planned_4'] = {"zh-CN":"从干净仓库重新部署并完成发布验证后，再进入正式交付。","en":"Complete clean-repository redeployment and release verification before formal delivery."};
  MESSAGES['tour.dashboard_title'] = {"zh-CN":"系统看板","en":"Dashboard"};
  MESSAGES['tour.dashboard_desc'] = {"zh-CN":"查看模型状态、系统资源、网络连通性和最近活动。","en":"Review model status, host resources, connectivity, and recent activity."};
  MESSAGES['tour.images_title'] = {"zh-CN":"生图工作台","en":"Image workspace"};
  MESSAGES['tour.images_desc'] = {"zh-CN":"在单模型或多模型模式中输入提示词、生成图片并比较结果。","en":"Enter prompts, generate images, and compare results in single- or multi-model mode."};
  MESSAGES['tour.video_title'] = {"zh-CN":"生视频工作台","en":"Video workspace"};
  MESSAGES['tour.video_desc'] = {"zh-CN":"使用统一的提示词输入区完成文生视频、图生视频和关键帧任务。","en":"Use the unified prompt workspace for text-to-video, image-to-video, and keyframes."};
  MESSAGES['tour.library_title'] = {"zh-CN":"媒体库","en":"Media Library"};
  MESSAGES['tour.library_desc'] = {"zh-CN":"集中查看、筛选和管理本地图片与视频。","en":"Browse, filter, and manage local images and videos in one place."};
  MESSAGES['tour.extensions_title'] = {"zh-CN":"扩展功能","en":"Extensions"};
  MESSAGES['tour.extensions_desc'] = {"zh-CN":"在这里部署 chatgpt2api、配置私网链路并管理已部署服务。","en":"Deploy chatgpt2api, configure private networking, and manage deployed services here."};
  MESSAGES['proxy.title'] = {"zh-CN":"网络代理","en":"Network proxy"};
  MESSAGES['proxy.hint'] = {"zh-CN":"用于连接国外模型厂商（OpenAI、Gemini 等）","en":"Used to connect to overseas model providers such as OpenAI and Gemini."};
  MESSAGES['update.auto_check'] = {"zh-CN":"启动时自动检查更新","en":"Automatically check for updates at startup"};
  MESSAGES['dashboard.ip_show'] = {"zh-CN":"显示 IP","en":"Show IP"};
  MESSAGES['dashboard.ip_hide'] = {"zh-CN":"隐藏 IP","en":"Hide IP"};

  MESSAGES['common.continue'] = {"zh-CN":"继续","en":"Continue"};
  MESSAGES['extensions.step_vps'] = {"zh-CN":"开始部署","en":"Start deployment"};
  MESSAGES['extensions.step_deploy'] = {"zh-CN":"准备应用服务","en":"Prepare service"};
  MESSAGES['extensions.step_choose_network'] = {"zh-CN":"准备本机网络","en":"Prepare local network"};
  MESSAGES['extensions.step_configure'] = {"zh-CN":"连接并测试","en":"Connect and test"};
  MESSAGES['extensions.step_verify'] = {"zh-CN":"完成","en":"Finish"};
  MESSAGES['extensions.guide_kicker'] = {"zh-CN":"当前只做一件事","en":"One action at a time"};
  MESSAGES['extensions.guide_connect_title'] = {"zh-CN":"部署 GenBox 扩展服务","en":"Deploy a GenBox extension service"};
  MESSAGES['extensions.guide_found'] = {"zh-CN":"系统已发现","en":"GenBox found"};
  MESSAGES['extensions.guide_action'] = {"zh-CN":"你现在只需","en":"Your only action"};
  MESSAGES['extensions.guide_after'] = {"zh-CN":"完成后会","en":"Then GenBox will"};
  MESSAGES['extensions.show_advanced'] = {"zh-CN":"查看高级设置和日志","en":"Show advanced settings and logs"};
  MESSAGES['extensions.hide_advanced'] = {"zh-CN":"收起高级设置和日志","en":"Hide advanced settings and logs"};
  MESSAGES['extensions.guide_step1_title'] = {"zh-CN":"先连接你的服务器","en":"Connect your server first"};
  MESSAGES['extensions.guide_step1_unsaved'] = {"zh-CN":"这台 VPS 还没有保存。","en":"This VPS has not been saved yet."};
  MESSAGES['extensions.guide_step1_save'] = {"zh-CN":"确认名称、地址和 SSH 用户，然后点“保存”。","en":"Confirm the name, address, and SSH user, then save."};
  MESSAGES['extensions.guide_step1_saved'] = {"zh-CN":"VPS 信息已保存，还差一次服务器身份确认。","en":"The VPS is saved; its public identity still needs confirmation."};
  MESSAGES['extensions.guide_step1_host_key'] = {"zh-CN":"在你已登录的终端中确认这台服务器；这一步不输入密码或私钥。","en":"Confirm this server in a terminal where you are already signed in; this does not enter a password or private key."};
  MESSAGES['extensions.guide_step1_pairing_active'] = {"zh-CN":"把下方确认工具复制到已信任终端运行，再粘贴确认码。","en":"Copy the confirmation tool below into your trusted terminal, run it, then paste the confirmation code."};
  MESSAGES['extensions.guide_step1_pairing_after'] = {"zh-CN":"粘贴后，点击“确认这台服务器”。","en":"After pasting, select Confirm this server."};
  MESSAGES['extensions.guide_step1_identity_ready'] = {"zh-CN":"服务器身份已经确认。","en":"The server identity is confirmed."};
  MESSAGES['extensions.guide_step1_credential'] = {"zh-CN":"输入本次使用的 SSH 密码或私钥。它只留在当前页面。","en":"Enter the SSH password or key for this session only."};
  MESSAGES['extensions.guide_step1_credential_after'] = {"zh-CN":"服务器确认已经完成；填写后只运行一次环境读取，不会部署或使用 sudo。","en":"Server confirmation is complete. After entering credentials, GenBox performs one environment read only; it does not deploy or use sudo."};
  MESSAGES['extensions.guide_step1_test'] = {"zh-CN":"让 GenBox 读取服务器环境，核对 Docker、端口和容量。","en":"Let GenBox read the server environment and check Docker, ports, and capacity."};
  MESSAGES['extensions.guide_step1_connected'] = {"zh-CN":"只读环境检查已完成。","en":"The read-only environment check is complete."};
  MESSAGES['extensions.guide_step1_next'] = {"zh-CN":"核对部署选项。","en":"Review deployment options."};
  MESSAGES['extensions.guide_step1_next_after'] = {"zh-CN":"继续核对环境和方案，仍不会部署。","en":"Review the environment and plan next; deployment still will not start."};
  MESSAGES['extensions.guide_step1_resume_ready'] = {"zh-CN":"已找到原来的应用服务和正确 VPS。","en":"The existing service and its VPS were found."};
  MESSAGES['extensions.guide_step1_resume'] = {"zh-CN":"继续检查这台电脑的 Tailscale。","en":"Continue with this computer's Tailscale check."};
  MESSAGES['extensions.guide_step1_resume_after'] = {"zh-CN":"不会重复部署应用。","en":"The service will not be deployed again."};
  MESSAGES['extensions.connection_path_kicker'] = {"zh-CN":"连接方式","en":"Connection method"};
  MESSAGES['extensions.connection_path_title'] = {"zh-CN":"先选择适合你的连接方式","en":"Choose the connection method that fits you"};
  MESSAGES['extensions.connection_path_help'] = {"zh-CN":"服务器连接器是后续的默认方向；在它真正可用前，SSH 仍可完整完成当前部署流程。","en":"A server connector is the future default; until it is truly available, SSH still completes the current deployment flow."};
  MESSAGES['extensions.connection_connector_status'] = {"zh-CN":"准备中","en":"In preparation"};
  MESSAGES['extensions.connection_connector_title'] = {"zh-CN":"服务器连接器（推荐）","en":"Server connector (recommended)"};
  MESSAGES['extensions.connection_connector_body'] = {"zh-CN":"连接器安装在你的服务器上，主动建立受限连接；它不会把 SSH 密码或私钥交给浏览器。","en":"The connector runs on your server and initiates a restricted connection; it does not give SSH passwords or private keys to the browser."};
  MESSAGES['extensions.connection_connector_unavailable'] = {"zh-CN":"当前版本还没有可安装的连接器和受信传输通道，因此不能假装已经连接或用于部署。","en":"This version has no installable connector or trusted transport yet, so it cannot claim to be connected or deploy."};
  MESSAGES['extensions.connection_ssh_status'] = {"zh-CN":"当前可用","en":"Available now"};
  MESSAGES['extensions.connection_ssh_title'] = {"zh-CN":"SSH 连接（高级方式）","en":"SSH connection (advanced)"};
  MESSAGES['extensions.connection_ssh_body'] = {"zh-CN":"这是当前完整可用的路径：保存服务器、确认服务器身份、临时输入凭据并测试部署权限。","en":"This is the complete path available now: save the server, confirm its identity, enter a temporary credential, and test deployment access."};
  MESSAGES['extensions.connection_ssh_button'] = {"zh-CN":"使用 SSH 继续","en":"Continue with SSH"};
  MESSAGES['extensions.ssh_fallback_selected'] = {"zh-CN":"已进入当前可用的 SSH 流程。先填写并保存服务器信息。","en":"The available SSH flow is selected. Fill in and save the server information first."};
  MESSAGES['extensions.step_start_deploy'] = {"zh-CN":"开始部署","en":"Start deployment"};
  MESSAGES['extensions.personal_start_ssh'] = {"zh-CN":"使用 SSH 设置服务器","en":"Set up with SSH"};
  MESSAGES['extensions.personal_server_details'] = {"zh-CN":"填写服务器资料","en":"Add server details"};
  MESSAGES['extensions.personal_identity_kicker'] = {"zh-CN":"安全确认","en":"Safety check"};
  MESSAGES['extensions.personal_identity_title'] = {"zh-CN":"确认这就是你的服务器","en":"Confirm this is your server"};
  MESSAGES['extensions.personal_identity_changed_title'] = {"zh-CN":"服务器身份发生变化","en":"The server identity changed"};
  MESSAGES['extensions.personal_identity_help'] = {"zh-CN":"这一步完成前不会使用 SSH 密码或私钥。","en":"SSH passwords and private keys are not used until this step is complete."};
  MESSAGES['extensions.personal_edit_server'] = {"zh-CN":"返回修改服务器资料","en":"Edit server details"};
  MESSAGES['extensions.personal_access_kicker'] = {"zh-CN":"访问检查","en":"Access check"};
  MESSAGES['extensions.personal_access_title'] = {"zh-CN":"运行一次只读检查","en":"Run one read-only check"};
  MESSAGES['extensions.personal_access_help'] = {"zh-CN":"凭据只用于这次检查，关闭页面后不会保留。不会部署服务，也不会使用 sudo。","en":"Credentials are used only for this check and are not kept after the page closes. It does not deploy a service or use sudo."};
  MESSAGES['extensions.personal_check_continue'] = {"zh-CN":"运行只读检查","en":"Run read-only check"};
  MESSAGES['extensions.advanced_deployment_access'] = {"zh-CN":"高级部署权限（本次不用填）","en":"Advanced deployment access (not needed for this check)"};
  MESSAGES['extensions.advanced_deployment_access_help'] = {"zh-CN":"只读环境检查不会使用 sudo。只有准备部署或私网设置时，才按实际需要填写。","en":"The read-only environment check does not use sudo. Provide these only when preparing deployment or private-network setup."};
  MESSAGES['extensions.personal_ready_kicker'] = {"zh-CN":"检查完成","en":"Check complete"};
  MESSAGES['extensions.personal_ready_title'] = {"zh-CN":"环境检查完成","en":"Environment check complete"};
  MESSAGES['extensions.personal_ready_help'] = {"zh-CN":"下一步核对部署选项和安全计划；不会自动部署。","en":"Next, review deployment options and the safety plan; deployment will not start automatically."};
  MESSAGES['extensions.personal_begin_planning'] = {"zh-CN":"核对部署选项","en":"Review deployment options"};
  MESSAGES['extensions.personal_ssh_selected'] = {"zh-CN":"先填写服务器资料；系统会按顺序完成确认和检查。","en":"Add the server details first; GenBox will guide the next checks in order."};
  MESSAGES['extensions.guide_step1_after'] = {"zh-CN":"安全进入下一步，不会修改现有服务。","en":"Move forward safely without changing the existing service."};
  MESSAGES['extensions.enter_password_button'] = {"zh-CN":"去输入 SSH 密码","en":"Enter SSH password"};
  MESSAGES['extensions.enter_private_key_button'] = {"zh-CN":"去输入 SSH 私钥","en":"Enter SSH private key"};
  MESSAGES['extensions.guide_step2_title'] = {"zh-CN":"准备应用服务","en":"Prepare the service"};
  MESSAGES['extensions.guide_step2_ready'] = {"zh-CN":"应用服务已经部署完成。","en":"The service is already deployed."};
  MESSAGES['extensions.guide_step2_skip'] = {"zh-CN":"直接继续准备本机网络。","en":"Continue directly to local networking."};
  MESSAGES['extensions.guide_step2_unknown'] = {"zh-CN":"还不知道 VPS 上有哪些服务和安装条件。","en":"The VPS environment has not been checked yet."};
  MESSAGES['extensions.guide_step2_detect'] = {"zh-CN":"运行一次只读环境检测。","en":"Run one read-only environment check."};
  MESSAGES['extensions.guide_step2_after'] = {"zh-CN":"给出推荐方案；部署前仍会让你确认。","en":"Recommend a plan and still ask before deployment."};
  MESSAGES['extensions.guide_step2_discovering'] = {"zh-CN":"正在安全读取 VPS 环境，不会修改现有服务。","en":"Safely reading the VPS environment without changing existing services."};
  MESSAGES['extensions.readonly_discovery_ready'] = {"zh-CN":"已可运行一次只读环境检查；部署权限会在真正部署前单独核对。","en":"A one-time read-only environment check is ready; deployment access is checked separately before an actual deployment."};
  MESSAGES['extensions.readonly_discovery_timeout'] = {"zh-CN":"只读环境检查在限定时间内未完成，已停止本次检查。无需重新确认服务器身份；请检查 SSH 或 Docker 响应后再试。","en":"The read-only environment check did not finish in time and has stopped. You do not need to reconfirm the server identity; check SSH or Docker responsiveness before trying again."};
  MESSAGES['extensions.discovery_ready_for_planning'] = {"zh-CN":"只读环境检查完成。现在可以核对部署选项；不会自动部署。","en":"Read-only environment check complete. You can now review deployment options; deployment will not start automatically."};
  MESSAGES['extensions.discovery_deploy_access_limited'] = {"zh-CN":"只读环境检查完成，但当前会话尚未确认部署权限。请先核对结果；需要部署时再选择高级权限诊断。","en":"Read-only environment check complete, but deployment access is not confirmed for this session. Review the result first; use the advanced access diagnostic only when preparing to deploy."};
  MESSAGES['extensions.discovery_deploy_access_action'] = {"zh-CN":"部署权限尚未确认。","en":"Deployment access is not confirmed."};
  MESSAGES['extensions.discovery_deploy_access_after'] = {"zh-CN":"这不会重新配对或重新读取环境。","en":"This does not restart pairing or re-read the environment."};
  MESSAGES['extensions.guide_step2_wait_discovery'] = {"zh-CN":"请稍等，检测结束后会自动告诉你下一步。","en":"Wait briefly; the next action will appear automatically."};
  MESSAGES['extensions.guide_step2_discovered'] = {"zh-CN":"VPS 环境已经检测完成。","en":"The VPS environment check is complete."};
  MESSAGES['extensions.guide_step2_make_plan'] = {"zh-CN":"根据检测结果生成一份可核对的安全计划。","en":"Generate a reviewable safety plan from the results."};
  MESSAGES['extensions.guide_step2_image_needed'] = {"zh-CN":"部署镜像还没有准备好。","en":"The deployment image is not ready yet."};
  MESSAGES['extensions.guide_step2_image_action'] = {"zh-CN":"先填写可由服务器拉取的镜像摘要地址。","en":"Enter the immutable image reference the server can pull."};
  MESSAGES['extensions.guide_step2_image_after'] = {"zh-CN":"填写完成后，才能生成安全计划；不会自动部署。","en":"After entering it, you can generate a safety plan; nothing deploys automatically."};
  MESSAGES['extensions.prepare_deploy_image'] = {"zh-CN":"填写部署镜像","en":"Enter deployment image"};
  MESSAGES['extensions.plan_discovery_confirm'] = {"zh-CN":"生成安全计划前，GenBox 会对这台隔离开发机进行两次固定的只读复核，用来核对端口、目录和隔离范围。不会部署、拉取镜像或改动服务。现在继续吗？","en":"Before generating the safety plan, GenBox will run two fixed read-only checks on this isolated development server to verify ports, directories, and isolation. It will not deploy, pull an image, or change services. Continue?"};
  MESSAGES['extensions.plan_confirm_kicker'] = {"zh-CN":"部署前复核","en":"Pre-deployment review"};
  MESSAGES['extensions.plan_confirm_title'] = {"zh-CN":"允许只读复核并生成计划","en":"Allow read-only review and generate the plan"};
  MESSAGES['extensions.plan_confirm_body'] = {"zh-CN":"GenBox 将再次读取隔离开发机的端口、目录和隔离状态，不会部署、拉取镜像或修改服务。","en":"GenBox will re-check ports, directories, and isolation on the development machine. It will not deploy, pull an image, or modify services."};
  MESSAGES['extensions.plan_confirm_continue'] = {"zh-CN":"继续生成计划","en":"Continue to generate plan"};
  MESSAGES['extensions.plan_discovery_cancelled'] = {"zh-CN":"已取消部署前只读复核；未连接服务器，也未生成计划。","en":"Deployment preflight was cancelled. The server was not contacted and no plan was created."};
  MESSAGES['extensions.plan_discovery_timeout'] = {"zh-CN":"生成安全计划前的只读复核在限定时间内未完成，已停止本次复核。无需重新确认服务器身份；请检查 SSH 或 Docker 响应后再试。","en":"The read-only checks before generating the safety plan did not finish in time and have stopped. You do not need to reconfirm the server identity; check SSH or Docker responsiveness before trying again."};
  MESSAGES['extensions.guide_step2_planning'] = {"zh-CN":"正在计算安装方式、端口和隔离范围。","en":"Calculating the installation method, ports, and isolation boundaries."};
  MESSAGES['extensions.guide_step2_wait_plan'] = {"zh-CN":"请稍等，计划生成后不会自动部署。","en":"Wait briefly; generating a plan does not deploy automatically."};
  MESSAGES['extensions.guide_step2_plan_after'] = {"zh-CN":"计划生成后，你还要亲自确认才会开始安装。","en":"You must still confirm before installation starts."};
  MESSAGES['extensions.guide_step2_plan_ready'] = {"zh-CN":"安全计划已经生成，尚未改动 VPS。","en":"The safety plan is ready and the VPS has not been changed."};
  MESSAGES['extensions.guide_step2_confirm'] = {"zh-CN":"核对计划后，明确确认开始部署。","en":"Review the plan, then explicitly confirm deployment."};
  MESSAGES['extensions.guide_step2_confirm_after'] = {"zh-CN":"部署期间会显示进度；失败时只给出一个恢复动作。","en":"Progress will be shown, with one recovery action if it fails."};
  MESSAGES['extensions.deploy_confirm_prompt'] = {"zh-CN":"即将按当前安全计划修改这台隔离开发机并开始部署。请确认镜像、实例名称和端口均无误。现在开始部署吗？","en":"This will modify the isolated development server according to the current safety plan and begin deployment. Confirm that the image, instance name, and port are correct. Start deployment now?"};
  MESSAGES['extensions.deploy_confirm_kicker'] = {"zh-CN":"最后一步","en":"Final step"};
  MESSAGES['extensions.deploy_confirm_title'] = {"zh-CN":"确认开始隔离部署","en":"Confirm isolated deployment"};
  MESSAGES['extensions.deploy_confirm_body'] = {"zh-CN":"确认后才会在已保存的隔离开发机上创建新实例；现有服务和生产实例不会被修改。","en":"Only after confirmation will a new instance be created on the saved development machine; existing services and the production instance will not be modified."};
  MESSAGES['extensions.deploy_confirm_continue'] = {"zh-CN":"确认并开始部署","en":"Confirm and start deployment"};
  MESSAGES['extensions.deploy_confirm_cancelled'] = {"zh-CN":"已取消部署确认；安全计划仍保留，VPS 未被修改。","en":"Deployment confirmation was cancelled. The safety plan is still available and the VPS was not changed."};
  MESSAGES['extensions.guide_step2_deploying'] = {"zh-CN":"应用正在部署，重复点击已被锁定。","en":"The service is deploying and duplicate clicks are locked."};
  MESSAGES['extensions.guide_step2_wait_deploy'] = {"zh-CN":"请保持页面打开，等待任务完成。","en":"Keep this page open and wait for the task to finish."};
  MESSAGES['extensions.guide_step2_deploy_after'] = {"zh-CN":"部署完成后先交付登录信息，再继续配置私网。","en":"After deployment, save the login details and continue to private networking."};
  MESSAGES['extensions.guide_step2_deploy_failed'] = {"zh-CN":"这次部署没有完成，现有服务不会自动重放。","en":"This deployment did not finish and will not replay automatically."};
  MESSAGES['extensions.guide_step2_recover'] = {"zh-CN":"按失败提示重新生成安全计划。","en":"Regenerate the safety plan using the failure guidance."};
  MESSAGES['extensions.guide_step2_recover_credential'] = {"zh-CN":"远程任务已结束，临时 SSH 凭据已清除；请重新输入后再安全重试。","en":"The remote task ended and temporary SSH credentials were cleared; enter them again before a safe retry."};
  MESSAGES['extensions.guide_step2_recover_after'] = {"zh-CN":"重新确认前不会再次修改 VPS。","en":"The VPS will not be changed again until you reconfirm."};
  MESSAGES['extensions.guide_step2_confirmation_failed'] = {"zh-CN":"安全计划确认未通过。VPS 未被修改；无任务已创建。","en":"Safety-plan confirmation was blocked. The VPS was not changed and no task was created."};
  MESSAGES['extensions.guide_step2_confirmation_recover'] = {"zh-CN":"根据上方安全原因重新生成计划。","en":"Regenerate the plan using the safe reason shown above."};
  MESSAGES['extensions.guide_step2_confirmation_after'] = {"zh-CN":"重新确认前不会部署，也不会自动重试。","en":"Nothing will deploy or retry automatically before you reconfirm."};
  MESSAGES['extensions.regenerate_safe_plan'] = {"zh-CN":"重新生成安全计划","en":"Regenerate safety plan"};
  MESSAGES['extensions.deploy_plan_service_port_changed'] = {"zh-CN":"服务端口与已确认的安全计划不一致。","en":"The service port does not match the confirmed safety plan."};
  MESSAGES['extensions.deploy_plan_image_changed'] = {"zh-CN":"容器镜像与已确认的安全计划不一致。","en":"The container image does not match the confirmed safety plan."};
  MESSAGES['extensions.deploy_plan_identity_changed'] = {"zh-CN":"VPS 连接身份与已确认的安全计划不一致。","en":"The VPS connection identity does not match the confirmed safety plan."};
  MESSAGES['extensions.deploy_confirmation_safe_notice'] = {"zh-CN":"VPS 未被修改；无任务已创建。","en":"The VPS was not changed and no task was created."};
  MESSAGES['extensions.deploy_task_reconcile_pending'] = {"zh-CN":"部署响应未能确认。请勿再次部署；GenBox 正在核对已有任务状态。","en":"The deployment response could not be confirmed. Do not deploy again; GenBox is reconciling the existing task state."};
  MESSAGES['extensions.deploy_attempt_unavailable'] = {"zh-CN":"浏览器无法生成安全的部署尝试标识，已停止提交。请更新浏览器后重试。","en":"The browser could not generate a secure deployment attempt ID, so submission was stopped. Update the browser and try again."};
  MESSAGES['extensions.deploy_plan_unavailable'] = {"zh-CN":"已确认的部署计划不存在或已过期，请重新生成安全计划。","en":"The confirmed deployment plan is missing or expired. Generate a new safety plan."};
  MESSAGES['extensions.deploy_snapshot_changed'] = {"zh-CN":"确认计划后 VPS 环境已变化，请重新检测环境后再生成计划。","en":"The VPS environment changed after plan confirmation. Run discovery again before creating a new plan."};
  MESSAGES['extensions.deploy_resource_conflict'] = {"zh-CN":"另一个部署正在占用相同资源。请先查看任务状态，再重载页面后重新规划。","en":"Another deployment currently owns the same resources. Check task status, then reload before planning again."};
  MESSAGES['extensions.deploy_task_reconcile_manual'] = {"zh-CN":"GenBox 多次检查后仍无法确认部署任务。请勿再次部署；请重载页面并人工查看任务状态。","en":"GenBox could not confirm the deployment task after several checks. Do not deploy again; reload and check task status manually."};
  MESSAGES['extensions.guide_step2_manual_check'] = {"zh-CN":"部署任务状态仍未确认。","en":"The deployment task status is still unconfirmed."};
  MESSAGES['extensions.guide_step2_manual_reload'] = {"zh-CN":"请重载页面并查看已有任务，不要再次提交部署。","en":"Reload and inspect existing tasks; do not submit deployment again."};
  MESSAGES['extensions.guide_step2_manual_after'] = {"zh-CN":"确认任务状态后再决定后续恢复。","en":"Confirm task status before choosing the next recovery step."};
  MESSAGES['extensions.deploy_attempt_conflict'] = {"zh-CN":"部署尝试标识与另一份已确认上下文冲突，已拒绝继续。请重新生成计划后再确认。","en":"The deployment attempt ID conflicts with another confirmed context. The request was rejected; create a new plan before confirming again."};
  MESSAGES['extensions.deploy_identity_reconfirm_notice'] = {"zh-CN":"请返回 VPS 信息，核对已保存的目标与主机身份，重新输入凭据并再次验证 SSH，然后再创建新计划。","en":"Return to VPS information, review the saved target and host identity, re-enter credentials, and verify SSH again before creating a new plan."};
  MESSAGES['extensions.prepare_local_network'] = {"zh-CN":"准备本机网络","en":"Prepare local network"};
  MESSAGES['extensions.guide_step3_title'] = {"zh-CN":"准备这台电脑的 Tailscale","en":"Prepare Tailscale on this computer"};
  MESSAGES['extensions.guide_step3_checking'] = {"zh-CN":"正在读取本机状态。","en":"Checking local status."};
  MESSAGES['extensions.guide_step3_wait'] = {"zh-CN":"等待检测结果，必要时可重新检测。","en":"Wait for the result or check again."};
  MESSAGES['extensions.guide_step3_missing'] = {"zh-CN":"这台电脑还没有安装 Tailscale。","en":"Tailscale is not installed on this computer."};
  MESSAGES['extensions.guide_step3_install'] = {"zh-CN":"点击安装，按 Windows 提示完成。","en":"Install it and follow the Windows prompt."};
  MESSAGES['extensions.guide_step3_installed'] = {"zh-CN":"Tailscale 已安装，但还没有登录。","en":"Tailscale is installed but not signed in."};
  MESSAGES['extensions.guide_step3_login'] = {"zh-CN":"打开官方登录，并使用你的 Tailscale 账号登录。","en":"Open the official sign-in and use your Tailscale account."};
  MESSAGES['extensions.guide_step3_online'] = {"zh-CN":"本机已经加入 Tailnet。","en":"This computer has joined the Tailnet."};
  MESSAGES['extensions.guide_step3_serve'] = {"zh-CN":"启用 GenBox 私网入口。","en":"Enable the private GenBox entry."};
  MESSAGES['extensions.guide_step3_ready'] = {"zh-CN":"本机 Tailscale 和 GenBox 私网入口都已准备好。","en":"Local Tailscale and the private GenBox entry are ready."};
  MESSAGES['extensions.guide_step3_next'] = {"zh-CN":"让 VPS 自动连接并测试。","en":"Let the VPS connect and test automatically."};
  MESSAGES['extensions.guide_step3_next_after'] = {"zh-CN":"自动检查 VPS、两端互通和 GenBox 访问。","en":"Check the VPS, peer reachability, and GenBox access."};
  MESSAGES['extensions.guide_step3_after'] = {"zh-CN":"本机准备好后，再处理 VPS，不会混在一起。","en":"Finish the local side before handling the VPS."};
  MESSAGES['extensions.connect_and_test'] = {"zh-CN":"连接并自动测试","en":"Connect and test"};
  MESSAGES['extensions.guide_step4_title'] = {"zh-CN":"连接 VPS 并自动测试","en":"Connect the VPS and test automatically"};
  MESSAGES['extensions.guide_step4_host_missing'] = {"zh-CN":"还没有确认这台 VPS 的公开身份。","en":"This VPS identity is not confirmed yet."};
  MESSAGES['extensions.guide_step4_return_host'] = {"zh-CN":"返回步骤 1，独立核对主机密钥算法和完整指纹。","en":"Return to Step 1 and independently verify the host-key algorithm and full fingerprint."};
  MESSAGES['extensions.guide_step4_return_after'] = {"zh-CN":"确认后仍会按顺序完成部署与本机网络准备，不会跳过步骤 2 或 3。","en":"After confirmation, deployment and local network setup still continue in order; Steps 2 and 3 are not skipped."};
  MESSAGES['extensions.guide_step4_read_host'] = {"zh-CN":"读取主机指纹。此操作不验证密码。","en":"Read the host key without testing credentials."};
  MESSAGES['extensions.guide_step4_confirm_host'] = {"zh-CN":"核对页面显示的主机指纹并确认。","en":"Review and confirm the displayed host key."};
  MESSAGES['extensions.guide_step4_host_ready'] = {"zh-CN":"VPS 身份已确认。","en":"The VPS identity is confirmed."};
  MESSAGES['extensions.guide_step4_credential'] = {"zh-CN":"输入本次 SSH 凭证，再回到这里继续。","en":"Enter a session SSH credential, then continue here."};
  MESSAGES['extensions.guide_step4_ready'] = {"zh-CN":"本机、VPS 身份和本次 SSH 凭证都已准备好。","en":"The local side, VPS identity, and session credential are ready."};
  MESSAGES['extensions.guide_step4_start'] = {"zh-CN":"点击一次，GenBox 会按顺序自动检查。","en":"Click once and GenBox will run the checks in order."};
  MESSAGES['extensions.guide_step4_running'] = {"zh-CN":"自动检查正在进行。","en":"Automatic checks are running."};
  MESSAGES['extensions.guide_step4_wait'] = {"zh-CN":"不用重复点击，等待当前检查完成。","en":"Do not click again; wait for the current check."};
  MESSAGES['extensions.guide_step4_failed'] = {"zh-CN":"已经定位到没有完成的具体环节。","en":"GenBox identified the exact unfinished stage."};
  MESSAGES['extensions.guide_step4_retry'] = {"zh-CN":"按黄色提示处理后，点击一次重新检测。","en":"Follow the recovery hint, then check once again."};
  MESSAGES['extensions.guide_step4_complete'] = {"zh-CN":"VPS 到 GenBox 的私网访问已经通过。","en":"Private access from the VPS to GenBox passed."};
  MESSAGES['extensions.guide_step4_done'] = {"zh-CN":"进入完成页查看最终地址。","en":"Open the finish page to view the final address."};
  MESSAGES['extensions.guide_step4_complete_after'] = {"zh-CN":"保存可供后续 Push 使用的私网地址。","en":"Save the private URL for later Push use."};
  MESSAGES['extensions.guide_step4_after'] = {"zh-CN":"依次验证 VPS Tailscale、设备互通和 GenBox 页面。","en":"Verify VPS Tailscale, peer reachability, and GenBox access in order."};
  MESSAGES['extensions.guide_step5_title'] = {"zh-CN":"连接已经完成","en":"Connection complete"};
  MESSAGES['extensions.guide_step5_found'] = {"zh-CN":"服务、VPS 和私网地址都已确认。","en":"The service, VPS, and private URL are confirmed."};
  MESSAGES['extensions.guide_step5_action'] = {"zh-CN":"查看最终地址和后续操作。","en":"Review the final URL and next actions."};
  MESSAGES['extensions.guide_step5_after'] = {"zh-CN":"可以进入下一阶段的图片 Push 联调。","en":"You can proceed to image Push integration."};
  MESSAGES['extensions.guide_step5_delivery_title'] = {"zh-CN":"应用已装好，私网还没完成","en":"Service installed; private networking is still pending"};
  MESSAGES['extensions.guide_step5_delivery_found'] = {"zh-CN":"登录地址和一次性管理密钥已经交付。","en":"The login URL and one-time admin key are ready."};
  MESSAGES['extensions.guide_step5_delivery_action'] = {"zh-CN":"先复制或保存登录信息，再继续准备本机网络。","en":"Copy or save the login details, then prepare local networking."};
  MESSAGES['extensions.guide_step5_delivery_after'] = {"zh-CN":"只有 VPS 能通过私网访问 GenBox 后，才会显示真正完成。","en":"Completion appears only after the VPS reaches GenBox over the private network."};
  MESSAGES['extensions.deploy_complete_save_key_then_network'] = {"zh-CN":"应用部署完成。请先保存本页的一次性登录信息，然后点击上方按钮继续配置私网。","en":"Deployment complete. Save the one-time login details, then use the guide above to continue private networking."};
  MESSAGES['extensions.guide_finish'] = {"zh-CN":"已完成","en":"Finished"};
  MESSAGES['extensions.recovery_title'] = {"zh-CN":"这一步没有完成","en":"This step did not finish"};
  MESSAGES['extensions.network_failed_plain'] = {"zh-CN":"自动检查没有全部通过，请按页面上的一条恢复提示处理。","en":"The automatic checks did not all pass. Follow the single recovery hint shown."};
  MESSAGES['extensions.network_diag_command_failed'] = {"zh-CN":"检测命令没有正常返回；通常是 VPS 上 Tailscale 服务或命令不可用。","en":"The status command failed; Tailscale may not be available on the VPS."};
  MESSAGES['extensions.network_diag_no_output'] = {"zh-CN":"VPS 没有返回 Tailscale 状态，建议先确认服务正在运行。","en":"The VPS returned no Tailscale status; confirm the service is running."};
  MESSAGES['extensions.network_diag_json_shape'] = {"zh-CN":"VPS 返回了非标准状态格式，GenBox 没有读取原始内容。","en":"The VPS returned an unexpected status shape; raw content was not retained."};
  MESSAGES['extensions.network_diag_needs_login'] = {"zh-CN":"VPS 的 Tailscale 已安装，但还没有登录或加入 Tailnet。","en":"Tailscale is installed on the VPS but has not joined the Tailnet."};
  MESSAGES['extensions.network_diag_starting'] = {"zh-CN":"VPS 的 Tailscale 仍在启动，稍后可重新检测。","en":"Tailscale is still starting on the VPS; check again shortly."};
  MESSAGES['extensions.network_diag_stopped'] = {"zh-CN":"VPS 的 Tailscale 当前已停止。","en":"Tailscale is stopped on the VPS."};
  MESSAGES['extensions.network_diag_state_unknown'] = {"zh-CN":"VPS 的 Tailscale 没有进入可用状态。","en":"Tailscale on the VPS is not in a usable state."};
  MESSAGES['extensions.network_diag_no_ipv4'] = {"zh-CN":"Tailscale 正在运行，但 VPS 尚未获得私网 IPv4 地址。","en":"Tailscale is running, but the VPS has no private IPv4 address yet."};
  MESSAGES['extensions.network_diag_many_ipv4'] = {"zh-CN":"VPS 返回了多个候选私网地址，需要先整理 Tailscale 状态。","en":"The VPS returned multiple candidate private addresses."};
  MESSAGES['extensions.network_diag_retryable'] = {"zh-CN":"状态看起来正常，可按恢复提示重新检测。","en":"The status looks usable; follow the recovery hint and check again."};
  MESSAGES['extensions.network_diag_magicdns'] = {"zh-CN":"私网已连通，但 VPS 解析不了这台电脑的 Tailscale 名称。请确认 Tailnet 已开启 MagicDNS。","en":"The private network is connected, but the VPS cannot resolve this computer's Tailscale name. Confirm MagicDNS is enabled."};
  MESSAGES['extensions.network_diag_entry_refused'] = {"zh-CN":"VPS 已到达这台电脑，但私网入口端口没有接受连接。请重新检查本机私网入口。","en":"The VPS reached this computer, but the private entry port refused the connection. Recheck the local private entry."};
  MESSAGES['extensions.network_diag_http_error'] = {"zh-CN":"VPS 已连到私网入口，但入口返回了 HTTP 错误。通常是访问地址或 Tailscale Serve 映射不一致。","en":"The VPS reached the private entry, but it returned an HTTP error. The address or Tailscale Serve mapping may not match."};
  MESSAGES['extensions.network_diag_probe_timeout'] = {"zh-CN":"VPS 访问 GenBox 私网入口超时。请检查 Tailnet 访问规则和两台设备在线状态。","en":"The VPS timed out while reaching the private GenBox entry. Check Tailnet access rules and both devices' status."};
  MESSAGES['extensions.network_diag_invalid_genbox_response'] = {"zh-CN":"VPS 打开了目标地址，但返回的不是 GenBox 状态接口。请确认私网入口指向当前 GenBox 端口。","en":"The VPS opened the target, but the response was not the GenBox status endpoint. Confirm the private entry targets the current GenBox port."};

  function readStoredLanguage() {
    try {
      if (global.location && typeof global.location.search === 'string') {
        var params = new URLSearchParams(global.location.search);
        var queryLang = params.get('lang');
        if (queryLang === 'en' || queryLang === 'zh-CN') return queryLang;
      }
    } catch (error) {}
    try {
      if (global.localStorage) {
        var stored = global.localStorage.getItem('igs_language');
        if (stored === 'en' || stored === 'zh-CN') return stored;
      }
    } catch (error2) {}
    if (global.__genboxLanguage === 'en' || global.__genboxLanguage === 'zh-CN') return global.__genboxLanguage;
    if (global.document && global.document.documentElement) {
      var htmlLang = global.document.documentElement.lang;
      if (htmlLang === 'en' || htmlLang === 'zh-CN') return htmlLang;
    }
    return 'zh-CN';
  }

  function language() {
    return readStoredLanguage();
  }

  function interpolate(value, params) {
    return String(value).replace(/\{([A-Za-z0-9_]+)\}/g, function (_, name) {
      return params && params[name] !== undefined ? String(params[name]) : '';
    });
  }

  function t(key, params) {
    var entry = MESSAGES[key];
    if (!entry) {
      if (global.console) global.console.warn('[i18n] Missing translation key:', key);
      return key;
    }
    return interpolate(entry[language()] || entry['zh-CN'] || key, params);
  }

  function apply(root) {
    var scope = root || global.document;
    if (!scope || !scope.querySelectorAll) return;
    var nodes = [];
    if (scope.nodeType === 1 && scope.hasAttribute('data-i18n')) nodes.push(scope);
    Array.prototype.push.apply(nodes, scope.querySelectorAll('[data-i18n]'));
    nodes.forEach(function (node) { node.textContent = t(node.getAttribute('data-i18n')); });
    ['title', 'placeholder', 'aria-label'].forEach(function (attribute) {
      var marker = 'data-i18n-' + attribute;
      var marked = [];
      if (scope.nodeType === 1 && scope.hasAttribute(marker)) marked.push(scope);
      Array.prototype.push.apply(marked, scope.querySelectorAll('[' + marker + ']'));
      marked.forEach(function (node) { node.setAttribute(attribute, t(node.getAttribute(marker))); });
    });
  }

  function setLanguage(value) {
    var next = value === 'en' ? 'en' : 'zh-CN';
    global.__genboxLanguage = next;
    if (global.document && global.document.documentElement) global.document.documentElement.lang = next;
    try {
      if (global.localStorage) global.localStorage.setItem('igs_language', next);
    } catch (error) {}
    apply(global.document && global.document.body ? global.document.body : global.document);
    try {
      if (global.location && global.location.href && global.location.replace) {
        var url = new URL(global.location.href);
        url.searchParams.set('lang', next);
        global.location.replace(url.toString());
        return;
      }
    } catch (urlError) {}
    if (global.location && global.location.reload) global.location.reload();
  }

  MESSAGES['extensions.plan_review_title'] = {"zh-CN":"请先核对以下部署计划","en":"Review this deployment plan first"};
  MESSAGES['extensions.plan_review_instance'] = {"zh-CN":"实例名称：","en":"Instance:"};
  MESSAGES['extensions.plan_review_port'] = {"zh-CN":"服务端口：","en":"Service port:"};
  MESSAGES['extensions.plan_review_image'] = {"zh-CN":"容器镜像：","en":"Container image:"};
  MESSAGES['extensions.plan_review_method'] = {"zh-CN":"部署方式：","en":"Deployment method:"};
  MESSAGES['extensions.plan_review_scope'] = {"zh-CN":"部署范围：","en":"Deployment scope:"};
  MESSAGES['extensions.plan_review_isolated'] = {"zh-CN":"创建新的隔离实例","en":"Create a new isolated instance"};
  MESSAGES['extensions.plan_review_existing'] = {"zh-CN":"仅登记现有实例","en":"Register the existing instance only"};
  MESSAGES['extensions.plan_review_confirm'] = {"zh-CN":"核对无误后，仍需点击“确认并部署”才会执行。","en":"Nothing runs until you select Confirm and deploy."};
  MESSAGES['extensions.update_image'] = {"zh-CN":"更新镜像","en":"Update image"};
  MESSAGES['extensions.update_image_title'] = {"zh-CN":"更新隔离实例镜像","en":"Update isolated instance image"};
  MESSAGES['extensions.update_image_warning'] = {"zh-CN":"只会更新已登记的隔离开发实例。镜像必须使用不可变的 @sha256 摘要；生产实例不会出现在这里。","en":"Only the registered isolated development instance can be updated. Use an immutable @sha256 digest; production instances are excluded."};
  MESSAGES['extensions.update_image_digest'] = {"zh-CN":"新镜像摘要地址","en":"New image digest"};
  MESSAGES['extensions.image_source_placeholder'] = {"zh-CN":"registry.example/chatgpt2api@sha256:...","en":"registry.example/chatgpt2api@sha256:..."};
  MESSAGES['extensions.review_update'] = {"zh-CN":"生成核对清单","en":"Review update"};
  MESSAGES['extensions.confirm_update'] = {"zh-CN":"确认更新","en":"Confirm update"};
  MESSAGES['extensions.update_image_plan_ready'] = {"zh-CN":"核对清单：拉取不可变镜像、备份配置、重建应用、检查健康；失败会回滚。","en":"Review: pull immutable image, back up configuration, recreate the app, and verify health; failures roll back."};
  MESSAGES['extensions.update_image_started'] = {"zh-CN":"正在更新隔离实例镜像，请稍候…","en":"Updating the isolated instance image…"};
  MESSAGES['extensions.update_image_success'] = {"zh-CN":"镜像更新完成，健康检查已通过。","en":"Image updated and health check passed."};
  MESSAGES['extensions.update_image_failed'] = {"zh-CN":"镜像更新未完成，原实例配置已保留或回滚。","en":"Image update did not complete; the original configuration was preserved or rolled back."};
  MESSAGES['extensions.update_image_unavailable'] = {"zh-CN":"请先解锁本机凭证库并保存该实例的 SSH 凭证。","en":"Unlock the local credential vault and save SSH credentials for this instance first."};
  MESSAGES['extensions.push_save_to_vault'] = {"zh-CN":"保存到本机凭证库","en":"Save to local credential vault"};
  MESSAGES['extensions.push_key_not_available'] = {"zh-CN":"当前没有可保存的新 Push 密钥。请先创建或轮换密钥；如需保留现有密钥，请从 chatgpt2api 重新配置。","en":"There is no new Push key available to save. Create or rotate a key first; to keep the existing key, retrieve it from chatgpt2api."};
  MESSAGES['extensions.push_key_ready_to_save'] = {"zh-CN":"新 Push 密钥仅在本次创建或轮换后可见。请先复制配置，再勾选本地保存并确认。","en":"A new Push key is available from this create or rotation. Copy the configuration, then opt in and confirm local saving."};
  global.GenBoxI18n = { messages: MESSAGES, language: language, t: t, apply: apply, setLanguage: setLanguage };
  global.t = t;
  global.i18nText = t;
})(window);
