
// ═══════════════════════════════════════════════════════════════════
// 全局状态
// ═══════════════════════════════════════════════════════════════════
var allProviders = [];
var selectedProviders = [];
var currentMode = 't2i';
var uploadedImageData = null;
var uploadedImageDataList = [];
var continuousSessionId = null;
var currentResults = {};   // 当前生成结果，用于灯箱/对比
var currentGroupTimings = {}; // 当前分组耗时 {pid: {total, images: []}}
var quickPrompts = {};
var lastGenContext = null; // 上次生图上下文，用于单模型重试

// Precision edit is a separate annotation-reference workflow. It intentionally
// does not reuse the mask-only inpaint state or the general I2I upload state.
var PRECISION_ANNOTATION_CONTRACT = 'genbox-annotation-v3';
var PRECISION_CUTOUT_CONTRACT = 'genbox-cutout-v1';
var PRECISION_CUTOUT_REFINE_CONTRACT = 'genbox-cutout-refine-v1';
var PRECISION_CUTOUT_SELECTION_MASK_CONTRACT = 'genbox-cutout-selection-mask-v1';
var PRECISION_CUTOUT_MODEL_INSTALL_CONTRACT = 'genbox-cutout-model-install-v1';
var PRECISION_CUTOUT_MODEL_SOURCE_ID = 'rembg-u2net-human-seg-v0.0.0';
var PRECISION_CUTOUT_MODEL_RELATIVE_PATH = 'storage/models/cutout/u2net_human_seg.onnx';
var PRECISION_CUTOUT_MODEL_POLL_INTERVAL_MS = 800;
var PRECISION_CUTOUT_CAPABILITY_TIMEOUT_MS = 15000;
var PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE = 'gpt-image-2';
var PRECISION_GPT_IMAGE_2_SIZE_ALIGNMENT = 16;
var PRECISION_GPT_IMAGE_2_MIN_OUTPUT_PIXELS = 655360;
var PRECISION_GPT_IMAGE_2_MAX_OUTPUT_PIXELS = 8294400;
var PRECISION_GPT_IMAGE_2_MAX_SIDE = 3840;
var PRECISION_GPT_IMAGE_2_CANONICAL_PRESETS = {
  '1k': '1024x1024',
  '2k': '2048x1152',
  '4k': '3840x2160'
};
// Preset dimensions are local form helpers. Every entry satisfies the strict
// gpt-image-2 envelope; provider capability authorization is still required.
var PRECISION_GPT_IMAGE_2_TIER_RATIOS = {
  '1k': {
    '1:1': '1024x1024', '16:9': '1168x656', '9:16': '656x1168',
    '4:3': '1024x768', '3:4': '768x1024', '3:2': '1008x672',
    '2:3': '672x1008', '21:9': '1344x576', '9:21': '576x1344'
  },
  '2k': {
    '1:1': '2048x2048', '16:9': '2048x1152', '9:16': '1152x2048',
    '4:3': '2048x1536', '3:4': '1536x2048', '3:2': '2016x1344',
    '2:3': '1344x2016', '21:9': '2544x1088', '9:21': '1088x2544'
  },
  '4k': {
    '1:1': '2880x2880', '16:9': '3840x2160', '9:16': '2160x3840',
    '4:3': '3328x2480', '3:4': '2480x3328', '3:2': '3520x2352',
    '2:3': '2352x3520', '21:9': '3840x1648', '9:21': '1648x3840'
  }
};
var PRECISION_CUTOUT_MAX_FEATHER = 64;
var PRECISION_MAX_OUTPUT_PIXELS = 64 * 1024 * 1024;
var PRECISION_HISTORY_LIMIT = 30;
var precisionEditSourceImageData = null;
var precisionEditSourceImage = null;
var precisionEditSourceWidth = 0;
var precisionEditSourceHeight = 0;
var precisionEditObjects = [];
var precisionEditHistory = [];
var precisionEditRedo = [];
var precisionEditTool = 'select';
var precisionEditSelectedId = null;
var precisionEditDraftObject = null;
var precisionEditPointerId = null;
var precisionEditPointerTarget = null;
var precisionEditPointerFinishing = false;
var precisionEditDragOrigin = null;
var precisionEditDragMoved = false;
var precisionEditGestureCheckpoint = null;
var precisionEditDoubleClickCheckpoint = null;
var PRECISION_DOUBLE_CLICK_ROLLBACK_WINDOW_MS = 1500;
var PRECISION_DOUBLE_CLICK_ROLLBACK_DISTANCE_PX = 8;
var precisionEditAnnotationsVisible = true;
var precisionEditIdCounter = 0;
var precisionEditLabelCounter = 0;
var precisionEditTextDraftPoint = null;
var precisionEditTextEditingId = null;
var precisionAnnotationInstructionPopoverState = {
  selectedId: '',
  dismissedId: '',
  manuallyPositioned: false,
  drag: null,
  // Keep a viewport position per annotation so switching between objects does
  // not force every instruction card back over the image.
  positions: {},
  confirmedIds: {},
  dismissedIds: {}
};
var PRECISION_MODEL_VISIBILITY_STORAGE_KEY = 'genbox_precision_model_visibility_v1';
var PRECISION_MODEL_VISIBILITY_KEY_PATTERN = /^[A-Za-z0-9._:@-]{1,80}::[A-Za-z0-9._:@-]{1,160}$/;
var PRECISION_MODEL_VISIBILITY_FORBIDDEN_PATTERN = /(api[_-]?key|apikey|secret|token|credential|password|bearer|base[_-]?url|prompt|error|userinfo|cookie|authorization)/i;
var precisionEditModelVisibility = {};
var precisionModelVisibilityMenuOpen = false;
var precisionModelVisibilityMenuProviderId = '';
var precisionModelVisibilityDraft = null;
var precisionModelVisibilityDismissBound = false;
var precisionEditSelectedModel = { providerId: '', model: '' };
var precisionEditStrategy = 'standard';
var precisionEditSelectionMode = 'annotation';
var precisionSelectionFeather = 0;
var precisionGuidanceTransitionTimer = null;
var precisionEditSizeMode = 'preserve';
var precisionOutputSizePolicy = 'strict';
var PRECISION_RESIZE_PRESET_STORAGE_KEY = 'genbox_precision_resize_presets_v1';
var PRECISION_RESIZE_PRESET_SCHEMA_VERSION = 1;
var PRECISION_RESIZE_PRESET_LIMIT = 20;
var precisionResizeSavedPresets = [];
var precisionResizePresetIdCounter = 0;
var precisionResizeCapabilityPending = null;
var precisionEditSession = { source: null, versions: [], selectedVersionId: 'original', baseVersionId: 'original', taskBaseVersionId: null, view: 'after', taskId: null };
var precisionWorkflowHistoryState = { items: [], calendarItems: [], selectedWorkflow: null, selectedWorkflowId: '', listRequest: 0, detailRequest: 0, loaded: false, loading: false, filterOpener: null, actionOpener: null };
var precisionComparePointerId = null;
var precisionComparePointerTarget = null;
if (typeof window !== 'undefined' && typeof window.__genboxPrecisionCompareResizeCleanup === 'function') {
  window.__genboxPrecisionCompareResizeCleanup();
}
var precisionCompareResizeCleanup = null;
var precisionImageFullscreenRestore = null;
var PRECISION_FULLSCREEN_EXIT_WAIT_MS = 500;
var precisionVersionLoadToken = 0;
var precisionBaseVersionSwitchPending = false;
var precisionSourceLoadGeneration = 0;
var precisionPendingSourceIntent = null;
var precisionGenerationControlState = 'idle';
var precisionSourceTaskEpoch = 0;
var precisionSourceTaskStatus = 'idle';
var precisionTaskSourceGeneration = 0;
var precisionViewZoom = 100;
var precisionEditPendingInstruction = '';
var precisionEditEraserSnapshot = null;
var precisionEditEraserChanged = false;
var PRECISION_ANNOTATION_MIN_SIZE = 0.004;
var PRECISION_HANDLE_MOUSE_PX = 10;
var PRECISION_HANDLE_TOUCH_PX = 24;
var precisionTaskMonitorData = null;
var precisionTaskMonitorStartedAtMs = 0;
var precisionTaskMonitorElapsedSeconds = null;
var precisionTaskMonitorTerminal = false;
var precisionTaskMonitorTimer = null;
var precisionCanvasResizeState = null;
var precisionCanvasVerticalResizeState = null;
var precisionCanvasVerticalResizeRestore = null;
var precisionAutoBaseVersionTarget = '';
var precisionAutoBaseVersionTimer = null;
var precisionInspectorResizeState = null;
var PRECISION_INSPECTOR_WIDTH_STORAGE_KEY = 'genbox_precision_inspector_width_v1';
// View-only interaction state. These values never enter annotation payloads.
var precisionCanvasPanState = null;
var precisionCanvasSpaceHeld = false;
var precisionEditModelPickerReady = false;
var precisionEditAuthorizationPending = false;
var precisionCutoutCapability = null;
var precisionCutoutPending = false;
var precisionCutoutProbeToken = 0;
var precisionCutoutAvailabilityAbortController = null;
var precisionCutoutOperationToken = 0;
var precisionCutoutAbortController = null;
var precisionCutoutModel = null;
var precisionCutoutModelTask = null;
var precisionCutoutModelRefreshToken = 0;
var precisionCutoutModelTaskToken = 0;
var precisionCutoutModelTaskId = '';
var precisionCutoutModelPollTimer = null;
var precisionCutoutModelMutationPending = false;
var precisionCutoutModelDetailsPreference = null;
var precisionCutoutSelectedAdapter = '';
var precisionCutoutAdapterDetailsExpanded = false;
var precisionCutoutMode = 'simple';
var precisionCutoutProfessionalOpener = null;
var precisionCutoutProfessionalHome = null;
var precisionCutoutProfessionalDockWidth = 410;
var precisionCutoutProfessionalDockCollapsed = false;
var precisionCutoutProfessionalDockResizeState = null;
var precisionCutoutProfessionalDockObserver = null;

// 生图数量: {provider_id: int}
var providerQuantities = {};
function onQtyChange(sel) {
  var v = parseInt(sel.value);
  if (isNaN(v) || v < 1) v = 1;
  if (v > 4) v = 4;
  sel.value = v;
  providerQuantities[sel.dataset.pid] = v;
}

function adjustQty(pid, delta) {
  var input = document.querySelector('.provider-qty[data-pid="' + pid + '"]');
  if (!input) return;
  var v = parseInt(input.value) + delta;
  if (isNaN(v) || v < 1) v = 1;
  if (v > 4) v = 4;
  input.value = v;
  providerQuantities[pid] = v;
}

// 预览区切换状态
var previewImages = [];   // [{pid, src, name, color, seq, fname, realPid}, ...]
var previewIndex = 0;
// 分组预览: { realPid: [previewImage, ...] }
var previewGroups = {};
// 失败分组: { realPid: [{pid, error, seq}, ...] }
var failedGroups = {};
// 占位符状态: { key: { cardEl, imgEl, state } }
var previewPlaceholders = {};
// 持久化分组预览: { realPid: { images: [...], activeIdx: 0, name, color } }
var groupedPreviews = {};

// 灯箱缩放
var lightboxZoom = 1;

// ═══════════════════════════════════════════════════════════════════
// 快捷提示词配置（分类 + 折叠）
// ═══════════════════════════════════════════════════════════════════
var QUICK_PROMPTS = {
  style: [
    {zh: "电影感画面", en: "Cinematic lighting, 21:9 widescreen, 8K HDR, volumetric lighting, film grain"},
    {zh: "赛博朋克城市", en: "Cyberpunk neon city at night, rain reflections, hyper-realistic, Unreal Engine 5"},
    {zh: "商业产品摄影", en: "Studio product photography, white background, soft box lighting, commercial grade"},
    {zh: "油画风格", en: "Oil painting style, classical, Renaissance technique, rich textures"},
    {zh: "水彩插画", en: "Watercolor illustration, soft gradients, delicate brushwork"},
    {zh: "动漫风格", en: "Anime style, vibrant colors, Studio Ghibli inspired, detailed background"},
    {zh: "像素艺术", en: "Pixel art, 16-bit, retro gaming aesthetic, nostalgic"},
    {zh: "低多边形3D", en: "Low-poly 3D render, geometric, clean, minimal design"}
  ],
  oriental: [
    {zh: "仙侠古风", en: "Xianxia fantasy, ethereal beauty in flowing hanfu, ice lotus glow cyan light, cinematic"},
    {zh: "大唐宫廷", en: "Tang dynasty palace scene, silk robes, traditional architecture, golden hour light"},
    {zh: "水墨山水", en: "Ancient Chinese landscape painting style, mountains and mist, ink wash"},
    {zh: "清朝宫廷", en: "Qing Dynasty court portrait, ornate costumes, detailed embroidery"},
    {zh: "古风战士", en: "Fantasy warrior in ancient Chinese armor, dramatic pose, epic battle scene"}
  ],
  nature: [
    {zh: "日出山景", en: "Misty mountain landscape at sunrise, golden light, aerial drone view"},
    {zh: "热带海滩日落", en: "Tropical beach at sunset, palm trees, crystal clear water, photorealistic"},
    {zh: "樱花满开", en: "Cherry blossom trees in full bloom, traditional Japanese garden, spring"},
    {zh: "极光雪山", en: "Northern lights over snowy mountains, aurora borealis, night sky"},
    {zh: "秋日森林", en: "Autumn forest path, golden leaves, soft overcast lighting, peaceful"}
  ],
  architecture: [
    {zh: "未来城市", en: "Futuristic cityscape, flying vehicles, holographic billboards, night"},
    {zh: "中世纪城堡", en: "Medieval European castle on cliff, storm clouds, dramatic lighting"},
    {zh: "现代极简建筑", en: "Minimalist modern architecture, white concrete, geometric forms, sunlight"},
    {zh: "古代遗迹", en: "Ancient ruins overgrown with vegetation, mysterious atmosphere, moss"},
    {zh: "夜市街景", en: "Bustling Asian night market, street food stalls, warm lantern light"}
  ],
  portrait: [
    {zh: "专业人像摄影", en: "Professional portrait photography, studio lighting, shallow depth of field"},
    {zh: "时尚大片", en: "Fashion editorial, editorial makeup, high-end magazine cover style"},
    {zh: "街拍风格", en: "Candid street photography, natural lighting, urban environment"},
    {zh: "复古胶片", en: "Vintage film photography aesthetic, grain, warm tones, nostalgic"},
    {zh: "精致五官特写", en: "Close-up beauty shot, dramatic eye detail, glossy lips, luxury cosmetics"}
  ],
  scifi: [
    {zh: "飞船驾驶舱", en: "Spaceship interior bridge, holographic displays, alien planet view through windows"},
    {zh: "仿生人", en: "Robot android in futuristic city, chrome reflections, blue hour lighting"},
    {zh: "外星地表", en: "Alien planet surface, bioluminescent flora, twin moons in sky"},
    {zh: "深空站", en: "Deep space station orbiting distant nebula, realistic sci-fi design"},
    {zh: "复古未来主义", en: "Retro-futuristic 1950s sci-fi aesthetic, chrome appliances, atomic age"}
  ]
};

// ═══════════════════════════════════════════════════════════════════
// 初始化
// ═══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', function() {
  startRuntimeHeartbeat();
  loadProviders().then(function(){
    checkSetupWizard();
  });
  renderQuickPrompts();
  loadDashboard();
  checkGlobalUpdate();

  // 拖拽上传 (i2i)
  var zone = document.getElementById('uploadZone');
  if (zone) {
    zone.addEventListener('dragover', function(e){ e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', function(){ zone.classList.remove('dragover'); });
    zone.addEventListener('drop', function(e){
      e.preventDefault();
      zone.classList.remove('dragover');
      var files = Array.prototype.slice.call(e.dataTransfer.files || []);
      if (files.length) setUploadedImages(files);
    });
  }

  // 拖拽上传 (局部重绘)
  var inpaintZone = document.getElementById('inpaintUploadZone');
  if (inpaintZone) {
    inpaintZone.addEventListener('dragover', function(e){ e.preventDefault(); inpaintZone.classList.add('dragover'); });
    inpaintZone.addEventListener('dragleave', function(){ inpaintZone.classList.remove('dragover'); });
    inpaintZone.addEventListener('drop', function(e){
      e.preventDefault();
      inpaintZone.classList.remove('dragover');
      var f = e.dataTransfer.files[0];
      if (f) handleInpaintFile(f);
    });
  }
  initializeInpaintCanvasInteractions();
  ensurePrecisionEditPanel();

  // 快捷提示词搜索
  document.getElementById('quickSearch').addEventListener('input', function() {
    filterQuickPrompts(this.value);
  });

  // 变换强度滑块
  document.getElementById('selStrength').addEventListener('input', function() {
    document.getElementById('strengthVal').textContent = this.value;
  });

  // 模型选择联动
  var selModel = document.getElementById('selModel');
  if (selModel) selModel.addEventListener('change', onImageSettingsModelChange);

  // 放大选项开关
  var chkUpscale = document.getElementById('chkUpscale');
  if (chkUpscale) chkUpscale.addEventListener('change', function() {
    document.getElementById('upscaleOpts').style.display = this.checked ? '' : 'none';
  });

  // ESC 关闭弹窗
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeLightbox();
      closeCompare();
      closeProviderModal();
    }
    // 预览区左右键切换
    if (e.key === 'ArrowLeft' && previewImages.length > 1) previewPrev();
    if (e.key === 'ArrowRight' && previewImages.length > 1) previewNext();
  });
});

// ═══════════════════════════════════════════════════════════════════
// 导航切换
// ═══════════════════════════════════════════════════════════════════
var dockHideTimer=null;
var dockPinned=false;
function readDockPinned(){
  try{return localStorage.getItem('igs_dock_pinned')==='1';}catch(error){return false;}
}
function persistDockPinned(){
  try{localStorage.setItem('igs_dock_pinned',dockPinned?'1':'0');}catch(error){}
}
function updateDockHandle(){
  var handle=document.getElementById('dockRevealHandle');
  if(!handle)return;
  var visible=document.body.classList.contains('dock-revealed')||document.body.classList.contains('dock-pinned');
  handle.setAttribute('aria-expanded',visible?'true':'false');
  handle.setAttribute('aria-label',visible?i18nText('dock.collapse'):i18nText('dock.expand'));
  handle.title=visible?i18nText('dock.collapse'):i18nText('dock.expand');
  var pin=document.getElementById('dockPinButton');
  if(pin){
    var locked=document.body.classList.contains('dock-pinned');
    pin.setAttribute('aria-pressed',locked?'true':'false');
    pin.setAttribute('aria-label',locked?i18nText('dock.unpin'):i18nText('dock.pin'));
    pin.title=locked?i18nText('dock.unpin'):i18nText('dock.pin');
    pin.innerHTML=locked
      ? '<div class="dock-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="10" width="10" height="10" rx="2"/><path d="M9 10V7a3 3 0 0 1 6 0"/></svg></div><div class="dock-dot"></div>'
      : '<div class="dock-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="10" width="10" height="10" rx="2"/><path d="M9 10V7a3 3 0 0 1 6 0v3"/></svg></div><div class="dock-dot"></div>';
  }
}
function revealDock(){
  clearTimeout(dockHideTimer);
  document.body.classList.add('dock-revealed');
  updateDockHandle();
}
function hideDockNow(){
  if(dockPinned)return;
  var dock=document.getElementById('macDock');
  if(dock&&(dock.matches(':hover')||dock.contains(document.activeElement)))return;
  document.body.classList.remove('dock-revealed');
  updateDockHandle();
}
function scheduleDockHide(delay){
  clearTimeout(dockHideTimer);
  dockHideTimer=setTimeout(hideDockNow,typeof delay==='number'?delay:650);
}
function toggleDockReveal(){
  if(!document.body.classList.contains('dock-auto-hide'))return;
  if(document.body.classList.contains('dock-revealed'))scheduleDockHide(120);
  else revealDock();
}
function toggleDockPinned(){
  if(!document.body.classList.contains('dock-auto-hide'))return;
  dockPinned=!dockPinned;
  document.body.classList.toggle('dock-pinned',dockPinned);
  persistDockPinned();
  if(dockPinned)revealDock();
  else scheduleDockHide(120);
  updateDockHandle();
}
function setDockPageMode(name){
  document.body.classList.add('dock-auto-hide');
  dockPinned=readDockPinned();
  document.body.classList.toggle('dock-pinned',dockPinned);
  if(dockPinned)revealDock();
  else scheduleDockHide(180);
  updateDockHandle();
}
function initializeDockAutoHide(){
  var dock=document.getElementById('macDock');
  var zone=document.getElementById('dockRevealZone');
  var handle=document.getElementById('dockRevealHandle');
  if(!dock||dock.dataset.autoHideReady==='yes')return;
  dock.dataset.autoHideReady='yes';
  dockPinned=readDockPinned();
  [zone,handle].forEach(function(target){if(target){target.addEventListener('mouseenter',revealDock);target.addEventListener('focus',revealDock);target.addEventListener('mouseleave',function(){scheduleDockHide(850);});target.addEventListener('blur',function(){scheduleDockHide(450);});}});
  dock.addEventListener('mouseenter',revealDock);
  dock.addEventListener('focusin',revealDock);
  dock.addEventListener('mouseleave',function(){scheduleDockHide(700);});
  dock.addEventListener('focusout',function(){scheduleDockHide(700);});
  var active=document.querySelector('.dock-item.active[data-page]');
  setDockPageMode(active?active.getAttribute('data-page'):'dashboard');
}
var appRouteReady=false;
var appRouteApplying=false;
var lastHandledAppRoute='';
function getVisibleAppPage(){
  var page=document.querySelector('.page-content:not(.hidden)');
  return page&&page.id?page.id.replace(/^page/,'').toLowerCase():'dashboard';
}
function buildAppRoute(page){
  if(page==='generate')return '#/generate/'+(currentMode||'t2i')+'/'+(localStorage.getItem('igs_image_workbench')||'multi');
  if(page==='video')return '#/video/'+(currentVideoMode||'ti2vid')+'/'+(localStorage.getItem('igs_video_workbench')||'multi');
  if(['dashboard','gallery','history','extensions'].indexOf(page)===-1)page='dashboard';
  return '#/'+page;
}
function updateAppRoute(page,replace){
  if(!appRouteReady||appRouteApplying)return;
  var route=buildAppRoute(page||getVisibleAppPage());
  if(location.hash===route){lastHandledAppRoute=route;return;}
  var url=location.pathname+location.search+route;
  if(replace)history.replaceState(null,'',url);
  else history.pushState(null,'',url);
  lastHandledAppRoute=route;
}
function restoreAppRoute(){
  var route=location.hash||'#/dashboard';
  if(route===lastHandledAppRoute)return;
  var parts=route.replace(/^#\/?/,'').split('/').filter(Boolean);
  var page=parts[0]||'dashboard';
  if(['dashboard','generate','video','gallery','history','extensions'].indexOf(page)===-1)page='dashboard';
  appRouteApplying=true;
  if(page==='generate'){
    var imageWorkbench=parts[2]==='single'?'single':parts[2]==='precision'?'precision':'multi';
    setCreatorWorkbenchMode('image',imageWorkbench);
    if(imageWorkbench!=='precision')switchSubTab(['t2i','i2i','inpaint'].indexOf(parts[1])!==-1?parts[1]:'t2i');
  }else if(page==='video'){
    setCreatorWorkbenchMode('video',parts[2]==='single'?'single':'multi');
    switchVideoSubTab(['ti2vid','i2vid','keyframes'].indexOf(parts[1])!==-1?parts[1]:'ti2vid');
  }
  var navIds={dashboard:'navDashboard',generate:'navGen',video:'navVideo',gallery:'navGallery',history:'navHistory',extensions:'navExtensions'};
  switchNav(page,document.getElementById(navIds[page]));
  appRouteApplying=false;
  lastHandledAppRoute=buildAppRoute(page);
  if(location.hash!==lastHandledAppRoute)updateAppRoute(page,true);
}
function initializeAppRouting(){
  appRouteReady=true;
  restoreAppRoute();
  window.addEventListener('hashchange',restoreAppRoute);
  window.addEventListener('popstate',restoreAppRoute);
}
function switchNav(name, el) {
  document.getElementById('pageGenerate').classList.toggle('hidden', name !== 'generate');
  document.getElementById('pageVideo').classList.toggle('hidden', name !== 'video');
  document.getElementById('pageGallery').classList.toggle('hidden', name !== 'gallery');
  document.getElementById('pageHistory').classList.toggle('hidden', name !== 'history');
  document.getElementById('pageDashboard').classList.toggle('hidden', name !== 'dashboard');
  document.getElementById('pageExtensions').classList.toggle('hidden', name !== 'extensions');

  document.querySelectorAll('.nav-item').forEach(function(n){ n.classList.remove('active'); });
  if (el) el.classList.add('active');

  document.querySelectorAll('.dock-item[data-page]').forEach(function(d){ d.classList.remove('active'); });
  var dockTarget = document.querySelector('.dock-item[data-page="' + name + '"]');
  if (dockTarget) dockTarget.classList.add('active');
  setDockPageMode(name);

  if (name === 'gallery') loadGallery();
  if (name === 'history') loadHistory();
  if (name === 'video') loadVideoProviders();
  if (name === 'dashboard') loadDashboard();
  if (name === 'extensions' && window.loadExtensions) window.loadExtensions();
  updateAppRoute(name);
}

window.dockNav = {
  switchPage: function(pageId) {
    var dockItem = document.querySelector('.dock-item[data-page="' + pageId + '"]');
    switchNav(pageId, dockItem);
  },
  currentPage: function() {
    var active = document.querySelector('.dock-item.active[data-page]');
    return active ? active.getAttribute('data-page') : 'dashboard';
  }
};

// ═══════════════════════════════════════════════════════════════════
// 图像设置：宽高比 / 质量 / 数量 / 尺寸联动
// ═══════════════════════════════════════════════════════════════════

// 宽高比 → 尺寸映射（标准 1024 基准）
var RATIO_SIZES = {
  '1:1':      [1024, 1024],
  '2:3':      [832,  1248],
  '3:2':      [1248, 832],
  '3:4':      [896,  1152],
  '4:3':      [1152, 896],
  '9:16':     [768,  1360],
  '16:9':     [1360, 768],   // 电影画幅
  '21:9':     [1536, 656],   // 超宽银幕
  '1:1-2k':   [1536, 1536],
  '16:9-2k':  [2048, 1152],
  '9:16-2k':  [1152, 2048],
  '21:9-2k':  [2544, 1088],  // 近似 21:9，符合 GPT Image 2 的 16px 倍数约束
  '16:9-4k':  [4096, 2304],
  '9:16-4k':  [2304, 4096],
};

function setRatio(el, ratio) {
  // 更新选中状态
  document.querySelectorAll('#ratioGrid .ratio-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  document.getElementById('selRatio').value = ratio;
  var cropToggle = document.getElementById('chkExactRatioCrop');
  if (cropToggle) cropToggle.disabled = ratio.indexOf('21:9') !== 0;

  // 联动尺寸输入框
  if (ratio === 'auto') {
    // auto 模式：保持当前输入值不变
    return;
  }
  var sz = RATIO_SIZES[ratio];
  if (sz) {
    document.getElementById('inputW').value = sz[0];
    document.getElementById('inputH').value = sz[1];
  }
}

function onSizeInput() {
  // 手动输入尺寸时，清除宽高比选中状态（除非恰好匹配某个预设）
  var w = parseInt(document.getElementById('inputW').value) || 1024;
  var h = parseInt(document.getElementById('inputH').value) || 1024;
  var matched = false;
  for (var ratio in RATIO_SIZES) {
    var sz = RATIO_SIZES[ratio];
    if (sz[0] === w && sz[1] === h) {
      // 匹配到预设，高亮对应按钮
      document.querySelectorAll('#ratioGrid .ratio-btn').forEach(function(b){
        b.classList.toggle('active', b.dataset.ratio === ratio);
      });
      document.getElementById('selRatio').value = ratio;
      matched = true;
      break;
    }
  }
  if (!matched) {
    document.querySelectorAll('#ratioGrid .ratio-btn').forEach(function(b){ b.classList.remove('active'); });
    document.getElementById('selRatio').value = '';
  }
}

function setQuality(el, val) {
  document.querySelectorAll('#qualityBtns .quality-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  document.getElementById('selQuality').value = val;
}

function setQty(el, val) {
  document.querySelectorAll('#qtyBtns .qty-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  document.getElementById('selQty').value = val;
}

// 模型选择联动：更新 provider 的 model 字段
// ═══════════════════════════════════════════════════════════════════
// 图像设置：模型切换 + 保存/加载 per-model 设置
// ═══════════════════════════════════════════════════════════════════

// 加载模型下拉列表（含"全局"选项）
function loadModelDropdown() {
  var sel = document.getElementById('selModel');
  var currentVal = sel.value || '_global';
  sel.innerHTML = '';
  // 全局选项
  var optGlobal = document.createElement('option');
  optGlobal.value = '_global';
  optGlobal.textContent = i18nText('creator.global_all');
  sel.appendChild(optGlobal);
  // 收集所有 image provider 的模型（去重 + 过滤非生图模型）
  var models = [];
  for (var i = 0; i < allProviders.length; i++) {
    var p = allProviders[i];
    if (p.type === 'image' && p.enabled !== false) {
      var pModels = (p.models && p.models.length) ? p.models : [p.model || 'default'];
      var filtered = filterModelsByType(pModels, 'image');
      for (var j = 0; j < filtered.length; j++) {
        var m = filtered[j];
        if (models.indexOf(m) < 0) models.push(m);
      }
    }
  }
  for (var k = 0; k < models.length; k++) {
    var opt = document.createElement('option');
    opt.value = models[k];
    opt.textContent = models[k];
    sel.appendChild(opt);
  }
  // 恢复选中值
  sel.value = currentVal;
}

// 切换模型时加载对应设置
function onImageSettingsModelChange() {
  var modelVal = document.getElementById('selModel').value;
  loadImageSettings(modelVal);
}

// 加载指定模型的设置到 UI
function loadImageSettings(modelKey) {
  var all = loadProviderSettings();
  var ps = all[modelKey] || all['_global'] || {};

  // 质量
  var q = ps.quality || '';
  document.querySelectorAll('#qualityBtns .quality-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.val === q);
  });
  document.getElementById('selQuality').value = q;

  // 宽高比
  var ratio = ps.ratio || '1:1';
  document.querySelectorAll('#ratioGrid .ratio-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.ratio === ratio);
  });
  document.getElementById('selRatio').value = ratio;
  var cropToggle = document.getElementById('chkExactRatioCrop');
  if (cropToggle) {
    cropToggle.checked = Boolean(ps.exact_ratio_crop);
    cropToggle.disabled = ratio.indexOf('21:9') !== 0;
  }

  // 尺寸
  if (ratio !== 'auto' && RATIO_SIZES[ratio]) {
    var sz = RATIO_SIZES[ratio];
    document.getElementById('inputW').value = sz[0];
    document.getElementById('inputH').value = sz[1];
  } else if (ps.w && ps.h) {
    document.getElementById('inputW').value = ps.w;
    document.getElementById('inputH').value = ps.h;
  }

  // 数量
  var qty = ps.qty || 1;
  document.querySelectorAll('#qtyBtns .qty-btn').forEach(function(b){
    b.classList.toggle('active', parseInt(b.dataset.val) === qty);
  });
  document.getElementById('selQty').value = qty;
}

// 保存当前模型的设置
function saveImageSettings() {
  var modelKey = document.getElementById('selModel').value || '_global';
  var all = loadProviderSettings();
  all[modelKey] = {
    quality: document.getElementById('selQuality').value || '',
    ratio: document.getElementById('selRatio').value || '1:1',
    w: parseInt(document.getElementById('inputW').value) || 1024,
    h: parseInt(document.getElementById('inputH').value) || 1024,
    qty: parseInt(document.getElementById('selQty').value) || 1,
    exact_ratio_crop: Boolean(document.getElementById('chkExactRatioCrop') && document.getElementById('chkExactRatioCrop').checked),
  };
  try {
    localStorage.setItem('genbox_image_settings', JSON.stringify(all));
    var label = modelKey === '_global' ? i18nText('creator.global') : modelKey;
    var toast = document.getElementById('saveSettingsToast');
    if (toast) {
      toast.textContent = i18nText('creator.saved_prefix') + label + i18nText('creator.saved_suffix');
      toast.classList.remove('hidden');
      setTimeout(function(){ toast.classList.add('hidden'); }, 2500);
    }
    setStatus(i18nText('creator.saved_prefix') + label + i18nText('creator.saved_suffix'));
  } catch(e) {
    var toast2 = document.getElementById('saveSettingsToast');
    if (toast2) {
      toast2.textContent = i18nText('common.save_failed');
      toast2.style.color = '#ef4444';
      toast2.style.background = 'rgba(239,68,68,0.08)';
      toast2.style.borderColor = 'rgba(239,68,68,0.2)';
      toast2.classList.remove('hidden');
      setTimeout(function(){ toast2.classList.add('hidden'); toast2.style.color=''; toast2.style.background=''; toast2.style.borderColor=''; }, 2500);
    }
    setStatus(i18nText('common.save_failed'));
  }
}

// 加载所有设置（从 localStorage）
function loadProviderSettings() {
  try {
    return JSON.parse(localStorage.getItem('genbox_image_settings') || '{}');
  } catch(e) { return {}; }
}

// ═══════════════════════════════════════════════════════════════════
// 子标签: 文生图 / 图生图
// ═══════════════════════════════════════════════════════════════════
function switchSubTab(mode) {
  if (mode === 'variation') mode = 'inpaint';
  if (['t2i', 'i2i', 'precision_edit', 'inpaint'].indexOf(mode) === -1) mode = 't2i';
  var page = document.getElementById('pageGenerate');
  var precisionWorkbench = !!(page && page.classList.contains('precision-workbench'));
  if (mode === 'precision_edit' && !precisionWorkbench) {
    setCreatorWorkbenchMode('image', 'precision');
    return;
  }
  if (mode !== 'precision_edit' && precisionWorkbench) {
    cancelPrecisionQuickStart();
    setCreatorWorkbenchMode('image', 'multi');
    if (mode === 't2i') return;
  }
  ensurePrecisionEditPanel();
  currentMode = mode;
  var generatePage = document.getElementById('pageGenerate');
  if (generatePage) generatePage.classList.toggle('precision-edit-active', mode === 'precision_edit');
  document.getElementById('panelT2I').classList.toggle('hidden', mode !== 't2i');
  document.getElementById('panelI2I').classList.toggle('hidden', mode !== 'i2i');
  document.getElementById('panelVAR').classList.toggle('hidden', mode !== 'inpaint');
  var precisionPanel = document.getElementById('panelPrecisionEdit');
  if (precisionPanel) precisionPanel.classList.toggle('hidden', mode !== 'precision_edit');
  document.getElementById('subTabT2I').classList.toggle('active', mode === 't2i');
  document.getElementById('subTabI2I').classList.toggle('active', mode === 'i2i');
  document.getElementById('subTabVAR').classList.toggle('active', mode === 'inpaint');
  var precisionTab = document.getElementById('subTabPrecisionEdit');
  if (precisionTab) {
    precisionTab.classList.toggle('active', mode === 'precision_edit');
    precisionTab.setAttribute('aria-selected', mode === 'precision_edit' ? 'true' : 'false');
  }
  document.getElementById('strengthGroup').style.display = mode === 'i2i' ? '' : 'none';
  document.getElementById('quickCard').style.display = mode === 't2i' ? '' : 'none';
  mountCreatorGenerateAction(mode);
  updateInpaintAvailability();
  updatePrecisionEditControls();
  hideEnhance();
  if(getVisibleAppPage()==='generate')updateAppRoute('generate');
  if (mode === 'precision_edit') schedulePrecisionQuickStart();
}

// Precision edit needs a larger, stable annotation surface. Keep the normal
// workbench intact and temporarily collapse only its display-only regions.
var precisionFocusState = {
  active: false,
  saved: null,
  previewCollapsed: false,
  taskCollapsed: false,
  previewHasNewResult: false,
  taskHasActivity: false
};

function isPrecisionFocusActive() {
  return precisionFocusState.active;
}

function ensurePrecisionFocusControls() {
  var controls = document.getElementById('precisionFocusControls');
  if (controls) return controls;
  var host = document.querySelector('#pageGenerate .creator-mode-switch');
  if (!host) return null;
  controls = document.createElement('div');
  controls.id = 'precisionFocusControls';
  controls.setAttribute('role', 'group');
  controls.setAttribute('aria-label', i18nText('creator.precision_edit'));
  controls.style.cssText = 'display:none;align-items:center;gap:6px;margin-left:4px;';
  controls.innerHTML = '<button type="button" id="btnPrecisionFocusPreview" class="btn-ghost" onclick="togglePrecisionFocusPreview()"></button>';
  var previewHeader = document.querySelector('#previewPanel .flex.items-center.justify-between');
  if (!previewHeader) return null;
  previewHeader.appendChild(controls);
  return controls;
}

function updatePrecisionFocusControls() {
  var controls = ensurePrecisionFocusControls();
  if (!controls) return;
  controls.style.display = precisionFocusState.active ? 'inline-flex' : 'none';
  if (!precisionFocusState.active) return;
  var preview = document.getElementById('btnPrecisionFocusPreview');
  if (preview) {
    var previewText = i18nText(precisionFocusState.previewCollapsed ? 'creator.precision_focus_show_preview' : 'creator.precision_focus_hide_preview');
    if (precisionFocusState.previewHasNewResult && precisionFocusState.previewCollapsed) previewText += ' · ' + i18nText('creator.precision_focus_result_ready_short');
    preview.textContent = previewText;
    preview.title = previewText;
    preview.setAttribute('aria-expanded', precisionFocusState.previewCollapsed ? 'false' : 'true');
  }
}

function setPrecisionFocusPreviewCollapsed(collapsed) {
  if (!precisionFocusState.active) return;
  var row = document.getElementById('creatorCanvasRow');
  if (!row) return;
  precisionFocusState.previewCollapsed = !!collapsed;
  var center = row.closest('.generate-center');
  if (center) center.classList.toggle('precision-preview-collapsed', !!collapsed);
  if (collapsed) {
    row.style.display = 'none';
    row.setAttribute('aria-hidden', 'true');
  } else {
    row.style.display = precisionFocusState.saved ? precisionFocusState.saved.previewDisplay : '';
    if (precisionFocusState.saved && precisionFocusState.saved.previewAriaHidden === null) row.removeAttribute('aria-hidden');
    else if (precisionFocusState.saved) row.setAttribute('aria-hidden', precisionFocusState.saved.previewAriaHidden);
    precisionFocusState.previewHasNewResult = false;
  }
  updatePrecisionFocusControls();
}

function togglePrecisionFocusPreview() {
  setPrecisionFocusPreviewCollapsed(!precisionFocusState.previewCollapsed);
}

function togglePrecisionFocusTasks() {
  if (!precisionFocusState.active) return;
  showCreatorTaskMonitor(precisionFocusState.taskCollapsed);
}

function notifyPrecisionFocusActivity(kind) {
  if (!precisionFocusState.active) return;
  if (kind === 'preview') {
    precisionFocusState.previewHasNewResult = true;
    if (precisionFocusState.previewCollapsed) setStatus(i18nText('creator.precision_focus_result_ready'));
  } else if (kind === 'task') {
    precisionFocusState.taskHasActivity = true;
  }
  updatePrecisionFocusControls();
}

function setPrecisionFocusMode(enabled) {
  var row = document.getElementById('creatorCanvasRow');
  var monitor = document.getElementById('creatorTaskMonitor');
  if (enabled) {
    if (precisionFocusState.active) {
      updatePrecisionFocusControls();
      return;
    }
    precisionFocusState.active = true;
    precisionFocusState.saved = {
      previewDisplay: row ? row.style.display : '',
      previewAriaHidden: row ? row.getAttribute('aria-hidden') : null,
      taskExpanded: !!(monitor && monitor.classList.contains('expanded'))
    };
    precisionFocusState.previewHasNewResult = false;
    precisionFocusState.taskHasActivity = false;
    setPrecisionFocusPreviewCollapsed(true);
    if (monitor) monitor.classList.add('precision-mode-hidden');
    return;
  }
  if (!precisionFocusState.active) return;
  var saved = precisionFocusState.saved;
  precisionFocusState.active = false;
  var center = row && row.closest('.generate-center');
  if (center) center.classList.remove('precision-preview-collapsed');
  if (row && saved) {
    row.style.display = saved.previewDisplay;
    if (saved.previewAriaHidden === null) row.removeAttribute('aria-hidden');
    else row.setAttribute('aria-hidden', saved.previewAriaHidden);
  }
  if (monitor) monitor.classList.remove('precision-mode-hidden');
  if (saved) showCreatorTaskMonitor(saved.taskExpanded);
  precisionFocusState.saved = null;
  precisionFocusState.previewCollapsed = false;
  precisionFocusState.taskCollapsed = false;
  precisionFocusState.previewHasNewResult = false;
  precisionFocusState.taskHasActivity = false;
  updatePrecisionFocusControls();
}

// ═══════════════════════════════════════════════════════════════════
// Precision edit: annotation-reference canvas (frontend MVP)
// ═══════════════════════════════════════════════════════════════════
function ensurePrecisionEditPanel() {
  var tab = document.getElementById('subTabPrecisionEdit');
  if (tab) {
    tab.onclick = function() { switchSubTab('precision_edit'); };
    tab.setAttribute('aria-controls', 'panelPrecisionEdit');
  }

  var existing = document.getElementById('panelPrecisionEdit');
  if (!existing) return null;
  var inspector = document.getElementById('precisionInspectorResizeHandle');
  inspector = inspector && inspector.parentNode;
  if (inspector && inspector.dataset.precisionSectionsOrdered !== 'true') {
    var sectionOrder = ['#precisionTaskMonitor', '.precision-model-picker', '.precision-edit-actions', '.precision-quick-tools'];
    var sections = sectionOrder.map(function(selector) { return inspector.querySelector(selector); });
    if (sections.every(Boolean)) {
      sections.forEach(function(section) { inspector.appendChild(section); });
      inspector.dataset.precisionSectionsOrdered = 'true';
    }
  }
  ensurePrecisionSessionShowcaseControls();
  var surface = document.getElementById('precisionCanvasSurface');
  if (surface && surface.dataset.precisionFullscreenBound !== 'true') {
    surface.dataset.precisionFullscreenBound = 'true';
    surface.addEventListener('pointerdown', handlePrecisionCanvasSurfacePointerdown, true);
  }
  var canvas = document.getElementById('precisionAnnotationCanvas');
  if (canvas && canvas.dataset.precisionBound !== 'true') {
    canvas.dataset.precisionBound = 'true';
    canvas.addEventListener('pointerdown', beginPrecisionEditPointer);
    canvas.addEventListener('pointermove', continuePrecisionEditPointer);
    canvas.addEventListener('pointerup', endPrecisionEditPointer);
    canvas.addEventListener('pointercancel', endPrecisionEditPointer);
    canvas.addEventListener('lostpointercapture', endPrecisionEditPointer);
    canvas.addEventListener('dblclick', handlePrecisionCanvasDoubleClick);
    canvas.addEventListener('keydown', handlePrecisionEditCanvasKeydown);
    canvas.addEventListener('keyup', handlePrecisionEditCanvasKeyup);
    canvas.addEventListener('blur', resetPrecisionCanvasKeyboardState);
    setPrecisionEditTool(precisionEditTool);
  }
  var precisionShortcutRoot = document.documentElement;
  if (precisionShortcutRoot && !precisionShortcutRoot.dataset.precisionToolShortcutBound) {
    precisionShortcutRoot.dataset.precisionToolShortcutBound = 'true';
    document.addEventListener('keydown', handlePrecisionToolShortcut, true);
  }
  [['precisionToolSelect', 'select'], ['precisionToolEllipse', 'ellipse'], ['precisionToolArrow', 'arrow'], ['precisionToolRect', 'rect'], ['precisionToolBrush', 'brush'], ['precisionToolEraser', 'eraser'], ['precisionToolText', 'text']].forEach(function(binding) {
    var button = document.getElementById(binding[0]);
    if (button && button.dataset.precisionBound !== 'true') {
      button.dataset.precisionBound = 'true';
      button.addEventListener('click', function() { setPrecisionEditTool(binding[1]); });
    }
  });
  var undo = document.getElementById('btnPrecisionUndo');
  var redo = document.getElementById('btnPrecisionRedo');
  var clear = document.getElementById('btnPrecisionClear');
  var visibility = document.getElementById('btnPrecisionToggleAnnotations');
  var upload = document.getElementById('precisionFileInput');
  var cutoutControls = getPrecisionCutoutControls();
  var cutout = cutoutControls.button;
  var cutoutRefine = cutoutControls.refineButton;
  var cutoutCancel = cutoutControls.cancelButton;
  var cutoutFeather = cutoutControls.feather;
  var cutoutUseSelection = cutoutControls.useSelection;
  var cutoutAdapterSelect = cutoutControls.adapterSelect;
  var cutoutCapabilityRefresh = cutoutControls.capabilityRefreshButton;
  var cutoutAdapterDetailsToggle = cutoutControls.adapterDetailsToggle;
  var cutoutModelInstall = cutoutControls.modelInstallButton;
  var cutoutModelDetailsToggle = cutoutControls.modelDetailsToggle;
  var cutoutModelCancel = cutoutControls.modelCancelButton;
  var cutoutModelRetry = cutoutControls.modelRetryButton;
  var cutoutModelRemoveCorrupt = cutoutControls.modelRemoveCorruptButton;
  var cutoutModelDelete = cutoutControls.modelDeleteButton;
  var colorInput = document.getElementById('precisionAnnotationColor');
  var strokeWidth = document.getElementById('precisionStrokeWidth');
  var textSize = document.getElementById('precisionTextSize');
  var textEditor = document.getElementById('precisionTextEditor');
  if (textEditor && textEditor.dataset.precisionFullscreenBound !== 'true') {
    textEditor.dataset.precisionFullscreenBound = 'true';
    textEditor.addEventListener('dblclick', handlePrecisionCanvasDoubleClick);
    textEditor.addEventListener('pointerdown', handlePrecisionTextEditorPointerdown);
    textEditor.addEventListener('pointerup', handlePrecisionTextEditorPointerup);
  }
  bindPrecisionAnnotationInstructionPopover();
  var zoom = document.getElementById('precisionViewZoom');
  var zoomFit = document.getElementById('btnPrecisionZoomFit');
  if (undo && !undo.onclick) undo.onclick = undoPrecisionEdit;
  if (redo && !redo.onclick) redo.onclick = redoPrecisionEdit;
  if (clear && !clear.onclick) clear.onclick = clearPrecisionEdit;
  if (visibility && !visibility.onclick) visibility.onclick = function() { setPrecisionEditAnnotationsVisible(!precisionEditAnnotationsVisible); };
  if (upload && upload.dataset.precisionBound !== 'true') {
    upload.dataset.precisionBound = 'true';
    upload.addEventListener('change', loadPrecisionEditLocalFile);
    upload.addEventListener('cancel', function() { precisionPendingSourceIntent = null; });
  }
  if (cutout && cutout.dataset.precisionBound !== 'true') {
    cutout.dataset.precisionBound = 'true';
    cutout.addEventListener('click', startPrecisionCutout);
  }
  if (cutoutControls.simpleButton && cutoutControls.simpleButton.dataset.precisionBound !== 'true') {
    cutoutControls.simpleButton.dataset.precisionBound = 'true';
    cutoutControls.simpleButton.addEventListener('click', startPrecisionCutout);
  }
  if (cutoutControls.professionalRunButton && cutoutControls.professionalRunButton.dataset.precisionBound !== 'true') {
    cutoutControls.professionalRunButton.dataset.precisionBound = 'true';
    cutoutControls.professionalRunButton.addEventListener('click', startPrecisionCutout);
  }
  if (cutoutControls.simpleModeButton && cutoutControls.simpleModeButton.dataset.precisionBound !== 'true') {
    cutoutControls.simpleModeButton.dataset.precisionBound = 'true';
    cutoutControls.simpleModeButton.addEventListener('click', function() { setPrecisionCutoutMode('simple'); });
  }
  if (cutoutControls.professionalModeButton && cutoutControls.professionalModeButton.dataset.precisionBound !== 'true') {
    cutoutControls.professionalModeButton.dataset.precisionBound = 'true';
    cutoutControls.professionalModeButton.addEventListener('click', openPrecisionCutoutProfessionalDialog);
  }
  if (cutoutControls.professionalOpenButton && cutoutControls.professionalOpenButton.dataset.precisionBound !== 'true') {
    cutoutControls.professionalOpenButton.dataset.precisionBound = 'true';
    cutoutControls.professionalOpenButton.addEventListener('click', openPrecisionCutoutProfessionalDialog);
  }
  if (cutoutControls.professionalCloseButton && cutoutControls.professionalCloseButton.dataset.precisionBound !== 'true') {
    cutoutControls.professionalCloseButton.dataset.precisionBound = 'true';
    cutoutControls.professionalCloseButton.addEventListener('click', closePrecisionCutoutProfessionalDialog);
  }
  bindPrecisionCutoutProfessionalDock();
  if (cutoutControls.professionalDialog && cutoutControls.professionalDialog.dataset.precisionBound !== 'true') {
    cutoutControls.professionalDialog.dataset.precisionBound = 'true';
    cutoutControls.professionalDialog.addEventListener('keydown', function(event) {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      closePrecisionCutoutProfessionalDialog();
    });
  }
  if (cutoutControls.professionalAlgorithm && cutoutControls.professionalAlgorithm.dataset.precisionBound !== 'true') {
    cutoutControls.professionalAlgorithm.dataset.precisionBound = 'true';
    cutoutControls.professionalAlgorithm.addEventListener('change', function() { setPrecisionCutoutSelectedAdapter(cutoutControls.professionalAlgorithm.value); });
  }
  if (cutoutControls.professionalRefreshButton && cutoutControls.professionalRefreshButton.dataset.precisionBound !== 'true') {
    cutoutControls.professionalRefreshButton.dataset.precisionBound = 'true';
    cutoutControls.professionalRefreshButton.addEventListener('click', refreshPrecisionCutoutSetup);
  }
  if (cutoutControls.professionalFeather && cutoutControls.professionalFeather.dataset.precisionBound !== 'true') {
    cutoutControls.professionalFeather.dataset.precisionBound = 'true';
    cutoutControls.professionalFeather.addEventListener('input', function() { if (cutoutControls.feather) cutoutControls.feather.value = cutoutControls.professionalFeather.value; updatePrecisionCutoutRefineControls(); });
  }
  if (cutoutControls.professionalUseSelection && cutoutControls.professionalUseSelection.dataset.precisionBound !== 'true') {
    cutoutControls.professionalUseSelection.dataset.precisionBound = 'true';
    cutoutControls.professionalUseSelection.addEventListener('change', function() { if (cutoutControls.useSelection) { cutoutControls.useSelection.checked = cutoutControls.professionalUseSelection.checked; if (cutoutControls.useSelection.checked) activatePrecisionCutoutSelection(); } updatePrecisionCutoutRefineControls(); });
  }
  if (cutoutControls.professionalRestoreMode && cutoutControls.professionalRestoreMode.dataset.precisionBound !== 'true') {
    cutoutControls.professionalRestoreMode.dataset.precisionBound = 'true';
    cutoutControls.professionalRestoreMode.addEventListener('change', function() { if (cutoutControls.restoreMode) cutoutControls.restoreMode.checked = cutoutControls.professionalRestoreMode.checked; updatePrecisionCutoutRefineControls(); });
  }
  if (cutoutControls.professionalRestoreMinAlpha && cutoutControls.professionalRestoreMinAlpha.dataset.precisionBound !== 'true') {
    cutoutControls.professionalRestoreMinAlpha.dataset.precisionBound = 'true';
    cutoutControls.professionalRestoreMinAlpha.addEventListener('input', function() { if (cutoutControls.restoreMinAlpha) cutoutControls.restoreMinAlpha.value = cutoutControls.professionalRestoreMinAlpha.value; updatePrecisionCutoutRefineControls(); });
  }
  if (cutoutControls.professionalRefineButton && cutoutControls.professionalRefineButton.dataset.precisionBound !== 'true') {
    cutoutControls.professionalRefineButton.dataset.precisionBound = 'true';
    cutoutControls.professionalRefineButton.addEventListener('click', startPrecisionCutoutRefine);
  }
  if (cutoutRefine && cutoutRefine.dataset.precisionBound !== 'true') {
    cutoutRefine.dataset.precisionBound = 'true';
    cutoutRefine.addEventListener('click', startPrecisionCutoutRefine);
  }
  if (cutoutCancel && cutoutCancel.dataset.precisionBound !== 'true') {
    cutoutCancel.dataset.precisionBound = 'true';
    cutoutCancel.addEventListener('click', cancelPrecisionCutoutOperation);
  }
  if (cutoutFeather && cutoutFeather.dataset.precisionBound !== 'true') {
    cutoutFeather.dataset.precisionBound = 'true';
    cutoutFeather.addEventListener('input', updatePrecisionCutoutRefineControls);
  }
  if (cutoutUseSelection && cutoutUseSelection.dataset.precisionBound !== 'true') {
    cutoutUseSelection.dataset.precisionBound = 'true';
    cutoutUseSelection.addEventListener('change', function() {
      if (cutoutUseSelection.checked) activatePrecisionCutoutSelection();
      updatePrecisionCutoutRefineControls();
    });
  }
  if (cutoutAdapterSelect && cutoutAdapterSelect.dataset.precisionBound !== 'true') {
    cutoutAdapterSelect.dataset.precisionBound = 'true';
    cutoutAdapterSelect.addEventListener('change', function() { setPrecisionCutoutSelectedAdapter(cutoutAdapterSelect.value); });
  }
  if (cutoutCapabilityRefresh && cutoutCapabilityRefresh.dataset.precisionBound !== 'true') {
    cutoutCapabilityRefresh.dataset.precisionBound = 'true';
    cutoutCapabilityRefresh.addEventListener('click', refreshPrecisionCutoutSetup);
  }
  if (cutoutAdapterDetailsToggle && cutoutAdapterDetailsToggle.dataset.precisionBound !== 'true') {
    cutoutAdapterDetailsToggle.dataset.precisionBound = 'true';
    cutoutAdapterDetailsToggle.addEventListener('click', togglePrecisionCutoutAdapterDetails);
  }
  var precisionSelectionFeatherInput = document.getElementById('precisionSelectionFeather');
  if (precisionSelectionFeatherInput && precisionSelectionFeatherInput.dataset.precisionBound !== 'true') {
    precisionSelectionFeatherInput.dataset.precisionBound = 'true';
    precisionSelectionFeatherInput.addEventListener('input', updatePrecisionSelectionFeather);
  }
  var precisionGuidanceCard = document.getElementById('precisionGuidanceCard');
  var precisionGuidanceToggle = document.getElementById('btnPrecisionGuidanceToggle');
  if (precisionGuidanceToggle && precisionGuidanceToggle.dataset.precisionBound !== 'true') {
    precisionGuidanceToggle.dataset.precisionBound = 'true';
    precisionGuidanceToggle.addEventListener('click', togglePrecisionGuidance);
  }
  if (precisionGuidanceCard && precisionGuidanceCard.dataset.precisionEscapeBound !== 'true') {
    precisionGuidanceCard.dataset.precisionEscapeBound = 'true';
    document.addEventListener('keydown', handlePrecisionGuidanceKeydown);
  }
  updatePrecisionGuidanceSummary();
  if (cutoutModelInstall && cutoutModelInstall.dataset.precisionBound !== 'true') {
    cutoutModelInstall.dataset.precisionBound = 'true';
    cutoutModelInstall.addEventListener('click', requestPrecisionCutoutModelInstall);
  }
  if (cutoutModelDetailsToggle && cutoutModelDetailsToggle.dataset.precisionBound !== 'true') {
    cutoutModelDetailsToggle.dataset.precisionBound = 'true';
    cutoutModelDetailsToggle.addEventListener('click', togglePrecisionCutoutModelDetails);
    cutoutModelDetailsToggle.addEventListener('keydown', function(event) {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      togglePrecisionCutoutModelDetails();
    });
  }
  if (cutoutModelCancel && cutoutModelCancel.dataset.precisionBound !== 'true') {
    cutoutModelCancel.dataset.precisionBound = 'true';
    cutoutModelCancel.addEventListener('click', cancelPrecisionCutoutModelDownload);
  }
  if (cutoutModelRetry && cutoutModelRetry.dataset.precisionBound !== 'true') {
    cutoutModelRetry.dataset.precisionBound = 'true';
    cutoutModelRetry.addEventListener('click', retryPrecisionCutoutModelDownload);
  }
  if (cutoutModelRemoveCorrupt && cutoutModelRemoveCorrupt.dataset.precisionBound !== 'true') {
    cutoutModelRemoveCorrupt.dataset.precisionBound = 'true';
    cutoutModelRemoveCorrupt.addEventListener('click', function() { deletePrecisionCutoutModel('corrupt'); });
  }
  if (cutoutModelDelete && cutoutModelDelete.dataset.precisionBound !== 'true') {
    cutoutModelDelete.dataset.precisionBound = 'true';
    cutoutModelDelete.addEventListener('click', function() { deletePrecisionCutoutModel('ready'); });
  }
  var cutoutRestoreMode = cutoutControls.restoreMode;
  if (cutoutRestoreMode && cutoutRestoreMode.dataset.precisionBound !== 'true') {
    cutoutRestoreMode.dataset.precisionBound = 'true';
    cutoutRestoreMode.addEventListener('change', updatePrecisionCutoutRefineControls);
  }
  var cutoutRestoreMinAlpha = cutoutControls.restoreMinAlpha;
  if (cutoutRestoreMinAlpha && cutoutRestoreMinAlpha.dataset.precisionBound !== 'true') {
    cutoutRestoreMinAlpha.dataset.precisionBound = 'true';
    cutoutRestoreMinAlpha.addEventListener('input', updatePrecisionCutoutRefineControls);
  }
  if (colorInput && colorInput.dataset.precisionBound !== 'true') {
    colorInput.dataset.precisionBound = 'true';
    colorInput.addEventListener('input', function() { updatePrecisionSelectedStyle(colorInput, 'color', colorInput.value); });
    colorInput.addEventListener('change', function() { finishPrecisionEditObjectInput(colorInput); });
  }
  if (strokeWidth && strokeWidth.dataset.precisionBound !== 'true') {
    strokeWidth.dataset.precisionBound = 'true';
    strokeWidth.addEventListener('input', function() {
      updatePrecisionStrokeWidthValue();
      updatePrecisionSelectedStyle(strokeWidth, 'strokeWidth', Number(strokeWidth.value) || 5);
    });
    strokeWidth.addEventListener('change', function() { finishPrecisionEditObjectInput(strokeWidth); });
    updatePrecisionStrokeWidthValue();
  }
  if (textSize && textSize.dataset.precisionBound !== 'true') {
    textSize.dataset.precisionBound = 'true';
    textSize.addEventListener('input', function() {
      var output = document.getElementById('precisionTextSizeValue');
      if (output) output.value = output.textContent = String(Math.max(12, Math.min(96, Number(textSize.value) || 24)));
      var selected = precisionEditObjectById(precisionEditSelectedId);
      if (selected && selected.type === 'text') updatePrecisionSelectedStyle(textSize, 'fontSize', Number(textSize.value) || 24);
      renderPrecisionEditCanvas();
    });
    textSize.addEventListener('change', function() { finishPrecisionEditObjectInput(textSize); });
  }
  if (textEditor && textEditor.dataset.precisionBound !== 'true') {
    textEditor.dataset.precisionBound = 'true';
    textEditor.addEventListener('keydown', function(event) {
      if (event.key === 'Enter') { event.preventDefault(); commitPrecisionEditText(); }
      if (event.key === 'Escape') { event.preventDefault(); cancelPrecisionEditText(); }
    });
    textEditor.addEventListener('blur', commitPrecisionEditText);
  }
  if (zoom && zoom.dataset.precisionBound !== 'true') {
    zoom.dataset.precisionBound = 'true';
    zoom.addEventListener('input', function() { setPrecisionViewZoom(zoom.value); });
  }
  if (zoomFit && zoomFit.dataset.precisionBound !== 'true') {
    zoomFit.dataset.precisionBound = 'true';
    zoomFit.addEventListener('click', fitPrecisionCanvasToWindow);
  }
  bindPrecisionResizeControls();
  if (typeof setPrecisionEditStrategy === 'function') setPrecisionEditStrategy(precisionEditStrategy);
  if (typeof setPrecisionEditSelectionMode === 'function') setPrecisionEditSelectionMode(precisionEditSelectionMode);
  bindPrecisionCanvasResizeHandle();
  bindPrecisionCanvasVerticalResizeHandle();
  bindPrecisionInspectorResizeHandle();
  bindPrecisionHelpTooltips();
  bindPrecisionWorkbenchHelp();
  bindPrecisionDocsDialog();
  var sourceMenu = document.getElementById('precisionSourceMenu');
  if (sourceMenu && sourceMenu.dataset.precisionBound !== 'true') {
    sourceMenu.dataset.precisionBound = 'true';
    sourceMenu.addEventListener('keydown', handlePrecisionSourceMenuKeydown);
  }
  var sessionCalendar = document.getElementById('precisionSessionCalendar');
  if (sessionCalendar && sessionCalendar.dataset.precisionBound !== 'true') {
    sessionCalendar.dataset.precisionBound = 'true';
    sessionCalendar.addEventListener('keydown', handlePrecisionSessionCalendarKeydown);
  }
  var workflowCalendar = document.getElementById('precisionWorkflowHistoryCalendar');
  if (workflowCalendar && workflowCalendar.dataset.precisionBound !== 'true') {
    workflowCalendar.dataset.precisionBound = 'true';
    workflowCalendar.addEventListener('keydown', handlePrecisionWorkflowHistoryCalendarKeydown);
  }
  var cutoutModelPanel = cutoutControls.modelPanel;
  if (cutoutModelPanel && cutoutModelPanel.dataset.precisionModelBound !== 'true') {
    cutoutModelPanel.dataset.precisionModelBound = 'true';
    refreshPrecisionCutoutModelStatus();
  }
  var zoomShell = document.getElementById('precisionCanvasShell');
  if (zoomShell && zoomShell.dataset.precisionZoomBound !== 'true') {
    zoomShell.dataset.precisionZoomBound = 'true';
    zoomShell.addEventListener('wheel', function(event) {
      if (!event.shiftKey || !precisionEditSourceImageData) return;
      var target = event.target;
      if (target && target.closest && target.closest('#precisionCanvasResizeHandle, #precisionCanvasVerticalResizeHandle, #precisionAnnotationInstructionPopover, #precisionTextEditor')) {
        if (precisionCanvasResizeState) endPrecisionCanvasResize();
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      if (!precisionCanvasZoomHotspotContains(event, zoomShell)) return;
      event.preventDefault();
      event.stopPropagation();
      setPrecisionViewZoom(precisionViewZoom + (event.deltaY < 0 ? 10 : -10), event);
    }, { passive: false, capture: true });
    zoomShell.addEventListener('mousedown', function(event) {
      if (event.button !== 1 || !precisionEditSourceImageData) return;
      event.preventDefault();
      event.stopPropagation();
      setPrecisionViewZoom(100, { resetScroll: true });
    }, true);
    zoomShell.addEventListener('auxclick', function(event) {
      if (event.button !== 1) return;
      event.preventDefault();
      event.stopPropagation();
    }, true);
  }
  var compareStage = document.getElementById('precisionCompareStage');
  if (compareStage) bindPrecisionCompareEvents(compareStage);
  var fullscreenButton = document.getElementById('btnPrecisionFullscreen');
  if (fullscreenButton && fullscreenButton.dataset.precisionFullscreenBound !== 'true') {
    fullscreenButton.dataset.precisionFullscreenBound = 'true';
    document.addEventListener('fullscreenchange', syncPrecisionFullscreenState);
    document.addEventListener('keydown', handlePrecisionFullscreenKeydown);
  }
  syncPrecisionFullscreenState();
  updatePrecisionEditControls();
  return existing;
}

function precisionCanvasZoomHotspotContains(event, shell) {
  if (!event || !shell || typeof shell.getBoundingClientRect !== 'function') return false;
  var rect = shell.getBoundingClientRect();
  var width = Math.max(1, rect.width || shell.clientWidth || 0);
  var height = Math.max(1, rect.height || shell.clientHeight || 0);
  var hotspotWidth = width * 0.1;
  var hotspotHeight = height * 0.1;
  var left = rect.left + (width - hotspotWidth) / 2;
  var top = rect.top + (height - hotspotHeight) / 2;
  return Number(event.clientX) >= left && Number(event.clientX) <= left + hotspotWidth && Number(event.clientY) >= top && Number(event.clientY) <= top + hotspotHeight;
}

function precisionResizeDimensionKey(width, height) {
  if (typeof width !== 'number' || typeof height !== 'number') return '';
  var numericWidth = width;
  var numericHeight = height;
  if (!Number.isInteger(numericWidth) || !Number.isInteger(numericHeight)) return '';
  if (numericWidth < 64 || numericHeight < 64 || numericWidth > 8192 || numericHeight > 8192) return '';
  if (numericWidth * numericHeight > PRECISION_MAX_OUTPUT_PIXELS) return '';
  return numericWidth + 'x' + numericHeight;
}

function precisionResizeInputDimension(id) {
  var element = document.getElementById(id);
  var raw = element ? String(element.value || '') : '';
  if (!/^[1-9]\d*$/.test(raw)) return null;
  var numeric = Number(raw);
  return Number.isInteger(numeric) ? numeric : null;
}

function precisionResizeTierRatioSize(tier, ratio) {
  var table = PRECISION_GPT_IMAGE_2_TIER_RATIOS[String(tier || '').toLowerCase()];
  var value = table && table[String(ratio || '')];
  return value && precisionGptImage2SizeError(value) === '' ? value : '';
}

function precisionResizeTierRatioForSize(size) {
  var result = { tier: 'custom', ratio: 'custom' };
  Object.keys(PRECISION_GPT_IMAGE_2_TIER_RATIOS).some(function(tier) {
    var table = PRECISION_GPT_IMAGE_2_TIER_RATIOS[tier];
    return Object.keys(table).some(function(ratio) {
      if (table[ratio] !== size) return false;
      result = { tier: tier, ratio: ratio };
      return true;
    });
  });
  return result;
}

function syncPrecisionResizeTierRatioFromSize(size) {
  var match = precisionResizeTierRatioForSize(size);
  var tier = document.getElementById('precisionResizeTier');
  var ratio = document.getElementById('precisionResizeRatio');
  if (tier) tier.value = match.tier;
  if (ratio) ratio.value = match.ratio;
  return match;
}

function applyPrecisionResizeTierRatio() {
  var tier = document.getElementById('precisionResizeTier');
  var ratio = document.getElementById('precisionResizeRatio');
  var tierValue = tier && tier.value;
  var ratioValue = ratio && ratio.value;
  // A partial selection resolves to the neutral 1:1 pair, keeping the two
  // controls coupled instead of silently leaving stale pixel dimensions.
  if (tierValue && tierValue !== 'custom' && (!ratioValue || ratioValue === 'custom')) {
    ratioValue = '1:1';
    if (ratio) ratio.value = ratioValue;
  }
  if (ratioValue && ratioValue !== 'custom' && (!tierValue || tierValue === 'custom')) {
    tierValue = '1k';
    if (tier) tier.value = tierValue;
  }
  var size = precisionResizeTierRatioSize(tierValue, ratioValue);
  if (!size) {
    markPrecisionResizeCustom();
    return '';
  }
  var parts = size.split('x');
  var width = document.getElementById('precisionResizeWidth');
  var height = document.getElementById('precisionResizeHeight');
  if (width) width.value = parts[0];
  if (height) height.value = parts[1];
  var preset = document.getElementById('precisionResizePreset');
  if (preset) {
    var presetValue = getPrecisionOutputSizePolicy() === 'fit_crop' ? 'crop:' + size : size;
    preset.value = presetValue;
  }
  syncPrecisionAspectRatioHint();
  updatePrecisionResizePresetControls();
  updatePrecisionEditControls();
  return size;
}

function precisionResizeDimensions(value, output) {
  if (value === null || value === undefined) return;
  if (typeof value === 'string') {
    var match = /^([1-9]\d{1,4})x([1-9]\d{1,4})$/.exec(value);
    var stringKey = match ? precisionResizeDimensionKey(Number(match[1]), Number(match[2])) : '';
    if (stringKey && stringKey === value) output[stringKey] = true;
    return;
  }
  if (Array.isArray(value)) {
    value.forEach(function(item) { precisionResizeDimensions(item, output); });
  }
}

function precisionCapabilitySizeDeclaration(capability) {
  if (!capability || typeof capability !== 'object' || Array.isArray(capability)) {
    return { present: false, valid: false, sizes: {}, reason: 'precision_size_declaration_missing' };
  }
  var fields = ['supported_sizes', 'supportedSizes', 'sizes', 'dimensions'];
  var presentFields = fields.filter(function(field) {
    return Object.prototype.hasOwnProperty.call(capability, field);
  });
  if (!presentFields.length) return { present: false, valid: false, sizes: {}, reason: 'precision_size_declaration_missing' };
  var canonicalSizes = null;
  for (var fieldIndex = 0; fieldIndex < presentFields.length; fieldIndex += 1) {
    var rawValues = capability[presentFields[fieldIndex]];
    var values = typeof rawValues === 'string' ? [rawValues] : rawValues;
    if (!Array.isArray(values) || !values.length) {
      return { present: true, valid: false, sizes: {}, reason: 'precision_size_declaration_invalid' };
    }
    var sizes = {};
    for (var valueIndex = 0; valueIndex < values.length; valueIndex += 1) {
      if (typeof values[valueIndex] !== 'string') {
        return { present: true, valid: false, sizes: {}, reason: 'precision_size_declaration_invalid' };
      }
      var match = /^([1-9]\d{1,4})x([1-9]\d{1,4})$/.exec(values[valueIndex]);
      var key = match ? precisionResizeDimensionKey(Number(match[1]), Number(match[2])) : '';
      if (!key || key !== values[valueIndex]) {
        return { present: true, valid: false, sizes: {}, reason: 'precision_size_declaration_invalid' };
      }
      sizes[key] = true;
    }
    if (canonicalSizes === null) canonicalSizes = sizes;
    else {
      var canonicalKeys = Object.keys(canonicalSizes).sort();
      var sizeKeys = Object.keys(sizes).sort();
      if (canonicalKeys.length !== sizeKeys.length || canonicalKeys.some(function(key, index) { return key !== sizeKeys[index]; })) {
        return { present: true, valid: false, sizes: {}, reason: 'precision_size_declaration_collision' };
      }
    }
  }
  return { present: true, valid: true, sizes: canonicalSizes || {}, reason: '' };
}

function resolvePrecisionModelCapability(provider, selectedModel) {
  var model = typeof selectedModel === 'string' ? selectedModel : '';
  var capabilities = provider && provider.model_capabilities;
  var invalid = function(reason, canonicalModel, aliasDepth) {
    return {
      selectedModel: model, canonicalModel: canonicalModel || '', capability: null, sizes: {},
      aliasDepth: aliasDepth || 0, structureValid: false, precisionEditConfirmed: false,
      sizeDeclarationPresent: false, sizeDeclarationValid: false, flexibleSizes: false, reason: reason
    };
  };
  if (!model || model !== model.trim() || !capabilities || typeof capabilities !== 'object' || Array.isArray(capabilities)) {
    return invalid('precision_model_unknown');
  }
  if (!Object.prototype.hasOwnProperty.call(capabilities, model)) return invalid('precision_model_unknown');
  var selected = capabilities[model];
  if (!selected || typeof selected !== 'object' || Array.isArray(selected)) return invalid('precision_model_record_invalid');

  function aliasTarget(record) {
    var fields = ['alias_of', 'canonical_model'].filter(function(field) {
      return Object.prototype.hasOwnProperty.call(record, field);
    });
    if (!fields.length) return { target: '', error: '' };
    var targets = [];
    for (var index = 0; index < fields.length; index += 1) {
      var target = record[fields[index]];
      if (typeof target !== 'string' || !target || target !== target.trim()) return { target: '', error: 'precision_alias_target_invalid' };
      targets.push(target);
    }
    if (targets.some(function(target) { return target !== targets[0]; })) return { target: '', error: 'precision_alias_target_collision' };
    return { target: targets[0], error: '' };
  }

  var alias = aliasTarget(selected);
  if (alias.error) return invalid(alias.error);
  var canonicalModel = model;
  var canonical = selected;
  var aliasDepth = 0;
  if (alias.target) {
    if (alias.target === model) return invalid('precision_alias_cycle');
    aliasDepth = 1;
    canonicalModel = alias.target;
    canonical = capabilities[canonicalModel];
    if (!canonical || typeof canonical !== 'object' || Array.isArray(canonical)) return invalid('precision_alias_target_unknown', canonicalModel, aliasDepth);
    var nextAlias = aliasTarget(canonical);
    if (nextAlias.error) return invalid(nextAlias.error, canonicalModel, aliasDepth);
    if (nextAlias.target) {
      return invalid(nextAlias.target === model || nextAlias.target === canonicalModel ? 'precision_alias_cycle' : 'precision_alias_chain_too_deep', canonicalModel, aliasDepth);
    }
  }
  var sizeDeclaration = precisionCapabilitySizeDeclaration(canonical);
  var hasSizePolicy = Object.prototype.hasOwnProperty.call(canonical, 'size_policy');
  var policyValid = !hasSizePolicy || canonical.size_policy === 'gpt_image_2_flexible';
  var flexibleSizes = policyValid && canonical.size_policy === 'gpt_image_2_flexible';
  var precisionEditConfirmed = canonical.precision_edit === true;
  return {
    selectedModel: model, canonicalModel: canonicalModel, capability: canonical, sizes: sizeDeclaration.sizes,
    aliasDepth: aliasDepth, structureValid: true, precisionEditConfirmed: precisionEditConfirmed,
    sizeDeclarationPresent: sizeDeclaration.present, sizeDeclarationValid: sizeDeclaration.valid,
    flexibleSizes: flexibleSizes,
    reason: !precisionEditConfirmed ? 'precision_edit_unconfirmed' : (!policyValid ? 'precision_size_policy_invalid' : sizeDeclaration.reason)
  };
}

function getPrecisionResizeCapability() {
  var provider = findProvider(precisionEditSelectedModel.providerId);
  var model = precisionEditSelectedModel.model;
  var resolution = resolvePrecisionModelCapability(provider, model);
  var catalogSizes = {};
  var catalog = provider && Array.isArray(provider.precision_size_catalog)
    ? provider.precision_size_catalog : [];
  var catalogEntry = catalog.find(function(entry) {
    return entry && (entry.model === model || entry.canonical_model === resolution.canonicalModel);
  });
  if (catalogEntry && Array.isArray(catalogEntry.strict_selectable_sizes)) {
    precisionResizeDimensions(catalogEntry.strict_selectable_sizes, catalogSizes);
  }
  var sizes = Object.keys(catalogSizes).length ? catalogSizes
    : (resolution.structureValid && resolution.sizeDeclarationValid ? resolution.sizes : {});
  return {
    known: !!(resolution.structureValid && ((resolution.sizeDeclarationValid && resolution.reason !== 'precision_size_policy_invalid') || Object.keys(catalogSizes).length)),
    declared: !!(Object.keys(catalogSizes).length || (resolution.structureValid && resolution.sizeDeclarationPresent)),
    sizes: sizes,
    canonicalModel: resolution.canonicalModel || '',
    flexibleSizes: !!resolution.flexibleSizes
  };
}

function precisionGptImage2SizeError(value) {
  var match = /^([1-9]\d{1,4})x([1-9]\d{1,4})$/.exec(String(value || ''));
  if (!match) return 'precision_target_size_invalid';
  var width = Number(match[1]);
  var height = Number(match[2]);
  if (width > PRECISION_GPT_IMAGE_2_MAX_SIDE || height > PRECISION_GPT_IMAGE_2_MAX_SIDE) return 'precision_target_size_side_exceeded';
  if (width % PRECISION_GPT_IMAGE_2_SIZE_ALIGNMENT || height % PRECISION_GPT_IMAGE_2_SIZE_ALIGNMENT) return 'precision_target_size_alignment_invalid';
  var ratio = width / height;
  if (ratio < (1 / 3) || ratio > 3) return 'precision_target_size_aspect_invalid';
  var pixels = width * height;
  if (pixels < PRECISION_GPT_IMAGE_2_MIN_OUTPUT_PIXELS) return 'precision_target_size_pixels_too_small';
  if (pixels > PRECISION_GPT_IMAGE_2_MAX_OUTPUT_PIXELS) return 'precision_target_size_pixels_exceeded';
  return '';
}

function getPrecisionResizeTargetSize() {
  var width = precisionResizeInputDimension('precisionResizeWidth');
  var height = precisionResizeInputDimension('precisionResizeHeight');
  return precisionResizeDimensionKey(width, height);
}

function getPrecisionResizeCapabilityState() {
  var targetSize = getPrecisionResizeTargetSize();
  var authorization = getPrecisionEditModelAuthorizationState();
  var capability = getPrecisionResizeCapability();
  var outputPolicy = getPrecisionOutputSizePolicy();
  return {
    targetSize: targetSize,
    authorization: authorization,
    capability: capability,
    supported: !!(targetSize && authorization.authorized && capability.known && (
      outputPolicy === 'fit_crop' ||
      (capability.flexibleSizes && precisionGptImage2SizeError(targetSize) === '') ||
      capability.sizes[targetSize] === true
    ))
  };
}

function normalizePrecisionResizePresetName(value) {
  var normalized = String(value === null || value === undefined ? '' : value);
  if (typeof normalized.normalize === 'function') {
    try { normalized = normalized.normalize('NFKC'); } catch (ignore) {}
  }
  normalized = normalized.replace(/[\u0000-\u001f\u007f-\u009f]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!normalized || Array.from(normalized).length > 40) return '';
  return normalized;
}

function precisionResizePresetNameKey(value) {
  return normalizePrecisionResizePresetName(value).toLowerCase();
}

function sanitizePrecisionResizePreset(value) {
  if (!value || typeof value !== 'object') return null;
  var id = String(value.id || '');
  var name = normalizePrecisionResizePresetName(value.name);
  var size = precisionResizeDimensionKey(value.width, value.height);
  if (!/^[a-z0-9_-]{1,64}$/i.test(id) || !name || !size) return null;
  return { id: id, name: name, width: value.width, height: value.height };
}

function readPrecisionResizePresets() {
  try {
    var raw = window.localStorage && window.localStorage.getItem(PRECISION_RESIZE_PRESET_STORAGE_KEY);
    if (!raw) return [];
    var parsed = JSON.parse(raw);
    if (!parsed || parsed.version !== PRECISION_RESIZE_PRESET_SCHEMA_VERSION || !Array.isArray(parsed.presets)) return [];
    var ids = {};
    var names = {};
    var sizes = {};
    var presets = [];
    parsed.presets.some(function(value) {
      var preset = sanitizePrecisionResizePreset(value);
      if (!preset) return false;
      var nameKey = precisionResizePresetNameKey(preset.name);
      var sizeKey = precisionResizeDimensionKey(preset.width, preset.height);
      if (!nameKey || ids[preset.id] || names[nameKey] || sizes[sizeKey]) return false;
      ids[preset.id] = true;
      names[nameKey] = true;
      sizes[sizeKey] = true;
      presets.push(preset);
      return presets.length >= PRECISION_RESIZE_PRESET_LIMIT;
    });
    return presets;
  } catch (error) {
    return [];
  }
}

function writePrecisionResizePresets(presets) {
  var sanitized = [];
  var ids = {};
  var names = {};
  var sizes = {};
  (Array.isArray(presets) ? presets : []).some(function(value) {
    var preset = sanitizePrecisionResizePreset(value);
    if (!preset) return false;
    var nameKey = precisionResizePresetNameKey(preset.name);
    var sizeKey = precisionResizeDimensionKey(preset.width, preset.height);
    if (!nameKey || ids[preset.id] || names[nameKey] || sizes[sizeKey]) return false;
    ids[preset.id] = true;
    names[nameKey] = true;
    sizes[sizeKey] = true;
    sanitized.push({ id: preset.id, name: preset.name, width: preset.width, height: preset.height });
    return sanitized.length >= PRECISION_RESIZE_PRESET_LIMIT;
  });
  try {
    window.localStorage.setItem(PRECISION_RESIZE_PRESET_STORAGE_KEY, JSON.stringify({
      version: PRECISION_RESIZE_PRESET_SCHEMA_VERSION,
      presets: sanitized
    }));
    return true;
  } catch (error) {
    return false;
  }
}

function createPrecisionResizePresetId(presets) {
  var id = '';
  do {
    precisionResizePresetIdCounter += 1;
    id = 'preset-' + Date.now().toString(36) + '-' + precisionResizePresetIdCounter.toString(36);
  } while ((presets || []).some(function(preset) { return preset.id === id; }));
  return id;
}

function precisionResizePresetSize(value, option) {
  var candidate = option && option.dataset && option.dataset.size ? option.dataset.size : value;
  var match = /^(\d{2,5})x(\d{2,5})$/i.exec(String(candidate || '').trim());
  return match ? precisionResizeDimensionKey(Number(match[1]), Number(match[2])) : '';
}

function setPrecisionResizePresetStatus(key, params, tone) {
  var status = document.getElementById('precisionResizePresetStatus');
  if (!status) return;
  status.textContent = key ? i18nText(key, params) : '';
  status.classList.toggle('is-error', tone === 'error');
  status.classList.toggle('is-success', tone === 'success');
}

function sanitizePrecisionOutputSizePolicy(value) {
  return value === 'fit_crop' ? 'fit_crop' : 'strict';
}

function syncPrecisionOutputSizePolicyControls() {
  precisionOutputSizePolicy = sanitizePrecisionOutputSizePolicy(precisionOutputSizePolicy);
  ['strict', 'fit_crop'].forEach(function(policy) {
    var input = document.getElementById('precisionOutputPolicy' + (policy === 'strict' ? 'Strict' : 'FitCrop'));
    if (input) input.checked = precisionOutputSizePolicy === policy;
  });
  var hint = document.getElementById('precisionOutputSizePolicyHint');
  if (hint) hint.textContent = i18nText(precisionOutputSizePolicy === 'fit_crop'
    ? 'creator.precision_output_size_policy_fit_crop_hint'
    : 'creator.precision_output_size_policy_strict_hint');
  var mode = document.getElementById('precisionResizeMode');
  if (mode) mode.value = precisionOutputSizePolicy;
  var modeHint = document.getElementById('precisionResizeModeHint');
  if (modeHint) modeHint.textContent = i18nText(precisionOutputSizePolicy === 'fit_crop'
    ? 'creator.precision_size_mode_fit_crop_hint'
    : 'creator.precision_size_mode_strict_hint');
  updatePrecisionResizeModeControls();
}

// The selected size policy is the second step in the resize flow. Model sizes
// are a fail-closed preset list; custom dimensions and saved presets belong
// exclusively to the local crop-to-fit branch.
function updatePrecisionResizeModeControls() {
  var policy = sanitizePrecisionOutputSizePolicy(precisionOutputSizePolicy);
  var preset = document.getElementById('precisionResizePreset');
  var selected = preset && preset.options ? preset.options[preset.selectedIndex] : null;
  var isCrop = policy === 'fit_crop';
  var isCustom = !!(selected && selected.value === 'custom');
  var label = document.getElementById('precisionResizePresetLabel');
  var customFields = document.getElementById('precisionResizeCustomFields');
  var editor = document.getElementById('precisionResizePresetEditor');
  if (label) label.textContent = i18nText(isCrop ? 'creator.precision_size_crop_preset' : 'creator.precision_size_model_preset');
  if (customFields) customFields.classList.toggle('hidden', !isCrop || !isCustom);
  if (editor) editor.classList.toggle('hidden', !isCrop);
}

function setPrecisionOutputSizePolicy(value) {
  precisionOutputSizePolicy = sanitizePrecisionOutputSizePolicy(value);
  syncPrecisionOutputSizePolicyControls();
  updatePrecisionEditControls();
  return precisionOutputSizePolicy;
}

function getPrecisionOutputSizePolicy() {
  // The visible second-level mode select is the single source of truth. The
  // legacy radio controls remain hidden for compatibility with older callers
  // and must never override the current mode.
  var mode = document.getElementById('precisionResizeMode');
  if (mode && mode.value) return sanitizePrecisionOutputSizePolicy(mode.value);
  var checked = document.querySelector ? document.querySelector('input[name="precisionOutputSizePolicy"]:checked') : null;
  if (checked && checked.value) return sanitizePrecisionOutputSizePolicy(checked.value);
  return sanitizePrecisionOutputSizePolicy(precisionOutputSizePolicy);
}

function precisionGreatestCommonDivisor(a, b) {
  a = Math.abs(Number(a) || 0);
  b = Math.abs(Number(b) || 0);
  while (b) {
    var next = a % b;
    a = b;
    b = next;
  }
  return a || 1;
}

function precisionResizeAspectConstraint(targetSize) {
  var match = /^([1-9]\d{1,4})x([1-9]\d{1,4})$/.exec(String(targetSize || ''));
  if (!match) return '';
  var width = Number(match[1]);
  var height = Number(match[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return '';
  var ratio = width / height;
  var known = [
    { width: 1, height: 1 },
    { width: 3, height: 2 },
    { width: 2, height: 3 },
    { width: 4, height: 3 },
    { width: 3, height: 4 },
    { width: 16, height: 9 },
    { width: 9, height: 16 },
    { width: 21, height: 9 },
    { width: 9, height: 21 }
  ];
  for (var index = 0; index < known.length; index += 1) {
    var candidate = known[index];
    if (Math.abs(ratio - candidate.width / candidate.height) < 0.01) {
      return candidate.width + ':' + candidate.height + ' aspect ratio';
    }
  }
  var divisor = precisionGreatestCommonDivisor(width, height);
  return Math.round(width / divisor) + ':' + Math.round(height / divisor) + ' aspect ratio';
}

function syncPrecisionAspectRatioHint() {
  var hint = document.getElementById('precisionAspectRatioHint');
  if (!hint) return;
  var targetSize = getPrecisionResizeTargetSize();
  var aspect = precisionResizeAspectConstraint(targetSize);
  hint.textContent = targetSize && aspect
    ? i18nText('creator.precision_aspect_ratio_hint', { size: targetSize, ratio: aspect })
    : i18nText('creator.precision_aspect_ratio_hint_empty');
}

function updatePrecisionResizePresetControls() {
  var select = document.getElementById('precisionResizePreset');
  var selected = select && select.options ? select.options[select.selectedIndex] : null;
  var savedSelected = !!(selected && selected.dataset && selected.dataset.precisionSavedPreset === 'true');
  var remove = document.getElementById('btnPrecisionDeleteResizePreset');
  var reset = document.getElementById('btnPrecisionResetResizePresets');
  if (remove) remove.disabled = !savedSelected;
  if (reset) reset.disabled = !precisionResizeSavedPresets.length;
}

function renderPrecisionResizeSavedPresets(preferredValue) {
  var select = document.getElementById('precisionResizePreset');
  if (!select) return;
  var previous = preferredValue || select.value || 'custom';
  Array.prototype.slice.call(select.querySelectorAll('option[data-precision-saved-preset="true"]')).forEach(function(option) {
    option.remove();
  });
  precisionResizeSavedPresets = readPrecisionResizePresets();
  precisionResizeSavedPresets.forEach(function(preset) {
    var option = document.createElement('option');
    option.value = 'saved:' + preset.id;
    option.textContent = preset.name + ' · ' + preset.width + ' × ' + preset.height;
    option.dataset.precisionSavedPreset = 'true';
    option.dataset.precisionResizeMode = 'fit_crop';
    option.dataset.size = preset.width + 'x' + preset.height;
    select.appendChild(option);
  });
  var available = Array.prototype.some.call(select.options || [], function(option) { return option.value === previous; });
  select.value = available ? previous : 'custom';
  updatePrecisionResizeCapabilityUI();
  updatePrecisionResizePresetControls();
}

// Strict and crop-to-fit presets are deliberately independent families. Strict
// presets describe sizes the upstream model may natively return; crop presets
// are common local finishing sizes. Older templates that do not yet include a
// crop family are upgraded by mirroring strict entries as a compatibility
// fallback only.
function ensurePrecisionResizeModePresetGroups() {
  var select = document.getElementById('precisionResizePreset');
  if (!select || (select.dataset && select.dataset.precisionModeGroups === 'true')) return;
  if (typeof select.querySelectorAll !== 'function' || typeof select.appendChild !== 'function') return;
  var strictGroups = Array.prototype.slice.call(select.querySelectorAll('optgroup')).filter(function(group) {
    return !group.dataset || group.dataset.precisionResizeMode !== 'fit_crop';
  });
  strictGroups.forEach(function(group) { group.dataset.precisionResizeMode = 'strict'; });
  var cropGroups = Array.prototype.slice.call(select.querySelectorAll('optgroup[data-precision-resize-mode="fit_crop"]'));
  // Author-provided crop entries remain the source of truth. Namespace their
  // values so the same pixel size can exist in both branches without the
  // browser picking a hidden strict option when the mode changes.
  cropGroups.forEach(function(group) {
    Array.prototype.slice.call(group.options || group.querySelectorAll('option')).forEach(function(option) {
      var size = precisionResizePresetSize(option.value, option);
      if (!size) return;
      option.value = 'crop:' + size;
      option.dataset.size = size;
      option.dataset.precisionCropPreset = 'true';
    });
  });
  // The crop branch has its own 1K/2K/4K catalogue. The compact "common
  // sizes" group omitted many tier/ratio pairs, so a tier selection could
  // point at a missing crop: value and fall back to Custom. These are local
  // crop presets only; they never expand the strict upstream whitelist.
  strictGroups.forEach(function(strictGroup) {
    var tierMatch = /\b([124]K)\b/i.exec(String(strictGroup.label || ''));
    var tier = tierMatch ? tierMatch[1].toUpperCase() : '';
    if (!tier) return;
    var cropGroup = cropGroups.find(function(group) {
      return group.dataset && group.dataset.precisionResizeTier === tier;
    });
    if (!cropGroup) {
      cropGroup = document.createElement('optgroup');
      cropGroup.label = '裁切适配 · ' + tier;
      cropGroup.dataset.precisionResizeMode = 'fit_crop';
      cropGroup.dataset.precisionResizeTier = tier;
      select.appendChild(cropGroup);
      cropGroups.push(cropGroup);
    }
    Array.prototype.slice.call(strictGroup.options || strictGroup.querySelectorAll('option')).forEach(function(option) {
      var size = precisionResizePresetSize(option.value, option);
      if (!size) return;
      var cropValue = 'crop:' + size;
      var exists = Array.prototype.some.call(cropGroup.options || cropGroup.querySelectorAll('option'), function(candidate) {
        return candidate.value === cropValue;
      });
      if (exists) return;
      var clone = option.cloneNode(true);
      clone.value = cropValue;
      clone.dataset.size = size;
      clone.dataset.precisionCropPreset = 'true';
      clone.dataset.precisionResizeMode = 'fit_crop';
      cropGroup.appendChild(clone);
    });
  });
  if (!cropGroups.length) {
    strictGroups.forEach(function(group) {
    var cropGroup = document.createElement('optgroup');
    cropGroup.label = '裁切适配 · ' + String(group.label || '').replace(/^(严格尺寸|模型尺寸)\s*·\s*/, '');
    cropGroup.dataset.precisionResizeMode = 'fit_crop';
    Array.prototype.slice.call(group.options || group.querySelectorAll('option')).forEach(function(option) {
      var size = precisionResizePresetSize(option.value, option);
      if (!size) return;
      var clone = option.cloneNode(true);
      clone.value = 'crop:' + size;
      clone.dataset.size = size;
      clone.dataset.precisionCropPreset = 'true';
      cropGroup.appendChild(clone);
    });
    select.appendChild(cropGroup);
    });
  }
  if (select.dataset) select.dataset.precisionModeGroups = 'true';
}

function syncPrecisionResizeModePresetSelection(policy) {
  var select = document.getElementById('precisionResizePreset');
  if (!select) return;
  var value = String(select.value || 'custom');
  var size = precisionResizePresetSize(value, select.options[select.selectedIndex]);
  if (!size) return;
  var desired = policy === 'fit_crop' ? 'crop:' + size : size;
  if (desired === value) return;
  var target = Array.prototype.find.call(select.options || [], function(option) { return option.value === desired; });
  if (target && !target.hidden) select.value = desired;
}

function updatePrecisionResizeCapabilityUI() {
  var select = document.getElementById('precisionResizePreset');
  ensurePrecisionResizeModePresetGroups();
  var capability = getPrecisionResizeCapability();
  var options = select && select.options || [];
  var outputPolicy = getPrecisionOutputSizePolicy();
  syncPrecisionResizeModePresetSelection(outputPolicy);
  // A strict-size declaration controls generation readiness, not which
  // candidate sizes a user may inspect and explicitly authorize. Hiding an
  // undeclared preset made new upstream model variants impossible to try even
  // after the user had checked their endpoint documentation. The action gate
  // below still keeps Generate disabled until a scoped confirmation is saved.
  var selectedOption = select && select.options ? select.options[select.selectedIndex] : null;
  for (var i = 0; i < options.length; i++) {
    var option = options[i];
    var size = precisionResizePresetSize(option.value, option);
    var custom = option.value === 'custom';
    var optionMode = option.dataset && option.dataset.precisionResizeMode
      ? option.dataset.precisionResizeMode
      : option.parentNode && option.parentNode.dataset
        ? option.parentNode.dataset.precisionResizeMode : '';
    var modeMismatch = outputPolicy === 'fit_crop'
      ? (optionMode === 'strict')
      : (optionMode === 'fit_crop');
    var supported = (custom && outputPolicy === 'fit_crop') || outputPolicy === 'fit_crop' || (capability.flexibleSizes
      ? !!size && precisionGptImage2SizeError(size) === ''
      : capability.known && !!size && capability.sizes[size] === true);
    var capabilityState = custom || outputPolicy === 'fit_crop'
      ? 'local'
      : !capability.known
        ? 'unknown'
        : supported ? 'supported' : 'needs-authorization';
    option.hidden = modeMismatch;
    option.disabled = false;
    option.title = custom || supported ? '' : i18nText('creator.precision_size_preset_trial_required');
    option.dataset.precisionCapabilityState = capabilityState;
    option.dataset.precisionCapabilityModel = capability.canonicalModel || '';
    if (size && !optionMode) option.dataset.precisionResizeMode = 'strict';
  }
  // Switching between strict and crop-to-fit can hide the active option.
  // Keep its dimensions in the number fields while selecting a visible helper.
  if (selectedOption && selectedOption.hidden && select) {
    var visibleOption = Array.prototype.find.call(options, function(option) {
      return !option.hidden && option.value !== 'custom';
    });
    select.value = visibleOption ? visibleOption.value : 'custom';
    if (visibleOption) applyPrecisionResizePreset(visibleOption.value);
  }
  // Collapse empty built-in groups so a strict model does not show blank 1K,
  // 2K, or 4K headings after filtering. Saved options are appended directly
  // to the select and therefore do not need group handling.
  if (select && select.querySelectorAll) {
    Array.prototype.forEach.call(select.querySelectorAll('optgroup'), function(group) {
      var children = group.options || group.querySelectorAll('option');
      var groupMode = group.dataset.precisionResizeMode || 'strict';
      var visible = groupMode === outputPolicy && Array.prototype.some.call(children || [], function(option) { return !option.hidden; });
      group.hidden = !visible;
    });
  }
  if (select) select.disabled = false;
  updatePrecisionResizeModeControls();
  updatePrecisionResizePresetControls();
  var status = document.getElementById('precisionResizeCapabilityStatus');
  if (!status) return;
  var state = getPrecisionResizeCapabilityState();
  var pending = precisionResizeCapabilityPending;
  var pendingCurrent = !!(pending && pending.providerId === state.authorization.providerId &&
    pending.model === state.authorization.model && pending.size === state.targetSize);
  var messageKey = 'creator.precision_size_capability_model_required';
  if (precisionEditSizeMode === 'resize') {
    if (!state.targetSize) messageKey = 'creator.precision_size_capability_invalid';
    else if (!state.authorization.authorized) messageKey = 'creator.precision_size_capability_model_required';
    else if (outputPolicy === 'fit_crop') {
      // Crop-to-fit requires a confirmed model contract, but its target is a
      // local finishing size rather than a claim that the upstream natively
      // supports that exact resolution. Never offer per-size authorization in
      // this mode because it would incorrectly mutate the strict whitelist.
      messageKey = state.capability.known
        ? 'creator.precision_size_capability_fit_crop'
        : 'creator.precision_size_capability_unknown';
    } else if (state.supported) {
      messageKey = state.capability.flexibleSizes
        ? 'creator.precision_size_capability_flexible'
        : 'creator.precision_size_capability_supported';
    } else {
      messageKey = state.capability.known ? 'creator.precision_size_capability_unsupported' : 'creator.precision_size_capability_unknown';
    }
  }
  if (pendingCurrent) messageKey = pending.enabled ? 'creator.precision_size_confirming' : 'creator.precision_size_revoking';
  if (status) {
    status.textContent = i18nText(messageKey, { size: state.targetSize || '' });
    status.dataset.state = pendingCurrent ? 'pending'
      : outputPolicy === 'fit_crop' && state.supported ? 'crop-fit'
      : state.supported ? 'supported' : 'blocked';
  }
  // A model-size grant is deliberately scoped to the current provider, model,
  // and exact target size.  It is an explicit user-authorized experiment, not
  // an inferred capability from a different model or an automatic retry.
  var canManageExactSize = precisionEditSizeMode === 'resize' &&
    outputPolicy === 'strict' && state.targetSize && state.authorization.authorized;
  var confirmAction = document.getElementById('btnPrecisionConfirmResizeSize');
  var revokeAction = document.getElementById('btnPrecisionRevokeResizeSize');
  if (confirmAction) {
    var canConfirm = !!(canManageExactSize && !state.supported && !pendingCurrent);
    confirmAction.hidden = !canManageExactSize || state.supported;
    confirmAction.disabled = !canConfirm;
    confirmAction.textContent = i18nText('creator.precision_size_confirm_action', { size: state.targetSize || '' });
  }
  if (revokeAction) {
    var canRevoke = !!(canManageExactSize && state.supported && !pendingCurrent && !state.capability.flexibleSizes);
    revokeAction.hidden = !canManageExactSize || !state.supported || state.capability.flexibleSizes;
    revokeAction.disabled = !canRevoke;
    revokeAction.textContent = i18nText('creator.precision_size_revoke_action', { size: state.targetSize || '' });
  }
}

function submitPrecisionResizeCapability(enabled) {
  if (precisionResizeCapabilityPending) return Promise.resolve(false);
  var state = getPrecisionResizeCapabilityState();
  if (!state.targetSize || !state.authorization.authorized) return Promise.resolve(false);
  if ((enabled && state.supported) || (!enabled && !state.supported)) return Promise.resolve(false);
  var confirmKey = enabled ? 'creator.precision_size_confirm_dialog' : 'creator.precision_size_revoke_dialog';
  if (!confirm(i18nText(confirmKey, { size: state.targetSize }))) return Promise.resolve(false);
  var request = {
    providerId: state.authorization.providerId,
    model: state.authorization.model,
    size: state.targetSize,
    enabled: enabled
  };
  precisionResizeCapabilityPending = request;
  updatePrecisionEditControls();
  return _authFetch('/api/providers/' + encodeURIComponent(request.providerId) + '/precision-capability', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: request.model, enabled: enabled, confirmed: true, size: request.size })
  }).then(function(response) {
    if (!response.ok) throw new Error('precision_size_capability_save_failed');
    return response.json();
  }).then(function() {
    return loadProviders();
  }).then(function() {
    if (precisionResizeCapabilityPending === request) precisionResizeCapabilityPending = null;
    updatePrecisionEditControls();
    setStatus(i18nText(enabled ? 'creator.precision_size_confirmed' : 'creator.precision_size_revoked', { size: request.size }));
    return true;
  }).catch(function() {
    if (precisionResizeCapabilityPending === request) precisionResizeCapabilityPending = null;
    updatePrecisionEditControls();
    setStatus(i18nText('creator.precision_size_capability_save_failed'));
    return false;
  });
}

function confirmPrecisionResizeCapability() {
  return submitPrecisionResizeCapability(true);
}

function revokePrecisionResizeCapability() {
  return submitPrecisionResizeCapability(false);
}

function submitPrecisionFlexibleSizes(enabled) {
  if (precisionResizeCapabilityPending) return Promise.resolve(false);
  var state = getPrecisionResizeCapabilityState();
  if (!state.authorization.authorized || !state.capability.known || state.capability.flexibleSizes === enabled) return Promise.resolve(false);
  var confirmKey = enabled ? 'creator.precision_size_flexible_enable_dialog' : 'creator.precision_size_flexible_disable_dialog';
  if (!confirm(i18nText(confirmKey))) return Promise.resolve(false);
  var request = { providerId: state.authorization.providerId, model: state.authorization.model, flexibleSizes: enabled };
  precisionResizeCapabilityPending = request;
  updatePrecisionEditControls();
  return _authFetch('/api/providers/' + encodeURIComponent(request.providerId) + '/precision-capability', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: request.model, enabled: true, confirmed: true, flexible_sizes: enabled })
  }).then(function(response) {
    if (!response.ok) throw new Error('precision_flexible_size_capability_save_failed');
    return response.json();
  }).then(function() {
    return loadProviders();
  }).then(function() {
    if (precisionResizeCapabilityPending === request) precisionResizeCapabilityPending = null;
    updatePrecisionEditControls();
    setStatus(i18nText(enabled ? 'creator.precision_size_flexible_enabled' : 'creator.precision_size_flexible_disabled'));
    return true;
  }).catch(function() {
    if (precisionResizeCapabilityPending === request) precisionResizeCapabilityPending = null;
    updatePrecisionEditControls();
    setStatus(i18nText('creator.precision_size_capability_save_failed'));
    return false;
  });
}

function enablePrecisionFlexibleSizes() {
  return submitPrecisionFlexibleSizes(true);
}

function disablePrecisionFlexibleSizes() {
  return submitPrecisionFlexibleSizes(false);
}

function findPrecisionResizeOptionBySize(size) {
  var select = document.getElementById('precisionResizePreset');
  if (!select || !size) return null;
  for (var i = 0; i < select.options.length; i++) {
    if (precisionResizePresetSize(select.options[i].value, select.options[i]) === size) return select.options[i];
  }
  return null;
}

function savePrecisionResizePreset() {
  if (getPrecisionOutputSizePolicy() !== 'fit_crop') {
    setPrecisionResizePresetStatus('creator.precision_size_preset_crop_only', null, 'error');
    return;
  }
  var nameInput = document.getElementById('precisionResizePresetName');
  var name = normalizePrecisionResizePresetName(nameInput && nameInput.value);
  if (!name) {
    setPrecisionResizePresetStatus('creator.precision_size_preset_name_invalid', null, 'error');
    return;
  }
  var width = Number((document.getElementById('precisionResizeWidth') || { value: '' }).value);
  var height = Number((document.getElementById('precisionResizeHeight') || { value: '' }).value);
  var size = precisionResizeDimensionKey(width, height);
  if (!size) {
    setPrecisionResizePresetStatus('creator.precision_size_invalid', null, 'error');
    return;
  }
  var presets = readPrecisionResizePresets();
  var nameKey = precisionResizePresetNameKey(name);
  var duplicateName = presets.find(function(preset) { return precisionResizePresetNameKey(preset.name) === nameKey; });
  if (duplicateName) {
    var exactDuplicate = precisionResizeDimensionKey(duplicateName.width, duplicateName.height) === size;
    if (exactDuplicate) {
      var duplicateValue = 'saved:' + duplicateName.id;
      renderPrecisionResizeSavedPresets(duplicateValue);
      applyPrecisionResizePreset(duplicateValue);
    }
    setPrecisionResizePresetStatus(
      exactDuplicate ? 'creator.precision_size_preset_exists' : 'creator.precision_size_preset_name_duplicate',
      { name: duplicateName.name },
      exactDuplicate ? '' : 'error'
    );
    return;
  }
  var duplicateSize = findPrecisionResizeOptionBySize(size);
  if (duplicateSize) {
    var select = document.getElementById('precisionResizePreset');
    if (select) select.value = duplicateSize.value;
    applyPrecisionResizePreset(duplicateSize.value);
    updatePrecisionResizePresetControls();
    setPrecisionResizePresetStatus('creator.precision_size_preset_size_duplicate', { name: duplicateSize.textContent || size }, 'error');
    return;
  }
  if (presets.length >= PRECISION_RESIZE_PRESET_LIMIT) {
    setPrecisionResizePresetStatus('creator.precision_size_preset_limit', { count: PRECISION_RESIZE_PRESET_LIMIT }, 'error');
    return;
  }
  var preset = { id: createPrecisionResizePresetId(presets), name: name, width: width, height: height };
  if (!writePrecisionResizePresets(presets.concat([preset]))) {
    setPrecisionResizePresetStatus('creator.precision_size_preset_storage_error', null, 'error');
    return;
  }
  renderPrecisionResizeSavedPresets('saved:' + preset.id);
  if (nameInput) nameInput.value = '';
  setPrecisionResizePresetStatus('creator.precision_size_preset_saved', { name: name }, 'success');
}

function deleteSelectedPrecisionResizePreset() {
  var select = document.getElementById('precisionResizePreset');
  var option = select && select.options ? select.options[select.selectedIndex] : null;
  if (!option || !option.dataset || option.dataset.precisionSavedPreset !== 'true' || option.value.indexOf('saved:') !== 0) {
    setPrecisionResizePresetStatus('creator.precision_size_preset_delete_saved_only', null, 'error');
    updatePrecisionResizePresetControls();
    return;
  }
  var id = option.value.slice(6);
  var presets = readPrecisionResizePresets();
  var preset = presets.find(function(item) { return item.id === id; });
  if (!preset) {
    renderPrecisionResizeSavedPresets('custom');
    setPrecisionResizePresetStatus('creator.precision_size_preset_delete_saved_only', null, 'error');
    return;
  }
  if (!writePrecisionResizePresets(presets.filter(function(item) { return item.id !== id; }))) {
    setPrecisionResizePresetStatus('creator.precision_size_preset_storage_error', null, 'error');
    return;
  }
  renderPrecisionResizeSavedPresets('custom');
  setPrecisionResizePresetStatus('creator.precision_size_preset_deleted', { name: preset.name }, 'success');
}

function resetPrecisionResizePresets() {
  var presets = readPrecisionResizePresets();
  if (!presets.length) {
    setPrecisionResizePresetStatus('creator.precision_size_preset_reset_empty');
    return;
  }
  if (!confirm(i18nText('creator.precision_size_preset_reset_confirm'))) return;
  if (!writePrecisionResizePresets([])) {
    setPrecisionResizePresetStatus('creator.precision_size_preset_storage_error', null, 'error');
    return;
  }
  renderPrecisionResizeSavedPresets('custom');
  setPrecisionResizePresetStatus('creator.precision_size_preset_reset_done', null, 'success');
}

function bindPrecisionResizeControls() {
  precisionOutputSizePolicy = sanitizePrecisionOutputSizePolicy(precisionOutputSizePolicy);
  syncPrecisionOutputSizePolicyControls();
  var modeSelect = document.getElementById('precisionResizeMode');
  if (modeSelect && modeSelect.dataset.precisionBound !== 'true') {
    modeSelect.dataset.precisionBound = 'true';
    modeSelect.addEventListener('change', function() {
      setPrecisionOutputSizePolicy(this.value);
      updatePrecisionResizeCapabilityUI();
      updatePrecisionEditControls();
    });
  }
  ['precisionOutputPolicyStrict', 'precisionOutputPolicyFitCrop'].forEach(function(id) {
    var input = document.getElementById(id);
    if (!input || input.dataset.precisionBound === 'true') return;
    input.dataset.precisionBound = 'true';
    input.addEventListener('change', function() {
      if (this.checked) setPrecisionOutputSizePolicy(this.value);
    });
  });
  var select = document.getElementById('precisionResizePreset');
  if (select && select.dataset.precisionBound !== 'true') {
    select.dataset.precisionBound = 'true';
    select.addEventListener('change', function() {
      if (this.options[this.selectedIndex] && this.options[this.selectedIndex].disabled) {
        this.value = 'custom';
        return;
      }
      applyPrecisionResizePreset(this.value);
      updatePrecisionResizePresetControls();
      setPrecisionResizePresetStatus('');
      updatePrecisionEditControls();
    });
  }
  ['precisionResizeTier', 'precisionResizeRatio'].forEach(function(id) {
    var input = document.getElementById(id);
    if (!input || input.dataset.precisionBound === 'true') return;
    input.dataset.precisionBound = 'true';
    input.addEventListener('change', function() {
      if (this.value === 'custom') {
        markPrecisionResizeCustom();
        return;
      }
      applyPrecisionResizeTierRatio();
    });
  });
  var promptPreset = document.getElementById('precisionResizePromptPreset');
  if (promptPreset && promptPreset.dataset.precisionBound !== 'true') {
    promptPreset.dataset.precisionBound = 'true';
    promptPreset.addEventListener('change', function() {
      applyPrecisionResizePromptPreset(this.value);
      updatePrecisionEditControls();
    });
  }
  ['precisionResizeWidth', 'precisionResizeHeight'].forEach(function(id) {
    var input = document.getElementById(id);
    if (!input || input.dataset.precisionReadinessBound === 'true') return;
    input.dataset.precisionReadinessBound = 'true';
    input.addEventListener('input', function() {
      syncPrecisionAspectRatioHint();
      updatePrecisionEditControls();
    });
  });
  var prompt = document.getElementById('precisionResizePrompt');
  if (prompt && prompt.dataset.precisionPromptPresetBound !== 'true') {
    prompt.dataset.precisionPromptPresetBound = 'true';
    prompt.addEventListener('input', function() {
      this.setCustomValidity('');
      updatePrecisionEditControls();
    });
  }
  var save = document.getElementById('btnPrecisionSaveResizePreset');
  var remove = document.getElementById('btnPrecisionDeleteResizePreset');
  var reset = document.getElementById('btnPrecisionResetResizePresets');
  var name = document.getElementById('precisionResizePresetName');
  var confirmSize = document.getElementById('btnPrecisionConfirmResizeSize');
  var revokeSize = document.getElementById('btnPrecisionRevokeResizeSize');
  if (save && save.dataset.precisionBound !== 'true') {
    save.dataset.precisionBound = 'true';
    save.addEventListener('click', savePrecisionResizePreset);
  }
  if (remove && remove.dataset.precisionBound !== 'true') {
    remove.dataset.precisionBound = 'true';
    remove.addEventListener('click', deleteSelectedPrecisionResizePreset);
  }
  if (reset && reset.dataset.precisionBound !== 'true') {
    reset.dataset.precisionBound = 'true';
    reset.addEventListener('click', resetPrecisionResizePresets);
  }
  if (name && name.dataset.precisionBound !== 'true') {
    name.dataset.precisionBound = 'true';
    name.addEventListener('keydown', function(event) {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      savePrecisionResizePreset();
    });
  }
  if (confirmSize && confirmSize.dataset.precisionBound !== 'true') {
    confirmSize.dataset.precisionBound = 'true';
    confirmSize.addEventListener('click', confirmPrecisionResizeCapability);
  }
  if (revokeSize && revokeSize.dataset.precisionBound !== 'true') {
    revokeSize.dataset.precisionBound = 'true';
    revokeSize.addEventListener('click', revokePrecisionResizeCapability);
  }
  renderPrecisionResizeSavedPresets();
  if (typeof syncPrecisionResizeTierRatioFromSize === 'function') {
    syncPrecisionResizeTierRatioFromSize(getPrecisionResizeTargetSize());
  }
  syncPrecisionAspectRatioHint();
}

function setPrecisionHelpTooltip(trigger, open) {
  if (!trigger) return;
  var tooltipId = trigger.getAttribute('aria-describedby');
  var tooltip = tooltipId ? document.getElementById(tooltipId) : null;
  trigger.dataset.precisionTooltipOpen = open ? 'true' : 'false';
  trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
  if (!tooltip) return;
  if (open) {
    tooltip.style.removeProperty('opacity');
    tooltip.style.removeProperty('visibility');
    tooltip.style.removeProperty('pointer-events');
  } else {
    tooltip.style.opacity = '0';
    tooltip.style.visibility = 'hidden';
    tooltip.style.pointerEvents = 'none';
  }
}

function bindPrecisionHelpTooltips() {
  var panel = document.getElementById('panelPrecisionEdit');
  if (!panel) return;
  panel.querySelectorAll('.precision-help-trigger').forEach(function(trigger) {
    if (trigger.dataset.precisionHelpBound === 'true') return;
    trigger.dataset.precisionHelpBound = 'true';
    var tooltipId = trigger.getAttribute('aria-describedby');
    if (tooltipId) trigger.setAttribute('aria-controls', tooltipId);
    setPrecisionHelpTooltip(trigger, false);
    trigger.addEventListener('focus', function() { setPrecisionHelpTooltip(trigger, true); });
    trigger.addEventListener('blur', function() { setPrecisionHelpTooltip(trigger, false); });
    trigger.addEventListener('click', function() { setPrecisionHelpTooltip(trigger, true); });
    trigger.addEventListener('keydown', function(event) {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      setPrecisionHelpTooltip(trigger, false);
    });
    var wrapper = trigger.closest('.precision-help-tip');
    if (wrapper) {
      wrapper.addEventListener('mouseenter', function() { setPrecisionHelpTooltip(trigger, true); });
      wrapper.addEventListener('mouseleave', function() {
        if (document.activeElement !== trigger) setPrecisionHelpTooltip(trigger, false);
      });
    }
  });
}

function setPrecisionWorkbenchHelp(open, returnFocus, resetState) {
  var trigger = document.getElementById('precisionWorkbenchHelpTrigger');
  var popover = document.getElementById('precisionWorkbenchHelpPopover');
  if (!trigger || !popover) return;
  if (!open && resetState && trigger._precisionHelpState) {
    trigger._precisionHelpState.pinned = false;
    trigger._precisionHelpState.hover = false;
    trigger._precisionHelpState.focusWithin = false;
    trigger._precisionHelpState.suppressNextFocus = false;
  }
  trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
  popover.classList.toggle('hidden', !open);
  if (!open && returnFocus && typeof trigger.focus === 'function') trigger.focus();
}

function bindPrecisionWorkbenchHelp() {
  var wrapper = document.getElementById('precisionWorkbenchHelp');
  var trigger = document.getElementById('precisionWorkbenchHelpTrigger');
  var popover = document.getElementById('precisionWorkbenchHelpPopover');
  if (!wrapper || !trigger || !popover || wrapper.dataset.precisionHelpBound === 'true') return;
  wrapper.dataset.precisionHelpBound = 'true';
  var state = trigger._precisionHelpState = {
    pinned: false,
    hover: false,
    focusWithin: false,
    suppressNextFocus: false
  };
  function showTransientHelp() {
    if (state.suppressNextFocus) {
      state.suppressNextFocus = false;
      return;
    }
    if (!state.pinned) setPrecisionWorkbenchHelp(true);
  }
  trigger.addEventListener('click', function(event) {
    event.preventDefault();
    state.pinned = !state.pinned;
    if (state.pinned) {
      setPrecisionWorkbenchHelp(true);
    } else {
      state.focusWithin = false;
      setPrecisionWorkbenchHelp(false);
    }
  });
  trigger.addEventListener('focus', function() {
    state.focusWithin = true;
    showTransientHelp();
  });
  wrapper.addEventListener('mouseenter', function() {
    state.hover = true;
    showTransientHelp();
  });
  wrapper.addEventListener('mouseleave', function() {
    state.hover = false;
    state.focusWithin = wrapper.contains(document.activeElement);
    if (!state.pinned && !state.focusWithin) setPrecisionWorkbenchHelp(false);
  });
  wrapper.addEventListener('focusout', function() {
    setTimeout(function() {
      state.focusWithin = wrapper.contains(document.activeElement);
      if (!state.pinned && !state.hover && !state.focusWithin) setPrecisionWorkbenchHelp(false);
    }, 0);
  });
  document.addEventListener('pointerdown', function(event) {
    if (trigger.getAttribute('aria-expanded') === 'true' && !wrapper.contains(event.target)) {
      state.pinned = false;
      state.hover = false;
      state.focusWithin = false;
      setPrecisionWorkbenchHelp(false);
    }
  });
  document.addEventListener('keydown', function(event) {
    if (event.key !== 'Escape' || trigger.getAttribute('aria-expanded') !== 'true') return;
    event.preventDefault();
    state.pinned = false;
    state.hover = false;
    state.focusWithin = false;
    var restoreFocus = document.activeElement !== trigger;
    state.suppressNextFocus = restoreFocus;
    setPrecisionWorkbenchHelp(false, restoreFocus);
  });
}

var precisionQuickStartShown = false;
var precisionQuickStartTimer = null;

function schedulePrecisionQuickStart() {
  if (precisionQuickStartShown || precisionQuickStartTimer !== null) return;
  try { if (window.localStorage.getItem('genbox_precision_quick_start_v1') === 'seen') return; } catch (error) {}
  precisionQuickStartTimer = setTimeout(function() {
    precisionQuickStartTimer = null;
    var panel = document.getElementById('panelPrecisionEdit');
    if (currentMode !== 'precision_edit' || getVisibleAppPage() !== 'generate' || !panel || !panel.getClientRects().length || precisionSourceTaskIsActive()) return;
    var overlays = document.querySelectorAll('[aria-modal="true"], .modal-overlay, #setupWizard, #welcomePage, #loginPage, #onboardingTour');
    if (Array.prototype.some.call(overlays, function(element) {
      var style = getComputedStyle(element);
      var rect = element.getBoundingClientRect();
      return element.getClientRects().length && style.display !== 'none' && style.visibility !== 'hidden'
        && rect.width > 0 && rect.height > 0 && rect.left < window.innerWidth && rect.right > 0
        && rect.top < window.innerHeight && rect.bottom > 0;
    })) {
      schedulePrecisionQuickStart();
      return;
    }
    if (openPrecisionDocsDialog()) precisionQuickStartShown = true;
  }, 500);
}

function navigatePrecisionQuickStart(area) {
  var selectors = {
    model: '#precisionModelPicker', source: '#precisionCanvasShell',
    size: '.precision-size-tool', generate: '#precisionGalleryCommandBar',
    local: '.precision-quick-tools'
  };
  if (!Object.prototype.hasOwnProperty.call(selectors, area)) return false;
  var target = document.querySelector(selectors[area]);
  if (!target) return false;
  closePrecisionDocsDialog(false);
  if (area === 'model') target.open = true;
  target.classList.add('precision-quick-nav-target');
  var previousTabindex = target.getAttribute('tabindex');
  target.setAttribute('tabindex', '-1');
  target.scrollIntoView({ block: 'center', behavior: 'auto' });
  target.focus({ preventScroll: true });
  target.addEventListener('blur', function cleanup() {
    target.classList.remove('precision-quick-nav-target');
    if (previousTabindex === null) target.removeAttribute('tabindex');
    else target.setAttribute('tabindex', previousTabindex);
  }, { once: true });
  return true;
}

function precisionDocsFocusable(dialog) {
  if (!dialog || !dialog.querySelectorAll) return [];
  return Array.prototype.filter.call(dialog.querySelectorAll('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])'), function(element) {
    return !element.disabled && !element.hidden && element.getAttribute('aria-hidden') !== 'true';
  });
}

function openPrecisionDocsDialog() {
  var dialog = document.getElementById('precisionDocsDialog');
  if (!dialog) return false;
  var gallery = document.getElementById('precisionGalleryOverlay');
  if (gallery && gallery.parentNode) gallery.parentNode.removeChild(gallery);
  dialog._precisionReturnFocus = document.activeElement && typeof document.activeElement.focus === 'function' ? document.activeElement : document.getElementById('btnPrecisionDocs');
  dialog.classList.remove('hidden');
  dialog.setAttribute('aria-hidden', 'false');
  if (document.body) document.body.classList.add('precision-docs-open');
  bindPrecisionDocsDialog();
  var body = document.getElementById('precisionDocsBody');
  if (body) body.scrollTop = 0;
  var close = document.getElementById('btnPrecisionDocsClose');
  var panel = document.getElementById('precisionDocsPanel');
  var target = close || panel;
  if (target && typeof target.focus === 'function') target.focus();
  return true;
}

function closePrecisionDocsDialog(returnFocus) {
  var dialog = document.getElementById('precisionDocsDialog');
  if (!dialog || dialog.classList.contains('hidden')) return false;
  var restore = dialog._precisionReturnFocus;
  dialog.classList.add('hidden');
  dialog.setAttribute('aria-hidden', 'true');
  if (document.body) document.body.classList.remove('precision-docs-open');
  dialog._precisionReturnFocus = null;
  precisionQuickStartShown = true;
  try { window.localStorage.setItem('genbox_precision_quick_start_v1', 'seen'); } catch (error) {}
  if (returnFocus !== false && restore && typeof restore.focus === 'function') restore.focus();
  return true;
}

function cancelPrecisionQuickStart() {
  if (precisionQuickStartTimer !== null) {
    clearTimeout(precisionQuickStartTimer);
    precisionQuickStartTimer = null;
  }
  closePrecisionDocsDialog(false);
}

function bindPrecisionDocsDialog() {
  var dialog = document.getElementById('precisionDocsDialog');
  if (!dialog || dialog.dataset.precisionDocsBound === 'true') return;
  dialog.dataset.precisionDocsBound = 'true';
  dialog.addEventListener('pointerdown', function(event) {
    if (event.target === dialog) closePrecisionDocsDialog();
  });
  dialog.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      closePrecisionDocsDialog();
      return;
    }
    if (event.key !== 'Tab') return;
    var focusable = precisionDocsFocusable(dialog);
    if (!focusable.length) {
      var panel = document.getElementById('precisionDocsPanel');
      if (panel && typeof panel.focus === 'function') panel.focus();
      event.preventDefault();
      return;
    }
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      last.focus();
      event.preventDefault();
    } else if (!event.shiftKey && document.activeElement === last) {
      first.focus();
      event.preventDefault();
    }
  });
}

function precisionCanvasResizeLimits(shell) {
  var stage = shell && shell.closest ? shell.closest('.precision-edit-stage-column') : null;
  var stageWidth = stage ? stage.clientWidth : 0;
  if (!stageWidth && stage && stage.getBoundingClientRect) stageWidth = stage.getBoundingClientRect().width;
  if (!stageWidth && shell && shell.parentElement) stageWidth = shell.parentElement.clientWidth;
  var viewportWidth = Math.max(document.documentElement && document.documentElement.clientWidth || 0, window.innerWidth || 0);
  var viewportHeight = Math.max(document.documentElement && document.documentElement.clientHeight || 0, window.innerHeight || 0);
  var maxHeight = viewportHeight ? Math.max(240, Math.min(760, viewportHeight - 120)) : 760;
  var heightLimitedWidth = precisionEditSourceHeight
    ? maxHeight * precisionEditSourceWidth / precisionEditSourceHeight
    : 1600;
  var max = Math.max(1, Math.min(1600, stageWidth || viewportWidth || 1600, heightLimitedWidth || 1600));
  var min = Math.min(max, max <= 480 ? 180 : 280);
  return { min: min, max: max, maxHeight: maxHeight, stageWidth: stageWidth };
}

function positionPrecisionCanvasResizeHandle() {
  var shell = document.getElementById('precisionCanvasShell');
  var handle = document.getElementById('precisionCanvasResizeHandle');
  var parent = handle && handle.offsetParent;
  if (!shell || !handle || !parent || shell.classList.contains('is-empty') || !shell.getBoundingClientRect || !parent.getBoundingClientRect) return;
  var shellRect = shell.getBoundingClientRect();
  var parentRect = parent.getBoundingClientRect();
  var width = handle.offsetWidth || 44;
  var height = handle.offsetHeight || 44;
  var left;
  var top;
  if (parent === shell) {
    // The handle is an absolutely positioned child of the scroll container.
    // Convert the visible lower-right corner back into the container's content
    // coordinate system so zoom/pan scroll offsets cannot carry it away.
    left = Math.max(0, (shell.scrollLeft || 0) + (shell.clientWidth || shellRect.width) - width);
    top = Math.max(0, (shell.scrollTop || 0) + (shell.clientHeight || shellRect.height) - height);
  } else {
    // Keep this robust if a future wrapper becomes the offset parent.
    left = Math.max(0, shellRect.left + (shell.clientLeft || 0) + (shell.clientWidth || shellRect.width) - parentRect.left - (parent.clientLeft || 0) + (parent.scrollLeft || 0) - width);
    top = Math.max(0, shellRect.top + (shell.clientTop || 0) + (shell.clientHeight || shellRect.height) - parentRect.top - (parent.clientTop || 0) + (parent.scrollTop || 0) - height);
  }
  handle.style.right = 'auto';
  handle.style.bottom = 'auto';
  handle.style.left = left + 'px';
  handle.style.top = top + 'px';
}

function applyPrecisionCanvasVisualSize(width) {
  var shell = document.getElementById('precisionCanvasShell');
  var surface = document.getElementById('precisionCanvasSurface');
  if (!shell || !precisionEditSourceWidth || !precisionEditSourceHeight) return;
  var limits = precisionCanvasResizeLimits(shell);
  var measuredWidth = shell.getBoundingClientRect ? shell.getBoundingClientRect().width : shell.clientWidth;
  var visualWidth = Math.max(limits.min, Math.min(limits.max, Number(width) || measuredWidth || limits.max));
  var visualHeight = visualWidth * precisionEditSourceHeight / precisionEditSourceWidth;
  shell.style.width = visualWidth + 'px';
  shell.style.height = visualHeight + 'px';
  shell.style.aspectRatio = precisionEditSourceWidth + ' / ' + precisionEditSourceHeight;
  if (surface) {
    surface.style.width = precisionViewZoom + '%';
    surface.style.aspectRatio = precisionEditSourceWidth + ' / ' + precisionEditSourceHeight;
  }
  var schedule = typeof requestAnimationFrame === 'function' ? requestAnimationFrame : function(callback) { callback(); };
  schedule(function() {
    if (typeof positionPrecisionCanvasResizeHandle === 'function') positionPrecisionCanvasResizeHandle();
  });
}

function reflowPrecisionCanvasVisualSize(force) {
  var shell = document.getElementById('precisionCanvasShell');
  if (!shell || shell.classList.contains('is-empty') || !precisionEditSourceWidth || !precisionEditSourceHeight) return;
  var inlineWidth = parseFloat(shell.style.width);
  if (!force && !Number.isFinite(inlineWidth)) return;
  var measuredWidth = shell.getBoundingClientRect ? shell.getBoundingClientRect().width : shell.clientWidth;
  applyPrecisionCanvasVisualSize(Number.isFinite(inlineWidth) ? inlineWidth : measuredWidth);
}

function beginPrecisionCanvasResize(event) {
  var handle = event && event.currentTarget;
  var shell = document.getElementById('precisionCanvasShell');
  if (!event || event.isPrimary === false || (event.button !== undefined && event.button !== 0)) return;
  if (!handle || !shell || shell.classList.contains('is-empty') || !precisionEditSourceWidth || !precisionEditSourceHeight) return;
  if (precisionCanvasResizeState) endPrecisionCanvasResize();
  var rect = shell.getBoundingClientRect();
  precisionCanvasResizeState = { pointerId: event.pointerId, startX: event.clientX, startWidth: rect.width || shell.clientWidth, handle: handle, shell: shell };
  shell.classList.add('is-resizing');
  if (handle.setPointerCapture) { try { handle.setPointerCapture(event.pointerId); } catch (ignore) {} }
  window.addEventListener('pointermove', continuePrecisionCanvasResize, { passive: false });
  window.addEventListener('pointerup', endPrecisionCanvasResize);
  window.addEventListener('pointercancel', endPrecisionCanvasResize);
  event.preventDefault();
}

function continuePrecisionCanvasResize(event) {
  var state = precisionCanvasResizeState;
  if (!state || state.pointerId !== event.pointerId) return;
  applyPrecisionCanvasVisualSize(state.startWidth + event.clientX - state.startX);
  event.preventDefault();
}

function endPrecisionCanvasResize(event) {
  var state = precisionCanvasResizeState;
  if (!state || (event && event.pointerId !== undefined && state.pointerId !== event.pointerId)) return;
  precisionCanvasResizeState = null;
  window.removeEventListener('pointermove', continuePrecisionCanvasResize);
  window.removeEventListener('pointerup', endPrecisionCanvasResize);
  window.removeEventListener('pointercancel', endPrecisionCanvasResize);
  if (state.shell) state.shell.classList.remove('is-resizing');
  if (state.handle && state.handle.releasePointerCapture) {
    try { state.handle.releasePointerCapture(state.pointerId); } catch (ignore) {}
  }
}

function bindPrecisionCanvasResizeHandle() {
  var handle = document.getElementById('precisionCanvasResizeHandle');
  if (!handle || handle.dataset.precisionResizeBound === 'true') return;
  handle.dataset.precisionResizeBound = 'true';
  handle.addEventListener('pointerdown', beginPrecisionCanvasResize);
  handle.addEventListener('lostpointercapture', endPrecisionCanvasResize);
  handle.addEventListener('keydown', function(event) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    var shell = document.getElementById('precisionCanvasShell');
    if (!shell || shell.classList.contains('is-empty')) return;
    var width = shell.getBoundingClientRect ? shell.getBoundingClientRect().width : shell.clientWidth;
    applyPrecisionCanvasVisualSize(width + (event.key === 'ArrowRight' ? 24 : -24));
    event.preventDefault();
  });
  var shell = document.getElementById('precisionCanvasShell');
  var stage = shell && shell.closest ? shell.closest('.precision-edit-stage-column') : null;
  var reflow = function() {
    if (!precisionCanvasResizeState) reflowPrecisionCanvasVisualSize(false);
    if (typeof positionPrecisionCanvasResizeHandle === 'function') positionPrecisionCanvasResizeHandle();
  };
  if (shell && typeof positionPrecisionCanvasResizeHandle === 'function') {
    shell.addEventListener('scroll', positionPrecisionCanvasResizeHandle, { passive: true });
  }
  if (stage && typeof ResizeObserver === 'function') {
    handle._precisionCanvasResizeObserver = new ResizeObserver(reflow);
    handle._precisionCanvasResizeObserver.observe(stage);
  }
  window.addEventListener('resize', reflow);
  window.addEventListener('orientationchange', reflow);
}

function precisionCanvasVerticalResizeLimits(stage) {
  var rect = stage && stage.getBoundingClientRect ? stage.getBoundingClientRect() : null;
  var available = rect && rect.height ? rect.height : (window.innerHeight || 0);
  var minimumGallery = Math.min(220, Math.max(120, available * 0.24));
  var min = Math.min(Math.max(220, available * 0.32), Math.max(180, available - minimumGallery));
  var max = Math.max(min, available - minimumGallery);
  return { min: min, max: max, available: available, minimumGallery: minimumGallery };
}

function setPrecisionCanvasVerticalSize(height) {
  var panel = document.getElementById('panelPrecisionEdit');
  var stage = document.querySelector('#panelPrecisionEdit .precision-edit-stage-column');
  var shell = document.getElementById('precisionCanvasShell');
  var showcase = document.getElementById('precisionSessionShowcase');
  if (!panel || document.fullscreenElement !== panel || !stage || !shell) return false;
  var limits = precisionCanvasVerticalResizeLimits(stage);
  var value = Math.max(limits.min, Math.min(limits.max, Number(height) || limits.min));
  if (!precisionCanvasVerticalResizeRestore) {
    precisionCanvasVerticalResizeRestore = {
      shellHeight: shell.style.height,
      shellFlexBasis: shell.style.flexBasis,
      stageCanvasSize: stage.style.getPropertyValue('--precision-canvas-vertical-size'),
      stageGallerySize: stage.style.getPropertyValue('--precision-session-gallery-size')
    };
  }
  stage.style.setProperty('--precision-canvas-vertical-size', Math.round(value) + 'px');
  stage.style.setProperty('--precision-session-gallery-size', Math.round(Math.max(limits.minimumGallery, limits.available - value)) + 'px');
  shell.style.height = Math.round(value) + 'px';
  shell.style.flexBasis = Math.round(value) + 'px';
  if (showcase) showcase.style.setProperty('--precision-session-gallery-size', Math.round(Math.max(limits.minimumGallery, limits.available - value)) + 'px');
  var handle = document.getElementById('precisionCanvasVerticalResizeHandle');
  if (handle) {
    handle.setAttribute('aria-valuemin', String(Math.round(limits.min)));
    handle.setAttribute('aria-valuemax', String(Math.round(limits.max)));
    handle.setAttribute('aria-valuenow', String(Math.round(value)));
  }
  return value;
}

function clearPrecisionCanvasVerticalSize() {
  var stage = document.querySelector('#panelPrecisionEdit .precision-edit-stage-column');
  var shell = document.getElementById('precisionCanvasShell');
  var showcase = document.getElementById('precisionSessionShowcase');
  var restore = precisionCanvasVerticalResizeRestore;
  if (stage) {
    stage.style.setProperty('--precision-canvas-vertical-size', restore ? restore.stageCanvasSize : '');
    stage.style.setProperty('--precision-session-gallery-size', restore ? restore.stageGallerySize : '');
  }
  if (showcase) showcase.style.removeProperty('--precision-session-gallery-size');
  if (shell && restore) {
    shell.style.height = restore.shellHeight;
    shell.style.flexBasis = restore.shellFlexBasis;
  }
  precisionCanvasVerticalResizeRestore = null;
}

function beginPrecisionCanvasVerticalResize(event) {
  var handle = event && event.currentTarget;
  var panel = document.getElementById('panelPrecisionEdit');
  var stage = handle && handle.closest ? handle.closest('.precision-edit-stage-column') : null;
  var shell = document.getElementById('precisionCanvasShell');
  if (!event || event.isPrimary === false || (event.button !== undefined && event.button !== 0) || !handle || !panel || document.fullscreenElement !== panel || !stage || !shell) return;
  if (precisionCanvasVerticalResizeState) endPrecisionCanvasVerticalResize();
  var rect = shell.getBoundingClientRect();
  precisionCanvasVerticalResizeState = { pointerId: event.pointerId, startY: event.clientY, startHeight: rect.height || shell.clientHeight, handle: handle, stage: stage };
  stage.classList.add('is-canvas-vertical-resizing');
  if (handle.setPointerCapture) { try { handle.setPointerCapture(event.pointerId); } catch (ignore) {} }
  window.addEventListener('pointermove', continuePrecisionCanvasVerticalResize, { passive: false });
  window.addEventListener('pointerup', endPrecisionCanvasVerticalResize);
  window.addEventListener('pointercancel', endPrecisionCanvasVerticalResize);
  event.preventDefault();
}

function continuePrecisionCanvasVerticalResize(event) {
  var state = precisionCanvasVerticalResizeState;
  if (!state || state.pointerId !== event.pointerId) return;
  setPrecisionCanvasVerticalSize(state.startHeight + event.clientY - state.startY);
  event.preventDefault();
}

function endPrecisionCanvasVerticalResize(event) {
  var state = precisionCanvasVerticalResizeState;
  if (!state || (event && event.pointerId !== undefined && state.pointerId !== event.pointerId)) return;
  precisionCanvasVerticalResizeState = null;
  window.removeEventListener('pointermove', continuePrecisionCanvasVerticalResize);
  window.removeEventListener('pointerup', endPrecisionCanvasVerticalResize);
  window.removeEventListener('pointercancel', endPrecisionCanvasVerticalResize);
  if (state.stage) state.stage.classList.remove('is-canvas-vertical-resizing');
  if (state.handle && state.handle.releasePointerCapture) {
    try { state.handle.releasePointerCapture(state.pointerId); } catch (ignore) {}
  }
}

function bindPrecisionCanvasVerticalResizeHandle() {
  var handle = document.getElementById('precisionCanvasVerticalResizeHandle');
  if (!handle || handle.dataset.precisionResizeBound === 'true') return;
  handle.dataset.precisionResizeBound = 'true';
  handle.addEventListener('pointerdown', beginPrecisionCanvasVerticalResize);
  handle.addEventListener('lostpointercapture', endPrecisionCanvasVerticalResize);
  handle.addEventListener('keydown', function(event) {
    var panel = document.getElementById('panelPrecisionEdit');
    if (!panel || document.fullscreenElement !== panel) return;
    var stage = handle.closest ? handle.closest('.precision-edit-stage-column') : null;
    var shell = document.getElementById('precisionCanvasShell');
    if (!stage || !shell) return;
    var limits = precisionCanvasVerticalResizeLimits(stage);
    var current = shell.getBoundingClientRect ? shell.getBoundingClientRect().height : shell.clientHeight;
    var next = current;
    if (event.key === 'ArrowUp') next -= 24;
    else if (event.key === 'ArrowDown') next += 24;
    else if (event.key === 'Home') next = limits.min;
    else if (event.key === 'End') next = limits.max;
    else return;
    setPrecisionCanvasVerticalSize(next);
    event.preventDefault();
  });
}

function precisionInspectorResizeLimits(workspace) {
  var total = workspace && workspace.getBoundingClientRect ? workspace.getBoundingClientRect().width : 0;
  if (!total) total = workspace && workspace.clientWidth || window.innerWidth || 1280;
  var min = Math.min(300, Math.max(220, total * 0.28));
  var max = Math.max(min, Math.min(560, total * 0.52));
  return { min: min, max: max, total: total };
}

function setPrecisionInspectorWidth(width, persist) {
  var workspace = document.querySelector('#pageGenerate.precision-workbench .precision-edit-workspace') || document.querySelector('.precision-edit-workspace');
  if (!workspace) return false;
  var limits = precisionInspectorResizeLimits(workspace);
  var value = Math.max(limits.min, Math.min(limits.max, Number(width) || limits.min));
  workspace.style.setProperty('--precision-inspector-width', value + 'px');
  var handle = document.getElementById('precisionInspectorResizeHandle');
  if (handle) {
    handle.setAttribute('aria-valuemin', String(Math.round(limits.min)));
    handle.setAttribute('aria-valuemax', String(Math.round(limits.max)));
    handle.setAttribute('aria-valuenow', String(Math.round(value)));
  }
  if (persist !== false) {
    try { localStorage.setItem(PRECISION_INSPECTOR_WIDTH_STORAGE_KEY, String(Math.round(value))); } catch (error) {}
  }
  return value;
}

function beginPrecisionInspectorResize(event) {
  var handle = event && event.currentTarget;
  var workspace = handle && handle.closest ? handle.closest('.precision-edit-workspace') : null;
  var inspector = handle && handle.closest ? handle.closest('.precision-edit-inspector') : null;
  if (!event || event.isPrimary === false || (event.button !== undefined && event.button !== 0) || !workspace || !inspector) return;
  if (window.matchMedia && window.matchMedia('(max-width: 900px)').matches) return;
  var rect = inspector.getBoundingClientRect();
  precisionInspectorResizeState = { pointerId: event.pointerId, startX: event.clientX, startWidth: rect.width || inspector.clientWidth, handle: handle, workspace: workspace };
  workspace.classList.add('is-inspector-resizing');
  if (handle.setPointerCapture) { try { handle.setPointerCapture(event.pointerId); } catch (ignore) {} }
  window.addEventListener('pointermove', continuePrecisionInspectorResize, { passive: false });
  window.addEventListener('pointerup', endPrecisionInspectorResize);
  window.addEventListener('pointercancel', endPrecisionInspectorResize);
  event.preventDefault();
}

function continuePrecisionInspectorResize(event) {
  var state = precisionInspectorResizeState;
  if (!state || state.pointerId !== event.pointerId) return;
  setPrecisionInspectorWidth(state.startWidth - (event.clientX - state.startX));
  event.preventDefault();
}

function endPrecisionInspectorResize(event) {
  var state = precisionInspectorResizeState;
  if (!state || (event && event.pointerId !== undefined && state.pointerId !== event.pointerId)) return;
  precisionInspectorResizeState = null;
  window.removeEventListener('pointermove', continuePrecisionInspectorResize);
  window.removeEventListener('pointerup', endPrecisionInspectorResize);
  window.removeEventListener('pointercancel', endPrecisionInspectorResize);
  if (state.workspace) state.workspace.classList.remove('is-inspector-resizing');
  if (state.handle && state.handle.releasePointerCapture) {
    try { state.handle.releasePointerCapture(state.pointerId); } catch (ignore) {}
  }
}

function bindPrecisionInspectorResizeHandle() {
  var handle = document.getElementById('precisionInspectorResizeHandle');
  if (!handle || handle.dataset.precisionResizeBound === 'true') return;
  handle.dataset.precisionResizeBound = 'true';
  handle.addEventListener('pointerdown', beginPrecisionInspectorResize);
  handle.addEventListener('lostpointercapture', endPrecisionInspectorResize);
  handle.addEventListener('keydown', function(event) {
    var workspace = handle.closest ? handle.closest('.precision-edit-workspace') : null;
    if (!workspace || (window.matchMedia && window.matchMedia('(max-width: 900px)').matches)) return;
    var inspector = document.querySelector('#pageGenerate.precision-workbench .precision-edit-inspector') || document.querySelector('.precision-edit-inspector');
    var current = inspector && inspector.getBoundingClientRect ? inspector.getBoundingClientRect().width : 0;
    var limits = precisionInspectorResizeLimits(workspace);
    var next = current;
    if (event.key === 'ArrowLeft') next -= 24;
    else if (event.key === 'ArrowRight') next += 24;
    else if (event.key === 'Home') next = limits.min;
    else if (event.key === 'End') next = limits.max;
    else return;
    setPrecisionInspectorWidth(next);
    event.preventDefault();
  });
  var saved = null;
  try { saved = Number(localStorage.getItem(PRECISION_INSPECTOR_WIDTH_STORAGE_KEY)); } catch (error) {}
  if (Number.isFinite(saved) && saved > 0) setPrecisionInspectorWidth(saved, false);
  var reflow = function() {
    if (precisionInspectorResizeState) return;
    var workspace = handle.closest ? handle.closest('.precision-edit-workspace') : null;
    var inspector = handle.closest ? handle.closest('.precision-edit-inspector') : null;
    if (!workspace || !inspector || (window.matchMedia && window.matchMedia('(max-width: 900px)').matches)) return;
    var current = inspector.getBoundingClientRect ? inspector.getBoundingClientRect().width : inspector.clientWidth;
    if (current) setPrecisionInspectorWidth(current, false);
  };
  window.addEventListener('resize', reflow);
  window.addEventListener('orientationchange', reflow);
}

function getPrecisionCutoutControls() {
  return {
    button: document.getElementById('btnPrecisionCutout'),
    simpleButton: document.getElementById('btnPrecisionCutoutSimple'),
    professionalRunButton: document.getElementById('btnPrecisionCutoutProfessionalRun'),
    simpleAlgorithm: document.getElementById('precisionCutoutSimpleAlgorithm'),
    simpleModeButton: document.getElementById('btnPrecisionCutoutSimpleMode'),
    professionalModeButton: document.getElementById('btnPrecisionCutoutProfessionalMode'),
    professionalOpenButton: document.getElementById('btnPrecisionCutoutProfessionalOpen'),
    professionalDialog: document.getElementById('precisionCutoutProfessionalDialog'),
    professionalCloseButton: document.getElementById('btnPrecisionCutoutProfessionalClose'),
    professionalCollapseButton: document.getElementById('btnPrecisionCutoutProfessionalCollapse'),
    professionalResizeHandle: document.getElementById('precisionCutoutProfessionalResizeHandle'),
    professionalAlgorithm: document.getElementById('precisionCutoutProfessionalAlgorithm'),
    professionalAlgorithmStatus: document.getElementById('precisionCutoutProfessionalAlgorithmStatus'),
    professionalRefreshButton: document.getElementById('btnPrecisionCutoutProfessionalRefresh'),
    professionalFeather: document.getElementById('precisionCutoutProfessionalFeather'),
    professionalFeatherValue: document.getElementById('precisionCutoutProfessionalFeatherValue'),
    professionalUseSelection: document.getElementById('precisionCutoutProfessionalUseSelection'),
    professionalRestoreMode: document.getElementById('precisionCutoutProfessionalRestoreMode'),
    professionalRestoreMinAlpha: document.getElementById('precisionCutoutProfessionalRestoreMinAlpha'),
    professionalRestoreMinAlphaValue: document.getElementById('precisionCutoutProfessionalRestoreMinAlphaValue'),
    professionalRefineHint: document.getElementById('precisionCutoutProfessionalRefineHint'),
    professionalRefineButton: document.getElementById('btnPrecisionCutoutProfessionalRefine'),
    refineButton: document.getElementById('btnPrecisionCutoutRefine'),
    cancelButton: document.getElementById('btnPrecisionCutoutCancel'),
    feather: document.getElementById('precisionCutoutFeather'),
    featherValue: document.getElementById('precisionCutoutFeatherValue'),
    useSelection: document.getElementById('precisionCutoutUseSelection'),
    restoreMode: document.getElementById('precisionCutoutRestoreMode'),
    restoreMinAlpha: document.getElementById('precisionCutoutRestoreMinAlpha'),
    restoreMinAlphaValue: document.getElementById('precisionCutoutRestoreMinAlphaValue'),
    restoreHint: document.getElementById('precisionCutoutRestoreHint'),
    selectionHint: document.getElementById('precisionCutoutSelectionHint'),
    status: document.getElementById('precisionCutoutStatus'),
    adapterPanel: document.getElementById('precisionCutoutAdapterPicker'),
    adapterSelect: document.getElementById('precisionCutoutAlgorithm'),
    capabilityRefreshButton: document.getElementById('btnPrecisionCutoutCapabilityRefresh'),
    adapterStatus: document.getElementById('precisionCutoutAlgorithmStatus'),
    adapterDetailsToggle: document.getElementById('btnPrecisionCutoutAdapterDetails'),
    adapterDetails: document.getElementById('precisionCutoutAdapterDetails'),
    modelPanel: document.getElementById('precisionCutoutModelInstall'),
    modelStatus: document.getElementById('precisionCutoutModelStatus'),
    modelDetailsToggle: document.getElementById('btnPrecisionCutoutModelDetails'),
    modelDetails: document.getElementById('precisionCutoutModelDetails'),
    modelSource: document.getElementById('precisionCutoutModelSource'),
    modelSize: document.getElementById('precisionCutoutModelSize'),
    modelPath: document.getElementById('precisionCutoutModelPath'),
    modelProgress: document.getElementById('precisionCutoutModelProgress'),
    modelProgressBar: document.getElementById('precisionCutoutModelProgressBar'),
    modelProgressText: document.getElementById('precisionCutoutModelProgressText'),
    modelInstallButton: document.getElementById('btnPrecisionCutoutModelInstall'),
    modelCancelButton: document.getElementById('btnPrecisionCutoutModelCancel'),
    modelRetryButton: document.getElementById('btnPrecisionCutoutModelRetry'),
    modelRemoveCorruptButton: document.getElementById('btnPrecisionCutoutModelRemoveCorrupt'),
    modelDeleteButton: document.getElementById('btnPrecisionCutoutModelDelete')
  };
}

function precisionEditToolButton(tool, labelKey) {
  return '<button type="button" class="btn-ghost" id="precisionTool' + tool.charAt(0).toUpperCase() + tool.slice(1) + '" onclick="setPrecisionEditTool(\'' + tool + '\')" title="' + escAttr(i18nText(labelKey)) + '">' + escHtml(i18nText(labelKey)) + '</button>';
}

function precisionEditClone(value) {
  return JSON.parse(JSON.stringify(value || []));
}

function precisionEditNewId() {
  precisionEditIdCounter += 1;
  return 'annotation-' + Date.now().toString(36) + '-' + precisionEditIdCounter;
}

function precisionEditNewLabel() {
  precisionEditLabelCounter += 1;
  return precisionEditLabelCounter;
}

function precisionSourceTaskIsActive() {
  var monitorStatus = String(precisionTaskMonitorData && precisionTaskMonitorData.status || '').toLowerCase();
  var monitorActive = ['queued', 'running', 'generating', 'stopping', 'cancelling'].indexOf(monitorStatus) !== -1;
  return !!(genIsPrecisionTask && (genCurrentGenId || genCancelRequested || ['submitting', 'generating', 'cancelling'].indexOf(precisionGenerationControlState) !== -1)) || monitorActive;
}

function setPrecisionSourceMenuOpen(open, restoreFocus) {
  var menu = document.getElementById('precisionSourceMenu');
  var trigger = document.getElementById('btnPrecisionReplaceSource');
  if (!menu || !trigger) return false;
  var wasOpen = !menu.hidden;
  var nextOpen = !!open && !trigger.disabled && !!precisionEditSourceImageData;
  menu.hidden = !nextOpen;
  trigger.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  if (nextOpen) {
    // Keep the compact source chooser within the viewport when the left action
    // cluster is close to a narrow viewport edge.
    if (menu.style) {
      menu.style.left = '';
      menu.style.right = '';
    }
    if (menu.style && typeof menu.getBoundingClientRect === 'function') {
      var menuRect = menu.getBoundingClientRect();
      var viewportWidth = Math.max(document.documentElement && document.documentElement.clientWidth || 0, window.innerWidth || 0);
      if (viewportWidth && menuRect.right > viewportWidth) {
        menu.style.left = Math.min(0, viewportWidth - menuRect.right - 8) + 'px';
      }
      if (menuRect.left < 0) menu.style.left = '0px';
    }
    var first = menu.querySelector && menu.querySelector('[role="menuitem"]:not(:disabled)');
    if (first && typeof first.focus === 'function') first.focus();
  } else if (restoreFocus && wasOpen && typeof trigger.focus === 'function') {
    trigger.focus();
  }
  return wasOpen;
}

function togglePrecisionSourceMenu() {
  var menu = document.getElementById('precisionSourceMenu');
  var trigger = document.getElementById('btnPrecisionReplaceSource');
  if (!menu || !trigger || trigger.disabled || !precisionEditSourceImageData) return false;
  setPrecisionSourceMenuOpen(menu.hidden);
  return !menu.hidden;
}

function choosePrecisionLocalSource() {
  setPrecisionSourceMenuOpen(false);
  return requestPrecisionLocalSource();
}

function choosePrecisionGallerySource() {
  var trigger = document.getElementById('btnPrecisionReplaceSource');
  setPrecisionSourceMenuOpen(false, true);
  return openPrecisionGalleryPicker(trigger);
}

function handlePrecisionSourceMenuKeydown(event) {
  var menu = document.getElementById('precisionSourceMenu');
  if (!menu || menu.hidden) return;
  if (event.key === 'Escape') {
    event.preventDefault();
    event.stopPropagation();
    setPrecisionSourceMenuOpen(false, true);
    return;
  }
  if (['ArrowDown', 'ArrowUp', 'Home', 'End'].indexOf(event.key) === -1) return;
  var items = Array.prototype.slice.call(menu.querySelectorAll('[role="menuitem"]:not(:disabled)'));
  if (!items.length) return;
  event.preventDefault();
  var current = items.indexOf(document.activeElement);
  if (event.key === 'Home') current = 0;
  else if (event.key === 'End') current = items.length - 1;
  else if (event.key === 'ArrowDown') current = (current + 1 + items.length) % items.length;
  else current = (current - 1 + items.length) % items.length;
  items[current].focus();
}

function updatePrecisionSourceActions() {
  var actions = document.getElementById('precisionSourceActions');
  var replace = document.getElementById('btnPrecisionReplaceSource');
  var local = document.getElementById('btnPrecisionReplaceLocal');
  var gallery = document.getElementById('btnPrecisionReplaceFromGallery');
  var hint = document.getElementById('precisionReplaceDisabledHint');
  var hasSource = !!precisionEditSourceImageData;
  var blocked = precisionSourceTaskIsActive() || (typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending);
  if (actions) actions.classList.toggle('hidden', !hasSource);
  if (hint) {
    hint.classList.toggle('sr-only', !blocked);
    hint.classList.toggle('is-visible', blocked);
  }
  [replace, local, gallery].forEach(function(button) {
    if (!button) return;
    button.disabled = blocked;
    button.setAttribute('aria-disabled', blocked ? 'true' : 'false');
    if (blocked) button.setAttribute('aria-describedby', 'precisionReplaceDisabledHint');
    else button.removeAttribute('aria-describedby');
  });
  if (!hasSource || blocked) setPrecisionSourceMenuOpen(false);
}

function precisionSourceHasDirtyState() {
  var width = parseInt((document.getElementById('precisionResizeWidth') || { value: '' }).value, 10);
  var height = parseInt((document.getElementById('precisionResizeHeight') || { value: '' }).value, 10);
  var resizePrompt = String((document.getElementById('precisionResizePrompt') || { value: '' }).value || '').trim();
  var overallPrompt = String((document.getElementById('txtPromptPrecision') || { value: '' }).value || '').trim();
  return !!(
    precisionEditObjects.length || precisionEditHistory.length || precisionEditRedo.length ||
    precisionEditSelectedId || precisionEditDraftObject || precisionEditPointerId !== null ||
    precisionEditPointerTarget || precisionEditDragOrigin || precisionEditDragMoved ||
    precisionEditTextDraftPoint || precisionEditPendingInstruction || precisionEditEraserSnapshot || precisionEditEraserChanged ||
    precisionEditSession.versions.length || precisionEditSession.selectedVersionId !== 'original' || precisionEditSession.baseVersionId !== 'original' ||
    (typeof precisionEditStrategy === 'string' && precisionEditStrategy !== 'standard') ||
    (typeof precisionEditSelectionMode === 'string' && precisionEditSelectionMode !== 'annotation') ||
    (typeof precisionSelectionFeather === 'number' && precisionSelectionFeather !== 0) ||
    precisionEditSizeMode !== 'preserve' || resizePrompt || overallPrompt ||
    (Number.isFinite(width) && precisionEditSourceWidth && width !== precisionEditSourceWidth) ||
    (Number.isFinite(height) && precisionEditSourceHeight && height !== precisionEditSourceHeight) ||
    precisionCutoutPending || precisionEditSession.taskId || precisionTaskMonitorData
  );
}

function preparePrecisionSourceReplacement() {
  if (typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending) {
    setStatus(i18nText('common.loading'));
    return false;
  }
  if (precisionSourceTaskIsActive()) {
    setStatus(i18nText('creator.precision_replace_task_active'));
    return false;
  }
  if (precisionEditSourceImageData && precisionSourceHasDirtyState() && !confirm(i18nText('creator.precision_replace_confirm'))) return false;
  return true;
}

function requestPrecisionLocalSource() {
  if (!preparePrecisionSourceReplacement()) return false;
  var input = document.getElementById('precisionFileInput');
  if (!input) return false;
  var generation = ++precisionSourceLoadGeneration;
  precisionPendingSourceIntent = {
    approved: true,
    generation: generation,
    taskEpoch: precisionSourceTaskEpoch
  };
  input.click();
  return true;
}

function resetPrecisionSourceSpecificState(generation) {
  precisionVersionLoadToken += 1;
  if (typeof precisionBaseVersionSwitchPending !== 'undefined') precisionBaseVersionSwitchPending = false;
  precisionCutoutProbeToken += 1;
  precisionCutoutOperationToken += 1;
  if (typeof precisionCutoutAbortController !== 'undefined' && precisionCutoutAbortController) {
    try { precisionCutoutAbortController.abort(); } catch (ignore) {}
    precisionCutoutAbortController = null;
  }
  if (precisionCanvasResizeState) endPrecisionCanvasResize();
  if (precisionEditPointerTarget && precisionEditPointerTarget.releasePointerCapture && precisionEditPointerId !== null) {
    try { precisionEditPointerTarget.releasePointerCapture(precisionEditPointerId); } catch (ignore) {}
  }
  cancelPrecisionEditText();
  precisionEditSourceImageData = null;
  precisionEditSourceImage = null;
  precisionEditSourceWidth = 0;
  precisionEditSourceHeight = 0;
  precisionEditObjects = [];
  precisionEditHistory = [];
  precisionEditRedo = [];
  precisionEditSelectedId = null;
  precisionEditDraftObject = null;
  precisionEditPointerId = null;
  precisionEditPointerTarget = null;
  precisionEditPointerFinishing = false;
  precisionEditDragOrigin = null;
  precisionEditDragMoved = false;
  precisionEditGestureCheckpoint = null;
  precisionEditTextDraftPoint = null;
  precisionEditPendingInstruction = '';
  precisionEditEraserSnapshot = null;
  precisionEditEraserChanged = false;
  precisionCanvasPanState = null;
  precisionCanvasSpaceHeld = false;
  precisionEditIdCounter = 0;
  precisionEditLabelCounter = 0;
  if (typeof resetPrecisionAnnotationInstructionPopover === 'function') resetPrecisionAnnotationInstructionPopover();
  precisionComparePointerId = null;
  precisionComparePointerTarget = null;
  precisionEditSizeMode = 'preserve';
  precisionEditStrategy = 'standard';
  precisionEditSelectionMode = 'annotation';
  precisionSelectionFeather = 0;
  precisionCutoutPending = false;
  precisionTaskSourceGeneration = 0;
  precisionEditSession = { source: null, versions: [], selectedVersionId: 'original', baseVersionId: 'original', taskBaseVersionId: null, view: 'after', taskId: null, sourceGeneration: generation };
  if (lastGenContext && lastGenContext.mode === 'precision_edit') lastGenContext = null;
  updatePrecisionTaskMonitor(null);
  ['txtPromptPrecision', 'precisionResizeWidth', 'precisionResizeHeight', 'precisionResizePrompt', 'precisionResizePresetName'].forEach(function(id) {
    var field = document.getElementById(id);
    if (field) field.value = '';
  });
  var resizePreset = document.getElementById('precisionResizePreset');
  var resizePromptPreset = document.getElementById('precisionResizePromptPreset');
  var selectionFeather = document.getElementById('precisionSelectionFeather');
  var rail = document.getElementById('precisionVersionRail');
  var before = document.getElementById('precisionCompareBefore');
  var after = document.getElementById('precisionCompareAfter');
  var imageInfo = document.getElementById('precisionCanvasImageInfo');
  if (resizePreset) resizePreset.value = 'custom';
  if (resizePromptPreset) resizePromptPreset.value = '';
  if (selectionFeather) selectionFeather.value = '0';
  if (typeof setPrecisionEditStrategy === 'function') setPrecisionEditStrategy(precisionEditStrategy);
  if (typeof setPrecisionEditSelectionMode === 'function') setPrecisionEditSelectionMode(precisionEditSelectionMode);
  if (rail) rail.textContent = '';
  if (before) before.removeAttribute('src');
  if (after) after.removeAttribute('src');
  if (imageInfo) { imageInfo.hidden = true; imageInfo.textContent = ''; }
}

function loadPrecisionEditLocalFile(event) {
  var input = event && event.currentTarget;
  if (typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending) {
    precisionPendingSourceIntent = null;
    if (input) input.value = '';
    if (typeof setStatus === 'function') setStatus(i18nText('common.loading'));
    return false;
  }
  if (typeof precisionSourceTaskIsActive === 'function' && precisionSourceTaskIsActive()) {
    precisionPendingSourceIntent = null;
    if (input) input.value = '';
    if (typeof setStatus === 'function') setStatus(i18nText('creator.precision_replace_task_active'));
    return false;
  }
  var file = input && input.files && input.files[0];
  if (!file) {
    precisionPendingSourceIntent = null;
    return false;
  }
  if (!/^image\//.test(file.type || '')) {
    alert(i18nText('creator.precision_edit_file_required'));
    input.value = '';
    precisionPendingSourceIntent = null;
    return false;
  }
  var intent = precisionPendingSourceIntent;
  precisionPendingSourceIntent = null;
  var currentTaskEpoch = typeof precisionSourceTaskEpoch === 'number' ? precisionSourceTaskEpoch : 0;
  if (intent && intent.approved && (intent.generation !== precisionSourceLoadGeneration || intent.taskEpoch !== currentTaskEpoch)) {
    input.value = '';
    return false;
  }
  if (!(intent && intent.approved) && !preparePrecisionSourceReplacement()) {
    input.value = '';
    return false;
  }
  var generation = intent && intent.approved ? intent.generation : ++precisionSourceLoadGeneration;
  var reader = new FileReader();
  reader.onload = function() {
    if (generation !== precisionSourceLoadGeneration) return;
    loadPrecisionEditSourceImage(String(reader.result || ''), '', { generation: generation });
  };
  reader.onerror = function() {
    if (generation === precisionSourceLoadGeneration) alert(i18nText('image.load_failed'));
  };
  reader.readAsDataURL(file);
  input.value = '';
  return true;
}

function loadPrecisionEditSourceImage(dataUrl, prompt, options) {
  options = options || {};
  var baseVersionLoadToken = Number.isFinite(options.baseVersionLoadToken) ? options.baseVersionLoadToken : null;
  if (typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending && baseVersionLoadToken !== precisionVersionLoadToken) return false;
  ensurePrecisionEditPanel();
  var generation = Number.isFinite(options.generation)
    ? options.generation
    : ++precisionSourceLoadGeneration;
  if (generation !== precisionSourceLoadGeneration) return generation;
  var source = new Image();
  source.onload = function() {
    if (generation !== precisionSourceLoadGeneration) {
      if (typeof options.onError === 'function') options.onError();
      return;
    }
    var width = source.naturalWidth || source.width;
    var height = source.naturalHeight || source.height;
    if (!width || !height || width * height > INPAINT_MAX_PIXELS) {
      if (typeof options.onError === 'function') options.onError();
      else alert(i18nText('creator.inpaint_image_too_large'));
      return;
    }
    if (typeof options.beforeCommit === 'function' && options.beforeCommit() === false) {
      if (typeof options.onError === 'function') options.onError();
      return;
    }
    if (!options.preserveSession) resetPrecisionSourceSpecificState(generation);
    precisionEditSourceImageData = dataUrl;
    precisionEditSourceWidth = width;
    precisionEditSourceHeight = height;
    precisionEditObjects = [];
    precisionEditHistory = [];
    precisionEditRedo = [];
    precisionEditLabelCounter = 0;
    precisionEditSelectedId = null;
    precisionEditDraftObject = null;
    precisionEditSourceImage = source;
    var canvas = document.getElementById('precisionAnnotationCanvas');
    var shell = document.getElementById('precisionCanvasShell');
    var baseImage = document.getElementById('precisionBaseImage');
    var empty = document.getElementById('precisionUploadZone');
    var dimensions = document.getElementById('precisionCanvasDimensions');
    var surface = document.getElementById('precisionCanvasSurface');
    if (canvas) {
      canvas.width = width;
      canvas.height = height;
      canvas.classList.remove('hidden');
    }
    if (shell) {
      shell.classList.remove('is-empty');
    }
    if (surface) {
      surface.style.aspectRatio = width + ' / ' + height;
      surface.classList.remove('hidden');
    }
    if (baseImage) baseImage.classList.add('hidden');
    if (empty) empty.classList.add('hidden');
    if (dimensions) dimensions.textContent = width + ' × ' + height;
    if (typeof updatePrecisionCanvasImageInfo === 'function') updatePrecisionCanvasImageInfo();
    requestAnimationFrame(function() {
      reflowPrecisionCanvasVisualSize(true);
      fitPrecisionCanvasToWindow();
      if (typeof positionPrecisionCanvasResizeHandle === 'function') positionPrecisionCanvasResizeHandle();
    });
    if (precisionEditSizeMode === 'preserve') setPrecisionSizeMode('preserve');
    if (prompt) {
      var promptInput = document.getElementById('txtPromptPrecision');
      if (promptInput && !promptInput.value.trim()) promptInput.value = prompt;
    }
    if (!options.preserveSession) {
      precisionEditSession = {
        source: { id: 'original', label: i18nText('creator.precision_original'), data: dataUrl, width: width, height: height, prompt: String(prompt || ''), createdAt: options.createdAt || options.created_at || new Date().toISOString() },
        versions: [], selectedVersionId: 'original', baseVersionId: 'original', taskBaseVersionId: null, view: 'after', taskId: null, sourceGeneration: generation
      };
      updatePrecisionTaskMonitor(null);
    }
    renderPrecisionEditCanvas();
    updatePrecisionEditControls();
    renderPrecisionEditSession();
    updatePrecisionCutoutAvailability();
    updatePrecisionSourceActions();
    if (typeof options.onLoaded === 'function') options.onLoaded();
  };
  source.onerror = function() {
    if (generation !== precisionSourceLoadGeneration) {
      if (typeof options.onError === 'function') options.onError();
      return;
    }
    if (typeof options.onError === 'function') options.onError();
    else alert(i18nText('image.load_failed') + i18nText('image.unavailable'));
  };
  source.src = dataUrl;
  return generation;
}

function precisionVersionDimensions(entry) {
  if (!entry) return null;
  if (entry.data && entry.data === precisionEditSourceImageData && precisionEditSourceWidth > 0 && precisionEditSourceHeight > 0) {
    entry.width = precisionEditSourceWidth;
    entry.height = precisionEditSourceHeight;
    entry.dimensionsData = entry.data;
  }
  if (entry.data && entry.dimensionsData !== entry.data && entry.dimensionsLoadingData !== entry.data) {
    var data = entry.data;
    var image = new Image();
    entry.dimensionsLoadingData = data;
    image.onload = function() {
      if (entry.data !== data) return;
      entry.dimensionsData = data;
      entry.dimensionsLoadingData = '';
      if (image.naturalWidth > 0 && image.naturalHeight > 0) {
        entry.width = image.naturalWidth;
        entry.height = image.naturalHeight;
      }
      updatePrecisionCanvasImageInfo();
    };
    image.onerror = function() {
      if (entry.data !== data) return;
      entry.dimensionsData = data;
      entry.dimensionsLoadingData = '';
    };
    image.src = data;
  }
  return Number.isInteger(entry.width) && entry.width > 0 && Number.isInteger(entry.height) && entry.height > 0
    ? { width: entry.width, height: entry.height } : null;
}

function precisionVersionDisplayTime(value) {
  if (value === null || value === undefined || value === '') return '';
  var text = String(value).trim();
  var naive = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?$/.exec(text);
  if (naive) {
    var parts = [Number(naive[1]), Number(naive[2]), Number(naive[3]), Number(naive[4] || 0), Number(naive[5] || 0), Number(naive[6] || 0)];
    var check = new Date(0);
    check.setUTCFullYear(parts[0], parts[1] - 1, parts[2]);
    check.setUTCHours(parts[3], parts[4], parts[5], 0);
    if (check.getUTCFullYear() !== parts[0] || check.getUTCMonth() + 1 !== parts[1] || check.getUTCDate() !== parts[2] ||
        check.getUTCHours() !== parts[3] || check.getUTCMinutes() !== parts[4] || check.getUTCSeconds() !== parts[5]) return '';
    return naive[1] + '-' + naive[2] + '-' + naive[3] + ' ' + (naive[4] || '00') + ':' + (naive[5] || '00') + ':' + (naive[6] || '00');
  }
  var date = typeof value === 'number' && Number.isFinite(value)
    ? new Date(value > 100000000000 ? value : value * 1000)
    : /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text) ? new Date(text) : null;
  if (!date || !Number.isFinite(date.getTime())) return '';
  var pad = function(part) { return String(part).padStart(2, '0'); };
  return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) + ' ' +
    pad(date.getHours()) + ':' + pad(date.getMinutes()) + ':' + pad(date.getSeconds());
}

function precisionVersionInfoText(entry) {
  if (!entry) return '';
  var dimensions = precisionVersionDimensions(entry);
  var parts = [String(entry.label || (entry.id === 'original' ? '原图' : entry.id))];
  parts.push(dimensions ? dimensions.width + ' × ' + dimensions.height : '尺寸待确认');
  var timestamp = precisionVersionDisplayTime(entry.createdAt || entry.created_at || '');
  if (timestamp) parts.push('版本时间 ' + timestamp);
  if (entry.transparent === true) parts.push('透明背景');
  return parts.join(' · ');
}

function updatePrecisionCanvasImageInfo() {
  var info = document.getElementById('precisionCanvasImageInfo');
  if (!info || !precisionEditSession.source) {
    if (info) { info.hidden = true; info.textContent = ''; }
    return;
  }
  var entries = precisionEditSessionEntries();
  var entry = precisionEditSessionEntry(entries, precisionEditSession.selectedVersionId, precisionEditSession.source);
  var base = precisionEditSessionEntry(entries, entry.parentId || 'original', precisionEditSession.source);
  var view = precisionEditSession.view;
  info.textContent = view === 'before' ? precisionVersionInfoText(base)
    : view === 'compare' && base.id !== entry.id
      ? precisionVersionInfoText(base) + ' | ' + precisionVersionInfoText(entry)
      : precisionVersionInfoText(entry);
  info.hidden = false;
}

function updatePrecisionStrokeWidthValue() {
  var input = document.getElementById('precisionStrokeWidth');
  var output = document.getElementById('precisionStrokeWidthValue');
  if (input && output) output.value = output.textContent = input.value;
}

function precisionEditCanvasPoint(event) {
  var canvas = event && event.currentTarget && event.currentTarget.tagName === 'CANVAS'
    ? event.currentTarget : document.getElementById('precisionAnnotationCanvas');
  if (!canvas || !canvas.width || !canvas.height) return null;
  var rect = canvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;
  var clientX = Number(event && event.clientX);
  var clientY = Number(event && event.clientY);
  if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
  // Pointer coordinates are in CSS pixels while annotation geometry is normalized
  // against the intrinsic canvas pixels. Keep the conversion explicit so a
  // resized canvas cannot persist coordinates from the display scale.
  var scaleX = canvas.width / rect.width;
  var scaleY = canvas.height / rect.height;
  var canvasX = (clientX - rect.left) * scaleX;
  var canvasY = (clientY - rect.top) * scaleY;
  return {
    x: Math.max(0, Math.min(1, canvasX / canvas.width)),
    y: Math.max(0, Math.min(1, canvasY / canvas.height))
  };
}

function setPrecisionEditTool(tool) {
  if (['select', 'ellipse', 'arrow', 'rect', 'brush', 'eraser', 'text'].indexOf(tool) === -1) return;
  precisionEditTool = tool;
  var canvas = document.getElementById('precisionAnnotationCanvas');
  if (canvas) updatePrecisionEditCanvasCursor(null, canvas);
  ['select', 'ellipse', 'arrow', 'rect', 'brush', 'eraser', 'text'].forEach(function(name) {
    var button = document.getElementById('precisionTool' + name.charAt(0).toUpperCase() + name.slice(1));
    if (button) {
      button.classList.toggle('btn-secondary', name === tool);
      button.classList.toggle('btn-ghost', name !== tool);
      button.setAttribute('aria-pressed', name === tool ? 'true' : 'false');
    }
  });
}

function setPrecisionViewZoom(value, anchor) {
  precisionViewZoom = Math.max(50, Math.min(200, Math.round((Number(value) || 100) / 10) * 10));
  var shell = document.getElementById('precisionCanvasShell');
  var surface = document.getElementById('precisionCanvasSurface');
  var input = document.getElementById('precisionViewZoom');
  var output = document.getElementById('precisionViewZoomValue');
  if (surface) {
    var previousRect = surface.getBoundingClientRect ? surface.getBoundingClientRect() : { width: 0, height: 0 };
    var shellRect = shell && shell.getBoundingClientRect ? shell.getBoundingClientRect() : { left: 0, top: 0 };
    var previousWidth = previousRect.width || 0;
    var previousHeight = previousRect.height || 0;
    var shellWidth = shell && shell.clientWidth || 0;
    var shellHeight = shell && shell.clientHeight || 0;
    var resetScroll = !!(anchor && anchor.resetScroll);
    var clientX = Number(anchor && anchor.clientX);
    var clientY = Number(anchor && anchor.clientY);
    var viewportX = Number.isFinite(clientX) && shellWidth > 0 ? Math.max(0, Math.min(shellWidth, clientX - (shellRect.left || 0))) : shellWidth / 2;
    var viewportY = Number.isFinite(clientY) && shellHeight > 0 ? Math.max(0, Math.min(shellHeight, clientY - (shellRect.top || 0))) : shellHeight / 2;
    var anchorRatioX = previousWidth > 0 ? (Number(shell && shell.scrollLeft || 0) + viewportX) / previousWidth : 0.5;
    var anchorRatioY = previousHeight > 0 ? (Number(shell && shell.scrollTop || 0) + viewportY) / previousHeight : 0.5;
    surface.style.width = precisionViewZoom + '%';
    if (shell && shellWidth > 0 && shellHeight > 0) {
      var schedule = typeof requestAnimationFrame === 'function' ? requestAnimationFrame : function(callback) { callback(); };
      schedule(function() {
        var nextRect = surface.getBoundingClientRect ? surface.getBoundingClientRect() : { width: 0, height: 0 };
        var maxScrollLeft = Math.max(0, (nextRect.width || 0) - shellWidth);
        var maxScrollTop = Math.max(0, (nextRect.height || 0) - shellHeight);
        shell.scrollLeft = resetScroll ? 0 : Math.max(0, Math.min(maxScrollLeft, anchorRatioX * (nextRect.width || 0) - viewportX));
        shell.scrollTop = resetScroll ? 0 : Math.max(0, Math.min(maxScrollTop, anchorRatioY * (nextRect.height || 0) - viewportY));
        if (typeof positionPrecisionCanvasResizeHandle === 'function') positionPrecisionCanvasResizeHandle();
      });
    }
  }
  if (input && String(input.value) !== String(precisionViewZoom)) input.value = String(precisionViewZoom);
  if (output) output.value = output.textContent = precisionViewZoom + '%';
}

function fitPrecisionCanvasToWindow() {
  var shell = document.getElementById('precisionCanvasShell');
  if (!shell || !precisionEditSourceWidth || !precisionEditSourceHeight) return;
  var width = Math.max(1, shell.clientWidth || shell.getBoundingClientRect().width);
  var limits = precisionCanvasResizeLimits(shell);
  var viewportHeight = typeof window !== 'undefined' ? window.innerHeight : limits.maxHeight;
  var availableHeight = Math.max(1, Math.min(limits.maxHeight, viewportHeight || limits.maxHeight));
  var heightFit = (availableHeight * precisionEditSourceWidth / (width * precisionEditSourceHeight)) * 100;
  setPrecisionViewZoom(Math.min(100, Math.max(50, heightFit)), { resetScroll: true });
}

function precisionCanvasPanRequested(event) {
  if (!event || event.isPrimary === false) return false;
  return event.button === 1 || (event.button === 0 && precisionCanvasSpaceHeld);
}

function beginPrecisionCanvasPan(event) {
  var shell = document.getElementById('precisionCanvasShell');
  var canvas = event && event.currentTarget;
  if (!shell || !canvas || !precisionEditSourceImageData || precisionCanvasPanState) return false;
  precisionCanvasPanState = { pointerId: event.pointerId, target: canvas, button: event.button, startX: event.clientX, startY: event.clientY, scrollLeft: shell.scrollLeft, scrollTop: shell.scrollTop, moved: false };
  canvas.classList.add('is-panning');
  try { canvas.setPointerCapture(event.pointerId); } catch (error) {}
  event.preventDefault();
  return true;
}

function continuePrecisionCanvasPan(event) {
  var state = precisionCanvasPanState;
  var shell = document.getElementById('precisionCanvasShell');
  if (!state || !shell || !event || event.pointerId !== state.pointerId) return false;
  var deltaX = event.clientX - state.startX;
  var deltaY = event.clientY - state.startY;
  if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) state.moved = true;
  shell.scrollLeft = state.scrollLeft - deltaX;
  shell.scrollTop = state.scrollTop - deltaY;
  event.preventDefault();
  return true;
}

function endPrecisionCanvasPan(event) {
  var state = precisionCanvasPanState;
  if (!state || !event || event.pointerId !== state.pointerId) return false;
  var target = state.target;
  precisionCanvasPanState = null;
  if (target) {
    target.classList.remove('is-panning');
    if (target.hasPointerCapture && target.hasPointerCapture(event.pointerId) && target.releasePointerCapture) {
      try { target.releasePointerCapture(event.pointerId); } catch (error) {}
    }
  }
  if (state.button === 1 && !state.moved) setPrecisionViewZoom(100, { resetScroll: true });
  return true;
}

function cancelPrecisionCanvasInteraction() {
  var checkpoint = precisionEditGestureCheckpoint;
  var pointerTarget = precisionEditPointerTarget;
  var pointerId = precisionEditPointerId;
  var panState = precisionCanvasPanState;
  var hadInteraction = !!(checkpoint || precisionEditDraftObject || precisionEditDragOrigin || panState || precisionEditTextDraftPoint || precisionEditSelectedId);
  cancelPrecisionEditText();
  if (checkpoint) {
    precisionEditObjects = precisionEditClone(checkpoint.objects);
    precisionEditHistory = precisionEditClone(checkpoint.history);
    precisionEditRedo = precisionEditClone(checkpoint.redo);
    precisionEditSelectedId = checkpoint.selectedId;
  }
  precisionEditPointerFinishing = true;
  precisionEditDraftObject = null;
  precisionEditDragOrigin = null;
  precisionEditPointerId = null;
  precisionEditPointerTarget = null;
  precisionEditDragMoved = false;
  precisionEditGestureCheckpoint = null;
  precisionEditEraserSnapshot = null;
  precisionEditEraserChanged = false;
  precisionCanvasPanState = null;
  var canvas = document.getElementById('precisionAnnotationCanvas');
  if (canvas) canvas.classList.remove('is-panning', 'is-pan-ready');
  if (pointerTarget && pointerTarget.releasePointerCapture && pointerId !== null) {
    try { pointerTarget.releasePointerCapture(pointerId); } catch (error) {}
  }
  if (panState && panState.target && panState.target.releasePointerCapture) {
    try { panState.target.releasePointerCapture(panState.pointerId); } catch (error) {}
  }
  precisionEditPointerFinishing = false;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
  return hadInteraction;
}

function deletePrecisionEditSelection() {
  if (!precisionEditSelectedId || !precisionEditObjectById(precisionEditSelectedId)) return false;
  capturePrecisionEditHistory();
  precisionEditObjects = precisionEditObjects.filter(function(object) { return object.id !== precisionEditSelectedId; });
  precisionEditSelectedId = null;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
  return true;
}

function handlePrecisionEditCanvasKeydown(event) {
  var canvas = event && event.currentTarget;
  if (!event || !canvas) return;
  var modifier = event.ctrlKey || event.metaKey;
  var key = String(event.key || '');
  var lowerKey = key.toLowerCase();
  if (key === ' ' && precisionEditSourceImageData) {
    precisionCanvasSpaceHeld = true;
    canvas.classList.add('is-pan-ready');
    updatePrecisionEditCanvasCursor(null, canvas);
    event.preventDefault();
    return;
  }
  if (key === 'Escape') {
    if (cancelPrecisionCanvasInteraction()) event.preventDefault();
    return;
  }
  if (key === 'Delete' || key === 'Backspace') {
    if (deletePrecisionEditSelection()) event.preventDefault();
    return;
  }
  if (modifier && key === '0') {
    event.preventDefault();
    fitPrecisionCanvasToWindow();
    return;
  }
  if (modifier && (lowerKey === 'z' || lowerKey === 'y')) {
    event.preventDefault();
    if (lowerKey === 'y' || event.shiftKey) redoPrecisionEdit(); else undoPrecisionEdit();
    return;
  }
  if ((key === '+' || key === '=' || key === '-' || key === '_') && precisionEditSourceImageData) {
    event.preventDefault();
    setPrecisionViewZoom(precisionViewZoom + (key === '-' || key === '_' ? -10 : 10));
  }
}

function handlePrecisionToolShortcut(event) {
  if (!event || event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
  var panel = document.getElementById('panelPrecisionEdit');
  if (!panel || panel.hidden || panel.classList.contains('hidden')) return;
  var target = event.target;
  if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT|OPTION|BUTTON)$/.test(String(target.tagName || '').toUpperCase()))) return;
  var key = String(event.key || '').toLowerCase();
  if (key === 'f') {
    togglePrecisionCompareFullscreen();
    event.preventDefault();
    return;
  }
  var tool = ({ v: 'select', o: 'ellipse', a: 'arrow', r: 'rect', b: 'brush', e: 'eraser', t: 'text' })[key];
  if (!tool) return;
  setPrecisionEditTool(tool);
  event.preventDefault();
}

function handlePrecisionEditCanvasKeyup(event) {
  if (!event || event.key !== ' ') return;
  precisionCanvasSpaceHeld = false;
  var canvas = event.currentTarget;
  if (canvas) {
    canvas.classList.remove('is-pan-ready', 'is-panning');
    updatePrecisionEditCanvasCursor(null, canvas);
  }
  event.preventDefault();
}

function resetPrecisionCanvasKeyboardState(event) {
  precisionCanvasSpaceHeld = false;
  var canvas = event && event.currentTarget || document.getElementById('precisionAnnotationCanvas');
  if (canvas) {
    canvas.classList.remove('is-pan-ready', 'is-panning');
    updatePrecisionEditCanvasCursor(null, canvas);
  }
}

function startPrecisionAiErase(kind) {
  precisionEditPendingInstruction = i18nText(kind === 'watermark' ? 'creator.precision_remove_watermark_instruction' : 'creator.precision_remove_people_instruction');
  setPrecisionEditTool('brush');
  setStatus(i18nText('creator.precision_ai_remove_ready'));
}

function capturePrecisionEditHistory() {
  precisionEditHistory.push(precisionEditClone(precisionEditObjects));
  if (precisionEditHistory.length > PRECISION_HISTORY_LIMIT) precisionEditHistory.shift();
  precisionEditRedo = [];
}

function precisionEditObjectInstruction(object) {
  if (!object) return '';
  var value = object.instruction;
  // Older drafts used explanation/note for the same per-object field. Read them
  // for compatibility, but keep instruction as the v2 wire-field.
  if (value === undefined || value === null) value = object.explanation || object.note;
  return String(value || '').trim().slice(0, 500);
}

function precisionEditContextPrompt(context) {
  if (!context) return '';
  var candidates = [context.prompt, context.overall_instruction, context.overall_prompt];
  for (var index = 0; index < candidates.length; index++) {
    if (typeof candidates[index] === 'string' && candidates[index].trim()) return candidates[index].trim().slice(0, 2000);
  }
  return '';
}

function precisionEditContextAnnotations(context) {
  if (!context) return [];
  var candidates = [
    context.annotation_objects,
    context.annotations,
    context.annotation_data && context.annotation_data.objects,
    context.annotation_data && context.annotation_data.annotations
  ];
  var fallback = [];
  for (var index = 0; index < candidates.length; index++) {
    if (!Array.isArray(candidates[index])) continue;
    if (!fallback.length) fallback = candidates[index];
    if (candidates[index].length) return candidates[index];
  }
  return fallback;
}

function normalizePrecisionEditObject(object) {
  var x1 = Math.max(0, Math.min(1, Number(object.x) || 0));
  var y1 = Math.max(0, Math.min(1, Number(object.y) || 0));
  var x2 = Math.max(0, Math.min(1, Number(object.x2) || 0));
  var y2 = Math.max(0, Math.min(1, Number(object.y2) || 0));
  var normalized;
  if (object.type === 'arrow') normalized = { type: 'arrow', x1: x1, y1: y1, x2: x2, y2: y2 };
  else if (object.type === 'rect' || object.type === 'ellipse') normalized = { type: object.type === 'rect' ? 'rectangle' : 'ellipse', x: Math.min(x1, x2), y: Math.min(y1, y2), width: Math.abs(x2 - x1), height: Math.abs(y2 - y1) };
  else if (object.type === 'brush') normalized = { type: 'brush', points: (object.points || []).slice(0, 1024).map(function(point) { return { x: Math.max(0, Math.min(1, Number(point.x) || 0)), y: Math.max(0, Math.min(1, Number(point.y) || 0)) }; }) };
  else normalized = { type: 'text', x: x1, y: y1, text: String(object.text || '').slice(0, 500) };
  normalized.label = Number(object.label) || 0;
  if (/^#[0-9a-f]{6}$/i.test(object.color || '')) normalized.color = object.color;
  if (Number.isFinite(Number(object.strokeWidth))) normalized.stroke_width = Math.max(2, Math.min(16, Number(object.strokeWidth)));
  if (object.type === 'text' && Number.isFinite(Number(object.fontSize))) normalized.font_size = Math.max(12, Math.min(96, Number(object.fontSize)));
  var precisionInstruction = precisionEditObjectInstruction(object);
  if (object.type !== 'text' || precisionInstruction) normalized.instruction = precisionInstruction;
  return normalized;
}

function serializePrecisionAnnotationForRequest(object) {
  if (!object || typeof object !== 'object') return null;
  var type = object.type === 'rect' ? 'rectangle' : object.type;
  var label = Number(object.label) || 0;
  var instruction = precisionEditObjectInstruction(object);
  var clamp = function(value) { return Math.max(0, Math.min(1, Number(value) || 0)); };
  if (type === 'arrow') {
    return {
      type: 'arrow',
      label: label,
      instruction: instruction,
      x1: clamp(object.x1 !== undefined ? object.x1 : object.x),
      y1: clamp(object.y1 !== undefined ? object.y1 : object.y),
      x2: clamp(object.x2),
      y2: clamp(object.y2)
    };
  }
  if (type === 'rectangle' || type === 'ellipse') {
    if (object.width !== undefined && object.height !== undefined) {
      var boxX = clamp(object.x);
      var boxY = clamp(object.y);
      return {
        type: type,
        label: label,
        instruction: instruction,
        x: boxX,
        y: boxY,
        width: Math.max(0, Math.min(1 - boxX, Number(object.width) || 0)),
        height: Math.max(0, Math.min(1 - boxY, Number(object.height) || 0))
      };
    }
    var x1 = clamp(object.x);
    var y1 = clamp(object.y);
    var x2 = clamp(object.x2);
    var y2 = clamp(object.y2);
    return {
      type: type,
      label: label,
      instruction: instruction,
      x: Math.min(x1, x2),
      y: Math.min(y1, y2),
      width: Math.abs(x2 - x1),
      height: Math.abs(y2 - y1)
    };
  }
  if (type === 'brush') {
    return {
      type: 'brush',
      label: label,
      instruction: instruction,
      points: (object.points || []).slice(0, 1024).map(function(point) {
        return { x: clamp(point && point.x), y: clamp(point && point.y) };
      })
    };
  }
  if (type === 'text') {
    var annotation = {
      type: 'text',
      label: label,
      text: String(object.text || '').slice(0, 500),
      x: clamp(object.x),
      y: clamp(object.y)
    };
    if (instruction) annotation.instruction = instruction;
    return annotation;
  }
  return null;
}

function serializePrecisionAnnotationsForRequest(objects) {
  if (!Array.isArray(objects)) return [];
  return objects.map(serializePrecisionAnnotationForRequest).filter(Boolean);
}

function precisionEditStyle() {
  var colorInput = document.getElementById('precisionAnnotationColor');
  var widthInput = document.getElementById('precisionStrokeWidth');
  var fontInput = document.getElementById('precisionTextSize');
  var color = colorInput && /^#[0-9a-f]{6}$/i.test(colorInput.value) ? colorInput.value : '#ef4444';
  var strokeWidth = Math.max(2, Math.min(16, Number(widthInput && widthInput.value) || 5));
  var fontSize = Math.max(12, Math.min(96, Number(fontInput && fontInput.value) || 24));
  return { color: color, strokeWidth: strokeWidth, fontSize: fontSize };
}

function precisionEditObjectBounds(object) {
  if (object.type === 'brush' && object.points && object.points.length) {
    var xs = object.points.map(function(point) { return point.x; });
    var ys = object.points.map(function(point) { return point.y; });
    return { left: Math.min.apply(Math, xs), right: Math.max.apply(Math, xs), top: Math.min.apply(Math, ys), bottom: Math.max.apply(Math, ys) };
  }
  var x1 = object.x || 0, y1 = object.y || 0;
  var x2 = object.type === 'text' ? Math.min(1, x1 + 0.18) : (object.x2 === undefined ? x1 : object.x2);
  var y2 = object.type === 'text' ? Math.min(1, y1 + 0.06) : (object.y2 === undefined ? y1 : object.y2);
  return { left: Math.min(x1, x2), right: Math.max(x1, x2), top: Math.min(y1, y2), bottom: Math.max(y1, y2) };
}

function precisionEditIsTransformable(object) {
  return !!object && ['rect', 'ellipse', 'arrow', 'brush', 'text'].indexOf(object.type) !== -1;
}

function precisionEditApplyBounds(object, originBounds, nextBounds) {
  var oldWidth = Math.max(PRECISION_ANNOTATION_MIN_SIZE, originBounds.right - originBounds.left);
  var oldHeight = Math.max(PRECISION_ANNOTATION_MIN_SIZE, originBounds.bottom - originBounds.top);
  var newWidth = Math.max(PRECISION_ANNOTATION_MIN_SIZE, nextBounds.right - nextBounds.left);
  var newHeight = Math.max(PRECISION_ANNOTATION_MIN_SIZE, nextBounds.bottom - nextBounds.top);
  if (object.type === 'brush' && Array.isArray(object.points)) {
    object.points = object.points.map(function(point) {
      return {
        x: Math.max(0, Math.min(1, nextBounds.left + ((point.x - originBounds.left) / oldWidth) * newWidth)),
        y: Math.max(0, Math.min(1, nextBounds.top + ((point.y - originBounds.top) / oldHeight) * newHeight))
      };
    });
    return object;
  }
  if (object.type === 'arrow') {
    object.x = Math.max(0, Math.min(1, nextBounds.left + ((object.x - originBounds.left) / oldWidth) * newWidth));
    object.y = Math.max(0, Math.min(1, nextBounds.top + ((object.y - originBounds.top) / oldHeight) * newHeight));
    object.x2 = Math.max(0, Math.min(1, nextBounds.left + ((object.x2 - originBounds.left) / oldWidth) * newWidth));
    object.y2 = Math.max(0, Math.min(1, nextBounds.top + ((object.y2 - originBounds.top) / oldHeight) * newHeight));
    return object;
  }
  object.x = nextBounds.left;
  object.y = nextBounds.top;
  object.x2 = nextBounds.right;
  object.y2 = nextBounds.bottom;
  if (object.type === 'text') {
    object.fontSize = Math.max(10, Math.round((Number(object.fontSize) || 24) * Math.min(newWidth / oldWidth, newHeight / oldHeight)));
  }
  return object;
}

function precisionEditIsBoxShape(object) {
  return !!object && (object.type === 'rect' || object.type === 'ellipse');
}

function precisionEditPointerTolerance(event, pixels) {
  var canvas = event && event.currentTarget && event.currentTarget.tagName === 'CANVAS'
    ? event.currentTarget : document.getElementById('precisionAnnotationCanvas');
  var rect = canvas && canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : null;
  var fallbackWidth = canvas && canvas.width || 1;
  var fallbackHeight = canvas && canvas.height || 1;
  return {
    x: Math.max(0, Number(pixels) || 0) / Math.max(1, rect && rect.width || fallbackWidth),
    y: Math.max(0, Number(pixels) || 0) / Math.max(1, rect && rect.height || fallbackHeight)
  };
}

function precisionEditShapeHit(point, object, tolerance) {
  if (!point || !precisionEditIsBoxShape(object)) return false;
  var bounds = precisionEditObjectBounds(object);
  var padX = tolerance && tolerance.x || 0;
  var padY = tolerance && tolerance.y || 0;
  if (object.type === 'rect') {
    return point.x >= bounds.left - padX && point.x <= bounds.right + padX &&
      point.y >= bounds.top - padY && point.y <= bounds.bottom + padY;
  }
  var radiusX = (bounds.right - bounds.left) / 2 + padX;
  var radiusY = (bounds.bottom - bounds.top) / 2 + padY;
  if (radiusX <= 0 || radiusY <= 0) return false;
  var centerX = (bounds.left + bounds.right) / 2;
  var centerY = (bounds.top + bounds.bottom) / 2;
  var normalizedX = (point.x - centerX) / radiusX;
  var normalizedY = (point.y - centerY) / radiusY;
  return normalizedX * normalizedX + normalizedY * normalizedY <= 1;
}

function findPrecisionEditShape(point, event) {
  var tolerance = precisionEditPointerTolerance(event, 8);
  for (var index = precisionEditObjects.length - 1; index >= 0; index--) {
    var object = precisionEditObjects[index];
    if (precisionEditShapeHit(point, object, tolerance)) return object;
  }
  return null;
}

function findPrecisionEditObject(point, event) {
  var tolerance = precisionEditPointerTolerance(event, 8);
  for (var index = precisionEditObjects.length - 1; index >= 0; index--) {
    var object = precisionEditObjects[index];
    if (precisionEditIsBoxShape(object)) {
      if (precisionEditShapeHit(point, object, tolerance)) return object;
      continue;
    }
    var bounds = precisionEditObjectBounds(object);
    var pad = 0.025;
    if (point && point.x >= bounds.left - pad && point.x <= bounds.right + pad && point.y >= bounds.top - pad && point.y <= bounds.bottom + pad) return object;
  }
  return null;
}

function precisionEditHandlePoints(object) {
  if (object && object.type === 'arrow') {
    return {
      start: { x: Math.max(0, Math.min(1, Number(object.x) || 0)), y: Math.max(0, Math.min(1, Number(object.y) || 0)) },
      end: { x: Math.max(0, Math.min(1, Number(object.x2) || 0)), y: Math.max(0, Math.min(1, Number(object.y2) || 0)) }
    };
  }
  if (object && object.type === 'brush' && Array.isArray(object.points)) {
    return object.points.reduce(function(handles, point, index) {
      handles['point-' + index] = {
        x: Math.max(0, Math.min(1, Number(point && point.x) || 0)),
        y: Math.max(0, Math.min(1, Number(point && point.y) || 0))
      };
      return handles;
    }, {});
  }
  var bounds = precisionEditObjectBounds(object);
  return {
    nw: { x: bounds.left, y: bounds.top },
    ne: { x: bounds.right, y: bounds.top },
    sw: { x: bounds.left, y: bounds.bottom },
    se: { x: bounds.right, y: bounds.bottom }
  };
}

function findPrecisionEditHandle(point, object, event) {
  if (!precisionEditIsTransformable(object)) return null;
  var pointerPixels = event && event.pointerType === 'touch' ? PRECISION_HANDLE_TOUCH_PX : PRECISION_HANDLE_MOUSE_PX;
  var tolerance = precisionEditPointerTolerance(event, pointerPixels);
  var handles = precisionEditHandlePoints(object);
  var names = Object.keys(handles);
  for (var index = 0; index < names.length; index++) {
    var name = names[index];
    var handle = handles[name];
    if (Math.abs(point.x - handle.x) <= tolerance.x && Math.abs(point.y - handle.y) <= tolerance.y) return name;
  }
  return null;
}

function precisionEditResizeCursor(handle) {
  if (handle === 'start' || handle === 'end') return 'crosshair';
  if (String(handle || '').indexOf('point-') === 0) return 'move';
  return handle === 'nw' || handle === 'se' ? 'nwse-resize' : 'nesw-resize';
}

function precisionEditBrushSegmentIndex(point, object, event) {
  if (!point || !object || object.type !== 'brush' || !Array.isArray(object.points) || object.points.length < 2) return -1;
  var tolerance = precisionEditPointerTolerance(event, event && event.pointerType === 'touch' ? PRECISION_HANDLE_TOUCH_PX : PRECISION_HANDLE_MOUSE_PX);
  var limit = Math.max(tolerance.x, tolerance.y);
  for (var index = 0; index < object.points.length - 1; index++) {
    var start = object.points[index];
    var end = object.points[index + 1];
    var dx = end.x - start.x;
    var dy = end.y - start.y;
    var lengthSquared = dx * dx + dy * dy;
    var position = lengthSquared ? Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared)) : 0;
    var nearestX = start.x + dx * position;
    var nearestY = start.y + dy * position;
    if (Math.hypot(point.x - nearestX, point.y - nearestY) <= limit) return index;
  }
  return -1;
}

function beginPrecisionEditBrushNode(point, object, segmentIndex) {
  var original = precisionEditClone(precisionEditObjects);
  var nextObject = precisionEditClone([object])[0];
  var nodeIndex = Math.max(0, Math.min(nextObject.points.length - 1, segmentIndex + 1));
  nextObject.points.splice(nodeIndex, 0, { x: Math.max(0, Math.min(1, point.x)), y: Math.max(0, Math.min(1, point.y)) });
  precisionEditObjects = original.map(function(item) { return item.id === object.id ? nextObject : item; });
  precisionEditSelectedId = object.id;
  precisionEditDragOrigin = {
    point: { x: point.x, y: point.y },
    objects: original,
    mode: 'node',
    handle: 'point-' + nodeIndex,
    objectId: object.id,
    insertedNode: true
  };
  precisionEditDragMoved = true;
  precisionEditDraftObject = null;
}

function updatePrecisionEditCanvasCursor(event, canvas) {
  canvas = canvas || document.getElementById('precisionAnnotationCanvas');
  if (!canvas) return;
  if (precisionCanvasPanState) { canvas.style.cursor = 'grabbing'; return; }
  if (precisionCanvasSpaceHeld) { canvas.style.cursor = 'grab'; return; }
  if (precisionEditDragOrigin) {
    canvas.style.cursor = precisionEditDragOrigin.mode === 'resize'
      ? precisionEditResizeCursor(precisionEditDragOrigin.handle) : 'grabbing';
    return;
  }
  if (precisionEditTool === 'eraser') { canvas.style.cursor = 'cell'; return; }
  if ((precisionEditTool === 'select' || precisionEditTool === 'rect' || precisionEditTool === 'ellipse' || precisionEditTool === 'arrow') && event) {
    var point = precisionEditCanvasPoint(event);
    var selected = precisionEditObjectById(precisionEditSelectedId);
    var handle = point && findPrecisionEditHandle(point, selected, event);
    if (handle) { canvas.style.cursor = precisionEditResizeCursor(handle); return; }
    if (point && findPrecisionEditObject(point, event)) { canvas.style.cursor = 'grab'; return; }
  }
  canvas.style.cursor = precisionEditTool === 'select' ? 'default' : 'crosshair';
}

function beginPrecisionEditTransform(point, object, mode, handle) {
  precisionEditSelectedId = object.id;
  precisionEditDragOrigin = {
    point: { x: point.x, y: point.y },
    objects: precisionEditClone(precisionEditObjects),
    mode: mode,
    handle: handle || null,
    objectId: object.id
  };
  precisionEditDraftObject = null;
}

function precisionEditCreateGestureCheckpoint() {
  return {
    objects: precisionEditClone(precisionEditObjects),
    history: precisionEditClone(precisionEditHistory),
    redo: precisionEditClone(precisionEditRedo),
    selectedId: precisionEditSelectedId,
    sourceGeneration: precisionSourceLoadGeneration,
    sourceData: precisionEditSourceImageData
  };
}

function precisionEditDoubleClickMatches(checkpoint, event) {
  if (!checkpoint || !event || checkpoint.target !== 'canvas') return false;
  if (Date.now() - checkpoint.createdAt > PRECISION_DOUBLE_CLICK_ROLLBACK_WINDOW_MS) return false;
  var clientX = Number(event.clientX);
  var clientY = Number(event.clientY);
  if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return false;
  return Math.hypot(clientX - checkpoint.clientX, clientY - checkpoint.clientY) <= PRECISION_DOUBLE_CLICK_ROLLBACK_DISTANCE_PX;
}

function rememberPrecisionEditDoubleClickCheckpoint(event, checkpoint) {
  if (!checkpoint || !event) return;
  if (precisionEditDoubleClickMatches(precisionEditDoubleClickCheckpoint, event)) return;
  var clientX = Number(event.clientX);
  var clientY = Number(event.clientY);
  if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return;
  var candidate = {
    target: 'canvas',
    clientX: clientX,
    clientY: clientY,
    createdAt: Date.now(),
    checkpoint: checkpoint,
    focusId: precisionEditSelectedId,
    deferredStatus: checkpoint.deferredStatus || ''
  };
  precisionEditDoubleClickCheckpoint = candidate;
  if (typeof window !== 'undefined' && typeof window.setTimeout === 'function') {
    window.setTimeout(function() {
      if (precisionEditDoubleClickCheckpoint !== candidate) return;
      precisionEditDoubleClickCheckpoint = null;
      if (candidate.deferredStatus) setStatus(candidate.deferredStatus);
      if (candidate.focusId && precisionEditSelectedId === candidate.focusId) focusPrecisionEditInstruction(candidate.focusId);
    }, PRECISION_DOUBLE_CLICK_ROLLBACK_WINDOW_MS);
  }
}

function rollbackPrecisionEditDoubleClickCheckpoint(checkpoint) {
  if (!checkpoint || checkpoint.sourceGeneration !== precisionSourceLoadGeneration || checkpoint.sourceData !== precisionEditSourceImageData) return false;
  precisionEditObjects = precisionEditClone(checkpoint.objects || []);
  precisionEditHistory = precisionEditClone(checkpoint.history || []);
  precisionEditRedo = precisionEditClone(checkpoint.redo || []);
  precisionEditSelectedId = checkpoint.selectedId || null;
  precisionEditPointerId = null;
  precisionEditPointerTarget = null;
  precisionEditDraftObject = null;
  precisionEditDragOrigin = null;
  precisionEditDragMoved = false;
  precisionEditGestureCheckpoint = null;
  precisionEditEraserSnapshot = null;
  precisionEditEraserChanged = false;
  cancelPrecisionEditText();
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
  return true;
}

function handlePrecisionCanvasDoubleClick(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  var checkpoint = precisionEditDoubleClickCheckpoint;
  if (precisionEditDoubleClickMatches(checkpoint, event)) rollbackPrecisionEditDoubleClickCheckpoint(checkpoint.checkpoint);
  precisionEditDoubleClickCheckpoint = null;
  return openPrecisionCanvasImageFullscreen(event);
}

function handlePrecisionTextEditorPointerup(event) {
  var checkpoint = precisionEditDoubleClickCheckpoint;
  if (precisionEditDoubleClickMatches(checkpoint, event)) {
    precisionEditDoubleClickCheckpoint = null;
    rollbackPrecisionEditDoubleClickCheckpoint(checkpoint.checkpoint);
    return openPrecisionCanvasImageFullscreen(event);
  }
  rememberPrecisionEditDoubleClickCheckpoint(event, precisionEditGestureCheckpoint);
  return false;
}

function handlePrecisionTextEditorPointerdown(event) {
  var checkpoint = precisionEditDoubleClickCheckpoint;
  if (!precisionEditDoubleClickMatches(checkpoint, event)) return false;
  event.preventDefault();
  event.stopPropagation();
  precisionEditDoubleClickCheckpoint = null;
  rollbackPrecisionEditDoubleClickCheckpoint(checkpoint.checkpoint);
  return openPrecisionCanvasImageFullscreen(event);
}

function handlePrecisionCanvasSurfacePointerdown(event) {
  var checkpoint = precisionEditDoubleClickCheckpoint;
  if (!precisionEditDoubleClickMatches(checkpoint, event)) return false;
  event.preventDefault();
  event.stopImmediatePropagation();
  precisionEditDoubleClickCheckpoint = null;
  rollbackPrecisionEditDoubleClickCheckpoint(checkpoint.checkpoint);
  return openPrecisionCanvasImageFullscreen({ currentTarget: { id: 'precisionAnnotationCanvas' }, clientX: event.clientX, clientY: event.clientY });
}

function beginPrecisionEditPointer(event) {
  if (!precisionEditSourceImageData || precisionEditPointerId !== null) return;
  if (precisionCanvasPanRequested(event)) {
    beginPrecisionCanvasPan(event);
    return;
  }
  if (event.isPrimary === false || (event.pointerType === 'mouse' && event.button !== 0)) return;
  var point = precisionEditCanvasPoint(event);
  if (!point) return;
  event.preventDefault();
  var canvas = event.currentTarget;
  var doubleClickCheckpoint = precisionEditDoubleClickCheckpoint;
  if (precisionEditDoubleClickMatches(doubleClickCheckpoint, event)) {
    precisionEditDoubleClickCheckpoint = null;
    rollbackPrecisionEditDoubleClickCheckpoint(doubleClickCheckpoint.checkpoint);
    openPrecisionCanvasImageFullscreen(event);
    return;
  }

  if (precisionEditTool === 'text' && !event.altKey) {
    var textHit = findPrecisionEditObject(point, event);
    if (textHit && textHit.type === 'text') {
      precisionEditSelectedId = textHit.id;
      beginPrecisionEditTransform(point, textHit, 'move');
      precisionEditPointerId = event.pointerId;
      precisionEditPointerTarget = canvas;
      precisionEditPointerFinishing = false;
      precisionEditDragMoved = false;
      try { canvas.setPointerCapture(event.pointerId); } catch (error) {}
      renderPrecisionEditCanvas();
      updatePrecisionEditControls();
      return;
    }
    precisionEditGestureCheckpoint = precisionEditCreateGestureCheckpoint();
    openPrecisionEditTextEditor(point);
    return;
  }

  if (!event.altKey) {
    var selected = precisionEditObjectById(precisionEditSelectedId);
    var handle = findPrecisionEditHandle(point, selected, event);
    var shape = handle ? selected : findPrecisionEditObject(point, event);
    if (shape) {
      if (precisionEditTool !== 'eraser' && (precisionEditTool === 'select' || shape.type === precisionEditTool || ((precisionEditTool === 'rect' || precisionEditTool === 'ellipse') && precisionEditIsBoxShape(shape)))) {
        var segmentIndex = event.shiftKey && !handle && shape.type === 'brush' && precisionEditTool === 'brush' && shape.id === precisionEditSelectedId
          ? precisionEditBrushSegmentIndex(point, shape, event) : -1;
        if (segmentIndex >= 0) beginPrecisionEditBrushNode(point, shape, segmentIndex);
        else beginPrecisionEditTransform(point, shape, handle && shape.type === 'brush' ? 'node' : handle ? 'resize' : 'move', handle);
      } else {
        shape = null;
      }
    }
    if (shape) {
      precisionEditGestureCheckpoint = precisionEditCreateGestureCheckpoint();
      precisionEditPointerId = event.pointerId;
      precisionEditPointerTarget = canvas;
      precisionEditPointerFinishing = false;
      precisionEditDragMoved = false;
      try { canvas.setPointerCapture(event.pointerId); } catch (error) {}
      renderPrecisionEditCanvas();
      updatePrecisionEditControls();
      updatePrecisionEditCanvasCursor(event, canvas);
      return;
    }
  }

  if (precisionEditTool === 'select') {
    precisionEditSelectedId = null;
    renderPrecisionEditCanvas();
    updatePrecisionEditControls();
    updatePrecisionEditCanvasCursor(event, canvas);
    return;
  }

  precisionEditGestureCheckpoint = precisionEditCreateGestureCheckpoint();
  precisionEditPointerId = event.pointerId;
  precisionEditPointerTarget = canvas;
  precisionEditPointerFinishing = false;
  precisionEditDragMoved = false;
  try { canvas.setPointerCapture(event.pointerId); } catch (error) {}
  if (precisionEditTool === 'eraser') {
    precisionEditEraserSnapshot = precisionEditClone(precisionEditObjects);
    precisionEditEraserChanged = false;
    var selectedObject = precisionEditObjectById(precisionEditSelectedId);
    var selectedBrushHandle = selectedObject && selectedObject.type === 'brush' ? findPrecisionEditHandle(point, selectedObject, event) : null;
    if (selectedBrushHandle && selectedObject.points.length > 2) {
      var selectedBrushIndex = Number(String(selectedBrushHandle).slice('point-'.length));
      if (Number.isInteger(selectedBrushIndex) && selectedBrushIndex >= 0 && selectedBrushIndex < selectedObject.points.length) {
        capturePrecisionEditHistory();
        selectedObject.points.splice(selectedBrushIndex, 1);
        precisionEditEraserChanged = true;
        renderPrecisionEditCanvas();
        updatePrecisionEditControls();
        return;
      }
    }
    if (selectedObject && findPrecisionEditObject(point, event) === selectedObject) {
      capturePrecisionEditHistory();
      precisionEditObjects = precisionEditObjects.filter(function(item) { return item.id !== selectedObject.id; });
      precisionEditSelectedId = null;
      precisionEditEraserChanged = true;
      precisionEditGestureCheckpoint.deferredStatus = i18nText('creator.precision_edit_eraser_deleted');
      renderPrecisionEditCanvas();
      updatePrecisionEditControls();
    } else {
      erasePrecisionBrushAt(point);
    }
    return;
  }

  var style = precisionEditStyle();
  precisionEditDraftObject = {
    id: precisionEditNewId(), type: precisionEditTool,
    x: point.x, y: point.y, x2: point.x, y2: point.y,
    color: style.color, strokeWidth: style.strokeWidth, label: precisionEditNewLabel(), instruction: precisionEditPendingInstruction
  };
  if (precisionEditTool === 'brush') precisionEditDraftObject.points = [point];
  renderPrecisionEditCanvas();
}

function applyPrecisionEditPointerPoint(point) {
  if (!point) return false;
  if (precisionEditTool === 'eraser') return erasePrecisionBrushAt(point);
  if (precisionEditDraftObject) {
    if (precisionEditDraftObject.type === 'brush') {
      var points = precisionEditDraftObject.points || (precisionEditDraftObject.points = []);
      var last = points[points.length - 1];
      var distance = last ? Math.hypot(point.x - last.x, point.y - last.y) : 1;
      if (distance >= 0.002 && points.length < 1024) points.push(point);
      return distance >= 0.002;
    }
    precisionEditDraftObject.x2 = point.x;
    precisionEditDraftObject.y2 = point.y;
    return true;
  }
  if (!precisionEditDragOrigin || !precisionEditSelectedId) return false;
  var dx = point.x - precisionEditDragOrigin.point.x;
  var dy = point.y - precisionEditDragOrigin.point.y;
  var originObject = precisionEditDragOrigin.objects.find(function(object) { return object.id === precisionEditSelectedId; });
  if (!precisionEditIsTransformable(originObject)) return false;
  var bounds = precisionEditObjectBounds(originObject);
  var nextBounds;
  if (precisionEditDragOrigin.mode === 'node' && originObject.type === 'brush') {
    var nodeIndex = Number(String(precisionEditDragOrigin.handle || '').slice('point-'.length));
    var nextBrush = precisionEditClone([originObject])[0];
    if (precisionEditDragOrigin.insertedNode) {
      if (nodeIndex < 0 || nodeIndex > nextBrush.points.length) return false;
      nextBrush.points.splice(nodeIndex, 0, { x: point.x, y: point.y });
    }
    if (!Number.isInteger(nodeIndex) || nodeIndex < 0 || nodeIndex >= nextBrush.points.length) return false;
    nextBrush.points[nodeIndex] = { x: Math.max(0, Math.min(1, point.x)), y: Math.max(0, Math.min(1, point.y)) };
    var originalNode = originObject.points[nodeIndex];
    var changedNode = precisionEditDragOrigin.insertedNode
      ? true
      : !!originalNode && (Math.abs(nextBrush.points[nodeIndex].x - originalNode.x) > 0.0001 || Math.abs(nextBrush.points[nodeIndex].y - originalNode.y) > 0.0001);
    precisionEditDragMoved = changedNode;
    if (!changedNode) return false;
    precisionEditObjects = precisionEditClone(precisionEditDragOrigin.objects).map(function(object) {
      return object.id === precisionEditSelectedId ? nextBrush : object;
    });
    return true;
  }
  if (precisionEditDragOrigin.mode === 'resize') {
    var handle = precisionEditDragOrigin.handle;
    if (originObject.type === 'arrow' && (handle === 'start' || handle === 'end')) {
      var nextArrow = precisionEditClone([originObject])[0];
      var fixedX = handle === 'start' ? Number(originObject.x2) : Number(originObject.x);
      var fixedY = handle === 'start' ? Number(originObject.y2) : Number(originObject.y);
      if (Math.hypot(point.x - fixedX, point.y - fixedY) < PRECISION_ANNOTATION_MIN_SIZE) return false;
      if (handle === 'start') {
        nextArrow.x = Math.max(0, Math.min(1, point.x));
        nextArrow.y = Math.max(0, Math.min(1, point.y));
      } else {
        nextArrow.x2 = Math.max(0, Math.min(1, point.x));
        nextArrow.y2 = Math.max(0, Math.min(1, point.y));
      }
      var changedArrow = Math.abs(Number(nextArrow.x) - Number(originObject.x)) > 0.0001 || Math.abs(Number(nextArrow.y) - Number(originObject.y)) > 0.0001 ||
        Math.abs(Number(nextArrow.x2) - Number(originObject.x2)) > 0.0001 || Math.abs(Number(nextArrow.y2) - Number(originObject.y2)) > 0.0001;
      precisionEditDragMoved = changedArrow;
      if (!changedArrow) return false;
      precisionEditObjects = precisionEditClone(precisionEditDragOrigin.objects).map(function(object) {
        return object.id === precisionEditSelectedId ? nextArrow : object;
      });
      return true;
    }
    nextBounds = { left: bounds.left, right: bounds.right, top: bounds.top, bottom: bounds.bottom };
    if (handle === 'nw' || handle === 'sw') nextBounds.left = Math.max(0, Math.min(bounds.right - PRECISION_ANNOTATION_MIN_SIZE, point.x));
    if (handle === 'ne' || handle === 'se') nextBounds.right = Math.min(1, Math.max(bounds.left + PRECISION_ANNOTATION_MIN_SIZE, point.x));
    if (handle === 'nw' || handle === 'ne') nextBounds.top = Math.max(0, Math.min(bounds.bottom - PRECISION_ANNOTATION_MIN_SIZE, point.y));
    if (handle === 'sw' || handle === 'se') nextBounds.bottom = Math.min(1, Math.max(bounds.top + PRECISION_ANNOTATION_MIN_SIZE, point.y));
  } else {
    var clampedDx = Math.max(-bounds.left, Math.min(1 - bounds.right, dx));
    var clampedDy = Math.max(-bounds.top, Math.min(1 - bounds.bottom, dy));
    nextBounds = {
      left: bounds.left + clampedDx, right: bounds.right + clampedDx,
      top: bounds.top + clampedDy, bottom: bounds.bottom + clampedDy
    };
  }
  var changedFromOrigin = Math.abs(nextBounds.left - bounds.left) > 0.0001 || Math.abs(nextBounds.right - bounds.right) > 0.0001 ||
    Math.abs(nextBounds.top - bounds.top) > 0.0001 || Math.abs(nextBounds.bottom - bounds.bottom) > 0.0001;
  if (!changedFromOrigin) nextBounds = bounds;
  var currentObject = precisionEditObjectById(precisionEditSelectedId);
  var currentBounds = precisionEditObjectBounds(currentObject || originObject);
  var displayChanged = Math.abs(nextBounds.left - currentBounds.left) > 0.0000001 || Math.abs(nextBounds.right - currentBounds.right) > 0.0000001 ||
    Math.abs(nextBounds.top - currentBounds.top) > 0.0000001 || Math.abs(nextBounds.bottom - currentBounds.bottom) > 0.0000001;
  precisionEditDragMoved = changedFromOrigin;
  if (!displayChanged) return false;
  precisionEditObjects = precisionEditClone(precisionEditDragOrigin.objects).map(function(object) {
    if (object.id !== precisionEditSelectedId) return object;
    return precisionEditApplyBounds(object, bounds, nextBounds);
  });
  return true;
}

function erasePrecisionBrushAt(point) {
  var canvas = document.getElementById('precisionAnnotationCanvas');
  var rect = canvas && canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : null;
  var shortSide = Math.max(1, Math.min(rect && rect.width || 1, rect && rect.height || 1));
  var radius = Math.max(0.012, Math.min(0.08, (precisionEditStyle().strokeWidth * 3) / shortSide));
  var changed = false;
  precisionEditObjects = precisionEditObjects.reduce(function(output, object) {
    if (object.type !== 'brush' || !object.points) { output.push(object); return output; }
    var objectChanged = false;
    var segments = [];
    var segment = [object.points[0]];
    function distanceToSegment(target, start, end) {
      var dx = end.x - start.x;
      var dy = end.y - start.y;
      var lengthSquared = dx * dx + dy * dy;
      if (!lengthSquared) return Math.hypot(target.x - start.x, target.y - start.y);
      var position = Math.max(0, Math.min(1, ((target.x - start.x) * dx + (target.y - start.y) * dy) / lengthSquared));
      return Math.hypot(target.x - (start.x + position * dx), target.y - (start.y + position * dy));
    }
    for (var pointIndex = 1; pointIndex < object.points.length; pointIndex++) {
      var previous = object.points[pointIndex - 1];
      var current = object.points[pointIndex];
      if (distanceToSegment(point, previous, current) <= radius) {
        objectChanged = true;
        if (segment.length >= 2) segments.push(segment);
        segment = [current];
      } else {
        segment.push(current);
      }
    }
    if (segment.length >= 2) segments.push(segment);
    if (!objectChanged) {
      output.push(object);
      return output;
    }
    changed = true;
    segments.forEach(function(points, segmentIndex) {
      var fragment = precisionEditClone([object])[0];
      fragment.points = points;
      if (segmentIndex > 0) {
        fragment.id = precisionEditNewId();
        fragment.label = precisionEditNewLabel();
      }
      output.push(fragment);
    });
    if (!segments.length && precisionEditSelectedId === object.id) precisionEditSelectedId = null;
    return output;
  }, []);
  if (changed && !precisionEditEraserChanged && precisionEditEraserSnapshot) {
    precisionEditHistory.push(precisionEditEraserSnapshot);
    if (precisionEditHistory.length > PRECISION_HISTORY_LIMIT) precisionEditHistory.shift();
    precisionEditRedo = [];
    precisionEditEraserChanged = true;
  }
  return changed;
}

function continuePrecisionEditPointer(event) {
  if (continuePrecisionCanvasPan(event)) {
    updatePrecisionEditCanvasCursor(event, event.currentTarget);
    return;
  }
  if (event.pointerId !== precisionEditPointerId) {
    updatePrecisionEditCanvasCursor(event, event.currentTarget);
    return;
  }
  var point = precisionEditCanvasPoint(event);
  if (!point) return;
  event.preventDefault();
  applyPrecisionEditPointerPoint(point);
  renderPrecisionEditCanvas();
  updatePrecisionEditCanvasCursor(event, event.currentTarget);
}

function endPrecisionEditPointer(event) {
  if (endPrecisionCanvasPan(event)) {
    updatePrecisionEditCanvasCursor(event, event.currentTarget);
    return;
  }
  if (!event || event.pointerId !== precisionEditPointerId || precisionEditPointerFinishing) return;
  precisionEditPointerFinishing = true;
  var pointerId = precisionEditPointerId;
  var canvas = precisionEditPointerTarget || event.currentTarget;
  var gestureCheckpoint = precisionEditGestureCheckpoint;
  var doubleClickCheckpoint = precisionEditDoubleClickMatches(precisionEditDoubleClickCheckpoint, event) ? precisionEditDoubleClickCheckpoint : null;
  try {
    // pointerup can be the last event outside the move stream; apply it before
    // copying the draft so the persisted geometry matches the visible endpoint.
    var finalPoint = precisionEditCanvasPoint(event);
    if (finalPoint) applyPrecisionEditPointerPoint(finalPoint);
    var draft = precisionEditClone([precisionEditDraftObject])[0];
    var dragOrigin = precisionEditDragOrigin;
    if (draft) {
      var bounds = precisionEditObjectBounds(draft);
      var validBrush = draft.type === 'brush' && draft.points && draft.points.length >= 2;
      if (validBrush || (bounds.right - bounds.left) > PRECISION_ANNOTATION_MIN_SIZE || (bounds.bottom - bounds.top) > PRECISION_ANNOTATION_MIN_SIZE) {
        capturePrecisionEditHistory();
        precisionEditObjects.push(draft);
        precisionEditSelectedId = draft.id;
        precisionEditPendingInstruction = '';
      }
    } else if (dragOrigin && precisionEditSelectedId && precisionEditDragMoved) {
      // The live array already contains the transformed object. Save the origin
      // as the undo snapshot instead of replacing the final object.
      capturePrecisionEditHistory();
      precisionEditHistory[precisionEditHistory.length - 1] = dragOrigin.objects;
    }
    precisionEditPointerId = null;
    precisionEditPointerTarget = null;
    precisionEditDraftObject = null;
    precisionEditDragOrigin = null;
    precisionEditDragMoved = false;
    precisionEditGestureCheckpoint = null;
    precisionEditEraserSnapshot = null;
    precisionEditEraserChanged = false;
    renderPrecisionEditCanvas();
    updatePrecisionEditControls();
    updatePrecisionEditCanvasCursor(event, canvas);
    if (doubleClickCheckpoint) {
      precisionEditDoubleClickCheckpoint = null;
      rollbackPrecisionEditDoubleClickCheckpoint(doubleClickCheckpoint.checkpoint);
      openPrecisionCanvasImageFullscreen(event);
      return;
    }
    rememberPrecisionEditDoubleClickCheckpoint(event, gestureCheckpoint);
    if (!precisionEditDoubleClickCheckpoint && precisionEditSelectedId) focusPrecisionEditInstruction(precisionEditSelectedId);
  } finally {
    // Clear state before releasing capture: browsers may synchronously dispatch
    // lostpointercapture, which must not commit the same gesture twice.
    if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(pointerId)) {
      try { canvas.releasePointerCapture(pointerId); } catch (error) {}
    }
    precisionEditPointerFinishing = false;
  }
}

function openPrecisionEditTextEditor(point, existingObject) {
  var editor = document.getElementById('precisionTextEditor');
  var surface = document.getElementById('precisionCanvasSurface');
  if (!editor || !surface) return;
  precisionEditTextDraftPoint = point;
  precisionEditTextEditingId = existingObject ? existingObject.id : null;
  editor.value = existingObject ? String(existingObject.text || '') : '';
  editor.style.color = existingObject && existingObject.color ? existingObject.color : precisionEditStyle().color;
  editor.style.fontSize = Math.max(12, Math.min(40, Number(existingObject && existingObject.fontSize) || Number(precisionEditStyle().fontSize) || 24)) + 'px';
  editor.classList.remove('hidden');
  var padding = 8;
  var left = point.x * surface.clientWidth;
  var top = point.y * surface.clientHeight;
  editor.style.left = Math.max(padding, Math.min(left, surface.clientWidth - editor.offsetWidth - padding)) + 'px';
  editor.style.top = Math.max(padding, Math.min(top, surface.clientHeight - editor.offsetHeight - padding)) + 'px';
  editor.focus();
}

function commitPrecisionEditText() {
  var editor = document.getElementById('precisionTextEditor');
  if (!editor || editor.classList.contains('hidden')) return;
  var text = editor.value.trim();
  var point = precisionEditTextDraftPoint;
  editor.classList.add('hidden');
  precisionEditTextDraftPoint = null;
  var editingId = precisionEditTextEditingId;
  precisionEditTextEditingId = null;
  if (!text || !point) return;
  if (editingId) {
    updatePrecisionEditObject(editingId, 'text', text);
    precisionEditSelectedId = editingId;
    return;
  }
  capturePrecisionEditHistory();
  var style = precisionEditStyle();
  var object = { id: precisionEditNewId(), type: 'text', x: point.x, y: point.y, text: text, label: precisionEditNewLabel(), instruction: text, color: style.color, strokeWidth: style.strokeWidth, fontSize: style.fontSize };
  precisionEditObjects.push(object);
  precisionEditSelectedId = object.id;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
  focusPrecisionEditInstruction(object.id);
}

function cancelPrecisionEditText() {
  var editor = document.getElementById('precisionTextEditor');
  if (editor) editor.classList.add('hidden');
  precisionEditTextDraftPoint = null;
  precisionEditTextEditingId = null;
}

function drawPrecisionEditObject(context, object, width, height, selected) {
  var x = object.x * width, y = object.y * height;
  var x2 = (object.x2 === undefined ? object.x : object.x2) * width;
  var y2 = (object.y2 === undefined ? object.y : object.y2) * height;
  context.save();
  var objectColor = /^#[0-9a-f]{6}$/i.test(object.color || '') ? object.color : '#ef4444';
  var objectStrokeWidth = Math.max(2, Math.min(16, Number(object.strokeWidth) || 5));
  context.strokeStyle = objectColor;
  context.fillStyle = objectColor;
  context.lineWidth = objectStrokeWidth;
  context.lineJoin = 'round';
  context.lineCap = 'round';
  if (object.type === 'rect') {
    context.strokeRect(x, y, x2 - x, y2 - y);
  } else if (object.type === 'ellipse') {
    context.beginPath();
    context.ellipse((x + x2) / 2, (y + y2) / 2, Math.abs(x2 - x) / 2, Math.abs(y2 - y) / 2, 0, 0, Math.PI * 2);
    context.stroke();
  } else if (object.type === 'brush') {
    var points = object.points || [];
    if (points.length) {
      context.beginPath();
      context.moveTo(points[0].x * width, points[0].y * height);
      points.slice(1).forEach(function(point) { context.lineTo(point.x * width, point.y * height); });
      context.stroke();
    }
  } else if (object.type === 'arrow') {
    var angle = Math.atan2(y2 - y, x2 - x);
    var head = Math.max(10, context.lineWidth * 4);
    context.beginPath();
    context.moveTo(x, y);
    context.lineTo(x2, y2);
    context.stroke();
    context.beginPath();
    context.moveTo(x2, y2);
    context.lineTo(x2 - head * Math.cos(angle - Math.PI / 6), y2 - head * Math.sin(angle - Math.PI / 6));
    context.lineTo(x2 - head * Math.cos(angle + Math.PI / 6), y2 - head * Math.sin(angle + Math.PI / 6));
    context.closePath();
    context.fill();
  } else if (object.type === 'text') {
    var fontSize = Math.max(12, Math.min(96, Number(object.fontSize) || Math.round(Math.min(width, height) * 0.035)));
    context.font = '600 ' + fontSize + 'px sans-serif';
    context.textBaseline = 'top';
    var textWidth = context.measureText(object.text).width;
    context.fillStyle = 'rgba(0,0,0,0.7)';
    context.fillRect(x - 5, y - 4, textWidth + 10, fontSize + 8);
    context.fillStyle = objectColor;
    context.fillText(object.text, x, y);
  }
  if (selected) drawPrecisionEditSelectionHighlight(context, object, width, height, objectStrokeWidth);
  drawPrecisionEditLabel(context, object, width, height, selected);
  if (selected && precisionEditIsBoxShape(object)) drawPrecisionEditHandles(context, object, width, height);
  else if (selected && precisionEditIsTransformable(object)) drawPrecisionEditHandles(context, object, width, height);
  context.restore();
}

function drawPrecisionEditSelectionHighlight(context, object, width, height, strokeWidth) {
  var accent = '#38bdf8';
  var glow = 'rgba(56, 189, 248, 0.2)';
  var outline = Math.max(2, Math.min(8, strokeWidth + 2));
  var pad = Math.max(5, outline * 1.5);
  var x = Number(object.x) * width;
  var y = Number(object.y) * height;
  var x2 = (object.x2 === undefined ? object.x : Number(object.x2)) * width;
  var y2 = (object.y2 === undefined ? object.y : Number(object.y2)) * height;
  context.save();
  context.lineJoin = 'round';
  context.lineCap = 'round';
  context.strokeStyle = accent;
  context.fillStyle = glow;
  context.lineWidth = outline;
  context.setLineDash([Math.max(5, outline * 2), Math.max(4, outline * 1.25)]);
  if (object.type === 'rect') {
    var left = Math.min(x, x2) - pad;
    var top = Math.min(y, y2) - pad;
    var rectWidth = Math.abs(x2 - x) + pad * 2;
    var rectHeight = Math.abs(y2 - y) + pad * 2;
    context.fillRect(left, top, rectWidth, rectHeight);
    context.strokeRect(left, top, rectWidth, rectHeight);
  } else if (object.type === 'ellipse') {
    var radiusX = Math.max(1, Math.abs(x2 - x) / 2) + pad;
    var radiusY = Math.max(1, Math.abs(y2 - y) / 2) + pad;
    context.beginPath();
    context.ellipse((x + x2) / 2, (y + y2) / 2, radiusX, radiusY, 0, 0, Math.PI * 2);
    context.fill();
    context.stroke();
  } else if (object.type === 'brush') {
    var points = object.points || [];
    if (points.length) {
      context.setLineDash([]);
      context.strokeStyle = 'rgba(56, 189, 248, 0.42)';
      context.lineWidth = strokeWidth + pad * 2;
      context.beginPath();
      context.moveTo(points[0].x * width, points[0].y * height);
      points.slice(1).forEach(function(point) { context.lineTo(point.x * width, point.y * height); });
      context.stroke();
      context.strokeStyle = accent;
      context.lineWidth = outline;
      context.beginPath();
      context.moveTo(points[0].x * width, points[0].y * height);
      points.slice(1).forEach(function(point) { context.lineTo(point.x * width, point.y * height); });
      context.stroke();
    }
  } else if (object.type === 'arrow') {
    context.setLineDash([]);
    context.strokeStyle = 'rgba(56, 189, 248, 0.42)';
    context.lineWidth = strokeWidth + pad * 2;
    context.beginPath();
    context.moveTo(x, y);
    context.lineTo(x2, y2);
    context.stroke();
    context.strokeStyle = accent;
    context.lineWidth = outline;
    context.beginPath();
    context.moveTo(x, y);
    context.lineTo(x2, y2);
    context.stroke();
  } else if (object.type === 'text') {
    var fontSize = Math.max(12, Math.min(96, Number(object.fontSize) || Math.round(Math.min(width, height) * 0.035)));
    context.font = '600 ' + fontSize + 'px sans-serif';
    var textWidth = context.measureText(object.text || '').width;
    context.fillRect(x - pad, y - pad, textWidth + pad * 2, fontSize + pad * 2);
    context.strokeRect(x - pad, y - pad, textWidth + pad * 2, fontSize + pad * 2);
  }
  context.restore();
}

function drawPrecisionEditHandles(context, object, width, height) {
  var handles = precisionEditHandlePoints(object);
  var halfSize = Math.max(5, Math.min(width, height) * 0.008);
  context.save();
  context.fillStyle = '#ffffff';
  context.strokeStyle = '#f59e0b';
  context.lineWidth = Math.max(2, Math.min(5, halfSize * 0.35));
  Object.keys(handles).forEach(function(name) {
    var point = handles[name];
    context.fillRect(point.x * width - halfSize, point.y * height - halfSize, halfSize * 2, halfSize * 2);
    context.strokeRect(point.x * width - halfSize, point.y * height - halfSize, halfSize * 2, halfSize * 2);
  });
  context.restore();
}

function drawPrecisionEditLabel(context, object, width, height, selected) {
  if (!object.label) return;
  var label = String(object.label);
  var radius = Math.max(10, context.lineWidth * 2.2);
  var anchor = object.type === 'brush' && object.points && object.points.length ? object.points[0] : object;
  var x = (anchor.x === undefined ? 0 : anchor.x) * width;
  var y = (anchor.y === undefined ? 0 : anchor.y) * height;
  var centerY = Math.max(radius, y - radius);
  if (object.type === 'text') centerY = Math.max(radius, y - radius * 0.4);
  context.font = '700 ' + Math.max(12, Math.round(radius)) + 'px sans-serif';
  context.fillStyle = selected ? '#0f172a' : '#ef4444';
  context.beginPath();
  context.arc(x + radius, centerY, radius, 0, Math.PI * 2);
  context.fill();
  context.strokeStyle = '#ffffff';
  context.lineWidth = 2;
  context.stroke();
  context.fillStyle = '#ffffff';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(label, x + radius, centerY);
  context.textAlign = 'start';
  context.textBaseline = 'alphabetic';
}

function renderPrecisionEditCanvas(includeAnnotations) {
  var canvas = document.getElementById('precisionAnnotationCanvas');
  if (!canvas || !precisionEditSourceImage) return;
  var context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.drawImage(precisionEditSourceImage, 0, 0, canvas.width, canvas.height);
  var drawAnnotations = includeAnnotations === undefined ? precisionEditAnnotationsVisible : includeAnnotations;
  if (drawAnnotations) {
    precisionEditObjects.forEach(function(object) {
      drawPrecisionEditObject(context, object, canvas.width, canvas.height, object.id === precisionEditSelectedId);
    });
    if (precisionEditDraftObject) drawPrecisionEditObject(context, precisionEditDraftObject, canvas.width, canvas.height, true);
  }
}

function precisionEditObjectById(id) {
  return precisionEditObjects.find(function(object) { return object.id === id; }) || null;
}

function precisionEditObjectName(object) {
  var typeKey = object.type === 'rect' ? 'creator.precision_edit_rectangle' : object.type === 'ellipse' ? 'creator.precision_edit_ellipse' : object.type === 'brush' ? 'creator.precision_edit_brush' : object.type === 'arrow' ? 'creator.precision_edit_arrow' : 'creator.precision_edit_text';
  return i18nText(typeKey) + ' ' + (object.label || '');
}

function selectPrecisionEditObject(id) {
  precisionEditSelectedId = precisionEditObjectById(id) ? id : null;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
  syncPrecisionAnnotationInstructionPopover();
}

function syncPrecisionEditStyleControls() {
  var object = precisionEditObjectById(precisionEditSelectedId);
  if (!object) return;
  var color = document.getElementById('precisionAnnotationColor');
  var width = document.getElementById('precisionStrokeWidth');
  var textSize = document.getElementById('precisionTextSize');
  if (color && /^#[0-9a-f]{6}$/i.test(object.color || '')) color.value = object.color;
  if (width && Number.isFinite(Number(object.strokeWidth))) width.value = String(Math.max(2, Math.min(16, Number(object.strokeWidth))));
  if (textSize && object.type === 'text') textSize.value = String(Math.max(12, Math.min(96, Number(object.fontSize) || 24)));
  updatePrecisionStrokeWidthValue();
  var textOutput = document.getElementById('precisionTextSizeValue');
  if (textOutput && textSize) textOutput.value = textOutput.textContent = textSize.value;
}

function updatePrecisionSelectedStyle(input, field, value) {
  var object = precisionEditObjectById(precisionEditSelectedId);
  if (!object || (field === 'fontSize' && object.type !== 'text')) return false;
  var captureHistory = !input || !input.dataset || input.dataset.precisionHistoryCaptured !== 'true';
  var changed = updatePrecisionEditObject(object.id, field, value, { captureHistory: captureHistory, preserveEditor: true });
  if (changed && captureHistory && input && input.dataset) input.dataset.precisionHistoryCaptured = 'true';
  return changed;
}

function focusPrecisionEditInstruction(id) {
  requestAnimationFrame(function() {
    if (!precisionEditObjectById(id)) return;
    precisionEditSelectedId = id;
    syncPrecisionAnnotationInstructionPopover({ focus: true, force: true });
    var input = document.getElementById('precisionAnnotationInstructionText');
    if (input) input.focus();
  });
}

function resetPrecisionAnnotationInstructionPopover() {
  precisionAnnotationInstructionPopoverState = {
    selectedId: '', dismissedId: '', manuallyPositioned: false, drag: null,
    positions: {}, confirmedIds: {}, dismissedIds: {}
  };
  var popover = document.getElementById('precisionAnnotationInstructionPopover');
  if (!popover) return;
  Array.prototype.slice.call(document.querySelectorAll('[data-precision-annotation-instruction-card="true"]')).forEach(function(card) { card.remove(); });
  popover.hidden = true;
  popover.setAttribute('aria-hidden', 'true');
  syncPrecisionAnnotationSummary();
  popover.removeAttribute('data-object-id');
}

function precisionAnnotationInstructionAnchor(object) {
  if (!object) return { x: 0.5, y: 0.5 };
  var x = Number(object.x);
  var y = Number(object.y);
  var x2 = Number(object.x2);
  var y2 = Number(object.y2);
  if (object.type === 'brush' && Array.isArray(object.points) && object.points.length) {
    var last = object.points[object.points.length - 1];
    x = Number(last.x);
    y = Number(last.y);
  } else if (object.type === 'rect' || object.type === 'ellipse' || object.type === 'arrow') {
    x = Number.isFinite(x2) ? Math.max(x, x2) : x;
    y = Number.isFinite(y2) ? Math.max(y, y2) : y;
  }
  return {
    x: Math.max(0, Math.min(1, Number.isFinite(x) ? x : 0.5)),
    y: Math.max(0, Math.min(1, Number.isFinite(y) ? y : 0.5))
  };
}

function precisionAnnotationInstructionCardElements(popover) {
  return {
    input: popover && popover.querySelector('textarea'),
    selection: popover && popover.querySelector('[data-precision-annotation-selection], #precisionAnnotationInstructionSelection'),
    confirm: popover && popover.querySelector('[data-precision-annotation-confirm], #btnPrecisionAnnotationInstructionConfirm'),
    close: popover && popover.querySelector('[data-precision-annotation-close], #btnPrecisionAnnotationInstructionClose')
  };
}

function precisionAnnotationInstructionClampPosition(popover, left, top) {
  var panel = document.getElementById('panelPrecisionEdit');
  if (!popover || !panel || !panel.getBoundingClientRect) return null;
  var rect = panel.getBoundingClientRect();
  var viewportWidth = Math.max(document.documentElement && document.documentElement.clientWidth || 0, window.innerWidth || 0);
  var viewportHeight = Math.max(document.documentElement && document.documentElement.clientHeight || 0, window.innerHeight || 0);
  var padding = 12;
  var width = Math.max(220, popover.offsetWidth || 280);
  var height = Math.max(150, popover.offsetHeight || 174);
  var minLeft = Math.max(padding, rect.left);
  var maxLeft = Math.max(minLeft, Math.min(viewportWidth - padding, rect.right) - width);
  var minTop = Math.max(padding, rect.top);
  var maxTop = Math.max(minTop, Math.min(viewportHeight - padding, rect.bottom) - height);
  return {
    left: Math.max(minLeft, Math.min(Number(left) || minLeft, maxLeft)),
    top: Math.max(minTop, Math.min(Number(top) || minTop, maxTop)),
    width: width,
    height: height
  };
}

function placePrecisionAnnotationInstructionPopover(popover, object, index) {
  // Keep the original one-argument call shape for focused UI contracts and
  // existing callers; multi-card rendering supplies its own card explicitly.
  if (!object) {
    object = popover;
    popover = document.getElementById('precisionAnnotationInstructionPopover');
  }
  var canvas = document.getElementById('precisionAnnotationCanvas');
  var panel = document.getElementById('panelPrecisionEdit');
  if (!popover || !canvas || !panel || !canvas.getBoundingClientRect || !panel.getBoundingClientRect) return;
  var panelRect = panel.getBoundingClientRect();
  var canvasRect = canvas.getBoundingClientRect();
  if (!panelRect.width || !panelRect.height || !canvasRect.width || !canvasRect.height) return;
  var viewportWidth = Math.max(document.documentElement && document.documentElement.clientWidth || 0, window.innerWidth || 0);
  var viewportHeight = Math.max(document.documentElement && document.documentElement.clientHeight || 0, window.innerHeight || 0);
  var padding = 12;
  var width = Math.max(220, popover.offsetWidth || 280);
  var height = Math.max(150, popover.offsetHeight || 174);
  var minLeft = Math.max(padding, panelRect.left);
  var maxLeft = Math.max(minLeft, Math.min(viewportWidth - padding, panelRect.right) - width);
  var minTop = Math.max(padding, panelRect.top);
  var maxTop = Math.max(minTop, Math.min(viewportHeight - padding, panelRect.bottom) - height);
  var clampPosition = function(left, top) {
    return {
      left: Math.max(minLeft, Math.min(Number(left) || minLeft, maxLeft)),
      top: Math.max(minTop, Math.min(Number(top) || minTop, maxTop)),
      width: width,
      height: height
    };
  };
  var state = precisionAnnotationInstructionPopoverState;
  var saved = object && state.positions && state.positions[object.id];
  if (saved && Number.isFinite(Number(saved.left)) && Number.isFinite(Number(saved.top))) {
    var savedPosition = clampPosition(saved.left, saved.top);
    popover.style.left = savedPosition.left + 'px';
    popover.style.top = savedPosition.top + 'px';
    state.positions[object.id] = savedPosition;
    return;
  }
  var anchor = precisionAnnotationInstructionAnchor(object);
  var anchorLeft = canvasRect.left + anchor.x * canvasRect.width;
  var anchorTop = canvasRect.top + anchor.y * canvasRect.height;
  var offsets = [
    [14, 14], [width + 26, 14], [14, height + 26], [-width - 26, 14],
    [14, -height - 26], [width + 26, height + 26], [-width - 26, height + 26],
    [width + 26, -height - 26], [-width - 26, -height - 26]
  ];
  var candidates = offsets.slice((Number(index) || 0) % offsets.length).concat(offsets.slice(0, (Number(index) || 0) % offsets.length));
  var position = null;
  candidates.some(function(offset) {
    var candidate = clampPosition(anchorLeft + offset[0], anchorTop + offset[1]);
    var overlaps = Object.keys(state.positions || {}).some(function(otherId) {
      if (otherId === object.id) return false;
      var other = state.positions[otherId];
      if (!other || !Number.isFinite(Number(other.left)) || !Number.isFinite(Number(other.top))) return false;
      var otherWidth = Math.max(220, Number(other.width) || width);
      var otherHeight = Math.max(150, Number(other.height) || height);
      return candidate.left < Number(other.left) + otherWidth + 12 && candidate.left + width + 12 > Number(other.left) && candidate.top < Number(other.top) + otherHeight + 12 && candidate.top + height + 12 > Number(other.top);
    });
    if (!overlaps) {
      position = candidate;
      return true;
    }
    return false;
  });
  position = position || clampPosition(anchorLeft + 14, anchorTop + 14);
  popover.style.left = position.left + 'px';
  popover.style.top = position.top + 'px';
  state.positions[object.id] = position;
}

function precisionAnnotationInstructionCardForObject(template, objectId) {
  if (template && template.dataset.objectId === objectId) return template;
  return document.querySelector('[data-precision-annotation-instruction-card="true"][data-object-id="' + String(objectId).replace(/"/g, '\\"') + '"]');
}

function createPrecisionAnnotationInstructionCard(template, objectId) {
  var card = template.cloneNode(true);
  var suffix = String(objectId).replace(/[^A-Za-z0-9_-]/g, '-');
  var title = card.querySelector('#precisionAnnotationInstructionTitle');
  var selection = card.querySelector('#precisionAnnotationInstructionSelection');
  var input = card.querySelector('#precisionAnnotationInstructionText');
  var label = card.querySelector('label[for="precisionAnnotationInstructionText"]');
  var confirm = card.querySelector('#btnPrecisionAnnotationInstructionConfirm');
  var close = card.querySelector('#btnPrecisionAnnotationInstructionClose');
  var handle = card.querySelector('#precisionAnnotationInstructionDragHandle');
  card.removeAttribute('id');
  card.dataset.precisionAnnotationInstructionCard = 'true';
  card.dataset.objectId = objectId;
  card.dataset.precisionBound = '';
  if (title) title.id = 'precisionAnnotationInstructionTitle-' + suffix;
  if (selection) { selection.id = 'precisionAnnotationInstructionSelection-' + suffix; selection.dataset.precisionAnnotationSelection = 'true'; }
  if (input) {
    input.id = 'precisionAnnotationInstructionText-' + suffix;
    input.dataset.precisionAnnotationInput = 'true';
    // The original textarea is styled through its legacy ID. Preserve the
    // essential dimensions for clones without widening the stylesheet scope.
    input.style.width = '100%';
    input.style.minHeight = '66px';
    input.style.resize = 'vertical';
  }
  if (label && input) label.htmlFor = input.id;
  if (confirm) { confirm.removeAttribute('id'); confirm.dataset.precisionAnnotationConfirm = 'true'; }
  if (close) { close.removeAttribute('id'); close.dataset.precisionAnnotationClose = 'true'; }
  if (handle) handle.removeAttribute('id');
  card.setAttribute('aria-labelledby', title ? title.id : '');
  card.setAttribute('aria-describedby', selection ? selection.id : '');
  template.insertAdjacentElement('afterend', card);
  return card;
}

function syncPrecisionAnnotationInstructionCard(popover, object, index, options) {
  var state = precisionAnnotationInstructionPopoverState;
  var elements = precisionAnnotationInstructionCardElements(popover);
  if (!popover || !elements.input) return;
  var dismissed = state.dismissedIds && state.dismissedIds[object.id];
  if (dismissed && !(options && options.force && object.id === precisionEditSelectedId)) {
    popover.hidden = true;
    popover.setAttribute('aria-hidden', 'true');
    return;
  }
  if (dismissed && options && options.force && object.id === precisionEditSelectedId) delete state.dismissedIds[object.id];
  popover.hidden = false;
  popover.setAttribute('aria-hidden', 'false');
  popover.dataset.objectId = object.id;
  popover.classList.toggle('is-confirmed', !!state.confirmedIds[object.id]);
  popover.dataset.confirmed = state.confirmedIds[object.id] ? 'true' : 'false';
  if (elements.selection) elements.selection.textContent = precisionEditObjectName(object);
  if (elements.confirm) elements.confirm.setAttribute('aria-pressed', state.confirmedIds[object.id] ? 'true' : 'false');
  if (document.activeElement !== elements.input) elements.input.value = precisionEditObjectInstruction(object);
  placePrecisionAnnotationInstructionPopover(popover, object, index);
}

function syncPrecisionAnnotationInstructionPopover(options) {
  options = options || {};
  var popover = document.getElementById('precisionAnnotationInstructionPopover');
  var input = document.getElementById('precisionAnnotationInstructionText');
  var objects = precisionEditObjects.slice();
  if (!popover || !input || !precisionEditSourceImage || !objects.length) {
    if (popover) {
      popover.hidden = true;
      popover.setAttribute('aria-hidden', 'true');
    }
    Array.prototype.slice.call(document.querySelectorAll('[data-precision-annotation-instruction-card="true"]')).forEach(function(card) { card.remove(); });
    syncPrecisionAnnotationSummary();
    return;
  }
  var state = precisionAnnotationInstructionPopoverState;
  var selected = precisionEditObjectById(precisionEditSelectedId) || objects[0];
  state.selectedId = selected.id;
  Array.prototype.slice.call(document.querySelectorAll('[data-precision-annotation-instruction-card="true"]')).forEach(function(card) { card.remove(); });
  bindPrecisionAnnotationInstructionCard(popover);
  if (state.confirmedIds[selected.id] && !options.force) {
    popover.hidden = true;
    popover.setAttribute('aria-hidden', 'true');
  } else {
    syncPrecisionAnnotationInstructionCard(popover, selected, 0, options);
  }
  syncPrecisionAnnotationSummary();
  if (options.focus) input.focus();
}

function syncPrecisionAnnotationSummary() {
  var region = document.getElementById('precisionAnnotationSummary');
  var cards = document.getElementById('precisionAnnotationSummaryCards');
  if (!region || !cards) return;
  cards.innerHTML = '';
  var confirmed = precisionEditObjects.filter(function(object) {
    return precisionAnnotationInstructionPopoverState.confirmedIds && precisionAnnotationInstructionPopoverState.confirmedIds[object.id];
  });
  region.hidden = !confirmed.length;
  if (!confirmed.length) return;
  confirmed.forEach(function(object) {
    var card = document.createElement('article');
    card.className = 'precision-annotation-summary-card';
    card.setAttribute('role', 'listitem');
    card.dataset.objectId = object.id;
    var open = document.createElement('button');
    open.type = 'button';
    open.className = 'precision-annotation-summary-card-open';
    open.setAttribute('aria-label', '编辑' + precisionEditObjectName(object) + '的修改说明');
    var title = document.createElement('strong');
    title.textContent = precisionEditObjectName(object);
    var text = document.createElement('span');
    text.textContent = precisionEditObjectInstruction(object) || '尚未填写修改说明';
    open.appendChild(title);
    open.appendChild(text);
    open.addEventListener('click', function() { focusPrecisionEditInstruction(object.id); });
    var remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'btn-ghost precision-annotation-summary-card-delete';
    remove.setAttribute('aria-label', '删除' + precisionEditObjectName(object) + '批注');
    remove.title = '删除批注';
    remove.textContent = '×';
    remove.addEventListener('click', function(event) {
      event.preventDefault();
      event.stopPropagation();
      confirmPrecisionAnnotationSummaryDelete(object.id);
    });
    card.appendChild(open);
    card.appendChild(remove);
    cards.appendChild(card);
  });
}

function confirmPrecisionAnnotationSummaryDelete(id) {
  var object = precisionEditObjectById(id);
  if (!object) return false;
  var message = '确定删除“' + precisionEditObjectName(object) + '”及其修改说明吗？此操作可通过撤销恢复。';
  if (typeof window === 'undefined' || typeof window.confirm !== 'function' || !window.confirm(message)) return false;
  // The object list is the generation payload source of truth. Keeping the
  // confirmation marker lets the existing object-history undo restore this
  // summary card without maintaining a second, divergent history stack.
  deletePrecisionEditObject(id);
  return true;
}

function bindPrecisionAnnotationInstructionCard(popover) {
  var elements = precisionAnnotationInstructionCardElements(popover);
  var input = elements.input;
  var close = elements.close;
  var confirm = elements.confirm;
  if (!popover || !input || popover.dataset.precisionBound === 'true') return;
  popover.dataset.precisionBound = 'true';
  input.addEventListener('input', function() {
    var id = popover.dataset.objectId;
    if (!id) return;
    var captureHistory = input.dataset.precisionHistoryCaptured !== 'true';
    var changed = updatePrecisionEditObject(id, 'instruction', input.value, { captureHistory: captureHistory, preserveEditor: true });
    if (changed && captureHistory) input.dataset.precisionHistoryCaptured = 'true';
    delete precisionAnnotationInstructionPopoverState.confirmedIds[id];
    popover.classList.remove('is-confirmed');
    popover.dataset.confirmed = 'false';
    if (confirm) confirm.setAttribute('aria-pressed', 'false');
    syncPrecisionAnnotationSummary();
  });
  input.addEventListener('blur', function() { finishPrecisionEditObjectInput(input); });
  var confirmInstruction = function(event) {
    if (event) { event.preventDefault(); event.stopPropagation(); }
    var id = popover.dataset.objectId || precisionAnnotationInstructionPopoverState.selectedId;
    if (id) precisionAnnotationInstructionPopoverState.confirmedIds[id] = true;
    finishPrecisionEditObjectInput(input);
    input.blur();
    popover.classList.add('is-confirmed');
    popover.dataset.confirmed = 'true';
    if (confirm) confirm.setAttribute('aria-pressed', 'true');
    popover.hidden = true;
    popover.setAttribute('aria-hidden', 'true');
    syncPrecisionAnnotationSummary();
  };
  if (confirm) confirm.addEventListener('click', confirmInstruction);
  if (close) close.addEventListener('click', function(event) {
    if (event) { event.preventDefault(); event.stopPropagation(); }
    var id = popover.dataset.objectId || precisionAnnotationInstructionPopoverState.selectedId;
    if (id) precisionAnnotationInstructionPopoverState.dismissedIds[id] = true;
    precisionAnnotationInstructionPopoverState.dismissedId = id || '';
    popover.hidden = true;
    popover.setAttribute('aria-hidden', 'true');
  });
  var beginDrag = function(event) {
    if (event.button !== 0) return;
    // Text fields and action buttons retain their native click/focus behavior;
    // every other blank card area is a drag surface.
    var target = event.target;
    if (target && target.closest && target.closest('textarea, input, button, select, a, label')) return;
    event.preventDefault();
    event.stopPropagation();
    precisionAnnotationInstructionPopoverState.drag = {
      pointerId: event.pointerId,
      card: popover,
      left: parseFloat(popover.style.left) || 0,
      top: parseFloat(popover.style.top) || 0,
      startX: event.clientX,
      startY: event.clientY
    };
    if (popover.setPointerCapture) {
      try { popover.setPointerCapture(event.pointerId); } catch (ignore) {}
    }
  };
  popover.addEventListener('pointerdown', beginDrag);
  popover.addEventListener('pointermove', function(event) {
    var drag = precisionAnnotationInstructionPopoverState.drag;
    var panel = document.getElementById('panelPrecisionEdit');
    if (!drag || drag.card !== popover || drag.pointerId !== event.pointerId || !panel || !panel.getBoundingClientRect) return;
    var position = precisionAnnotationInstructionClampPosition(popover, drag.left + event.clientX - drag.startX, drag.top + event.clientY - drag.startY);
    if (!position) return;
    popover.style.left = position.left + 'px';
    popover.style.top = position.top + 'px';
    precisionAnnotationInstructionPopoverState.manuallyPositioned = true;
    var id = popover.dataset.objectId || precisionAnnotationInstructionPopoverState.selectedId;
    if (id) precisionAnnotationInstructionPopoverState.positions[id] = position;
  });
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function(type) {
    popover.addEventListener(type, function(event) {
      var drag = precisionAnnotationInstructionPopoverState.drag;
      if (!drag || (event.pointerId !== undefined && drag.pointerId !== event.pointerId)) return;
      precisionAnnotationInstructionPopoverState.drag = null;
    });
  });
}

function bindPrecisionAnnotationInstructionPopover() {
  var popover = document.getElementById('precisionAnnotationInstructionPopover');
  if (!popover) return;
  var selection = document.getElementById('precisionAnnotationInstructionSelection');
  var input = document.getElementById('precisionAnnotationInstructionText');
  var confirm = document.getElementById('btnPrecisionAnnotationInstructionConfirm');
  var close = document.getElementById('btnPrecisionAnnotationInstructionClose');
  if (selection) selection.dataset.precisionAnnotationSelection = 'true';
  if (confirm) confirm.dataset.precisionAnnotationConfirm = 'true';
  if (close) close.dataset.precisionAnnotationClose = 'true';
  if (typeof bindPrecisionAnnotationInstructionCard === 'function') {
    bindPrecisionAnnotationInstructionCard(popover);
    return;
  }
  // The focused UI contract executes this legacy entry point in isolation.
  // Keep its pointer behavior self-contained while production uses the shared
  // binder above for the template and each cloned card.
  if (!input || popover.dataset.precisionBound === 'true') return;
  popover.dataset.precisionBound = 'true';
  popover.addEventListener('pointerdown', function(event) {
    if (event.button !== 0) return;
    var target = event.target;
    if (target && target.closest && target.closest('textarea, input, button, select, a, label')) return;
    event.preventDefault();
    event.stopPropagation();
    precisionAnnotationInstructionPopoverState.drag = {
      pointerId: event.pointerId, card: popover,
      left: parseFloat(popover.style.left) || 0,
      top: parseFloat(popover.style.top) || 0,
      startX: event.clientX, startY: event.clientY
    };
    if (popover.setPointerCapture) { try { popover.setPointerCapture(event.pointerId); } catch (ignore) {} }
  });
  popover.addEventListener('pointermove', function(event) {
    var drag = precisionAnnotationInstructionPopoverState.drag;
    var panel = document.getElementById('panelPrecisionEdit');
    if (!drag || drag.card !== popover || drag.pointerId !== event.pointerId || !panel || !panel.getBoundingClientRect) return;
    var rect = panel.getBoundingClientRect();
    var viewportWidth = Math.max(document.documentElement && document.documentElement.clientWidth || 0, window.innerWidth || 0);
    var viewportHeight = Math.max(document.documentElement && document.documentElement.clientHeight || 0, window.innerHeight || 0);
    var minLeft = Math.max(12, rect.left);
    var maxLeft = Math.max(minLeft, Math.min(viewportWidth - 12, rect.right) - popover.offsetWidth);
    var minTop = Math.max(12, rect.top);
    var maxTop = Math.max(minTop, Math.min(viewportHeight - 12, rect.bottom) - popover.offsetHeight);
    var left = Math.max(minLeft, Math.min(maxLeft, drag.left + event.clientX - drag.startX));
    var top = Math.max(minTop, Math.min(maxTop, drag.top + event.clientY - drag.startY));
    popover.style.left = left + 'px';
    popover.style.top = top + 'px';
    var id = popover.dataset.objectId || precisionAnnotationInstructionPopoverState.selectedId;
    if (id) precisionAnnotationInstructionPopoverState.positions[id] = { left: left, top: top, width: popover.offsetWidth, height: popover.offsetHeight };
  });
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function(type) {
    popover.addEventListener(type, function(event) {
      var drag = precisionAnnotationInstructionPopoverState.drag;
      if (!drag || (event.pointerId !== undefined && drag.pointerId !== event.pointerId)) return;
      precisionAnnotationInstructionPopoverState.drag = null;
    });
  });
}

function updatePrecisionEditObject(id, field, value, options) {
  var object = precisionEditObjectById(id);
  if (!object) return false;
  var next = field === 'instruction' || field === 'text' ? String(value || '').slice(0, 500) : value;
  if (object[field] === next) return false;
  var previous = object[field];
  if (!options || options.captureHistory !== false) capturePrecisionEditHistory();
  object[field] = next;
  if (field === 'text' && (!precisionEditObjectInstruction(object) || object.instruction === previous)) object.instruction = next;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls({ renderObjectList: !(options && options.preserveEditor) });
  return true;
}

function updatePrecisionEditObjectFromInput(input, field) {
  if (!input) return;
  var id = field === 'text' ? input.dataset.precisionText : input.dataset.precisionInstruction;
  var captureHistory = input.dataset.precisionHistoryCaptured !== 'true';
  var changed = updatePrecisionEditObject(id, field, input.value, {
    captureHistory: captureHistory,
    preserveEditor: true
  });
  if (changed && captureHistory) input.dataset.precisionHistoryCaptured = 'true';
}

function finishPrecisionEditObjectInput(input) {
  if (input && input.dataset) delete input.dataset.precisionHistoryCaptured;
}

function deletePrecisionEditObject(id) {
  var object = precisionEditObjectById(id);
  if (!object) return;
  capturePrecisionEditHistory();
  precisionEditObjects = precisionEditObjects.filter(function(item) { return item.id !== id; });
  if (precisionEditSelectedId === id) precisionEditSelectedId = null;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
}

function renderPrecisionEditObjectList() {
  var list = document.getElementById('precisionEditObjectList');
  var summary = document.getElementById('precisionSessionSummary');
  if (!list && !summary) return;
  // Confirmed annotation cards live in the canvas-side summary rather than
  // duplicating the same editable list in the fixed inspector.
  var annotationSummary = document.getElementById('precisionAnnotationSummary');
  if (list && annotationSummary) {
    var listSection = list.closest && list.closest('.precision-edit-list');
    if (listSection) listSection.hidden = true;
    list.innerHTML = '';
    list.setAttribute('aria-hidden', 'true');
    list = null;
  }
  var useSessionSummary = !!summary;
  if (summary) {
    summary.innerHTML = precisionEditObjects.length ? precisionEditObjects.map(function(object) {
      var selected = object.id === precisionEditSelectedId;
      var instruction = precisionEditObjectInstruction(object);
      return '<article class="precision-session-summary-item' + (selected ? ' selected' : '') + '" data-precision-summary-object="' + escAttr(object.id) + '">' +
        '<strong>' + escHtml(precisionEditObjectName(object)) + '</strong>' +
        '<p title="' + escAttr(instruction || i18nText('creator.precision_edit_object_instruction_placeholder')) + '"><span>' + escHtml(i18nText('creator.precision_edit_object_instruction')) + '</span><b>' + escHtml(instruction || i18nText('creator.precision_edit_object_instruction_placeholder')) + '</b></p>' +
      '</article>';
    }).join('') : '<p class="precision-session-summary-empty">' + escHtml(i18nText('creator.precision_edit_changes_empty')) + '</p>';
  }
  if (!list) return;
  if (!precisionEditObjects.length) {
    list.innerHTML = '<p class="precision-object-empty">' + escHtml(i18nText('creator.precision_edit_changes_empty')) + '</p>';
    return;
  }
  list.innerHTML = precisionEditObjects.map(function(object) {
    var selected = object.id === precisionEditSelectedId;
    var instruction = precisionEditObjectInstruction(object);
    var textField = !useSessionSummary && object.type === 'text'
      ? '<input class="precision-object-text" value="' + escAttr(object.text || '') + '" maxlength="500" data-precision-text="' + escAttr(object.id) + '" aria-label="' + escAttr(i18nText('creator.precision_edit_text')) + '">'
      : '';
    var instructionSummary = useSessionSummary ? '' :
      '<p class="precision-object-instruction-summary" title="' + escAttr(instruction || i18nText('creator.precision_edit_object_instruction_placeholder')) + '"><span>' + escHtml(i18nText('creator.precision_edit_object_instruction')) + '</span><strong>' + escHtml(instruction || i18nText('creator.precision_edit_object_instruction_placeholder')) + '</strong></p>';
    return '<article class="precision-object-row' + (selected ? ' selected' : '') + '" data-precision-object="' + escAttr(object.id) + '">' +
      '<button type="button" class="precision-object-select" onclick="selectPrecisionEditObject(\'' + escAttr(object.id) + '\')">' + escHtml(precisionEditObjectName(object)) + '</button>' +
      textField +
      instructionSummary +
      '<button type="button" class="btn-ghost precision-object-delete" onclick="deletePrecisionEditObject(\'' + escAttr(object.id) + '\')" title="' + escAttr(i18nText('creator.precision_edit_delete')) + '">×</button>' +
    '</article>';
  }).join('');
  list.querySelectorAll('[data-precision-text]').forEach(function(input) {
    input.addEventListener('input', function() { updatePrecisionEditObjectFromInput(input, 'text'); });
    input.addEventListener('blur', function() { finishPrecisionEditObjectInput(input); });
  });
}

function updatePrecisionAnnotationPreview() {
  var image = document.getElementById('precisionAnnotationPreview');
  var empty = document.getElementById('precisionPreviewEmpty');
  var frame = document.getElementById('precisionPreviewFrame');
  var count = document.getElementById('precisionAnnotationCount');
  if (count) count.textContent = String(precisionEditObjects.length);
  if (!image || !empty || !frame) return;
  if (!precisionEditSourceImage || !precisionEditObjects.length) {
    image.removeAttribute('src');
    image.classList.add('hidden');
    empty.classList.remove('hidden');
    frame.classList.add('is-empty');
    return;
  }
  image.src = exportPrecisionEditAnnotationImage();
  image.classList.remove('hidden');
  empty.classList.add('hidden');
  frame.classList.remove('is-empty');
}

function precisionLocalPathUrl(localPath) {
  if (!localPath) return '';
  return '/api/gallery/image/' + encodeURIComponent(String(localPath).split(/[\\/]/).pop());
}

function precisionCompareValueFromPointer(event, stage) {
  var rect = stage && stage.getBoundingClientRect ? stage.getBoundingClientRect() : null;
  var clientX = Number(event && event.clientX);
  if (!rect || !rect.width || !Number.isFinite(clientX)) return null;
  return ((clientX - rect.left) / rect.width) * 100;
}

function beginPrecisionComparePointer(event) {
  var stage = event && event.currentTarget;
  if (!stage || precisionEditSession.view !== 'compare' || precisionComparePointerId !== null) return;
  if (event.button !== undefined && event.button !== 0 && event.pointerType !== 'touch') return;
  precisionComparePointerId = event.pointerId;
  precisionComparePointerTarget = stage;
  if (stage.setPointerCapture) {
    try { stage.setPointerCapture(event.pointerId); } catch (error) {}
  }
  if (event.preventDefault) event.preventDefault();
  var value = precisionCompareValueFromPointer(event, stage);
  if (value !== null) updatePrecisionCompareSlider(value);
}

function continuePrecisionComparePointer(event) {
  if (!event || event.pointerId !== precisionComparePointerId) return;
  if (event.preventDefault) event.preventDefault();
  var stage = precisionComparePointerTarget || event.currentTarget;
  var value = precisionCompareValueFromPointer(event, stage);
  if (value !== null) updatePrecisionCompareSlider(value);
}

function endPrecisionComparePointer(event) {
  if (!event || event.pointerId !== precisionComparePointerId) return;
  var pointerId = precisionComparePointerId;
  var stage = precisionComparePointerTarget || event.currentTarget;
  if (event.type === 'pointerup') {
    var value = precisionCompareValueFromPointer(event, stage);
    if (value !== null) updatePrecisionCompareSlider(value);
  }
  precisionComparePointerId = null;
  precisionComparePointerTarget = null;
  if (stage && stage.hasPointerCapture && stage.hasPointerCapture(pointerId) && stage.releasePointerCapture) {
    try { stage.releasePointerCapture(pointerId); } catch (error) {}
  }
}

function handlePrecisionCompareKeydown(event) {
  if (precisionEditSession.view !== 'compare' || ['ArrowLeft', 'ArrowRight', 'Home', 'End'].indexOf(event.key) === -1) return;
  event.preventDefault();
  var slider = document.getElementById('precisionCompareSlider');
  var value = Number(slider && slider.value || 50);
  if (event.key === 'ArrowLeft') value -= 5;
  if (event.key === 'ArrowRight') value += 5;
  if (event.key === 'Home') value = 0;
  if (event.key === 'End') value = 100;
  updatePrecisionCompareSlider(value);
}

function bindPrecisionCompareEvents(stage) {
  if (!stage) {
    if (precisionCompareResizeCleanup) precisionCompareResizeCleanup();
    return;
  }
  if (stage.dataset.precisionBound !== 'true') {
    stage.dataset.precisionBound = 'true';
    stage.style.touchAction = 'none';
    stage.setAttribute('role', 'slider');
    stage.setAttribute('aria-valuemin', '0');
    stage.setAttribute('aria-valuemax', '100');
    stage.addEventListener('pointerdown', beginPrecisionComparePointer);
    stage.addEventListener('pointermove', continuePrecisionComparePointer);
    stage.addEventListener('pointerup', endPrecisionComparePointer);
    stage.addEventListener('pointercancel', endPrecisionComparePointer);
    stage.addEventListener('lostpointercapture', endPrecisionComparePointer);
    stage.addEventListener('keydown', handlePrecisionCompareKeydown);
    stage.addEventListener('dblclick', function(event) {
      event.preventDefault();
      event.stopPropagation();
      openPrecisionCanvasImageFullscreen(event);
    });
  }
  if (stage.dataset.precisionResizeBound === 'true') return;
  if (precisionCompareResizeCleanup) precisionCompareResizeCleanup();
  stage.dataset.precisionResizeBound = 'true';
  var syncCompareSize = function() {
    var slider = document.getElementById('precisionCompareSlider');
    updatePrecisionCompareSlider(slider ? slider.value : 50);
  };
  var observer = null;
  if (typeof ResizeObserver === 'function') {
    observer = new ResizeObserver(syncCompareSize);
    observer.observe(stage);
    stage._precisionResizeObserver = observer;
  }
  var cleanup = function() {
    if (observer) observer.disconnect();
    window.removeEventListener('resize', syncCompareSize);
    window.removeEventListener('pagehide', cleanup);
    if (stage._precisionResizeObserver === observer) delete stage._precisionResizeObserver;
    if (stage.dataset) delete stage.dataset.precisionResizeBound;
    if (precisionCompareResizeCleanup === cleanup) precisionCompareResizeCleanup = null;
    if (window.__genboxPrecisionCompareResizeCleanup === cleanup) window.__genboxPrecisionCompareResizeCleanup = null;
  };
  precisionCompareResizeCleanup = cleanup;
  window.__genboxPrecisionCompareResizeCleanup = cleanup;
  window.addEventListener('resize', syncCompareSize);
  window.addEventListener('pagehide', cleanup, { once: true });
}

function precisionEditSessionEntries() {
  return [precisionEditSession.source].concat(precisionEditSession.versions || []).filter(Boolean);
}

function precisionEditSessionEntry(entries, id, fallback) {
  return entries.find(function(entry) { return entry && entry.id === id; }) || fallback || null;
}

function precisionFullscreenVisibleEntry(event) {
  var entries = precisionEditSessionEntries();
  var source = precisionEditSessionEntry(entries, 'original', entries[0]);
  var current = precisionEditSessionEntry(entries, precisionEditSession.selectedVersionId, source);
  var comparisonBase = precisionEditSessionEntry(entries, current && current.parentId || 'original', source);
  if (event && event.precisionSelectedVersion === true) return current;
  var target = event && event.currentTarget;
  if (target && (target.id === 'precisionAnnotationCanvas' || target.id === 'precisionTextEditor')) {
    return precisionEditSessionEntry(entries, precisionEditSession.baseVersionId, source);
  }
  if (precisionEditSession.view === 'before') return comparisonBase;
  if (precisionEditSession.view === 'compare') {
    var stage = document.getElementById('precisionCompareStage');
    var slider = document.getElementById('precisionCompareSlider');
    var divider = Math.max(0, Math.min(100, Number(slider && slider.value) || 50));
    var pointerValue = precisionCompareValueFromPointer(event, stage);
    return pointerValue !== null && pointerValue <= divider ? current : comparisonBase;
  }
  return current;
}

function movePrecisionImageFullscreenIntoCurrentRoot() {
  var overlay = document.getElementById('precisionImageFullscreen');
  var root = document.fullscreenElement;
  if (!overlay || !root || (root.contains && root.contains(overlay))) return false;
  precisionImageFullscreenRestore = { parent: overlay.parentNode, nextSibling: overlay.nextSibling };
  if (!precisionImageFullscreenRestore.parent || !root.appendChild) {
    precisionImageFullscreenRestore = null;
    return false;
  }
  root.appendChild(overlay);
  return true;
}

function restorePrecisionImageFullscreenRoot() {
  if (!precisionImageFullscreenRestore) return;
  var overlay = document.getElementById('precisionImageFullscreen');
  var restore = precisionImageFullscreenRestore;
  precisionImageFullscreenRestore = null;
  if (!overlay || !restore.parent) return;
  if (restore.nextSibling && restore.nextSibling.parentNode === restore.parent && restore.parent.insertBefore) restore.parent.insertBefore(overlay, restore.nextSibling);
  else if (restore.parent.appendChild) restore.parent.appendChild(overlay);
}

function openPrecisionCanvasImageFullscreen(event) {
  var entries = precisionEditSessionEntries();
  var current = precisionFullscreenVisibleEntry(event);
  if (!current || !current.data) return false;
  var openViewer = function() {
    return openPrecisionImageFullscreen(current.data, current.label || '', {
      prompt: current.prompt || '',
      sessionEntries: entries,
      currentId: current.id
    });
  };
  if (document.fullscreenElement && typeof document.exitFullscreen === 'function') {
    var settled = false;
    var timeoutId = null;
    var cleanup = function() {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
      if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);
      timeoutId = null;
    };
    var finish = function(fallback) {
      if (settled) return false;
      settled = true;
      cleanup();
      if (fallback) {
        setStatus('无法退出工作台全屏，已在当前工作台中打开图片查看。');
        movePrecisionImageFullscreenIntoCurrentRoot();
      }
      return openViewer();
    };
    var onFullscreenChange = function() {
      if (!document.fullscreenElement) finish(false);
    };
    var scheduleFallback = function() {
      if (settled) return;
      if (typeof setTimeout !== 'function') { finish(true); return; }
      timeoutId = setTimeout(function() {
        if (!settled) finish(true);
      }, PRECISION_FULLSCREEN_EXIT_WAIT_MS);
    };
    document.addEventListener('fullscreenchange', onFullscreenChange);
    try {
      var exitResult = document.exitFullscreen();
      if (exitResult && typeof exitResult.then === 'function') {
        exitResult.then(function() {
          if (!document.fullscreenElement) finish(false);
          else scheduleFallback();
        }).catch(function() { finish(true); });
        return true;
      }
      if (!document.fullscreenElement) return finish(false);
      scheduleFallback();
      return true;
    } catch (error) {
      return finish(true);
    }
  }
  return openViewer();
}

function openPrecisionSelectedImageFullscreen() {
  return openPrecisionCanvasImageFullscreen({ precisionSelectedVersion: true });
}

function renderPrecisionEditSession() {
  var rail = document.getElementById('precisionVersionRail');
  var before = document.getElementById('precisionCompareBefore');
  var after = document.getElementById('precisionCompareAfter');
  var stage = document.getElementById('precisionCompareStage');
  var useAsBase = document.getElementById('btnPrecisionUseSelectedAsBase');
  if (!rail || !before || !after || !stage) return;
  if (!precisionEditSession.source) {
    renderPrecisionSessionShowcase([]);
    return;
  }
  var selected = precisionEditSession.selectedVersionId;
  var entries = [precisionEditSession.source].concat(precisionEditSession.versions);
  var versionSwitchPending = typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending;
  rail.innerHTML = entries.map(function(entry) {
    var active = entry.id === selected;
    return '<div class="precision-version-item" role="presentation"><button type="button" role="tab" class="precision-version' + (active ? ' selected' : '') + '" data-precision-version-id="' + escAttr(entry.id) + '" aria-selected="' + (active ? 'true' : 'false') + '"' + (active ? ' aria-current="true"' : '') + ' tabindex="' + (active ? '0' : '-1') + '" onclick="selectPrecisionVersion(\'' + escAttr(entry.id) + '\',{focusRail:true})" onkeydown="handlePrecisionVersionRailKeydown(event)"' + (versionSwitchPending ? ' disabled aria-disabled="true"' : '') + '>' + escHtml(entry.label) + '</button></div>';
  }).join('');
  var current = entries.find(function(entry) { return entry.id === selected; }) || precisionEditSession.source;
  var base = entries.find(function(entry) { return entry.id === (current.parentId || 'original'); }) || precisionEditSession.source;
  var hasComparison = current.id !== base.id;
  var isEditingBase = current.id === precisionEditSession.baseVersionId;
  var canUseSelectedAsBase = current.id !== precisionEditSession.baseVersionId && !precisionSourceTaskIsActive() && !(typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending);
  if (useAsBase) {
    useAsBase.disabled = !canUseSelectedAsBase;
    useAsBase.setAttribute('aria-disabled', canUseSelectedAsBase ? 'false' : 'true');
  }
  before.src = base.data;
  after.src = current.data;
  stage.dataset.afterTransparent = current.transparent === true ? 'true' : 'false';
  stage.style.display = !isEditingBase || (hasComparison && precisionEditSession.view !== 'after') ? 'block' : 'none';
  stage.style.pointerEvents = precisionEditSession.view === 'compare' ? 'auto' : 'none';
  stage.classList.toggle('is-before', precisionEditSession.view === 'before');
  stage.classList.toggle('is-after', precisionEditSession.view === 'after');
  stage.classList.toggle('is-compare', precisionEditSession.view === 'compare');
  document.querySelectorAll('[data-precision-view]').forEach(function(button) {
    var active = button.dataset.precisionView === precisionEditSession.view;
    button.classList.toggle('btn-secondary', active);
    button.classList.toggle('btn-ghost', !active);
  });
  updatePrecisionCompareSlider((document.getElementById('precisionCompareSlider') || { value: 50 }).value);
  renderPrecisionSessionShowcase(entries);
  if (typeof updatePrecisionCanvasImageInfo === 'function') updatePrecisionCanvasImageInfo();
  updatePrecisionCutoutRefineControls();
}

function renderPrecisionSessionShowcase(entries) {
  ensurePrecisionSessionShowcaseControls();
  var gallery = document.getElementById('precisionSessionGallery');
  var count = document.getElementById('precisionSessionResultCount');
  var strip = document.getElementById('precisionPromptStrip');
  entries = (entries || []).filter(function(entry) { return entry && entry.data; });
  var source = entries[0] || null;
  var results = entries.slice(1);
  var historyPosters = precisionWorkflowHistoryPosterMarkup(precisionWorkflowHistoryState.items || []);
  if (count) count.textContent = String(results.length + historyPosters.count);
  if (gallery) gallery.innerHTML = results.length || historyPosters.markup ? results.map(function(entry, index) {
    var selected = entry.id === precisionEditSession.selectedVersionId;
    var label = String(entry.label || ('结果 ' + (index + 1)));
    return '<div class="precision-session-item" role="listitem"><button type="button" class="precision-session-thumb' + (selected ? ' selected' : '') + '" data-version-id="' + escAttr(entry.id) + '" onclick="selectPrecisionVersion(\'' + escAttr(entry.id) + '\')" aria-label="' + escAttr(label) + '"' + (selected ? ' aria-current="true"' : '') + ' title="' + escAttr(label) + '"><img src="' + escAttr(entry.data) + '" alt="" loading="lazy" draggable="false"><span>' + (index + 1) + '</span></button></div>';
  }).join('') + historyPosters.markup : '<p class="precision-session-empty">' + escHtml(i18nText('creator.precision_session_empty')) + '</p>';
  if (strip) strip.innerHTML = '';
}

function setPrecisionSessionShowcaseOpen(open, restoreFocus) {
  var showcase = document.getElementById('precisionSessionShowcase');
  var trigger = document.getElementById('btnPrecisionSessionShowcaseToggle');
  var content = document.getElementById('precisionSessionShowcaseContent');
  if (!showcase || !trigger || !content) return false;
  var wasOpen = showcase.classList.contains('is-expanded');
  var nextOpen = !!open;
  showcase.classList.toggle('is-expanded', nextOpen);
  trigger.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  content.setAttribute('aria-hidden', nextOpen ? 'false' : 'true');
  if (nextOpen) content.removeAttribute('inert');
  else content.setAttribute('inert', '');
  if (!nextOpen) {
    togglePrecisionSessionDatePopover(false);
    setPrecisionWorkflowHistoryFilterOpen(false);
    setPrecisionWorkflowHistoryActionOpen(false);
  }
  if (nextOpen && !precisionWorkflowHistoryState.loaded) loadPrecisionWorkflowHistory();
  if (!nextOpen && restoreFocus && wasOpen && typeof trigger.focus === 'function') trigger.focus();
  return wasOpen;
}

function togglePrecisionSessionShowcase() {
  var showcase = document.getElementById('precisionSessionShowcase');
  if (!showcase) return false;
  setPrecisionSessionShowcaseOpen(!showcase.classList.contains('is-expanded'));
  return showcase.classList.contains('is-expanded');
}

function ensurePrecisionSessionShowcaseControls() {
  var showcase = document.getElementById('precisionSessionShowcase');
  var content = document.getElementById('precisionSessionShowcaseContent');
  var toggle = document.getElementById('btnPrecisionSessionShowcaseToggle');
  var workflow = showcase && showcase.querySelector('.precision-workflow-history');
  if (!showcase || !content || !toggle || !workflow) return null;
  var controls = document.getElementById('precisionSessionShowcaseControls');
  if (!controls) {
    controls = document.createElement('div');
    controls.id = 'precisionSessionShowcaseControls';
    controls.className = 'precision-session-showcase-controls';
    controls.setAttribute('role', 'group');
    controls.setAttribute('aria-label', '精准改图图库操作');
    showcase.insertBefore(controls, content);
  }
  if (toggle.parentElement !== controls) controls.appendChild(toggle);
  if (workflow.parentElement !== controls) controls.appendChild(workflow);
  return controls;
}

function precisionWorkflowHistoryMediaUrl(value) {
  var url = String(value || '');
  return /^\/api\/precision\/workflows\/pw_[a-f0-9]{32}\/versions\/(?:original|pv_[a-f0-9]{24})\/(?:thumb|image)$/.test(url) ? url : '';
}

function precisionWorkflowHistoryStatus(message) {
  var status = document.getElementById('precisionWorkflowHistoryStatus');
  if (status) status.textContent = message || '';
}

function precisionWorkflowHistoryFilters() {
  var state = precisionWorkflowHistoryCalendarState();
  return {
    dateFrom: String(state.dateFrom || ''),
    dateTo: String(state.dateTo || '')
  };
}

function precisionWorkflowHistoryCalendarState() {
  return window.precisionWorkflowHistoryCalendarState || (window.precisionWorkflowHistoryCalendarState = {
    anchor: new Date(),
    dateFrom: '',
    dateTo: '',
    anchorExplicit: false
  });
}

function precisionWorkflowHistoryDateKeys(workflow) {
  var keys = [];
  (Array.isArray(workflow && workflow.versions) ? workflow.versions : []).forEach(function(version) {
    var time = Date.parse(String(version && version.created_at || ''));
    if (Number.isFinite(time)) keys.push(precisionCalendarDateKey(new Date(time)));
  });
  if (!keys.length) {
    var fallback = Date.parse(String(workflow && (workflow.updated_at || workflow.created_at) || ''));
    if (Number.isFinite(fallback)) keys.push(precisionCalendarDateKey(new Date(fallback)));
  }
  return keys;
}

function precisionWorkflowHistoryCalendarIndex() {
  var index = {};
  (precisionWorkflowHistoryState.calendarItems || precisionWorkflowHistoryState.items || []).forEach(function(workflow) {
    precisionWorkflowHistoryDateKeys(workflow).forEach(function(key) {
      index[key] = (index[key] || 0) + 1;
    });
  });
  return index;
}

function renderPrecisionWorkflowHistoryCalendar() {
  var calendar = document.getElementById('precisionWorkflowHistoryCalendar');
  var label = document.getElementById('precisionWorkflowHistoryCalendarLabel');
  if (!calendar || !label) return;
  var state = precisionWorkflowHistoryCalendarState();
  var anchor = new Date(state.anchor.getFullYear(), state.anchor.getMonth(), 1);
  state.anchor = anchor;
  label.textContent = anchor.getFullYear() + '年' + (anchor.getMonth() + 1) + '月';
  var firstDay = new Date(anchor.getFullYear(), anchor.getMonth(), 1).getDay();
  var days = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0).getDate();
  var index = precisionWorkflowHistoryCalendarIndex();
  var today = precisionCalendarDateKey(new Date());
  var html = ['<span class="precision-workflow-history-calendar-weekday">日</span><span class="precision-workflow-history-calendar-weekday">一</span><span class="precision-workflow-history-calendar-weekday">二</span><span class="precision-workflow-history-calendar-weekday">三</span><span class="precision-workflow-history-calendar-weekday">四</span><span class="precision-workflow-history-calendar-weekday">五</span><span class="precision-workflow-history-calendar-weekday">六</span>'];
  for (var blank = 0; blank < firstDay; blank += 1) html.push('<span class="precision-workflow-history-calendar-day is-placeholder" aria-hidden="true"></span>');
  for (var day = 1; day <= days; day += 1) {
    var key = precisionCalendarDateKey(new Date(anchor.getFullYear(), anchor.getMonth(), day));
    var hasHistory = !!index[key];
    var selected = !!state.dateFrom && key >= state.dateFrom && (!state.dateTo || key <= state.dateTo);
    var classes = 'precision-workflow-history-calendar-day' + (hasHistory ? ' has-history' : ' is-empty') + (selected ? ' selected' : '') + (key === today ? ' today' : '');
    html.push('<button type="button" class="' + classes + '" data-workflow-date="' + key + '" aria-label="' + escAttr(key + (hasHistory ? '，' + index[key] + ' 个历史工作流' : '，无历史工作流')) + '" aria-pressed="' + (selected ? 'true' : 'false') + '" onclick="selectPrecisionWorkflowHistoryCalendarDate(\'' + key + '\')"><span>' + day + '</span>' + (hasHistory ? '<small></small>' : '') + '</button>');
  }
  calendar.innerHTML = html.join('');
}

function shiftPrecisionWorkflowHistoryCalendar(offset) {
  var state = precisionWorkflowHistoryCalendarState();
  state.anchor = new Date(state.anchor.getFullYear(), state.anchor.getMonth() + Number(offset || 0), 1);
  state.anchorExplicit = true;
  renderPrecisionWorkflowHistoryCalendar();
  var toolbar = document.querySelector('.precision-workflow-history-calendar-toolbar');
  var buttons = toolbar ? toolbar.querySelectorAll('button') : [];
  var focusTarget = buttons[Number(offset) < 0 ? 0 : buttons.length - 1];
  if (focusTarget && typeof focusTarget.focus === 'function') focusTarget.focus();
}

function setPrecisionWorkflowHistoryDateRange(range) {
  var end = new Date();
  var start = new Date(end);
  if (range === '3d' || range === '5d') start.setDate(start.getDate() - (range === '3d' ? 2 : 4));
  else if (range === 'week') start.setDate(end.getDate() - end.getDay());
  else if (range === 'month') start = new Date(end.getFullYear(), end.getMonth(), 1);
  else if (range === 'quarter') start = new Date(end.getFullYear(), Math.floor(end.getMonth() / 3) * 3, 1);
  else if (range === 'half-year') start = new Date(end.getFullYear(), end.getMonth() < 6 ? 0 : 6, 1);
  else if (range === 'year') start = new Date(end.getFullYear(), 0, 1);
  else return false;
  var state = precisionWorkflowHistoryCalendarState();
  state.dateFrom = precisionCalendarDateKey(start);
  state.dateTo = precisionCalendarDateKey(end);
  state.anchor = new Date(end.getFullYear(), end.getMonth(), 1);
  state.anchorExplicit = true;
  renderPrecisionWorkflowHistoryCalendar();
  return loadPrecisionWorkflowHistory(true);
}

function selectPrecisionWorkflowHistoryCalendarDate(key) {
  var state = precisionWorkflowHistoryCalendarState();
  state.dateFrom = key;
  state.dateTo = key;
  state.anchor = new Date((precisionCalendarDateFromKey(key) || new Date()).getFullYear(), (precisionCalendarDateFromKey(key) || new Date()).getMonth(), 1);
  state.anchorExplicit = true;
  renderPrecisionWorkflowHistoryCalendar();
  return loadPrecisionWorkflowHistory(true);
}

function clearPrecisionWorkflowHistoryDateFilter() {
  var state = precisionWorkflowHistoryCalendarState();
  state.dateFrom = '';
  state.dateTo = '';
  renderPrecisionWorkflowHistoryCalendar();
  return loadPrecisionWorkflowHistory(true);
}

function handlePrecisionWorkflowHistoryCalendarKeydown(event) {
  var calendar = document.getElementById('precisionWorkflowHistoryCalendar');
  if (!calendar) return;
  var days = Array.prototype.slice.call(calendar.querySelectorAll('button[data-workflow-date]'));
  var index = days.indexOf(document.activeElement);
  if (['Enter', ' ', 'Spacebar'].indexOf(event.key) !== -1) {
    if (index < 0) return;
    event.preventDefault();
    return selectPrecisionWorkflowHistoryCalendarDate(days[index].dataset.workflowDate);
  }
  if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].indexOf(event.key) === -1) return;
  if (index < 0) index = 0;
  if (event.key === 'Home') index = 0;
  else if (event.key === 'End') index = days.length - 1;
  else if (event.key === 'ArrowLeft') index -= 1;
  else if (event.key === 'ArrowRight') index += 1;
  else if (event.key === 'ArrowUp') index -= 7;
  else index += 7;
  event.preventDefault();
  days[Math.max(0, Math.min(days.length - 1, index))].focus();
}

function setPrecisionWorkflowHistoryFilterOpen(open, restoreFocus) {
  var trigger = document.getElementById('btnPrecisionWorkflowHistoryFilter');
  var popover = document.getElementById('precisionWorkflowHistoryFilterPopover');
  if (!trigger || !popover) return false;
  var wasOpen = !popover.hidden;
  var nextOpen = !!open;
  popover.hidden = !nextOpen;
  trigger.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  if (nextOpen) {
    precisionWorkflowHistoryState.filterOpener = trigger;
    setPrecisionWorkflowHistoryActionOpen(false);
    if (!precisionWorkflowHistoryState.loaded) loadPrecisionWorkflowHistory(true);
    renderPrecisionWorkflowHistoryCalendar();
    if (typeof popover.focus === 'function') popover.focus();
  } else if (restoreFocus && wasOpen && precisionWorkflowHistoryState.filterOpener && typeof precisionWorkflowHistoryState.filterOpener.focus === 'function') {
    precisionWorkflowHistoryState.filterOpener.focus();
  }
  return wasOpen;
}

function togglePrecisionWorkflowHistoryFilter() {
  var popover = document.getElementById('precisionWorkflowHistoryFilterPopover');
  if (!popover) return false;
  setPrecisionWorkflowHistoryFilterOpen(popover.hidden);
  return !popover.hidden;
}

function setPrecisionWorkflowHistoryActionOpen(open, restoreFocus) {
  var popover = document.getElementById('precisionWorkflowHistoryActionPopover');
  if (!popover) return false;
  var wasOpen = !popover.hidden;
  var nextOpen = !!open && !!precisionWorkflowHistoryMediaUrl(precisionWorkflowHistoryState.selectedWorkflow && precisionWorkflowHistoryState.selectedWorkflow.restore && precisionWorkflowHistoryState.selectedWorkflow.restore.image_url);
  popover.hidden = !nextOpen;
  if (nextOpen && typeof popover.focus === 'function') popover.focus();
  if (!nextOpen && restoreFocus && wasOpen && precisionWorkflowHistoryState.actionOpener && typeof precisionWorkflowHistoryState.actionOpener.focus === 'function') precisionWorkflowHistoryState.actionOpener.focus();
  return wasOpen;
}

function precisionWorkflowHistoryVersionMarkup(version, resultIndex) {
  var available = !!(version && version.available);
  var thumbnail = available ? precisionWorkflowHistoryMediaUrl(version.thumbnail) : '';
  var label = version && version.kind === 'source'
    ? i18nText('creator.precision_workflow_history_original')
    : i18nText('creator.precision_workflow_history_step', { count: resultIndex });
  return '<span class="precision-workflow-history-version' + (available && thumbnail ? '' : ' is-unavailable') + '" title="' + escAttr(label) + '">'
    + (thumbnail ? '<img src="' + escAttr(thumbnail) + '" alt="' + escAttr(label) + '" loading="lazy" draggable="false">' : '<span class="precision-workflow-history-missing" aria-hidden="true">—</span>')
    + '<small>' + escHtml(label) + '</small></span>';
}

function precisionWorkflowHistoryItemMarkup(workflow) {
  var workflowId = String(workflow && workflow.workflow_id || '');
  var versions = Array.isArray(workflow && workflow.versions) ? workflow.versions : [];
  var summary = workflow && workflow.summary || {};
  var resultIndex = 0;
  // The history card is a visual workflow: source first, then each edit in order.
  // Keep only the first source projection because an API history record has one base image.
  var orderedVersions = versions.filter(function(version) { return version && version.kind === 'source'; }).slice(0, 1)
    .concat(versions.filter(function(version) { return version && version.kind === 'result'; }));
  var versionMarkup = orderedVersions.map(function(version, index) {
    if (version && version.kind === 'result') resultIndex += 1;
    var arrow = index ? '<span class="precision-workflow-history-arrow" aria-hidden="true">→</span>' : '';
    return arrow + precisionWorkflowHistoryVersionMarkup(version, resultIndex);
  }).join('');
  var updated = String(workflow && workflow.updated_at || '').slice(0, 10);
  var count = Number(workflow && workflow.edit_count || 0);
  var latestSize = /^\d{1,5}x\d{1,5}$/.test(String(summary.latest_size || '')) ? String(summary.latest_size) : '';
  var meta = updated + (updated && count ? ' · ' : '') + i18nText('creator.precision_workflow_history_edits', { count: count }) + (latestSize ? ' · ' + latestSize : '');
  return '<div class="precision-workflow-history-item" role="listitem"><button type="button" class="precision-workflow-history-select" onclick="selectPrecisionWorkflowHistory(\'' + escAttr(workflowId) + '\',event)"><span class="precision-workflow-history-item-meta"><strong>' + escHtml(updated || i18nText('creator.precision_workflow_history_date_unknown')) + '</strong><small>' + escHtml(meta) + '</small></span><span class="precision-workflow-history-version-row">' + versionMarkup + '</span></button></div>';
}

function precisionWorkflowHistoryPosterMarkup(workflows) {
  var count = 0;
  var markup = (workflows || []).map(function(workflow) {
    var workflowId = String(workflow && workflow.workflow_id || '');
    var updated = String(workflow && workflow.updated_at || '').slice(0, 10);
    var step = 0;
    return (Array.isArray(workflow && workflow.versions) ? workflow.versions : []).map(function(version) {
      if (!version || version.kind !== 'result') return '';
      step += 1;
      var thumbnail = version.available ? precisionWorkflowHistoryMediaUrl(version.thumbnail) : '';
      if (!thumbnail) return '';
      count += 1;
      var label = (updated ? updated + ' · ' : '') + i18nText('creator.precision_workflow_history_step', { count: step });
      return '<div class="precision-session-item precision-history-poster" role="listitem"><button type="button" class="precision-session-thumb" onclick="selectPrecisionWorkflowHistory(\'' + escAttr(workflowId) + '\',event)" aria-label="' + escAttr(label) + '" title="' + escAttr(label) + '"><img src="' + escAttr(thumbnail) + '" alt="" loading="lazy" draggable="false"></button></div>';
    }).join('');
  }).join('');
  return { markup: markup, count: count };
}

function renderPrecisionWorkflowHistory() {
  var list = document.getElementById('precisionWorkflowHistoryList');
  if (!list) return;
  var items = precisionWorkflowHistoryState.items || [];
  list.innerHTML = items.length ? items.map(precisionWorkflowHistoryItemMarkup).join('') : '<p class="precision-workflow-history-empty">' + escHtml(i18nText('creator.precision_workflow_history_empty')) + '</p>';
}

function loadPrecisionWorkflowHistory(force) {
  var filters = precisionWorkflowHistoryFilters();
  if (!force && precisionWorkflowHistoryState.loading) return false;
  var request = ++precisionWorkflowHistoryState.listRequest;
  precisionWorkflowHistoryState.loading = true;
  precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_loading'));
  var query = new URLSearchParams({ limit: '100' });
  if (filters.dateFrom) query.set('date_from', filters.dateFrom);
  if (filters.dateTo) query.set('date_to', filters.dateTo);
  return _authFetch('/api/precision/workflows?' + query.toString()).then(function(response) {
    if (!response.ok) throw new Error('precision_workflow_history_load_failed');
    return response.json();
  }).then(function(data) {
    if (request !== precisionWorkflowHistoryState.listRequest) return false;
    precisionWorkflowHistoryState.items = Array.isArray(data && data.items) ? data.items : [];
    if (!filters.dateFrom && !filters.dateTo) precisionWorkflowHistoryState.calendarItems = precisionWorkflowHistoryState.items.slice();
    var calendarState = precisionWorkflowHistoryCalendarState();
    if (!calendarState.anchorExplicit) {
      var indexedDates = Object.keys(precisionWorkflowHistoryCalendarIndex()).sort();
      var latestDate = indexedDates[indexedDates.length - 1];
      var latest = precisionCalendarDateFromKey(latestDate);
      if (latest) calendarState.anchor = new Date(latest.getFullYear(), latest.getMonth(), 1);
    }
    precisionWorkflowHistoryState.loaded = true;
    precisionWorkflowHistoryState.loading = false;
    if (!precisionWorkflowHistoryState.items.some(function(item) { return item && item.workflow_id === precisionWorkflowHistoryState.selectedWorkflowId; })) {
      precisionWorkflowHistoryState.selectedWorkflow = null;
      precisionWorkflowHistoryState.selectedWorkflowId = '';
      setPrecisionWorkflowHistoryActionOpen(false);
    }
    precisionWorkflowHistoryStatus(precisionWorkflowHistoryState.items.length ? i18nText('creator.precision_workflow_history_loaded', { count: precisionWorkflowHistoryState.items.length }) : i18nText('creator.precision_workflow_history_empty'));
    renderPrecisionWorkflowHistory();
    renderPrecisionWorkflowHistoryCalendar();
    renderPrecisionSessionShowcase(precisionEditSession.source ? [precisionEditSession.source].concat(precisionEditSession.versions) : []);
    return true;
  }).catch(function() {
    if (request !== precisionWorkflowHistoryState.listRequest) return false;
    precisionWorkflowHistoryState.loading = false;
    precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_load_failed'));
    renderPrecisionWorkflowHistory();
    renderPrecisionWorkflowHistoryCalendar();
    renderPrecisionSessionShowcase(precisionEditSession.source ? [precisionEditSession.source].concat(precisionEditSession.versions) : []);
    return false;
  });
}

function selectPrecisionWorkflowHistory(workflowId, event) {
  if (event && typeof event.stopPropagation === 'function') event.stopPropagation();
  if (!/^pw_[a-f0-9]{32}$/.test(String(workflowId || ''))) return false;
  var request = ++precisionWorkflowHistoryState.detailRequest;
  precisionWorkflowHistoryState.actionOpener = event && event.currentTarget || null;
  precisionWorkflowHistoryState.selectedWorkflowId = workflowId;
  precisionWorkflowHistoryState.selectedWorkflow = null;
  setPrecisionWorkflowHistoryFilterOpen(false);
  setPrecisionWorkflowHistoryActionOpen(false);
  precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_loading'));
  renderPrecisionWorkflowHistory();
  return _authFetch('/api/precision/workflows/' + encodeURIComponent(workflowId)).then(function(response) {
    if (!response.ok) throw new Error('precision_workflow_history_detail_failed');
    return response.json();
  }).then(function(data) {
    if (request !== precisionWorkflowHistoryState.detailRequest || precisionWorkflowHistoryState.selectedWorkflowId !== workflowId) return false;
    var workflow = data && data.workflow;
    if (!workflow || workflow.workflow_id !== workflowId) throw new Error('precision_workflow_history_detail_invalid');
    precisionWorkflowHistoryState.selectedWorkflow = workflow;
    precisionWorkflowHistoryStatus('');
    renderPrecisionWorkflowHistory();
    setPrecisionWorkflowHistoryActionOpen(true);
    return true;
  }).catch(function() {
    if (request !== precisionWorkflowHistoryState.detailRequest || precisionWorkflowHistoryState.selectedWorkflowId !== workflowId) return false;
    precisionWorkflowHistoryState.selectedWorkflow = null;
    precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_load_failed'));
    renderPrecisionWorkflowHistory();
    return false;
  });
}

function viewPrecisionWorkflowHistoryImage() {
  var workflow = precisionWorkflowHistoryState.selectedWorkflow;
  var imageUrl = precisionWorkflowHistoryMediaUrl(workflow && workflow.restore && workflow.restore.image_url);
  if (!imageUrl) return false;
  setPrecisionWorkflowHistoryActionOpen(false);
  var trigger = document.getElementById('btnPrecisionWorkflowHistoryFilter');
  if (trigger && typeof trigger.focus === 'function') trigger.focus();
  return openPrecisionImageFullscreen(imageUrl, i18nText('creator.precision_workflow_history_view_image'), { promptEntries: [] });
}

function precisionWorkflowHistoryImageDataUrl(url) {
  return _authFetch(url).then(function(response) {
    if (!response.ok) throw new Error('precision_workflow_history_restore_fetch_failed');
    return response.blob();
  }).then(function(blob) {
    return new Promise(function(resolve, reject) {
      var reader = new FileReader();
      reader.onload = function() { resolve(String(reader.result || '')); };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  });
}

function precisionWorkflowHistorySnapshotObjects(snapshot, versionId) {
  if (!snapshot || !Array.isArray(snapshot.annotations)) return [];
  var fallbackColor = (typeof precisionEditStyle === 'function' && precisionEditStyle().color) || '#ef4444';
  var fallbackStroke = (typeof precisionEditStyle === 'function' && precisionEditStyle().strokeWidth) || 5;
  return snapshot.annotations.map(function(annotation, index) {
    if (!annotation || typeof annotation !== 'object') return null;
    var type = annotation.type === 'rectangle' ? 'rect' : annotation.type;
    if (['arrow', 'rect', 'ellipse', 'brush', 'text'].indexOf(type) === -1) return null;
    var label = Number(annotation.label);
    if (!Number.isInteger(label) || label <= 0) label = index + 1;
    var object = {
      id: 'workflow-' + String(versionId || 'restore') + '-' + index,
      type: type,
      label: label,
      color: fallbackColor,
      strokeWidth: fallbackStroke,
      instruction: String(annotation.instruction || '')
    };
    if (type === 'arrow') {
      object.x = Number(annotation.x1) || 0;
      object.y = Number(annotation.y1) || 0;
      object.x2 = Number(annotation.x2) || 0;
      object.y2 = Number(annotation.y2) || 0;
    } else if (type === 'rect' || type === 'ellipse') {
      object.x = Number(annotation.x) || 0;
      object.y = Number(annotation.y) || 0;
      object.x2 = object.x + (Number(annotation.width) || 0);
      object.y2 = object.y + (Number(annotation.height) || 0);
    } else if (type === 'brush') {
      object.points = Array.isArray(annotation.points) ? annotation.points.map(function(point) {
        return { x: Number(point && point.x) || 0, y: Number(point && point.y) || 0 };
      }) : [];
    } else {
      object.x = Number(annotation.x) || 0;
      object.y = Number(annotation.y) || 0;
      object.text = String(annotation.text || '');
      object.fontSize = (typeof precisionEditStyle === 'function' && precisionEditStyle().fontSize) || 24;
    }
    return object;
  }).filter(Boolean);
}

function precisionWorkflowHistoryLoadVersionData(versions) {
  var loaded = {};
  var requests = (versions || []).map(function(version) {
    var id = String(version && version.version_id || '');
    var imageUrl = precisionWorkflowHistoryMediaUrl(version && version.image_url);
    if (!id || !imageUrl) return Promise.resolve();
    return precisionWorkflowHistoryImageDataUrl(imageUrl).then(function(dataUrl) {
      if (dataUrl) loaded[id] = dataUrl;
    }).catch(function() {
      // Keep the metadata chain intact when one historical artifact is gone.
      // The selected version gets a second direct restore attempt below.
    });
  });
  return Promise.all(requests).then(function() { return loaded; });
}

function precisionWorkflowHistoryEnsureVersionData(versions, imageData, ids) {
  var wanted = (ids || []).map(String).filter(function(id) { return id && !imageData[id]; });
  return Promise.all(wanted.map(function(id) {
    var version = (versions || []).find(function(candidate) { return String(candidate && candidate.version_id || '') === id; });
    var imageUrl = precisionWorkflowHistoryMediaUrl(version && version.image_url);
    if (!imageUrl) return Promise.resolve();
    return precisionWorkflowHistoryImageDataUrl(imageUrl).then(function(dataUrl) {
      if (dataUrl) imageData[id] = dataUrl;
    });
  })).then(function() { return imageData; });
}

function precisionWorkflowHistoryRestoredSession(workflow, imageData) {
  var versions = Array.isArray(workflow && workflow.versions) ? workflow.versions : [];
  var sourceVersion = versions.find(function(version) { return version && version.version_id === 'original'; });
  if (!sourceVersion || !imageData || !imageData.original) return null;
  var session = {
    source: {
      id: 'original', label: i18nText('creator.precision_original'), data: imageData.original,
      createdAt: String(sourceVersion.createdAt || sourceVersion.created_at || ''),
      width: sourceVersion.width, height: sourceVersion.height
    },
    versions: [], selectedVersionId: 'original', baseVersionId: 'original',
    taskBaseVersionId: null, view: 'after', taskId: null,
    sourceGeneration: precisionSourceLoadGeneration
  };
  versions.forEach(function(version, index) {
    if (!version || version.version_id === 'original') return;
    session.versions.push({
      id: version.version_id,
      label: String(session.versions.length + 1),
      data: imageData[version.version_id] || '',
      parentId: imageData[version.parent_version_id] ? version.parent_version_id : 'original',
      createdAt: String(version.createdAt || version.created_at || ''),
      width: version.width, height: version.height,
      annotationSnapshot: version.annotation_snapshot || null,
      workflowIndex: index
    });
  });
  session.annotationSnapshots = {};
  session.versions.forEach(function(version) {
    if (version.annotationSnapshot) session.annotationSnapshots[version.id] = version.annotationSnapshot;
  });
  return session;
}

function applyPrecisionWorkflowVersionAnnotations(versionId) {
  var snapshot = precisionEditSession && precisionEditSession.annotationSnapshots && precisionEditSession.annotationSnapshots[versionId];
  if (!snapshot) return false;
  precisionEditObjects = precisionWorkflowHistorySnapshotObjects(snapshot, versionId);
  precisionEditLabelCounter = precisionEditObjects.reduce(function(maximum, object) { return Math.max(maximum, Number(object.label) || 0); }, 0);
  precisionEditSelectedId = precisionEditObjects.length ? precisionEditObjects[0].id : null;
  precisionAnnotationInstructionPopoverState.confirmedIds = {};
  precisionAnnotationInstructionPopoverState.dismissedIds = {};
  precisionEditObjects.forEach(function(object) { precisionAnnotationInstructionPopoverState.confirmedIds[object.id] = true; });
  if (typeof setPrecisionEditStrategy === 'function') setPrecisionEditStrategy(snapshot.precision_strategy || 'standard');
  precisionSelectionFeather = Math.max(0, Math.min(64, Math.round(Number(snapshot.precision_selection_feather) || 0)));
  var featherInput = document.getElementById('precisionSelectionFeather');
  if (featherInput) featherInput.value = String(precisionSelectionFeather);
  if (typeof setPrecisionEditSelectionMode === 'function') setPrecisionEditSelectionMode(snapshot.precision_selection_mode || 'annotation');
  return true;
}

function restorePrecisionWorkflowHistory() {
  var workflow = precisionWorkflowHistoryState.selectedWorkflow;
  var restore = workflow && workflow.restore;
  var restoredVersionId = String(restore && restore.version_id || '');
  var versions = Array.isArray(workflow && workflow.versions) ? workflow.versions : [];
  if (!restoredVersionId || !versions.length || !preparePrecisionSourceReplacement()) return false;
  setPrecisionWorkflowHistoryActionOpen(false);
  var generation = ++precisionSourceLoadGeneration;
  precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_restoring'));
  return precisionWorkflowHistoryLoadVersionData(versions).then(function(imageData) {
    if (generation !== precisionSourceLoadGeneration) return false;
    var baseVersionId = String(restore && restore.base_version_id || 'original');
    return precisionWorkflowHistoryEnsureVersionData(versions, imageData, ['original', baseVersionId, restoredVersionId]).then(function() {
      if (generation !== precisionSourceLoadGeneration) return false;
    var session = precisionWorkflowHistoryRestoredSession(workflow, imageData);
    var selected = session && precisionEditSessionEntry([session.source].concat(session.versions), restoredVersionId, null);
    if (!session || !selected) throw new Error('precision_workflow_history_restore_incomplete');
    baseVersionId = String(restore && restore.base_version_id || selected.parentId || 'original');
    var base = precisionEditSessionEntry([session.source].concat(session.versions), baseVersionId, session.source);
    var snapshot = (restore && restore.annotation_snapshot) || selected.annotationSnapshot || null;
    var restoredObjects = precisionWorkflowHistorySnapshotObjects(snapshot, restoredVersionId);
    resetPrecisionSourceSpecificState(generation);
    session.selectedVersionId = selected.id;
    session.baseVersionId = base.id;
    session.view = selected.id === base.id ? 'after' : 'compare';
    session.sourceGeneration = generation;
    precisionEditSession = session;
    setCreatorWorkbenchMode('image', 'precision');
    loadPrecisionEditSourceImage(base.data, '', { generation: generation, preserveSession: true, onLoaded: function() {
      if (generation !== precisionSourceLoadGeneration) return;
      precisionEditObjects = restoredObjects;
      precisionEditHistory = [];
      precisionEditRedo = [];
      precisionEditLabelCounter = restoredObjects.reduce(function(maximum, object) { return Math.max(maximum, Number(object.label) || 0); }, 0);
      precisionEditSelectedId = restoredObjects.length ? restoredObjects[0].id : null;
      precisionAnnotationInstructionPopoverState.confirmedIds = {};
      precisionAnnotationInstructionPopoverState.dismissedIds = {};
      restoredObjects.forEach(function(object) { precisionAnnotationInstructionPopoverState.confirmedIds[object.id] = true; });
      if (snapshot) {
        if (typeof setPrecisionEditStrategy === 'function') setPrecisionEditStrategy(snapshot.precision_strategy || 'standard');
        precisionSelectionFeather = Math.max(0, Math.min(64, Math.round(Number(snapshot.precision_selection_feather) || 0)));
        var featherInput = document.getElementById('precisionSelectionFeather');
        if (featherInput) featherInput.value = String(precisionSelectionFeather);
        if (typeof setPrecisionEditSelectionMode === 'function') setPrecisionEditSelectionMode(snapshot.precision_selection_mode || 'annotation');
      }
      renderPrecisionEditCanvas();
      updatePrecisionEditControls();
      renderPrecisionEditSession();
      precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_restored'));
    }, onError: function() {
      precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_load_failed'));
    }});
    return true;
    });
  }).catch(function() {
    if (generation === precisionSourceLoadGeneration) precisionWorkflowHistoryStatus(i18nText('creator.precision_workflow_history_load_failed'));
    return false;
  });
}

function precisionCalendarDateKey(date) {
  var y = date.getFullYear();
  var m = String(date.getMonth() + 1).padStart(2, '0');
  var d = String(date.getDate()).padStart(2, '0');
  return y + '-' + m + '-' + d;
}

function precisionCalendarDateFromKey(key) {
  var parts = String(key || '').split('-').map(Number);
  return parts.length === 3 && parts.every(Number.isFinite) ? new Date(parts[0], parts[1] - 1, parts[2]) : null;
}

function precisionCalendarDateIndex() {
  var index = {};
  (window.precisionSessionCalendarEntries || []).forEach(function(entry) {
    var time = precisionSessionEntryTime(entry);
    if (!Number.isFinite(time)) return;
    var key = precisionCalendarDateKey(new Date(time));
    index[key] = (index[key] || 0) + 1;
  });
  return index;
}

function renderPrecisionSessionCalendar() {
  var calendar = document.getElementById('precisionSessionCalendar');
  var label = document.getElementById('precisionSessionCalendarLabel');
  if (!calendar || !label) return;
  var state = window.precisionSessionCalendarState || (window.precisionSessionCalendarState = { anchor: new Date(), start: '', end: '' });
  var anchor = new Date(state.anchor.getFullYear(), state.anchor.getMonth(), 1);
  state.anchor = anchor;
  label.textContent = anchor.getFullYear() + '年' + (anchor.getMonth() + 1) + '月';
  var firstDay = new Date(anchor.getFullYear(), anchor.getMonth(), 1).getDay();
  var days = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0).getDate();
  var index = precisionCalendarDateIndex();
  var today = precisionCalendarDateKey(new Date());
  var html = ['<span class="precision-session-calendar-weekday">日</span><span class="precision-session-calendar-weekday">一</span><span class="precision-session-calendar-weekday">二</span><span class="precision-session-calendar-weekday">三</span><span class="precision-session-calendar-weekday">四</span><span class="precision-session-calendar-weekday">五</span><span class="precision-session-calendar-weekday">六</span>'];
  for (var i = 0; i < firstDay; i += 1) html.push('<span class="precision-session-calendar-day is-placeholder" aria-hidden="true"></span>');
  for (var day = 1; day <= days; day += 1) {
    var date = new Date(anchor.getFullYear(), anchor.getMonth(), day);
    var key = precisionCalendarDateKey(date);
    var has = !!index[key];
    var selected = state.start && key >= state.start && (!state.end || key <= state.end);
    var classes = 'precision-session-calendar-day' + (has ? ' has-results' : ' is-empty') + (selected ? ' selected' : '') + (key === today ? ' today' : '');
    html.push('<button type="button" class="' + classes + '" data-date="' + key + '" aria-label="' + key + (has ? '，' + index[key] + ' 个结果' : '，无结果') + '" aria-pressed="' + (selected ? 'true' : 'false') + '" onclick="selectPrecisionSessionCalendarDate(\'' + key + '\')"><span>' + day + '</span>' + (has ? '<small>' + index[key] + '</small>' : '') + '</button>');
  }
  calendar.innerHTML = html.join('');
}

function updatePrecisionSessionDateSummary() {
  var summary = document.getElementById('precisionSessionDateSummary');
  var from = document.getElementById('precisionSessionDateFrom');
  var to = document.getElementById('precisionSessionDateTo');
  if (!summary) return;
  if (!from || !to || (!from.value && !to.value)) summary.textContent = '日期筛选';
  else if (from.value && to.value && from.value !== to.value) summary.textContent = from.value + ' 至 ' + to.value;
  else summary.textContent = from && from.value ? from.value : to.value;
}

function togglePrecisionSessionDatePopover(force, restoreFocus) {
  var popover = document.getElementById('precisionSessionDatePopover');
  var trigger = document.getElementById('precisionSessionDateToggle');
  if (!popover || !trigger) return false;
  var wasOpen = !popover.hidden;
  var open = typeof force === 'boolean' ? force : popover.hidden;
  popover.hidden = !open;
  trigger.setAttribute('aria-expanded', String(open));
  if (open) {
    if (!window.precisionSessionCalendarState) window.precisionSessionCalendarState = { anchor: new Date(), start: '', end: '' };
    renderPrecisionSessionCalendar();
  }
  if (!open && restoreFocus && wasOpen && typeof trigger.focus === 'function') trigger.focus();
  return wasOpen;
}

function shiftPrecisionSessionCalendar(offset) {
  var state = window.precisionSessionCalendarState || (window.precisionSessionCalendarState = { anchor: new Date(), start: '', end: '' });
  state.anchor = new Date(state.anchor.getFullYear(), state.anchor.getMonth() + Number(offset || 0), 1);
  renderPrecisionSessionCalendar();
  focusPrecisionSessionCalendarMonthButton(offset);
}

function setPrecisionSessionDateRange(range) {
  var end = new Date();
  var start = new Date(end);
  if (range === '3d' || range === '5d') start.setDate(start.getDate() - (range === '3d' ? 2 : 4));
  else if (range === 'week') { start.setDate(end.getDate() - end.getDay()); }
  else if (range === 'month') { start = new Date(end.getFullYear(), end.getMonth(), 1); }
  else if (range === 'quarter') { start = new Date(end.getFullYear(), Math.floor(end.getMonth() / 3) * 3, 1); }
  else if (range === 'half-year') { start = new Date(end.getFullYear(), end.getMonth() < 6 ? 0 : 6, 1); }
  else if (range === 'year') { start = new Date(end.getFullYear(), 0, 1); }
  else return;
  var from = document.getElementById('precisionSessionDateFrom');
  var to = document.getElementById('precisionSessionDateTo');
  if (from) from.value = precisionCalendarDateKey(start);
  if (to) to.value = precisionCalendarDateKey(end);
  var state = window.precisionSessionCalendarState || (window.precisionSessionCalendarState = { anchor: new Date(), start: '', end: '' });
  state.start = from ? from.value : '';
  state.end = to ? to.value : '';
  applyPrecisionSessionDateFilter();
  updatePrecisionSessionDateSummary();
  renderPrecisionSessionCalendar();
}

function selectPrecisionSessionCalendarDate(key) {
  var state = window.precisionSessionCalendarState || (window.precisionSessionCalendarState = { anchor: new Date(), start: '', end: '' });
  if (!state.start || state.end) { state.start = key; state.end = ''; }
  else if (key < state.start) { state.end = state.start; state.start = key; }
  else state.end = key;
  var from = document.getElementById('precisionSessionDateFrom');
  var to = document.getElementById('precisionSessionDateTo');
  if (from) from.value = state.start;
  if (to) to.value = state.end;
  applyPrecisionSessionDateFilter();
  updatePrecisionSessionDateSummary();
  renderPrecisionSessionCalendar();
  focusPrecisionSessionCalendarDate(key);
}

function precisionSessionEntryTime(entry) {
  if (!entry) return NaN;
  var raw = entry.createdAt || entry.created_at || entry.timestamp || entry.created || '';
  var time = Date.parse(raw);
  return Number.isFinite(time) ? time : NaN;
}

function filterPrecisionSessionEntries(entries) {
  var fromInput = document.getElementById('precisionSessionDateFrom');
  var toInput = document.getElementById('precisionSessionDateTo');
  var fromValue = fromInput ? fromInput.value : '';
  var toValue = toInput ? toInput.value : '';
  if (!fromValue && !toValue) return entries;
  var fromTime = fromValue ? Date.parse(fromValue + 'T00:00:00') : -Infinity;
  var toTime = toValue ? Date.parse(toValue + 'T23:59:59.999') : Infinity;
  if (Number.isFinite(fromTime) && Number.isFinite(toTime) && fromTime > toTime) return [];
  return entries.filter(function(entry) {
    var time = precisionSessionEntryTime(entry);
    return Number.isFinite(time) && time >= fromTime && time <= toTime;
  });
}

function applyPrecisionSessionDateFilter() {
  var state = window.precisionSessionCalendarState || (window.precisionSessionCalendarState = { anchor: new Date(), start: '', end: '' });
  var from = document.getElementById('precisionSessionDateFrom');
  var to = document.getElementById('precisionSessionDateTo');
  state.start = from ? from.value : '';
  state.end = to ? to.value : '';
  updatePrecisionSessionDateSummary();
  renderPrecisionEditSession();
}

function clearPrecisionSessionDateFilter() {
  var fromInput = document.getElementById('precisionSessionDateFrom');
  var toInput = document.getElementById('precisionSessionDateTo');
  if (fromInput) fromInput.value = '';
  if (toInput) toInput.value = '';
  var state = window.precisionSessionCalendarState || (window.precisionSessionCalendarState = { anchor: new Date(), start: '', end: '' });
  state.start = '';
  state.end = '';
  renderPrecisionEditSession();
  updatePrecisionSessionDateSummary();
}

function focusPrecisionSessionCalendarDate(key) {
  var calendar = document.getElementById('precisionSessionCalendar');
  if (!calendar) return false;
  var days = Array.prototype.slice.call(calendar.querySelectorAll('button[data-date]'));
  var day = days.find(function(button) {
    return (button.dataset && button.dataset.date) === key || (button.getAttribute && button.getAttribute('data-date') === key);
  });
  if (!day || typeof day.focus !== 'function') return false;
  day.focus();
  return true;
}

function focusPrecisionSessionCalendarMonthButton(offset) {
  var toolbar = document.querySelector('.precision-session-calendar-toolbar');
  if (!toolbar) return false;
  var buttons = Array.prototype.slice.call(toolbar.querySelectorAll('button'));
  var button = buttons[Number(offset) < 0 ? 0 : buttons.length - 1];
  if (!button || typeof button.focus !== 'function') return false;
  button.focus();
  return true;
}

function handlePrecisionSessionCalendarKeydown(event) {
  var calendar = document.getElementById('precisionSessionCalendar');
  if (!calendar) return;
  var days = Array.prototype.slice.call(calendar.querySelectorAll('button[data-date]'));
  if (!days.length) return;
  var index = days.indexOf(document.activeElement);
  if (['Enter', ' ', 'Spacebar'].indexOf(event.key) !== -1) {
    if (index < 0) return;
    var key = (days[index].dataset && days[index].dataset.date) || (days[index].getAttribute && days[index].getAttribute('data-date'));
    if (!key) return;
    event.preventDefault();
    selectPrecisionSessionCalendarDate(key);
    return;
  }
  if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].indexOf(event.key) === -1) return;
  if (index < 0) index = 0;
  if (event.key === 'Home') index = 0;
  else if (event.key === 'End') index = days.length - 1;
  else if (event.key === 'ArrowLeft') index -= 1;
  else if (event.key === 'ArrowRight') index += 1;
  else if (event.key === 'ArrowUp') index -= 7;
  else index += 7;
  index = Math.max(0, Math.min(days.length - 1, index));
  event.preventDefault();
  days[index].focus();
}

document.addEventListener('click', function(event) {
  var wrap = document.querySelector('.precision-session-date-filter');
  if (wrap && !wrap.contains(event.target)) togglePrecisionSessionDatePopover(false);
  var sourceActions = document.getElementById('precisionSourceActions');
  if (sourceActions && !sourceActions.contains(event.target)) setPrecisionSourceMenuOpen(false);
  var historyFilters = document.querySelector('.precision-workflow-history-filters');
  var eventPath = typeof event.composedPath === 'function' ? event.composedPath() : [];
  var eventInsideHistoryFilters = historyFilters && (historyFilters.contains(event.target) || eventPath.indexOf(historyFilters) !== -1);
  if (historyFilters && !eventInsideHistoryFilters) {
    setPrecisionWorkflowHistoryFilterOpen(false);
    setPrecisionWorkflowHistoryActionOpen(false);
  }
});
document.addEventListener('keydown', function(event) {
  if (event.key !== 'Escape') return;
  var sourceMenu = document.getElementById('precisionSourceMenu');
  if (sourceMenu && !sourceMenu.hidden) {
    event.preventDefault();
    setPrecisionSourceMenuOpen(false, true);
    return;
  }
  var historyAction = document.getElementById('precisionWorkflowHistoryActionPopover');
  if (historyAction && !historyAction.hidden) {
    event.preventDefault();
    setPrecisionWorkflowHistoryActionOpen(false, true);
    return;
  }
  var historyFilter = document.getElementById('precisionWorkflowHistoryFilterPopover');
  if (historyFilter && !historyFilter.hidden) {
    event.preventDefault();
    setPrecisionWorkflowHistoryFilterOpen(false, true);
    return;
  }
  var datePopover = document.getElementById('precisionSessionDatePopover');
  if (datePopover && !datePopover.hidden) {
    event.preventDefault();
    togglePrecisionSessionDatePopover(false, true);
    return;
  }
  var showcase = document.getElementById('precisionSessionShowcase');
  if (showcase && showcase.classList.contains('is-expanded')) {
    event.preventDefault();
    setPrecisionSessionShowcaseOpen(false, true);
  }
});

function precisionVersionRailReducedMotion() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function focusPrecisionVersionRailEntry(id) {
  var rail = document.getElementById('precisionVersionRail');
  if (!rail) return false;
  var buttons = Array.prototype.slice.call(rail.querySelectorAll('[data-precision-version-id]'));
  var button = buttons.find(function(candidate) { return candidate.getAttribute('data-precision-version-id') === id; });
  if (!button || button.disabled) return false;
  button.focus({ preventScroll: true });
  if (typeof button.scrollIntoView === 'function') button.scrollIntoView({ behavior: precisionVersionRailReducedMotion() ? 'auto' : 'smooth', block: 'nearest', inline: 'nearest' });
  return true;
}

function handlePrecisionVersionRailKeydown(event) {
  if (!event || ['ArrowLeft', 'ArrowRight', 'Home', 'End'].indexOf(event.key) === -1) return;
  var rail = document.getElementById('precisionVersionRail');
  if (!rail) return;
  var buttons = Array.prototype.slice.call(rail.querySelectorAll('[data-precision-version-id]:not(:disabled)'));
  var currentIndex = buttons.indexOf(event.currentTarget);
  if (currentIndex === -1 || !buttons.length) return;
  var nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
  var nextId = buttons[nextIndex].getAttribute('data-precision-version-id');
  event.preventDefault();
  selectPrecisionVersion(nextId, { focusRail: true });
}

function selectPrecisionVersion(id, options) {
  if (typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending) return false;
  var entries = [precisionEditSession.source].concat(precisionEditSession.versions);
  if (!entries.some(function(entry) { return entry.id === id; })) return;
  precisionEditSession.selectedVersionId = id;
  precisionEditSession.view = 'after';
  if (precisionEditSession.annotationSnapshots && applyPrecisionWorkflowVersionAnnotations(id)) {
    precisionEditHistory = [];
    precisionEditRedo = [];
  }
  renderPrecisionEditSession();
  if (id === 'original' && precisionCutoutHasSource() && !precisionCutoutUiBusy()) updatePrecisionCutoutAvailability();
  if (options && options.focusRail) focusPrecisionVersionRailEntry(id);
}

function useSelectedPrecisionVersionAsBase() {
  return setPrecisionBaseVersion(precisionEditSession.selectedVersionId);
}

function setPrecisionVersionView(view) {
  if (['before', 'after', 'compare'].indexOf(view) === -1) return;
  precisionEditSession.view = view;
  renderPrecisionEditSession();
}

function updatePrecisionCompareSlider(value) {
  var wrap = document.getElementById('precisionCompareAfterWrap');
  var slider = document.getElementById('precisionCompareSlider');
  var stage = document.getElementById('precisionCompareStage');
  var after = document.getElementById('precisionCompareAfter');
  var amount = Math.max(0, Math.min(100, Number(value) || 0));
  if (slider && String(slider.value) !== String(amount)) slider.value = String(amount);
  if (wrap) wrap.style.width = amount + '%';
  if (stage) stage.setAttribute('aria-valuenow', String(amount));
  if (stage && after && stage.getBoundingClientRect) {
    var width = stage.getBoundingClientRect().width;
    if (width) after.style.width = width + 'px';
  }
}

function togglePrecisionCompareFullscreen() {
  var panel = document.getElementById('panelPrecisionEdit');
  if (!panel) return false;
  if (document.fullscreenElement === panel) {
    if (typeof document.exitFullscreen === 'function') document.exitFullscreen();
    return true;
  }
  if (document.fullscreenElement && typeof document.exitFullscreen === 'function') {
    var exitResult = document.exitFullscreen();
    if (exitResult && typeof exitResult.then === 'function') {
      exitResult.then(function() { if (panel.requestFullscreen) panel.requestFullscreen(); }).catch(function() {});
      return true;
    }
  }
  if (!panel.requestFullscreen) return false;
  var request = panel.requestFullscreen();
  var button = document.getElementById('btnPrecisionFullscreen');
  // Reflect the requested state immediately; a rejected request is corrected
  // by the settled promise or the browser fullscreenchange event.
  if (button) button.setAttribute('aria-pressed', 'true');
  if (request && typeof request.then === 'function') request.then(syncPrecisionFullscreenState, syncPrecisionFullscreenState);
  else window.setTimeout(syncPrecisionFullscreenState, 0);
  return true;
}

function handlePrecisionFullscreenKeydown(event) {
  if (!event || event.key !== 'Escape' || event.defaultPrevented) return false;
  var panel = document.getElementById('panelPrecisionEdit');
  if (!panel || document.fullscreenElement !== panel || typeof document.exitFullscreen !== 'function') return false;
  event.preventDefault();
  document.exitFullscreen();
  return true;
}

function syncPrecisionFullscreenState() {
  var panel = document.getElementById('panelPrecisionEdit');
  var button = document.getElementById('btnPrecisionFullscreen');
  if (!button) return false;
  var active = !!(panel && document.fullscreenElement === panel);
  var verticalHandle = document.getElementById('precisionCanvasVerticalResizeHandle');
  var stage = document.querySelector('#panelPrecisionEdit .precision-edit-stage-column');
  if (verticalHandle) {
    verticalHandle.hidden = !active;
    verticalHandle.setAttribute('aria-hidden', active ? 'false' : 'true');
    verticalHandle.tabIndex = active ? 0 : -1;
  }
  if (stage) stage.classList.toggle('is-canvas-vertical-resizable', active && !!verticalHandle);
  if (!active) {
    if (precisionCanvasVerticalResizeState) endPrecisionCanvasVerticalResize();
    clearPrecisionCanvasVerticalSize();
  }
  var labelKey = active ? 'creator.precision_exit_fullscreen_label' : 'creator.precision_fullscreen_label';
  var tooltipKey = active ? 'creator.precision_exit_fullscreen_tooltip' : 'creator.precision_fullscreen_tooltip';
  button.setAttribute('aria-pressed', active ? 'true' : 'false');
  button.setAttribute('aria-label', i18nText(labelKey));
  button.setAttribute('title', i18nText(tooltipKey));
  button.dataset.i18nAriaLabel = labelKey;
  button.dataset.i18nTitle = tooltipKey;
  var label = button.querySelector('[data-i18n]');
  if (label) {
    label.dataset.i18n = active ? 'creator.precision_exit_fullscreen_label' : 'creator.precision_fullscreen';
    label.textContent = i18nText(label.dataset.i18n);
  }
  return active;
}

function syncPrecisionResizeInputsToSource() {
  var width = document.getElementById('precisionResizeWidth');
  var height = document.getElementById('precisionResizeHeight');
  var preset = document.getElementById('precisionResizePreset');
  if (width && precisionEditSourceWidth) width.value = String(precisionEditSourceWidth);
  if (height && precisionEditSourceHeight) height.value = String(precisionEditSourceHeight);
  if (preset) preset.value = 'custom';
  if (typeof syncPrecisionResizeTierRatioFromSize === 'function') {
    syncPrecisionResizeTierRatioFromSize(precisionEditSourceWidth && precisionEditSourceHeight
      ? precisionEditSourceWidth + 'x' + precisionEditSourceHeight : '');
  }
  updatePrecisionResizePresetControls();
  syncPrecisionAspectRatioHint();
}

function precisionSelectionFeatherValue() {
  var input = document.getElementById('precisionSelectionFeather');
  var value = input ? Number(input.value) : Number(typeof precisionSelectionFeather === 'number' ? precisionSelectionFeather : 0);
  if (!Number.isFinite(value)) value = 0;
  return Math.max(0, Math.min(64, Math.round(value)));
}

function precisionEditStrategyValue() {
  return typeof precisionEditStrategy === 'string' && ['fine', 'standard', 'fast'].indexOf(precisionEditStrategy) !== -1
    ? precisionEditStrategy : 'standard';
}

function precisionEditSelectionModeValue() {
  return typeof precisionEditSelectionMode === 'string' && precisionEditSelectionMode === 'local'
    ? 'local' : 'annotation';
}

function updatePrecisionGuidanceSummary() {
  var status = document.getElementById('precisionGuidanceStatus');
  if (!status) return '';
  var strategyButtons = {
    fine: document.getElementById('btnPrecisionStrategyFine'),
    standard: document.getElementById('btnPrecisionStrategyStandard'),
    fast: document.getElementById('btnPrecisionStrategyFast')
  };
  var selectionButtons = {
    annotation: document.getElementById('btnPrecisionSelectionAnnotation'),
    local: document.getElementById('btnPrecisionSelectionLocal')
  };
  var strategy = strategyButtons[precisionEditStrategyValue()];
  var selection = selectionButtons[precisionEditSelectionModeValue()];
  var summary = [strategy, selection].map(function(button) {
    return button ? button.textContent.trim() : '';
  }).filter(Boolean).join(' · ');
  status.textContent = summary;
  return summary;
}

function precisionGuidanceReducedMotion() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function setPrecisionGuidanceExpanded(expanded, options) {
  var card = document.getElementById('precisionGuidanceCard');
  var toggle = document.getElementById('btnPrecisionGuidanceToggle');
  var body = document.getElementById('precisionGuidanceBody');
  if (!card || !toggle || !body) return false;
  var shouldExpand = expanded === true;
  var reducedMotion = precisionGuidanceReducedMotion();
  if (precisionGuidanceTransitionTimer) {
    clearTimeout(precisionGuidanceTransitionTimer);
    precisionGuidanceTransitionTimer = null;
  }
  updatePrecisionGuidanceSummary();
  toggle.setAttribute('aria-expanded', shouldExpand ? 'true' : 'false');
  body.setAttribute('aria-hidden', shouldExpand ? 'false' : 'true');
  if (shouldExpand) {
    body.hidden = false;
    if (reducedMotion) {
      card.dataset.state = 'expanded';
    } else {
      card.dataset.state = 'collapsed';
      body.getBoundingClientRect();
      card.dataset.state = 'expanding';
    }
  } else {
    card.dataset.state = reducedMotion ? 'collapsed' : 'collapsing';
    if (options && options.restoreFocus && typeof toggle.focus === 'function') toggle.focus();
  }
  if (reducedMotion) {
    if (!shouldExpand) body.hidden = true;
    return shouldExpand;
  }
  precisionGuidanceTransitionTimer = setTimeout(function() {
    card.dataset.state = shouldExpand ? 'expanded' : 'collapsed';
    if (!shouldExpand) body.hidden = true;
    precisionGuidanceTransitionTimer = null;
  }, 420);
  return shouldExpand;
}

function togglePrecisionGuidance() {
  var toggle = document.getElementById('btnPrecisionGuidanceToggle');
  var expanded = !!toggle && toggle.getAttribute('aria-expanded') === 'true';
  return setPrecisionGuidanceExpanded(!expanded);
}

function handlePrecisionGuidanceKeydown(event) {
  if (!event || event.key !== 'Escape') return;
  var card = document.getElementById('precisionGuidanceCard');
  var toggle = document.getElementById('btnPrecisionGuidanceToggle');
  if (!card || !toggle || toggle.getAttribute('aria-expanded') !== 'true' || !card.contains(event.target)) return;
  event.preventDefault();
  event.stopPropagation();
  setPrecisionGuidanceExpanded(false, { restoreFocus: true });
}

function setPrecisionEditStrategy(strategy) {
  precisionEditStrategy = ['fine', 'standard', 'fast'].indexOf(strategy) !== -1 ? strategy : 'standard';
  [
    ['fine', 'btnPrecisionStrategyFine'],
    ['standard', 'btnPrecisionStrategyStandard'],
    ['fast', 'btnPrecisionStrategyFast']
  ].forEach(function(pair) {
    var button = document.getElementById(pair[1]);
    if (!button) return;
    var active = precisionEditStrategy === pair[0];
    button.classList.toggle('btn-secondary', active);
    button.classList.toggle('btn-ghost', !active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  updatePrecisionGuidanceSummary();
  updatePrecisionEditControls();
  return precisionEditStrategy;
}

function setPrecisionEditSelectionMode(mode) {
  precisionEditSelectionMode = mode === 'local' ? 'local' : 'annotation';
  [
    ['annotation', 'btnPrecisionSelectionAnnotation'],
    ['local', 'btnPrecisionSelectionLocal']
  ].forEach(function(pair) {
    var button = document.getElementById(pair[1]);
    if (!button) return;
    var active = precisionEditSelectionMode === pair[0];
    button.classList.toggle('btn-secondary', active);
    button.classList.toggle('btn-ghost', !active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  var control = document.getElementById('precisionSelectionFeatherControl');
  var input = document.getElementById('precisionSelectionFeather');
  var active = precisionEditSelectionMode === 'local';
  if (control) control.classList.toggle('hidden', !active);
  if (input) {
    input.disabled = !active;
    input.value = String(precisionSelectionFeatherValue());
  }
  var output = document.getElementById('precisionSelectionFeatherValue');
  if (output) output.textContent = String(precisionSelectionFeatherValue());
  var modeHint = document.getElementById('precisionSelectionModeHint');
  if (modeHint) modeHint.textContent = i18nText(active ? 'creator.precision_selection_local_hint' : 'creator.precision_selection_annotation_hint');
  updatePrecisionGuidanceSummary();
  updatePrecisionEditControls();
  return precisionEditSelectionMode;
}

function updatePrecisionSelectionFeather() {
  precisionSelectionFeather = precisionSelectionFeatherValue();
  var output = document.getElementById('precisionSelectionFeatherValue');
  if (output) output.textContent = String(precisionSelectionFeather);
  updatePrecisionEditControls();
}

function setPrecisionSizeMode(mode) {
  precisionEditSizeMode = mode === 'resize' ? 'resize' : 'preserve';
  var preserve = document.getElementById('btnPrecisionSizePreserve');
  var resize = document.getElementById('btnPrecisionSizeResize');
  var fields = document.getElementById('precisionResizeFields');
  var hint = document.getElementById('precisionSizeHint');
  [preserve, resize].forEach(function(button) {
    if (!button) return;
    var active = (button === resize) === (precisionEditSizeMode === 'resize');
    button.classList.toggle('btn-secondary', active);
    button.classList.toggle('btn-ghost', !active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  if (fields) fields.classList.toggle('hidden', precisionEditSizeMode !== 'resize');
  if (precisionEditSizeMode === 'resize') syncPrecisionOutputSizePolicyControls();
  if (hint) hint.textContent = i18nText(precisionEditSizeMode === 'resize' ? 'creator.precision_size_resize_active_hint' : 'creator.precision_size_preserve_hint');
  if (precisionEditSizeMode === 'preserve') syncPrecisionResizeInputsToSource();
  syncPrecisionAspectRatioHint();
  updatePrecisionEditControls();
}

function applyPrecisionResizePreset(value) {
  var select = document.getElementById('precisionResizePreset');
  var option = null;
  if (select) {
    option = Array.prototype.find.call(select.options || [], function(candidate) {
      return candidate.value === value && !candidate.hidden;
    }) || Array.prototype.find.call(select.options || [], function(candidate) { return candidate.value === value; }) || null;
  }
  var size = precisionResizePresetSize(value, option);
  if (!size) return;
  var parts = size.split('x');
  var width = document.getElementById('precisionResizeWidth');
  var height = document.getElementById('precisionResizeHeight');
  if (width) width.value = parts[0];
  if (height) height.value = parts[1];
  if (typeof syncPrecisionResizeTierRatioFromSize === 'function') syncPrecisionResizeTierRatioFromSize(size);
  syncPrecisionAspectRatioHint();
  updatePrecisionEditControls();
}

function applyPrecisionResizePromptPreset(key) {
  var select = document.getElementById('precisionResizePromptPreset');
  var textarea = document.getElementById('precisionResizePrompt');
  if (!key || !textarea) return false;
  var preset = i18nText(key);
  if (!preset || preset === key) {
    if (select) select.value = '';
    return false;
  }
  if (textarea.maxLength > 0 && preset.length > textarea.maxLength) {
    textarea.setCustomValidity(i18nText('creator.precision_size_prompt_preset_too_long'));
    if (typeof textarea.reportValidity === 'function') textarea.reportValidity();
    if (select) select.value = '';
    return false;
  }
  textarea.setCustomValidity('');
  textarea.value = preset;
  if (typeof textarea.dispatchEvent === 'function' && typeof Event === 'function') {
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }
  if (typeof textarea.focus === 'function') textarea.focus();
  if (select) select.value = '';
  updatePrecisionEditControls();
  return true;
}

function markPrecisionResizeCustom() {
  if (getPrecisionOutputSizePolicy() !== 'fit_crop') {
    updatePrecisionResizeCapabilityUI();
    return;
  }
  var preset = document.getElementById('precisionResizePreset');
  var tier = document.getElementById('precisionResizeTier');
  var ratio = document.getElementById('precisionResizeRatio');
  if (preset) preset.value = 'custom';
  if (tier) tier.value = 'custom';
  if (ratio) ratio.value = 'custom';
  updatePrecisionResizePresetControls();
  syncPrecisionAspectRatioHint();
  updatePrecisionEditControls();
}

function getPrecisionSizeRequest() {
  if (precisionEditSizeMode !== 'resize') return { mode: 'preserve' };
  syncPrecisionAspectRatioHint();
  var width = precisionResizeInputDimension('precisionResizeWidth');
  var height = precisionResizeInputDimension('precisionResizeHeight');
  var targetSize = precisionResizeDimensionKey(width, height);
  if (!targetSize) {
    return { error: i18nText('creator.precision_size_invalid') };
  }
  var resizePrompt = (document.getElementById('precisionResizePrompt') || { value: '' }).value.trim();
  // Pure resize/outpaint must remain usable when the user has already picked a
  // target size but has no special composition request. Keep the field empty
  // for an uncluttered UI, while sending the same safe baseline as the first
  // composition preset.
  if (!resizePrompt) resizePrompt = i18nText('creator.precision_size_prompt_preset_keep_style_subject').trim();
  if (!resizePrompt || resizePrompt === 'creator.precision_size_prompt_preset_keep_style_subject') {
    return { error: i18nText('creator.precision_size_instruction_required') };
  }
  var capability = getPrecisionResizeCapability();
  var outputPolicy = getPrecisionOutputSizePolicy();
  var selectedPrecisionModel = precisionEditSelectedModel && precisionEditSelectedModel.model || '';
  var compatibilityProfile = typeof PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE === 'string'
    ? PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE : 'gpt-image-2';
  var protocolModel = selectedPrecisionModel === compatibilityProfile || capability.flexibleSizes;
  if (!protocolModel && capability.canonicalModel === compatibilityProfile) {
    var declaredProtocolSizes = Object.keys(capability.sizes || {});
    protocolModel = declaredProtocolSizes.length > 0 && declaredProtocolSizes.every(function(size) {
      return precisionGptImage2SizeError(size) === '';
    });
  }
  if (protocolModel) {
    var protocolError = precisionGptImage2SizeError(targetSize);
    if (protocolError) {
      return {
        error: i18nText('creator.precision_size_invalid'),
        rejection: { code: protocolError, target_size: targetSize }
      };
    }
  }
  if (!capability.known) {
    return {
      error: i18nText('creator.precision_size_capability_unknown', { size: targetSize }),
      rejection: { code: 'precision_edit_size_capability_unknown', target_size: targetSize }
    };
  }
  if (outputPolicy !== 'fit_crop' && !capability.flexibleSizes && capability.sizes[targetSize] !== true) {
    return {
      error: i18nText('creator.precision_size_capability_unsupported', { size: targetSize }),
      rejection: { code: 'precision_edit_size_undeclared', target_size: targetSize, supported_sizes: Object.keys(capability.sizes) }
    };
  }
  return {
    mode: 'resize',
    targetSize: targetSize,
    prompt: resizePrompt,
    outputSizePolicy: getPrecisionOutputSizePolicy()
  };
}

function setPrecisionBaseVersion(id) {
  var entries = [precisionEditSession.source].concat(precisionEditSession.versions);
  var version = entries.find(function(entry) { return entry.id === id; });
  if (!version || version.id === precisionEditSession.baseVersionId || precisionSourceTaskIsActive() || precisionBaseVersionSwitchPending) return false;
  precisionBaseVersionSwitchPending = true;
  var loadToken = ++precisionVersionLoadToken;
  var sourceGeneration = precisionSourceLoadGeneration;
  renderPrecisionEditSession();
  if (typeof updatePrecisionEditControls === 'function') updatePrecisionEditControls();
  setStatus(i18nText('common.loading'));
  var prompt = (document.getElementById('txtPromptPrecision') || { value: '' }).value;
  var source = version.data;
  function isCurrentSwitch() {
    return sourceGeneration === precisionSourceLoadGeneration && loadToken === precisionVersionLoadToken && precisionBaseVersionSwitchPending;
  }
  function finishFailedSwitch() {
    if (loadToken !== precisionVersionLoadToken || !precisionBaseVersionSwitchPending) return false;
    precisionBaseVersionSwitchPending = false;
    if (sourceGeneration !== precisionSourceLoadGeneration) return false;
    renderPrecisionEditSession();
    if (typeof updatePrecisionEditControls === 'function') updatePrecisionEditControls();
    setStatus(i18nText('image.load_failed'));
    return true;
  }
  function activateVersion(dataUrl) {
    if (!isCurrentSwitch() || typeof dataUrl !== 'string' || dataUrl.indexOf('data:') !== 0) {
      finishFailedSwitch();
      return;
    }
    try {
      loadPrecisionEditSourceImage(dataUrl, prompt, {
        preserveSession: true,
        generation: sourceGeneration,
        baseVersionLoadToken: loadToken,
        beforeCommit: function() {
          if (!isCurrentSwitch()) return false;
          precisionEditSession.baseVersionId = id;
          precisionEditSession.selectedVersionId = id;
          precisionEditSession.view = 'after';
          precisionBaseVersionSwitchPending = false;
          return true;
        },
        onLoaded: function() {
          if (sourceGeneration !== precisionSourceLoadGeneration || loadToken !== precisionVersionLoadToken) return;
          setStatus(i18nText('creator.precision_base_updated'));
        },
        onError: finishFailedSwitch
      });
    } catch (error) {
      finishFailedSwitch();
    }
  }
  if (String(source).indexOf('data:') === 0) {
    activateVersion(source);
    return true;
  }
  _authFetch(source).then(function(response) {
    if (sourceGeneration !== precisionSourceLoadGeneration || loadToken !== precisionVersionLoadToken) {
      finishFailedSwitch();
      return null;
    }
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.blob();
  }).then(function(blob) {
    if (sourceGeneration !== precisionSourceLoadGeneration || loadToken !== precisionVersionLoadToken) {
      finishFailedSwitch();
      return;
    }
    if (!blob) {
      finishFailedSwitch();
      return;
    }
    var reader = new FileReader();
    reader.onload = function() {
      if (sourceGeneration !== precisionSourceLoadGeneration || loadToken !== precisionVersionLoadToken) {
        finishFailedSwitch();
        return;
      }
      activateVersion(String(reader.result || ''));
    };
    reader.onerror = function() {
      finishFailedSwitch();
    };
    reader.readAsDataURL(blob);
  }).catch(function() {
    finishFailedSwitch();
  });
  return true;
}

function appendPrecisionEditVersion(result, expectedGeneration) {
  if (Number.isFinite(expectedGeneration) && expectedGeneration !== precisionSourceLoadGeneration) return;
  if (!result || !result.success || !result.local_path || !precisionEditSession.source) return;
  var src = precisionLocalPathUrl(result.local_path);
  var promptField = typeof document !== 'undefined' ? document.getElementById('txtPromptPrecision') : null;
  var prompt = result.prompt || result.enhanced_prompt || (promptField ? promptField.value : '');
  appendPrecisionEditImageVersion(src, null, {
    prompt: prompt, autoSetBase: true,
    createdAt: result.createdAt || result.created_at || result.timestamp || '',
    width: result.width, height: result.height
  });
}

function schedulePrecisionAutoBaseVersion(id) {
  precisionAutoBaseVersionTarget = String(id || '');
  if (precisionAutoBaseVersionTimer !== null) return;
  precisionAutoBaseVersionTimer = setTimeout(function() {
    precisionAutoBaseVersionTimer = null;
    var target = precisionAutoBaseVersionTarget;
    precisionAutoBaseVersionTarget = '';
    if (!target || !precisionEditSession.versions.some(function(version) { return version.id === target; })) return;
    setPrecisionBaseVersion(target);
  }, 0);
}

function appendPrecisionEditImageVersion(src, parentId, metadata) {
  if (!src || precisionEditSession.versions.some(function(version) { return version.data === src; })) return;
  metadata = metadata || {};
  var next = precisionEditSession.versions.length + 1;
  var id = 'version-' + next;
  var versionParentId = parentId || precisionEditSession.taskBaseVersionId || precisionEditSession.baseVersionId || 'original';
  precisionEditSession.versions.push({
    id: id,
    label: String(next),
    data: src,
    parentId: versionParentId,
    imageData: typeof metadata.imageData === 'string' ? metadata.imageData : '',
    transparent: metadata.transparent === true,
    previewBackground: metadata.previewBackground === 'checkerboard' ? 'checkerboard' : '',
    operation: typeof metadata.operation === 'string' ? metadata.operation : '',
    prompt: typeof metadata.prompt === 'string' ? metadata.prompt : '',
    remoteVersionId: typeof metadata.remoteVersionId === 'string' ? metadata.remoteVersionId : '',
    adapter: precisionCutoutAdapterId(metadata.adapter),
    fallbackFrom: precisionCutoutAdapterId(metadata.fallbackFrom),
    restoreMode: metadata.restoreMode === true,
    createdAt: metadata.createdAt || metadata.created_at || metadata.timestamp || new Date().toISOString(),
    restoreMinAlpha: Number.isInteger(metadata.restoreMinAlpha) ? metadata.restoreMinAlpha : null,
    selectionApplied: metadata.selectionApplied === true,
    width: Number.isInteger(metadata.width) ? metadata.width : null,
    height: Number.isInteger(metadata.height) ? metadata.height : null
  });
  precisionEditSession.selectedVersionId = id;
  precisionEditSession.view = 'after';
  renderPrecisionEditSession();
  if (metadata.autoSetBase === true) schedulePrecisionAutoBaseVersion(id);
  return true;
}

function precisionTaskMonitorIsTerminal(value) {
  return ['completed', 'failed', 'error', 'cancelled', 'timeout', 'interrupted'].indexOf(String(value || '').toLowerCase()) !== -1;
}

function precisionTaskMonitorStartedAt(value) {
  if (typeof value === 'number' && Number.isFinite(value)) return value > 100000000000 ? value : value * 1000;
  if (typeof value === 'string' && value.trim()) {
    var numeric = Number(value);
    if (Number.isFinite(numeric)) return numeric > 100000000000 ? numeric : numeric * 1000;
    var parsed = Date.parse(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function renderPrecisionTaskMonitorElapsed() {
  var elapsed = document.getElementById('precisionTaskElapsed');
  if (!elapsed) return;
  elapsed.textContent = precisionTaskMonitorElapsedSeconds === null ? '' : Math.max(0, precisionTaskMonitorElapsedSeconds).toFixed(1) + 's';
}

function setPrecisionTaskMonitorExpanded(expanded, restoreFocus) {
  var monitor = document.getElementById('precisionTaskMonitor');
  var toggle = document.getElementById('btnPrecisionTaskMonitorToggle');
  var body = document.getElementById('precisionTaskMonitorBody');
  if (!monitor || !toggle || !body) return false;
  var next = !!expanded;
  var wasExpanded = monitor.classList.contains('precision-task-expanded');
  monitor.classList.toggle('precision-task-expanded', next);
  monitor.classList.toggle('precision-task-collapsed', !next);
  toggle.setAttribute('aria-expanded', next ? 'true' : 'false');
  toggle.setAttribute('aria-label', next ? '折叠处理进度' : '展开处理进度');
  toggle.setAttribute('title', next ? '折叠处理进度' : '展开处理进度');
  body.setAttribute('aria-hidden', next ? 'false' : 'true');
  if (!next && restoreFocus && wasExpanded && typeof toggle.focus === 'function') toggle.focus();
  return wasExpanded;
}

function togglePrecisionTaskMonitor() {
  var monitor = document.getElementById('precisionTaskMonitor');
  if (!monitor) return false;
  setPrecisionTaskMonitorExpanded(!monitor.classList.contains('precision-task-expanded'));
  return monitor.classList.contains('precision-task-expanded');
}

function precisionDisplaySize(value) {
  if (typeof value === 'string') {
    var stringMatch = /^(\d{2,5})x(\d{2,5})$/i.exec(value.trim());
    return stringMatch ? Number(stringMatch[1]) + 'x' + Number(stringMatch[2]) : '';
  }
  if (value && typeof value === 'object') {
    var objectWidth = Number(value.width || value.w);
    var objectHeight = Number(value.height || value.h);
    if (Number.isFinite(objectWidth) && Number.isFinite(objectHeight) && objectWidth > 0 && objectHeight > 0) {
      return Math.round(objectWidth) + 'x' + Math.round(objectHeight);
    }
  }
  return '';
}

function precisionDisplaySizeFromFields(record, names, widthNames, heightNames) {
  record = record || {};
  for (var index = 0; index < names.length; index += 1) {
    var fromValue = precisionDisplaySize(record[names[index]]);
    if (fromValue) return fromValue;
  }
  for (var pair = 0; pair < widthNames.length; pair += 1) {
    var width = Number(record[widthNames[pair]]);
    var height = Number(record[heightNames[pair]]);
    if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
      return Math.round(width) + 'x' + Math.round(height);
    }
  }
  return '';
}

function precisionOutputSizeNoticeFromRecord(record) {
  if (!record || typeof record !== 'object') return '';
  var actual = precisionDisplaySizeFromFields(record,
    ['actual_size', 'actualSize', 'upstream_size', 'upstreamSize', 'upstream_output_size', 'original_size'],
    ['actual_width', 'actualWidth', 'upstream_width', 'original_width'],
    ['actual_height', 'actualHeight', 'upstream_height', 'original_height']);
  var target = precisionDisplaySizeFromFields(record,
    ['target_size', 'targetSize', 'requested_size', 'requestedSize', 'precision_target_size', 'output_size'],
    ['target_width', 'targetWidth', 'requested_width', 'output_width'],
    ['target_height', 'targetHeight', 'requested_height', 'output_height']);
  var adjusted = precisionDisplaySizeFromFields(record,
    ['adjusted_size', 'adjustedSize', 'local_size', 'localSize', 'final_size', 'finalSize'],
    ['adjusted_width', 'adjustedWidth', 'local_width', 'final_width'],
    ['adjusted_height', 'adjustedHeight', 'local_height', 'final_height']);
  var code = String(record.code || record.error_code || record.reason_code || record.status_code || '').toLowerCase();
  var status = String(record.status || '').toLowerCase();
  var warning = String(record.size_adjusted_warning || record.output_size_warning || '').trim();
  var failedMismatch = code.indexOf('size_mismatch') !== -1 || code.indexOf('output_size_mismatch') !== -1 || status.indexOf('mismatch') !== -1;
  if ((adjusted || warning) && actual && (adjusted || target)) {
    return i18nText('creator.precision_output_size_adjusted', { actual: actual, target: adjusted || target });
  }
  if (failedMismatch && actual && target) {
    return i18nText('creator.precision_output_size_strict_mismatch', { actual: actual, target: target });
  }
  return warning;
}

function precisionOutputSizeNotices(data) {
  var notices = [];
  var seen = {};
  var add = function(value) {
    value = String(value || '').trim();
    if (!value || seen[value]) return;
    seen[value] = true;
    notices.push(value);
  };
  var visit = function(record) {
    if (!record || typeof record !== 'object') return;
    add(precisionOutputSizeNoticeFromRecord(record));
    visit(record.error_details);
    visit(record.details);
    var warnings = Array.isArray(record.warnings) ? record.warnings : [];
    warnings.forEach(function(item) {
      if (typeof item === 'string') add(item);
      else visit(item);
    });
  };
  visit(data);
  var states = data && data.provider_states ? data.provider_states : {};
  Object.keys(states).forEach(function(key) {
    var state = states[key] || {};
    visit(state);
    visit(state.result);
  });
  return notices;
}

function precisionTransportFailureNoticeFromRecord(record) {
  if (!record || typeof record !== 'object') return '';
  var stage = String(record.transport_stage || record.transportStage || '').toLowerCase();
  var errorType = String(record.transport_error || record.transportError || '').toLowerCase();
  var retry = String(record.automatic_retry || record.automaticRetry || '').toLowerCase();
  if (stage === 'response_read' && errorType === 'readerror' && retry === 'suppressed_non_idempotent_image_edit') {
    return i18nText('creator.precision_connection_response_read_no_retry');
  }
  return '';
}

function precisionTransportFailureNotices(data) {
  var notices = [];
  var seen = {};
  var add = function(value) {
    value = String(value || '').trim();
    if (!value || seen[value]) return;
    seen[value] = true;
    notices.push(value);
  };
  var visit = function(record) {
    if (!record || typeof record !== 'object') return;
    add(precisionTransportFailureNoticeFromRecord(record));
    visit(record.error_details);
    visit(record.details);
  };
  visit(data);
  var states = data && data.provider_states ? data.provider_states : {};
  Object.keys(states).forEach(function(key) {
    var state = states[key] || {};
    visit(state);
    visit(state.result);
  });
  return notices;
}

function updatePrecisionTaskMonitor(data) {
  var monitor = document.getElementById('precisionTaskMonitor');
  var status = document.getElementById('precisionTaskStatus');
  var progress = document.getElementById('precisionTaskProgress');
  var elapsed = document.getElementById('precisionTaskElapsed');
  var log = document.getElementById('precisionTaskLog');
  var progressBar = document.getElementById('precisionTaskProgressBar');
  var progressFill = document.getElementById('precisionTaskProgressFill');
  var sourceTaskStatus = String(data && data.status || 'idle').toLowerCase();
  if (sourceTaskStatus !== precisionSourceTaskStatus) {
    precisionSourceTaskStatus = sourceTaskStatus;
    precisionSourceTaskEpoch += 1;
    precisionPendingSourceIntent = null;
  }

  if (!data) {
    if (monitor) monitor.classList.add('precision-task-idle');
    if (typeof setPrecisionTaskMonitorExpanded === 'function') setPrecisionTaskMonitorExpanded(false);
    if (monitor) {
      monitor.classList.remove('precision-task-active', 'precision-task-terminal', 'precision-task-failed', 'precision-task-completed');
      monitor.removeAttribute('data-task-status');
    }
    if (precisionTaskMonitorTimer) { clearInterval(precisionTaskMonitorTimer); precisionTaskMonitorTimer = null; }
    precisionTaskMonitorData = null;
    precisionTaskMonitorStartedAtMs = 0;
    precisionTaskMonitorElapsedSeconds = null;
    precisionTaskMonitorTerminal = false;
    if (status) status.textContent = '';
    if (progress) progress.textContent = '';
    if (elapsed) elapsed.textContent = '';
    if (log) log.textContent = '';
    if (progressBar) {
      progressBar.style.width = '';
      progressBar.removeAttribute('aria-valuenow');
      progressBar.setAttribute('aria-valuetext', '');
      progressBar.classList.remove('indeterminate');
    }
    if (progressFill) {
      progressFill.style.width = '';
      progressFill.removeAttribute('aria-valuenow');
      progressFill.setAttribute('aria-valuetext', '');
      progressFill.classList.remove('indeterminate');
    }
    updatePrecisionSourceActions();
    return;
  }

  if (monitor) monitor.classList.remove('precision-task-idle');
  precisionTaskMonitorData = data;
  var taskStatus = String(data.status || i18nText('status.queued'));
  var terminal = precisionTaskMonitorIsTerminal(taskStatus);
  var wasTerminal = precisionTaskMonitorTerminal;
  var now = Date.now();
  var reportedElapsed = Number(data.elapsed_seconds);
  var hasReportedElapsed = data.elapsed_seconds !== undefined && data.elapsed_seconds !== null && Number.isFinite(reportedElapsed) && reportedElapsed >= 0;
  var reportedStartedAt = precisionTaskMonitorStartedAt(data.started_at);

  if (terminal && wasTerminal) {
  } else if (hasReportedElapsed) {
    var previousElapsed = precisionTaskMonitorElapsedSeconds;
    precisionTaskMonitorElapsedSeconds = terminal ? reportedElapsed : Math.max(previousElapsed === null ? 0 : previousElapsed, reportedElapsed);
    if (!precisionTaskMonitorStartedAtMs || previousElapsed === null || reportedElapsed > previousElapsed) {
      precisionTaskMonitorStartedAtMs = now - reportedElapsed * 1000;
    }
  } else if (reportedStartedAt) {
    precisionTaskMonitorStartedAtMs = reportedStartedAt;
    var fromStartedAt = Math.max(0, (now - reportedStartedAt) / 1000);
    precisionTaskMonitorElapsedSeconds = terminal ? fromStartedAt : Math.max(precisionTaskMonitorElapsedSeconds === null ? 0 : precisionTaskMonitorElapsedSeconds, fromStartedAt);
  } else if (!terminal) {
    if (!precisionTaskMonitorStartedAtMs) precisionTaskMonitorStartedAtMs = now;
    precisionTaskMonitorElapsedSeconds = Math.max(precisionTaskMonitorElapsedSeconds === null ? 0 : precisionTaskMonitorElapsedSeconds, (now - precisionTaskMonitorStartedAtMs) / 1000);
  } else if (!precisionTaskMonitorStartedAtMs && precisionTaskMonitorElapsedSeconds === null) {
    precisionTaskMonitorElapsedSeconds = null;
  } else if (precisionTaskMonitorElapsedSeconds === null) {
    precisionTaskMonitorElapsedSeconds = Math.max(0, (now - precisionTaskMonitorStartedAtMs) / 1000);
  }

  precisionTaskMonitorTerminal = terminal;
  if (precisionTaskMonitorTimer) { clearInterval(precisionTaskMonitorTimer); precisionTaskMonitorTimer = null; }
  if (!terminal) {
    precisionTaskMonitorTimer = setInterval(function() {
      if (precisionTaskMonitorTerminal || !precisionTaskMonitorStartedAtMs) return;
      precisionTaskMonitorElapsedSeconds = Math.max(precisionTaskMonitorElapsedSeconds === null ? 0 : precisionTaskMonitorElapsedSeconds, (Date.now() - precisionTaskMonitorStartedAtMs) / 1000);
      renderPrecisionTaskMonitorElapsed();
    }, 200);
  }

  var states = data.provider_states || {};
  var lines = [];
  Object.keys(states).forEach(function(key) { lines = lines.concat(states[key].log || []); });
  lines = lines.concat(precisionOutputSizeNotices(data));
  lines = lines.concat(precisionTransportFailureNotices(data));
  var stateKeys = Object.keys(states);
  var successfulCompleted = stateKeys.filter(function(key) {
    var state = states[key] || {};
    return String(state.status || '').toLowerCase() === 'completed' && (!state.result || state.result.success !== false);
  }).length;
  var actualProgress = stateKeys.length ? successfulCompleted / stateKeys.length * 100 : 0;
  var terminalFailed = terminal && String(taskStatus).toLowerCase() !== 'completed';
  var hasActualProgress = stateKeys.length > 0 && successfulCompleted > 0 && !(terminalFailed && successfulCompleted === stateKeys.length);
  var numericEstimate = Number(data.progress);
  var hasEstimate = !terminal && data.progress !== undefined && data.progress !== null && Number.isFinite(numericEstimate);
  var actualLabel = stateKeys.length ? '实际完成 ' + successfulCompleted + '/' + stateKeys.length : '实际进度待确认';
  var progressText = hasEstimate ? actualLabel + ' · 耗时估算中' : actualLabel;
  if (status) status.textContent = taskStatus;
  if (progress) progress.textContent = progressText;
  if (monitor) {
    if (typeof monitor.setAttribute === 'function') monitor.setAttribute('data-task-status', String(taskStatus).toLowerCase());
    monitor.classList.toggle('precision-task-active', !terminal);
    monitor.classList.toggle('precision-task-terminal', terminal);
    monitor.classList.toggle('precision-task-failed', terminalFailed);
    monitor.classList.toggle('precision-task-completed', String(taskStatus).toLowerCase() === 'completed');
  }
  // A live task opens the monitor automatically; terminal results stay open
  // until the user explicitly collapses them.
  if (typeof setPrecisionTaskMonitorExpanded === 'function') setPrecisionTaskMonitorExpanded(true);
  renderPrecisionTaskMonitorElapsed();
  if (log) {
    log.textContent = lines.join('\n');
    _smartScroll(log);
  }

  if (progressBar) {
    progressBar.classList.toggle('indeterminate', hasEstimate);
    progressBar.classList.toggle('has-estimate', hasEstimate);
    if (hasActualProgress && !hasEstimate) {
      progressBar.style.width = actualProgress + '%';
      progressBar.setAttribute('aria-valuenow', String(Math.round(actualProgress)));
      progressBar.setAttribute('aria-valuetext', actualLabel);
    } else {
      progressBar.style.width = terminal ? '0%' : '';
      progressBar.removeAttribute('aria-valuenow');
      progressBar.setAttribute('aria-valuetext', terminal ? taskStatus + '，' + actualLabel : progressText);
    }
  }
  if (progressFill) {
    progressFill.classList.toggle('indeterminate', hasEstimate);
    progressFill.classList.toggle('has-estimate', hasEstimate);
    progressFill.style.width = hasActualProgress && !hasEstimate ? actualProgress + '%' : (terminal ? '0%' : '');
    progressFill.removeAttribute('aria-valuenow');
    progressFill.removeAttribute('aria-valuetext');
  }
  updatePrecisionSourceActions();
}

function precisionCutoutHasSource() {
  return typeof precisionEditSourceImageData === 'string'
    && /^data:image\/[^;,]+;base64,/i.test(precisionEditSourceImageData)
    && precisionEditSourceWidth > 0
    && precisionEditSourceHeight > 0
    && !!precisionEditSession.source;
}

// UI controls should only be locked while a live cutout/refine request exists.
// A stale pending flag can survive SPA navigation or a cancelled request; the
// abort controller is the authoritative marker that work is still in flight.
function precisionCutoutUiBusy() {
  return precisionCutoutPending === true
    && (typeof precisionCutoutAbortController === 'undefined'
      || (!!precisionCutoutAbortController
        && (!precisionCutoutAbortController.signal || precisionCutoutAbortController.signal.aborted !== true)));
}

function precisionCutoutIsExecutable(capability) {
  return !!(capability
    && capability.contract === PRECISION_CUTOUT_CONTRACT
    && capability.available === true
    && capability.executable === true
    && Array.isArray(capability.adapters)
    && capability.adapters.length > 0);
}

function precisionCutoutAdapterId(value) {
  var adapterId = typeof value === 'string' ? value.trim() : '';
  return /^[a-z0-9][a-z0-9._-]{0,127}$/.test(adapterId) ? adapterId : '';
}

function precisionCutoutAdapterText(value, fallback) {
  var text = typeof value === 'string' ? value.trim() : '';
  return text || fallback || '';
}

function precisionCutoutAdapterRecords(capability) {
  if (!capability || capability.contract !== PRECISION_CUTOUT_CONTRACT) return [];
  var records = [];
  var seen = {};
  var rawCapabilities = Array.isArray(capability.adapter_capabilities) ? capability.adapter_capabilities : [];
  rawCapabilities.forEach(function(raw) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return;
    var descriptor = raw.descriptor && typeof raw.descriptor === 'object' && !Array.isArray(raw.descriptor) ? raw.descriptor : {};
    var adapterId = precisionCutoutAdapterId(raw.adapter || descriptor.adapter_id);
    if (!adapterId || seen[adapterId]) return;
    seen[adapterId] = true;
    var dependencies = Array.isArray(raw.dependencies) ? raw.dependencies : (Array.isArray(descriptor.dependencies) ? descriptor.dependencies : []);
    var resource = precisionCutoutAdapterText(raw.resource_status || descriptor.resource_status, '');
    if (!resource && raw.needs_model === true && raw.needs_dependency === true) resource = i18nText('creator.cutout_algorithm_resources_model_dependency');
    else if (!resource && raw.needs_model === true) resource = i18nText('creator.cutout_algorithm_resources_model');
    else if (!resource && raw.needs_dependency === true) resource = i18nText('creator.cutout_algorithm_resources_dependency');
    else if (!resource) resource = precisionCutoutAdapterText(raw.state, '');
    records.push({
      adapter: adapterId,
      algorithm: precisionCutoutAdapterText(raw.algorithm || descriptor.algorithm, adapterId),
      available: raw.available === true,
      executable: raw.executable === true,
      state: precisionCutoutAdapterText(raw.state || descriptor.status, ''),
      source: precisionCutoutAdapterText(raw.source_page || descriptor.source_page || raw.weights_source || descriptor.weights_source, ''),
      license: precisionCutoutAdapterText((raw.license && raw.license.name) || (descriptor.license && descriptor.license.name) || descriptor.license_name, ''),
      licenseStatus: precisionCutoutAdapterText((raw.license && raw.license.status) || (descriptor.license && descriptor.license.status) || descriptor.license_status, ''),
      dependencies: dependencies.filter(function(item) { return typeof item === 'string' && item.trim(); }).map(function(item) { return item.trim(); }),
      resource: resource,
      reason: precisionCutoutAdapterText(raw.reason || descriptor.reason, '')
    });
  });
  if (!records.length && capability.available === true && capability.executable === true && Array.isArray(capability.adapters)) {
    capability.adapters.forEach(function(adapter) {
      var adapterId = precisionCutoutAdapterId(adapter);
      if (!adapterId || seen[adapterId]) return;
      seen[adapterId] = true;
      records.push({ adapter: adapterId, algorithm: adapterId, available: true, executable: true, state: 'ready', source: '', license: '', licenseStatus: '', dependencies: [], resource: '', reason: '' });
    });
  }
  return records;
}

function precisionCutoutExecutableAdapterRecords(capability) {
  return precisionCutoutAdapterRecords(capability).filter(function(record) {
    return record.available === true && record.executable === true;
  });
}

function precisionCutoutSelectedAdapterRecord(capability) {
  var executable = precisionCutoutExecutableAdapterRecords(capability);
  var selected = precisionCutoutAdapterId(precisionCutoutSelectedAdapter);
  return executable.find(function(record) { return record.adapter === selected; })
    || executable.find(function(record) { return record.adapter === 'u2net-human-seg-onnx'; })
    || executable[0]
    || null;
}

function precisionCutoutAdapterDisplayName(record) {
  var algorithm = precisionCutoutAdapterText(record && record.algorithm, '');
  // Keep the legacy descriptor as a compatibility alias, but key the label
  // off the adapter id emitted by the runtime registry.
  if (record && (record.adapter === 'modnet-portrait-onnx' || record.adapter === 'modnet-photographic-portrait')) {
    return algorithm + ' - ' + i18nText('creator.cutout_algorithm_modnet_lab_notice');
  }
  return algorithm;
}

function precisionCutoutAdapterEscaped(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function precisionCutoutAdapterFact(label, value) {
  var content = precisionCutoutAdapterText(value, i18nText('creator.cutout_algorithm_not_reported'));
  return '<div><dt>' + precisionCutoutAdapterEscaped(label) + '</dt><dd>' + precisionCutoutAdapterEscaped(content) + '</dd></div>';
}

function setPrecisionCutoutAdapterDetailsExpanded(expanded) {
  var controls = getPrecisionCutoutControls();
  var panel = controls.adapterPanel;
  var toggle = controls.adapterDetailsToggle;
  var details = controls.adapterDetails;
  if (!panel || !toggle || !details) return false;
  precisionCutoutAdapterDetailsExpanded = expanded === true;
  panel.dataset.detailsExpanded = precisionCutoutAdapterDetailsExpanded ? 'true' : 'false';
  toggle.setAttribute('aria-expanded', precisionCutoutAdapterDetailsExpanded ? 'true' : 'false');
  details.classList.toggle('hidden', !precisionCutoutAdapterDetailsExpanded);
  details.setAttribute('aria-hidden', precisionCutoutAdapterDetailsExpanded ? 'false' : 'true');
  return precisionCutoutAdapterDetailsExpanded;
}

function setPrecisionCutoutMode(mode) {
  var next = mode === 'professional' ? 'professional' : 'simple';
  precisionCutoutMode = next;
  var controls = getPrecisionCutoutControls();
  if (controls.simpleModeButton) controls.simpleModeButton.setAttribute('aria-selected', next === 'simple' ? 'true' : 'false');
  if (controls.professionalModeButton) controls.professionalModeButton.setAttribute('aria-selected', next === 'professional' ? 'true' : 'false');
  if (controls.simpleButton) controls.simpleButton.classList.toggle('hidden', next !== 'simple');
  if (controls.professionalOpenButton) controls.professionalOpenButton.classList.toggle('hidden', next !== 'simple');
  if (next === 'professional') openPrecisionCutoutProfessionalDialog();
  return next;
}

function openPrecisionCutoutProfessionalDialog() {
  var controls = getPrecisionCutoutControls();
  precisionCutoutMode = 'professional';
  if (controls.simpleModeButton) controls.simpleModeButton.setAttribute('aria-selected', 'false');
  if (controls.professionalModeButton) controls.professionalModeButton.setAttribute('aria-selected', 'true');
  if (controls.professionalDialog) {
    if (!precisionCutoutProfessionalOpener) precisionCutoutProfessionalOpener = document.activeElement;
    if (!precisionCutoutProfessionalHome && controls.professionalDialog.parentNode) {
      precisionCutoutProfessionalHome = {
        parent: controls.professionalDialog.parentNode,
        nextSibling: controls.professionalDialog.nextSibling
      };
    }
    if (document.body && controls.professionalDialog.parentNode !== document.body) {
      document.body.appendChild(controls.professionalDialog);
    }
    if (document.body) document.body.classList.add('precision-cutout-professional-focus');
    var page = document.getElementById('pageGenerate');
    if (page) page.classList.add('precision-cutout-professional-focus');
    controls.professionalDialog.hidden = false;
    controls.professionalDialog.setAttribute('aria-hidden', 'false');
    setPrecisionCutoutProfessionalDockCollapsed(false);
    setPrecisionCutoutProfessionalDockWidth(precisionCutoutProfessionalDockWidth);
    observePrecisionCutoutProfessionalDockGeometry();
    schedulePrecisionCutoutProfessionalDockGeometry();
  }
  if (controls.simpleButton) controls.simpleButton.classList.add('hidden');
  if (controls.professionalOpenButton) controls.professionalOpenButton.classList.add('hidden');
  renderPrecisionCutoutAdapterPicker(precisionCutoutCapability);
  if (controls.professionalCloseButton && typeof controls.professionalCloseButton.focus === 'function') {
    controls.professionalCloseButton.focus({ preventScroll: true });
  }
  return true;
}

function closePrecisionCutoutProfessionalDialog() {
  var controls = getPrecisionCutoutControls();
  stopObservingPrecisionCutoutProfessionalDockGeometry();
  if (controls.professionalDialog) {
    controls.professionalDialog.hidden = true;
    controls.professionalDialog.setAttribute('aria-hidden', 'true');
    controls.professionalDialog.style.removeProperty('top');
    controls.professionalDialog.style.removeProperty('height');
    controls.professionalDialog.style.removeProperty('bottom');
    if (precisionCutoutProfessionalHome && precisionCutoutProfessionalHome.parent) {
      if (precisionCutoutProfessionalHome.nextSibling && precisionCutoutProfessionalHome.nextSibling.parentNode === precisionCutoutProfessionalHome.parent) {
        precisionCutoutProfessionalHome.parent.insertBefore(controls.professionalDialog, precisionCutoutProfessionalHome.nextSibling);
      } else {
        precisionCutoutProfessionalHome.parent.appendChild(controls.professionalDialog);
      }
    }
  }
  if (document.body) document.body.classList.remove('precision-cutout-professional-focus');
  var page = document.getElementById('pageGenerate');
  if (page) page.classList.remove('precision-cutout-professional-focus');
  precisionCutoutMode = 'simple';
  if (controls.simpleModeButton) controls.simpleModeButton.setAttribute('aria-selected', 'true');
  if (controls.professionalModeButton) controls.professionalModeButton.setAttribute('aria-selected', 'false');
  if (controls.simpleButton) controls.simpleButton.classList.remove('hidden');
  if (controls.professionalOpenButton) controls.professionalOpenButton.classList.remove('hidden');
  if (precisionCutoutProfessionalOpener && typeof precisionCutoutProfessionalOpener.focus === 'function') precisionCutoutProfessionalOpener.focus();
  precisionCutoutProfessionalOpener = null;
  precisionCutoutProfessionalHome = null;
  precisionCutoutProfessionalDockCollapsed = false;
  if (document.documentElement) document.documentElement.style.removeProperty('--precision-cutout-professional-dock-width');
  return true;
}

function precisionCutoutProfessionalDockLimits() {
  var viewport = Math.max(0, Number(typeof window !== 'undefined' && window.innerWidth) || 0);
  return { min: 320, max: Math.max(360, Math.min(560, viewport ? viewport * 0.46 : 560)) };
}

function setPrecisionCutoutProfessionalDockWidth(width) {
  var limits = precisionCutoutProfessionalDockLimits();
  var value = Math.max(limits.min, Math.min(limits.max, Number(width) || limits.min));
  precisionCutoutProfessionalDockWidth = Math.round(value);
  if (document.documentElement) document.documentElement.style.setProperty('--precision-cutout-professional-dock-width', precisionCutoutProfessionalDockWidth + 'px');
  var handle = document.getElementById('precisionCutoutProfessionalResizeHandle');
  if (handle) {
    handle.setAttribute('aria-valuemin', String(Math.round(limits.min)));
    handle.setAttribute('aria-valuemax', String(Math.round(limits.max)));
    handle.setAttribute('aria-valuenow', String(precisionCutoutProfessionalDockWidth));
  }
  positionPrecisionCanvasResizeHandle();
  schedulePrecisionCutoutProfessionalDockGeometry();
  return precisionCutoutProfessionalDockWidth;
}

function syncPrecisionCutoutProfessionalDockGeometry() {
  var dialog = document.getElementById('precisionCutoutProfessionalDialog');
  var shell = document.getElementById('precisionCanvasShell');
  if (!dialog || dialog.hidden || !shell || !document.body || !document.body.classList.contains('precision-cutout-professional-focus') || !shell.getBoundingClientRect) return;
  var rect = shell.getBoundingClientRect();
  if (!rect || rect.height < 1) return;
  var viewportHeight = Math.max(0, Number(typeof window !== 'undefined' && window.innerHeight) || 0);
  var top = Math.max(0, Math.round(rect.top));
  var height = Math.round(rect.height);
  if (viewportHeight) height = Math.min(height, Math.max(1, viewportHeight - top - 14));
  dialog.style.top = top + 'px';
  dialog.style.height = height + 'px';
  dialog.style.bottom = 'auto';
}

function schedulePrecisionCutoutProfessionalDockGeometry() {
  // Opening the focus workbench changes the canvas grid. Wait for that grid
  // reflow before sampling its bounds, otherwise the dock can retain an old height.
  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(function() {
      requestAnimationFrame(syncPrecisionCutoutProfessionalDockGeometry);
    });
  } else if (typeof setTimeout === 'function') {
    setTimeout(syncPrecisionCutoutProfessionalDockGeometry, 0);
  } else {
    syncPrecisionCutoutProfessionalDockGeometry();
  }
}

function observePrecisionCutoutProfessionalDockGeometry() {
  stopObservingPrecisionCutoutProfessionalDockGeometry();
  var shell = document.getElementById('precisionCanvasShell');
  if (!shell || typeof ResizeObserver !== 'function') return;
  precisionCutoutProfessionalDockObserver = new ResizeObserver(function() {
    schedulePrecisionCutoutProfessionalDockGeometry();
  });
  precisionCutoutProfessionalDockObserver.observe(shell);
}

function stopObservingPrecisionCutoutProfessionalDockGeometry() {
  if (!precisionCutoutProfessionalDockObserver) return;
  precisionCutoutProfessionalDockObserver.disconnect();
  precisionCutoutProfessionalDockObserver = null;
}

function setPrecisionCutoutProfessionalDockCollapsed(collapsed) {
  precisionCutoutProfessionalDockCollapsed = collapsed === true;
  var body = document.body;
  if (body) body.classList.toggle('precision-cutout-professional-dock-collapsed', precisionCutoutProfessionalDockCollapsed);
  var controls = getPrecisionCutoutControls();
  if (controls.professionalCollapseButton) {
    controls.professionalCollapseButton.setAttribute('aria-expanded', precisionCutoutProfessionalDockCollapsed ? 'false' : 'true');
    controls.professionalCollapseButton.setAttribute('aria-label', precisionCutoutProfessionalDockCollapsed ? '展开专业工具侧栏' : '收起专业工具侧栏');
    controls.professionalCollapseButton.title = precisionCutoutProfessionalDockCollapsed ? '展开专业工具侧栏' : '收起专业工具侧栏';
    controls.professionalCollapseButton.textContent = precisionCutoutProfessionalDockCollapsed ? '‹' : '›';
  }
  if (controls.professionalDialog) controls.professionalDialog.setAttribute('data-collapsed', precisionCutoutProfessionalDockCollapsed ? 'true' : 'false');
  positionPrecisionCanvasResizeHandle();
  schedulePrecisionCutoutProfessionalDockGeometry();
  return precisionCutoutProfessionalDockCollapsed;
}

function beginPrecisionCutoutProfessionalDockResize(event) {
  var handle = event && event.currentTarget;
  if (!event || !handle || event.isPrimary === false || (event.button !== undefined && event.button !== 0) || precisionCutoutProfessionalDockCollapsed) return;
  precisionCutoutProfessionalDockResizeState = { pointerId: event.pointerId, startX: event.clientX, startWidth: precisionCutoutProfessionalDockWidth, handle: handle };
  if (handle.setPointerCapture) { try { handle.setPointerCapture(event.pointerId); } catch (ignore) {} }
  window.addEventListener('pointermove', continuePrecisionCutoutProfessionalDockResize, { passive: false });
  window.addEventListener('pointerup', endPrecisionCutoutProfessionalDockResize);
  window.addEventListener('pointercancel', endPrecisionCutoutProfessionalDockResize);
  event.preventDefault();
}

function continuePrecisionCutoutProfessionalDockResize(event) {
  var state = precisionCutoutProfessionalDockResizeState;
  if (!state || state.pointerId !== event.pointerId) return;
  setPrecisionCutoutProfessionalDockWidth(state.startWidth + (state.startX - event.clientX));
  event.preventDefault();
}

function endPrecisionCutoutProfessionalDockResize(event) {
  var state = precisionCutoutProfessionalDockResizeState;
  if (!state || (event && event.pointerId !== undefined && event.pointerId !== state.pointerId)) return;
  precisionCutoutProfessionalDockResizeState = null;
  window.removeEventListener('pointermove', continuePrecisionCutoutProfessionalDockResize);
  window.removeEventListener('pointerup', endPrecisionCutoutProfessionalDockResize);
  window.removeEventListener('pointercancel', endPrecisionCutoutProfessionalDockResize);
  if (state.handle && state.handle.releasePointerCapture) { try { state.handle.releasePointerCapture(state.pointerId); } catch (ignore) {} }
}

function bindPrecisionCutoutProfessionalDock() {
  var controls = getPrecisionCutoutControls();
  if (controls.professionalCollapseButton && controls.professionalCollapseButton.dataset.precisionBound !== 'true') {
    controls.professionalCollapseButton.dataset.precisionBound = 'true';
    controls.professionalCollapseButton.addEventListener('click', function() { setPrecisionCutoutProfessionalDockCollapsed(!precisionCutoutProfessionalDockCollapsed); });
  }
  var handle = controls.professionalResizeHandle;
  if (!handle || handle.dataset.precisionBound === 'true') return;
  handle.dataset.precisionBound = 'true';
  handle.addEventListener('pointerdown', beginPrecisionCutoutProfessionalDockResize);
  handle.addEventListener('lostpointercapture', endPrecisionCutoutProfessionalDockResize);
  handle.addEventListener('keydown', function(event) {
    if (precisionCutoutProfessionalDockCollapsed) return;
    var limits = precisionCutoutProfessionalDockLimits();
    var next = precisionCutoutProfessionalDockWidth;
    if (event.key === 'ArrowLeft') next += 24;
    else if (event.key === 'ArrowRight') next -= 24;
    else if (event.key === 'Home') next = limits.min;
    else if (event.key === 'End') next = limits.max;
    else return;
    setPrecisionCutoutProfessionalDockWidth(next);
    event.preventDefault();
  });
  if (typeof window !== 'undefined' && window.addEventListener && handle.dataset.precisionGeometryBound !== 'true') {
    handle.dataset.precisionGeometryBound = 'true';
    window.addEventListener('resize', schedulePrecisionCutoutProfessionalDockGeometry);
  }
}

function togglePrecisionCutoutAdapterDetails() {
  return setPrecisionCutoutAdapterDetailsExpanded(!precisionCutoutAdapterDetailsExpanded);
}

// Build native options explicitly when the browser DOM is available. This
// avoids stale disabled attributes left behind by an initial capability probe
// and keeps the accessibility tree aligned with the actual selectable state.
function renderPrecisionCutoutAdapterOptions(select, executable) {
  if (!select) return;
  var unavailableLabel = precisionCutoutAdapterEscaped(i18nText('creator.cutout_algorithm_unavailable'));
  var canCreateOption = typeof document !== 'undefined' && typeof document.createElement === 'function'
    && typeof select.appendChild === 'function';
  if (!canCreateOption) {
    select.innerHTML = executable.length
      ? executable.map(function(record) {
        return '<option value="' + precisionCutoutAdapterEscaped(record.adapter) + '">' + precisionCutoutAdapterEscaped(precisionCutoutAdapterDisplayName(record)) + '</option>';
      }).join('')
      : '<option value="">' + unavailableLabel + '</option>';
    return;
  }
  select.innerHTML = '';
  if (!executable.length) {
    var emptyOption = document.createElement('option');
    emptyOption.value = '';
    emptyOption.textContent = i18nText('creator.cutout_algorithm_unavailable');
    emptyOption.disabled = false;
    select.appendChild(emptyOption);
    return;
  }
  executable.forEach(function(record) {
    var option = document.createElement('option');
    option.value = record.adapter;
    option.textContent = precisionCutoutAdapterDisplayName(record);
    option.disabled = false;
    select.appendChild(option);
  });
}

function renderPrecisionCutoutAdapterPicker(capability) {
  var controls = getPrecisionCutoutControls();
  var records = precisionCutoutAdapterRecords(capability);
  var executable = records.filter(function(record) { return record.available === true && record.executable === true; });
  var selected = precisionCutoutSelectedAdapterRecord(capability);
  precisionCutoutSelectedAdapter = selected ? selected.adapter : '';
  if (controls.adapterSelect) {
    var selectDisabled = precisionCutoutUiBusy() || !executable.length;
    controls.adapterSelect.disabled = true;
    renderPrecisionCutoutAdapterOptions(controls.adapterSelect, executable);
    controls.adapterSelect.value = selected ? selected.adapter : '';
    controls.adapterSelect.disabled = selectDisabled;
  }
  if (controls.professionalAlgorithm) {
    controls.professionalAlgorithm.disabled = precisionCutoutUiBusy() || !executable.length;
    renderPrecisionCutoutAdapterOptions(controls.professionalAlgorithm, executable);
    controls.professionalAlgorithm.value = selected ? selected.adapter : '';
  }
  if (controls.simpleAlgorithm) {
    controls.simpleAlgorithm.textContent = selected
      ? i18nText('creator.cutout_algorithm_ready', { algorithm: precisionCutoutAdapterDisplayName(selected) })
      : i18nText('creator.cutout_algorithm_unavailable');
    controls.simpleAlgorithm.dataset.state = selected ? 'ready' : 'unavailable';
  }
  if (controls.professionalAlgorithmStatus) {
    controls.professionalAlgorithmStatus.textContent = selected
      ? i18nText('creator.cutout_algorithm_ready', { algorithm: precisionCutoutAdapterDisplayName(selected) })
      : i18nText('creator.cutout_algorithm_unavailable');
  }
  if (controls.simpleButton) {
    controls.simpleButton.disabled = precisionCutoutUiBusy() || !precisionCutoutHasSource() || !selected;
    controls.simpleButton.setAttribute('aria-busy', precisionCutoutUiBusy() ? 'true' : 'false');
  }
  if (controls.professionalRunButton) {
    controls.professionalRunButton.disabled = precisionCutoutUiBusy() || !precisionCutoutHasSource() || !selected;
    controls.professionalRunButton.setAttribute('aria-busy', precisionCutoutUiBusy() ? 'true' : 'false');
  }
  if (controls.capabilityRefreshButton) {
    controls.capabilityRefreshButton.disabled = precisionCutoutModelMutationPending || precisionCutoutModelTaskIsActive(precisionCutoutModelTask) || precisionCutoutUiBusy();
  }
  if (controls.adapterStatus) {
    controls.adapterStatus.textContent = selected
      ? i18nText('creator.cutout_algorithm_ready', { algorithm: precisionCutoutAdapterDisplayName(selected) })
      : i18nText('creator.cutout_algorithm_unavailable');
    controls.adapterStatus.dataset.state = selected ? 'ready' : 'unavailable';
  }
  if (controls.adapterDetails) {
    controls.adapterDetails.innerHTML = records.length ? records.map(function(record) {
      var status = record.available === true && record.executable === true
        ? i18nText('creator.cutout_algorithm_verified')
        : i18nText('creator.cutout_algorithm_unverified');
      var license = [record.license, record.licenseStatus].filter(Boolean).join(' · ');
      return '<section class="precision-cutout-adapter-record" data-adapter="' + precisionCutoutAdapterEscaped(record.adapter) + '" data-executable="' + (record.available === true && record.executable === true ? 'true' : 'false') + '">' +
        '<strong>' + precisionCutoutAdapterEscaped(precisionCutoutAdapterDisplayName(record)) + '</strong>' +
        '<span class="precision-cutout-adapter-state">' + precisionCutoutAdapterEscaped(status) + '</span>' +
        '<dl class="precision-cutout-model-facts">' +
          precisionCutoutAdapterFact(i18nText('creator.cutout_algorithm_adapter_id'), record.adapter) +
          precisionCutoutAdapterFact(i18nText('creator.cutout_algorithm_source'), record.source) +
          precisionCutoutAdapterFact(i18nText('creator.cutout_algorithm_license'), license) +
          precisionCutoutAdapterFact(i18nText('creator.cutout_algorithm_dependencies'), record.dependencies.join(', ')) +
          precisionCutoutAdapterFact(i18nText('creator.cutout_algorithm_resources'), record.resource || record.reason || record.state) +
        '</dl></section>';
    }).join('') : '<p class="precision-cutout-adapter-empty">' + precisionCutoutAdapterEscaped(i18nText('creator.cutout_algorithm_details_empty')) + '</p>';
  }
  setPrecisionCutoutAdapterDetailsExpanded(precisionCutoutAdapterDetailsExpanded);
  return selected;
}

function setPrecisionCutoutSelectedAdapter(adapterId) {
  var normalized = precisionCutoutAdapterId(adapterId);
  var selectable = precisionCutoutExecutableAdapterRecords(precisionCutoutCapability).find(function(record) {
    return record.adapter === normalized;
  });
  if (!selectable) {
    renderPrecisionCutoutAdapterPicker(precisionCutoutCapability);
    return false;
  }
  precisionCutoutSelectedAdapter = selectable.adapter;
  renderPrecisionCutoutAdapterPicker(precisionCutoutCapability);
  return true;
}

function precisionCutoutPngData(value) {
  var imageData = typeof value === 'string' ? value : '';
  return /^data:image\/png;base64,iVBORw0KGgo[A-Za-z0-9+/]*={0,2}$/i.test(imageData) ? imageData : '';
}

function precisionCutoutGalleryUrl(result) {
  var galleryUrl = result && typeof result.gallery_url === 'string' ? result.gallery_url : '';
  var galleryPrefix = '/api/gallery/image/';
  if (galleryUrl.indexOf(galleryPrefix) !== 0 || /[?#]/.test(galleryUrl)) return '';
  var encodedName = galleryUrl.slice(galleryPrefix.length);
  if (!encodedName || encodedName.indexOf('/') !== -1 || encodedName.indexOf('\\') !== -1) return '';
  var decodedName = '';
  try { decodedName = decodeURIComponent(encodedName); } catch (error) { return ''; }
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,254}\.png$/i.test(decodedName)) return '';
  var filename = result && typeof result.filename === 'string' ? result.filename : '';
  if (filename && filename !== decodedName) return '';
  return galleryUrl;
}

function precisionCutoutSelectedVersion() {
  var entries = [precisionEditSession.source].concat(precisionEditSession.versions || []).filter(Boolean);
  return entries.find(function(entry) { return entry.id === precisionEditSession.selectedVersionId; }) || null;
}

function precisionCutoutSelectedTransparentVersion() {
  var selected = precisionCutoutSelectedVersion();
  if (!selected || selected.id === 'original' || selected.transparent !== true) return null;
  if (!precisionCutoutPngData(selected.imageData)) return null;
  if (!Number.isInteger(selected.width) || !Number.isInteger(selected.height) || selected.width !== precisionEditSourceWidth || selected.height !== precisionEditSourceHeight) return null;
  return selected;
}

function precisionCutoutSelectionObjects() {
  return (precisionEditObjects || []).filter(function(object) {
    return object && ['rect', 'ellipse', 'brush'].indexOf(object.type) !== -1;
  });
}

function activatePrecisionCutoutSelection() {
  var controls = getPrecisionCutoutControls();
  if (!controls.useSelection || !controls.useSelection.checked) return false;
  var selections = precisionCutoutSelectionObjects();
  if (!selections.length) return false;
  var selected = precisionEditObjectById(precisionEditSelectedId);
  if (!selected || ['rect', 'ellipse', 'brush'].indexOf(selected.type) === -1) {
    selected = selections[0];
    precisionEditSelectedId = selected.id;
  }
  // A local refinement selection must be visible and editable on the canvas.
  // Keep the existing shape tool active so the matching toolbar affordance is
  // highlighted rather than silently switching the generation selection mode.
  if (!precisionEditAnnotationsVisible) setPrecisionEditAnnotationsVisible(true);
  setPrecisionEditTool(selected.type);
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
  syncPrecisionAnnotationInstructionPopover();
  var canvas = document.getElementById('precisionAnnotationCanvas');
  if (canvas) {
    canvas.classList.add('is-cutout-selection-active');
    if (typeof canvas.focus === 'function') {
      try { canvas.focus({ preventScroll: true }); } catch (ignore) { canvas.focus(); }
    }
  }
  return true;
}

function exportPrecisionCutoutSelectionMask() {
  var objects = precisionCutoutSelectionObjects();
  if (!objects.length || !precisionEditSourceWidth || !precisionEditSourceHeight) return '';
  var output = document.createElement('canvas');
  output.width = precisionEditSourceWidth;
  output.height = precisionEditSourceHeight;
  var context = output.getContext('2d');
  if (!context) return '';
  context.clearRect(0, 0, output.width, output.height);
  context.fillStyle = '#ffffff';
  context.strokeStyle = '#ffffff';
  context.lineJoin = 'round';
  context.lineCap = 'round';
  objects.forEach(function(object) {
    var x1 = Math.max(0, Math.min(1, Number(object.x) || 0)) * output.width;
    var y1 = Math.max(0, Math.min(1, Number(object.y) || 0)) * output.height;
    var x2 = Math.max(0, Math.min(1, Number(object.x2) || 0)) * output.width;
    var y2 = Math.max(0, Math.min(1, Number(object.y2) || 0)) * output.height;
    if (object.type === 'rect') {
      context.fillRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
    } else if (object.type === 'ellipse') {
      context.beginPath();
      context.ellipse((x1 + x2) / 2, (y1 + y2) / 2, Math.abs(x2 - x1) / 2, Math.abs(y2 - y1) / 2, 0, 0, Math.PI * 2);
      context.fill();
    } else if (object.type === 'brush') {
      var points = object.points || [];
      if (!points.length) return;
      context.lineWidth = Math.max(6, Math.min(64, (Number(object.strokeWidth) || 5) * 4));
      context.beginPath();
      context.moveTo(points[0].x * output.width, points[0].y * output.height);
      points.slice(1).forEach(function(point) { context.lineTo(point.x * output.width, point.y * output.height); });
      if (points.length === 1) {
        context.lineTo(points[0].x * output.width + 0.01, points[0].y * output.height + 0.01);
      }
      context.stroke();
    }
  });
  return precisionCutoutPngData(output.toDataURL('image/png'));
}

function precisionCutoutModelRecord(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  if (value.contract !== PRECISION_CUTOUT_MODEL_INSTALL_CONTRACT || value.source_id !== PRECISION_CUTOUT_MODEL_SOURCE_ID) return null;
  if (typeof value.installed !== 'boolean' || typeof value.valid !== 'boolean' || typeof value.state !== 'string') return null;
  return value;
}

function precisionCutoutModelTaskRecord(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  if (value.contract !== PRECISION_CUTOUT_MODEL_INSTALL_CONTRACT || value.source_id !== PRECISION_CUTOUT_MODEL_SOURCE_ID) return null;
  if (typeof value.id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value.id)) return null;
  if (['queued', 'downloading', 'verifying', 'installing', 'completed', 'failed', 'cancelled'].indexOf(value.status) === -1) return null;
  return value;
}

function precisionCutoutModelTaskIsActive(task) {
  return !!(task && ['queued', 'downloading', 'verifying', 'installing'].indexOf(task.status) !== -1);
}

function precisionCutoutModelState(model, task) {
  if (precisionCutoutModelTaskIsActive(task)) return 'downloading';
  if (task && task.status === 'failed') {
    return String(task.error_code || '').toLowerCase().indexOf('hash_mismatch') !== -1 ? 'hash_mismatch' : 'error';
  }
  if (model && model.installed === true && model.valid === true && model.state === 'ready') return 'ready';
  var reason = String(model && model.reason || '').toLowerCase();
  var state = String(model && model.state || '').toLowerCase();
  if (state === 'hash_mismatch' || reason.indexOf('hash_mismatch') !== -1) return 'hash_mismatch';
  if (model && model.installed === false && (state === 'missing' || reason.indexOf('missing') !== -1 || reason.indexOf('not_installed') !== -1)) return 'missing';
  return 'error';
}

function formatPrecisionCutoutModelBytes(value) {
  var bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return i18nText('creator.cutout_model_size_approx');
  if (bytes >= 1000000) return i18nText('creator.cutout_model_size_value', { size: String(Math.round(bytes / 100000) / 10) });
  if (bytes >= 1000) return i18nText('creator.cutout_model_size_kb', { size: String(Math.round(bytes / 100) / 10) });
  return i18nText('creator.cutout_model_size_bytes', { size: String(Math.round(bytes)) });
}

function precisionCutoutModelPhaseKey(task) {
  var phase = String(task && (task.phase || task.status) || '').toLowerCase();
  if (phase === 'queued') return 'creator.cutout_model_queued';
  if (phase === 'verifying') return 'creator.cutout_model_verifying';
  if (phase === 'installing') return 'creator.cutout_model_installing';
  return 'creator.cutout_model_downloading';
}

function setPrecisionCutoutModelDetailsExpanded(expanded, remember) {
  var controls = getPrecisionCutoutControls();
  var panel = controls.modelPanel;
  var toggle = controls.modelDetailsToggle;
  var details = controls.modelDetails;
  if (!panel || !toggle || !details) return false;
  var nextExpanded = expanded === true;
  if (remember !== false) precisionCutoutModelDetailsPreference = nextExpanded;
  if (!nextExpanded && typeof document !== 'undefined' && details.contains &&
      details.contains(document.activeElement) && typeof toggle.focus === 'function') {
    toggle.focus();
  }
  panel.dataset.detailsExpanded = nextExpanded ? 'true' : 'false';
  toggle.setAttribute('aria-expanded', nextExpanded ? 'true' : 'false');
  var affordance = toggle.querySelector && toggle.querySelector('.precision-cutout-model-toggle');
  if (affordance) affordance.setAttribute('aria-expanded', nextExpanded ? 'true' : 'false');
  details.classList.toggle('hidden', !nextExpanded);
  details.setAttribute('aria-hidden', nextExpanded ? 'false' : 'true');
  return nextExpanded;
}

function syncPrecisionCutoutModelDetails(state) {
  // Keep the installer compact by default; users can expand details on demand.
  // A remembered preference is respected across status refreshes.
  var expanded = precisionCutoutModelDetailsPreference === true;
  return setPrecisionCutoutModelDetailsExpanded(expanded, false);
}

function togglePrecisionCutoutModelDetails() {
  var controls = getPrecisionCutoutControls();
  var panel = controls.modelPanel;
  var toggle = controls.modelDetailsToggle;
  if (!panel || !toggle) return false;
  return setPrecisionCutoutModelDetailsExpanded(toggle.getAttribute('aria-expanded') !== 'true', true);
}

function renderPrecisionCutoutModelInstaller(model, task, overrideState) {
  var controls = getPrecisionCutoutControls();
  var panel = controls.modelPanel;
  if (!panel || !controls.modelStatus) return '';
  var state = overrideState || precisionCutoutModelState(model, task);
  var activeTask = precisionCutoutModelTaskIsActive(task) ? task : null;
  var downloadSupported = !!(model && model.download_supported === true && model.install_supported === true);
  var progress = activeTask ? Math.max(0, Math.min(100, Number(activeTask.progress) || 0)) : 0;
  var statusKey = state === 'checking' ? 'creator.cutout_model_checking'
    : state === 'missing' && !downloadSupported ? 'creator.cutout_model_download_unavailable'
    : state === 'missing' ? 'creator.cutout_model_missing'
    : state === 'downloading' ? precisionCutoutModelPhaseKey(activeTask)
    : state === 'hash_mismatch' ? 'creator.cutout_model_hash_mismatch'
    : state === 'ready' ? 'creator.cutout_model_ready'
    : 'creator.cutout_model_error';

  panel.dataset.state = state;
  panel.setAttribute('aria-busy', (state === 'checking' || state === 'downloading' || precisionCutoutModelMutationPending) ? 'true' : 'false');
  syncPrecisionCutoutModelDetails(state);
  controls.modelStatus.textContent = i18nText(statusKey, { progress: String(Math.round(progress)) });
  if (controls.modelSource) controls.modelSource.textContent = PRECISION_CUTOUT_MODEL_SOURCE_ID;
  if (controls.modelSize) controls.modelSize.textContent = formatPrecisionCutoutModelBytes(model && model.size_bytes);
  if (controls.modelPath) controls.modelPath.textContent = PRECISION_CUTOUT_MODEL_RELATIVE_PATH;

  if (controls.modelProgress) controls.modelProgress.classList.toggle('hidden', state !== 'downloading');
  if (controls.modelProgressBar) controls.modelProgressBar.value = progress;
  if (controls.modelProgressText) {
    var downloaded = Number(activeTask && activeTask.downloaded_bytes);
    var total = Number(activeTask && activeTask.total_bytes);
    controls.modelProgressText.textContent = Number.isFinite(downloaded) && Number.isFinite(total) && total > 0
      ? formatPrecisionCutoutModelBytes(downloaded) + ' / ' + formatPrecisionCutoutModelBytes(total)
      : Math.round(progress) + '%';
  }

  var installVisible = state === 'missing';
  var cancelVisible = state === 'downloading';
  var retryVisible = state === 'hash_mismatch' || state === 'error';
  var corruptVisible = state === 'hash_mismatch';
  var deleteVisible = state === 'ready';
  if (controls.modelInstallButton) {
    controls.modelInstallButton.classList.toggle('hidden', !installVisible);
    controls.modelInstallButton.disabled = precisionCutoutModelMutationPending || !downloadSupported;
    controls.modelInstallButton.textContent = i18nText(downloadSupported ? 'creator.cutout_model_install' : 'creator.cutout_model_install_unavailable');
  }
  if (controls.modelCancelButton) {
    controls.modelCancelButton.classList.toggle('hidden', !cancelVisible);
    controls.modelCancelButton.disabled = precisionCutoutModelMutationPending || !activeTask;
  }
  if (controls.modelRetryButton) {
    controls.modelRetryButton.classList.toggle('hidden', !retryVisible);
    controls.modelRetryButton.disabled = precisionCutoutModelMutationPending || !downloadSupported;
    controls.modelRetryButton.textContent = i18nText(!downloadSupported ? 'creator.cutout_model_install_unavailable' : state === 'hash_mismatch' ? 'creator.cutout_model_remove_retry' : 'creator.cutout_model_retry');
  }
  if (controls.modelRemoveCorruptButton) {
    controls.modelRemoveCorruptButton.classList.toggle('hidden', !corruptVisible);
    controls.modelRemoveCorruptButton.disabled = precisionCutoutModelMutationPending;
  }
  if (controls.modelDeleteButton) {
    controls.modelDeleteButton.classList.toggle('hidden', !deleteVisible);
    controls.modelDeleteButton.disabled = precisionCutoutModelMutationPending;
  }
  return state;
}

function stopPrecisionCutoutModelPolling(invalidate) {
  if (precisionCutoutModelPollTimer !== null) {
    clearTimeout(precisionCutoutModelPollTimer);
    precisionCutoutModelPollTimer = null;
  }
  precisionCutoutModelTaskId = '';
  if (invalidate !== false) precisionCutoutModelTaskToken += 1;
}

function disablePrecisionCutoutForModel() {
  precisionCutoutProbeToken += 1;
  precisionCutoutCapability = null;
  if (typeof renderPrecisionCutoutAdapterPicker === 'function') renderPrecisionCutoutAdapterPicker(null);
  if (!precisionCutoutPending) setPrecisionCutoutUi('creator.cutout_unconfigured_clear', 'unavailable');
}

function pollPrecisionCutoutModelTask(taskId, taskToken) {
  if (!taskId || taskToken !== precisionCutoutModelTaskToken || taskId !== precisionCutoutModelTaskId) return Promise.resolve(false);
  return _authFetch('/api/image-tools/cutout/model/download/' + encodeURIComponent(taskId)).then(readPrecisionCutoutResponse).then(function(result) {
    if (taskToken !== precisionCutoutModelTaskToken || taskId !== precisionCutoutModelTaskId) return false;
    if (!result.ok) throw precisionCutoutResponseError(result);
    var task = precisionCutoutModelTaskRecord(result.data && result.data.task);
    if (!task || task.id !== taskId) throw new Error('invalid cutout model task response');
    precisionCutoutModelTask = task;
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, task);
    if (precisionCutoutModelTaskIsActive(task)) {
      precisionCutoutModelPollTimer = setTimeout(function() {
        precisionCutoutModelPollTimer = null;
        pollPrecisionCutoutModelTask(taskId, taskToken);
      }, PRECISION_CUTOUT_MODEL_POLL_INTERVAL_MS);
      return true;
    }
    stopPrecisionCutoutModelPolling(false);
    if (task.status === 'completed' || task.status === 'cancelled') return refreshPrecisionCutoutModelStatus();
    disablePrecisionCutoutForModel();
    return false;
  }).catch(function() {
    if (taskToken !== precisionCutoutModelTaskToken || taskId !== precisionCutoutModelTaskId) return false;
    stopPrecisionCutoutModelPolling(false);
    precisionCutoutModelTask = { status: 'failed', error_code: 'model_task_status_failed' };
    disablePrecisionCutoutForModel();
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask, 'error');
    return false;
  });
}

function monitorPrecisionCutoutModelTask(task) {
  var validTask = precisionCutoutModelTaskRecord(task);
  if (!validTask || !precisionCutoutModelTaskIsActive(validTask)) return false;
  stopPrecisionCutoutModelPolling();
  precisionCutoutModelTask = validTask;
  precisionCutoutModelTaskId = validTask.id;
  var taskToken = precisionCutoutModelTaskToken;
  renderPrecisionCutoutModelInstaller(precisionCutoutModel, validTask);
  pollPrecisionCutoutModelTask(validTask.id, taskToken);
  return true;
}

function refreshPrecisionCutoutModelStatus() {
  var refreshToken = ++precisionCutoutModelRefreshToken;
  renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask, 'checking');
  return _authFetch('/api/image-tools/cutout/model', { cache: 'no-store' }).then(readPrecisionCutoutResponse).then(function(result) {
    if (refreshToken !== precisionCutoutModelRefreshToken) return false;
    if (!result.ok) throw precisionCutoutResponseError(result);
    var model = precisionCutoutModelRecord(result.data);
    if (!model) throw new Error('invalid cutout model response');
    precisionCutoutModel = model;
    var activeTask = precisionCutoutModelTaskRecord(model.active_task);
    precisionCutoutModelTask = activeTask;
    if (activeTask && precisionCutoutModelTaskIsActive(activeTask)) {
      disablePrecisionCutoutForModel();
      monitorPrecisionCutoutModelTask(activeTask);
      return true;
    }
    stopPrecisionCutoutModelPolling();
    renderPrecisionCutoutModelInstaller(model, null);
    if (precisionCutoutModelState(model, null) === 'ready') {
      return updatePrecisionCutoutAvailability().then(function(capability) {
        return precisionCutoutIsExecutable(capability);
      });
    }
    disablePrecisionCutoutForModel();
    return true;
  }).catch(function() {
    if (refreshToken !== precisionCutoutModelRefreshToken) return false;
    stopPrecisionCutoutModelPolling();
    precisionCutoutModelTask = null;
    disablePrecisionCutoutForModel();
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, null, 'error');
    return false;
  });
}

// A failed model-status refresh must not strand the capability UI in a
// permanent checking state. The capability endpoint is independently
// authoritative for whether a local cutout request may be enabled.
function refreshPrecisionCutoutSetup() {
  if (precisionCutoutModelMutationPending || precisionCutoutModelTaskIsActive(precisionCutoutModelTask) || precisionCutoutUiBusy()) return Promise.resolve(false);
  return refreshPrecisionCutoutModelStatus().then(function(refreshed) {
    if (refreshed) return true;
    return updatePrecisionCutoutAvailability().then(function(capability) {
      return precisionCutoutIsExecutable(capability);
    });
  });
}

function precisionCutoutModelMutationPayload() {
  return {
    contract: PRECISION_CUTOUT_MODEL_INSTALL_CONTRACT,
    source_id: PRECISION_CUTOUT_MODEL_SOURCE_ID,
    confirmed: true
  };
}

function submitPrecisionCutoutModelDownload() {
  if (precisionCutoutModelMutationPending || !precisionCutoutModel || precisionCutoutModel.download_supported !== true || precisionCutoutModel.install_supported !== true) return Promise.resolve(false);
  precisionCutoutModelMutationPending = true;
  renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask);
  return _authFetch('/api/image-tools/cutout/model/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(precisionCutoutModelMutationPayload())
  }).then(readPrecisionCutoutResponse).then(function(result) {
    if (!result.ok || result.data.ok !== true) throw precisionCutoutResponseError(result);
    var task = precisionCutoutModelTaskRecord(result.data.task);
    if (!task || !precisionCutoutModelTaskIsActive(task)) throw new Error('invalid cutout model download task');
    precisionCutoutModelTask = task;
    disablePrecisionCutoutForModel();
    monitorPrecisionCutoutModelTask(task);
    return true;
  }).catch(function() {
    precisionCutoutModelTask = { status: 'failed', error_code: 'model_download_request_failed' };
    disablePrecisionCutoutForModel();
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask, 'error');
    return false;
  }).finally(function() {
    precisionCutoutModelMutationPending = false;
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask);
  });
}

function requestPrecisionCutoutModelInstall() {
  if (precisionCutoutModelMutationPending || precisionCutoutModelTaskIsActive(precisionCutoutModelTask)) return Promise.resolve(false);
  if (!precisionCutoutModel || precisionCutoutModel.download_supported !== true || precisionCutoutModel.install_supported !== true) return Promise.resolve(false);
  if (!confirm(i18nText('creator.cutout_model_install_confirm', {
    size: formatPrecisionCutoutModelBytes(precisionCutoutModel.size_bytes),
    path: PRECISION_CUTOUT_MODEL_RELATIVE_PATH
  }))) return Promise.resolve(false);
  return submitPrecisionCutoutModelDownload();
}

function deletePrecisionCutoutModel(mode, skipConfirm) {
  if (precisionCutoutModelMutationPending || precisionCutoutModelTaskIsActive(precisionCutoutModelTask)) return Promise.resolve(false);
  var confirmKey = mode === 'corrupt' ? 'creator.cutout_model_remove_corrupt_confirm' : 'creator.cutout_model_delete_confirm';
  if (skipConfirm !== true && !confirm(i18nText(confirmKey, { path: PRECISION_CUTOUT_MODEL_RELATIVE_PATH }))) return Promise.resolve(false);
  stopPrecisionCutoutModelPolling();
  precisionCutoutModelMutationPending = true;
  disablePrecisionCutoutForModel();
  renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask);
  return _authFetch('/api/image-tools/cutout/model/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(precisionCutoutModelMutationPayload())
  }).then(readPrecisionCutoutResponse).then(function(result) {
    if (!result.ok || result.data.ok !== true || result.data.deleted !== true) throw precisionCutoutResponseError(result);
    var model = precisionCutoutModelRecord(result.data.model);
    if (!model) throw new Error('invalid cutout model delete response');
    precisionCutoutModel = model;
    precisionCutoutModelTask = null;
    renderPrecisionCutoutModelInstaller(model, null);
    return true;
  }).catch(function() {
    precisionCutoutModelTask = { status: 'failed', error_code: 'model_delete_request_failed' };
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask, 'error');
    return false;
  }).finally(function() {
    precisionCutoutModelMutationPending = false;
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask);
  });
}

function retryPrecisionCutoutModelDownload() {
  if (precisionCutoutModelMutationPending || precisionCutoutModelTaskIsActive(precisionCutoutModelTask)) return Promise.resolve(false);
  if (!precisionCutoutModel) return refreshPrecisionCutoutModelStatus();
  if (precisionCutoutModel.download_supported !== true || precisionCutoutModel.install_supported !== true) return Promise.resolve(false);
  var state = precisionCutoutModelState(precisionCutoutModel, precisionCutoutModelTask);
  if (state === 'hash_mismatch') {
    if (!confirm(i18nText('creator.cutout_model_remove_retry_confirm', {
      size: formatPrecisionCutoutModelBytes(precisionCutoutModel.size_bytes),
      path: PRECISION_CUTOUT_MODEL_RELATIVE_PATH
    }))) return Promise.resolve(false);
    return deletePrecisionCutoutModel('corrupt', true).then(function(deleted) {
      return deleted ? submitPrecisionCutoutModelDownload() : false;
    });
  }
  return requestPrecisionCutoutModelInstall();
}

function cancelPrecisionCutoutModelDownload() {
  var task = precisionCutoutModelTaskRecord(precisionCutoutModelTask);
  if (precisionCutoutModelMutationPending || !task || !precisionCutoutModelTaskIsActive(task)) return Promise.resolve(false);
  var taskId = task.id;
  stopPrecisionCutoutModelPolling();
  precisionCutoutModelMutationPending = true;
  renderPrecisionCutoutModelInstaller(precisionCutoutModel, task, 'downloading');
  return _authFetch('/api/image-tools/cutout/model/download/' + encodeURIComponent(taskId), { method: 'DELETE' }).then(readPrecisionCutoutResponse).then(function(result) {
    if (!result.ok) throw precisionCutoutResponseError(result);
    var cancelledTask = precisionCutoutModelTaskRecord(result.data && result.data.task);
    if (!cancelledTask || cancelledTask.id !== taskId || cancelledTask.status !== 'cancelled') throw new Error('invalid cutout model cancellation response');
    precisionCutoutModelTask = cancelledTask;
    return refreshPrecisionCutoutModelStatus();
  }).catch(function() {
    precisionCutoutModelTask = task;
    return refreshPrecisionCutoutModelStatus();
  }).finally(function() {
    precisionCutoutModelMutationPending = false;
    renderPrecisionCutoutModelInstaller(precisionCutoutModel, precisionCutoutModelTask);
  });
}

function precisionCutoutFeatherRadius() {
  var feather = getPrecisionCutoutControls().feather;
  var value = Number(feather && feather.value);
  return Number.isFinite(value) && value >= 0 && value <= PRECISION_CUTOUT_MAX_FEATHER ? value : null;
}

function precisionCutoutRestoreMinAlpha() {
  var control = getPrecisionCutoutControls().restoreMinAlpha;
  var value = Number(control && control.value);
  return Number.isFinite(value) && value >= 0 && value <= 255 ? Math.round(value) : null;
}

function updatePrecisionCutoutRefineControls() {
  var controls = getPrecisionCutoutControls();
  if (!controls.refineButton && !controls.feather && !controls.useSelection && !controls.restoreMode && !controls.restoreMinAlpha && !controls.cancelButton) return;
  var radius = precisionCutoutFeatherRadius();
  var selectionCount = precisionCutoutSelectionObjects().length;
  var canvas = document.getElementById('precisionAnnotationCanvas');
  var transparentVersion = precisionCutoutSelectedTransparentVersion();
  var restoreReady = !!(transparentVersion && selectionCount > 0);
  var restoreEnabled = !!(controls.restoreMode && controls.restoreMode.checked);
  if (controls.featherValue) controls.featherValue.value = controls.featherValue.textContent = radius === null ? '0' : String(radius);
  if (controls.restoreMode) {
    controls.restoreMode.disabled = precisionCutoutUiBusy() || !restoreReady;
    if (!restoreReady) controls.restoreMode.checked = false;
    restoreEnabled = !!controls.restoreMode.checked;
  }
  if (controls.useSelection) {
    controls.useSelection.disabled = precisionCutoutUiBusy() || selectionCount === 0 || restoreEnabled;
    if (!selectionCount) controls.useSelection.checked = false;
    else if (restoreEnabled) controls.useSelection.checked = true;
  }
  if (canvas) {
    canvas.classList.toggle('is-cutout-selection-active', !!(
      controls.useSelection && controls.useSelection.checked && selectionCount > 0
    ));
  }
  var restoreMinAlpha = precisionCutoutRestoreMinAlpha();
  if (controls.restoreMinAlphaValue) {
    var restoreAlphaText = restoreMinAlpha === null ? '255' : String(restoreMinAlpha);
    controls.restoreMinAlphaValue.value = controls.restoreMinAlphaValue.textContent = restoreAlphaText;
  }
  if (controls.restoreMinAlpha) {
    controls.restoreMinAlpha.disabled = precisionCutoutUiBusy() || !restoreReady || !restoreEnabled;
  }
  if (controls.restoreHint) {
    var restoreHintKey = !transparentVersion ? 'creator.cutout_restore_source_required' : selectionCount === 0 ? 'creator.cutout_restore_selection_empty' : 'creator.cutout_restore_hint';
    var restoreHint = i18nText(restoreHintKey, {
      count: String(selectionCount),
      alpha: String(restoreMinAlpha === null ? 255 : restoreMinAlpha)
    });
    if (restoreEnabled && transparentVersion && selectionCount > 0) {
      restoreHint = i18nText('creator.cutout_restore_ready', {
        count: String(selectionCount),
        alpha: String(restoreMinAlpha === null ? 255 : restoreMinAlpha)
      });
    }
    controls.restoreHint.textContent = restoreHint;
  }
  if (controls.selectionHint) {
    controls.selectionHint.textContent = i18nText(selectionCount ? 'creator.cutout_refine_selection_ready' : 'creator.cutout_refine_selection_empty').replace('{count}', String(selectionCount));
  }
  var selectionReady = restoreEnabled ? selectionCount > 0 : !(controls.useSelection && controls.useSelection.checked) || selectionCount > 0;
  if (controls.refineButton) {
    controls.refineButton.disabled = precisionCutoutUiBusy() || !transparentVersion || radius === null || !selectionReady || (restoreEnabled && restoreMinAlpha === null);
    controls.refineButton.setAttribute('aria-busy', precisionCutoutUiBusy() ? 'true' : 'false');
  }
  if (controls.cancelButton) {
    controls.cancelButton.classList.toggle('hidden', !precisionCutoutPending);
    controls.cancelButton.disabled = !precisionCutoutPending;
  }
}

function setPrecisionCutoutUi(key, state, values) {
  var controls = getPrecisionCutoutControls();
  var button = controls.button;
  var status = controls.status;
  if (!button || !status) return;
  status.textContent = i18nText(key, values || {});
  status.dataset.key = key;
  status.dataset.state = state || 'idle';
  status.classList.toggle('is-processing', state === 'checking' || state === 'processing');
  status.classList.toggle('is-success', state === 'success');
  status.classList.toggle('is-error', state === 'busy' || state === 'timeout' || state === 'error');
  button.dataset.state = state || 'idle';
  button.setAttribute('aria-busy', precisionCutoutUiBusy() ? 'true' : 'false');
  button.disabled = precisionCutoutUiBusy() || !precisionCutoutHasSource() || !precisionCutoutIsExecutable(precisionCutoutCapability);
  var executable = precisionCutoutIsExecutable(precisionCutoutCapability);
  [controls.simpleButton, controls.professionalRunButton].forEach(function(action) {
    if (!action) return;
    action.disabled = precisionCutoutUiBusy() || !precisionCutoutHasSource() || !executable;
    action.setAttribute('aria-busy', precisionCutoutUiBusy() ? 'true' : 'false');
  });
  updatePrecisionCutoutRefineControls();
}

function readPrecisionCutoutResponse(response) {
  return response.text().then(function(text) {
    var body = {};
    try { body = text ? JSON.parse(text) : {}; } catch (error) { body = {}; }
    var detail = body && body.detail && typeof body.detail === 'object' ? body.detail : body;
    return { ok: response.ok, status: response.status, data: detail && typeof detail === 'object' ? detail : {} };
  });
}

function precisionCutoutResponseError(result) {
  var detail = result && result.data || {};
  var error = new Error(typeof detail.message === 'string' && detail.message ? detail.message : 'HTTP ' + (result && result.status || 0));
  error.code = typeof detail.code === 'string' ? detail.code : '';
  error.status = result && result.status || 0;
  error.detail = detail;
  return error;
}

function probePrecisionCutoutCapability(signal) {
  // Capabilities change when local model files are installed or updated. Do
  // not let the browser reuse an older one-algorithm response.
  var options = { cache: 'no-store' };
  var timeoutMs = Number(typeof PRECISION_CUTOUT_CAPABILITY_TIMEOUT_MS === 'number' ? PRECISION_CUTOUT_CAPABILITY_TIMEOUT_MS : 15000);
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) timeoutMs = 15000;
  var requestController = null;
  var requestSignal = signal || null;
  var detachAbortForwarder = null;
  // Compose a caller abort signal with the local timeout when the browser
  // supports abort events. Older test shims may only expose `aborted`; in
  // that case preserve the caller signal and still fail closed on timeout.
  if (typeof AbortController === 'function' && (!signal || typeof signal.addEventListener === 'function')) {
    requestController = new AbortController();
    requestSignal = requestController.signal;
    if (signal) {
      var forwardAbort = function() {
        try { requestController.abort(); } catch (ignore) {}
      };
      if (signal.aborted === true) forwardAbort();
      else if (typeof signal.addEventListener === 'function') {
        signal.addEventListener('abort', forwardAbort);
        detachAbortForwarder = function() {
          if (typeof signal.removeEventListener === 'function') signal.removeEventListener('abort', forwardAbort);
        };
      }
    }
  } else if (signal) {
    requestSignal = signal;
  } else if (typeof AbortController === 'function') {
    requestController = new AbortController();
    requestSignal = requestController.signal;
  }
  if (requestSignal) options.signal = requestSignal;
  var timeoutId = null;
  var request = Promise.resolve().then(function() {
    return _authFetch('/api/image-tools/cutout/capabilities', options);
  }).then(readPrecisionCutoutResponse).then(function(result) {
    if (!result.ok && !(result.data && result.data.available === false)) throw precisionCutoutResponseError(result);
    return result.data;
  });
  var timeout = new Promise(function(resolve, reject) {
    timeoutId = setTimeout(function() {
      if (requestController) {
        try { requestController.abort(); } catch (ignore) {}
      }
      var error = new Error('cutout capability probe timed out');
      error.code = 'cutout_timeout';
      reject(error);
    }, timeoutMs);
  });
  return Promise.race([request, timeout]).then(function(result) {
    if (timeoutId !== null) clearTimeout(timeoutId);
    if (detachAbortForwarder) detachAbortForwarder();
    return result;
  }, function(error) {
    if (timeoutId !== null) clearTimeout(timeoutId);
    if (detachAbortForwarder) detachAbortForwarder();
    throw error;
  });
}

function updatePrecisionCutoutAvailability() {
  var probeToken = ++precisionCutoutProbeToken;
  var sourceGeneration = precisionSourceLoadGeneration;
  if (precisionCutoutAvailabilityAbortController) {
    try { precisionCutoutAvailabilityAbortController.abort(); } catch (ignore) {}
  }
  var availabilityAbortController = typeof AbortController === 'function' ? new AbortController() : null;
  precisionCutoutAvailabilityAbortController = availabilityAbortController;
  if (!precisionCutoutPending) {
    precisionCutoutCapability = null;
    setPrecisionCutoutUi('creator.cutout_checking', 'checking');
  }
  return probePrecisionCutoutCapability(availabilityAbortController && availabilityAbortController.signal).then(function(capability) {
    if (sourceGeneration !== precisionSourceLoadGeneration || probeToken !== precisionCutoutProbeToken) return capability;
    precisionCutoutCapability = capability;
    renderPrecisionCutoutAdapterPicker(capability);
    if (precisionCutoutPending) return capability;
    if (!precisionCutoutIsExecutable(capability)) {
      setPrecisionCutoutUi('creator.cutout_unconfigured_clear', 'unavailable');
    } else if (!precisionCutoutHasSource()) {
      setPrecisionCutoutUi('creator.cutout_source_required', 'source-required');
    } else {
      setPrecisionCutoutUi('creator.cutout_ready', 'ready');
    }
    return capability;
  }).catch(function(error) {
    if (sourceGeneration !== precisionSourceLoadGeneration || probeToken !== precisionCutoutProbeToken) return null;
    precisionCutoutCapability = null;
    renderPrecisionCutoutAdapterPicker(null);
    if (!precisionCutoutPending) setPrecisionCutoutUi('creator.cutout_check_failed', 'error');
    return null;
  }).finally(function() {
    if (precisionCutoutAvailabilityAbortController === availabilityAbortController) precisionCutoutAvailabilityAbortController = null;
  });
}

function precisionCutoutResultSource(result, expectedWidth, expectedHeight) {
  if (!result
      || result.contract !== PRECISION_CUTOUT_CONTRACT
      || result.success !== true
      || result.status !== 'completed'
      || result.source_preserved !== true
      || result.transparent !== true
      || result.preview_background !== 'checkerboard') return '';
  var adapter = precisionCutoutAdapterId(result.adapter);
  var fallbackFrom = result.fallback_from == null ? '' : precisionCutoutAdapterId(result.fallback_from);
  if (!adapter || (result.fallback_from != null && !fallbackFrom) || (fallbackFrom && fallbackFrom === adapter)) return '';
  if (Array.isArray(result.adapters) && result.adapters.indexOf(adapter) === -1) return '';
  var width = Number(result.width);
  var height = Number(result.height);
  if (!Number.isInteger(width) || !Number.isInteger(height) || width !== expectedWidth || height !== expectedHeight) return '';
  var imageData = precisionCutoutPngData(result.image_data);
  var galleryUrl = precisionCutoutGalleryUrl(result);
  return imageData && galleryUrl ? galleryUrl : '';
}

function appendPrecisionCutoutVersion(result, expectedWidth, expectedHeight, parentId) {
  var source = precisionCutoutResultSource(result, expectedWidth, expectedHeight);
  return source ? appendPrecisionEditImageVersion(source, parentId, {
    imageData: result.image_data,
    transparent: true,
    previewBackground: 'checkerboard',
    operation: 'cutout',
    adapter: result.adapter,
    fallbackFrom: result.fallback_from,
    width: expectedWidth,
    height: expectedHeight,
    autoSetBase: false
  }) === true : false;
}

function startPrecisionCutout() {
  if (precisionCutoutPending) return Promise.resolve(false);
  if (!precisionCutoutHasSource()) {
    setPrecisionCutoutUi('creator.cutout_source_required', 'source-required');
    return Promise.resolve(false);
  }
  var requestSource = precisionEditSourceImageData;
  var requestWidth = precisionEditSourceWidth;
  var requestHeight = precisionEditSourceHeight;
  var requestParentId = precisionEditSession.baseVersionId || 'original';
  var requestGeneration = precisionSourceLoadGeneration;
  var operationToken = ++precisionCutoutOperationToken;
  var abortController = typeof AbortController === 'function' ? new AbortController() : null;
  precisionCutoutAbortController = abortController;
  precisionCutoutPending = true;
  setPrecisionCutoutUi('creator.cutout_checking', 'checking');

  return probePrecisionCutoutCapability(abortController && abortController.signal).then(function(capability) {
    if (operationToken !== precisionCutoutOperationToken || requestGeneration !== precisionSourceLoadGeneration) return null;
    precisionCutoutCapability = capability;
    var selectedAdapter = renderPrecisionCutoutAdapterPicker(capability);
    if (!selectedAdapter || !precisionCutoutIsExecutable(capability)) {
      setPrecisionCutoutUi('creator.cutout_unconfigured_clear', 'unavailable');
      return null;
    }
    setPrecisionCutoutUi('creator.cutout_processing', 'processing');
    return _authFetch('/api/image-tools/cutout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contract: PRECISION_CUTOUT_CONTRACT,
        image_data: requestSource,
        adapter: selectedAdapter.adapter,
        algorithm: selectedAdapter.algorithm
      }),
      signal: abortController && abortController.signal
    }).then(readPrecisionCutoutResponse).then(function(result) {
      if (operationToken !== precisionCutoutOperationToken || requestGeneration !== precisionSourceLoadGeneration) return null;
      if (!result.ok) throw precisionCutoutResponseError(result);
      return result.data;
    });
  }).then(function(result) {
    if (operationToken !== precisionCutoutOperationToken || requestGeneration !== precisionSourceLoadGeneration) return false;
    if (!result) return false;
    if (precisionEditSourceImageData !== requestSource || precisionEditSourceWidth !== requestWidth || precisionEditSourceHeight !== requestHeight) {
      setPrecisionCutoutUi('creator.cutout_source_changed', 'error');
      return false;
    }
    if (!appendPrecisionCutoutVersion(result, requestWidth, requestHeight, requestParentId)) {
      setPrecisionCutoutUi('creator.cutout_result_invalid', 'error');
      return false;
    }
    var actualAdapter = precisionCutoutAdapterId(result.adapter);
    var fallbackFrom = result.fallback_from == null ? '' : precisionCutoutAdapterId(result.fallback_from);
    var completionKey = fallbackFrom ? 'creator.cutout_completed_fallback' : 'creator.cutout_completed';
    var completionValues = fallbackFrom ? { adapter: actualAdapter, requested: fallbackFrom } : {};
    setPrecisionCutoutUi(completionKey, 'success', completionValues);
    setStatus(i18nText(completionKey, completionValues));
    return true;
  }).catch(function(error) {
    if (operationToken !== precisionCutoutOperationToken || requestGeneration !== precisionSourceLoadGeneration) return false;
    if (error && error.name === 'AbortError') {
      setPrecisionCutoutUi('creator.cutout_cancelled', 'cancelled');
    } else if (error && error.code === 'cutout_busy') {
      setPrecisionCutoutUi('creator.cutout_busy', 'busy');
    } else if (error && (error.code === 'cutout_timeout' || error.status === 504)) {
      setPrecisionCutoutUi('creator.cutout_timeout', 'timeout');
    } else if (error && error.detail && error.detail.available === false && error.status === 503) {
      precisionCutoutCapability = error.detail;
      setPrecisionCutoutUi('creator.cutout_unconfigured_clear', 'unavailable');
    } else {
      setPrecisionCutoutUi('creator.cutout_failed', 'error');
    }
    return false;
  }).finally(function() {
    if (operationToken !== precisionCutoutOperationToken) return;
    precisionCutoutPending = false;
    if (precisionCutoutAbortController === abortController) precisionCutoutAbortController = null;
    if (requestGeneration !== precisionSourceLoadGeneration) return;
    var dataset = (getPrecisionCutoutControls().status || { dataset: {} }).dataset;
    setPrecisionCutoutUi(dataset.key || 'creator.cutout_ready', dataset.state || 'ready');
  });
}

function precisionCutoutRefineResultSource(result, expectedWidth, expectedHeight, expectedParentId, expectedFeatherRadius, expectedRestoreMode, expectedRestoreMinAlpha, expectedSelection) {
  if (!result
      || result.contract !== PRECISION_CUTOUT_REFINE_CONTRACT
      || result.success !== true
      || result.status !== 'completed'
      || result.operation !== 'alpha_refine'
      || result.local_only !== true
      || result.source_preserved !== true
      || result.transparent !== true
      || result.preview_background !== 'checkerboard'
      || result.parent_version_id !== expectedParentId) return '';
  var width = Number(result.width);
  var height = Number(result.height);
  var featherRadius = Number(result.feather_radius);
  var restoreMode = result.restore_mode === true;
  var restoreApplied = result.restore_applied === true;
  var restoreMinAlpha = Number(result.restore_min_alpha);
  if (!Number.isInteger(width) || !Number.isInteger(height) || width !== expectedWidth || height !== expectedHeight) return '';
  if (!Number.isFinite(featherRadius) || featherRadius < 0 || featherRadius > PRECISION_CUTOUT_MAX_FEATHER || Math.abs(featherRadius - expectedFeatherRadius) > 0.000001) return '';
  if (!expectedSelection && result.selection_mask_contract !== null) return '';
  if (result.selection_applied !== expectedSelection) return '';
  if (expectedSelection && result.selection_mask_contract !== PRECISION_CUTOUT_SELECTION_MASK_CONTRACT) return '';
  if (restoreMode !== !!expectedRestoreMode || restoreApplied !== !!expectedRestoreMode) return '';
  if (expectedRestoreMode) {
    if (!Number.isFinite(restoreMinAlpha) || restoreMinAlpha < 0 || restoreMinAlpha > 255 || Math.round(restoreMinAlpha) !== expectedRestoreMinAlpha) return '';
  } else if (result.restore_min_alpha !== null) {
    return '';
  }
  if (typeof result.alpha_changed !== 'boolean') return '';
  if (!Array.isArray(result.alpha_extrema) || result.alpha_extrema.length !== 2 || result.alpha_extrema.some(function(value) {
    return !Number.isInteger(value) || value < 0 || value > 255;
  })) return '';
  if (typeof result.version_id !== 'string' || !/^cutout-refine-[A-Za-z0-9._:-]{1,127}$/.test(result.version_id)) return '';
  var imageData = precisionCutoutPngData(result.image_data);
  var galleryUrl = precisionCutoutGalleryUrl(result);
  return imageData && galleryUrl ? galleryUrl : '';
}

function appendPrecisionCutoutRefineVersion(result, expectedWidth, expectedHeight, parentId, featherRadius, restoreMode, restoreMinAlpha, selectionApplied) {
  var source = precisionCutoutRefineResultSource(result, expectedWidth, expectedHeight, parentId, featherRadius, restoreMode, restoreMinAlpha, selectionApplied);
  return source ? appendPrecisionEditImageVersion(source, parentId, {
    imageData: result.image_data,
    transparent: true,
    previewBackground: 'checkerboard',
    operation: 'alpha_refine',
    remoteVersionId: result.version_id,
    restoreMode: result.restore_mode === true,
    restoreMinAlpha: result.restore_mode === true && Number.isFinite(Number(result.restore_min_alpha)) ? Math.round(Number(result.restore_min_alpha)) : null,
    selectionApplied: selectionApplied === true,
    width: expectedWidth,
    height: expectedHeight,
    autoSetBase: false
  }) === true : false;
}

function startPrecisionCutoutRefine() {
  if (precisionCutoutPending) return Promise.resolve(false);
  var selected = precisionCutoutSelectedTransparentVersion();
  if (!selected) {
    setPrecisionCutoutUi('creator.cutout_refine_source_required', 'error');
    return Promise.resolve(false);
  }
  var controls = getPrecisionCutoutControls();
  var featherRadius = precisionCutoutFeatherRadius();
  if (featherRadius === null) {
    setPrecisionCutoutUi('creator.cutout_refine_feather_invalid', 'error');
    return Promise.resolve(false);
  }
  var restoreMode = !!(controls.restoreMode && controls.restoreMode.checked);
  var restoreMinAlpha = restoreMode ? precisionCutoutRestoreMinAlpha() : null;
  if (restoreMode && restoreMinAlpha === null) {
    setPrecisionCutoutUi('creator.cutout_restore_min_alpha_invalid', 'error');
    return Promise.resolve(false);
  }
  var selectionCount = precisionCutoutSelectionObjects().length;
  var useSelection = !!(controls.useSelection && controls.useSelection.checked);
  var selectionMask = (useSelection || restoreMode) ? exportPrecisionCutoutSelectionMask() : '';
  if ((useSelection || restoreMode) && !selectionMask) {
    setPrecisionCutoutUi(restoreMode ? 'creator.cutout_restore_selection_required' : 'creator.cutout_refine_selection_empty', 'error');
    return Promise.resolve(false);
  }
  var selectionApplied = !!selectionMask;
  var requestSource = selected.imageData;
  var requestWidth = selected.width;
  var requestHeight = selected.height;
  var requestParentId = selected.id;
  var requestGeneration = precisionSourceLoadGeneration;
  var requestBaseSource = precisionEditSourceImageData;
  var requestSessionSource = precisionEditSession.source && precisionEditSession.source.data;
  var operationToken = ++precisionCutoutOperationToken;
  var abortController = typeof AbortController === 'function' ? new AbortController() : null;
  precisionCutoutAbortController = abortController;
  precisionCutoutPending = true;
  setPrecisionCutoutUi(restoreMode ? 'creator.cutout_restore_processing' : 'creator.cutout_refine_processing', 'processing');
  var payload = {
    contract: PRECISION_CUTOUT_REFINE_CONTRACT,
    image_data: requestSource,
    feather_radius: featherRadius,
    parent_version_id: requestParentId
  };
  if (selectionApplied) {
    payload.selection_mask_data = selectionMask;
    payload.selection_mask_contract = PRECISION_CUTOUT_SELECTION_MASK_CONTRACT;
  }
  if (restoreMode) {
    payload.restore_mode = true;
    payload.restore_source_image_data = requestBaseSource;
    payload.restore_min_alpha = restoreMinAlpha;
  }
  return _authFetch('/api/image-tools/cutout/refine', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: abortController && abortController.signal
  }).then(readPrecisionCutoutResponse).then(function(result) {
    if (operationToken !== precisionCutoutOperationToken || requestGeneration !== precisionSourceLoadGeneration) return null;
    if (!result.ok) throw precisionCutoutResponseError(result);
    return result.data;
  }).then(function(result) {
    if (operationToken !== precisionCutoutOperationToken || requestGeneration !== precisionSourceLoadGeneration) return false;
    if (!result) return false;
    if (precisionEditSourceImageData !== requestBaseSource || !precisionEditSession.source || precisionEditSession.source.data !== requestSessionSource) {
      setPrecisionCutoutUi('creator.cutout_source_changed', 'error');
      return false;
    }
    if (!appendPrecisionCutoutRefineVersion(result, requestWidth, requestHeight, requestParentId, featherRadius, restoreMode, restoreMinAlpha, selectionApplied)) {
      setPrecisionCutoutUi('creator.cutout_result_invalid', 'error');
      return false;
    }
    if (restoreMode) {
      setPrecisionCutoutUi('creator.cutout_restore_completed', 'success');
      setStatus(i18nText('creator.cutout_restore_completed', {
        count: String(selectionCount),
        alpha: String(restoreMinAlpha)
      }));
    } else {
      setPrecisionCutoutUi('creator.cutout_refine_completed', 'success');
      setStatus(i18nText('creator.cutout_refine_completed'));
    }
    return true;
  }).catch(function(error) {
    if (operationToken !== precisionCutoutOperationToken || requestGeneration !== precisionSourceLoadGeneration) return false;
    if (error && error.name === 'AbortError') setPrecisionCutoutUi('creator.cutout_cancelled', 'cancelled');
    else setPrecisionCutoutUi(restoreMode ? 'creator.cutout_restore_failed' : 'creator.cutout_refine_failed', 'error');
    return false;
  }).finally(function() {
    if (operationToken !== precisionCutoutOperationToken) return;
    precisionCutoutPending = false;
    if (precisionCutoutAbortController === abortController) precisionCutoutAbortController = null;
    if (requestGeneration !== precisionSourceLoadGeneration) return;
    var dataset = (getPrecisionCutoutControls().status || { dataset: {} }).dataset;
    setPrecisionCutoutUi(dataset.key || 'creator.cutout_ready', dataset.state || 'ready');
  });
}

function cancelPrecisionCutoutOperation() {
  if (!precisionCutoutPending) return false;
  precisionCutoutOperationToken += 1;
  if (precisionCutoutAbortController) {
    try { precisionCutoutAbortController.abort(); } catch (ignore) {}
    precisionCutoutAbortController = null;
  }
  precisionCutoutPending = false;
  setPrecisionCutoutUi('creator.cutout_cancelled', 'cancelled');
  setStatus(i18nText('creator.cutout_cancelled'));
  return true;
}

function exportPrecisionEditAnnotationImage() {
  if (!precisionEditSourceImage || !precisionEditSourceWidth || !precisionEditSourceHeight) return null;
  var output = document.createElement('canvas');
  output.width = precisionEditSourceWidth;
  output.height = precisionEditSourceHeight;
  var context = output.getContext('2d');
  context.drawImage(precisionEditSourceImage, 0, 0, output.width, output.height);
  precisionEditObjects.forEach(function(object) { drawPrecisionEditObject(context, object, output.width, output.height, false); });
  return output.toDataURL('image/png');
}

function buildPrecisionEditAnnotationData() {
  return {
    contract: PRECISION_ANNOTATION_CONTRACT,
    coordinate_space: 'normalized-0-1',
    source_width: precisionEditSourceWidth,
    source_height: precisionEditSourceHeight,
    objects: precisionEditObjects.map(normalizePrecisionEditObject)
  };
}

function setPrecisionEditAnnotationsVisible(visible) {
  precisionEditAnnotationsVisible = !!visible;
  renderPrecisionEditCanvas();
}

function undoPrecisionEdit() {
  if (!precisionEditHistory.length) return;
  precisionEditRedo.push(precisionEditClone(precisionEditObjects));
  precisionEditObjects = precisionEditHistory.pop();
  precisionEditSelectedId = null;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
}

function redoPrecisionEdit() {
  if (!precisionEditRedo.length) return;
  precisionEditHistory.push(precisionEditClone(precisionEditObjects));
  precisionEditObjects = precisionEditRedo.pop();
  precisionEditSelectedId = null;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
}

function clearPrecisionEdit() {
  if (!precisionEditObjects.length) return;
  capturePrecisionEditHistory();
  precisionEditObjects = [];
  precisionEditSelectedId = null;
  renderPrecisionEditCanvas();
  updatePrecisionEditControls();
}

function getPrecisionEditReadiness() {
  if (typeof precisionBaseVersionSwitchPending !== 'undefined' && precisionBaseVersionSwitchPending) return { ready: false, message: i18nText('common.loading') };
  if (!precisionEditSourceImageData) return { ready: false, message: i18nText('creator.precision_source_required') };
  var selectionMode = typeof precisionEditSelectionMode === 'string' && precisionEditSelectionMode === 'local'
    ? 'local' : 'annotation';
  var hasLocalSelection = precisionEditObjects.some(function(object) {
    return object && ['rect', 'ellipse', 'brush'].indexOf(object.type) !== -1;
  });
  if (!precisionEditObjects.length) {
    if (precisionEditSizeMode === 'resize') {
      if (!selectedProviders.length) return { ready: false, message: i18nText('creator.model_required') };
      var pureResize = getPrecisionSizeRequest();
      if (pureResize.error) return { ready: false, message: pureResize.error };
      return { ready: true, pureResize: true, message: i18nText('creator.precision_pure_resize_ready') };
    }
    if (selectionMode === 'local') return { ready: false, message: i18nText('creator.precision_selection_local_required') };
    return { ready: false, message: i18nText('creator.precision_annotation_required') };
  }
  if (selectionMode === 'local' && !hasLocalSelection) {
    return { ready: false, message: i18nText('creator.precision_selection_local_required') };
  }
  if (precisionEditObjects.some(function(object) { return object.type !== 'text' && !precisionEditObjectInstruction(object); })) return { ready: false, message: i18nText('creator.precision_instruction_required') };
  if (!selectedProviders.length) return { ready: false, message: i18nText('creator.model_required') };
  return { ready: true, message: i18nText('creator.precision_ready') };
}

function updatePrecisionEditControls(options) {
  var undo = document.getElementById('btnPrecisionUndo');
  var redo = document.getElementById('btnPrecisionRedo');
  var clear = document.getElementById('btnPrecisionClear');
  if (undo) undo.disabled = !precisionEditHistory.length;
  if (redo) redo.disabled = !precisionEditRedo.length;
  if (clear) clear.disabled = !precisionEditObjects.length;
  syncPrecisionEditStyleControls();
  updatePrecisionStrokeWidthValue();
  if (!options || options.renderObjectList !== false) renderPrecisionEditObjectList();
  if (typeof syncPrecisionAnnotationInstructionPopover === 'function') syncPrecisionAnnotationInstructionPopover();
  updatePrecisionAnnotationPreview();
  updatePrecisionResizeCapabilityUI();
  var status = document.getElementById('precisionEditStatus');
  var readiness = getPrecisionEditReadiness();
  if (status) status.textContent = readiness.message;
  if (currentMode === 'precision_edit' && !genCurrentGenId && !genCancelRequested) {
    var generateButton = document.getElementById('btnGen');
    if (generateButton) generateButton.disabled = !readiness.ready;
  }
  updatePrecisionCutoutRefineControls();
  updatePrecisionSourceActions();
  return readiness;
}

function getPrecisionEditModelAuthorizationState() {
  var endpointSelect = document.getElementById('precisionEditProviderEndpoint');
  var select = document.getElementById('precisionEditProviderModel');
  var providerId = endpointSelect ? String(endpointSelect.value || '') : '';
  var value = select ? String(select.value || '') : '';
  var split = value.split('::');
  var valueProviderId = split.shift() || '';
  var model = split.join('::');
  var provider = (allProviders || []).find(function(item) {
    return item && String(item.id) === providerId && item.type === 'image' && item.enabled !== false && item.has_key;
  }) || null;
  var models = provider ? precisionProviderModelRecords(provider).map(function(record) { return record.id; }) : [];
  var endpointOptionCurrent = !!(endpointSelect && Array.prototype.some.call(endpointSelect.options || [], function(option) {
    return !option.disabled && option.value === providerId;
  }));
  var modelOptionCurrent = !!(select && Array.prototype.some.call(select.options || [], function(option) {
    return !option.disabled && option.value === value;
  }));
  var valid = !!(precisionEditModelPickerReady && endpointSelect && select && !endpointSelect.disabled && !select.disabled &&
    provider && providerId && valueProviderId === providerId && model && endpointOptionCurrent && modelOptionCurrent &&
    models.some(function(candidate) { return String(candidate) === model; }));
  var resolution = valid ? resolvePrecisionModelCapability(provider, model) : null;
  var authorized = !!(valid && provider.endpoint_type === 'openai' && provider.capabilities &&
    provider.capabilities.precision_edit === true && resolution && resolution.structureValid && resolution.precisionEditConfirmed);
  var compatibilityResolution = valid
    ? resolvePrecisionModelCapability(provider, PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE)
    : null;
  var compatibilityActive = !!(authorized && resolution.aliasDepth === 1 &&
    resolution.canonicalModel === PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE);
  var canUseCompatibility = !!(valid && !authorized && model !== PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE &&
    compatibilityResolution && compatibilityResolution.structureValid &&
    compatibilityResolution.precisionEditConfirmed && compatibilityResolution.sizeDeclarationValid);
  return {
    valid: valid,
    provider: valid ? provider : null,
    providerId: valid ? providerId : '',
    model: valid ? model : '',
    authorized: authorized,
    compatibilityActive: compatibilityActive,
    canUseCompatibility: canUseCompatibility,
    canAuthorize: !!(valid && !authorized && provider.endpoint_type === 'openai' && !precisionEditAuthorizationPending),
    canRevoke: !!(valid && authorized && !precisionEditAuthorizationPending)
  };
}

function updatePrecisionEditAuthorizationControl() {
  var state = getPrecisionEditModelAuthorizationState();
  var authorize = document.getElementById('btnPrecisionAuthorizeModel');
  var revoke = document.getElementById('btnPrecisionRevokeModel');
  var compatibilityRow = document.getElementById('precisionEditCompatibilityOption');
  var compatibility = document.getElementById('precisionEditGptImage2Compatibility');
  var selectionKey = state.valid ? state.providerId + '::' + state.model : '';
  if (compatibility) {
    var previousSelectionKey = compatibility.dataset ? compatibility.dataset.selectionKey : '';
    if (previousSelectionKey !== selectionKey) {
      if (compatibility.dataset) compatibility.dataset.selectionKey = selectionKey;
      compatibility.checked = state.compatibilityActive;
    } else if (state.authorized) {
      compatibility.checked = state.compatibilityActive;
    }
    if (!state.canUseCompatibility && !state.compatibilityActive) compatibility.checked = false;
    compatibility.disabled = precisionEditAuthorizationPending || state.authorized || !state.canUseCompatibility;
  }
  if (compatibilityRow && compatibilityRow.classList && typeof compatibilityRow.classList.toggle === 'function') {
    compatibilityRow.classList.toggle('hidden', !state.canUseCompatibility && !state.compatibilityActive);
  }
  if (authorize) {
    authorize.disabled = !state.canAuthorize;
    if (authorize.classList && typeof authorize.classList.toggle === 'function') {
      authorize.classList.toggle('hidden', state.valid && state.authorized);
    }
    if (typeof authorize.setAttribute === 'function') {
      authorize.setAttribute('aria-busy', precisionEditAuthorizationPending ? 'true' : 'false');
    }
  }
  if (revoke) {
    revoke.disabled = !state.canRevoke;
    if (revoke.classList && typeof revoke.classList.toggle === 'function') {
      revoke.classList.toggle('hidden', !state.authorized);
    }
    if (typeof revoke.setAttribute === 'function') {
      revoke.setAttribute('aria-busy', precisionEditAuthorizationPending ? 'true' : 'false');
    }
  }
  return state;
}

function isPrecisionModelVisibilityStorageKey(key) {
  return typeof key === 'string' &&
    PRECISION_MODEL_VISIBILITY_KEY_PATTERN.test(key) &&
    !PRECISION_MODEL_VISIBILITY_FORBIDDEN_PATTERN.test(key);
}

function precisionModelVisibilityStorageKey(providerId, modelId) {
  var providerKey = String(providerId || '').trim();
  var modelKey = String(modelId || '').trim();
  var key = providerKey + '::' + modelKey;
  return isPrecisionModelVisibilityStorageKey(key) ? key : '';
}

function sanitizePrecisionModelVisibility(raw) {
  var sanitized = {};
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return sanitized;
  Object.keys(raw).forEach(function(key) {
    if (isPrecisionModelVisibilityStorageKey(key) && raw[key] === false) sanitized[key] = false;
  });
  return sanitized;
}

function readPrecisionModelVisibility() {
  try {
    var raw = window.localStorage && window.localStorage.getItem(PRECISION_MODEL_VISIBILITY_STORAGE_KEY);
    var parsed = raw ? JSON.parse(raw) : {};
    return sanitizePrecisionModelVisibility(parsed);
  } catch (error) { return {}; }
}

function writePrecisionModelVisibility() {
  try {
    precisionEditModelVisibility = sanitizePrecisionModelVisibility(precisionEditModelVisibility);
    window.localStorage.setItem(PRECISION_MODEL_VISIBILITY_STORAGE_KEY, JSON.stringify(precisionEditModelVisibility));
    return true;
  }
  catch (error) { return false; }
}

function precisionProviderModelRecords(provider) {
  var rawModels = provider && provider.models && provider.models.length ? provider.models : (provider && provider.model ? [provider.model] : []);
  var caps = provider && provider.model_capabilities || {};
  return rawModels.map(function(raw) {
    var record = raw && typeof raw === 'object' ? raw : { id: raw };
    var id = String(record.id || record.model || record.name || '').trim();
    if (!id) return null;
    var cap = record.capabilities && typeof record.capabilities === 'object' ? record.capabilities : caps[id];
    var resolution = resolvePrecisionModelCapability(provider, id);
    var explicitlyUnavailable = resolution.capability && Object.prototype.hasOwnProperty.call(resolution.capability, 'precision_edit') && resolution.capability.precision_edit === false;
    var hasCapabilityRecord = Object.prototype.hasOwnProperty.call(caps, id);
    var unavailable = (hasCapabilityRecord && !resolution.structureValid) || explicitlyUnavailable ||
      (provider.capabilities && provider.capabilities.precision_edit === false);
    var alias = String(record.alias || record.display_name || record.label || '').trim();
    return { id: id, alias: alias, capability: cap || null, unavailable: unavailable, authorized: resolution.structureValid && resolution.precisionEditConfirmed && provider.endpoint_type === 'openai' && provider.capabilities && provider.capabilities.precision_edit === true };
  }).filter(Boolean);
}

function setPrecisionModelVisibility(key, visible) {
  if (!isPrecisionModelVisibilityStorageKey(key)) return false;
  if (visible === false) precisionEditModelVisibility[key] = false;
  else delete precisionEditModelVisibility[key];
  var saved = writePrecisionModelVisibility();
  renderPrecisionEditModelPicker();
  return saved;
}

function copyPrecisionModelVisibilityState(value) {
  var copy = {};
  Object.keys(value || {}).forEach(function(key) { copy[key] = value[key]; });
  return sanitizePrecisionModelVisibility(copy);
}

function precisionModelVisibilityLabel(record) {
  return record.alias ? record.alias + ' · ' + record.id : record.id;
}

function precisionModelVisibilityRecords(records) {
  return (records || []).filter(function(record) { return record && !record.unavailable; });
}

function precisionModelVisibilityGroups(records) {
  // Name-based navigation only; groups never grant editing capability.
  var families = [
    { id: 'gpt-image', label: 'GPT Image', match: /^gpt[-_]?image/i },
    { id: 'gemini', label: 'Gemini / Nano Banana / Imagen', match: /^(gemini|nano[-_ ]?banana|imagen)/i },
    { id: 'grok-image', label: 'Grok Image', match: /^grok-imagine-image/i },
    { id: 'qwen', label: 'Qwen / Wanx', match: /^(qwen|wanx)/i },
    { id: 'seedream', label: 'Seedream / SeedEdit', match: /^(doubao[-_])?(seedream|seededit)/i },
    { id: 'video', label: i18nText('creator.precision_model_group_video'), match: /^(seedance|doubao[-_]seedance|veo|kling|wan[-_0-9]|sora|hailuo|happy[-_]horse|grok-imagine-video)/i },
    { id: 'chat', label: i18nText('creator.precision_model_group_chat'), match: /^(gpt[-_]|grok[-_]|o[134][-_.]|claude|deepseek)/i },
    { id: 'other', label: i18nText('common.other'), match: /./ }
  ];
  families.forEach(function(group) { group.records = []; });
  precisionModelVisibilityRecords(records).forEach(function(record) {
    var group = families.find(function(family) { return family.match.test(String(record.id || '')); });
    (group || families[families.length - 1]).records.push(record);
  });
  return families.filter(function(group) { return group.records.length; });
}

function precisionModelVisibilityState() {
  return precisionModelVisibilityDraft || precisionEditModelVisibility;
}

function precisionModelVisibilityIsVisible(providerId, record, state) {
  var key = precisionModelVisibilityStorageKey(providerId, record.id);
  return !key || (state || precisionEditModelVisibility)[key] !== false;
}

function precisionModelVisibilitySelectedCount(records, providerId, state) {
  return precisionModelVisibilityRecords(records).filter(function(record) {
    return precisionModelVisibilityIsVisible(providerId, record, state);
  }).length;
}

function precisionModelVisibilitySummary(records, providerId, state) {
  var available = precisionModelVisibilityRecords(records);
  if (!available.length) return i18nText('creator.precision_model_none_available');
  var selected = precisionModelVisibilitySelectedCount(available, providerId, state);
  if (selected === available.length) return i18nText('creator.precision_model_display_all', { count: available.length });
  return i18nText('creator.precision_model_display_summary', { selected: selected, total: available.length });
}

function bindPrecisionModelVisibilityDismiss() {
  if (precisionModelVisibilityDismissBound || typeof document === 'undefined' || !document.addEventListener) return;
  precisionModelVisibilityDismissBound = true;
  var attach = function() {
    if (!precisionModelVisibilityDismissBound) return;
    document.addEventListener('pointerdown', handlePrecisionModelVisibilityDocumentPointer, true);
    document.addEventListener('keydown', handlePrecisionModelVisibilityDocumentKeydown, true);
  };
  if (typeof setTimeout === 'function') setTimeout(attach, 0);
  else attach();
}

function unbindPrecisionModelVisibilityDismiss() {
  if (!precisionModelVisibilityDismissBound || typeof document === 'undefined' || !document.removeEventListener) return;
  precisionModelVisibilityDismissBound = false;
  document.removeEventListener('pointerdown', handlePrecisionModelVisibilityDocumentPointer, true);
  document.removeEventListener('keydown', handlePrecisionModelVisibilityDocumentKeydown, true);
  if (typeof window !== 'undefined' && window.removeEventListener) {
    window.removeEventListener('resize', positionPrecisionModelVisibilityMenu, true);
    window.removeEventListener('scroll', positionPrecisionModelVisibilityMenu, true);
    if (window.visualViewport && window.visualViewport.removeEventListener) {
      window.visualViewport.removeEventListener('resize', positionPrecisionModelVisibilityMenu);
      window.visualViewport.removeEventListener('scroll', positionPrecisionModelVisibilityMenu);
    }
  }
}

function focusPrecisionModelVisibilityTrigger(providerId) {
  if (typeof document === 'undefined' || !document.querySelector) return false;
  var focus = function() {
    var trigger = document.querySelector('[data-precision-model-visibility-toggle]');
    if (trigger && typeof trigger.focus === 'function') trigger.focus();
  };
  if (typeof setTimeout === 'function') setTimeout(focus, 0);
  else focus();
  return true;
}

function precisionModelVisibilityFocusableItems() {
  if (typeof document === 'undefined' || !document.getElementById) return [];
  var menu = document.getElementById('precisionModelVisibilityMenu');
  if (!menu || !menu.querySelectorAll) return [];
  return Array.prototype.slice.call(menu.querySelectorAll('button:not([disabled]), input:not([disabled])')).filter(function(item) {
    return item && item.offsetParent !== null && typeof item.focus === 'function';
  });
}

function focusFirstPrecisionModelVisibilityControl() {
  var focus = function() {
    var items = precisionModelVisibilityFocusableItems();
    if (items.length) items[0].focus();
  };
  if (typeof setTimeout === 'function') setTimeout(focus, 0);
  else focus();
}

function removePrecisionModelVisibilityPortal() {
  if (typeof document === 'undefined' || !document.getElementById) return false;
  var panel = document.getElementById('precisionEditModelVisibility');
  var menu = document.getElementById('precisionModelVisibilityMenu');
  if (!menu || !menu.parentNode || (panel && panel.contains && panel.contains(menu))) return false;
  menu.parentNode.removeChild(menu);
  return true;
}

function portalPrecisionModelVisibilityMenu() {
  if (typeof document === 'undefined' || !document.getElementById || !document.body) return false;
  var menu = document.getElementById('precisionModelVisibilityMenu');
  if (!menu) return false;
  if (menu.parentNode !== document.body) document.body.appendChild(menu);
  return true;
}

function positionPrecisionModelVisibilityMenu() {
  if (!precisionModelVisibilityMenuOpen || typeof document === 'undefined') return false;
  var panel = document.getElementById('precisionEditModelVisibility');
  var menu = document.getElementById('precisionModelVisibilityMenu');
  var trigger = panel && panel.querySelector ? panel.querySelector('[data-precision-model-visibility-toggle]') : null;
  if (!menu || !trigger || !trigger.getBoundingClientRect || typeof window === 'undefined') return false;
  var visualViewport = window.visualViewport;
  var viewportWidth = Math.max(0, visualViewport && visualViewport.width || window.innerWidth || document.documentElement && document.documentElement.clientWidth || 0);
  var viewportHeight = Math.max(0, visualViewport && visualViewport.height || window.innerHeight || document.documentElement && document.documentElement.clientHeight || 0);
  if (!viewportWidth || !viewportHeight) return false;
  var viewportLeft = Math.max(0, visualViewport && visualViewport.offsetLeft || 0);
  var viewportTop = Math.max(0, visualViewport && visualViewport.offsetTop || 0);
  var margin = Math.min(12, Math.floor(viewportWidth / 4), Math.floor(viewportHeight / 4));
  var triggerRect = trigger.getBoundingClientRect();
  var width = Math.max(1, Math.min(420, viewportWidth - (margin * 2)));
  var viewportRight = viewportLeft + viewportWidth;
  var viewportBottom = viewportTop + viewportHeight;
  var anchorRight = Math.min(viewportRight - margin, Math.max(viewportLeft + margin + width, triggerRect.right));
  var left = Math.min(Math.max(viewportLeft + margin, anchorRight - width), Math.max(viewportLeft + margin, viewportRight - margin - width));
  var belowTop = Math.max(viewportTop + margin, triggerRect.bottom + 6);
  var belowSpace = viewportBottom - belowTop - margin;
  var aboveSpace = triggerRect.top - viewportTop - margin - 6;
  var useAbove = belowSpace < 220 && aboveSpace > belowSpace;
  var viewportAvailableHeight = Math.max(0, viewportHeight - (margin * 2));
  var preferredSpace = Math.max(0, useAbove ? aboveSpace : belowSpace);
  var maxHeight = Math.max(1, Math.min(420, viewportAvailableHeight, Math.max(96, preferredSpace)));
  var top = useAbove ? triggerRect.top - 6 - maxHeight : belowTop;
  top = Math.min(Math.max(viewportTop + margin, top), Math.max(viewportTop + margin, viewportBottom - margin - maxHeight));
  menu.style.left = Math.round(left) + 'px';
  menu.style.right = 'auto';
  menu.style.top = Math.round(top) + 'px';
  menu.style.bottom = 'auto';
  menu.style.width = Math.round(width) + 'px';
  menu.style.maxHeight = Math.round(maxHeight) + 'px';
  menu.style.boxSizing = 'border-box';
  return true;
}

function handlePrecisionModelVisibilityDocumentPointer(event) {
  var panel = document.getElementById('precisionEditModelVisibility');
  if (panel && panel.contains && panel.contains(event.target)) return;
  var menu = document.getElementById('precisionModelVisibilityMenu');
  if (menu && menu.contains && menu.contains(event.target)) return;
  cancelPrecisionModelVisibilityMenu();
}

function handlePrecisionModelVisibilityDocumentKeydown(event) {
  if (!event) return;
  if (event.key === 'Escape') {
    if (event.preventDefault) event.preventDefault();
    cancelPrecisionModelVisibilityMenu(true);
    return;
  }
  if (event.key !== 'Tab' || !precisionModelVisibilityMenuOpen) return;
  var items = precisionModelVisibilityFocusableItems();
  if (!items.length) return;
  var active = document.activeElement;
  var currentIndex = items.indexOf(active);
  if (currentIndex === -1) {
    if (event.preventDefault) event.preventDefault();
    items[0].focus();
    return;
  }
  var nextIndex = event.shiftKey ? currentIndex - 1 : currentIndex + 1;
  if (nextIndex >= 0 && nextIndex < items.length) return;
  if (event.preventDefault) event.preventDefault();
  items[event.shiftKey ? items.length - 1 : 0].focus();
}

function openPrecisionModelVisibilityMenu(providerId) {
  if (!providerId) return false;
  precisionModelVisibilityMenuOpen = true;
  precisionModelVisibilityMenuProviderId = providerId;
  precisionModelVisibilityDraft = copyPrecisionModelVisibilityState(precisionEditModelVisibility);
  bindPrecisionModelVisibilityDismiss();
  renderPrecisionEditModelPicker();
  positionPrecisionModelVisibilityMenu();
  focusFirstPrecisionModelVisibilityControl();
  if (typeof window !== 'undefined' && window.addEventListener) {
    window.addEventListener('resize', positionPrecisionModelVisibilityMenu, true);
    window.addEventListener('scroll', positionPrecisionModelVisibilityMenu, true);
    if (window.visualViewport && window.visualViewport.addEventListener) {
      window.visualViewport.addEventListener('resize', positionPrecisionModelVisibilityMenu);
      window.visualViewport.addEventListener('scroll', positionPrecisionModelVisibilityMenu);
    }
  }
  return true;
}

function cancelPrecisionModelVisibilityMenu(restoreFocus) {
  var wasOpen = precisionModelVisibilityMenuOpen;
  var providerId = precisionModelVisibilityMenuProviderId;
  precisionModelVisibilityMenuOpen = false;
  precisionModelVisibilityMenuProviderId = '';
  precisionModelVisibilityDraft = null;
  unbindPrecisionModelVisibilityDismiss();
  if (wasOpen) {
    renderPrecisionEditModelPicker();
    updatePrecisionEditControls();
    if (restoreFocus) focusPrecisionModelVisibilityTrigger(providerId);
  }
  return wasOpen;
}

function precisionModelVisibilityMenuRecords() {
  var provider = precisionModelVisibilityMenuProviderId ? findProvider(precisionModelVisibilityMenuProviderId) : null;
  return provider ? precisionProviderModelRecords(provider) : [];
}

function setPrecisionModelVisibilityDraft(key, visible) {
  if (!precisionModelVisibilityDraft || !isPrecisionModelVisibilityStorageKey(key)) return false;
  var records = precisionModelVisibilityRecords(precisionModelVisibilityMenuRecords());
  if (!records.some(function(record) {
    return precisionModelVisibilityStorageKey(precisionModelVisibilityMenuProviderId, record.id) === key;
  })) return false;
  if (visible === false) precisionModelVisibilityDraft[key] = false;
  else delete precisionModelVisibilityDraft[key];
  refreshPrecisionModelVisibilityDraft();
  return true;
}

function setPrecisionModelVisibilityGroupDraft(groupId, visible) {
  if (!precisionModelVisibilityDraft) return false;
  var group = precisionModelVisibilityGroups(precisionModelVisibilityMenuRecords()).find(function(item) { return item.id === groupId; });
  if (!group) return false;
  group.records.forEach(function(record) {
    var key = precisionModelVisibilityStorageKey(precisionModelVisibilityMenuProviderId, record.id);
    if (!key) return;
    if (visible === false) precisionModelVisibilityDraft[key] = false;
    else delete precisionModelVisibilityDraft[key];
  });
  refreshPrecisionModelVisibilityDraft();
  return true;
}

function refreshPrecisionModelVisibilityDraft() {
  var menu = document.getElementById('precisionModelVisibilityMenu');
  if (!menu || !precisionModelVisibilityDraft) return;
  var providerId = precisionModelVisibilityMenuProviderId;
  var records = precisionModelVisibilityRecords(precisionModelVisibilityMenuRecords());
  var state = precisionModelVisibilityDraft;
  // Keep the existing nodes, scroll container and focused checkbox intact.
  menu.querySelectorAll('[data-precision-model-visibility]').forEach(function(input) {
    input.checked = state[input.dataset.precisionModelVisibility] !== false;
  });
  precisionModelVisibilityGroups(records).forEach(function(group) {
    var selected = precisionModelVisibilitySelectedCount(group.records, providerId, state);
    var inputs = menu.querySelectorAll('[data-precision-model-visibility-group="' + group.id + '"]');
    inputs.forEach(function(input) {
      input.checked = selected === group.records.length;
      input.indeterminate = selected > 0 && selected < group.records.length;
      input.disabled = !group.records.some(function(record) { return !!precisionModelVisibilityStorageKey(providerId, record.id); });
    });
    menu.querySelectorAll('[data-precision-model-group-count="' + group.id + '"]').forEach(function(count) {
      count.textContent = selected + '/' + group.records.length;
    });
  });
  var selectedCount = precisionModelVisibilitySelectedCount(records, providerId, state);
  menu.querySelectorAll('[data-precision-model-visibility-action="confirm"]').forEach(function(button) { button.disabled = selectedCount < 1; });
  menu.querySelectorAll('.precision-model-visibility-footer > [role="status"]').forEach(function(status) {
    status.textContent = selectedCount < 1 ? i18nText('creator.precision_model_keep_one') : precisionModelVisibilitySummary(records, providerId, state);
  });
}

function setAllPrecisionModelVisibilityDraft(visible) {
  if (!precisionModelVisibilityDraft) return false;
  precisionModelVisibilityRecords(precisionModelVisibilityMenuRecords()).forEach(function(record) {
    var key = precisionModelVisibilityStorageKey(precisionModelVisibilityMenuProviderId, record.id);
    if (!key) return;
    if (visible === false) precisionModelVisibilityDraft[key] = false;
    else delete precisionModelVisibilityDraft[key];
  });
  refreshPrecisionModelVisibilityDraft();
  return true;
}

function confirmPrecisionModelVisibilityMenu() {
  if (!precisionModelVisibilityDraft) return false;
  var providerId = precisionModelVisibilityMenuProviderId;
  var records = precisionModelVisibilityMenuRecords();
  if (precisionModelVisibilitySelectedCount(records, precisionModelVisibilityMenuProviderId, precisionModelVisibilityDraft) < 1) {
    refreshPrecisionModelVisibilityDraft();
    return false;
  }
  precisionEditModelVisibility = copyPrecisionModelVisibilityState(precisionModelVisibilityDraft);
  precisionModelVisibilityMenuOpen = false;
  precisionModelVisibilityMenuProviderId = '';
  precisionModelVisibilityDraft = null;
  unbindPrecisionModelVisibilityDismiss();
  var saved = writePrecisionModelVisibility();
  renderPrecisionEditModelPicker();
  updatePrecisionEditControls();
  focusPrecisionModelVisibilityTrigger(providerId);
  return saved;
}

function renderPrecisionModelVisibility(records, providerId) {
  var panel = document.getElementById('precisionEditModelVisibility');
  if (!panel) return;
  removePrecisionModelVisibilityPortal();
  var visibleRecords = precisionModelVisibilityRecords(records);
  if (!visibleRecords.length) {
    precisionModelVisibilityMenuOpen = false;
    precisionModelVisibilityMenuProviderId = '';
    precisionModelVisibilityDraft = null;
    unbindPrecisionModelVisibilityDismiss();
    panel.classList.remove('is-open');
    panel.innerHTML = '<span class="precision-model-visibility-empty">' + escHtml(i18nText('creator.precision_model_none_available')) + '</span>';
    return;
  }
  var menuOpen = precisionModelVisibilityMenuOpen && precisionModelVisibilityMenuProviderId === providerId;
  var state = menuOpen ? precisionModelVisibilityState() : precisionEditModelVisibility;
  var selectedCount = precisionModelVisibilitySelectedCount(visibleRecords, providerId, state);
  var menuId = 'precisionModelVisibilityMenu';
  panel.classList.toggle('is-open', menuOpen);
  panel.innerHTML =
    '<button type="button" class="precision-model-visibility-trigger" data-precision-model-visibility-toggle data-precision-model-visibility-provider="' + escAttr(providerId) + '" aria-haspopup="dialog" aria-expanded="' + (menuOpen ? 'true' : 'false') + '"' + (menuOpen ? ' aria-controls="' + menuId + '"' : '') + '>' +
      '<span>' + escHtml(i18nText('creator.precision_model_display')) + '</span>' +
      '<strong>' + escHtml(precisionModelVisibilitySummary(visibleRecords, providerId, state)) + '</strong>' +
    '</button>' +
    (menuOpen ? '<div id="' + menuId + '" class="precision-model-visibility-menu" role="dialog" aria-labelledby="precisionModelVisibilityTitle">' +
      '<div class="precision-model-visibility-menu-head"><strong id="precisionModelVisibilityTitle">' + escHtml(i18nText('creator.precision_model_menu_title')) + '</strong><span>' + escHtml(i18nText('creator.precision_model_menu_hint')) + '</span></div>' +
      '<div class="precision-model-visibility-actions"><button type="button" data-precision-model-visibility-action="all">' + escHtml(i18nText('creator.precision_model_select_all')) + '</button><button type="button" data-precision-model-visibility-action="clear">' + escHtml(i18nText('creator.precision_model_clear')) + '</button></div>' +
      '<div class="precision-model-visibility-list" role="group" aria-label="' + escAttr(i18nText('creator.precision_model_display')) + '">' + precisionModelVisibilityGroups(visibleRecords).map(function(group) {
        return '<section class="precision-model-visibility-group" aria-labelledby="precisionModelGroup-' + group.id + '">' +
          '<label class="precision-model-visibility-group-heading"><input type="checkbox" data-precision-model-visibility-group="' + group.id + '">' +
          '<span id="precisionModelGroup-' + group.id + '">' + escHtml(group.label) + '</span><span class="precision-model-group-count" data-precision-model-group-count="' + group.id + '"></span></label>' +
          group.records.map(function(record) {
    var key = precisionModelVisibilityStorageKey(providerId, record.id);
    var checked = precisionModelVisibilityIsVisible(providerId, record, state);
    var label = precisionModelVisibilityLabel(record);
    return '<label class="precision-model-visibility-option" title="' + escAttr(label) + '"><input type="checkbox" ' + (checked ? 'checked' : '') + (key ? ' data-precision-model-visibility="' + escAttr(key) + '"' : ' disabled') + '><span title="' + escAttr(label) + '">' + escHtml(label) + '</span></label>';
          }).join('') + '</section>';
      }).join('') + '</div>' +
      '<div class="precision-model-visibility-footer"><span role="status">' + escHtml(selectedCount < 1 ? i18nText('creator.precision_model_keep_one') : precisionModelVisibilitySummary(visibleRecords, providerId, state)) + '</span><div><button type="button" data-precision-model-visibility-action="cancel">' + escHtml(i18nText('common.cancel')) + '</button><button type="button" class="btn-primary" data-precision-model-visibility-action="confirm" ' + (selectedCount < 1 ? 'disabled' : '') + '>' + escHtml(i18nText('creator.precision_model_apply')) + '</button></div></div>' +
    '</div>' : '');
  if (menuOpen) {
    portalPrecisionModelVisibilityMenu();
    positionPrecisionModelVisibilityMenu();
  }
  var trigger = panel.querySelector('[data-precision-model-visibility-toggle]');
  if (trigger) trigger.addEventListener('click', function(event) {
    if (event && event.stopPropagation) event.stopPropagation();
    if (menuOpen) cancelPrecisionModelVisibilityMenu(true);
    else openPrecisionModelVisibilityMenu(providerId);
  });
  if (!menuOpen) return;
  var menuRoot = document.getElementById(menuId) || panel;
  menuRoot.querySelectorAll('[data-precision-model-visibility]').forEach(function(input) {
    input.addEventListener('change', function() { setPrecisionModelVisibilityDraft(input.dataset.precisionModelVisibility, input.checked); });
  });
  menuRoot.querySelectorAll('[data-precision-model-visibility-group]').forEach(function(input) {
    input.addEventListener('change', function() { setPrecisionModelVisibilityGroupDraft(input.dataset.precisionModelVisibilityGroup, input.checked); });
  });
  refreshPrecisionModelVisibilityDraft();
  menuRoot.querySelectorAll('[data-precision-model-visibility-action]').forEach(function(button) {
    button.addEventListener('click', function(event) {
      if (event && event.stopPropagation) event.stopPropagation();
      var action = button.dataset.precisionModelVisibilityAction;
      if (action === 'all') setAllPrecisionModelVisibilityDraft(true);
      else if (action === 'clear') setAllPrecisionModelVisibilityDraft(false);
      else if (action === 'cancel') cancelPrecisionModelVisibilityMenu(true);
      else if (action === 'confirm') confirmPrecisionModelVisibilityMenu();
    });
  });
}

function renderPrecisionEditModelPicker() {
  var endpointSelect = document.getElementById('precisionEditProviderEndpoint');
  var select = document.getElementById('precisionEditProviderModel');
  precisionEditModelPickerReady = false;
  updatePrecisionEditAuthorizationControl();
  if (!select) return;
  var previousEndpoint = endpointSelect ? endpointSelect.value : '';
  var previous = select.value;
  var providers = (allProviders || []).filter(function(provider) {
    return provider && provider.type === 'image' && provider.enabled !== false && provider.has_key;
  });
  if (endpointSelect) {
    endpointSelect.innerHTML = providers.length ? providers.map(function(provider) {
      return '<option value="' + escAttr(provider.id) + '">' + escHtml(provider.name || provider.id) + '</option>';
    }).join('') : '<option value="">' + escHtml(i18nText('creator.precision_edit_no_endpoint')) + '</option>';
    if (providers.some(function(provider) { return provider.id === previousEndpoint; })) endpointSelect.value = previousEndpoint;
    else if (providers.length) endpointSelect.value = providers[0].id;
    endpointSelect.disabled = !providers.length;
  }
  var activeProviderId = endpointSelect ? endpointSelect.value : '';
  precisionEditModelVisibility = readPrecisionModelVisibility();
  var options = [];
  var activeRecords = [];
  providers.forEach(function(provider) {
    if (activeProviderId && provider.id !== activeProviderId) return;
    if (!provider || provider.type !== 'image' || provider.enabled === false) return;
    var records = precisionProviderModelRecords(provider);
    activeRecords = records;
    renderPrecisionModelVisibility(records, provider.id);
    records.forEach(function(record) {
      var visibilityKey = precisionModelVisibilityStorageKey(provider.id, record.id);
      if (record.unavailable || (visibilityKey && precisionEditModelVisibility[visibilityKey] === false)) return;
      var label = precisionModelVisibilityLabel(record);
      label += record.authorized ? ' · ' + i18nText('creator.precision_edit_authorized') : ' · ' + i18nText('creator.precision_edit_unconfirmed');
      options.push({ value: provider.id + '::' + record.id, label: label, providerId: provider.id, model: record.id, authorized: record.authorized });
    });
  });
  if (!activeProviderId) renderPrecisionModelVisibility([], '');
  select.innerHTML = options.length ? options.map(function(option) {
    return '<option value="' + escAttr(option.value) + '">' + escHtml(option.label) + '</option>';
  }).join('') : '<option value="">' + escHtml(i18nText('creator.precision_edit_no_model')) + '</option>';
  if (options.some(function(option) { return option.value === previous; })) select.value = previous;
  else if (options.length) select.value = options[0].value;
  select.disabled = !options.length;
  precisionEditModelPickerReady = true;
  selectPrecisionEditModel(options.length ? select.value : '', true);
}

function selectPrecisionEditEndpoint() {
  renderPrecisionEditModelPicker();
  updatePrecisionEditControls();
}

function selectPrecisionEditModel(value, fromRender) {
  var select = document.getElementById('precisionEditProviderModel');
  if (select && value !== undefined && select.value !== value) {
    var hasOption = Array.prototype.some.call(select.options || [], function(option) { return option.value === value; });
    if (hasOption) select.value = value;
  }
  var state = getPrecisionEditModelAuthorizationState();
  selectedProviders = state.authorized ? [state.providerId] : [];
  precisionEditSelectedModel = { providerId: state.providerId, model: state.model };
  if (state.provider) state.provider.model = state.model;
  updatePrecisionResizeCapabilityUI();
  updatePrecisionEditAuthorizationControl();
  if (!fromRender) {
    renderProviderList();
  }
  updatePrecisionEditControls();
}

function authorizePrecisionEditModel() {
  var state = updatePrecisionEditAuthorizationControl();
  if (!state.canAuthorize) return;
  var compatibility = document.getElementById('precisionEditGptImage2Compatibility');
  var useCompatibility = !!(compatibility && compatibility.checked && state.canUseCompatibility);
  var confirmKey = useCompatibility
    ? 'creator.precision_edit_compatibility_confirm'
    : 'creator.precision_edit_authorize_confirm';
  if (!confirm(i18nText(confirmKey))) return;
  precisionEditAuthorizationPending = true;
  updatePrecisionEditAuthorizationControl();
  var payload = {model:state.model,enabled:true,confirmed:true};
  if (useCompatibility) payload.compatibility_profile = PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE;
  _authFetch('/api/providers/' + encodeURIComponent(state.providerId) + '/precision-capability', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
    .then(function(r){if(!r.ok)return r.json().then(function(body){throw new Error((body.detail&&body.detail.message)||('HTTP '+r.status));});return r.json();})
    .then(function(){return loadProviders();})
    .then(function(){precisionEditAuthorizationPending=false;renderPrecisionEditModelPicker();updatePrecisionEditControls();setStatus(i18nText('creator.precision_edit_authorize_saved'));})
    .catch(function(error){precisionEditAuthorizationPending=false;updatePrecisionEditAuthorizationControl();updatePrecisionEditControls();setStatus(i18nText('common.save_failed_colon')+error.message);});
}

function revokePrecisionEditModel() {
  var state = updatePrecisionEditAuthorizationControl();
  if (!state.canRevoke) return;
  if (!confirm(i18nText('creator.precision_edit_revoke_confirm'))) return;
  precisionEditAuthorizationPending = true;
  updatePrecisionEditAuthorizationControl();
  _authFetch('/api/providers/' + encodeURIComponent(state.providerId) + '/precision-capability', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:state.model,enabled:false,confirmed:true})})
    .then(function(r){if(!r.ok)return r.json().then(function(body){throw new Error((body.detail&&body.detail.message)||('HTTP '+r.status));});return r.json();})
    .then(function(){return loadProviders();})
    .then(function(){
      var compatibility = document.getElementById('precisionEditGptImage2Compatibility');
      if (compatibility) {
        compatibility.checked = false;
        if (compatibility.dataset) compatibility.dataset.selectionKey = '';
      }
      precisionEditAuthorizationPending=false;renderPrecisionEditModelPicker();updatePrecisionEditControls();setStatus(i18nText('creator.precision_edit_revoked'));
    })
    .catch(function(error){precisionEditAuthorizationPending=false;updatePrecisionEditAuthorizationControl();updatePrecisionEditControls();setStatus(i18nText('common.save_failed_colon')+error.message);});
}

// ═══════════════════════════════════════════════════════════════════
// Provider 加载
// ═══════════════════════════════════════════════════════════════════
function loadProviders(attempt) {
  var effectiveAttempt = _captureLoginAttempt(attempt);
  precisionEditModelPickerReady = false;
  var precisionEndpoint = document.getElementById('precisionEditProviderEndpoint');
  var precisionModel = document.getElementById('precisionEditProviderModel');
  if (precisionEndpoint) precisionEndpoint.disabled = true;
  if (precisionModel) precisionModel.disabled = true;
  updatePrecisionEditAuthorizationControl();
  return _authFetch('/api/providers').then(function(r){
    if (!_isCurrentLoginAttempt(effectiveAttempt)) return null;
    return r.json();
  }).then(function(data){
    if (!_isCurrentLoginAttempt(effectiveAttempt) || !data) return;
    allProviders = data.providers || [];
    loadProviderOrder();
    if((localStorage.getItem('igs_image_workbench')||'multi')==='single'){
      var imageProviders=allProviders.filter(function(provider){return provider.type==='image'&&provider.enabled!==false;});
      var selectedImage=selectedProviders[0];
      if(!imageProviders.some(function(provider){return provider.id===selectedImage;}))selectedImage=imageProviders[0]&&imageProviders[0].id;
      selectedProviders=selectedImage?[selectedImage]:[];
    }
    renderProviderList();
    renderCreatorProviderPickers();
    renderPrecisionEditModelPicker();
    updatePrecisionResizeCapabilityUI();
    loadModelDropdown();  // 更新模型下拉列表
    updateInpaintAvailability();
    setStatus(i18nText('provider.loaded_prefix') + allProviders.filter(function(p){return p.type==='image';}).length + i18nText('provider.image_count'));
  }).catch(function(e){
    if (_isCurrentLoginAttempt(effectiveAttempt) && e.message !== 'AUTH_REQUIRED') {
      setStatus(i18nText('provider.load_failed'));
    }
  });
}

function onImageModelChange(pid, newModel) {
  for (var i = 0; i < allProviders.length; i++) {
    if (allProviders[i].id === pid) {
      allProviders[i].model = newModel;
      break;
    }
  }
}

function modelSupportsGenerationMode(provider, model, mode) {
  var caps = provider && provider.capabilities && typeof provider.capabilities === 'object'
    ? provider.capabilities : {};
  var modelCaps = provider && provider.model_capabilities && provider.model_capabilities[model];
  if (mode === 'precision_edit') {
    var precisionResolution = resolvePrecisionModelCapability(provider, model);
    var explicitlyUnsupported = precisionResolution.capability && Object.prototype.hasOwnProperty.call(precisionResolution.capability, 'precision_edit') && precisionResolution.capability.precision_edit === false;
    return !!(provider && provider.endpoint_type === 'openai' && caps.precision_edit !== false &&
      precisionResolution.structureValid && !explicitlyUnsupported);
  }
  if (modelCaps && typeof modelCaps === 'object') {
    if (mode === 'inpaint' && (modelCaps.inpaint_mask === true || modelCaps.inpaint === true)) return true;
    if (mode === 'i2i' && (modelCaps.precision_edit === true || modelCaps.i2i === true)) return true;
    if (mode === 't2i' && modelCaps.t2i === true) return true;
    if (mode === 'inpaint' && (modelCaps.inpaint_mask === false || modelCaps.inpaint === false)) return false;
    if (mode === 'i2i' && modelCaps.precision_edit === false && modelCaps.i2i === false) return false;
    if (mode === 't2i' && modelCaps.t2i === false) return false;
  }

  if (mode === 'inpaint') {
    return getInpaintCapability(provider).supported;
  }
  if (mode === 'i2i') {
    if (caps.i2i !== undefined) return caps.i2i === true;
    var imageModel = String(model || '').toLowerCase();
    return imageModel.indexOf('edit') !== -1 || imageModel.indexOf('i2i') !== -1 || imageModel.indexOf('image-to-image') !== -1;
  }
  if (caps.t2i !== undefined) return caps.t2i === true;
  return true;
}

function updateGenerationModelHelp() {
  var help = document.getElementById('generationModelHelp');
  if (!help) return;
  var modeKey = currentMode === 'inpaint' ? 'creator.model_help_inpaint' : currentMode === 'precision_edit' ? 'creator.model_help_precision_edit' : currentMode === 'i2i' ? 'creator.model_help_i2i' : 'creator.model_help_t2i';
  var names = [];
  (allProviders || []).filter(function(provider) {
    return provider.type === 'image' && provider.enabled !== false;
  }).forEach(function(provider) {
    var models = provider.models && provider.models.length ? provider.models : (provider.model ? [provider.model] : []);
    models.filter(function(model) { return modelSupportsGenerationMode(provider, model, currentMode); }).forEach(function(model) {
      names.push((provider.name || provider.id) + ' / ' + model);
    });
  });
  var title = i18nText(modeKey);
  var list = names.length ? i18nText('creator.model_help_available') + names.join('、') : i18nText('creator.model_help_none');
  help.innerHTML = '<strong>' + escHtml(title) + '</strong><span>' + escHtml(list) + '</span><small>' + escHtml(i18nText('creator.model_help_custom')) + '</small>';
  help.classList.toggle('is-empty', !names.length);
}

function renderProviderList() {
  var container = document.getElementById('providerList');
  var html = '';
  var imageProviders = allProviders.filter(function(p){ return p.type === 'image'; });

  function modeModels(provider) {
    var models = provider.models && provider.models.length > 0 ? provider.models : (provider.model ? [provider.model] : []);
    return models.filter(function(model) { return modelSupportsGenerationMode(provider, model, currentMode); });
  }

  var eligibleProviderIds = imageProviders.filter(function(provider) {
    return modeModels(provider).length > 0 || currentMode === 'inpaint';
  }).map(function(provider) { return provider.id; });
  selectedProviders = selectedProviders.filter(function(id) { return eligibleProviderIds.indexOf(id) !== -1; });

  for (var i = 0; i < imageProviders.length; i++) {
    (function(p, idx){
      var sel = selectedProviders.indexOf(p.id) !== -1;
      var configured = p.api_key || p.has_key;
      var capability = currentMode === 'inpaint' ? getInpaintCapability(p) : { supported: true, reasonCode: '' };
      var modeEligible = modeModels(p).length > 0;
      var capabilityBlocked = !modeEligible && !(currentMode === 'inpaint' && inpaintManualChoice);
      var disabled = !p.enabled || !configured || capabilityBlocked;
      var capabilityHint = currentMode === 'inpaint' && !capability.supported
        ? ' title="' + escAttr(i18nText('creator.inpaint_model_unavailable')) + '"'
        : '';

      var allModels = p.models && p.models.length > 0 ? p.models : (p.model ? [p.model] : []);
      // 过滤掉非生图模型（视频模型 + LLM模型）
      var filteredModels = modeModels(p);
      if (filteredModels.length === 0) filteredModels = allModels;
      var modelOpts = filteredModels.length > 3
        ? buildModelOptsGrouped(filteredModels, p.model || '', groupImageModels)
        : filteredModels.map(function(m){ return '<option value="' + escAttr(m) + '"' + (p.model===m?' selected':'') + '>' + escHtml(m) + '</option>'; }).join('');

      html += '<div class="provider-card ' + (sel ? 'selected' : '') + ' ' + (disabled ? 'disabled' : '') + '" ' +
              'draggable="' + (!disabled) + '" ' +
              'ondragstart="onProviderDragStart(event, \'' + p.id + '\', ' + idx + ')" ' +
              'ondragover="onProviderDragOver(event, \'' + p.id + '\')" ' +
              'ondrop="onProviderDrop(event, \'' + p.id + '\')" ' +
              'ondragend="resetDragStyle()" ' +
              'onclick="' + (disabled ? '' : 'toggleProvider(\'' + p.id + '\')') + '" data-id="' + p.id + '"' + capabilityHint + '>' +
        '<div class="provider-dot" style="background:' + (p.color || '#5b8def') + ';"></div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div class="provider-name">' + escHtml(p.name) + '</div>' +
        '</div>' +
        '<label class="provider-checkbox" aria-hidden="true">' +
          '<input type="checkbox" tabindex="-1" ' + (sel ? 'checked' : '') + ' ' + (disabled ? 'disabled' : '') + '>' +
          '<span class="provider-checkmark"></span>' +
        '</label>' +
      '</div>' +
      '<div style="padding:2px 0 6px 22px;">' +
        '<select onclick="event.stopPropagation();" onchange="event.stopPropagation();onImageModelChange(\'' + p.id + '\', this.value)" ' + (!sel ? 'disabled' : '') + ' style="width:100%;font-size:11px;padding:4px 8px;background:var(--bg-base);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);' + (!sel ? 'opacity:0.5;' : '') + '">' +
          (modelOpts || i18nText('provider.no_models_html')) +
        '</select>' +
      '</div>';
    })(imageProviders[i], i);
  }

  container.innerHTML = html || i18nText('provider.no_models_add_html');
  updateSelCount();
  updateGenerationModelHelp();
}

// 构建 per-provider 宽高比按钮
function buildRatioBtns(pid, activeRatio) {
  var ratios = [
    ['1:1','1:1'], ['2:3','2:3'], ['3:2','3:2'], ['3:4','3:4'], ['4:3','4:3'],
    ['9:16','9:16'], ['16:9','16:9'], ['21:9','21:9'],
    ['auto','auto']
  ];
  var html = '';
  for (var i = 0; i < ratios.length; i++) {
    var r = ratios[i][0];
    var label = ratios[i][1];
    var isActive = r === activeRatio;
    html += '<button class="pratio-btn ' + (isActive ? 'active' : '') + '" ' +
            'onclick="event.stopPropagation();setProviderRatio(\'' + pid + '\',\'' + r + '\',this)" ' +
            'title="' + r + '">' + label + '</button>';
  }
  return html;
}

// per-provider 宽高比选择
function setProviderRatio(pid, ratio, el) {
  // 更新按钮状态
  el.parentElement.querySelectorAll('.pratio-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  // 联动尺寸
  if (ratio !== 'auto' && RATIO_SIZES[ratio]) {
    var sz = RATIO_SIZES[ratio];
    document.getElementById('pw_' + pid).value = sz[0];
    document.getElementById('ph_' + pid).value = sz[1];
  }
  saveProviderSetting(pid, 'ratio', ratio);
}

// per-provider 质量选择
function setProviderQuality(pid, val, el) {
  el.parentElement.querySelectorAll('.pquality-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  saveProviderSetting(pid, 'quality', val);
}

// per-provider 数量调整
function adjustProviderQty(pid, delta) {
  var el = document.getElementById('pqty_' + pid);
  var v = parseInt(el.textContent) || 1;
  v = Math.max(1, Math.min(10, v + delta));
  el.textContent = v;
  providerQuantities[pid] = v;
  saveProviderSetting(pid, 'qty', v);
}

// per-provider 尺寸输入
function onProviderSizeChange(pid) {
  var w = parseInt(document.getElementById('pw_' + pid).value) || 1024;
  var h = parseInt(document.getElementById('ph_' + pid).value) || 1024;
  saveProviderSetting(pid, 'w', w);
  saveProviderSetting(pid, 'h', h);
  // 尝试匹配宽高比
  var matched = '';
  for (var ratio in RATIO_SIZES) {
    var sz = RATIO_SIZES[ratio];
    if (sz[0] === w && sz[1] === h) { matched = ratio; break; }
  }
  var ratioBtns = document.getElementById('pratio_' + pid);
  if (ratioBtns) {
    ratioBtns.querySelectorAll('.pratio-btn').forEach(function(b){
      b.classList.toggle('active', b.title === matched);
    });
  }
  saveProviderSetting(pid, 'ratio', matched);
}

// ── per-provider 设置持久化 ──
function loadPerProviderSettings() {
  try {
    return JSON.parse(localStorage.getItem('genbox_provider_settings') || '{}');
  } catch(e) { return {}; }
}

function saveProviderSetting(pid, key, val) {
  var all = loadPerProviderSettings();
  if (!all[pid]) all[pid] = {};
  all[pid][key] = val;
  try { localStorage.setItem('genbox_provider_settings', JSON.stringify(all)); } catch(e) {}
}

function saveAllProviderSettings() {
  var imageProviders = allProviders.filter(function(p){ return p.type === 'image'; });
  var all = loadPerProviderSettings();
  for (var i = 0; i < imageProviders.length; i++) {
    var p = imageProviders[i];
    if (!all[p.id]) all[p.id] = {};
    // 从 DOM 读取当前值
    var wEl = document.getElementById('pw_' + p.id);
    var hEl = document.getElementById('ph_' + p.id);
    var qEl = document.getElementById('pqty_' + p.id);
    if (wEl) all[p.id].w = parseInt(wEl.value) || 1024;
    if (hEl) all[p.id].h = parseInt(hEl.value) || 1024;
    if (qEl) all[p.id].qty = parseInt(qEl.textContent) || 1;
    // 质量和宽高比从按钮读取
    var qCard = document.querySelector('.provider-card[data-id="' + p.id + '"]');
    if (qCard) {
      var qBtn = qCard.querySelector('.pquality-btn.active');
      if (qBtn) all[p.id].quality = qBtn.title === i18nText('common.auto') ? '' : qBtn.title === i18nText('common.low') ? 'low' : qBtn.title === i18nText('common.medium') ? 'medium' : 'high';
      var rBtn = qCard.querySelector('.pratio-btn.active');
      if (rBtn) all[p.id].ratio = rBtn.title;
    }
  }
  try {
    localStorage.setItem('genbox_provider_settings', JSON.stringify(all));
    setStatus(i18nText('provider.settings_saved'));
  } catch(e) { setStatus(i18nText('common.save_failed')); }
}

// Image provider drag sort
var dragProviderId = null;
var dragProviderOriginalIndex = null;

function onProviderDragStart(e, pid, idx) {
  dragProviderId = pid;
  dragProviderOriginalIndex = idx;
  e.dataTransfer.effectAllowed = 'move';
  var card = document.querySelector('.provider-card[data-id="' + pid + '"]');
  if (card) card.classList.add('dragging');
}

function onProviderDragOver(e, pid) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  var card = document.querySelector('.provider-card[data-id="' + pid + '"]');
  if (card) card.classList.add('drag-over');
}

function onProviderDrop(e, pid) {
  e.preventDefault();
  if (!dragProviderId || dragProviderId === pid) return;
  var imageProviders = allProviders.filter(function(p){ return p.type === 'image'; });
  var fromIdx = imageProviders.findIndex(function(p){ return p.id === dragProviderId; });
  var toIdx = imageProviders.findIndex(function(p){ return p.id === pid; });
  if (fromIdx < 0 || toIdx < 0) return;
  // Reorder imageProviders
  var item = imageProviders.splice(fromIdx, 1)[0];
  imageProviders.splice(toIdx, 0, item);
  // Also reorder in allProviders (image portion)
  var allFromIdx = allProviders.findIndex(function(p){ return p.id === dragProviderId && p.type === 'image'; });
  var allToIdx = allProviders.findIndex(function(p){ return p.id === pid && p.type === 'image'; });
  if (allFromIdx >= 0 && allToIdx >= 0) {
    var allItem = allProviders.splice(allFromIdx, 1)[0];
    allProviders.splice(allToIdx, 0, allItem);
  }
  // Update selectedProviders order
  var selFrom = selectedProviders.indexOf(dragProviderId);
  var selTo = selectedProviders.indexOf(pid);
  if (selFrom >= 0 && selTo >= 0) {
    selectedProviders.splice(selFrom, 1);
    selectedProviders.splice(selTo, 0, dragProviderId);
  }
  saveProviderOrder();
  renderProviderList();
}

function resetDragStyle() {
  dragProviderId = null;
  dragProviderOriginalIndex = null;
  document.querySelectorAll('.dragging, .drag-over').forEach(function(el){ el.classList.remove('dragging', 'drag-over'); });
}

function saveProviderOrder() {
  try {
    var imageProviders = allProviders.filter(function(p){ return p.type === 'image'; });
    localStorage.setItem('providerOrder', JSON.stringify(imageProviders.map(function(p){ return p.id; })));
  } catch(e) {}
}

function loadProviderOrder() {
  try {
    var saved = localStorage.getItem('providerOrder');
    if (!saved) return;
    var order = JSON.parse(saved);
    var imageProviders = allProviders.filter(function(p){ return p.type === 'image'; });
    var reordered = [];
    order.forEach(function(id) {
      var p = imageProviders.find(function(x){ return x.id === id; });
      if (p) reordered.push(p);
    });
    imageProviders.forEach(function(p) {
      if (reordered.indexOf(p) === -1) reordered.push(p);
    });
    // Replace in allProviders
    for (var i = 0; i < allProviders.length; i++) {
      if (allProviders[i].type === 'image') {
        allProviders[i] = reordered.shift() || allProviders[i];
      }
    }
  } catch(e) {}
}

function toggleProvider(id) {
  var mode=localStorage.getItem('igs_image_workbench')||'multi';
  if(mode==='single') selectedProviders=[id];
  else {
    var idx = selectedProviders.indexOf(id);
    if (idx !== -1) selectedProviders.splice(idx, 1);
    else selectedProviders.push(id);
  }
  renderProviderList();
  renderCreatorProviderPickers();
  updateInpaintAvailability();
}

function updateSelCount() {
  document.getElementById('selCountBadge').textContent = selectedProviders.length;
}

// ═══════════════════════════════════════════════════════════════════
// 快捷提示词: 渲染 + 搜索 + 折叠
// ═══════════════════════════════════════════════════════════════════
function renderQuickPrompts() {
  var area = document.getElementById('quickArea');
  area.innerHTML = '';
  quickPrompts = {};
  var isEnglish = getUiLanguage() === 'en';

  for (var cat in QUICK_PROMPTS) {
    var section = document.createElement('div');
    section.className = 'quick-section';
    section.setAttribute('data-cat', cat);

    var tagsId = 'qt_' + cat.replace(/[^a-z]/gi,'_');
    var items = pickRandomItems(QUICK_PROMPTS[cat], 3);

    section.innerHTML =
      '<div class="quick-section-header">' +
        '<div class="quick-section-title"><span>' + i18nText('quick.category.' + cat) + '</span><span style="font-size:10px;color:var(--text-muted);font-weight:400;">(' + QUICK_PROMPTS[cat].length + ')</span></div>' +
        '<div style="display:flex;align-items:center;gap:4px;">' +
          '<button class="quick-refresh" onclick="event.stopPropagation();shuffleQuickCategory(\'' + escHtml(cat).replace(/'/g,"\\'") + '\')">' + i18nText('prompt.shuffle') + '</button>' +
          '<span class="quick-chevron open" onclick="toggleQuickSection(this.parentElement.parentElement)">▼</span>' +
        '</div>' +
      '</div>' +
      '<div class="quick-tags" id="' + tagsId + '">' +
        items.map(function(t){
          var words = t.en.split(',').map(function(w){ return w.trim(); }).filter(function(w){ return w.length > 0; });
          return '<div class="quick-item">' +
            '<div class="quick-item-label">' + escHtml(isEnglish ? t.en.split(',')[0].trim() : t.zh) + '</div>' +
            '<div class="quick-item-words">' +
              words.map(function(w){
                return '<button class="quick-tag" onclick="insertQuickWord(this)" data-phrase="' + escHtml(w) + '">' + escHtml(w) + '</button>';
              }).join('') +
            '</div>' +
          '</div>';
        }).join('') +
      '</div>';

    area.appendChild(section);
    quickPrompts[cat] = { el: section, open: true, items: items };
  }
}

function pickRandomItems(arr, count) {
  var shuffled = arr.slice();
  for (var i = shuffled.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = shuffled[i];
    shuffled[i] = shuffled[j];
    shuffled[j] = tmp;
  }
  return shuffled.slice(0, Math.min(count, shuffled.length));
}

function shuffleQuickCategory(cat) {
  var data = quickPrompts[cat];
  if (!data) return;
  var allItems = QUICK_PROMPTS[cat];
  var newItems = pickRandomItems(allItems, 3);
  data.items = newItems;
  var isEnglish = getUiLanguage() === 'en';

  var tagsEl = data.el.querySelector('.quick-tags');
  tagsEl.innerHTML = newItems.map(function(t){
    var words = t.en.split(',').map(function(w){ return w.trim(); }).filter(function(w){ return w.length > 0; });
    return '<div class="quick-item">' +
      '<div class="quick-item-label">' + escHtml(isEnglish ? t.en.split(',')[0].trim() : t.zh) + '</div>' +
      '<div class="quick-item-words">' +
        words.map(function(w){
          return '<button class="quick-tag" onclick="insertQuickWord(this)" data-phrase="' + escHtml(w) + '">' + escHtml(w) + '</button>';
        }).join('') +
      '</div>' +
    '</div>';
  }).join('');

  tagsEl.classList.remove('collapsed');
  tagsEl.style.maxHeight = tagsEl.scrollHeight + 'px';
  data.el.querySelector('.quick-chevron').classList.add('open');
}

function toggleQuickSection(header) {
  var chevron = header.querySelector('.quick-chevron');
  var tags = header.nextElementSibling;
  var isOpen = chevron.classList.contains('open');

  if (isOpen) {
    chevron.classList.remove('open');
    tags.classList.add('collapsed');
    tags.style.maxHeight = tags.scrollHeight + 'px';
    requestAnimationFrame(function(){ tags.classList.add('collapsed'); });
  } else {
    tags.style.maxHeight = tags.scrollHeight + 'px';
    tags.classList.remove('collapsed');
    chevron.classList.add('open');
  }
}

function filterQuickPrompts(query) {
  query = query.trim().toLowerCase();
  for (var cat in quickPrompts) {
    var tags = quickPrompts[cat].el.querySelector('.quick-tags');
    var items = tags.querySelectorAll('.quick-item');
    var visibleCount = 0;
    items.forEach(function(item){
      var label = item.querySelector('.quick-item-label');
      var words = item.querySelectorAll('.quick-tag');
      var labelMatch = label && label.textContent.toLowerCase().indexOf(query) !== -1;
      var wordMatch = false;
      words.forEach(function(w){
        var phrase = (w.getAttribute('data-phrase') || '').toLowerCase();
        if (!query || phrase.indexOf(query) !== -1) {
          wordMatch = true;
        }
      });
      var match = !query || labelMatch || wordMatch;
      item.style.display = match ? '' : 'none';
      if (match) visibleCount++;
    });
    if (query) {
      tags.classList.remove('collapsed');
      tags.style.maxHeight = tags.scrollHeight + 'px';
      quickPrompts[cat].el.querySelector('.quick-chevron').classList.add('open');
    }
    quickPrompts[cat].el.style.display = visibleCount > 0 ? '' : 'none';
  }
}

function insertQuickWord(btn) {
  var phrase = btn.getAttribute('data-phrase') || btn.textContent;
  if (currentMode === 't2i') {
    var ta = document.getElementById('txtPrompt');
    if (ta.value.trim()) {
      ta.value += ', ' + phrase;
    } else {
      ta.value = phrase;
    }
    ta.focus();
  } else {
    var ta2 = document.getElementById('txtPromptI2I');
    if (ta2.value.trim()) {
      ta2.value += ', ' + phrase;
    } else {
      ta2.value = phrase;
    }
    ta2.focus();
  }
}

// ═══════════════════════════════════════════════════════════════════
// Resizable Panels
// ═══════════════════════════════════════════════════════════════════
var _resizeState = null;

function startResize(e, direction) {
  e.preventDefault();
  e.stopPropagation();

  var layout = e.target.closest('.generate-layout');
  if (!layout) return;
  var left = layout.querySelector('.generate-left');
  var center = layout.querySelector('.generate-center');
  var preview = center.querySelector('.generate-preview');
  var bottomRow = center.querySelector('.generate-bottom-row');

  var startX = e.clientX;
  var startY = e.clientY;
  var startLeftW = left ? left.offsetWidth : 260;
  var startPreviewH = preview ? preview.offsetHeight : 0;
  var startBottomH = bottomRow ? bottomRow.offsetHeight : 0;
  var startCenterH = center ? center.offsetHeight : 0;

  var handle = e.target;
  handle.classList.add('dragging');

  _resizeState = { direction: direction, handle: handle };

  function onMove(ev) {
    if (direction === 'left') {
      var dx = ev.clientX - startX;
      var newW = Math.max(180, Math.min(startLeftW + dx, 500));
      left.style.width = newW + 'px';
      left.style.minWidth = newW + 'px';
    } else if (direction === 'bottom') {
      var dy = ev.clientY - startY;
      var available = startCenterH - 24;
      var newPreviewH = Math.max(120, Math.min(startPreviewH + dy, available - 100));
      var newBottomH = available - newPreviewH;
      var previewFlex = newPreviewH / available;
      var bottomFlex = newBottomH / available;
      preview.style.flex = previewFlex.toFixed(2);
      bottomRow.style.flex = bottomFlex.toFixed(2);
    }
  }

  function onUp() {
    handle.classList.remove('dragging');
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    _resizeState = null;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  document.body.style.cursor = direction === 'left' ? 'col-resize' : 'row-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

function startModalResize(e, mode) {
  e.preventDefault();
  e.stopPropagation();
  var box = document.getElementById('providerModalBox');
  if (!box) return;
  var startX = e.clientX;
  var startY = e.clientY;
  var startW = box.offsetWidth;
  var startH = box.offsetHeight;
  var handle = e.target;
  handle.classList.add('dragging');
  function onMove(ev) {
    var dx = ev.clientX - startX;
    var dy = ev.clientY - startY;
    if (mode === 'ew') {
      box.style.width = Math.max(600, Math.min(startW + dx, window.innerWidth * 0.95)) + 'px';
    } else if (mode === 'ns') {
      box.style.height = Math.max(400, Math.min(startH + dy, window.innerHeight * 0.9)) + 'px';
    } else if (mode === 'both') {
      box.style.width = Math.max(600, Math.min(startW + dx, window.innerWidth * 0.95)) + 'px';
      box.style.height = Math.max(400, Math.min(startH + dy, window.innerHeight * 0.9)) + 'px';
    }
  }
  function onUp() {
    handle.classList.remove('dragging');
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
  document.body.style.cursor = mode === 'ew' ? 'ew-resize' : (mode === 'ns' ? 'ns-resize' : 'nwse-resize');
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

function startProviderColResize(e, colIndex) {
  e.preventDefault();
  e.stopPropagation();
  var grid = document.getElementById('providerGrid');
  if (!grid) return;
  var cards = grid.querySelectorAll('.provider-type-card');
  if (!cards[colIndex]) return;
  var startX = e.clientX;
  var startW = cards[colIndex].offsetWidth;
  var prevW = colIndex > 0 ? cards[colIndex - 1].offsetWidth : 0;
  var nextW = colIndex < cards.length - 1 ? cards[colIndex + 1].offsetWidth : 0;
  var handle = e.target;
  handle.style.background = 'var(--accent)';
  function onMove(ev) {
    var dx = ev.clientX - startX;
    var newW = Math.max(220, Math.min(startW + dx, 800));
    cards[colIndex].style.flex = 'none';
    cards[colIndex].style.width = newW + 'px';
  }
  function onUp() {
    handle.style.background = '';
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
  document.body.style.cursor = 'ew-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

function insertQuickPrompt(btn) {
  var text = btn.getAttribute('data-en') || btn.textContent;
  if (currentMode === 't2i') {
    var ta = document.getElementById('txtPrompt');
    if (ta.value.trim()) {
      ta.value += ' · ' + text;
    } else {
      ta.value = text;
    }
    ta.focus();
  } else {
    var ta2 = document.getElementById('txtPromptI2I');
    if (ta2.value.trim()) {
      ta2.value += ' · ' + text;
    } else {
      ta2.value = text;
    }
    ta2.focus();
  }
}

// ═══════════════════════════════════════════════════════════════════
// 图片上传
// ═══════════════════════════════════════════════════════════════════
function handleFileSelect(e) {
  setUploadedImages(Array.prototype.slice.call(e.target.files || []));
  e.target.value = '';
}

function setUploadedImages(files) {
  uploadedImageDataList = [];
  uploadedImageData = null;
  for (var i = 0; i < files.length; i++) handleFile(files[i], i);
}
function handleFile(f, index) {
  if (!f.type.startsWith('image/')) { alert(i18nText('upload.image_required')); return; }
  if (f.size > 10*1024*1024) { alert(i18nText('upload.image_too_large')); return; }
  var reader = new FileReader();
  reader.onload = function(e2) {
    uploadedImageDataList[index] = e2.target.result;
    uploadedImageData = uploadedImageDataList[0] || null;
    var p = document.getElementById('uploadPreview');
    p.src = uploadedImageData;
    p.classList.remove('hidden');
    renderUploadedImagePreviews();
    var ph = document.getElementById('uploadPlaceholder');
    if (ph) ph.style.display = 'none';
  };
  reader.readAsDataURL(f);
}

function renderUploadedImagePreviews() {
  var strip = document.getElementById('uploadPreviewStrip');
  var ph = document.getElementById('uploadPlaceholder');
  var images = uploadedImageDataList.filter(Boolean);
  if (strip) {
    strip.innerHTML = '';
    for (var i = 0; i < images.length; i++) {
      var img = document.createElement('img');
      img.src = images[i];
      img.className = 'upload-thumb';
      img.alt = 'Reference ' + (i + 1);
      strip.appendChild(img);
    }
  }
  if (ph) ph.style.display = images.length ? 'none' : '';
}

// ── Inpaint source and mask editor ──
var INPAINT_MASK_CONTRACT = 'genbox-edit-white-v1';
var INPAINT_MAX_PIXELS = 24000000;
var INPAINT_HISTORY_LIMIT = 12;
var inpaintSourceImageData = null;
var inpaintManualChoice = false;
var inpaintSourceWidth = 0;
var inpaintSourceHeight = 0;
var inpaintMaskHasPaint = false;
var inpaintTool = 'brush';
var inpaintBrushSize = 48;
var inpaintHistory = [];
var inpaintRedo = [];
var inpaintPointerId = null;
var inpaintLastPoint = null;
var inpaintRestoreToken = 0;

function openInpaintFilePicker(event) {
  if (event && event.type === 'keydown' && event.key !== 'Enter' && event.key !== ' ') return;
  if (event) event.preventDefault();
  var input = document.getElementById('fileInputInpaint');
  if (input) input.click();
}

function handleInpaintFileSelect(e) {
  var file = e.target.files && e.target.files[0];
  if (file) handleInpaintFile(file);
  e.target.value = '';
}

function handleInpaintFile(file) {
  if (!file.type || !file.type.startsWith('image/')) { alert(i18nText('upload.image_required')); return; }
  if (file.size > 10 * 1024 * 1024) { alert(i18nText('upload.image_too_large')); return; }
  var reader = new FileReader();
  reader.onload = function(event) {
    loadInpaintSourceImage(event.target.result);
  };
  reader.readAsDataURL(file);
}

function resetInpaintMaskState() {
  var canvas = document.getElementById('inpaintMaskCanvas');
  var pointerId = inpaintPointerId;
  if (canvas && pointerId !== null && canvas.hasPointerCapture && canvas.hasPointerCapture(pointerId)) {
    try { canvas.releasePointerCapture(pointerId); } catch (error) {}
  }
  inpaintRestoreToken += 1;
  inpaintPointerId = null;
  inpaintLastPoint = null;
  inpaintHistory = [];
  inpaintRedo = [];
  inpaintMaskHasPaint = false;
}

function loadInpaintSourceImage(dataUrl) {
  var source = new Image();
  source.onload = function() {
    var width = source.naturalWidth || source.width;
    var height = source.naturalHeight || source.height;
    if (!width || !height || width * height > INPAINT_MAX_PIXELS) {
      alert(i18nText('creator.inpaint_image_too_large'));
      return;
    }

    resetInpaintMaskState();
    inpaintSourceImageData = dataUrl;
    inpaintSourceWidth = width;
    inpaintSourceHeight = height;

    var preview = document.getElementById('inpaintUploadPreview');
    var placeholder = document.getElementById('inpaintUploadPlaceholder');
    var baseImage = document.getElementById('inpaintBaseImage');
    var canvas = document.getElementById('inpaintMaskCanvas');
    var shell = document.getElementById('inpaintCanvasShell');
    var empty = document.getElementById('inpaintCanvasEmpty');
    var dimensions = document.getElementById('inpaintCanvasDimensions');

    if (preview) { preview.src = dataUrl; preview.classList.remove('hidden'); }
    if (placeholder) placeholder.classList.add('hidden');
    if (baseImage) { baseImage.src = dataUrl; baseImage.classList.remove('hidden'); }
    if (canvas) {
      canvas.width = width;
      canvas.height = height;
      canvas.style.aspectRatio = width + ' / ' + height;
      canvas.getContext('2d').clearRect(0, 0, width, height);
    }
    if (shell) {
      shell.style.aspectRatio = width + ' / ' + height;
      shell.classList.remove('is-empty');
    }
    if (empty) empty.classList.add('hidden');
    if (dimensions) dimensions.textContent = width + ' × ' + height;
    updateInpaintHistoryControls();
    updateInpaintAvailability();
  };
  source.onerror = function() { alert(i18nText('image.data_failed')); };
  source.src = dataUrl;
}

function initializeInpaintCanvasInteractions() {
  var canvas = document.getElementById('inpaintMaskCanvas');
  if (!canvas || canvas.dataset.inpaintBound === 'true') return;
  canvas.dataset.inpaintBound = 'true';
  canvas.addEventListener('pointerdown', beginInpaintStroke);
  canvas.addEventListener('pointermove', continueInpaintStroke);
  canvas.addEventListener('pointerup', endInpaintStroke);
  canvas.addEventListener('pointercancel', endInpaintStroke);
  canvas.addEventListener('lostpointercapture', endInpaintStroke);
  canvas.addEventListener('contextmenu', function(event) { event.preventDefault(); });
}

function getInpaintCanvasPoint(event) {
  var canvas = document.getElementById('inpaintMaskCanvas');
  if (!canvas || !canvas.width || !canvas.height) return null;
  var rect = canvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;
  return {
    x: Math.max(0, Math.min(canvas.width, (event.clientX - rect.left) * canvas.width / rect.width)),
    y: Math.max(0, Math.min(canvas.height, (event.clientY - rect.top) * canvas.height / rect.height))
  };
}

function beginInpaintStroke(event) {
  if (!inpaintSourceImageData || inpaintPointerId !== null) return;
  if (event.isPrimary === false || (event.pointerType === 'mouse' && event.button !== 0)) return;
  var point = getInpaintCanvasPoint(event);
  if (!point) return;
  event.preventDefault();
  inpaintPointerId = event.pointerId;
  inpaintLastPoint = point;
  pushInpaintHistorySnapshot();
  try { event.currentTarget.setPointerCapture(event.pointerId); } catch (error) {}
  paintInpaintSegment(point, point);
}

function continueInpaintStroke(event) {
  if (event.pointerId !== inpaintPointerId || !inpaintLastPoint) return;
  var point = getInpaintCanvasPoint(event);
  if (!point) return;
  event.preventDefault();
  paintInpaintSegment(inpaintLastPoint, point);
  inpaintLastPoint = point;
}

function endInpaintStroke(event) {
  if (event.pointerId !== inpaintPointerId) return;
  var canvas = event.currentTarget;
  if (canvas && canvas.hasPointerCapture && canvas.hasPointerCapture(event.pointerId)) {
    try { canvas.releasePointerCapture(event.pointerId); } catch (error) {}
  }
  inpaintPointerId = null;
  inpaintLastPoint = null;
  inpaintMaskHasPaint = inpaintCanvasHasPaint();
  updateInpaintHistoryControls();
  updateInpaintAvailability();
}

function paintInpaintSegment(from, to) {
  var canvas = document.getElementById('inpaintMaskCanvas');
  if (!canvas) return;
  var context = canvas.getContext('2d');
  var size = Math.max(1, Number(inpaintBrushSize) || 1);
  context.save();
  context.globalCompositeOperation = inpaintTool === 'eraser' ? 'destination-out' : 'source-over';
  context.fillStyle = '#ffffff';
  context.strokeStyle = '#ffffff';
  context.lineCap = 'round';
  context.lineJoin = 'round';
  context.lineWidth = size;
  if (from.x === to.x && from.y === to.y) {
    context.beginPath();
    context.arc(from.x, from.y, size / 2, 0, Math.PI * 2);
    context.fill();
  } else {
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
  }
  context.restore();
  if (inpaintTool === 'brush') inpaintMaskHasPaint = true;
}

function setInpaintTool(tool) {
  if (tool !== 'brush' && tool !== 'eraser') return;
  inpaintTool = tool;
  var brush = document.getElementById('inpaintToolBrush');
  var eraser = document.getElementById('inpaintToolEraser');
  if (brush) {
    brush.classList.toggle('btn-secondary', tool === 'brush');
    brush.classList.toggle('btn-ghost', tool !== 'brush');
    brush.classList.toggle('active', tool === 'brush');
    brush.setAttribute('aria-pressed', tool === 'brush' ? 'true' : 'false');
  }
  if (eraser) {
    eraser.classList.toggle('btn-secondary', tool === 'eraser');
    eraser.classList.toggle('btn-ghost', tool !== 'eraser');
    eraser.classList.toggle('active', tool === 'eraser');
    eraser.setAttribute('aria-pressed', tool === 'eraser' ? 'true' : 'false');
  }
}

function setInpaintBrushSize(value) {
  inpaintBrushSize = Math.max(8, Math.min(240, Number(value) || 48));
  var input = document.getElementById('inpaintBrushSize');
  if (input) input.value = String(inpaintBrushSize);
  var output = document.getElementById('inpaintBrushSizeValue');
  if (output) output.textContent = String(inpaintBrushSize);
}

function inpaintCanvasHasPaint() {
  var canvas = document.getElementById('inpaintMaskCanvas');
  if (!canvas || !canvas.width || !canvas.height) return false;
  try {
    var pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    for (var index = 3; index < pixels.length; index += 4) {
      if (pixels[index] !== 0) return true;
    }
  } catch (error) {
    return inpaintMaskHasPaint;
  }
  return false;
}

function captureInpaintMaskSnapshot() {
  var canvas = document.getElementById('inpaintMaskCanvas');
  if (!inpaintSourceImageData || !canvas || !canvas.width || !canvas.height) return null;
  return canvas.toDataURL('image/png');
}

function pushInpaintHistorySnapshot() {
  var snapshot = captureInpaintMaskSnapshot();
  if (!snapshot) return;
  inpaintHistory.push(snapshot);
  if (inpaintHistory.length > INPAINT_HISTORY_LIMIT) inpaintHistory.shift();
  inpaintRedo = [];
  updateInpaintHistoryControls();
}

function restoreInpaintMaskSnapshot(snapshot) {
  var canvas = document.getElementById('inpaintMaskCanvas');
  if (!canvas || !snapshot) return;
  var token = ++inpaintRestoreToken;
  var mask = new Image();
  mask.onload = function() {
    if (token !== inpaintRestoreToken) return;
    var context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.drawImage(mask, 0, 0, canvas.width, canvas.height);
    inpaintMaskHasPaint = inpaintCanvasHasPaint();
    updateInpaintHistoryControls();
    updateInpaintAvailability();
  };
  mask.src = snapshot;
}

function undoInpaintMask() {
  if (!inpaintHistory.length) return;
  var current = captureInpaintMaskSnapshot();
  if (current) inpaintRedo.push(current);
  restoreInpaintMaskSnapshot(inpaintHistory.pop());
  updateInpaintHistoryControls();
}

function redoInpaintMask() {
  if (!inpaintRedo.length) return;
  var current = captureInpaintMaskSnapshot();
  if (current) inpaintHistory.push(current);
  restoreInpaintMaskSnapshot(inpaintRedo.pop());
  updateInpaintHistoryControls();
}

function clearInpaintMask() {
  if (!inpaintSourceImageData || !inpaintMaskHasPaint) return;
  pushInpaintHistorySnapshot();
  var canvas = document.getElementById('inpaintMaskCanvas');
  if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  inpaintMaskHasPaint = false;
  updateInpaintHistoryControls();
  updateInpaintAvailability();
}

function updateInpaintHistoryControls() {
  var undo = document.getElementById('btnInpaintUndo');
  var redo = document.getElementById('btnInpaintRedo');
  var clear = document.getElementById('btnInpaintClear');
  if (undo) undo.disabled = !inpaintHistory.length;
  if (redo) redo.disabled = !inpaintRedo.length;
  if (clear) clear.disabled = !inpaintMaskHasPaint;
}

function getInpaintCapability(provider) {
  var roots = [provider && provider.effective_capabilities, provider && provider.capabilities];
  for (var index = 0; index < roots.length; index++) {
    var capabilities = roots[index];
    if (!capabilities || typeof capabilities !== 'object') continue;
    var raw = Object.prototype.hasOwnProperty.call(capabilities, 'inpaint_mask') ? capabilities.inpaint_mask : capabilities.inpaint;
    if (raw === undefined) continue;
    if (raw === true || raw === 'supported') return { supported: true, reasonCode: '' };
    if (raw && typeof raw === 'object') {
      var state = raw.state || raw.status;
      if (raw.supported === true || state === 'supported') return { supported: true, reasonCode: '' };
      return { supported: false, reasonCode: raw.reason_code || raw.reasonCode || state || '' };
    }
    return { supported: false, reasonCode: typeof raw === 'string' ? raw : '' };
  }
  return { supported: false, reasonCode: 'mask_protocol_unverified' };
}

function inpaintCapabilityReasonText(reasonCode) {
  if (reasonCode === 'mask_protocol_unverified') return i18nText('creator.inpaint_protocol_unverified');
  if (reasonCode === 'unsupported') return i18nText('creator.inpaint_provider_unsupported_reason');
  return i18nText('creator.inpaint_provider_unknown');
}

function getInpaintReadiness() {
  if (!inpaintSourceImageData) return { ready: false, message: i18nText('creator.inpaint_base_required') };
  if (!inpaintMaskHasPaint) return { ready: false, message: i18nText('creator.inpaint_mask_required') };
  if (!selectedProviders.length) return { ready: false, message: i18nText('creator.inpaint_model_required') };

  var unsupported = [];
  for (var index = 0; index < selectedProviders.length; index++) {
    var provider = findProvider(selectedProviders[index]);
    var capability = getInpaintCapability(provider);
    if (!capability.supported) {
      unsupported.push({ name: (provider && (provider.name || provider.id)) || selectedProviders[index], reasonCode: capability.reasonCode });
    }
  }
  if (unsupported.length) {
    var names = unsupported.map(function(item) { return item.name; }).join(', ');
    return {
      ready: false,
      message: i18nText('creator.inpaint_provider_unsupported') + '：' + names + '。' + inpaintCapabilityReasonText(unsupported[0].reasonCode)
    };
  }
  return { ready: true, message: i18nText('creator.inpaint_ready') };
}

function updateInpaintAvailability() {
  var readiness = getInpaintReadiness();
  var status = document.getElementById('inpaintProviderStatus');
  if (status) {
    status.textContent = readiness.message;
    status.classList.toggle('is-ready', readiness.ready);
    status.classList.toggle('is-blocked', !readiness.ready);
  }
  if (currentMode !== 'inpaint') {
    if (!genCurrentGenId && !genCancelRequested) {
      var inactiveGenerateButton = document.getElementById('btnGen');
      if (inactiveGenerateButton) inactiveGenerateButton.disabled = false;
    }
    return readiness;
  }
  if (genCurrentGenId || genCancelRequested) return readiness;
  var generateButton = document.getElementById('btnGen');
  if (generateButton) generateButton.disabled = !readiness.ready;
  return readiness;
}

function setInpaintManualChoice(enabled) {
  inpaintManualChoice = !!enabled;
  renderProviderList();
  updateInpaintAvailability();
}

function exportInpaintMask() {
  if (!inpaintSourceImageData || !inpaintMaskHasPaint) return null;
  var sourceMask = document.getElementById('inpaintMaskCanvas');
  if (!sourceMask || !sourceMask.width || !sourceMask.height ||
      sourceMask.width !== inpaintSourceWidth || sourceMask.height !== inpaintSourceHeight) return null;
  var output = document.createElement('canvas');
  output.width = sourceMask.width;
  output.height = sourceMask.height;
  var context = output.getContext('2d');
  context.fillStyle = '#000000';
  context.fillRect(0, 0, output.width, output.height);
  context.drawImage(sourceMask, 0, 0);
  return output.toDataURL('image/png');
}

// ═══════════════════════════════════════════════════════════════════
// 尺寸推断
// ═══════════════════════════════════════════════════════════════════
function inferSize(p) {
  if (!p) return null;
  var l = p.toLowerCase();
  var wide = ['wide','widescreen','21:9','cinematic','panorama','panoramic','landscape','横屏','宽屏','电影感','全景','banner'];
  var tall = ['portrait','vertical','9:16','phone','mobile','poster','竖屏','海报','tall'];
  var por  = ['portrait photo','headshot','face','人像','头像','特写','beauty','fashion','model'];
  for (var i=0;i<wide.length;i++) if(l.indexOf(wide[i])!==-1) return '1792x1024';
  for (var i=0;i<tall.length;i++) if(l.indexOf(tall[i])!==-1) return '1024x1792';
  for (var i=0;i<por.length;i++)  if(l.indexOf(por[i])!==-1)  return '1536x1024';
  return '1024x1024';
}

// ═══════════════════════════════════════════════════════════════════
// 生成图片（异步队列 + 实时进度）
// ═══════════════════════════════════════════════════════════════════
var genPollTimer = null;
var genCurrentGenId = null;
var genCancelRequested = false;
var genDisplayedResults = {};
var genStartTs = 0;
var genTimerInterval = null;
var genIsPrecisionTask = false;

var genProviderCollapsed = {};

// 智能滚动：仅在用户已在底部附近时自动滚动，否则保持当前位置
function _smartScroll(el) {
  if (!el) return;
  var threshold = 80;
  var nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  if (nearBottom) el.scrollTop = el.scrollHeight;
}

function renderGenPerProviderBars(providerStates) {
  var container = document.getElementById('perProviderSection');
  if (!container) return;

  // 按 provider name 分组
  var groups = {};
  Object.keys(providerStates).forEach(function(key) {
    var s = providerStates[key];
    var gname = s.name || s.model || key;
    if (!groups[gname]) groups[gname] = [];
    groups[gname].push({ key: key, state: s });
  });

  var html = '';
  Object.keys(groups).forEach(function(gname) {
    var items = groups[gname];
    var firstState = items[0].state;
    var isCollapsed = !!genProviderCollapsed[gname];
    var groupColor = firstState.color || 'var(--accent)';
    var groupStatus = firstState.status;
    // 整组状态：只要有一个 generating 就算 generating
    items.forEach(function(it) {
      if (it.state.status === 'generating') groupStatus = 'generating';
    });
    var statusIcon = groupStatus === 'completed' ? '✔' : groupStatus === 'failed' ? '✗' : groupStatus === 'generating' ? '⏳' : '•';
    var completedCount = items.filter(function(it) { return it.state.status === 'completed' && it.state.result && it.state.result.success; }).length;
    var failedCount = items.filter(function(it) { return it.state.status === 'failed' || (it.state.result && !it.state.result.success); }).length;
    var totalCount = items.length;

    html += '<div style="margin-bottom:10px;border:1px solid var(--border);border-radius:10px;background:var(--bg-surface);overflow:hidden;">';
    // 组头（可折叠）
    html += '<div onclick="toggleGenProviderGroup(\'' + gname.replace(/'/g, "\\'") + '\')" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;cursor:pointer;background:var(--bg-card);border-bottom:1px solid ' + (isCollapsed ? 'var(--border)' : 'transparent') + ';">';
    html += '<div style="display:flex;align-items:center;gap:8px;">';
    html += '<span style="font-size:10px;transition:transform 0.2s;display:inline-block;transform:rotate(' + (isCollapsed ? '0' : '90') + 'deg);">▶</span>';
    html += '<span style="font-size:12px;font-weight:700;color:' + groupColor + ';">' + escHtml(gname) + '</span>';
    html += '<span style="font-size:10px;color:var(--text-muted);">' + completedCount + '/' + totalCount + '</span>';
    if (failedCount > 0) html += '<span style="font-size:10px;color:#ef4444;">' + failedCount + i18nText('result.failed_count') + '</span>';
    html += '</div>';
    html += '<span style="font-size:10px;color:' + (groupStatus === 'completed' ? '#22c55e' : groupStatus === 'failed' ? '#ef4444' : groupStatus === 'generating' ? 'var(--accent)' : 'var(--text-muted') + ';">' + statusIcon + ' ' + (groupStatus === 'completed' ? i18nText('status.done') : groupStatus === 'generating' ? i18nText('status.generating') : groupStatus === 'failed' ? i18nText('status.failed_plain') : i18nText('status.queued')) + '</span>';
    html += '</div>';

    // 组内容（可折叠）
    if (!isCollapsed) {
      html += '<div style="padding:8px 10px;">';
      items.forEach(function(it) {
        var s = it.state;
        var unsuccessfulTerminal = ['failed', 'error', 'cancelled', 'timeout', 'interrupted'].indexOf(s.status) !== -1;
        var statusText = s.status === 'queued' ? i18nText('status.queuing') : s.status === 'generating' ? i18nText('status.generating') + '...' : s.status === 'completed' ? '? ' + (s.result ? s.result.elapsed_seconds : '') + 's' : s.status === 'cancelled' ? i18nText('status.cancelled') : i18nText('status.failed_icon');
        var statusColor = s.status === 'completed' ? '#22c55e' : unsuccessfulTerminal ? '#ef4444' : s.status === 'generating' ? 'var(--accent)' : 'var(--text-muted)';
        var fillClass = s.status === 'generating' ? 'vprog-fill marquee' : s.status === 'completed' ? 'vprog-fill complete' : 'vprog-fill';
        var numericProgress = Number(s.progress);
        var accessibleProgress = unsuccessfulTerminal ? 0 : s.status === 'completed' ? 100 : Number.isFinite(numericProgress) ? Math.max(0, Math.min(99, numericProgress)) : 0;

        html += '<div style="margin-bottom:6px;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">';
        html += '<span style="font-size:10px;color:var(--text-muted);">#' + (parseInt(it.key.split('_').pop()) + 1) + '</span>';
        html += '<span id="gprog_label_' + it.key + '" style="font-size:10px;color:' + statusColor + ';">' + statusText + '</span>';
        html += '</div>';
        html += '<div role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + Math.round(accessibleProgress) + '" aria-valuetext="' + escAttr(statusText) + '" style="background:var(--border);border-radius:3px;overflow:hidden;height:4px;margin-bottom:3px;">';
        html += '<div class="' + fillClass + '" id="gprog_fill_' + it.key + '" style="width:' + accessibleProgress + '%;"></div>';
        html += '</div>';
        html += '<div id="glog_' + it.key + '" class="vlog-mini" style="display:block;">';
        html += (s.log || []).map(function(line) { return '<div style="color:var(--text-muted);">' + escHtml(line) + '</div>'; }).join('');
        html += '</div>';
        html += '</div>';
      });
      html += '</div>';
    }

    html += '</div>';
  });

  container.innerHTML = html;
  container.style.display = 'block';
  _smartScroll(container);
}

function toggleGenProviderGroup(name) {
  genProviderCollapsed[name] = !genProviderCollapsed[name];
  // 重新渲染需要重新获取 provider_states，通过缓存的 last states
  if (window._lastProviderStates) renderGenPerProviderBars(window._lastProviderStates);
}

function genLogProvider(key, msg, type) {
  var mini = document.getElementById('glog_' + key);
  var ts = new Date().toLocaleTimeString();
  var logColors = { info: 'var(--text-muted)', ok: '#22c55e', warn: '#f59e0b', error: '#ef4444' };
  var color = logColors[type] || logColors.info;
  if (mini) {
    var prefix = type === 'ok' ? '✔' : type === 'error' ? '✗' : type === 'warn' ? '⚠' : '▸';
    var line = document.createElement('div');
    line.style.cssText = 'color:' + color + ';';
    line.textContent = '[' + ts + '] ' + prefix + ' ' + msg;
    mini.appendChild(line);
    _smartScroll(mini);
  }
  var area = document.getElementById('genLogArea');
  if (area) {
    var line2 = document.createElement('div');
    line2.style.cssText = 'color:' + color + ';';
    line2.textContent = '[' + ts + '] ' + key + ': ' + msg;
    area.appendChild(line2);
    _smartScroll(area);
  }
  // Preview per-provider log
  var prevLog = document.getElementById('prev_log_' + key);
  if (prevLog) {
    var prefix2 = type === 'ok' ? '✔' : type === 'error' ? '✗' : type === 'warn' ? '⚠' : '▸';
    var logLine = document.createElement('div');
    logLine.className = 'log-line';
    logLine.style.color = color;
    logLine.textContent = '[' + ts + '] ' + prefix2 + ' ' + msg;
    prevLog.appendChild(logLine);
    prevLog.scrollTop = prevLog.scrollHeight;
  }
}

// ═══════════════════════════════════════════════════════════════════
//  Preview: Placeholder creation & streaming fill
// ═══════════════════════════════════════════════════════════════════

function createPreviewPlaceholders(providerStates) {
  var container = document.getElementById('previewResults');
  var emptyEl = document.getElementById('previewEmpty');
  var mainContent = document.getElementById('previewMainContent');
  if (!container) return;
  if (emptyEl) emptyEl.style.display = 'none';
  if (mainContent) {
    mainContent.classList.remove('hidden');
    mainContent.style.display = 'flex';
  }

  // Remove old placeholder cards only (preserve grouped previews)
  Object.keys(previewPlaceholders).forEach(function(k) {
    var ph = previewPlaceholders[k];
    if (ph && ph.cardEl && ph.cardEl.parentNode) ph.cardEl.remove();
  });
  previewPlaceholders = {};

  // Render existing grouped previews first
  renderGroupedPreviews();

  // Create placeholder cards for pending tasks
  var keys = Object.keys(providerStates);
  for (var i = 0; i < keys.length; i++) {
    var key = keys[i];
    var s = providerStates[key];
    if (s.status === 'completed' || s.status === 'failed') continue;
    var realPid = key.replace(/_\d+$/, '');
    var pInfo = findProvider(realPid) || findProvider(key) || { name: s.name || key, color: '#5b8def' };
    var seq = s.seq !== undefined ? s.seq : (parseInt(key.split('_').pop()) || 0);
    var displayName = pInfo.name + (seq >= 1 ? ' #' + (seq + 1) : '');

    var card = document.createElement('div');
    card.className = 'prev-card generating';
    card.id = 'prev_ph_' + key;

    var border = document.createElement('div');
    border.className = 'prev-card-border';
    card.appendChild(border);

    var ph = document.createElement('div');
    ph.className = 'prev-placeholder';
    ph.innerHTML = '<div class="spinner"></div><div class="ph-text">' + escHtml(displayName) + '</div>';
    card.appendChild(ph);

    var footer = document.createElement('div');
    footer.className = 'prev-footer';
    footer.innerHTML =
      '<div style="display:flex;align-items:center;gap:5px;">' +
        '<span class="provider-dot" style="background:' + pInfo.color + ';"></span>' +
        '<span class="provider-name">' + escHtml(displayName) + '</span>' +
      '</div>' +
      '<span class="elapsed-badge" id="prev_elapsed_' + key + '">' + i18nText('status.queuing') + '</span>';
    card.appendChild(footer);

    container.appendChild(card);

    previewPlaceholders[key] = {
      cardEl: card,
      realPid: realPid,
      color: pInfo.color,
      displayName: displayName,
      state: 'queued'
    };
  }
}

function fillPreviewPlaceholder(key, result) {
  var ph = previewPlaceholders[key];
  var fname = result.local_path.split(/[\\/]/).pop();
  var src = '/api/gallery/image/' + fname;
  var elapsed = result.elapsed_seconds ? result.elapsed_seconds.toFixed(1) + 's' : '';
  var realPid = ph ? ph.realPid : key.replace(/_\d+$/, '');
  var pInfo = ph || {};
  var displayName = pInfo.displayName || (findProvider(realPid) || { name: realPid }).name;

  var imgEntry = { pid: key, realPid: realPid, src: src, name: displayName, color: pInfo.color || '#5b8def', fname: fname };

  // Add to grouped preview (persistent)
  addImageToGroupedPreview(realPid, imgEntry);
  notifyPrecisionFocusActivity('preview');

  // Remove placeholder card
  if (ph && ph.cardEl && ph.cardEl.parentNode) {
    ph.cardEl.remove();
    delete previewPlaceholders[key];
  }

  // Update count
  var totalCount = 0;
  Object.keys(groupedPreviews).forEach(function(k) { totalCount += groupedPreviews[k].images.length; });
  var cnt = document.getElementById('resultCount');
  if (cnt) cnt.textContent = totalCount + i18nText('result.success_count');

  if (ph) ph.state = 'completed';
}

function markPreviewPlaceholderFailed(key, error) {
  var ph = previewPlaceholders[key];
  if (!ph) return;
  var card = ph.cardEl;
  card.className = 'prev-card failed';
  card.style.borderColor = '#ef444444';

  var oldPh = card.querySelector('.prev-placeholder');
  if (oldPh) {
    oldPh.innerHTML = i18nText('result.failure_html');
    oldPh.style.animation = 'none';
  }

  var elapsedBadge = card.querySelector('.elapsed-badge');
  if (elapsedBadge) { elapsedBadge.textContent = i18nText('status.failed_icon'); elapsedBadge.style.color = '#ef4444'; }

  // 添加重试按钮
  var retryBtn = document.createElement('button');
  retryBtn.className = 'prev-retry-btn';
  retryBtn.innerHTML = i18nText('result.retry');
  retryBtn.title = i18nText('result.retry_one');
  retryBtn.onclick = function(e) {
    e.stopPropagation();
    retryProvider(key, ph.realPid);
  };
  card.appendChild(retryBtn);

  ph.state = 'failed';
}

function generationResponseError(response) {
  return response.text().then(function(text) {
    var body = {};
    try {
      body = text ? JSON.parse(text) : {};
    } catch (error) {
      body = {};
    }

    var detail = body && body.detail;
    var message = '';
    var code = '';
    if (detail && typeof detail === 'object') {
      message = typeof detail.message === 'string' ? detail.message : '';
      code = typeof detail.code === 'string' ? detail.code : '';
    } else if (typeof detail === 'string') {
      message = detail;
    }
    if (!message && body && typeof body.error === 'string') {
      message = body.error;
    }

    var error = new Error(message || ('HTTP ' + response.status));
    if (code) error.code = code;
    throw error;
  });
}

function applyPrecisionEditPayload(payload, context) {
  context = context || {};
  payload.operation = 'precision_edit';
  payload.image_data = context.imageData;
  payload.precision_strategy = ['fine', 'standard', 'fast'].indexOf(context.strategy) !== -1 ? context.strategy : 'standard';
  payload.precision_selection_mode = context.selectionMode === 'local' ? 'local' : 'annotation';
  if (payload.precision_selection_mode === 'local') {
    var feather = Number(context.selectionFeather);
    payload.precision_selection_feather = Number.isFinite(feather) ? Math.max(0, Math.min(64, Math.round(feather))) : 0;
  }
  payload.precision_size_mode = context.sizeMode === 'resize' ? 'resize' : 'preserve';
  if (payload.precision_size_mode === 'resize') {
    payload.precision_target_size = context.targetSize;
    payload.precision_resize_prompt = context.resizePrompt;
    payload.precision_output_size_policy = sanitizePrecisionOutputSizePolicy(context.outputSizePolicy);
  }
  var annotations = Array.isArray(context.annotations)
    ? context.annotations
    : context.annotationData && Array.isArray(context.annotationData.objects)
      ? context.annotationData.objects
      : [];
  var requestAnnotations = serializePrecisionAnnotationsForRequest(annotations);
  if (context.annotationImageData && context.annotationContract && requestAnnotations.length) {
    payload.annotation_contract = context.annotationContract || PRECISION_ANNOTATION_CONTRACT;
    payload.annotation_image_data = context.annotationImageData;
    payload.annotations = requestAnnotations;
  }
  return payload;
}

function precisionRetryModelError(pid) {
  var error = new Error(i18nText('creator.precision_retry_model_required'));
  error.code = 'precision_edit_retry_model_required';
  error.detail = {
    code: error.code,
    provider_id: pid,
    message: error.message
  };
  return error;
}

function precisionRetryModelForProvider(pid) {
  var provider = findProvider(pid);
  var settings = lastGenContext && lastGenContext.provider_settings;
  var model = settings && settings[pid] && typeof settings[pid].model === 'string'
    ? settings[pid].model.trim() : '';
  if (!provider || !model) throw precisionRetryModelError(pid);
  var models = precisionProviderModelRecords(provider);
  var currentModel = models.some(function(record) { return record.id === model; });
  if (!currentModel) throw precisionRetryModelError(pid);
  return model;
}

function showPrecisionRetryModelError(error) {
  var message = error && error.message ? error.message : i18nText('creator.precision_retry_model_required');
  var code = error && error.code ? error.code : 'precision_edit_retry_model_required';
  var text = message + ' [' + code + ']';
  setStatus(text);
  alert(text);
}

function retryProvider(key, realPid) {
  if (!lastGenContext) { alert(i18nText('result.retry_missing')); return; }

  var pid = realPid || key.replace(/_\d+$/, '');
  var providerInfo = findProvider(pid) || { name: pid };
  var precisionRetryModel = '';
  if (lastGenContext.mode === 'precision_edit') {
    try {
      precisionRetryModel = precisionRetryModelForProvider(pid);
    } catch (error) {
      showPrecisionRetryModelError(error);
      return false;
    }
  }
  if (!confirm(i18nText('result.retry_prefix') + providerInfo.name + '??')) return;

  if (key.indexOf('_') !== -1) {
    var parts = key.split('_');
    parseInt(parts[parts.length - 1]) || 0;
  }

  var btn = document.getElementById('btnGen');
  if (btn) { btn.disabled = true; btn.innerHTML = i18nText('result.retrying'); }

  var payload = {
    prompt: lastGenContext.prompt,
    providers: [pid],
    quantities: {},
    mode: lastGenContext.mode,
    size: lastGenContext.size,
    quality: lastGenContext.quality || undefined,
    enhance_prompt: false,
    continuous: false,
  };
  if (lastGenContext.system_prompt) payload.system_prompt = lastGenContext.system_prompt;
  if (lastGenContext.mode === 'i2i' && lastGenContext.image_data) {
    payload.image_data = lastGenContext.image_data;
    payload.image_data_list = lastGenContext.image_data_list || [lastGenContext.image_data];
    payload.strength = lastGenContext.strength;
  } else if (lastGenContext.mode === 'precision_edit' && lastGenContext.image_data) {
    delete payload.size;
    applyPrecisionEditPayload(payload, {
      imageData: lastGenContext.image_data,
      strategy: lastGenContext.precision_strategy,
      selectionMode: lastGenContext.precision_selection_mode,
      selectionFeather: lastGenContext.precision_selection_feather,
      sizeMode: lastGenContext.precision_size_mode,
      targetSize: lastGenContext.precision_target_size,
      resizePrompt: lastGenContext.precision_resize_prompt,
      outputSizePolicy: lastGenContext.precision_output_size_policy,
      annotationContract: lastGenContext.annotation_contract,
      annotationImageData: lastGenContext.annotation_image_data,
      annotations: lastGenContext.annotations
    });
    payload.provider_settings = {};
    payload.provider_settings[pid] = { model: precisionRetryModel };
  } else if (lastGenContext.mode === 'inpaint' && lastGenContext.image_data && lastGenContext.mask_data) {
    payload.image_data = lastGenContext.image_data;
    payload.mask_data = lastGenContext.mask_data;
    payload.mask_contract = lastGenContext.mask_contract || INPAINT_MASK_CONTRACT;
  }

  return _authFetch('/api/generate', {
    method: 'POST',
    body: JSON.stringify(payload)
  }).then(function(r) {
    if (!r.ok) return generationResponseError(r);
    return r.json();
  }).then(function(data) {
    if (data.generation_id) {
      setStatus(i18nText('result.retry_submitted') + providerInfo.name);
      startGenPolling(data.generation_id);
    }
  }).catch(function(e) {
    alert(i18nText('result.retry_failed') + e.message);
    if (btn) { btn.disabled = false; btn.innerHTML = i18nText('creator.generate_image_sparkle'); }
  });
}

function renderGroupedPreviews() {
  var container = document.getElementById('previewResults');
  if (!container) return;
  // Only remove grouped cards, preserve placeholder cards
  container.querySelectorAll('.grouped-card').forEach(function(el) { el.remove(); });
  var rPids = Object.keys(groupedPreviews);
  if (rPids.length === 0 && Object.keys(previewPlaceholders).length === 0) {
  var emptyEl = document.getElementById('previewEmpty');
  if (emptyEl) emptyEl.style.display = '';
  var mainContent = document.getElementById('previewMainContent');
  if (mainContent) {
    mainContent.classList.add('hidden');
    mainContent.style.display = 'none';
  }
  return;
}
var emptyEl = document.getElementById('previewEmpty');
if (emptyEl) emptyEl.style.display = 'none';
var mainContent = document.getElementById('previewMainContent');
if (mainContent) {
  mainContent.classList.remove('hidden');
  mainContent.style.display = 'flex';
}
  for (var i = 0; i < rPids.length; i++) {
    container.appendChild(buildGroupCard(rPids[i]));
  }
}

function buildGroupCard(realPid) {
  var group = groupedPreviews[realPid];
  if (!group || !group.images.length) return document.createElement('div');
  var img = group.images[group.activeIdx];
  var total = group.images.length;

  var card = document.createElement('div');
  card.className = 'prev-card completed grouped-card';
  card.id = 'grouped_' + realPid;

  var border = document.createElement('div');
  border.className = 'prev-card-border';
  card.appendChild(border);

  var imgEl = document.createElement('img');
  imgEl.className = 'prev-img';
  imgEl.src = img.src;
  imgEl.alt = img.name;
  card.appendChild(imgEl);

  card.onclick = function() { openLightbox(img.src, img.name); };

  if (total > 1) {
    var idx = { value: group.activeIdx };
    var btnL = document.createElement('button');
    btnL.className = 'prev-arrow prev-arrow-left';
    btnL.innerHTML = '‹';
    btnL.onclick = function(e) {
      e.stopPropagation();
      idx.value = (idx.value - 1 + total) % total;
      group.activeIdx = idx.value;
      var newImg = group.images[idx.value];
      imgEl.src = newImg.src;
      imgEl.alt = newImg.name;
      card.onclick = function() { openLightbox(newImg.src, newImg.name); };
      var nameEl = card.querySelector('.prev-group-label');
      if (nameEl) nameEl.textContent = newImg.name;
      var cntEl = card.querySelector('.prev-group-count');
      if (cntEl) cntEl.textContent = (idx.value + 1) + '/' + total;
    };
    card.appendChild(btnL);
    var btnR = document.createElement('button');
    btnR.className = 'prev-arrow prev-arrow-right';
    btnR.innerHTML = '›';
    btnR.onclick = function(e) {
      e.stopPropagation();
      idx.value = (idx.value + 1) % total;
      group.activeIdx = idx.value;
      var newImg = group.images[idx.value];
      imgEl.src = newImg.src;
      imgEl.alt = newImg.name;
      card.onclick = function() { openLightbox(newImg.src, newImg.name); };
      var nameEl = card.querySelector('.prev-group-label');
      if (nameEl) nameEl.textContent = newImg.name;
      var cntEl = card.querySelector('.prev-group-count');
      if (cntEl) cntEl.textContent = (idx.value + 1) + '/' + total;
    };
    card.appendChild(btnR);
  }

  var countBadge = document.createElement('div');
  countBadge.className = 'prev-group-count';
  countBadge.textContent = total > 1 ? '1/' + total : '1/1';
  card.appendChild(countBadge);

  var footer = document.createElement('div');
  footer.className = 'prev-footer';
  footer.innerHTML =
    '<div style="display:flex;align-items:center;gap:5px;">' +
      '<span class="provider-dot" style="background:' + (group.color || '#5b8def') + ';"></span>' +
      '<span class="provider-name">' + escHtml(group.name || realPid) + '</span>' +
    '</div>';
  card.appendChild(footer);

  var label = document.createElement('div');
  label.className = 'prev-group-label';
  label.textContent = img.name;
  card.appendChild(label);

  return card;
}

function addImageToGroupedPreview(realPid, imgData) {
  if (!groupedPreviews[realPid]) {
    groupedPreviews[realPid] = {
      images: [],
      activeIdx: 0,
      name: imgData.name || realPid,
      color: imgData.color || '#5b8def'
    };
  }
  groupedPreviews[realPid].images.push(imgData);
  renderGroupedPreviews();
}

function clearGroupedPreviews() {
  groupedPreviews = {};
  previewImages = [];
  previewGroups = {};
  failedGroups = {};
  renderGroupedPreviews();
  var cnt = document.getElementById('resultCount');
  if (cnt) cnt.textContent = '';
}

function _updateGroupArrows(realPid, groupImgs) {
  if (groupImgs.length <= 1) return;
  // Find first card for this group and add arrows if not already present
  var firstEntry = groupImgs[0];
  var firstKey = null;
  var keys = Object.keys(previewPlaceholders);
  for (var i = 0; i < keys.length; i++) {
    if (previewPlaceholders[keys[i]].realPid === realPid) { firstKey = keys[i]; break; }
  }
  if (!firstKey) return;

  var card = previewPlaceholders[firstKey].cardEl;
  if (card.querySelector('.prev-arrow')) return; // already has arrows

  var idx = { value: 0 };

  var btnL = document.createElement('button');
  btnL.className = 'prev-arrow prev-arrow-left';
  btnL.innerHTML = '‹';
  btnL.onclick = function(e) {
    e.stopPropagation();
    idx.value = (idx.value - 1 + groupImgs.length) % groupImgs.length;
    _refreshGroupCard(card, groupImgs, idx.value, realPid);
  };
  card.appendChild(btnL);

  var btnR = document.createElement('button');
  btnR.className = 'prev-arrow prev-arrow-right';
  btnR.innerHTML = '›';
  btnR.onclick = function(e) {
    e.stopPropagation();
    idx.value = (idx.value + 1) % groupImgs.length;
    _refreshGroupCard(card, groupImgs, idx.value, realPid);
  };
  card.appendChild(btnR);

  // Store nav state
  card._groupIdx = idx;
  card._groupImgs = groupImgs;
}

function _refreshGroupCard(card, groupImgs, newIdx, realPid) {
  var imgEl = card.querySelector('.prev-img');
  if (imgEl) {
    imgEl.src = groupImgs[newIdx].src;
    imgEl.alt = groupImgs[newIdx].name;
  }
  // Update card click handler
  (function(s, n) {
    card.onclick = function() { openLightbox(s, n); };
  })(groupImgs[newIdx].src, groupImgs[newIdx].name);
  var nameEl = card.querySelector('.provider-name');
  if (nameEl) nameEl.textContent = groupImgs[newIdx].name;
}

function updatePreviewLogSections(providerStates) {
  var section = document.getElementById('previewLogSection');
  var grid = document.getElementById('previewLogGrid');
  if (!section || !grid) return;

  var keys = Object.keys(providerStates);
  var hasLogs = false;

  for (var i = 0; i < keys.length; i++) {
    var key = keys[i];
    var s = providerStates[key];
    var logs = s.log || [];
    if (logs.length > 0) hasLogs = true;
  }

  if (!hasLogs) {
    section.classList.add('hidden');
    return;
  }

  section.classList.remove('hidden');
  var html = '';

  for (var i = 0; i < keys.length; i++) {
    var key = keys[i];
    var s = providerStates[key];
    var logs = s.log || [];
    if (logs.length === 0) continue;

    var realPid = key.replace(/_\d+$/, '');
    var pInfo = findProvider(realPid) || findProvider(key) || { name: s.name || key, color: '#5b8def' };
    var status = s.status || 'queued';
    var dotColor = status === 'completed' ? '#22c55e' : status === 'failed' ? '#ef4444' : status === 'generating' ? 'var(--accent)' : 'var(--text-muted)';

    html += '<div class="prev-log-card" id="prev_log_' + key + '">';
    html += '<div class="log-header"><span class="log-dot" style="background:' + dotColor + ';"></span><span>' + escHtml(pInfo.name) + '</span></div>';
    for (var j = 0; j < logs.length; j++) {
      html += '<div class="log-line">' + escHtml(logs[j]) + '</div>';
    }
    html += '</div>';
  }

  grid.innerHTML = html;

  // Auto-scroll latest log cards
  var cards = grid.querySelectorAll('.prev-log-card');
  for (var c = 0; c < cards.length; c++) {
    cards[c].scrollTop = cards[c].scrollHeight;
  }
}

function updateGenerationProgress(value, valueText) {
  var bar = document.getElementById('generationProgressBar');
  var fill = document.getElementById('progressFill');
  var numeric = Number(value);
  var bounded = Number.isFinite(numeric) ? Math.max(0, Math.min(100, numeric)) : 0;
  if (fill) fill.style.width = bounded + '%';
  if (bar) {
    bar.setAttribute('aria-valuenow', String(Math.round(bounded)));
    bar.setAttribute('aria-valuetext', valueText || Math.round(bounded) + '%');
  }
}

function showGenerationProgressCloseButton(show) {
  var button = document.getElementById('progressCloseBtn');
  if (!button) return;
  button.classList.toggle('hidden', !show);
  button.style.display = show ? 'inline-block' : 'none';
}

function generationFailureMessage(data) {
  var sizeNotices = precisionOutputSizeNotices(data);
  if (sizeNotices.length) return sizeNotices[0];
  var transportNotices = precisionTransportFailureNotices(data);
  if (transportNotices.length) return transportNotices[0];
  if (data && data.error) return String(data.error);
  var states = data && data.provider_states ? data.provider_states : {};
  var keys = Object.keys(states);
  for (var i = 0; i < keys.length; i++) {
    var state = states[keys[i]] || {};
    if (state.error) return String(state.error);
    if (state.result && state.result.error) return String(state.result.error);
  }
  return i18nText('status.failed');
}

function finishGenerationTerminalStatus(data, precisionTask) {
  var terminalStatus = String(data && data.status || '').toLowerCase();
  if (['cancelled', 'failed', 'completed'].indexOf(terminalStatus) === -1) return false;

  var ptxt = document.getElementById('progressText');
  if (precisionTask) updatePrecisionTaskMonitor(data);

  if (terminalStatus === 'cancelled') {
    stopGenPolling();
    genCurrentGenId = null;
    genCancelRequested = false;
    currentResults = data.results || {};
    currentGroupTimings = data.group_timings || {};
    if (ptxt) ptxt.textContent = i18nText('status.cancelled');
    if (!precisionTask) updateGenerationProgress(0, i18nText('status.cancelled'));
    showGenerationProgressCloseButton(true);
    setStatus(i18nText('status.cancelled'));
    setGenerationControls('idle');
    return true;
  }

  if (data.status === 'failed') {
    stopGenPolling();
    genCurrentGenId = null;
    genCancelRequested = false;
    if (!precisionTask) {
      currentResults = data.results || {};
      currentGroupTimings = data.group_timings || {};
    }
    var failureMessage = generationFailureMessage(data);
    if (ptxt) ptxt.textContent = i18nText('status.failed_plain') + ': ' + failureMessage;
    if (!precisionTask) updateGenerationProgress(0, i18nText('status.failed_plain') + ': ' + failureMessage);
    setStatus(i18nText('status.failed_plain') + ': ' + failureMessage);
    setGenerationControls('idle');
    showGenerationProgressCloseButton(true);
    return true;
  }

  stopGenPolling();
  genCurrentGenId = null;
  genCancelRequested = false;
  var elapsedEl = document.getElementById('elapsedSeconds');
  if (elapsedEl && data.elapsed_seconds !== undefined) elapsedEl.textContent = data.elapsed_seconds.toFixed(1);
  currentResults = data.results || {};
  currentGroupTimings = data.group_timings || {};
  if (data.continuous_id) window.continuousSessionId = data.continuous_id;
  if (data.enhanced_prompt) showEnhanceResult(data.enhanced_prompt);
  if (data.llm_error && !data.enhanced_prompt) showEnhanceResult('⚠️ ' + data.llm_error);
  showResults(currentResults, '', currentGroupTimings);
  if (precisionTask && precisionTaskSourceGeneration === precisionSourceLoadGeneration && precisionEditSession.taskSourceGeneration === precisionTaskSourceGeneration) {
    Object.keys(currentResults).forEach(function(key) { appendPrecisionEditVersion(currentResults[key], precisionTaskSourceGeneration); });
  }
  var pfill = document.getElementById('progressFill');
  if (pfill && !precisionTask) updateGenerationProgress(100, i18nText('status.done'));
  var okCount = Object.values(currentResults).filter(function(result) { return result.success; }).length;
  var totalProviders = Object.keys(data.provider_states || {}).length;
  if (ptxt) ptxt.textContent = i18nText('result.complete_prefix') + okCount + '/' + totalProviders + i18nText('result.success_suffix');
  setStatus(i18nText('result.complete_middle') + okCount + '/' + totalProviders + i18nText('result.success_middle') + (data.elapsed_seconds || 0) + 's');
  loadGallery();
  setGenerationControls('idle');
  showGenerationProgressCloseButton(true);
  var logWrap = document.getElementById('genLogWrap');
  if (logWrap) { var cnt = document.getElementById('genLogCount'); if (cnt) cnt.textContent = i18nText('common.done'); }
  return true;
}

function startGenPolling(genId) {
  genCurrentGenId = genId;
  genIsPrecisionTask = !!(lastGenContext && lastGenContext.mode === 'precision_edit');
  if (genIsPrecisionTask) {
    precisionTaskSourceGeneration = precisionSourceLoadGeneration;
    precisionEditSession.taskId = genId;
    precisionEditSession.taskSourceGeneration = precisionTaskSourceGeneration;
  }
  setGenerationControls('generating');
  genDisplayedResults = {};
  window._placeholdersCreated = false;
  // 继续使用 genStartTs（提交阶段已设置），不停表
  var elapsedEl = document.getElementById('elapsedSeconds');
  if (genTimerInterval) clearInterval(genTimerInterval);
  genTimerInterval = setInterval(function() {
    var elapsed = ((Date.now() - genStartTs) / 1000).toFixed(1);
    if (elapsedEl) elapsedEl.textContent = elapsed;
  }, 200);
  var pollCount = 0;
  genPollTimer = setInterval(function() {
    pollCount++;
    fetchGenerationStatus(genId).then(function(data) {
      // A cancelled task can have one final status response in flight. Ignore it
      // once the user has moved on so it cannot overwrite the newer UI state.
      if (genId !== genCurrentGenId) return;
      var pfill = document.getElementById('progressFill');
      var ptxt = document.getElementById('progressText');
      if (pfill && !genIsPrecisionTask) updateGenerationProgress(data.progress, String(data.status || i18nText('status.generating')));

      // 更新进度文本
      if (ptxt && !genIsPrecisionTask && data.status !== 'completed') {
        var states = data.provider_states || {};
        var names = Object.keys(states).map(function(k) { return states[k].name || k; });
        var generating = Object.values(states).filter(function(s) { return s.status === 'generating'; });
        var done = Object.values(states).filter(function(s) { return s.status === 'completed' || s.status === 'failed' || s.status === 'cancelled'; });
        if (generating.length > 0) {
          if (ptxt) ptxt.textContent = generating.map(function(s) { return s.name || s.model; }).join(', ') + i18nText('status.generating_prefix') + done.length + '/' + names.length + i18nText('status.complete_paren');
        } else if (done.length < names.length) {
          if (ptxt) ptxt.textContent = i18nText('status.queued_prefix') + done.length + '/' + names.length + i18nText('status.complete_paren');
        }
      }

      if (genIsPrecisionTask) updatePrecisionTaskMonitor(data);
      if (genIsPrecisionTask && precisionTaskMonitorIsTerminal(data.status) && ['completed', 'failed', 'cancelled'].indexOf(data.status) === -1) {
        stopGenPolling();
        genCurrentGenId = null;
        genCancelRequested = false;
        setGenerationControls('idle');
      }
      if (data.provider_states && !genIsPrecisionTask) {
        window._lastProviderStates = data.provider_states;
        // 第一次收到 provider_states 时创建占位符
        if (!window._placeholdersCreated) {
          window._placeholdersCreated = true;
          createPreviewPlaceholders(data.provider_states);
        }
        renderGenPerProviderBars(data.provider_states);
        // 更新实时日志（旧的全局日志区域，保留兼容）
        var logEl = document.getElementById('genLogArea');
        if (logEl) {
          var allLogs = [];
          Object.keys(data.provider_states).forEach(function(k) {
            var logs = data.provider_states[k].log || [];
            logs.forEach(function(l) { if (allLogs.indexOf(l) === -1) allLogs.push(l); });
          });
          if (allLogs.length > 0) logEl.textContent = allLogs.join('\n');
        }
        // 更新预览区 per-provider 日志
        updatePreviewLogSections(data.provider_states);
        Object.keys(data.provider_states).forEach(function(key) {
          var s = data.provider_states[key];
          // 增量：占位符填图
          if (s.status === 'completed' && s.result && s.result.success && s.result.local_path && !genDisplayedResults[key]) {
            genDisplayedResults[key] = s.result;
            fillPreviewPlaceholder(key, s.result);
          }
          // 增量：标记失败
          if ((s.status === 'failed' || (s.result && !s.result.success)) && previewPlaceholders[key] && previewPlaceholders[key].state === 'queued') {
            markPreviewPlaceholderFailed(key, s.error || (s.result && s.result.error) || i18nText('status.failed'));
          }
        });
      }

      finishGenerationTerminalStatus(data, genIsPrecisionTask);
    }).catch(function(e) {
      console.error('Poll error:', e);
    });
  }, 1500);
}

function stopGenPolling() {
  if (genPollTimer) { clearInterval(genPollTimer); genPollTimer = null; }
  if (genTimerInterval) { clearInterval(genTimerInterval); genTimerInterval = null; }
}

function fetchGenerationStatus(genId) {
  return _authFetch('/api/generate/status/' + encodeURIComponent(genId)).then(function(response) {
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
  });
}

function resolveCancellationTerminalPayload(genId, cancelData) {
  var cancelStatus = String(cancelData && cancelData.status || '').toLowerCase();
  if (['cancelled', 'completed', 'failed'].indexOf(cancelStatus) === -1) {
    return Promise.reject(new Error('Unexpected cancellation status: ' + (cancelStatus || 'unknown')));
  }
  return fetchGenerationStatus(genId);
}

function setGenerationControls(state) {
  var nextControlState = state || 'idle';
  if (nextControlState !== precisionGenerationControlState) {
    precisionSourceTaskEpoch += 1;
    precisionPendingSourceIntent = null;
  }
  precisionGenerationControlState = nextControlState;
  var generateButton = document.getElementById('btnGen');
  var stopButton = document.getElementById('btnStopGen');
  updatePrecisionSourceActions();
  if (!generateButton || !stopButton) return;

  if (state === 'submitting') {
    generateButton.disabled = true;
    generateButton.innerHTML = i18nText('status.submitting_html');
    stopButton.classList.add('hidden');
    stopButton.disabled = false;
    return;
  }
  if (state === 'generating') {
    generateButton.disabled = true;
    generateButton.innerHTML = i18nText('status.generating_html');
    stopButton.classList.remove('hidden');
    stopButton.disabled = false;
    stopButton.innerHTML = i18nText('creator.stop_generation');
    return;
  }
  if (state === 'cancelling') {
    generateButton.disabled = true;
    generateButton.innerHTML = i18nText('status.cancelling_html');
    stopButton.classList.remove('hidden');
    stopButton.disabled = true;
    stopButton.innerHTML = i18nText('status.cancelling_html');
    return;
  }

  generateButton.disabled = false;
  generateButton.innerHTML = i18nText('creator.generate_image_sparkle');
  stopButton.classList.add('hidden');
  stopButton.disabled = false;
  stopButton.innerHTML = i18nText('creator.stop_generation');
  if (currentMode === 'inpaint') {
    generateButton.disabled = !getInpaintReadiness().ready;
  } else if (currentMode === 'precision_edit') {
    generateButton.disabled = !getPrecisionEditReadiness().ready;
  }
}

function cancelCurrentGeneration() {
  if (!genCurrentGenId || genCancelRequested) return;
  var cancelGenId = genCurrentGenId;
  var cancelledPrecisionTask = genIsPrecisionTask;
  genCancelRequested = true;
  setGenerationControls('cancelling');
  return _authFetch('/api/generate/cancel/' + encodeURIComponent(cancelGenId), { method: 'POST' })
    .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(cancelData) { return resolveCancellationTerminalPayload(cancelGenId, cancelData); })
    .then(function(terminalData) {
      if (cancelGenId !== genCurrentGenId) return;
      var terminalStatus = String(terminalData && terminalData.status || '').toLowerCase();
      if (!finishGenerationTerminalStatus(terminalData, cancelledPrecisionTask)) {
        throw new Error('Unexpected terminal status: ' + (terminalStatus || 'unknown'));
      }
    })
    .catch(function(e) {
      genCancelRequested = false;
      setGenerationControls(genCurrentGenId ? 'generating' : 'idle');
      setStatus(i18nText('status.cancel_failed') + e.message);
    });
}

function doGenerate() {
  var prompt = '';
  var systemPrompt = null;
  var inpaintMaskData = null;
  var precisionAnnotationImage = null;
  var precisionAnnotationData = null;
  var precisionSizeRequest = null;
  if (currentMode === 't2i') {
    prompt = getFinalPrompt();
    if (promptMode === 'pro') {
      systemPrompt = document.getElementById('txtSysPrompt').value.trim();
    }
  } else if (currentMode === 'i2i') {
    prompt = document.getElementById('txtPromptI2I').value.trim();
    if (!prompt && !uploadedImageData) { alert(i18nText('creator.reference_or_prompt')); return; }
    if (!uploadedImageData) { alert(i18nText('creator.reference_required')); return; }
  } else if (currentMode === 'inpaint') {
    prompt = document.getElementById('txtPromptInpaint').value.trim();
    var inpaintReadiness = updateInpaintAvailability();
    if (!inpaintReadiness.ready) { alert(inpaintReadiness.message); return; }
    inpaintMaskData = exportInpaintMask();
    if (!inpaintMaskData) { alert(i18nText('creator.inpaint_mask_required')); return; }
  } else if (currentMode === 'precision_edit') {
    prompt = (document.getElementById('txtPromptPrecision') || { value: '' }).value.trim();
    var precisionReadiness = updatePrecisionEditControls();
    if (!precisionReadiness.ready) { alert(precisionReadiness.message); return; }
    precisionSizeRequest = getPrecisionSizeRequest();
    if (precisionSizeRequest.error) { alert(precisionSizeRequest.error); return; }
    if (!precisionReadiness.pureResize) {
      precisionAnnotationImage = exportPrecisionEditAnnotationImage();
      precisionAnnotationData = buildPrecisionEditAnnotationData();
      if (!precisionAnnotationImage || !precisionAnnotationData || !precisionAnnotationData.objects.length) {
        alert(i18nText('creator.precision_annotation_required'));
        return;
      }
    }
  }
  if (!prompt && currentMode !== 'precision_edit') { alert(i18nText('creator.prompt_required')); return; }
  if (!selectedProviders.length) { alert(i18nText('creator.model_required')); return; }

  genCancelRequested = false;
  genIsPrecisionTask = currentMode === 'precision_edit';
  precisionTaskSourceGeneration = genIsPrecisionTask ? precisionSourceLoadGeneration : 0;
  if (genIsPrecisionTask) precisionEditSession.taskSourceGeneration = precisionTaskSourceGeneration;
  setGenerationControls('submitting');

  var pbox = document.getElementById('progressBox');
  var ptxt = document.getElementById('progressText');
  var pfill = document.getElementById('progressFill');
  var elapsedEl = document.getElementById('elapsedSeconds');
  var perSection = document.getElementById('perProviderSection');
  var logWrap = document.getElementById('genLogWrap');
  var logArea = document.getElementById('genLogArea');
  var logCount = document.getElementById('genLogCount');
  pbox.classList.remove('hidden');
  showGenerationProgressCloseButton(false);
  if (isPrecisionFocusActive()) {
    notifyPrecisionFocusActivity('task');
    // Preserve an explicitly opened monitor. Otherwise keep the annotation
    // canvas in place and surface progress through the task toggle.
    showCreatorTaskMonitor(!precisionFocusState.taskCollapsed);
  } else {
    showCreatorTaskMonitor(true);
  }
  ptxt.textContent = i18nText('status.submitting');
  updateGenerationProgress(5, i18nText('status.submitting'));
  elapsedEl.textContent = '0.0';
  if (perSection) { perSection.innerHTML = ''; perSection.style.display = 'none'; }
  if (logWrap) logWrap.style.display = 'block';
  if (logArea) logArea.innerHTML = '';
  if (logCount) logCount.textContent = '';
  // Hide preview log section for new generation
  var previewLogSection = document.getElementById('previewLogSection');
  if (previewLogSection) previewLogSection.classList.add('hidden');

  genStartTs = Date.now();
  var timerInterval = setInterval(function() {
    var elapsed = ((Date.now() - genStartTs) / 1000).toFixed(1);
    elapsedEl.textContent = elapsed;
  }, 200);

  // 从图像设置面板构建参数
  var imageSettings = loadProviderSettings();
  var selectedModel = document.getElementById('selModel').value || '_global';

  // 获取当前模型的设置（fallback 到全局）
  var currentSettings = imageSettings[selectedModel] || imageSettings['_global'] || {};
  var genQuality = currentSettings.quality || '';
  // Visible controls are authoritative. This keeps ratio and dimensions
  // synchronized even when older localStorage values are stale.
  var genRatio = document.getElementById('selRatio').value || currentSettings.ratio || '1:1';
  var genW = parseInt(document.getElementById('inputW').value, 10) || currentSettings.w || 1024;
  var genH = parseInt(document.getElementById('inputH').value, 10) || currentSettings.h || 1024;
  // The visible control is authoritative. Cached per-model settings may be stale
  // after an older release or a model switch and must not multiply the request.
  var visibleQty = parseInt(document.getElementById('selQty').value, 10);
  var genQty = Number.isFinite(visibleQty) ? Math.max(1, Math.min(10, visibleQty)) : 1;

  // 构建尺寸
  var genSize;
  if (genRatio === 'auto') {
    genSize = inferSize(prompt);
  } else if (genRatio && RATIO_SIZES[genRatio]) {
    var rsz = RATIO_SIZES[genRatio];
    genSize = rsz[0] + 'x' + rsz[1];
  } else {
    genSize = genW + 'x' + genH;
  }

  // 构建 quantities（所有选中的 provider 都用同一个数量）
  var qtyMap = {};
  for (var qi = 0; qi < selectedProviders.length; qi++) {
    qtyMap[selectedProviders[qi]] = genQty;
  }

  // 如果选了特定模型，更新对应 provider 的 model
  if (selectedModel !== '_global') {
    for (var pi = 0; pi < allProviders.length; pi++) {
      if (allProviders[pi].type === 'image' && selectedProviders.indexOf(allProviders[pi].id) >= 0) {
        allProviders[pi].model = selectedModel;
      }
    }
  }

  var payload = {
    prompt: prompt,
    providers: selectedProviders,
    enhance_prompt: document.getElementById('chkEnhance').checked,
    llm_provider_id: localStorage.getItem('igs_llm_provider') || undefined,
    mode: currentMode,
    quality: genQuality || undefined,
    continuous: document.getElementById('chkContinuous').checked,
    system_prompt: systemPrompt,
    continuous_id: window.continuousSessionId || null,
    quantities: qtyMap,
    exact_ratio_crop: Boolean(document.getElementById('chkExactRatioCrop') && document.getElementById('chkExactRatioCrop').checked),
  };
  if (currentMode !== 'precision_edit') payload.size = genSize;
  if (currentMode === 'i2i' && uploadedImageData) {
    payload.image_data = uploadedImageData;
    payload.image_data_list = uploadedImageDataList.filter(Boolean);
    payload.strength = parseFloat(document.getElementById('selStrength').value);
  } else if (currentMode === 'precision_edit') {
    // The source is never replaced locally. Annotated edits carry the V3
    // overlay; pure resize submits only the explicit resize envelope.
    applyPrecisionEditPayload(payload, {
      imageData: precisionEditSourceImageData,
      strategy: precisionEditStrategy,
      selectionMode: precisionEditSelectionMode,
      selectionFeather: precisionSelectionFeather,
      sizeMode: precisionSizeRequest.mode,
      targetSize: precisionSizeRequest.targetSize,
      resizePrompt: precisionSizeRequest.prompt,
      outputSizePolicy: precisionSizeRequest.outputSizePolicy,
      annotationContract: PRECISION_ANNOTATION_CONTRACT,
      annotationImageData: precisionAnnotationImage,
      annotations: precisionAnnotationData ? precisionAnnotationData.objects : []
    });
    payload.provider_settings = {};
    if (precisionEditSelectedModel.providerId && precisionEditSelectedModel.model) {
      payload.provider_settings[precisionEditSelectedModel.providerId] = { model: precisionEditSelectedModel.model };
    }
  } else if (currentMode === 'inpaint') {
    payload.mode = 'inpaint';
    payload.image_data = inpaintSourceImageData;
    payload.mask_data = inpaintMaskData;
    payload.mask_contract = INPAINT_MASK_CONTRACT;
  }
  // 尺寸自适应参数
  if (currentMode !== 'precision_edit' && document.getElementById('chkUpscale').checked) {
    payload.upscale_to = document.getElementById('upscaleSize').value;
    payload.upscale_method = document.getElementById('upscaleMethod').value;
    payload.upscale_ratio = document.getElementById('upscaleRatio').value;
  }

  // 保存生图上下文，用于单模型重试
  lastGenContext = {
    prompt: prompt,
    system_prompt: systemPrompt,
    mode: currentMode,
    size: currentMode === 'precision_edit' ? (precisionSizeRequest && precisionSizeRequest.targetSize || null) : genSize,
    quality: genQuality,
    image_data: currentMode === 'inpaint' ? inpaintSourceImageData : currentMode === 'precision_edit' ? precisionEditSourceImageData : uploadedImageData,
    image_data_list: currentMode === 'i2i' ? uploadedImageDataList.filter(Boolean) : [],
    mask_data: currentMode === 'inpaint' ? inpaintMaskData : null,
    mask_contract: currentMode === 'inpaint' ? INPAINT_MASK_CONTRACT : null,
    annotation_image_data: currentMode === 'precision_edit' ? precisionAnnotationImage : null,
    annotation_contract: currentMode === 'precision_edit' ? PRECISION_ANNOTATION_CONTRACT : null,
    annotations: currentMode === 'precision_edit' && payload.annotations ? precisionEditClone(payload.annotations) : [],
    precision_size_mode: currentMode === 'precision_edit' && precisionSizeRequest ? precisionSizeRequest.mode : null,
    precision_target_size: currentMode === 'precision_edit' && precisionSizeRequest ? precisionSizeRequest.targetSize || null : null,
    precision_resize_prompt: currentMode === 'precision_edit' && precisionSizeRequest ? precisionSizeRequest.prompt || null : null,
    precision_output_size_policy: currentMode === 'precision_edit' && precisionSizeRequest && precisionSizeRequest.mode === 'resize' ? precisionSizeRequest.outputSizePolicy : null,
    precision_strategy: currentMode === 'precision_edit' ? precisionEditStrategy : null,
    precision_selection_mode: currentMode === 'precision_edit' ? precisionEditSelectionMode : null,
    precision_selection_feather: currentMode === 'precision_edit' && precisionEditSelectionMode === 'local' ? precisionSelectionFeather : null,
    provider_settings: currentMode === 'precision_edit' && precisionEditSelectedModel.providerId
      ? (function() { var settings = {}; settings[precisionEditSelectedModel.providerId] = { model: precisionEditSelectedModel.model }; return settings; })() : {},
    strength: parseFloat(document.getElementById('selStrength').value || '0.55'),
    enhance_prompt: document.getElementById('chkEnhance').checked,
    llm_provider_id: localStorage.getItem('igs_llm_provider') || undefined,
    continuous: false,
  };

  _authFetch('/api/generate', {
    method: 'POST',
    body: JSON.stringify(payload)
  }).then(function(r) {
    clearInterval(timerInterval);
    if (!r.ok) return generationResponseError(r);
    return r.json();
  }).then(function(data) {
    clearInterval(timerInterval);
    updateGenerationProgress(15, i18nText('status.task_queued'));
    ptxt.textContent = i18nText('status.task_queued');
    // 立即创建占位卡片（从初始响应的 provider_states）
    if (data.provider_states && Object.keys(data.provider_states).length > 0) {
      window._placeholdersCreated = true;
      createPreviewPlaceholders(data.provider_states);
    }
    if (data.generation_id) {
      startGenPolling(data.generation_id);
    }
  }).catch(function(e) {
    clearInterval(timerInterval);
    stopGenPolling();
    pbox.classList.add('hidden');
    alert(i18nText('status.submit_failed') + e.message);
    setStatus(i18nText('status.submit_failed') + e.message);
    setGenerationControls('idle');
    if (!genCurrentGenId) genIsPrecisionTask = false;
  });
}

// ═══════════════════════════════════════════════════════════════════
// LLM 增强结果展示
// ═══════════════════════════════════════════════════════════════════
function showEnhanceResult(text) {
  var el = document.getElementById('enhanceResult');
  var et = document.getElementById('enhanceText');
  if (et) et.textContent = text;
  if (el) el.classList.add('show');
}

function hideEnhance() {
  document.getElementById('enhanceResult').classList.remove('show');
}

function insertEnhance() {
  var text = document.getElementById('enhanceText').textContent;
  if (currentMode === 't2i') {
    document.getElementById('txtPrompt').value = text;
  } else {
    document.getElementById('txtPromptI2I').value = text;
  }
  hideEnhance();
}

function copyEnhance() {
  var text = document.getElementById('enhanceText').textContent;
  navigator.clipboard.writeText(text).then(function(){
    setStatus(i18nText('common.copied_clipboard'));
  });
}

// ═══════════════════════════════════════════════════════════════════
// 结果展示
// ═══════════════════════════════════════════════════════════════════
function showResults(results, prompt, timings) {
  try {
  notifyPrecisionFocusActivity('preview');
  currentGroupTimings = timings || currentGroupTimings || {};
  var container = document.getElementById('previewResults');
  var mainContent = document.getElementById('previewMainContent');
  var cnt = document.getElementById('resultCount');
  if (!container) return;
  var keys = Object.keys(results);

  if (mainContent) {
    mainContent.classList.remove('hidden');
    mainContent.style.display = 'flex';
  }

  // Merge successful results into grouped state
  var addedCount = 0;
  var failedCount = 0;
  for (var i = 0; i < keys.length; i++) {
    var pid = keys[i];
    var r = results[pid];
    var realPid = pid.replace(/_\d+$/, '');
    var seq = r.seq !== undefined ? r.seq : -1;
    if (r.success && r.local_path) {
      var fname = r.local_path.split(/[\\/]/).pop();
      var pInfo = findProvider(pid) || {name: pid, color: '#5b8def'};
      var displayName = pInfo.name + (seq >= 1 ? ' #' + (seq+1) : '');
      var imgEntry = { pid: pid, realPid: realPid, src: '/api/gallery/image/' + fname, name: displayName, color: pInfo.color, fname: fname };

      // Check if already in grouped state (from fillPreviewPlaceholder)
      var alreadyExists = false;
      if (groupedPreviews[realPid]) {
        for (var j = 0; j < groupedPreviews[realPid].images.length; j++) {
          if (groupedPreviews[realPid].images[j].pid === pid) { alreadyExists = true; break; }
        }
      }
      if (!alreadyExists) {
        addImageToGroupedPreview(realPid, imgEntry);
        addedCount++;
      }
    } else {
      failedCount++;
    }
  }

  // Clean up remaining placeholders
  Object.keys(previewPlaceholders).forEach(function(k) {
    var ph = previewPlaceholders[k];
    if (ph && ph.cardEl && ph.cardEl.parentNode) ph.cardEl.remove();
  });
  previewPlaceholders = {};

  // Render final grouped state
  renderGroupedPreviews();

  // Update count
  var totalCount = 0;
  Object.keys(groupedPreviews).forEach(function(k) { totalCount += groupedPreviews[k].images.length; });
  var emptyEl = document.getElementById('previewEmpty');
  if (totalCount === 0 && failedCount === 0) {
    if (emptyEl) emptyEl.style.display = '';
    if (mainContent) mainContent.style.display = 'none';
  } else {
    if (emptyEl) emptyEl.style.display = 'none';
  }
  if (cnt) cnt.textContent = totalCount + i18nText('result.success_count') + (failedCount > 0 ? ' ? ' + failedCount + i18nText('result.failed_count') : '');

  } catch(e) { console.error('[showResults] error:', e); }
}

function _addCardArrows(card, groupImgs, realPid) {
  var idx = { value: 0 };

  var btnL = document.createElement('button');
  btnL.className = 'prev-arrow prev-arrow-left';
  btnL.innerHTML = '‹';
  btnL.onclick = function(e) {
    e.stopPropagation();
    idx.value = (idx.value - 1 + groupImgs.length) % groupImgs.length;
    _refreshGroupCard(card, groupImgs, idx.value, realPid);
  };
  card.appendChild(btnL);

  var btnR = document.createElement('button');
  btnR.className = 'prev-arrow prev-arrow-right';
  btnR.innerHTML = '›';
  btnR.onclick = function(e) {
    e.stopPropagation();
    idx.value = (idx.value + 1) % groupImgs.length;
    _refreshGroupCard(card, groupImgs, idx.value, realPid);
  };
  card.appendChild(btnR);
}

// Old renderPreviewViewer removed — grid layout handles preview directly
function renderPreviewViewer(container) { /* no-op: grid layout */ }

function addResultToPreview(key, result) {
  var container = document.getElementById('previewResults');
  var emptyEl = document.getElementById('previewEmpty');
  var mainContent = document.getElementById('previewMainContent');
  if (!container) return;

  var pid = result.model || key;
  var realPid = key.replace(/_\d+$/, '');
  var seq = result.seq !== undefined ? result.seq : -1;
  var fname = result.local_path.split(/[\\/]/).pop();
  var pInfo = findProvider(pid) || { name: pid, color: '#5b8def' };
  var displayName = pInfo.name + (seq >= 1 ? ' #' + (seq + 1) : '');

  var imgEntry = { pid: pid, realPid: realPid, src: '/api/gallery/image/' + fname, name: displayName, color: pInfo.color, fname: fname };
  addImageToGroupedPreview(realPid, imgEntry);

  if (emptyEl) emptyEl.style.display = 'none';
  if (mainContent) {
    mainContent.classList.remove('hidden');
    mainContent.style.display = 'flex';
  }
  renderGroupedPreviews();
}

// Old renderGroupedPreview, groupNav, renderGroupThumbs, previewPrev, previewNext removed
function renderGroupedPreview(container) { /* no-op: grid layout */ }
function groupNav(rp, dir) { /* no-op */ }
function renderGroupThumbs(rp, groupImgs, activeIdx, color) { /* no-op */ }
function previewPrev() { /* no-op: grid layout */ }
function previewNext() { /* no-op: grid layout */ }

function findProvider(pid) {
  // 精确匹配
  for (var i=0;i<allProviders.length;i++) {
    if (allProviders[i].id === pid) return allProviders[i];
  }
  // 兼容 pid_0, pid_1 等多图 key
  var basePid = pid.replace(/_\d+$/, '');
  if (basePid !== pid) {
    for (var j=0;j<allProviders.length;j++) {
      if (allProviders[j].id === basePid) return allProviders[j];
    }
  }
  return null;
}

// 获取 Provider 的看板显示名（display_name 回退到 name）
function getProviderDisplayName(pid) {
  var pInfo = findProvider(pid) || {name: pid, display_name: ''};
  return pInfo.display_name || pInfo.name || pid;
}

// ═══════════════════════════════════════════════════════════════════
// 灯箱
// ═══════════════════════════════════════════════════════════════════
var lightboxCurrentPrompt = '';
var lightboxCurrentSrc = '';

function openLightbox(src, label, prompt) {
  var lb = document.getElementById('lightbox');
  var img = document.getElementById('lightbox-img');
  var video = document.getElementById('lightbox-video');
  var dl = document.getElementById('lightbox-dl');
  var info = document.getElementById('lightbox-info');
  var promptBox = document.getElementById('lightbox-prompt-box');
  var promptEl = document.getElementById('lightbox-prompt');
  var promptChunks = document.getElementById('lightbox-prompt-chunks');
  if (lb && img) {
    bindLightboxImageFullscreen();
    // 重置：显示图片，隐藏视频
    img.classList.remove('hidden', 'zoomed');
    if (video) { video.classList.add('hidden'); video.pause(); video.src = ''; }
    img.src = src;
    img.alt = label || '';
    lightboxZoom = 1;
    img.style.transform = 'scale(1)';
    if (dl) dl.href = src;
    if (info) info.textContent = label || '';
    // 保存当前图片源
    lightboxCurrentSrc = src;
    // 显示提示词
    lightboxCurrentPrompt = prompt || '';
    if (promptEl) promptEl.textContent = prompt || '';
    if (promptChunks) {
      var chunks = splitDisplayPrompt(prompt || '');
      promptChunks.innerHTML = chunks.map(function(chunk, index) {
        return '<div class="lightbox-prompt-chunk"><b>' + (index + 1) + '</b> ' + escHtml(chunk) + '</div>';
      }).join('');
    }
    if (promptBox) promptBox.style.display = prompt ? 'block' : 'none';
    var lbLabel = promptBox ? promptBox.querySelector('.lb-prompt-label') : null;
    if (lbLabel) lbLabel.textContent = i18nText('lightbox.image_prompt');
    lb.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
}

function copyLightboxPrompt() {
  if (lightboxCurrentPrompt) {
    navigator.clipboard.writeText(lightboxCurrentPrompt).then(function(){
      setStatus(i18nText('lightbox.prompt_copied'));
    });
  }
}

// ═══════════════════════════════════════════════════════════════════
// 快捷操作：发送到图生图/生视频
// ═══════════════════════════════════════════════════════════════════
var lightboxCurrentSrc = '';

function sendToPrecisionEdit(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  if (!lightboxCurrentSrc) { alert(i18nText('image.unavailable')); return false; }
  if (!preparePrecisionSourceReplacement()) return false;
  var imgUrl = lightboxCurrentSrc;
  var prompt = lightboxCurrentPrompt || '';
  var generation = ++precisionSourceLoadGeneration;
  closeLightbox(e);
  if (window.dockNav) { window.dockNav.switchPage('generate'); }

  var fname = imgUrl.split(/[?#]/)[0].split('/').pop();
  _authFetch('/api/gallery/image/' + encodeURIComponent(fname) + '/base64')
    .then(function(r) {
      if (generation !== precisionSourceLoadGeneration || precisionSourceTaskIsActive()) return null;
      if (!r.ok) throw new Error(i18nText('image.data_failed'));
      return r.json();
    })
    .then(function(d) {
      if (!d || generation !== precisionSourceLoadGeneration || precisionSourceTaskIsActive()) return false;
      var imageData = d.data;
      if (typeof imageData !== 'string' || !imageData) throw new Error(i18nText('image.data_failed'));
      setTimeout(function() {
        if (generation !== precisionSourceLoadGeneration || precisionSourceTaskIsActive()) return;
        if (typeof setCreatorWorkbenchMode === 'function') {
          setCreatorWorkbenchMode('image', 'precision');
        }
        loadPrecisionEditSourceImage(imageData, prompt, {
          generation: generation,
          onLoaded: function() { setStatus(i18nText('image.sent_precision_edit')); }
        });
      }, 300);
      return true;
    })
    .catch(function(error) {
      if (generation !== precisionSourceLoadGeneration) return false;
      alert(i18nText('image.load_failed') + error.message);
      return false;
    });
  return true;
}

function splitDisplayPrompt(value, size) {
  var text = String(value || '').trim();
  var chunkSize = Number(size) || 280;
  if (!text) return [];
  var chunks = [];
  for (var index = 0; index < text.length; index += chunkSize) chunks.push(text.slice(index, index + chunkSize));
  return chunks;
}

function toggleLightboxImageFullscreen(event) {
  if (event && event.stopPropagation) event.stopPropagation();
  var img = document.getElementById('lightbox-img');
  if (!img || img.classList.contains('hidden') || !img.src) return false;
  var overlay = document.getElementById('precisionImageFullscreen');
  var target = document.getElementById('precisionImageFullscreenImg');
  if (!overlay || !target) return false;
  if (!overlay.classList.contains('hidden')) { closePrecisionImageFullscreen(); return true; }
  overlay._precisionReturnFocus = document.activeElement && typeof document.activeElement.focus === 'function' ? document.activeElement : img;
  target.src = img.src;
  target.alt = img.alt || '';
  overlay.dataset.zoom = '1';
  target.style.transform = 'scale(1)';
  overlay.classList.remove('hidden');
  overlay.classList.add('show');
  renderPrecisionImageFullscreenPrompts({
    label: img.alt || '',
    prompt: lightboxCurrentPrompt || ''
  });
  document.body.classList.add('precision-image-viewing');
  bindPrecisionImageFullscreenLifecycle();
  if (typeof overlay.focus === 'function') overlay.focus();
  return true;
}

function bindLightboxImageFullscreen() {
  var img = document.getElementById('lightbox-img');
  if (!img || img.dataset.precisionFullscreenBound === 'true') return;
  img.dataset.precisionFullscreenBound = 'true';
  img.addEventListener('dblclick', function(event) {
    event.preventDefault();
    event.stopPropagation();
    toggleLightboxImageFullscreen(event);
  });
}

function precisionImageFullscreenPromptEntries(options) {
  options = options || {};
  var sessionEntries = Array.isArray(options.sessionEntries)
    ? options.sessionEntries.filter(function(entry) { return entry && typeof entry === 'object'; })
    : [];
  if (!sessionEntries.length && String(options.prompt || '').trim()) {
    sessionEntries = [{
      id: 'current',
      label: options.label || '',
      prompt: String(options.prompt || ''),
      createdAt: new Date().toISOString()
    }];
  }
  return sessionEntries.map(function(entry, index) {
    var prompt = String(entry.prompt || '').trim();
    var operation = String(entry.operation || '').trim();
    var text = prompt || (operation ? '操作：' + operation + '（此版本未记录文字提示词）' : '此版本未记录文字提示词');
    return {
      id: String(entry.id || ('entry-' + index)),
      title: index === 0 ? '原图提示词' : '改图 ' + index + ' 提示词',
      prompt: text,
      rawPrompt: prompt,
      createdAt: entry.createdAt || entry.created_at || entry.timestamp || '',
      current: String(entry.id || ('entry-' + index)) === String(options.currentId || '')
    };
  });
}

function renderPrecisionImageFullscreenPrompts(options) {
  var overlay = document.getElementById('precisionImageFullscreen');
  var panel = document.getElementById('precisionImageFullscreenPromptPanel');
  var history = document.getElementById('precisionImageFullscreenPromptHistory');
  var caption = document.getElementById('precisionImageFullscreenCaption');
  if (!overlay || !panel || !history) return [];
  options = options || {};
  if (caption) caption.textContent = String(options.label || '');
  var entries = precisionImageFullscreenPromptEntries(options);
  overlay._precisionPromptEntries = entries;
  overlay._precisionPromptText = entries.map(function(entry) {
    return entry.title + '\n' + entry.prompt;
  }).join('\n\n');
  panel.classList.toggle('hidden', entries.length === 0);
  history.innerHTML = entries.map(function(entry) {
    var chunks = splitDisplayPrompt(entry.prompt, 220);
    var createdAt = entry.createdAt ? new Date(entry.createdAt) : null;
    var timeLabel = createdAt && Number.isFinite(createdAt.getTime()) ? ' · ' + createdAt.toLocaleString() : '';
    return '<section class="precision-image-fullscreen-prompt-entry' + (entry.current ? ' selected' : '') + '">' +
      '<div class="precision-image-fullscreen-prompt-title"><strong>' + escHtml(entry.title) + '</strong><span>' + escHtml(timeLabel) + '</span></div>' +
      '<div class="precision-image-fullscreen-prompt-chunks">' + chunks.map(function(chunk, index) {
        return '<div class="precision-image-fullscreen-prompt-chunk"><b>' + (index + 1) + '</b> ' + escHtml(chunk) + '</div>';
      }).join('') + '</div></section>';
  }).join('');
  return entries;
}

function copyPrecisionImageFullscreenPrompt(event) {
  if (event && event.stopPropagation) event.stopPropagation();
  var overlay = document.getElementById('precisionImageFullscreen');
  var text = overlay && String(overlay._precisionPromptText || '').trim();
  if (!text) return false;
  var copied = false;
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    navigator.clipboard.writeText(text).then(function() { setStatus(i18nText('lightbox.prompt_copied')); }).catch(function() {});
    copied = true;
  }
  if (!copied && document.execCommand) {
    var input = document.createElement('textarea');
    input.value = text;
    input.setAttribute('readonly', '');
    input.style.position = 'fixed';
    input.style.opacity = '0';
    document.body.appendChild(input);
    input.select();
    try { copied = document.execCommand('copy'); } catch (error) { copied = false; }
    input.remove();
    if (copied) setStatus(i18nText('lightbox.prompt_copied'));
  }
  return copied;
}

function openPrecisionImageFullscreen(src, label, options) {
  var overlay = document.getElementById('precisionImageFullscreen');
  var target = document.getElementById('precisionImageFullscreenImg');
  if (!overlay || !target || !src) return false;
  options = options || {};
  overlay._precisionReturnFocus = document.activeElement && typeof document.activeElement.focus === 'function' ? document.activeElement : null;
  target.src = src;
  target.alt = label || '';
  options.label = label || options.label || '';
  renderPrecisionImageFullscreenPrompts(options);
  overlay.classList.remove('hidden');
  overlay.classList.add('show');
  document.body.classList.add('precision-image-viewing');
  overlay.dataset.zoom = '1';
  target.style.transform = 'scale(1)';
  bindPrecisionImageFullscreenLifecycle();
  if (typeof overlay.focus === 'function') overlay.focus();
  return true;
}

function bindPrecisionImageFullscreenLifecycle() {
  var overlay = document.getElementById('precisionImageFullscreen');
  if (!overlay || overlay.dataset.precisionLifecycleBound === 'true') return;
  overlay.dataset.precisionLifecycleBound = 'true';
  overlay.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      closePrecisionImageFullscreen();
      return;
    }
    if (event.key !== 'Tab') return;
    var controls = Array.prototype.slice.call(overlay.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(function(node) { return !node.disabled && !node.hidden; });
    if (!controls.length) { event.preventDefault(); overlay.focus(); return; }
    var first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
}

function closePrecisionImageFullscreen() {
  var overlay = document.getElementById('precisionImageFullscreen');
  var target = document.getElementById('precisionImageFullscreenImg');
  var restore = overlay && overlay._precisionReturnFocus;
  if (target) { target.removeAttribute('src'); target.style.transform = 'scale(1)'; }
  var caption = document.getElementById('precisionImageFullscreenCaption');
  var history = document.getElementById('precisionImageFullscreenPromptHistory');
  var panel = document.getElementById('precisionImageFullscreenPromptPanel');
  if (caption) caption.textContent = '';
  if (history) history.textContent = '';
  if (panel) panel.classList.add('hidden');
  if (overlay) { overlay.classList.add('hidden'); overlay.classList.remove('show'); overlay.dataset.zoom = '1'; overlay._precisionReturnFocus = null; }
  if (overlay) { overlay._precisionPromptEntries = []; overlay._precisionPromptText = ''; }
  document.body.classList.remove('precision-image-viewing');
  restorePrecisionImageFullscreenRoot();
  if (restore && typeof restore.focus === 'function') restore.focus();
}

document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    var overlay = document.getElementById('precisionImageFullscreen');
    if (overlay && !overlay.classList.contains('hidden')) { event.preventDefault(); closePrecisionImageFullscreen(); }
  }
});

document.addEventListener('wheel', function(event) {
  var overlay = document.getElementById('precisionImageFullscreen');
  var target = document.getElementById('precisionImageFullscreenImg');
  if (!overlay || overlay.classList.contains('hidden') || !target) return;
  if (event.target !== target && !(event.target && event.target.closest && event.target.closest('.precision-image-fullscreen-figure'))) return;
  event.preventDefault();
  var zoom = Number(overlay.dataset.zoom || 1);
  zoom = Math.max(0.5, Math.min(4, zoom + (event.deltaY < 0 ? 0.1 : -0.1)));
  overlay.dataset.zoom = String(zoom);
  target.style.transform = 'scale(' + zoom + ')';
}, { passive: false });

document.addEventListener('mousedown', function(event) {
  var overlay = document.getElementById('precisionImageFullscreen');
  var target = document.getElementById('precisionImageFullscreenImg');
  if (!overlay || overlay.classList.contains('hidden') || !target || event.button !== 1) return;
  if (event.target !== target && !(event.target && event.target.closest && event.target.closest('.precision-image-fullscreen-figure'))) return;
  event.preventDefault();
  overlay.dataset.zoom = '1';
  target.style.transform = 'scale(1)';
});

function sendToVideo(e) {
  e.stopPropagation();
  if (!lightboxCurrentSrc) { alert(i18nText('image.unavailable')); return; }
  var imgUrl = lightboxCurrentSrc;
  window._pendingI2VPrompt = lightboxCurrentPrompt || '';
  closeLightbox(e);
  if (window.dockNav) { window.dockNav.switchPage('video'); }

  // 从 URL 获取 base64 数据
  var fname = imgUrl.split('/').pop();
  _authFetch('/api/gallery/image/' + fname + '/base64')
    .then(function(r) {
      if (!r.ok) throw new Error(i18nText('image.data_failed'));
      return r.json();
    })
    .then(function(d) {
      setTimeout(function() {
        if (typeof switchVideoSubTab === 'function') {
          switchVideoSubTab('i2vid');
        }
        if (!window.videoImages) window.videoImages = [];
        window.videoImages.push(d.data);
        if (typeof renderVideoImagePreview === 'function') renderVideoImagePreview();
        if (window._pendingI2VPrompt) {
          var ta = document.getElementById('txtVideoPrompt');
          if (ta) ta.value = window._pendingI2VPrompt;
        }
        setStatus(i18nText('image.sent_i2v'));
      }, 300);
    })
    .catch(function(e) {
      alert(i18nText('image.load_failed') + e.message);
    });
}

function loadImageFromUrl(url) {
  window.uploadedImageData = url;
  var p = document.getElementById('uploadPreview');
  if (p) { p.src = url; p.classList.remove('hidden'); }
  var ph = document.getElementById('uploadPlaceholder');
  if (ph) ph.style.display = 'none';
}

function loadVideoImageFromUrl(url) {
  if (!window.videoImages) window.videoImages = [];
  // 如果是 URL（非 base64），先获取 base64 数据
  if (url && !url.startsWith('data:')) {
    var fname = url.split('/').pop();
    _authFetch('/api/gallery/image/' + fname + '/base64')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        window.videoImages.push(d.data);
        if (typeof renderVideoImagePreview === 'function') renderVideoImagePreview();
      })
      .catch(function(e) { console.error('加载图片失败:', e); });
  } else {
    window.videoImages.push(url);
    if (typeof renderVideoImagePreview === 'function') renderVideoImagePreview();
  }
}

function closeLightbox(e) {
  if (e && e.target !== e.currentTarget && !e.target.closest('#lightbox-controls') && e.target.id !== 'lightbox-img') {
    // 只在背景点击时关闭
    if (e.target.id !== 'lightbox') return;
  }
  var lb = document.getElementById('lightbox');
  var video = document.getElementById('lightbox-video');
  if (video) { video.pause(); video.src = ''; video.classList.add('hidden'); }
  var img = document.getElementById('lightbox-img');
  if (img) img.classList.remove('hidden');
  lb.classList.remove('show');
  document.body.style.overflow = '';
}

function toggleZoom(e) {
  e.stopPropagation();
  if (lightboxZoom === 1) {
    lightboxZoom = 1.5;
    document.getElementById('lightbox-img').style.transform = 'scale(1.5)';
    document.getElementById('lightbox-img').classList.add('zoomed');
  } else {
    zoomReset(e);
  }
}

function zoomIn(e) { e.stopPropagation(); lightboxZoom = Math.min(3, lightboxZoom + 0.5); document.getElementById('lightbox-img').style.transform = 'scale(' + lightboxZoom + ')'; }
function zoomOut(e) { e.stopPropagation(); lightboxZoom = Math.max(0.5, lightboxZoom - 0.5); document.getElementById('lightbox-img').style.transform = 'scale(' + lightboxZoom + ')'; }
function zoomReset(e) { if(e)e.stopPropagation(); lightboxZoom = 1; document.getElementById('lightbox-img').style.transform = 'scale(1)'; document.getElementById('lightbox-img').classList.remove('zoomed'); }

// ═══════════════════════════════════════════════════════════════════
// 对比模式
// ═══════════════════════════════════════════════════════════════════
function openCompare() {
  var keys = Object.keys(currentResults);
  if (keys.length < 2) { alert(i18nText('compare.need_two')); return; }
  var container = document.getElementById('compareItems');
  container.innerHTML = '';
  for (var i = 0; i < keys.length; i++) {
    (function(pid){
      var r = currentResults[pid];
      if (!r.success || !r.local_path) return;
      var pInfo = findProvider(pid) || {name: pid, color: '#5b8def'};
      var fname = r.local_path.split(/[\\/]/).pop();
      var src = '/api/gallery/image/' + fname;
      var item = document.createElement('div');
      item.className = 'compare-item';
      item.innerHTML =
        '<img src="' + src + '" alt="' + escAttr(pid) + '" onclick="openLightbox(\'' + src + '\',\'' + escAttr(pid) + '\')">' +
        '<div class="compare-item-info">' +
          '<span style="font-size:11px;font-weight:600;color:' + pInfo.color + ';">' + escHtml(pInfo.name) + '</span>' +
          '<a href="' + src + '" download class="btn-ghost" style="padding:3px 8px;font-size:10px;">⬇</a>' +
        '</div>';
      container.appendChild(item);
    })(keys[i]);
  }
  document.getElementById('compareModal').classList.add('show');
  document.body.style.overflow = 'hidden';
}

function openCompareFromLightbox(e) {
  e.stopPropagation();
  closeLightbox();
  openCompare();
}

function closeCompare() {
  document.getElementById('compareModal').classList.remove('show');
  document.body.style.overflow = '';
}

// ═══════════════════════════════════════════════════════════════════
// 图库
// ═══════════════════════════════════════════════════════════════════
var galleryItems = []; // 存储完整图库数据
var activeMediaTab = 'image';

function switchMediaTab(type) {
  activeMediaTab = type;
  document.getElementById('mediaTabImage').classList.toggle('active', type === 'image');
  document.getElementById('mediaTabVideo').classList.toggle('active', type === 'video');
  var pushBtn = document.getElementById('btnPushToRef');
  if (pushBtn) {
    if (type === 'image') { pushBtn.style.display = ''; } else { pushBtn.style.display = 'none'; }
  }
  if (document.getElementById('btnGallerySelect') && document.getElementById('btnGallerySelect').classList.contains('active')) {
    showGalleryToolbar(true);
  }
  var gridEl = document.getElementById('galleryGrid');
  if (gridEl) gridEl.classList.toggle('gallery-grid-video', type === 'video');
  renderGalleryItems(galleryItems);
}

function applyMediaFilters() {
  renderGalleryItems(galleryItems);
}

function updateGalleryProviderFilter() {
  var sel = document.getElementById('galleryProviderFilter');
  if (!sel) return;
  var current = sel.value;
  var pids = {};
  for (var i = 0; i < galleryItems.length; i++) {
    pids[galleryItems[i].model] = true;
  }
  var opts = i18nText('provider.all_option_html');
  var keys = Object.keys(pids).sort();
  for (var k = 0; k < keys.length; k++) {
    var pInfo = findProvider(keys[k]) || {name: keys[k]};
    opts += '<option value="' + escAttr(keys[k]) + '"' + (current === keys[k] ? ' selected' : '') + '>' + escHtml(pInfo.name) + '</option>';
  }
  sel.innerHTML = opts;
}

function applyGallerySort() {
  renderGalleryItems(galleryItems);
}

function renderGalleryItems(items) {
  var g = document.getElementById('galleryGrid');
  // Apply type filter
  var filtered = items.slice();
  if (activeMediaTab === 'image') {
    filtered = filtered.filter(function(it) { return it.type !== 'video'; });
  } else if (activeMediaTab === 'video') {
    filtered = filtered.filter(function(it) { return it.type === 'video'; });
  }
  // Apply provider filter
  var providerFilter = document.getElementById('galleryProviderFilter');
  var providerVal = providerFilter ? providerFilter.value : '';
  if (providerVal) {
    filtered = filtered.filter(function(it) { return (it.model || '') === providerVal; });
  }
  // Apply search text filter
  var searchInput = document.getElementById('gallerySearchInput');
  var searchVal = searchInput ? searchInput.value.trim().toLowerCase() : '';
  if (searchVal) {
    filtered = filtered.filter(function(it) { return (it.prompt || '').toLowerCase().indexOf(searchVal) !== -1; });
  }
  var dateFrom = document.getElementById('galleryDateFrom');
  var dateTo = document.getElementById('galleryDateTo');
  var fromValue = dateFrom ? dateFrom.value : '';
  var toValue = dateTo ? dateTo.value : '';
  if (fromValue || toValue) {
    var fromTime = fromValue ? Date.parse(fromValue + 'T00:00:00') : -Infinity;
    var toTime = toValue ? Date.parse(toValue + 'T23:59:59.999') : Infinity;
    filtered = filtered.filter(function(it) {
      var raw = it.created_at || it.createdAt || '';
      var time = Date.parse(raw);
      return Number.isFinite(time) && time >= fromTime && time <= toTime;
    });
  }
  if (!filtered.length) {
    var emptyMsg = activeMediaTab === 'video' ? '\u6682\u65E0\u89C6\u9891' : '\u6682\u65E0\u56FE\u7247';
    g.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:60px;font-size:13px;">' + emptyMsg + '</div>';
    return;
  }
  // Sort
  var sortBy = document.getElementById('gallerySortBy') ? document.getElementById('gallerySortBy').value : 'created_at_desc';
  var sorted = filtered.slice();
  sorted.sort(function(a, b) {
    switch(sortBy) {
      case 'created_at_asc': return (a.created_at || '').localeCompare(b.created_at || '');
      case 'model_asc': return (a.model || '').localeCompare(b.model || '');
      case 'model_desc': return (b.model || '').localeCompare(a.model || '');
      case 'prompt_asc': return (a.prompt || '').localeCompare(b.prompt || '');
      default: return (b.created_at || '').localeCompare(a.created_at || '');
    }
  });
  var groupMode = document.getElementById('galleryGroupMode');
  var groupByModel = groupMode && groupMode.value === 'model';
  if (groupByModel) {
    sorted.sort(function(a, b) {
      var modelCmp = (a.model || 'unknown').localeCompare(b.model || 'unknown');
      if (modelCmp) return modelCmp;
      return (b.created_at || '').localeCompare(a.created_at || '');
    });
  }
  var h = '';
  var inSelectMode = document.getElementById('btnGallerySelect') && document.getElementById('btnGallerySelect').classList.contains('active');
  var currentModel = null;
  for (var i = 0; i < sorted.length; i++) {
    (function(item){
      var f = item.local_path.split(/[\\/]/).pop();
      var pInfo = findProvider(item.model) || {name: item.model, color: '#5b8def'};
      if (groupByModel && currentModel !== (item.model || 'unknown')) {
        currentModel = item.model || 'unknown';
        h += '<div class="gallery-model-header"><span class="gallery-model-dot" style="background:' + escAttr(pInfo.color || '#5b8def') + '"></span><span>' + escHtml(pInfo.name || currentModel) + '</span><span class="gallery-model-count">' + sorted.filter(function(x) { return (x.model || 'unknown') === currentModel; }).length + '</span></div>';
      }
      var isSelected = selectedGalleryItems.indexOf(item.id) !== -1;
      var isVideo = item.type === 'video';
      
      var clickHandler = inSelectMode
        ? 'onclick="toggleGalleryItem(\'' + escAttr(item.id) + '\',this)"'
        : (isVideo
          ? 'onclick="playVideoFromGallery(\'' + escAttr(item.id) + '\')"'
          : 'onclick="openLightboxFromGallery(\'' + escAttr(item.id) + '\')"');
      
      var typeIcon = '';
      var badgesHtml = '';
      var videoOverlayHtml = '';
      if (!isVideo && (item.source === 'cloud' || (item.tags || []).indexOf('cloud-sync') !== -1)) {
        badgesHtml = i18nText('library.cloud_badge_html');
      }
      if (isVideo) {
        typeIcon = '<div class="vid-play"><div class="vid-play-btn"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></div></div>';
        badgesHtml = '';
        var durationHtml = item.duration ? '<div class="vid-duration">' + item.duration + 's</div>' : '';
        var promptShort = (item.prompt || '').length > 40 ? (item.prompt || '').substring(0, 40) + '...' : (item.prompt || i18nText('video.unnamed'));
        var vidUrl = item.video_url || '';
        var vidPreviewHtml = vidUrl ? '<video class="vid-preview-video" preload="metadata" muted loop playsinline data-src="' + escAttr(vidUrl) + '"></video>' : '';
        videoOverlayHtml = vidPreviewHtml + '<div class="vid-info">' +
          '<div class="vid-info-title">' + escHtml(promptShort) + '</div>' +
          '<div class="vid-info-meta"><span>' + escHtml(pInfo.name) + '</span><div class="vid-info-dot"></div><span>' + escHtml(item.created_at || '') + '</span></div>' +
        '</div>' + durationHtml + '<div class="vid-progress"><div class="vid-progress-bar"></div></div>';
      }
      
      var thumbHtml = '<img src="' + item.thumbnail + '" loading="lazy" style="' + (isVideo ? 'object-fit:cover;' : '') + '">';
      
      h += '<div class="gallery-item' + (isSelected ? ' selected' : '') + (isVideo ? ' gallery-item-video' : '') + '" data-id="' + escAttr(item.id) + '" data-fname="' + escAttr(f) + '" data-type="' + (isVideo ? 'video' : 'image') + '" ' + clickHandler + '>' +
        thumbHtml +
        typeIcon +
        badgesHtml +
        videoOverlayHtml +
        (inSelectMode ? '' : (isVideo ? '' : '<div class="gallery-zoom-hint"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg></div>')) +
        (isVideo ? '' : '<div class="gallery-item-overlay">' +
          '<div class="gallery-item-label">' + escHtml(pInfo.name) + '</div>' +
        '</div>') +
      '</div>';
    })(sorted[i]);
  }
  g.innerHTML = h;
  initVideoHoverPreview();
}

var _vidHoverTimers = {};
function initVideoHoverPreview() {
  var grid = document.getElementById('galleryGrid');
  if (!grid || grid._vidHoverBound) return;
  grid._vidHoverBound = true;
  grid.addEventListener('mouseenter', function(e) {
    var card = e.target.closest('.gallery-item-video');
    if (!card || card.classList.contains('vid-previewing')) return;
    var vid = card.querySelector('.vid-preview-video');
    if (!vid || !vid.dataset.src) return;
    var id = card.dataset.id;
    clearTimeout(_vidHoverTimers['out_' + id]);
    _vidHoverTimers['in_' + id] = setTimeout(function() {
      if (!vid.src) vid.src = vid.dataset.src;
      vid.currentTime = 0.5;
      vid.play().then(function() {
        card.classList.add('vid-previewing');
      }).catch(function() {});
    }, 350);
  }, true);
  grid.addEventListener('mouseleave', function(e) {
    var card = e.target.closest('.gallery-item-video');
    if (!card) return;
    var vid = card.querySelector('.vid-preview-video');
    if (!vid) return;
    var id = card.dataset.id;
    clearTimeout(_vidHoverTimers['in_' + id]);
    _vidHoverTimers['out_' + id] = setTimeout(function() {
      vid.pause();
      vid.currentTime = 0;
      card.classList.remove('vid-previewing');
    }, 200);
  }, true);
}

function playVideoFromGallery(itemId) {
  var item = null;
  for (var i = 0; i < galleryItems.length; i++) {
    if (galleryItems[i].id === itemId) {
      item = galleryItems[i];
      break;
    }
  }
  if (!item || !item.video_url) { alert(i18nText('video.cannot_play')); return; }
  // 在灯箱中播放视频
  var lb = document.getElementById('lightbox');
  var lbImg = document.getElementById('lightbox-img');
  var lbVideo = document.getElementById('lightbox-video');
  var lbDl = document.getElementById('lightbox-dl');
  var lbInfo = document.getElementById('lightbox-info');
  var lbPromptBox = document.getElementById('lightbox-prompt-box');
  var lbPrompt = document.getElementById('lightbox-prompt');
  if (lbImg) { lbImg.classList.add('hidden'); lbImg.src = ''; }
  if (lbVideo) {
    lbVideo.src = item.video_url;
    lbVideo.classList.remove('hidden');
    lbVideo.play();
  }
  if (lbDl) {
    lbDl.href = item.video_url;
    lbDl.download = (item.id || 'video') + '.mp4';
    lbDl.textContent = i18nText('video.download');
    lbDl.classList.remove('hidden');
  }
  if (lbInfo) lbInfo.textContent = item.model || '';
  lightboxCurrentPrompt = item.prompt || '';
  if (lbPrompt) lbPrompt.textContent = item.prompt || '';
  if (lbPromptBox) lbPromptBox.style.display = item.prompt ? 'block' : 'none';
  var lbLabel = lbPromptBox ? lbPromptBox.querySelector('.lb-prompt-label') : null;
  if (lbLabel) lbLabel.textContent = i18nText('video.prompt_lightbox');
  lb.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function loadGallery() {
  var g = document.getElementById('galleryGrid');
  _authFetch('/api/gallery?limit=80').then(function(r){return r.json();}).then(function(d){
    var items = d.items || [];
    galleryItems = items; // 保存完整数据
    allGalleryIds = items.map(function(it){ return it.id; });
    updateGalleryProviderFilter();
    renderGalleryItems(items);
  }).catch(function(e){
    g.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:#f87171;padding:40px;">\u52A0\u8F7D\u5931\u8D25</div>';
  });
}

function openLightboxFromGallery(itemId) {
  // 从存储的数据中查找
  var item = null;
  for (var i = 0; i < galleryItems.length; i++) {
    if (galleryItems[i].id === itemId) {
      item = galleryItems[i];
      break;
    }
  }
  if (!item) { console.error('[Gallery] item_not_found'); alert(i18nText('image.open_missing')); return; }
  if (!item.local_path) { console.error('[Gallery] invalid_local_path'); alert(i18nText('image.open_invalid')); return; }
  var f = item.local_path.split(/[\\/]/).pop();
  var pInfo = findProvider(item.model) || {name: item.model, color: '#5b8def'};
  var src = '/api/gallery/image/' + encodeURIComponent(f);
  var prompt = item.prompt || '';
  console.log('[Gallery] lightbox_opened');
  openLightbox(src, pInfo.name, prompt);
}

// ═══════════════════════════════════════════════════════════════════
// 历史
// ═══════════════════════════════════════════════════════════════════
var allHistoryItems = []; // 存储完整历史数据

function updateHistoryFilterProviders() {
  var sel = document.getElementById('historyFilterProvider');
  if (!sel) return;
  var current = sel.value;
  // 收集所有 provider
  var pids = {};
  for (var i = 0; i < allHistoryItems.length; i++) {
    var providers = allHistoryItems[i].providers || [];
    for (var j = 0; j < providers.length; j++) {
      pids[providers[j]] = true;
    }
  }
  var opts = i18nText('provider.all_option_html');
  var keys = Object.keys(pids).sort();
  for (var k = 0; k < keys.length; k++) {
    var pInfo = findProvider(keys[k]) || {name: keys[k]};
    opts += '<option value="' + escAttr(keys[k]) + '"' + (current === keys[k] ? ' selected' : '') + '>' + escHtml(pInfo.name) + '</option>';
  }
  sel.innerHTML = opts;
}

// ═══════════════════════════════════════════════════════════════════
// 概览看板
// ═══════════════════════════════════════════════════════════════════
function loadDashboard() {
  var el = document.getElementById('dashboardContent');
  if (!el) return;
  el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">' + i18nText('common.loading') + '</div>';
  _loadNetStatus();

  _authFetch('/api/dashboard')
    .then(function(r){
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(d) {
      if (d.error) throw new Error(d.error);
      var s = d.system || {};
      var st = d.stats || {};
      var sc = d.score || {};
      var providers = d.providers || [];
      var logs = d.recent_logs || [];

      var scTotal = sc.total || 0;
      var scConn = sc.connectivity || 0;
      var scConf = sc.config || 0;
      var scDisk = sc.disk || 0;
      var scDep = sc.dependency || 0;
      var stImg = st.image || {};
      var stVid = st.video || {};

      var scoreColor = scTotal >= 80 ? '#22c55e' : scTotal >= 50 ? '#f59e0b' : '#ef4444';
      var scoreLabel = scTotal >= 80 ? i18nText('dashboard.score_excellent') : scTotal >= 50 ? i18nText('dashboard.score_good') : i18nText('dashboard.score_needs_work');

      var html = '';

      // ── 评分卡片 ──
      html += '<div class="dashboard-stats-grid">';
      html += _dashCard(i18nText('dashboard.overall_score'), '<div style="font-size:36px;font-weight:800;color:' + scoreColor + ';">' + scTotal + '</div><div style="font-size:11px;color:var(--text-muted);">' + scoreLabel + '</div>', scoreColor);
      html += _dashCard(i18nText('dashboard.image_generation'), '<div style="font-size:28px;font-weight:700;color:var(--accent);">' + (stImg.total || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">' + i18nText('dashboard.success') + ' ' + (stImg.success || 0) + ' / ' + i18nText('dashboard.failed') + ' ' + (stImg.failed || 0) + '</div>');
      html += _dashCard(i18nText('dashboard.video_generation'), '<div style="font-size:28px;font-weight:700;color:var(--accent-2);">' + (stVid.total || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">' + i18nText('dashboard.success') + ' ' + (stVid.success || 0) + ' / ' + i18nText('dashboard.failed') + ' ' + (stVid.failed || 0) + '</div>');
      html += _dashCard(i18nText('dashboard.avg_time'), '<div style="font-size:28px;font-weight:700;color:var(--accent);">' + (stImg.avg_time || 0) + 's</div><div style="font-size:11px;color:var(--text-muted);">' + i18nText('dashboard.image_generation_plain') + '</div>');
      html += '</div>';

      // ── 评分详情 + 系统信息 ──
      html += '<div class="dashboard-two-column">';
      html += '<div class="glass-card" style="padding:16px;display:flex;flex-direction:column;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">' + i18nText('dashboard.score_details') + '</div>';
      html += '<div style="flex:1;display:flex;flex-direction:column;justify-content:space-between;">';
      html += _scoreBar(i18nText('dashboard.connectivity'), scConn, 40, '#5b8def');
      html += _scoreBar(i18nText('dashboard.config_complete'), scConf, 30, '#22d3a5');
      html += _scoreBar(i18nText('dashboard.disk_space'), scDisk, 15, '#a78bfa');
      html += _scoreBar(i18nText('dashboard.dependencies'), scDep, 15, '#f59e0b');
      var totalScore = scConn + scConf + scDisk + scDep;
      var totalMax = 100;
      var scoreColor = totalScore >= 80 ? '#22c55e' : totalScore >= 50 ? '#f59e0b' : '#ef4444';
      html += '<div style="display:flex;align-items:center;justify-content:space-between;padding-top:8px;border-top:1px solid var(--border);margin-top:4px;">';
      html += '<span style="font-size:11px;color:var(--text-muted);">' + i18nText('dashboard.overall_score_plain') + '</span>';
      html += '<span style="font-size:16px;font-weight:800;color:' + scoreColor + ';">' + totalScore + '<span style="font-size:10px;font-weight:400;color:var(--text-muted);">/' + totalMax + '</span></span>';
      html += '</div>';
      html += '</div></div>';

      var diskFree = s.disk_free_gb || 0;
      var diskTotal = s.disk_total_gb || 0;
      var diskPct = s.disk_pct || 0;
      var galleryCount = s.gallery_count || 0;
      var gallerySize = s.gallery_size || '0 B';
      var videoCount = s.video_count || 0;
      var videoSize = s.video_size || '0 B';
      html += '<div class="glass-card" style="padding:16px;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">' + i18nText('dashboard.system_info') + '</div>';
      html += _infoRow(i18nText('dashboard.os'), '<span style="font-weight:600;">' + escHtml(s.os || '-') + '</span>');
      html += _infoRow(i18nText('dashboard.architecture'), escHtml(s.arch || '-') + ' (' + escHtml(s.machine || '-') + ')');
      html += _infoRow(i18nText('dashboard.hostname'), escHtml(s.hostname || '-'));
      html += _infoRow('Python', escHtml(s.python || '-'));
      html += _infoRow(i18nText('dashboard.uptime'), _fmtUptime(s.uptime_seconds || 0));
      html += _infoRow(i18nText('dashboard.disk_space'), diskFree + ' GB ' + i18nText('dashboard.available') + ' / ' + diskTotal + ' GB');
      html += _infoRow(i18nText('dashboard.disk_usage'), '<div style="flex:1;margin-left:10px;"><div style="height:6px;border-radius:3px;background:var(--bg-base);overflow:hidden;"><div style="height:100%;width:' + diskPct + '%;background:' + (diskPct > 90 ? '#ef4444' : diskPct > 70 ? '#f59e0b' : '#22c55e') + ';border-radius:3px;"></div></div></div><span style="font-size:11px;margin-left:6px;">' + diskPct + '%</span>');
      html += _infoRow(i18nText('dashboard.gallery'), galleryCount + ' ' + i18nText('dashboard.images_unit') + ' | ' + gallerySize);
      html += _infoRow(i18nText('dashboard.video_library'), videoCount + ' ' + i18nText('dashboard.videos_unit') + ' | ' + videoSize);
      html += '</div>';
      html += '</div>';

      // ── Provider 概览（分组） ──
      html += _renderProviderGroups(providers);

      // ── 最近活动 + 宿主机资源 ──
      html += '<div class="dashboard-two-column">';

      // Left: 最近活动
      html += '<div class="glass-card" style="padding:16px;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">' + i18nText('dashboard.recent_activity') + '</div>';
      if (logs.length === 0) {
        html += '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">' + i18nText('dashboard.no_activity') + '</div>';
      } else {
        html += '<div style="display:flex;flex-direction:column;gap:6px;max-height:240px;overflow-y:auto;">';
        for (var j = logs.length - 1; j >= 0; j--) {
          var log = logs[j];
          var catIcon = log.category === 'generate' ? '🎨' : log.category === 'delete' ? '🗑' : log.category === 'error' ? '⚠' : log.category === 'system' ? '⚙' : '📌';
          html += '<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 8px;border-radius:6px;background:var(--bg-base);">';
          html += '<span style="flex-shrink:0;">' + catIcon + '</span>';
          html += '<div style="flex:1;min-width:0;">';
          html += '<div style="font-size:11px;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(log.message || '') + '</div>';
          html += '<div style="font-size:10px;color:var(--text-muted);">' + (log.timestamp || '') + '</div>';
          html += '</div>';
          html += '</div>';
        }
        html += '</div>';
      }
      html += '</div>';

      // Right: 宿主机资源
      html += '<div class="glass-card" style="padding:16px;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">' + i18nText('dashboard.host_resources') + '</div>';
      html += '<div id="hostResPanel" style="display:flex;flex-direction:column;gap:8px;">';
      html += '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:11px;">' + i18nText('common.loading') + '</div>';
      html += '</div>';
      html += '</div>';

      html += '</div>';

      // ── 快捷导航 ──
      html += '<div class="dashboard-quick-grid">';
      html += _quickNav('<svg viewBox="0 0 24 24" aria-hidden="true" style="display:block;width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;"><rect x="3" y="3" width="18" height="18" rx="4"/><path d="M8 15.5 10.8 12l2.4 2.6 2.2-2.2L19 16"/><circle cx="9" cy="8.5" r="1.5"/><path d="M17.5 5.5v4M15.5 7.5h4"/></svg>', i18nText('nav.images'), "switchNav('generate',document.getElementById('navGen'))");
      html += _quickNav('<svg viewBox="0 0 24 24" aria-hidden="true" style="display:block;width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;"><rect x="3" y="5" width="14" height="14" rx="3"/><path d="m17 10 4-2v8l-4-2z"/><path d="m9 9 4 3-4 3z"/></svg>', i18nText('nav.video'), "switchNav('video',document.getElementById('navVideo'))");
      html += _quickNav('<svg viewBox="0 0 24 24" aria-hidden="true" style="display:block;width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;"><rect x="4" y="6" width="14" height="13" rx="2"/><path d="M8 6V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2"/><circle cx="8.5" cy="10" r="1.25"/><path d="m5.5 17 4-4 2.5 2.5 2-2 3.5 3.5"/></svg>', i18nText('nav.library'), "switchNav('gallery',document.getElementById('navGallery'))");
      html += _quickNav('<svg viewBox="0 0 24 24" aria-hidden="true" style="display:block;width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></svg>', i18nText('nav.history'), "switchNav('history',document.getElementById('navHistory'))");
      html += '</div>';

      el.innerHTML = html;
      _loadIpInfo();
      _loadHostResources();
    })
    .catch(function(e) {
      el.innerHTML = '<div style="text-align:center;padding:40px;color:#ef4444;">' + i18nText('common.load_failed_prefix') + escHtml(e.message) + '</div>';
    });
}

function _renderProviderGroups(providers) {
  // 两级分类 - 根据 capabilities 字段或关键字推断能力
  var cats = {
    [i18nText('provider.image')]: { [i18nText('history.t2i')]: [], [i18nText('history.i2i')]: [] },
    [i18nText('provider.video')]: { [i18nText('video.t2v')]: [], [i18nText('video.i2v')]: [] },
    [i18nText('provider.llm')]: { '_flat': [] }
  };

  for (var i = 0; i < providers.length; i++) {
    var p = providers[i];
    var ptype = p.type || 'image';
    var caps = p.capabilities || {};
    var modelStr = ((p.model || '') + ' ' + (p.models || []).join(' ')).toLowerCase();
    var providerId = (p.id || '').toLowerCase();
    var providerName = (p.name || '').toLowerCase();

    // i2i 能力：优先用 capabilities 显式声明，否则用关键字推断
    var hasI2I;
    if (caps.i2i !== undefined) {
      hasI2I = caps.i2i;
    } else {
      hasI2I = ptype === 'image' || modelStr.indexOf('i2i') !== -1 || modelStr.indexOf('edit') !== -1;
    }

    // i2v 能力：优先用 capabilities 显式声明，否则用关键字推断
    var hasI2V;
    if (caps.i2v !== undefined) {
      hasI2V = caps.i2v;
    } else {
      hasI2V = modelStr.indexOf('i2v') !== -1
        || modelStr.indexOf('veo_3_1_i2v') !== -1
        || providerId === 'agnes' || providerName.indexOf('agnes') !== -1;
    }

    if (ptype === 'llm') {
      cats[i18nText('provider.llm')]['_flat'].push(p);
    } else if (ptype === 'video') {
      cats[i18nText('provider.video')][i18nText('video.t2v')].push(p);
      if (hasI2V) {
        cats[i18nText('provider.video')][i18nText('video.i2v')].push(p);
      }
    } else {
      // image 类型 → 文生图 + 图生图
      cats[i18nText('provider.image')][i18nText('history.t2i')].push(p);
      if (hasI2I) {
        cats[i18nText('provider.image')][i18nText('history.i2i')].push(p);
      }
      // 同时有 video 模型 → 归入生视频
      var hasT2V = modelStr.indexOf('t2v') !== -1 || modelStr.indexOf('veo_') !== -1;
      if (hasT2V || hasI2V) {
        cats[i18nText('provider.video')][i18nText('video.t2v')].push(p);
        if (hasI2V) {
          cats[i18nText('provider.video')][i18nText('video.i2v')].push(p);
        }
      }
    }
  }

  function _renderProviderCard(p) {
    var statusDot = p.configured ? (p.enabled ? '#22c55e' : '#f59e0b') : '#6b7280';
    var statusText = p.configured ? (p.enabled ? i18nText('dashboard.enabled') : i18nText('dashboard.disabled')) : i18nText('common.not_configured');
    var h = '<div data-pid="' + p.id + '" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;background:var(--bg-base);border:1px solid var(--border);min-width:0;">';
    h += '<span style="width:8px;height:8px;border-radius:50%;background:' + statusDot + ';flex-shrink:0;"></span>';
    h += '<div style="flex:1;min-width:0;">';
    h += '<div style="font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(p.name) + '</div>';
    h += '<div style="font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(p.model || '-') + '</div>';
    h += '</div>';
    h += '<div style="text-align:right;flex-shrink:0;">';
    h += '<div style="font-size:10px;color:' + statusDot + ';">' + statusText + '</div>';
    h += '<div class="conn-ms" style="font-size:10px;color:var(--text-muted);"></div>';
    h += '</div>';
    h += '</div>';
    return h;
  }

  var html = '<div class="dashboard-two-column dashboard-provider-grid">';

  // ── Left: Provider 概览 ──
  html += '<div class="glass-card" style="padding:16px;min-width:0;overflow:hidden;">';
  html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">';
  html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);">' + i18nText('dashboard.model_provider') + '</div>';
  html += '<button onclick="runConnectivityTest()" id="connTestBtn" style="font-size:11px;padding:4px 12px;border-radius:6px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;transition:all 0.2s;">' + i18nText('dashboard.connectivity_check') + '</button>';
  html += '</div>';

  var catKeys = [i18nText('provider.image'), i18nText('provider.video'), i18nText('provider.llm')];
  for (var c = 0; c < catKeys.length; c++) {
    var catName = catKeys[c];
    var cat = cats[catName];
    var catIcon = catName.split(' ')[0];
    var catLabel = catName.substring(catName.indexOf(' ') + 1);

    html += '<div style="margin-bottom:14px;padding:12px;border-radius:10px;border:1px solid var(--border);background:var(--bg-surface);">';
    html += '<div style="font-size:12px;font-weight:700;color:var(--text-primary);margin-bottom:10px;display:flex;align-items:center;gap:6px;">';
    html += '<span>' + catIcon + '</span><span>' + catLabel + '</span>';
    html += '</div>';

    var subKeys = Object.keys(cat);
    for (var s = 0; s < subKeys.length; s++) {
      var subName = subKeys[s];
      var subProviders = cat[subName];
      if (subProviders.length === 0) continue;

      if (subName !== '_flat') {
        html += '<div style="margin-bottom:8px;">';
        html += '<div style="font-size:10px;font-weight:600;color:var(--accent);margin-bottom:5px;padding-left:2px;">└ ' + subName + ' (' + subProviders.length + ')</div>';
      } else {
        html += '<div style="margin-bottom:0;">';
      }
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:6px;">';
      for (var j = 0; j < subProviders.length; j++) {
        html += _renderProviderCard(subProviders[j]);
      }
      html += '</div>';
      html += '</div>';
    }
    html += '</div>';
  }
  html += '</div>';

  // ── Right: IP 信息面板 ──
  html += '<div class="glass-card" style="padding:16px;min-width:0;overflow:hidden;">';
  html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:14px;">' + i18nText('dashboard.local_ip_info') + '</div>';
  html += '<div id="ipInfoPanel" style="display:flex;flex-direction:column;gap:10px;">';
  html += '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:11px;">' + i18nText('common.loading') + '</div>';
  html += '</div>';
  html += '</div>';

  html += '</div>';
  return html;
}

function runConnectivityTest() {
  var btn = document.getElementById('connTestBtn');
  if (btn) { btn.textContent = i18nText('dashboard.connectivity_checking'); btn.disabled = true; btn.style.opacity = '0.6'; }

  _authFetch('/api/dashboard/connectivity')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var results = d.results || {};
      var ids = Object.keys(results);
      for (var i = 0; i < ids.length; i++) {
        var pid = ids[i];
        var r = results[pid];
        var cards = document.querySelectorAll('[data-pid="' + pid + '"]');
        for (var j = 0; j < cards.length; j++) {
          var card = cards[j];
          var msEl = card.querySelector('.conn-ms');
          if (msEl) {
            if (r.status === 'ok') {
              msEl.textContent = r.ms + 'ms';
              msEl.style.color = r.ms < 500 ? '#22c55e' : r.ms < 2000 ? '#f59e0b' : '#ef4444';
            } else if (r.status === 'no_url') {
              msEl.textContent = i18nText('dashboard.no_address');
              msEl.style.color = '#6b7280';
            } else {
              msEl.textContent = i18nText('dashboard.unreachable_short');
              msEl.style.color = '#ef4444';
            }
          }
          card.style.borderColor = r.status === 'ok' ? (r.ms < 500 ? '#22c55e40' : '#f59e0b40') : '#ef444440';
        }
      }
      if (btn) { btn.textContent = i18nText('dashboard.connectivity_done'); setTimeout(function(){ btn.textContent = i18nText('dashboard.connectivity_check'); btn.disabled = false; btn.style.opacity = '1'; }, 2000); }
    })
    .catch(function() {
      if (btn) { btn.textContent = i18nText('dashboard.connectivity_failed'); setTimeout(function(){ btn.textContent = i18nText('dashboard.connectivity_check'); btn.disabled = false; btn.style.opacity = '1'; }, 2000); }
    });
}

function _loadIpInfo() {
  var panel = document.getElementById('ipInfoPanel');
  if (!panel) return;
  var _ipHidden = true;

  _authFetch('/api/dashboard/ip-info')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (d.error) {
        panel.innerHTML = '<div style="text-align:center;padding:16px;color:#ef4444;font-size:11px;">' + escHtml(d.error) + '</div>';
        return;
      }

      var ip = d.ip || '-';
      var country = d.country || '-';
      var countryCode = d.country_code || '';
      var city = d.city || '-';
      var timezone = d.timezone || '-';
      var isNative = d.is_native;
      var nativeType = d.native_type || '-';
      var driftKm = d.drift_km || 0;
      var hasDrift = d.has_drift;
      var asn = d.asn || '-';
      var org = d.org || '-';
      var rdns = d.rdns || 'None';
      var ispType = d.isp_type || '-';
      var ispFlag = d.isp_flag || '';
      var ispWarning = d.isp_warning || '';
      var tcpRtt = d.tcp_rtt;
      var rttType = d.rtt_type || '';
      var threatListed = d.threat_listed;
      var dataSource = d.data_source || '';

      var html = '';

      // ── IP Header ──
      html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-radius:10px;background:var(--bg-base);border:1px solid var(--border);margin-bottom:10px;">';
      html += '<div style="display:flex;align-items:center;gap:8px;">';
      html += '<span style="font-size:16px;font-weight:800;color:var(--accent);font-variant-numeric:tabular-nums;font-family:monospace;" id="ipValue">' + escHtml(ip) + '</span>';
      var ipHideLabel = i18nText('dashboard.ip_hide');
      html += '<button onclick="toggleIpVisibility(this)" data-real="' + escAttr(ip) + '" data-shown="1" style="width:28px;height:24px;display:inline-grid;place-items:center;padding:0;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-muted);cursor:pointer;transition:all 0.15s;" title="' + escAttr(ipHideLabel) + '" aria-label="' + escAttr(ipHideLabel) + '">' + ipVisibilityIcon(true) + '</button>';
      html += '</div>';
      html += '<div style="display:flex;align-items:center;gap:6px;">';
      html += '<span style="font-size:9px;padding:2px 6px;border-radius:8px;background:rgba(34,197,94,0.1);color:#22c55e;border:1px solid rgba(34,197,94,0.2);font-weight:600;">' + escHtml(countryCode) + '</span>';
      html += '<span style="font-size:10px;color:var(--text-muted);">' + escHtml(country) + ' · ' + escHtml(city) + '</span>';
      html += '</div>';
      html += '</div>';

      // ── 3-Section Vertical ──
      html += '<div style="display:flex;flex-direction:column;gap:8px;">';

      // Section 1: 基础物理画像
      html += '<div style="padding:12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);">';
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">' + i18nText('dashboard.ip_basic_profile') + '</div>';
      function _ipRow(label, val, color) {
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:10px;border-bottom:1px solid var(--border);">' +
          '<span style="color:var(--text-muted);">' + label + '</span>' +
          '<span style="color:' + (color || 'var(--text-primary)') + ';font-weight:600;max-width:55%;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escHtml(String(val)) + '">' + escHtml(String(val)) + '</span></div>';
      }
      html += '<div class="ip-info-grid">';
      html += _ipRow(i18nText('dashboard.ip_origin'), nativeType, isNative ? '#22c55e' : '#f59e0b');
      html += _ipRow(i18nText('dashboard.business_flag'), ispType.replace(/.*[（(]/, '').replace(/[）)].*/, '') || '-', ispFlag === 'hosting' ? '#f59e0b' : '#22c55e');
      html += _ipRow(i18nText('dashboard.operator_type'), ispType, ispFlag === 'hosting' ? '#f59e0b' : '#22c55e');
      html += _ipRow(i18nText('dashboard.organization'), org);
      html += '</div></div>';

      // Section 2: ISP 网络底层
      html += '<div style="padding:12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);">';
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">' + i18nText('dashboard.isp_network_layer') + '</div>';
      html += '<div class="ip-info-grid">';
      html += _ipRow('ASN', asn, '#5b8def');
      html += _ipRow(i18nText('dashboard.resolved_timezone'), timezone);
      html += _ipRow(i18nText('dashboard.drift'), driftKm + ' km', hasDrift ? '#ef4444' : '#22c55e');
      html += _ipRow(i18nText('dashboard.reverse_dns'), rdns === 'None' ? 'None' : rdns);
      html += '</div></div>';

      // Section 3: 风险深度检测
      html += '<div style="padding:12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);">';
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">' + i18nText('dashboard.risk_scan') + '</div>';
      html += '<div class="ip-info-grid">';
      var spamColor = threatListed ? '#ef4444' : '#22c55e';
      var spamText = threatListed ? i18nText('dashboard.spamhaus_listed') : i18nText('dashboard.spamhaus_clean');
      html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:10px;border-bottom:1px solid var(--border);"><span style="color:var(--text-muted);">' + i18nText('dashboard.spamhaus_intel') + '</span><span style="color:' + spamColor + ';font-weight:600;">' + spamText + '</span></div>';
      var proxyText = ispWarning || (ispFlag === 'hosting' ? i18nText('dashboard.datacenter_traits') : i18nText('dashboard.no_rdns_traits'));
      html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:10px;border-bottom:1px solid var(--border);"><span style="color:var(--text-muted);">' + i18nText('dashboard.proxy_traits') + '</span><span style="color:' + (ispFlag === 'hosting' ? '#f59e0b' : '#22c55e') + ';font-weight:600;font-size:10px;max-width:55%;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escHtml(proxyText) + '">' + escHtml(proxyText) + '</span></div>';
      html += _ipRow(i18nText('dashboard.data_source'), dataSource);
      html += '</div></div>';

      html += '</div>';

      // ── Network Health Brief Section ──
      var netTips = [];
      if (ispFlag === 'hosting') {
        netTips.push(i18nText('dashboard.tip_hosting'));
      }
      if (threatListed) {
        netTips.push(i18nText('dashboard.tip_spamhaus'));
      }
      if (hasDrift) {
        netTips.push(i18nText('dashboard.tip_drift_prefix') + driftKm + 'km' + i18nText('dashboard.tip_drift_suffix'));
      }
      if (rdns === 'None') {
        netTips.push(i18nText('dashboard.tip_no_rdns'));
      }
      netTips.push(i18nText('dashboard.tip_assessment_prefix') + (ispFlag === 'hosting' ? i18nText('dashboard.needs_work') : i18nText('dashboard.good')));
      netTips.push(i18nText('dashboard.tip_advice'));
      netTips.push(i18nText('dashboard.tip_latency_prefix') + (tcpRtt !== null ? tcpRtt + 'ms' : i18nText('dashboard.not_tested')) + ' · ' + (tcpRtt !== null && tcpRtt < 200 ? i18nText('dashboard.link_excellent') : tcpRtt !== null && tcpRtt < 500 ? i18nText('dashboard.link_fair') : i18nText('dashboard.link_pending')));
      netTips.push(i18nText('dashboard.tip_source_prefix') + (dataSource || i18nText('dashboard.edge_native')) + i18nText('dashboard.tip_source_suffix'));

      var netTipText = netTips.join('　　　');

      // 计算综合网络评分
      var netScore = 100;
      if (ispFlag === 'hosting') netScore -= 25;
      if (threatListed) netScore -= 30;
      if (hasDrift) netScore -= 10;
      if (rdns === 'None') netScore -= 15;
      var netGrade = netScore >= 80 ? 'A' : netScore >= 60 ? 'B' : netScore >= 40 ? 'C' : 'D';
      var netColor = netScore >= 80 ? '#22c55e' : netScore >= 60 ? '#f59e0b' : '#ef4444';
      var netLabel = netScore >= 80 ? i18nText('dashboard.excellent') : netScore >= 60 ? i18nText('dashboard.good') : netScore >= 40 ? i18nText('dashboard.average') : i18nText('dashboard.poor');

      html += '<div style="padding:12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);display:flex;flex-direction:column;">';
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">' + i18nText('dashboard.network_brief') + '</div>';

      // Score row
      html += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;padding:6px 8px;border-radius:6px;background:var(--bg-base);border:1px solid var(--border);">';
      html += '<span style="font-size:20px;font-weight:800;color:' + netColor + ';">' + netGrade + '</span>';
      html += '<div style="flex:1;">';
      html += '<div style="font-size:10px;font-weight:600;color:' + netColor + ';">' + netLabel + ' (' + netScore + i18nText('dashboard.points_unit') + ')</div>';
      html += '<div style="font-size:9px;color:var(--text-muted);">' + escHtml(country) + ' · ' + escHtml(ispType) + ' · ' + escHtml(asn) + '</div>';
      html += '</div>';
      html += '<div style="text-align:right;">';
      html += '<div style="font-size:9px;color:var(--text-muted);">Spamhaus</div>';
      html += '<div style="font-size:10px;font-weight:600;color:' + (threatListed ? '#ef4444' : '#22c55e') + ';">' + (threatListed ? i18nText('dashboard.listed_short') : i18nText('dashboard.clean_short')) + '</div>';
      html += '</div>';
      html += '</div>';

      // Scrolling marquee
      html += '<div style="flex:1;overflow:hidden;border-radius:6px;background:var(--bg-base);border:1px solid var(--border);padding:6px 0;position:relative;min-height:28px;">';
      html += '<div style="position:absolute;left:0;top:0;bottom:0;width:20px;background:linear-gradient(90deg,var(--bg-base),transparent);z-index:1;"></div>';
      html += '<div class="ip-tip-marquee" style="display:flex;white-space:nowrap;animation:ipTipScroll 40s linear infinite;font-size:9px;color:var(--text-muted);letter-spacing:0.2px;">';
      html += '<span style="padding-right:60px;">' + escHtml(netTipText) + '</span>';
      html += '<span style="padding-right:60px;">' + escHtml(netTipText) + '</span>';
      html += '</div>';
      html += '<div style="position:absolute;right:0;top:0;bottom:0;width:20px;background:linear-gradient(270deg,var(--bg-base),transparent);z-index:1;"></div>';
      html += '</div>';

      html += '</div>';

      panel.innerHTML = html;
    })
    .catch(function() {
      panel.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:11px;">' + i18nText('dashboard.ip_load_failed') + '</div>';
    });
}

function ipVisibilityIcon(shown) {
  var slash = shown ? '' : '<path d="M3 3l18 18"/>';
  return '<svg viewBox="0 0 24 24" aria-hidden="true" style="width:15px;height:15px;display:block;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/>' + slash + '</svg>';
}

function updateIpVisibilityButton(btn, shown) {
  var label = i18nText(shown ? 'dashboard.ip_hide' : 'dashboard.ip_show');
  btn.innerHTML = ipVisibilityIcon(shown);
  btn.title = label;
  btn.setAttribute('aria-label', label);
}

function toggleIpVisibility(btn) {
  var ipEl = document.getElementById('ipValue');
  if (!ipEl) return;
  var shown = btn.dataset.shown === '1';
  if (shown) {
    ipEl.textContent = '***.***.***.***';
    btn.dataset.shown = '0';
    updateIpVisibilityButton(btn, false);
  } else {
    ipEl.textContent = btn.dataset.real;
    btn.dataset.shown = '1';
    updateIpVisibilityButton(btn, true);
  }
}

function _loadHostResources() {
  var panel = document.getElementById('hostResPanel');
  if (!panel) return;

  _authFetch('/api/dashboard/resources')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (d.error) {
        panel.innerHTML = '<div style="text-align:center;padding:16px;color:#ef4444;font-size:11px;">' + escHtml(d.error) + '</div>';
        return;
      }

      var html = '';

      function _resBar(label, val, pct, color) {
        return '<div style="margin-bottom:8px;">' +
          '<div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:3px;">' +
          '<span style="color:var(--text-muted);">' + label + '</span>' +
          '<span style="color:var(--text-primary);font-weight:600;">' + val + '</span>' +
          '</div>' +
          '<div style="height:4px;border-radius:2px;background:var(--border);overflow:hidden;">' +
          '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:2px;transition:width 0.5s;"></div>' +
          '</div></div>';
      }

      var cpuColor = d.cpu_percent > 80 ? '#ef4444' : d.cpu_percent > 50 ? '#f59e0b' : '#22c55e';
      var memColor = d.mem_percent > 80 ? '#ef4444' : d.mem_percent > 50 ? '#f59e0b' : '#22c55e';
      var diskColor = d.disk_percent > 90 ? '#ef4444' : d.disk_percent > 70 ? '#f59e0b' : '#22c55e';
      var swapColor = d.swap_percent > 50 ? '#ef4444' : d.swap_percent > 20 ? '#f59e0b' : '#22c55e';

      // CPU
      html += _resBar('CPU', d.cpu_percent + '% · ' + d.cpu_count + i18nText('dashboard.cpu_cores') + (d.cpu_count_physical ? '/' + d.cpu_count_physical + i18nText('dashboard.cpu_physical') : '') + (d.cpu_freq_mhz ? ' · ' + d.cpu_freq_mhz + 'MHz' : ''), d.cpu_percent, cpuColor);
      // Memory
      html += _resBar(i18nText('extensions.memory'), d.mem_used_gb + ' / ' + d.mem_total_gb + ' GB · ' + i18nText('dashboard.available') + ' ' + d.mem_available_gb + ' GB', d.mem_percent, memColor);
      // Swap
      if (d.swap_total_gb > 0) {
        html += _resBar('Swap', d.swap_used_gb + ' / ' + d.swap_total_gb + ' GB', d.swap_percent, swapColor);
      }
      // Disk
      html += _resBar(i18nText('extensions.disk'), d.disk_used_gb + ' / ' + d.disk_total_gb + ' GB · ' + i18nText('dashboard.free') + ' ' + d.disk_free_gb + ' GB', d.disk_percent, diskColor);

      // Network IO
      html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);">';
      html += '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">' + i18nText('dashboard.network_io') + '</div>';
      html += '<div style="display:flex;gap:8px;">';
      html += '<div style="flex:1;text-align:center;padding:4px;border-radius:6px;background:var(--bg-base);">';
      html += '<div style="font-size:12px;font-weight:700;color:#22c55e;">↑ ' + d.net_sent_mb + ' MB</div>';
      html += '<div style="font-size:8px;color:var(--text-muted);">' + i18nText('dashboard.sent') + '</div>';
      html += '</div>';
      html += '<div style="flex:1;text-align:center;padding:4px;border-radius:6px;background:var(--bg-base);">';
      html += '<div style="font-size:12px;font-weight:700;color:#5b8def;">↓ ' + d.net_recv_mb + ' MB</div>';
      html += '<div style="font-size:8px;color:var(--text-muted);">' + i18nText('dashboard.received') + '</div>';
      html += '</div>';
      html += '</div></div>';

      // Uptime
      var upSec = d.uptime_seconds || 0;
      var upDays = Math.floor(upSec / 86400);
      var upHours = Math.floor((upSec % 86400) / 3600);
      var upMins = Math.floor((upSec % 3600) / 60);
      var upStr = (upDays > 0 ? upDays + i18nText('dashboard.days_unit') : '') + upHours + i18nText('dashboard.hours_unit') + upMins + i18nText('dashboard.minutes_unit');
      html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;font-size:10px;">';
      html += '<span style="color:var(--text-muted);">' + i18nText('dashboard.uptime') + '</span>';
      html += '<span style="color:var(--text-primary);font-weight:600;">' + upStr + '</span>';
      html += '</div>';
      // Top processes
      if (d.top_processes && d.top_processes.length > 0) {
        html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);">';
        html += '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">' + i18nText('dashboard.top_processes') + '</div>';
        for (var i = 0; i < Math.min(d.top_processes.length, 3); i++) {
          var p = d.top_processes[i];
          html += '<div style="display:flex;justify-content:space-between;font-size:9px;padding:2px 0;color:var(--text-secondary);">';
          html += '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:50%;">' + escHtml(p.name) + '</span>';
          html += '<span>C:' + p.cpu + '% M:' + p.mem + '%</span>';
          html += '</div>';
        }
        html += '</div>';
      }

      panel.innerHTML = html;
    })
    .catch(function() {
      panel.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:11px;">' + i18nText('dashboard.resources_load_failed') + '</div>';
    });
}

function _loadNetStatus() {
  var bar = document.getElementById('netStatusBar');
  if (!bar) return;
  bar.innerHTML = '<span class="network-status-message">' + i18nText('dashboard.network_checking') + '</span>';

  _authFetch('/api/dashboard/network')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var results = d.results || {};
      var names = ['OpenAI', 'Gemini', 'Anthropic', 'Agnes', 'Qwen', 'Zhipu', 'Volcengine', 'Baidu', 'Tencent', 'Moonshot', 'DeepSeek', 'MiniMax'];
      var html = '<span class="network-status-label" title="' + i18nText('dashboard.network_latency_title') + '">' + i18nText('dashboard.network_connectivity') + '</span>';
      for (var i = 0; i < names.length; i++) {
        var n = names[i];
        var r = results[n] || {status:'error', ms:0};
        var statusClass = r.status === 'ok' ? (r.ms < 800 ? 'is-good' : r.ms < 2000 ? 'is-warn' : 'is-error') : 'is-error';
        var label = r.status === 'ok' ? r.ms + 'ms' : '✗';
        html += '<div class="network-status-chip ' + statusClass + '" title="' + n + (r.status === 'ok' ? ' ' + i18nText('dashboard.network_tcp_prefix') + r.ms + 'ms' : ' ' + i18nText('dashboard.unreachable')) + '">';
        html += '<span class="network-status-dot"></span>';
        html += '<span>' + n + '</span>';
        html += '<span class="network-status-value">' + label + '</span>';
        html += '</div>';
      }
      bar.innerHTML = html;
    })
    .catch(function() {
      bar.innerHTML = '<span class="network-status-message is-error">' + i18nText('dashboard.network_check_failed') + '</span>';
    });
}

function _dashCard(title, body, accentColor) {
  return '<div class="glass-card" style="padding:16px;text-align:center;">' +
    '<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">' + title + '</div>' +
    body + '</div>';
}

function _scoreBar(label, value, max, color) {
  var pct = max > 0 ? (value / max * 100) : 0;
  return '<div style="margin-bottom:8px;">' +
    '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">' +
      '<span style="color:var(--text-secondary);">' + label + '</span>' +
      '<span style="color:var(--text-primary);font-weight:600;">' + value + '/' + max + '</span>' +
    '</div>' +
    '<div style="height:5px;border-radius:3px;background:var(--bg-base);overflow:hidden;">' +
      '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:3px;transition:width 0.5s;"></div>' +
    '</div>' +
  '</div>';
}

function _infoRow(label, value) {
  return '<div style="display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:12px;">' +
    '<span style="color:var(--text-secondary);">' + label + '</span>' +
    '<span style="color:var(--text-primary);display:flex;align-items:center;">' + value + '</span>' +
  '</div>';
}

function _fmtUptime(sec) {
  if (sec < 60) return Math.round(sec) + 's';
  if (sec < 3600) return Math.floor(sec/60) + 'm ' + Math.round(sec%60) + 's';
  var h = Math.floor(sec/3600);
  var m = Math.floor((sec%3600)/60);
  return h + 'h ' + m + 'm';
}

function _quickNav(icon, label, onclick) {
  return '<div class="glass-card dashboard-quick-card" style="padding:14px;text-align:center;cursor:pointer;transition:transform 0.15s;" onclick="' + onclick + '" onmouseover="this.style.transform=\'translateY(-2px)\'" onmouseout="this.style.transform=\'none\'">' +
    '<div class="dashboard-quick-icon" style="width:30px;height:30px;margin:0 auto 7px;color:var(--accent);"><span style="display:block;width:100%;height:100%;">' + icon + '</span></div>' +
    '<div style="font-size:12px;font-weight:600;color:var(--text-primary);">' + label + '</div>' +
  '</div>';
}

function copyGenBoxQQGroup() {
  var group = '1005859624';
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(group).then(function(){ setStatus('QQ??????' + group); });
    return;
  }
  var input = document.createElement('textarea');
  input.value = group; input.style.position = 'fixed'; input.style.opacity = '0';
  document.body.appendChild(input); input.select(); document.execCommand('copy'); input.remove();
  setStatus('QQ??????' + group);
}

function serverControl(action) {
  if (action === 'stop' || action === 'restart') {
    alert(i18nText('server.use_lab_launcher'));
    return;
  }
  if (action === 'stop') {
    if (!confirm(i18nText('server.confirm_stop'))) return;
  }
  if (action === 'restart') {
    if (!confirm(i18nText('server.confirm_restart'))) return;
  }
  _authFetch('/api/server/control?action=' + action)
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (action === 'stop') {
        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--text-muted);font-size:16px;">' + i18nText('server.stopped') + '</div>';
      } else if (action === 'restart') {
        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--text-muted);font-size:16px;">' + i18nText('server.restarting') + '</div>';
        setTimeout(function(){ location.reload(); }, 5000);
      }
    })
    .catch(function(e) {
      alert(i18nText('server.action_failed') + e.message);
    });
}

function loadHistory() {
  var h = document.getElementById('historyList');
  var search = document.getElementById('historySearch') ? document.getElementById('historySearch').value : '';
  var provider = document.getElementById('historyFilterProvider') ? document.getElementById('historyFilterProvider').value : '';
  var mode = document.getElementById('historyFilterMode') ? document.getElementById('historyFilterMode').value : '';
  var sortBy = document.getElementById('historySortBy') ? document.getElementById('historySortBy').value : 'time_desc';
  var params = 'limit=100';
  if (search) params += '&search=' + encodeURIComponent(search);
  if (provider) params += '&provider=' + encodeURIComponent(provider);
  if (mode) params += '&mode=' + encodeURIComponent(mode);
  _authFetch('/api/history?' + params).then(function(r){return r.json();}).then(function(d){
    var items = d.items || [];
    allHistoryItems = items; // 保存完整数据
    updateHistoryFilterProviders();
    // 前端排序
    if (sortBy === 'time_asc') {
      items = items.slice().reverse();
    }
    if (!items.length) {
      h.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:60px;font-size:13px;">' + i18nText('history.empty') + '</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < items.length; i++) {
      (function(item){
        var isVideo = item.type === 'video';
        var ok = 0;
        for (var k in item.results) { if (item.results[k].success) ok++; }
        var modeTag = isVideo ? i18nText('dashboard.video_generation') : (item.mode === 'i2i' ? i18nText('creator.i2i') : i18nText('creator.t2i'));
        var tags = '';
        for (var j = 0; j < item.providers.length; j++) {
          var pInfo = findProvider(item.providers[j]) || {name: item.providers[j], color: '#5b8def'};
          tags += '<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;background:' + pInfo.color + '15;color:' + pInfo.color + ';border-radius:5px;font-size:10px;font-weight:600;">' +
            '<span style="width:5px;height:5px;border-radius:50%;background:' + pInfo.color + ';"></span>' +
            escHtml(pInfo.name) + '</span>';
        }
        var elapsedStr = item.elapsed_seconds ? (' · ' + item.elapsed_seconds.toFixed(1) + 's') : '';
        var statusTag = isVideo && item.status ? (' · <span style="color:' + (item.status === 'completed' ? '#22c3a5' : (item.status === 'failed' ? '#ef4444' : '#fbbf24')) + ';">' + item.status + '</span>') : '';
        html += '<div class="history-item">' +
          '<div class="history-meta">' +
            '<span>' + item.created_at + '</span>' +
            '<span>' + modeTag + '</span>' +
            '<span style="color:' + (ok === item.providers.length ? '#22c3a5' : '#fbbf24') + ';">' + ok + '/' + item.providers.length + ' ' + i18nText('dashboard.success') + '</span>' +
            '<span style="color:var(--accent);font-size:11px;">' + elapsedStr + statusTag + '</span>' +
          '</div>' +
          '<div class="history-prompt">' + escHtml(item.prompt || '') + '</div>' +
          (item.enhanced_prompt && item.enhanced_prompt !== item.prompt ?
            '<div style="font-size:11px;color:var(--accent);margin-top:6px;">✨ ' + escHtml(item.enhanced_prompt) + '</div>' : '') +
          '<div class="history-tags" style="margin-top:8px;">' + tags + '</div>' +
          (item.results ? '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">' +
            Object.values(item.results).filter(function(r){return r.success&&(r.local_path||r.video_url);}).map(function(r){
              if (isVideo) {
                return '<div onclick="event.stopPropagation();openLightbox(\'' + (r.video_url || '') + '\')" style="width:80px;height:60px;background:var(--bg-tertiary);border-radius:8px;border:1px solid var(--border);display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:20px;">▶</div>';
              } else {
                var f = r.local_path.split(/[\\/]/).pop();
                return '<img src="/api/gallery/thumb/' + f + '" style="width:60px;height:60px;object-fit:cover;border-radius:8px;border:1px solid var(--border);cursor:pointer;" onclick="openLightbox(\'/api/gallery/image/' + f + '\')">';
              }
            }).join('') + '</div>' : '') +
        '</div>';
      })(items[i]);
    }
    h.innerHTML = html;
  }).catch(function(e){
    h.innerHTML = '<div style="text-align:center;color:#f87171;padding:40px;">' + i18nText('common.load_failed') + '</div>';
  });
}

// ═══════════════════════════════════════════════════════════════════
// Provider 设置弹窗
// ═══════════════════════════════════════════════════════════════════
function _loadProxyConfig() {
  _authFetch('/api/proxy')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var el = document.getElementById('proxyEnabled');
      if (el) el.checked = d.enabled;
      var t = document.getElementById('proxyType');
      if (t) t.value = d.type || 'http';
      var h = document.getElementById('proxyHost');
      if (h) h.value = d.host || '127.0.0.1';
      var p = document.getElementById('proxyPort');
      if (p) p.value = d.port || 10808;
      var u = document.getElementById('proxyUser');
      if (u) u.value = d.username || '';
      var badge = document.getElementById('proxyStatusBadge');
      if (badge) {
        if (d.enabled) {
          badge.textContent = d.host + ':' + d.port;
          badge.style.background = '#22c55e22';
          badge.style.color = '#22c55e';
        } else {
          badge.textContent = i18nText('proxy.disabled');
          badge.style.background = '#6b728022';
          badge.style.color = '#6b7280';
        }
      }
    });
}

function saveProxyConfig() {
  var data = {
    enabled: document.getElementById('proxyEnabled').checked,
    type: document.getElementById('proxyType').value,
    host: document.getElementById('proxyHost').value.trim(),
    port: parseInt(document.getElementById('proxyPort').value) || 10808,
    username: document.getElementById('proxyUser').value.trim(),
    password: document.getElementById('proxyPass').value,
  };
  _authFetch('/api/proxy', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
  .then(function(r){ return r.json(); })
  .then(function(d) {
    var badge = document.getElementById('proxyStatusBadge');
    if (badge) {
      if (data.enabled) {
        badge.textContent = data.host + ':' + data.port;
        badge.style.background = '#22c55e22';
        badge.style.color = '#22c55e';
      } else {
        badge.textContent = i18nText('proxy.disabled');
        badge.style.background = '#6b728022';
        badge.style.color = '#6b7280';
      }
    }
    var result = document.getElementById('proxyTestResult');
    if (result) result.innerHTML = '<span style="color:#22c55e;">' + i18nText('proxy.saved') + '</span>';
  });
}

function testProxyConfig() {
  var btn = document.getElementById('proxyTestBtn');
  var result = document.getElementById('proxyTestResult');
  if (btn) { btn.textContent = i18nText('proxy.testing'); btn.disabled = true; }
  if (result) result.innerHTML = '<span style="color:var(--text-muted);">' + i18nText('proxy.testing_status') + '</span>';

  _authFetch('/api/proxy/test', { method: 'POST' })
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (btn) { btn.textContent = i18nText('extensions.test_connection'); btn.disabled = false; }
      if (!d.ok) {
        var msgs = [];
        var keys = Object.keys(d.results || {});
        for (var i = 0; i < keys.length; i++) {
          var r = d.results[keys[i]];
          msgs.push(keys[i] + ': ' + (r.status === 'ok' ? r.ms + 'ms ✓' : '✗ ' + (r.error || '不通')));
        }
        if (result) result.innerHTML = '<span style="color:#f59e0b;">' + i18nText('proxy.partial_failure') + '</span><br>' + msgs.join('<br>');
      } else {
        var msgs2 = [];
        var keys2 = Object.keys(d.results || {});
        for (var j = 0; j < keys2.length; j++) {
          var r2 = d.results[keys2[j]];
          msgs2.push(keys2[j] + ': ' + r2.ms + 'ms ✓');
        }
        if (result) result.innerHTML = '<span style="color:#22c55e;">' + i18nText('proxy.ok') + '</span><br>' + msgs2.join('<br>');
      }
    })
    .catch(function(e) {
      if (btn) { btn.textContent = i18nText('extensions.test_connection'); btn.disabled = false; }
      if (result) result.innerHTML = '<span style="color:#ef4444;">? ' + i18nText('proxy.test_failed_prefix') + escHtml(e.message) + '</span>';
    });
}

// ── 自动更新系统 ──

function _loadUpdateInfo() {
  _authFetch('/api/update/info')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var platformEl = document.getElementById('updatePlatformInfo');
      if (platformEl) {
        var typeLabel = { source: '源码', exe: '可执行文件', docker: 'Docker', pip: 'pip' };
        platformEl.textContent = i18nText('update.current_prefix') + _formatUpdateVersion(d.current_version) + ' | ' + (typeLabel[d.update_type] || d.update_type);
      }
      // 检查更新
      _checkForUpdates();
    })
    .catch(function() {
      var el = document.getElementById('updateContent');
      if (el) el.innerHTML = '<span style="color:var(--text-muted);">' + i18nText('update.info_unavailable') + '</span>';
    });
}

function _checkForUpdates() {
  var badge = document.getElementById('updateStatusBadge');
  var content = document.getElementById('updateContent');
  if (badge) { badge.textContent = i18nText('update.checking_short'); badge.style.background = '#6b728022'; badge.style.color = '#6b7280'; }
  if (content) content.innerHTML = '<span style="color:var(--text-muted);">' + i18nText('update.checking_progress') + '</span>';

  _authFetch('/api/update/check')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (d.available) {
        _globalUpdateData = d;
        if (localStorage.getItem('genbox_update_check') !== 'off') renderUpdateBadge(d);
        if (badge) { badge.textContent = i18nText('update.available_badge'); badge.style.background = '#f59e0b22'; badge.style.color = '#f59e0b'; }
        var notes = d.release_notes ? '<div style="margin:6px 0;padding:8px;border-radius:6px;background:var(--bg-card);max-height:120px;overflow-y:auto;white-space:pre-wrap;font-size:10px;color:var(--text-secondary);">' + escHtml(d.release_notes) + '</div>' : '';
        if (content) {
          content.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">' +
            '<span style="color:#f59e0b;font-weight:600;">⬆ ' + _formatUpdateVersion(d.latest_version) + ' 可用</span>' +
            '<a href="' + escHtml(_canonicalReleaseHref(d.latest_version)) + '" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="font-size:10px;">' + i18nText('update.open_verified_release') + '</a>' +
            '</div><div style="color:var(--text-secondary);line-height:1.5;">' + escHtml(i18nText('update.manual_install_guidance')) + '</div>' + notes;
        }
      } else {
        _globalUpdateData = d;
        renderUpdateBadge(d);
        if (badge) { badge.textContent = i18nText('update.up_to_date_badge'); badge.style.background = '#22c55e22'; badge.style.color = '#22c55e'; }
        if (content) content.innerHTML = '<span style="color:#22c55e;">? ' + i18nText('update.up_to_date') + '</span> <button onclick="_checkForUpdates()" style="margin-left:8px;padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">' + i18nText('update.recheck') + '</button>';
      }
    })
    .catch(function(e) {
      if (badge) { badge.textContent = i18nText('update.check_failed_badge'); badge.style.background = '#ef444422'; badge.style.color = '#ef4444'; }
      if (content) content.innerHTML = '<span style="color:#ef4444;">? ' + i18nText('update.check_failed_prefix') + escHtml(e.message) + '</span>';
    });
}

var _globalUpdateData = null;

function _formatUpdateVersion(version) {
  var value = String(version || '');
  return /^v/i.test(value) ? value : 'v' + value;
}

function _canonicalReleaseHref(version) {
  var value = String(version || '').trim();
  var releases = 'https://github.com/liwei9745/GenBox/releases';
  if (!/^v?\d+\.\d+\.\d+(?:-rc\.\d+)?$/.test(value)) return releases;
  return releases + '/tag/' + encodeURIComponent(value);
}

function checkGlobalUpdate(force) {
  if (!force && localStorage.getItem('genbox_update_check') === 'off') {
    _globalUpdateData = { disabled: true };
    renderUpdateBadge(_globalUpdateData);
    return Promise.resolve(_globalUpdateData);
  }
  renderUpdateBadge({ checking: true });
  return _authFetch('/api/update/check').then(function(r){
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(d){
    _globalUpdateData = d;
    renderUpdateBadge(d);
    return d;
  }).catch(function(e){
    _globalUpdateData = { check_error: true, error: e.message };
    renderUpdateBadge(_globalUpdateData);
    return _globalUpdateData;
  });
}

function renderUpdateBadge(d) {
  var badge = document.getElementById('globalUpdateBadge');
  var text = document.getElementById('globalUpdateBadgeText');
  var icon = document.getElementById('globalUpdateBadgeIcon');
  var versionSpan = document.getElementById('updateModalVersion');
  if (!badge || !text) return;
  badge.classList.remove('hidden', 'has-update', 'is-current', 'is-ignored', 'is-error', 'is-disabled', 'is-checking');
  if (!d || d.checking) {
    badge.classList.add('is-checking');
    if (icon) icon.textContent = '↻';
    text.textContent = i18nText('update.checking');
    return;
  }
  if (d.disabled) {
    badge.classList.add('is-disabled');
    if (icon) icon.textContent = '−';
    text.textContent = i18nText('update.auto_check_off');
    return;
  }
  if (d.check_error) {
    badge.classList.add('is-error');
    if (icon) icon.textContent = '!';
    text.textContent = i18nText('update.check_failed');
    return;
  }
  if (d && d.available && d.latest_version) {
    var ignored = localStorage.getItem('genbox_update_ignored');
    if (ignored === d.latest_version) {
      badge.classList.add('is-ignored');
      if (icon) icon.textContent = '−';
      text.textContent = _formatUpdateVersion(d.latest_version) + ' ' + i18nText('update.ignored_suffix');
    } else {
      badge.classList.add('has-update');
      if (icon) icon.textContent = '↑';
      text.textContent = _formatUpdateVersion(d.latest_version) + ' ' + i18nText('update.available_suffix');
    }
    if (versionSpan) versionSpan.textContent = _formatUpdateVersion(d.latest_version);
  } else {
    var currentVersion = d.current_version || d.latest_version || '';
    badge.classList.add('is-current');
    if (icon) icon.textContent = '✓';
    text.textContent = (currentVersion ? _formatUpdateVersion(currentVersion) + ' ' : '') + i18nText('update.up_to_date_badge');
  }
}

function openUpdateModal() {
  var d = _globalUpdateData;
  if (!d || d.disabled) {
    checkGlobalUpdate(true).then(openUpdateModal);
    return;
  }
  var heading = document.getElementById('updateModalHeading');
  var versionEl = document.getElementById('updateModalVersion');
  var notesEl = document.getElementById('updateModalNotes');
  var status = document.getElementById('updateModalStatus');
  status.classList.add('hidden');
  status.textContent = '';
  var applyBtn = document.getElementById('updateApplyBtn');
  applyBtn.disabled = false;
  var ignoreBtn = document.getElementById('updateIgnoreBtn');
  var downloadLink = document.getElementById('updateDownloadLink');
  if (d.check_error) {
    heading.textContent = i18nText('update.check_failed');
    versionEl.textContent = '';
    notesEl.textContent = d.error || i18nText('update.service_unavailable');
    ignoreBtn.classList.add('hidden');
    downloadLink.classList.add('hidden');
    applyBtn.textContent = i18nText('update.recheck');
  } else if (d.available) {
    heading.textContent = i18nText('update.found_new');
    versionEl.textContent = _formatUpdateVersion(d.latest_version);
    notesEl.textContent = d.release_notes || i18nText('update.no_notes');
    ignoreBtn.classList.remove('hidden');
    downloadLink.classList.remove('hidden');
    downloadLink.href = _canonicalReleaseHref(d.latest_version);
    downloadLink.textContent = i18nText('update.open_verified_release');
    applyBtn.disabled = true;
    applyBtn.setAttribute('aria-disabled', 'true');
    applyBtn.textContent = i18nText('update.auto_apply_unavailable');
    status.classList.remove('hidden');
    status.textContent = i18nText('update.manual_install_guidance');
  } else {
    heading.textContent = i18nText('update.up_to_date');
    versionEl.textContent = _formatUpdateVersion(d.current_version || d.latest_version);
    notesEl.textContent = i18nText('update.none_available');
    ignoreBtn.classList.add('hidden');
    downloadLink.classList.add('hidden');
    applyBtn.textContent = i18nText('update.recheck');
  }
  document.getElementById('updateModal').classList.add('show');
}

function closeUpdateModal() {
  document.getElementById('updateModal').classList.remove('show');
}

function ignoreGlobalUpdate() {
  var d = _globalUpdateData;
  if (!d || !d.latest_version) return;
  localStorage.setItem('genbox_update_ignored', d.latest_version);
  closeUpdateModal();
  renderUpdateBadge(d);
}

function applyGlobalUpdate() {
  var d = _globalUpdateData;
  if (!d || !d.available) {
    checkGlobalUpdate(true).then(openUpdateModal);
    return;
  }
  openUpdateModal();
}

function toggleUpdateCheck(el) {
  localStorage.setItem('genbox_update_check', el.checked ? 'on' : 'off');
  if (el.checked) checkGlobalUpdate();
  else { _globalUpdateData = { disabled: true }; renderUpdateBadge(_globalUpdateData); }
}

function _applyUpdate() {
  var badge = document.getElementById('updateStatusBadge');
  var content = document.getElementById('updateContent');
  var globalBtn = document.getElementById('updateApplyBtn');
  var globalStatus = document.getElementById('updateModalStatus');
  if (badge) { badge.textContent = i18nText('update.auto_apply_unavailable'); badge.style.background = '#f59e0b22'; badge.style.color = '#f59e0b'; }
  if (content) content.textContent = i18nText('update.manual_install_guidance');
  if (globalBtn) { globalBtn.disabled = true; globalBtn.setAttribute('aria-disabled', 'true'); globalBtn.textContent = i18nText('update.auto_apply_unavailable'); }
  if (globalStatus) { globalStatus.classList.remove('hidden'); globalStatus.textContent = i18nText('update.manual_install_guidance'); }

  _authFetch('/api/update/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var detail = d && d.detail ? d.detail : d;
      var unavailable = detail && detail.code === 'update_apply_unavailable';
      var messageText = unavailable ? i18nText('update.manual_install_guidance') : i18nText('update.auto_apply_unavailable');
      if (content) content.textContent = messageText;
      if (globalStatus) globalStatus.textContent = messageText;
    })
    .catch(function() {
      if (content) content.textContent = i18nText('update.manual_install_guidance');
      if (globalStatus) globalStatus.textContent = i18nText('update.manual_install_guidance');
    });
}

function openProviderModal() {
  document.getElementById('providerModal').classList.add('show');
  renderProviderEdit();
}
function closeProviderModal() {
  document.getElementById('providerModal').classList.remove('show');
}

// ══ 认证与安全策略 ══
var _adminKey = '';
var _loginAttemptGeneration = 0;
var _backendOnline = null;
var _backendFailureCount = 0;
var _runtimeHeartbeatTimer = null;
try { localStorage.removeItem('igs_admin_key'); } catch (error) {}

function _setBackendState(online, runtime) {
  if (_backendOnline === online && (!online || (runtime && window._genboxRuntimeId === runtime.runtime_id))) return;
  _backendOnline = online;
  var left = document.getElementById('statusLeft');
  var right = document.getElementById('statusRight');
  var banner = document.getElementById('backendOfflineBanner');
  if (online && runtime) {
    window._genboxRuntimeId = runtime.runtime_id;
    if (left) left.textContent = i18nText('runtime.online');
    if (right) right.textContent = 'GenBox' + (runtime.version ? ' v' + runtime.version : '') + ' · ' + runtime.mode.toUpperCase() + ' · ' + runtime.port;
    if (banner) banner.classList.add('hidden');
  } else {
    if (left) left.textContent = i18nText('runtime.offline');
    if (right) right.textContent = i18nText('runtime.offline_detail');
    if (banner) banner.classList.remove('hidden');
  }
  if (typeof window.setExtensionsBackendOnline === 'function') window.setExtensionsBackendOnline(online, runtime || null);
}

function checkRuntimeStatus(immediate) {
  return fetch('/api/setup/status', {cache: 'no-store'}).then(function(response) {
    if (!response.ok) throw new Error('SETUP_STATUS_UNAVAILABLE');
    return response.json();
  }).then(function(setup) {
    if (!setup || (setup.app_mode !== 'dev' && setup.app_mode !== 'prod')) throw new Error('SETUP_STATUS_INVALID');
    if (setup.app_mode === 'prod') return {service:'genbox',version:'',mode:'prod',port:Number(location.port||8891),runtime_id:'production'};
    return fetch('/api/runtime/status', {cache: 'no-store'}).then(function(response) {
      if (!response.ok) throw new Error('RUNTIME_STATUS_UNAVAILABLE');
      return response.json();
    });
  }).then(function(runtime) {
    if (!runtime || runtime.service !== 'genbox' || !runtime.runtime_id) throw new Error('RUNTIME_STATUS_INVALID');
    _backendFailureCount = 0;
    _setBackendState(true, runtime);
    return runtime;
  }).catch(function(error) {
    _backendFailureCount += 1;
    if (immediate || _backendFailureCount >= 2) _setBackendState(false, null);
    throw error;
  });
}

function startRuntimeHeartbeat() {
  if (location.hostname !== '127.0.0.1' && location.hostname !== 'localhost') return;
  checkRuntimeStatus(true).catch(function() {});
  if (_runtimeHeartbeatTimer) clearInterval(_runtimeHeartbeatTimer);
  _runtimeHeartbeatTimer = setInterval(function() { checkRuntimeStatus(false).catch(function() {}); }, 3000);
}

function _authFetch(url, opts) {
  opts = opts || {};
  if (!opts.headers) opts.headers = {};
  var requestKey = _adminKey;
  if (requestKey) opts.headers['X-Admin-Key'] = requestKey;
  if (opts.body && !opts.headers['Content-Type']) opts.headers['Content-Type'] = 'application/json';
  return fetch(url, opts).then(function(r) {
    if (r.status === 401) {
      if (_adminKey === requestKey) {
        _adminKey = '';
        try { localStorage.removeItem('igs_admin_key'); } catch (error) {}
        _showLogin();
      }
      throw new Error('AUTH_REQUIRED');
    }
    return r;
  }).catch(function(error) {
    if (error && error.message !== 'AUTH_REQUIRED' && typeof _setBackendState === 'function') _setBackendState(false, null);
    throw error;
  });
}

function _showLogin() {
  document.getElementById('loginPage').style.display = 'flex';
  document.getElementById('loginKeyInput').focus();
}
function _hideLogin() {
  document.getElementById('loginPage').style.display = 'none';
}
function _setLoginError(visible) {
  var error = document.getElementById('loginError');
  if (!error) return;
  error.style.display = visible ? 'block' : 'none';
  if (error.classList && typeof error.classList.toggle === 'function') {
    error.classList.toggle('hidden', !visible);
  }
}
function _setLoginPending(pending) {
  var page = document.getElementById('loginPage');
  var button = page && page.querySelector ? page.querySelector('button') : null;
  if (button) button.disabled = pending;
}
function _captureLoginAttempt(attempt) {
  return attempt === undefined || attempt === null ? _loginAttemptGeneration : attempt;
}
function _isCurrentLoginAttempt(attempt) {
  return attempt === _loginAttemptGeneration;
}
function _loadProvidersAfterLogin(attempt) {
  var result;
  if (typeof loadProviders === 'function') result = loadProviders(attempt);
  else if (window && typeof window.loadProviders === 'function') result = window.loadProviders(attempt);
  else result = Promise.resolve();
  return Promise.resolve(result).then(function(value) {
    if (!_isCurrentLoginAttempt(attempt)) return;
    return value;
  });
}
function doLogin() {
  var key = document.getElementById('loginKeyInput').value.trim();
  if (!key) return;
  var attempt = ++_loginAttemptGeneration;
  _adminKey = '';
  _setLoginError(false);
  _setLoginPending(true);
  return fetch('/api/providers', {headers: {'X-Admin-Key': key}}).then(function(r) {
    if (attempt !== _loginAttemptGeneration) return;
    if (!r.ok) throw new Error('LOGIN_REJECTED');
    _adminKey = key;
    _hideLogin();
    return _loadProvidersAfterLogin(attempt).then(function() {
      if (attempt !== _loginAttemptGeneration) return;
      return checkSetupWizard(attempt);
    });
  }).catch(function() {
    if (attempt !== _loginAttemptGeneration) return;
    _adminKey = '';
    _setLoginError(true);
    _showLogin();
  }).finally(function() {
    if (attempt === _loginAttemptGeneration) _setLoginPending(false);
  });
}
function _showWelcome(key) {
  document.getElementById('welcomeKeyText').textContent = key;
  document.getElementById('welcomePage').style.display = 'flex';
}
function copyWelcomeKey() {
  var key = document.getElementById('welcomeKeyText').textContent;
  navigator.clipboard.writeText(key).then(function() {
    setStatus(i18nText('welcome.key_copied'));
  });
}
function setupWizardMarkup() {
  return '' +
    '<div class="glass-panel" style="width:min(1080px,96vw);max-height:92vh;overflow-y:auto;padding:24px;">' +
      '<div class="flex items-start justify-between gap-12 flex-wrap mb-20">' +
        '<div style="max-width:640px;">' +
          '<div class="text-xs text-muted mb-8">' + i18nText('nav.guide') + '</div>' +
          '<h2 class="text-lg font-bold mb-8">' + i18nText('onboarding.title') + '</h2>' +
          '<p class="text-sm text-muted mb-12">' + i18nText('onboarding.subtitle') + '</p>' +
          '<div class="flex gap-8 flex-wrap">' +
            '<span class="status-chip" style="background:var(--accent-light);color:var(--accent);">' + i18nText('onboarding.badge_beginner') + '</span>' +
            '<span class="status-chip" style="background:rgba(34,197,94,.12);color:#22c55e;">' + i18nText('onboarding.badge_bilingual') + '</span>' +
          '</div>' +
        '</div>' +
        '<div style="min-width:260px;flex:1;max-width:340px;background:var(--bg-surface);border:1px solid var(--border);border-radius:16px;padding:16px;">' +
          '<div class="text-sm font-bold mb-10">' + i18nText('onboarding.path_title') + '</div>' +
          '<ol class="text-sm text-muted" style="display:grid;gap:10px;padding-left:18px;line-height:1.6;">' +
            '<li>' + i18nText('onboarding.path_step_1') + '</li>' +
            '<li>' + i18nText('onboarding.path_step_2') + '</li>' +
            '<li>' + i18nText('onboarding.path_step_3') + '</li>' +
          '</ol>' +
        '</div>' +
      '</div>' +
      '<div class="dash-grid" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:20px;">' +
        '<section class="glass-panel" style="padding:18px;border-radius:16px;">' +
          '<div class="text-sm font-bold mb-8">' + i18nText('onboarding.step_1_title') + '</div>' +
          '<p class="text-sm text-muted mb-12">' + i18nText('onboarding.step_1_desc') + '</p>' +
          '<div class="flex gap-8 flex-wrap">' +
            '<button class="btn-primary" type="button" onclick="onboardingOpenProviders()">' + i18nText('onboarding.action_models') + '</button>' +
            '<button class="btn-ghost" type="button" onclick="onboardingGoPage(\'generate\')">' + i18nText('onboarding.action_generate') + '</button>' +
          '</div>' +
        '</section>' +
        '<section class="glass-panel" style="padding:18px;border-radius:16px;">' +
          '<div class="text-sm font-bold mb-8">' + i18nText('onboarding.step_2_title') + '</div>' +
          '<p class="text-sm text-muted mb-12">' + i18nText('onboarding.step_2_desc') + '</p>' +
          '<div class="flex gap-8 flex-wrap">' +
            '<button class="btn-ghost" type="button" onclick="onboardingGoPage(\'gallery\')">' + i18nText('onboarding.action_gallery') + '</button>' +
            '<button class="btn-ghost" type="button" onclick="onboardingGoPage(\'history\')">' + i18nText('onboarding.action_history') + '</button>' +
          '</div>' +
        '</section>' +
        '<section class="glass-panel" style="padding:18px;border-radius:16px;">' +
          '<div class="text-sm font-bold mb-8">' + i18nText('onboarding.step_3_title') + '</div>' +
          '<p class="text-sm text-muted mb-12">' + i18nText('onboarding.step_3_desc') + '</p>' +
          '<div class="flex gap-8 flex-wrap">' +
            '<button class="btn-ghost" type="button" onclick="onboardingGoPage(\'extensions\')">' + i18nText('onboarding.action_extensions') + '</button>' +
            '<button class="btn-ghost" type="button" onclick="openSyncModal()">' + i18nText('onboarding.action_sync') + '</button>' +
          '</div>' +
        '</section>' +
      '</div>' +
      '<div class="glass-panel" style="padding:18px;border-radius:16px;margin-bottom:20px;">' +
        '<div class="flex items-start justify-between gap-12 flex-wrap mb-12">' +
          '<div>' +
            '<div class="text-sm font-bold mb-6">' + i18nText('onboarding.quick_setup_title') + '</div>' +
            '<p class="text-sm text-muted">' + i18nText('onboarding.quick_setup_desc') + '</p>' +
          '</div>' +
          '<button class="btn-ghost" type="button" onclick="onboardingOpenProviders()">' + i18nText('onboarding.manage_all') + '</button>' +
        '</div>' +
        '<div class="dash-grid" style="grid-template-columns:repeat(3,minmax(0,1fr));">' +
          '<div>' +
            '<h3 class="text-sm font-bold mb-10">' + i18nText('provider.image') + '</h3>' +
            '<div class="flex flex-col gap-8">' +
              '<div><label class="text-xs text-muted">GPT Image</label><input type="text" id="sw_gpt_url" placeholder="' + i18nText('setup.openai_default') + '" class="w-full text-xs p-8"><input type="password" id="sw_gpt_key" placeholder="API Key" class="w-full text-xs p-8 mt-4"></div>' +
              '<div><label class="text-xs text-muted">Gemini</label><input type="text" id="sw_gem_url" placeholder="URL" class="w-full text-xs p-8"><input type="password" id="sw_gem_key" placeholder="API Key" class="w-full text-xs p-8 mt-4"></div>' +
              '<div><label class="text-xs text-muted">Qwen</label><input type="text" id="sw_qwen_url" placeholder="URL" class="w-full text-xs p-8"><input type="password" id="sw_qwen_key" placeholder="API Key" class="w-full text-xs p-8 mt-4"></div>' +
            '</div>' +
          '</div>' +
          '<div>' +
            '<h3 class="text-sm font-bold mb-10">' + i18nText('provider.video') + '</h3>' +
            '<div class="flex flex-col gap-8">' +
              '<div><label class="text-xs text-muted">Agnes Video</label><input type="text" id="sw_agnes_v_url" placeholder="URL" class="w-full text-xs p-8"><input type="password" id="sw_agnes_v_key" placeholder="API Key" class="w-full text-xs p-8 mt-4"></div>' +
              '<div><label class="text-xs text-muted">Gemini Video</label><input type="text" id="sw_gem_v_url" placeholder="URL" class="w-full text-xs p-8"><input type="password" id="sw_gem_v_key" placeholder="API Key" class="w-full text-xs p-8 mt-4"></div>' +
              '<div><label class="text-xs text-muted">Qwen Video</label><input type="text" id="sw_qwen_v_url" placeholder="URL" class="w-full text-xs p-8"><input type="password" id="sw_qwen_v_key" placeholder="API Key" class="w-full text-xs p-8 mt-4"></div>' +
            '</div>' +
          '</div>' +
          '<div>' +
            '<h3 class="text-sm font-bold mb-10">' + i18nText('setup.llm_optional') + '</h3>' +
            '<div class="flex flex-col gap-8">' +
              '<div><label class="text-xs text-muted">LLM Provider</label><input type="text" id="sw_llm_url" placeholder="URL" class="w-full text-xs p-8"><input type="password" id="sw_llm_key" placeholder="API Key" class="w-full text-xs p-8 mt-4"></div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="flex gap-8 justify-between flex-wrap">' +
        '<button class="btn-ghost" onclick="closeSetupWizard()">' + i18nText('common.skip') + '</button>' +
        '<div class="flex gap-8 flex-wrap">' +
          '<button class="btn-secondary" type="button" onclick="onboardingGoPage(\'dashboard\')">' + i18nText('onboarding.action_dashboard') + '</button>' +
          '<button class="btn-primary" onclick="submitSetupWizard()">' + i18nText('setup.save') + '</button>' +
        '</div>' +
      '</div>' +
    '</div>';
}
function genboxLogoSvgMarkup(className) {
  return '<svg' + (className ? ' class="' + className + '"' : '') + ' viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3 27 9.5v13L16 29 5 22.5v-13Z"/><path d="m5 9.5 11 6.5 11-6.5M16 16v13"/><circle cx="16" cy="16" r="2.2"/></svg>';
}
function onboardingCapabilityGroupsMarkup() {
  var groups = [
    {titleKey:'onboarding.capability_image_title', descKey:'onboarding.capability_image_desc', tone:'ready'},
    {titleKey:'onboarding.capability_editing_title', descKey:'onboarding.capability_editing_desc', tone:'planned'},
    {titleKey:'onboarding.capability_video_title', descKey:'onboarding.capability_video_desc', tone:'ready'},
    {titleKey:'onboarding.capability_media_title', descKey:'onboarding.capability_media_desc', tone:'ready'},
    {titleKey:'onboarding.capability_prompt_title', descKey:'onboarding.capability_prompt_desc', tone:'ready'},
    {titleKey:'onboarding.capability_extensions_title', descKey:'onboarding.capability_extensions_desc', tone:'ready'}
  ];
  return groups.map(function(group){
    var badgeKey = group.tone === 'planned' ? 'onboarding.capability_planned' : 'onboarding.capability_ready';
    return '<article class="onboarding-capability-card onboarding-capability-' + group.tone + '"><div class="onboarding-capability-head"><strong>' + i18nText(group.titleKey) + '</strong><span>' + i18nText(badgeKey) + '</span></div><p>' + i18nText(group.descKey) + '</p></article>';
  }).join('');
}
function onboardingChecklistMarkup(keys) {
  return '<ul>' + keys.map(function(key){
    return '<li>' + i18nText(key) + '</li>';
  }).join('') + '</ul>';
}
function onboardingChatgptFeatureMarkup() {
  var features = [
    {titleKey:'onboarding.chatgpt_intro_api_title', descKey:'onboarding.chatgpt_intro_api_desc'},
    {titleKey:'onboarding.chatgpt_intro_studio_title', descKey:'onboarding.chatgpt_intro_studio_desc'},
    {titleKey:'onboarding.chatgpt_intro_ops_title', descKey:'onboarding.chatgpt_intro_ops_desc'},
    {titleKey:'onboarding.chatgpt_intro_host_title', descKey:'onboarding.chatgpt_intro_host_desc'}
  ];
  return features.map(function(feature){
    return '<article class="onboarding-chatgpt-feature"><strong>' + i18nText(feature.titleKey) + '</strong><p>' + i18nText(feature.descKey) + '</p></article>';
  }).join('');
}
function setupWizardMarkupV2() {
  var language = getUiLanguage();
  return '' +
    '<div class="onboarding-shell" role="dialog" aria-modal="true" aria-labelledby="onboardingTitle">' +
      '<header class="onboarding-header">' +
        '<div class="onboarding-brand">' + genboxLogoSvgMarkup('onboarding-brand-logo') + '<div><span>' + i18nText('onboarding.brand_kicker') + '</span><strong id="onboardingTitle">' + i18nText('onboarding.title') + '</strong></div></div>' +
        '<div class="onboarding-header-actions">' +
          '<label class="onboarding-language"><span>' + i18nText('language.select_label') + '</span><select onchange="setOnboardingLanguage(this.value)" aria-label="' + escAttr(i18nText('language.select_label')) + '"><option value="zh-CN"' + (language === 'zh-CN' ? ' selected' : '') + '>&#20013;&#25991;</option><option value="en"' + (language === 'en' ? ' selected' : '') + '>EN</option></select></label>' +
          '<button class="onboarding-close" type="button" onclick="closeSetupWizard()" aria-label="' + escAttr(i18nText('common.close')) + '">&times;</button>' +
        '</div>' +
      '</header>' +
      '<main class="onboarding-main">' +
        '<section class="onboarding-intro">' +
          '<div class="onboarding-intro-copy"><span class="onboarding-section-index">01 / ' + i18nText('nav.guide') + '</span><h2>' + i18nText('onboarding.title') + '</h2><p>' + i18nText('onboarding.subtitle') + '</p></div>' +
          '<div class="onboarding-steps">' +
            '<article><span>01</span><strong>' + i18nText('onboarding.step_1_title') + '</strong><p>' + i18nText('onboarding.step_1_desc') + '</p><button class="btn-primary" type="button" onclick="onboardingOpenProviders()">' + i18nText('onboarding.action_models') + '</button></article>' +
            '<article><span>02</span><strong>' + i18nText('onboarding.step_2_title') + '</strong><p>' + i18nText('onboarding.step_2_desc') + '</p><button class="btn-ghost" type="button" onclick="onboardingGoPage(\'gallery\')">' + i18nText('onboarding.action_gallery') + '</button></article>' +
            '<article><span>03</span><strong>' + i18nText('onboarding.step_3_title') + '</strong><p>' + i18nText('onboarding.step_3_desc') + '</p><button class="btn-ghost" type="button" onclick="onboardingGoPage(\'video\')">' + i18nText('nav.video') + '</button></article>' +
          '</div>' +
        '</section>' +
        '<section class="onboarding-capabilities">' +
          '<div class="onboarding-section-copy"><span class="onboarding-section-index">02 / CAPABILITIES</span><h3>' + i18nText('onboarding.capability_title') + '</h3><p>' + i18nText('onboarding.capability_desc') + '</p></div>' +
          '<div class="onboarding-capability-grid">' + onboardingCapabilityGroupsMarkup() + '</div>' +
          '<div class="onboarding-section-actions"><button class="btn-secondary" type="button" onclick="onboardingOpenProviders()">' + i18nText('onboarding.manage_all') + '</button><button class="btn-ghost" type="button" onclick="onboardingGoPage(\'dashboard\')">' + i18nText('onboarding.action_dashboard') + '</button></div>' +
        '</section>' +
        '<section class="onboarding-chatgpt-overview">' +
          '<div class="onboarding-section-copy"><span class="onboarding-section-index">03 / CHATGPT2API</span><h3>' + i18nText('onboarding.chatgpt_intro_title') + '</h3><p>' + i18nText('onboarding.chatgpt_intro_desc') + '</p></div>' +
          '<div class="onboarding-chatgpt-feature-grid">' + onboardingChatgptFeatureMarkup() + '</div>' +
          '<div class="onboarding-project-note"><span>' + i18nText('onboarding.chatgpt_intro_source') + '</span><a class="btn-ghost" href="https://github.com/yukkcat/chatgpt2api" target="_blank" rel="noopener noreferrer">' + i18nText('onboarding.chatgpt_intro_project') + '</a></div>' +
        '</section>' +
        '<section class="onboarding-chatgpt">' +
          '<div class="onboarding-chatgpt-copy"><span class="onboarding-section-index">04 / CONNECT TO GENBOX</span><h3>' + i18nText('onboarding.chat_title') + '</h3><p>' + i18nText('onboarding.chat_desc') + '</p><small>' + i18nText('onboarding.chat_meta') + '</small><div class="onboarding-chatgpt-actions"><button class="btn-primary" type="button" onclick="onboardingGoPage(\'extensions\')">' + i18nText('onboarding.action_extensions') + '</button></div></div>' +
          '<div class="onboarding-chatgpt-grid">' +
            '<article class="onboarding-chat-card"><span>' + i18nText('onboarding.chat_available_label') + '</span><strong>' + i18nText('onboarding.chat_available_title') + '</strong>' + onboardingChecklistMarkup(['onboarding.chat_available_1','onboarding.chat_available_2','onboarding.chat_available_3','onboarding.chat_available_4','onboarding.chat_available_5']) + '</article>' +
            '<article class="onboarding-chat-card onboarding-chat-card-planned"><span>' + i18nText('onboarding.chat_planned_label') + '</span><strong>' + i18nText('onboarding.chat_planned_title') + '</strong>' + onboardingChecklistMarkup(['onboarding.chat_planned_1','onboarding.chat_planned_2','onboarding.chat_planned_3','onboarding.chat_planned_4']) + '</article>' +
          '</div>' +
        '</section>' +
      '</main>' +
      '<footer class="onboarding-footer"><button class="btn-ghost" type="button" onclick="finishOnboardingTour()">' + i18nText('common.skip') + '</button><span>' + i18nText('onboarding.footer_hint') + '</span><button class="btn-primary" type="button" onclick="finishOnboardingTour()">' + i18nText('onboarding.finish') + '</button></footer>' +
    '</div>';
}
function renderSetupWizardGuide() {
  var wizard = document.getElementById('setupWizard');
  if (!wizard) return;
  wizard.innerHTML = setupWizardMarkupV2();
}
function openOnboardingGuide() {
  renderSetupWizardGuide();
  var wizard = document.getElementById('setupWizard');
  if (!wizard) return;
  wizard.style.display = 'flex';
  wizard.classList.add('show');
  setTimeout(function(){
    var firstAction = wizard.querySelector('button');
    if (firstAction) firstAction.focus();
  }, 0);
}
function onboardingGoPage(page) {
  closeSetupWizard();
  if (typeof switchNav === 'function') switchNav(page);
}
function setOnboardingLanguage(language) {
  try { sessionStorage.setItem('igs_reopen_onboarding', '1'); } catch (error) {}
  setUiLanguage(language);
}
function onboardingOpenProviders() {
  closeSetupWizard();
  if (typeof switchNav === 'function') switchNav('generate');
  setTimeout(function(){
    if (typeof openProviderModal === 'function') openProviderModal();
  }, 120);
}
var onboardingTourIndex = -1;
var onboardingTourSteps = [
  {selector:'#navDashboard,.dock-item[data-page="dashboard"]',title:'tour.dashboard_title',desc:'tour.dashboard_desc'},
  {selector:'#navGen,.dock-item[data-page="generate"]',title:'tour.images_title',desc:'tour.images_desc'},
  {selector:'#navVideo,.dock-item[data-page="video"]',title:'tour.video_title',desc:'tour.video_desc'},
  {selector:'#navGallery,.dock-item[data-page="gallery"]',title:'tour.library_title',desc:'tour.library_desc'},
  {selector:'#navExtensions,.dock-item[data-page="extensions"]',title:'tour.extensions_title',desc:'tour.extensions_desc'}
];
function finishOnboardingTour() {
  closeSetupWizard();
  startOnboardingTour();
}
function startOnboardingTour() {
  closeOnboardingTour();
  onboardingTourIndex = 0;
  var panel = document.createElement('aside');
  panel.id = 'onboardingTour';
  panel.className = 'onboarding-tour';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-live', 'polite');
  document.body.appendChild(panel);
  renderOnboardingTourStep();
}
function onboardingTourTarget(selector) {
  var nodes = document.querySelectorAll(selector);
  for (var i = 0; i < nodes.length; i++) {
    if (nodes[i].offsetParent !== null) return nodes[i];
  }
  return nodes[0] || null;
}
function renderOnboardingTourStep() {
  var panel = document.getElementById('onboardingTour');
  var step = onboardingTourSteps[onboardingTourIndex];
  if (!panel || !step) return closeOnboardingTour();
  document.querySelectorAll('.onboarding-tour-highlight').forEach(function(node){node.classList.remove('onboarding-tour-highlight');});
  var target = onboardingTourTarget(step.selector);
  if (target) target.classList.add('onboarding-tour-highlight');
  panel.innerHTML = '<div class="onboarding-tour-count">' + (onboardingTourIndex + 1) + ' / ' + onboardingTourSteps.length + '</div><strong>' + i18nText(step.title) + '</strong><p>' + i18nText(step.desc) + '</p><div><button class="btn-ghost" type="button" onclick="closeOnboardingTour()">' + i18nText('common.skip') + '</button><button class="btn-primary" type="button" onclick="onboardingTourNext()">' + (onboardingTourIndex === onboardingTourSteps.length - 1 ? i18nText('common.done') : i18nText('common.next')) + '</button></div>';
}
function onboardingTourNext() {
  onboardingTourIndex += 1;
  renderOnboardingTourStep();
}
function closeOnboardingTour() {
  document.querySelectorAll('.onboarding-tour-highlight').forEach(function(node){node.classList.remove('onboarding-tour-highlight');});
  var panel = document.getElementById('onboardingTour');
  if (panel) panel.remove();
  onboardingTourIndex = -1;
}
function confirmWelcome() {
  document.getElementById('welcomePage').style.display = 'none';
  openOnboardingGuide();
}

// ══ 首次设置向导 ══
function checkSetupWizard(attempt) {
  var effectiveAttempt = _captureLoginAttempt(attempt);
  return fetch('/api/setup/status').then(function(r){
    if (!_isCurrentLoginAttempt(effectiveAttempt)) return null;
    if (!r.ok) throw new Error('SETUP_STATUS_UNAVAILABLE');
    return r.json();
  }).then(function(d){
    if (!_isCurrentLoginAttempt(effectiveAttempt)) return;
    if (!d || typeof d.auth_required !== 'boolean') {
      throw new Error('SETUP_STATUS_INVALID');
    }
    if (d.auth_required === false) {
      _adminKey = '';
      _hideLogin();
      if (d.needs_provider_setup === true) openOnboardingGuide();
      return;
    }
    if (!_adminKey) {
      _showLogin();
      return;
    }
    return _authFetch('/api/providers').then(function(r) {
      if (!_isCurrentLoginAttempt(effectiveAttempt)) return;
      if (!r.ok) {
        _adminKey = '';
        throw new Error('AUTH_CHECK_FAILED');
      }
      if (d.needs_provider_setup === true) {
        openOnboardingGuide();
      }
    });
  }).catch(function(){
    if (_isCurrentLoginAttempt(effectiveAttempt) && (typeof _backendOnline === 'undefined' || _backendOnline !== false)) _showLogin();
  });
}
function closeSetupWizard() {
  var wizard = document.getElementById('setupWizard');
  wizard.style.display = 'none';
  wizard.classList.remove('show');
}
function submitSetupWizard() {
  var saves = [];
  // 生图
  var gptUrl = document.getElementById('sw_gpt_url').value.trim();
  var gptKey = document.getElementById('sw_gpt_key').value.trim();
  var gemUrl = document.getElementById('sw_gem_url').value.trim();
  var gemKey = document.getElementById('sw_gem_key').value.trim();
  var qwenUrl = document.getElementById('sw_qwen_url').value.trim();
  var qwenKey = document.getElementById('sw_qwen_key').value.trim();
  // 生视频
  var agnesVUrl = document.getElementById('sw_agnes_v_url').value.trim();
  var agnesVKey = document.getElementById('sw_agnes_v_key').value.trim();
  var gemVUrl = document.getElementById('sw_gem_v_url').value.trim();
  var gemVKey = document.getElementById('sw_gem_v_key').value.trim();
  var qwenVUrl = document.getElementById('sw_qwen_v_url').value.trim();
  var qwenVKey = document.getElementById('sw_qwen_v_key').value.trim();
  // LLM
  var llmUrl = document.getElementById('sw_llm_url').value.trim();
  var llmKey = document.getElementById('sw_llm_key').value.trim();

  if (gptKey) saves.push(saveWizardProvider('gpt-image', 'GPT Image 2', 'image', gptUrl || 'https://api.openai.com/v1', gptKey, '#22c55e'));
  if (gemKey) saves.push(saveWizardProvider('gemini', 'Gemini 3.1 Flash', 'image', gemUrl || '', gemKey, '#3b82f6'));
  if (qwenKey) saves.push(saveWizardProvider('qwen', 'Qwen2API', 'image', qwenUrl || '', qwenKey, '#f97316'));
  if (agnesVKey) saves.push(saveWizardProvider('agnes-video', 'Agnes Video', 'video', agnesVUrl || 'https://apihub.agnes-ai.com/v1', agnesVKey, '#ec4899'));
  if (gemVKey) saves.push(saveWizardProvider('gemini-video', 'Gemini Video', 'video', gemVUrl || '', gemVKey, '#6366f1'));
  if (qwenVKey) saves.push(saveWizardProvider('qwen-video', 'Qwen Video', 'video', qwenVUrl || '', qwenVKey, '#f97316'));
  if (llmKey) saves.push(saveWizardProvider('llm-default', i18nText('creator.prompt_optimization'), 'llm', llmUrl || '', llmKey, '#a855f7'));

  if (!saves.length) { alert('\u8BF7\u81F3\u5C11\u586B\u5199\u4E00\u4E2A API Key'); return; }
  Promise.all(saves).then(function(){
    closeSetupWizard();
    loadProviders();
    setStatus('\u2705 \u914D\u7F6E\u5B8C\u6210\uFF0C\u53EF\u4EE5\u5F00\u59CB\u751F\u56FE\u4E86!');
  });
}
function saveWizardProvider(pid, pname, ptype, url, key, color) {
  return _authFetch('/api/providers').then(function(r){ return r.json(); }).then(function(data){
    var providers = data.providers || [];
    var existing = null;
    for (var i = 0; i < providers.length; i++) {
      if (providers[i].id === pid) { existing = providers[i]; break; }
    }
    var p = existing || { id: pid, name: pname, type: ptype, models: [], color: color };
    p.base_url = url;
    p.api_key = key;
    p.enabled = true;
    return _authFetch('/api/providers', {
      method: 'POST',
      body: JSON.stringify(p)
    });
  });
}

// ══ 添加 Provider 类型选择 ══
function openAddProviderTypeModal() {
  document.getElementById('addProviderTypeModal').style.display = 'flex';
}
function closeAddProviderTypeModal() {
  document.getElementById('addProviderTypeModal').style.display = 'none';
}
function addProviderWithType(type) {
  closeAddProviderTypeModal();
  var defaults = {
    image: { id:'', name:'新生图 Provider', type:'image', api_key:'', api_keys:[], base_url:'', model:'', models:[], color:'#22c55e', enabled:true },
    video: { id:'', name:'新生视频 Provider', type:'video', api_key:'', api_keys:[], base_url:'', model:'', models:[], color:'#3b82f6', enabled:true },
    llm:   { id:'', name:'新 LLM Provider', type:'llm', api_key:'', api_keys:[], base_url:'', model:'', models:[], color:'#a855f7', enabled:true }
  };
  allProviders.push(defaults[type] || defaults.image);
  providerEditOpenIdx = allProviders.length - 1;
  renderProviderEdit();
}

var providerEditOpenIdx = -1;

function toggleProviderEdit(idx) {
  providerEditOpenIdx = providerEditOpenIdx === idx ? -1 : idx;
  renderProviderEdit();
}

function renderProviderEdit() {
  var body = document.getElementById('providerEditBody');
  var html = '';
  var providerEditOpenIdx = (typeof window.providerEditOpenIdx === 'number') ? window.providerEditOpenIdx : -1;

  // ── 代理设置区 ──
  html += '<div id="proxySection" style="margin-bottom:14px;padding:12px;border-radius:10px;border:1px solid var(--border);background:var(--bg-surface);">';
  html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">';
  html += '<div style="display:flex;align-items:center;gap:6px;">';
  html += '<span style="font-size:13px;">🌐</span>';
  html += '<span style="font-size:12px;font-weight:700;color:var(--text-primary);">网络代理</span>';
  html += '<span id="proxyStatusBadge" style="font-size:9px;padding:2px 6px;border-radius:8px;background:#6b728022;color:#6b7280;font-weight:600;">未配置</span>';
  html += '</div>';
  html += '<span style="font-size:10px;color:var(--text-muted);">用于连接国外模型厂商（OpenAI、Gemini 等）</span>';
  html += '</div>';
  html += '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">';
  html += '<label style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-secondary);cursor:pointer;">';
  html += '<input type="checkbox" id="proxyEnabled" style="accent-color:var(--accent);width:14px;height:14px;"> ' + i18nText('proxy.enable');
  html += '</label>';
  html += '<select id="proxyType" style="padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<option value="http">HTTP</option>';
  html += '<option value="socks5">SOCKS5</option>';
  html += '</select>';
  html += '<input type="text" id="proxyHost" placeholder="' + i18nText('proxy.host_placeholder') + '" style="width:120px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);" value="127.0.0.1">';
  html += '<input type="number" id="proxyPort" placeholder="' + i18nText('proxy.port_placeholder') + '" style="width:70px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);" value="10808">';
  html += '<input type="text" id="proxyUser" placeholder="' + i18nText('proxy.user_placeholder') + '" style="width:100px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<input type="password" id="proxyPass" placeholder="' + i18nText('proxy.pass_placeholder') + '" style="width:100px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<button onclick="saveProxyConfig()" style="padding:5px 12px;font-size:11px;border-radius:6px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;">保存</button>';
  html += '<button onclick="testProxyConfig()" id="proxyTestBtn" style="padding:5px 12px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">测试连接</button>';
  html += '</div>';
  html += '<div id="proxyTestResult" style="font-size:10px;margin-top:6px;"></div>';
  html += '</div>';

  // 加载代理配置
  _loadProxyConfig();

  // ── 系统更新区 ──
  html += '<div id="updateSection" style="margin-bottom:14px;padding:12px;border-radius:10px;border:1px solid var(--border);background:var(--bg-surface);">';
  html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">';
  html += '<div style="display:flex;align-items:center;gap:6px;">';
  html += '<span style="font-size:13px;">📦</span>';
  html += '<span style="font-size:12px;font-weight:700;color:var(--text-primary);">系统更新</span>';
  html += '<span id="updateStatusBadge" style="font-size:9px;padding:2px 6px;border-radius:8px;background:#6b728022;color:#6b7280;font-weight:600;">检测中...</span>';
  html += '</div>';
  html += '<span id="updatePlatformInfo" style="font-size:10px;color:var(--text-muted);"></span>';
  html += '</div>';
  html += '<label style="display:flex;align-items:center;gap:6px;margin-bottom:8px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
    '<input type="checkbox" id="updateCheckToggle" ' + (localStorage.getItem('genbox_update_check') !== 'off' ? 'checked' : '') + ' onchange="toggleUpdateCheck(this)" style="accent-color:var(--accent);width:13px;height:13px;"> 启动时自动检查更新</label>';
  html += '<div id="updateContent" style="font-size:11px;color:var(--text-muted);">正在检查更新...</div>';
  html += '</div>';

  // 加载更新信息
  _loadUpdateInfo();

  var groups = [
    { type: 'image', icon: '🎨', title: i18nText('provider.image'), hint: i18nText('provider.group_image_hint'), accent: '#22c55e' },
    { type: 'video', icon: '🎬', title: i18nText('provider.video'), hint: i18nText('provider.group_video_hint'), accent: '#3b82f6' },
    { type: 'llm', icon: '🤖', title: i18nText('creator.prompt_optimization'), hint: i18nText('provider.group_llm_hint'), accent: '#f59e0b' }
  ];

  html += '<div id="providerGrid" style="display:flex;gap:14px;min-height:420px;">';

  groups.forEach(function(group, gi) {
    var provsInGroup = allProviders.filter(function(p){ return p.type === group.type; });

    html += '<div class="provider-type-card" data-group="' + group.type + '" style="flex:1;min-width:260px;display:flex;flex-direction:column;border:1px solid var(--border);border-radius:12px;background:var(--bg-surface);overflow:hidden;position:relative;">' +
      '<div class="provider-col-resize" onmousedown="startProviderColResize(event,' + gi + ')" style="position:absolute;right:-4px;top:10px;bottom:10px;width:8px;cursor:ew-resize;z-index:5;"></div>' +
      '<div class="provider-col-resize" onmousedown="startProviderColResize(event,' + gi + ')" style="position:absolute;left:-4px;top:10px;bottom:10px;width:8px;cursor:ew-resize;z-index:5;"></div>' +
      // 卡片头部
      '<div style="padding:14px 16px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,' + group.accent + '08,transparent);display:flex;align-items:center;justify-content:space-between;">' +
        '<div style="display:flex;align-items:center;gap:8px;">' +
          '<span style="font-size:16px;">' + group.icon + '</span>' +
          '<span style="font-size:14px;font-weight:700;color:var(--text-primary);font-family:-apple-system,BlinkMacSystemFont,\'SF Pro Display\',system-ui,sans-serif;">' + group.title + '</span>' +
          '<span style="font-size:10px;padding:2px 8px;border-radius:10px;background:' + group.accent + '18;color:' + group.accent + ';font-weight:600;">' + provsInGroup.length + '</span>' +
        '</div>' +
        '<div style="font-size:10px;color:var(--text-muted);text-align:right;line-height:1.3;max-width:200px;" title="' + group.hint + '">' + group.hint + '</div>' +
      '</div>' +
      // Provider 列表（可滚动）
      '<div style="flex:1;overflow-y:auto;padding:8px;">';

    if (provsInGroup.length === 0) {
      html += '<div style="text-align:center;padding:30px 10px;color:var(--text-muted);font-size:12px;">' +
        '<div style="font-size:24px;margin-bottom:8px;">' + group.icon + '</div>' +
        '暂无' + group.title + '<br><span style="font-size:11px;color:var(--text-muted);">点击下方添加</span>' +
      '</div>';
    }

    provsInGroup.forEach(function(p) {
      var idx = allProviders.indexOf(p);
      var isOpen = providerEditOpenIdx === idx;
      var et = p.endpoint_type || 'auto';
      var modelOpts = '';
      if (p.models && p.models.length) {
        var filteredModels = filterModelsByType(p.models, p.type);
        var groupFn = p.type === 'video' ? groupVideoModels : (p.type === 'image' ? groupImageModels : null);
        modelOpts = (groupFn && filteredModels.length > 3)
          ? buildModelOptsGrouped(filteredModels, p.model || '', groupFn)
          : filteredModels.map(function(m){ return '<option value="' + escAttr(m) + '"' + (p.model===m?' selected':'') + '>' + escHtml(m) + '</option>'; }).join('');
        if (filteredModels.length === 0 && p.models.length > 0) {
          modelOpts = '<option value="" disabled>' + i18nText('provider.type_model_none') + ' (' + p.models.length + ')</option>';
        }
      } else {
        modelOpts = '<option value="" disabled>' + i18nText('provider.load_models_first') + '</option>';
        if (p.model) modelOpts = '<option value="' + escAttr(p.model) + '" selected>' + escHtml(p.model) + ' (' + i18nText('provider.manual_model_suffix') + ')</option>' + modelOpts;
      }
      var keyVal = '';
      var keyPlaceholder = p.has_key ? i18nText('provider.masked_configured') : i18nText('provider.api_key_placeholder');
      var statusColor = p.enabled ? '#22c55e' : '#6b7280';
      var statusTitle = p.enabled ? i18nText('dashboard.enabled') : i18nText('dashboard.disabled');

      // 单个 Provider 卡片
      html += '<div style="margin-bottom:8px;border:1px solid ' + (isOpen ? group.accent : 'var(--border)') + ';border-radius:8px;background:var(--bg-card);overflow:hidden;transition:border-color 0.2s;">' +
        // 摘要行（始终显示，点击展开）
        '<div style="display:flex;align-items:center;padding:10px 12px;cursor:pointer;gap:8px;" onclick="toggleProviderEdit(' + idx + ')">' +
          '<input type="color" class="color-dot" value="' + (p.color||'#5b8def') + '" id="color_' + idx + '" onclick="event.stopPropagation();" style="width:22px;height:22px;border-radius:6px;border:none;cursor:pointer;flex-shrink:0;">' +
          '<div style="flex:1;min-width:0;">' +
            '<div style="display:flex;align-items:center;gap:6px;">' +
              '<span style="font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(p.name) + '</span>' +
              '<span style="width:5px;height:5px;border-radius:50%;background:' + statusColor + ';flex-shrink:0;" title="' + statusTitle + '"></span>' +
              (p.key_count > 1 ? '<span style="font-size:9px;padding:1px 5px;border-radius:6px;background:#3b82f622;color:#3b82f6;font-weight:600;flex-shrink:0;" title="' + p.key_count + ' ' + i18nText('provider.api_key_rotation') + '">🔑×' + p.key_count + '</span>' : '') +
            '</div>' +
            '<div style="font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
              escHtml(p.model || i18nText('common.not_entered')) + (p.base_url ? ' · ' + escHtml(p.base_url.replace(/^https?:\/\//, '').substring(0, 30)) : '') +
            '</div>' +
          '</div>' +
          '<div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">' +
            '<button onclick="event.stopPropagation();testProvider(\'' + p.id + '\')" style="font-size:9px;padding:3px 8px;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-secondary);cursor:pointer;white-space:nowrap;">' + i18nText('common.test') + '</button>' +
            '<button onclick="event.stopPropagation();deleteProvider(\'' + p.id + '\')" style="font-size:9px;padding:3px 8px;border-radius:4px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;white-space:nowrap;">' + i18nText('common.delete') + '</button>' +
            '<span style="font-size:10px;color:var(--text-muted);transition:transform 0.2s;display:inline-block;transform:rotate(' + (isOpen ? '90' : '0') + 'deg);">▶</span>' +
          '</div>' +
        '</div>';

      // 展开的编辑区
      if (isOpen) {
        html += '<div style="padding:0 12px 12px;border-top:1px solid var(--border);">' +
          '<div style="padding-top:10px;">' +
            // 名称 + 类型
            '<div style="display:flex;gap:6px;margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="' + i18nText('provider.display_name_placeholder') + '" value="' + escHtml(p.name) + '" id="name_' + idx + '">' +
              '<select class="modal-input" style="width:88px;padding:6px 8px;font-size:11px;" id="type_' + idx + '" onchange="updateCapsSection(' + idx + ')">' +
                '<option value="image" ' + (p.type==='image'?'selected':'') + '>' + i18nText('provider.type_image') + '</option>' +
                '<option value="video" ' + (p.type==='video'?'selected':'') + '>' + i18nText('provider.type_video') + '</option>' +
                '<option value="llm" ' + (p.type==='llm'?'selected':'') + '>' + i18nText('provider.type_llm') + '</option>' +
              '</select>' +
            '</div>' +
            // 端点协议类型
            '<div style="margin-bottom:8px;">' +
              '<div style="font-size:10px;color:var(--text-muted);margin-bottom:3px;">' + i18nText('provider.endpoint_type_hint') + '</div>' +
              '<select class="modal-input" style="width:100%;padding:6px 8px;font-size:11px;box-sizing:border-box;" id="endpoint_type_' + idx + '">' +
                '<option value="auto" ' + (et==='auto'?'selected':'') + '>' + i18nText('provider.endpoint_auto') + '</option>' +
                '<option value="openai" ' + (et==='openai'?'selected':'') + '>' + i18nText('provider.endpoint_openai') + '</option>' +
                '<option value="gemini" ' + (et==='gemini'?'selected':'') + '>' + i18nText('provider.endpoint_gemini') + '</option>' +
                '<option value="qwen" ' + (et==='qwen'?'selected':'') + '>' + i18nText('provider.endpoint_qwen') + '</option>' +
                '<option value="agnes" ' + (et==='agnes'?'selected':'') + '>' + i18nText('provider.endpoint_agnes') + '</option>' +
                '<option value="volc_ark_plan" ' + (et==='volc_ark_plan'?'selected':'') + '>' + i18nText('provider.endpoint_volc_plan') + '</option>' +
                '<option value="volc_ark" ' + (et==='volc_ark'?'selected':'') + '>' + i18nText('provider.endpoint_volc_ark') + '</option>' +
              '</select>' +
              (et==='volc_ark_plan' && p.type==='video' ?
                '<div style="font-size:9px;color:#f59e0b;margin-top:3px;">' + i18nText('provider.video_plan_warning') + '</div>' : '') +
            '</div>' +
            // 看板显示名
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">' +
              '<span style="font-size:10px;color:var(--text-muted);white-space:nowrap;">' + i18nText('provider.board_name') + '</span>' +
              '<input type="text" class="modal-input" style="flex:1;padding:5px 8px;font-size:11px;" placeholder="' + i18nText('provider.board_name_placeholder') + '" value="' + escHtml(p.display_name || '') + '" id="display_name_' + idx + '">' +
            '</div>' +
            // Provider ID
            '<div style="margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="width:100%;padding:6px 10px;font-size:11px;box-sizing:border-box;" placeholder="' + i18nText('provider.id_placeholder') + '" value="' + escHtml(p.id) + '" id="id_' + idx + '" ' + (p.id?'readonly style="padding:6px 10px;font-size:11px;background:var(--bg-surface);box-sizing:border-box;"':'') + '>' +
            '</div>' +
            // URL + API Key
            '<div style="display:flex;gap:6px;margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="' + i18nText('provider.base_url') + '" value="' + escHtml(p.base_url) + '" id="url_' + idx + '">' +
              '<input type="password" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="' + keyPlaceholder + '" value="' + escHtml(keyVal) + '" id="key_' + idx + '">' +
            '</div>' +
            // 多账号轮询（api_keys）
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">' + i18nText('provider.multi_key_hint') + '</span>' +
                (p.keypool ? '<span style="font-size:9px;padding:2px 6px;border-radius:8px;background:' + (p.keypool.available_keys > 0 ? '#22c55e22;color:#22c55e' : '#ef444422;color:#ef4444') + ';font-weight:600;">' + p.keypool.available_keys + '/' + p.keypool.total_keys + ' ' + i18nText('provider.available') + '</span>' : '') +
              '</div>' +
              '<textarea class="modal-input" id="keys_' + idx + '" rows="3" style="width:100%;padding:6px 10px;font-size:10px;font-family:monospace;resize:vertical;box-sizing:border-box;" placeholder="' + i18nText('provider.multi_key_placeholder_html') + '">' + escHtml((p.api_keys || []).join('\n')) + '</textarea>' +
              (p.keypool && p.keypool.keys ? '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">' + p.keypool.keys.map(function(k,i){ return '<span style="font-size:9px;padding:2px 6px;border-radius:6px;border:1px solid ' + (k.available ? '#22c55e44' : '#ef444444') + ';background:' + (k.available ? '#22c55e11' : '#ef444411') + ';color:' + (k.available ? '#22c55e' : '#ef4444') + ';" title="' + i18nText('provider.fail_count_prefix') + k.fail_count + ' ' + i18nText('provider.success_count_prefix') + k.total_calls + '">' + (k.available ? '🟢' : '🔴') + ' ' + escHtml(k.key) + (k.cooldown_remaining > 0 ? ' ⏳' + Math.ceil(k.cooldown_remaining) + 's' : '') + '</span>'; }).join('') + '</div>' : '') +
            '</div>' +
            // 多端点（endpoints）
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">' + i18nText('provider.endpoint_pool') + '</span>' +
                '<span id="epCount_' + idx + '" style="font-size:9px;color:var(--text-muted);">' + (p.endpoints ? p.endpoints.length : 0) + ' ' + i18nText('provider.endpoint_count_unit') + '</span>' +
              '</div>' +
              '<div id="epList_' + idx + '" style="display:flex;flex-direction:column;gap:6px;">' +
                (p.endpoints || []).map(function(ep, ei) {
                  return '<div class="ep-item" style="border-radius:8px;border:1px solid var(--border);background:var(--bg-base);padding:8px 10px;">' +
                    // Row 1: Name + controls
                    '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">' +
                      '<span style="font-size:9px;color:var(--text-muted);flex-shrink:0;">#' + (ei+1) + '</span>' +
                      '<input type="text" placeholder="' + i18nText('provider.endpoint_name_placeholder') + '" value="' + escAttr(ep.name || '') + '" data-ep-idx="' + ei + '" data-field="name" style="flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-weight:500;">' +
                      '<label style="display:flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);cursor:pointer;flex-shrink:0;" title="' + i18nText('provider.endpoint_toggle_title') + '">' +
                        '<input type="checkbox" ' + (ep.enabled !== false ? 'checked' : '') + ' data-ep-idx="' + ei + '" data-field="enabled" style="accent-color:#22c55e;width:13px;height:13px;">' +
                        '<span>' + i18nText('dashboard.enabled') + '</span>' +
                      '</label>' +
                      '<button onclick="removeEndpoint(' + idx + ',' + ei + ')" title="' + i18nText('provider.endpoint_remove_title') + '" style="font-size:10px;padding:3px 7px;border-radius:5px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;flex-shrink:0;">✕</button>' +
                    '</div>' +
                    // Row 2: URL + Key
                    '<div style="display:flex;gap:6px;">' +
                      '<input type="text" placeholder="' + i18nText('provider.endpoint_url_placeholder') + '" value="' + escAttr(ep.url || '') + '" data-ep-idx="' + ei + '" data-field="url" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
                      '<input type="password" placeholder="' + i18nText('provider.api_key') + '" value="' + escAttr(ep.key || '') + '" data-ep-idx="' + ei + '" data-field="key" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
                    '</div>' +
                  '</div>';
                }).join('') +
              '</div>' +
              '<button onclick="addEndpoint(' + idx + ')" style="margin-top:6px;font-size:10px;padding:4px 10px;border-radius:6px;border:1px dashed var(--border);background:transparent;color:var(--accent);cursor:pointer;display:flex;align-items:center;gap:4px;">' + i18nText('provider.add_endpoint') + '</button>' +
            '</div>' +
            // 模型选择
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;gap:6px;align-items:center;margin-bottom:3px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">' + i18nText('provider.default_model') + '</span>' +
                '<span style="font-size:9px;color:var(--accent);">' + i18nText('provider.fetch_from_upstream') + '</span>' +
                (p.models && p.models.length ? '<span style="font-size:9px;color:var(--text-muted);">(' + filterModelsByType(p.models, p.type).length + '/' + p.models.length + ' ' + i18nText('provider.match_count_suffix') + ' ' + p.type + ')</span>' : '') +
              '</div>' +
              '<div style="display:flex;gap:6px;">' +
                '<select class="modal-input" style="flex:1;padding:6px 8px;font-size:11px;" id="model_' + idx + '">' + modelOpts + '</select>' +
                '<button class="btn-secondary" onclick="fetchModels(' + idx + ')" id="fetchBtn_' + idx + '" style="flex-shrink:0;padding:6px 10px;font-size:10px;">' + i18nText('provider.fetch_models') + '</button>' +
              '</div>' +
              '<div id="fetchStatus_' + idx + '" style="font-size:10px;color:var(--text-muted);margin-top:2px;"></div>' +
            '</div>' +
            // 能力声明（根据类型显示不同选项）
            '<div id="capsSection_' + idx + '" style="margin-bottom:8px;">' +
              (p.type === 'llm' ? '' :
                '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">' + i18nText('provider.capability_hint') + '</div>' +
                '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
                  (p.type === 'image' ?
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="t2i" ' + ((p.capabilities && p.capabilities.t2i !== false) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('history.t2i') +
                    '</label>' +
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="i2i" ' + ((p.capabilities && p.capabilities.i2i) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('history.i2i') +
                    '</label>' +
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="inpaint_mask" ' + ((p.capabilities && p.capabilities.inpaint_mask) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> 局部重绘/遮罩' +
                    '</label>' +
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="precision_edit" ' + ((p.capabilities && p.capabilities.precision_edit) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> 精准改图' +
                    '</label>'
                  :
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="t2v" ' + ((p.capabilities && p.capabilities.t2v) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('video.t2v') +
                    '</label>' +
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="i2v" ' + ((p.capabilities && p.capabilities.i2v) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('video.i2v') +
                    '</label>'
                  ) +
                '</div>' +
                '<div style="font-size:9px;color:var(--text-muted);margin-top:3px;">留空则自动根据模型名称和协议推断</div>'
              ) +
            '</div>' +
            // 跳过代理
            '<div style="margin-bottom:8px;">' +
              '<label style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                '<input type="checkbox" id="skip_proxy_' + idx + '" ' + (p.skip_proxy ? 'checked' : '') + ' style="accent-color:var(--accent);width:14px;height:14px;"> 🌐 跳过全局代理（直连，不走代理服务器）' +
              '</label>' +
              '<div style="font-size:9px;color:var(--text-muted);margin-top:2px;">适用于可直连的 API（如国内服务商），不受全局代理影响</div>' +
            '</div>' +
            // 启用 + 按钮
            '<div style="display:flex;align-items:center;justify-content:space-between;">' +
              '<label style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                '<input type="checkbox" id="en_' + idx + '" ' + (p.enabled?'checked':'') + ' style="accent-color:var(--accent);width:14px;height:14px;"> 启用' +
              '</label>' +
              '<div style="display:flex;gap:6px;">' +
                '<button class="btn-primary" onclick="saveProvider(' + idx + ')" style="padding:5px 14px;font-size:11px;">保存</button>' +
                '<button class="btn-secondary" onclick="testProvider(\'' + p.id + '\')" style="padding:5px 10px;font-size:11px;">测试</button>' +
                '<button class="btn-ghost" onclick="deleteProvider(\'' + p.id + '\')" style="color:#f87171;border-color:#f8717133;padding:5px 10px;font-size:11px;">删除</button>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>';
      }

      html += '</div>';
    });

    html += '</div></div>';
  });

  html += '</div>';

  body.innerHTML = html || '<div style="color:var(--text-muted);text-align:center;padding:40px;font-size:13px;">' + i18nText('provider.empty_hint') + '</div>';
  try {
    var proxyHint = body.querySelector('#proxySection span[style*="font-size:10px"]');
    if (proxyHint) proxyHint.textContent = i18nText('proxy.hint');
    var proxyTitle = body.querySelector('#proxySection div > div > span:nth-child(2)');
    if (proxyTitle) proxyTitle.textContent = i18nText('proxy.title');
    var proxyBadge = body.querySelector('#proxyStatusBadge');
    if (proxyBadge && (proxyBadge.textContent || '').trim() === '未配置') proxyBadge.textContent = i18nText('common.not_configured');
    body.querySelectorAll('button[onclick="saveProxyConfig()"]').forEach(function(btn){ btn.textContent = i18nText('common.save'); });
    body.querySelectorAll('button[onclick="testProxyConfig()"]').forEach(function(btn){ btn.textContent = i18nText('extensions.test_connection'); });
    var updateSection = body.querySelector('#updateSection');
    if (updateSection) {
      var updateTitle = updateSection.querySelector('div > div > span:nth-child(2)');
      if (updateTitle) updateTitle.textContent = i18nText('update.status');
      var updateBadge = updateSection.querySelector('#updateStatusBadge');
      if (updateBadge) updateBadge.textContent = i18nText('update.checking_progress');
      var updateLabel = updateSection.querySelector('label');
      if (updateLabel) {
        var updateToggle = updateLabel.querySelector('#updateCheckToggle');
        updateLabel.textContent = ' ' + i18nText('update.auto_check');
        if (updateToggle) updateLabel.prepend(updateToggle);
      }
      var updateContent = updateSection.querySelector('#updateContent');
      if (updateContent) updateContent.textContent = i18nText('update.checking_progress');
    }
    body.querySelectorAll('input[id^="en_"]').forEach(function(input){
      var label = input.parentNode;
      if (!label) return;
      label.textContent = ' ' + i18nText('dashboard.enabled');
      label.prepend(input);
    });
    body.querySelectorAll('button[onclick^="saveProvider("]').forEach(function(btn){ btn.textContent = i18nText('common.save'); });
    body.querySelectorAll('button[onclick^="testProvider("]').forEach(function(btn){ btn.textContent = i18nText('common.test'); });
    body.querySelectorAll('button[onclick^="deleteProvider("]').forEach(function(btn){ btn.textContent = i18nText('common.delete'); });
  } catch (e) {}
}

function saveProvider(idx) {
  var pid = document.getElementById('id_' + idx).value || '';
  // 优先从 localStorage 缓存获取拉取的完整模型列表
  var currentModels = [];
  try {
    var cached = localStorage.getItem('igs_models_' + pid);
    if (cached) currentModels = JSON.parse(cached);
  } catch(e){}
  // 缓存没有时，从下拉框读取
  if (!currentModels.length) {
    var modelSelect = document.getElementById('model_' + idx);
    if (modelSelect && modelSelect.options) {
      for (var mi = 0; mi < modelSelect.options.length; mi++) {
        var v = modelSelect.options[mi].value;
        if (v && !v.startsWith('请先')) currentModels.push(v);
      }
    }
  }

  // 收集能力声明
  var capabilities = {};
  var capSection = document.getElementById('capsSection_' + idx);
  var capChecks = capSection ? capSection.querySelectorAll('.cap-check') : [];
  capChecks.forEach(function(cb) {
    capabilities[cb.dataset.cap] = cb.checked;
  });

  var p = {
    id: document.getElementById('id_' + idx).value.trim() || 'p_' + Date.now(),
    name: document.getElementById('name_' + idx).value,
    type: document.getElementById('type_' + idx).value,
    base_url: document.getElementById('url_' + idx).value,
    api_key: document.getElementById('key_' + idx).value,
    api_keys: (document.getElementById('keys_' + idx).value || '').split('\n').map(function(s){ return s.trim(); }).filter(function(s){ return s.length > 0; }),
    endpoints: collectEndpoints(idx),
    model: document.getElementById('model_' + idx).value,
    color: document.getElementById('color_' + idx).value,
    enabled: document.getElementById('en_' + idx).checked,
    models: currentModels,
    display_name: (document.getElementById('display_name_' + idx) || {value:''}).value,
    capabilities: capabilities,
    skip_proxy: document.getElementById('skip_proxy_' + idx) ? document.getElementById('skip_proxy_' + idx).checked : false,
    endpoint_type: (document.getElementById('endpoint_type_' + idx) || {value:'auto'}).value,
    quality: '', extra: (findProvider(pid) && findProvider(pid).extra) || {}
  };
  _authFetch('/api/providers', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(p)
  }).then(function(r){ return r.json(); }).then(function(data){
    setStatus(i18nText('provider.saved_prefix') + p.name + i18nText('provider.saved_suffix'));
    loadProviders().then(function(){
      renderProviderEdit();
    });
  }).catch(function(e){ if (e.message !== 'AUTH_REQUIRED') setStatus(i18nText('common.save_failed_colon') + e.message); });
}

function updateCapsSection(idx) {
  var type = document.getElementById('type_' + idx).value;
  var section = document.getElementById('capsSection_' + idx);
  if (!section) return;

  if (type === 'llm') {
    section.innerHTML = '';
  } else if (type === 'image') {
    section.innerHTML =
      '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">' + i18nText('provider.capability_hint') + '</div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="t2i" checked style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('history.t2i') +
        '</label>' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="i2i" style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('history.i2i') +
        '</label>' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="inpaint_mask" style="accent-color:var(--accent);width:13px;height:13px;"> 局部重绘/遮罩' +
        '</label>' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="precision_edit" style="accent-color:var(--accent);width:13px;height:13px;"> 精准改图（确认上游支持后启用）' +
        '</label>' +
      '</div>' +
      '<div style="font-size:9px;color:var(--text-muted);margin-top:3px;">' + i18nText('provider.capability_auto_hint') + '</div>';
  } else if (type === 'video') {
    section.innerHTML =
      '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">' + i18nText('provider.capability_hint') + '</div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="t2v" checked style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('video.t2v') +
        '</label>' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="i2v" style="accent-color:var(--accent);width:13px;height:13px;"> ' + i18nText('video.i2v') +
        '</label>' +
      '</div>' +
      '<div style="font-size:9px;color:var(--text-muted);margin-top:3px;">' + i18nText('provider.capability_auto_hint') + '</div>';
  }
}

function deleteProvider(id) {
  if (!confirm(i18nText('provider.delete_confirm_prefix') + id + '"?')) return;
  _authFetch('/api/providers/' + id, {method:'DELETE'}).then(function(r){return r.json();}).then(function(){
    setStatus(i18nText('provider.deleted_prefix') + id);
    loadProviders().then(function(){
      renderProviderEdit();
    });
  }).catch(function(e){ setStatus(i18nText('common.delete_failed_colon') + e.message); });
}

function addEndpoint(idx) {
  var list = document.getElementById('epList_' + idx);
  if (!list) return;
  var ei = list.children.length;
  var div = document.createElement('div');
  div.className = 'ep-item';
  div.style.cssText = 'border-radius:8px;border:1px solid var(--border);background:var(--bg-base);padding:8px 10px;';
  div.innerHTML =
    '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">' +
      '<span style="font-size:9px;color:var(--text-muted);flex-shrink:0;">#' + (ei+1) + '</span>' +
      '<input type="text" placeholder="' + i18nText('provider.endpoint_name_placeholder') + '" data-ep-idx="' + ei + '" data-field="name" style="flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-weight:500;">' +
      '<label style="display:flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);cursor:pointer;flex-shrink:0;" title="' + i18nText('provider.endpoint_toggle_title') + '">' +
        '<input type="checkbox" checked data-ep-idx="' + ei + '" data-field="enabled" style="accent-color:#22c55e;width:13px;height:13px;">' +
        '<span>启用</span>' +
      '</label>' +
      '<button onclick="removeEndpoint(' + idx + ',' + ei + ')" title="' + i18nText('provider.endpoint_remove_title') + '" style="font-size:10px;padding:3px 7px;border-radius:5px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;flex-shrink:0;">?</button>' +
    '</div>' +
    '<div style="display:flex;gap:6px;">' +
      '<input type="text" placeholder="' + i18nText('provider.endpoint_url_placeholder') + '" data-ep-idx="' + ei + '" data-field="url" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
      '<input type="password" placeholder="API Key" data-ep-idx="' + ei + '" data-field="key" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
    '</div>';
  list.appendChild(div);
  // Focus the name input
  var nameInput = div.querySelector('[data-field="name"]');
  if (nameInput) nameInput.focus();
  var cnt = document.getElementById('epCount_' + idx);
  if (cnt) cnt.textContent = list.children.length + ' ' + i18nText('provider.endpoint_count_unit');
}

function removeEndpoint(idx, ei) {
  var list = document.getElementById('epList_' + idx);
  if (!list) return;
  var items = list.querySelectorAll('.ep-item');
  if (items[ei]) items[ei].remove();
  // Re-index
  var remaining = list.querySelectorAll('.ep-item');
  for (var r = 0; r < remaining.length; r++) {
    var inputs = remaining[r].querySelectorAll('input');
    for (var j = 0; j < inputs.length; j++) {
      inputs[j].setAttribute('data-ep-idx', r);
    }
    var btn = remaining[r].querySelector('button');
    if (btn) btn.setAttribute('onclick', 'removeEndpoint(' + idx + ',' + r + ')');
  }
  var cnt = document.getElementById('epCount_' + idx);
  if (cnt) cnt.textContent = remaining.length + ' ' + i18nText('provider.endpoint_count_unit');
}

function collectEndpoints(idx) {
  var list = document.getElementById('epList_' + idx);
  if (!list) return [];
  var items = list.querySelectorAll('.ep-item');
  var endpoints = [];
  for (var i = 0; i < items.length; i++) {
    var inputs = items[i].querySelectorAll('input');
    var ep = { name: '', url: '', key: '', enabled: true };
    for (var j = 0; j < inputs.length; j++) {
      var field = inputs[j].getAttribute('data-field');
      if (field === 'enabled') ep.enabled = inputs[j].checked;
      else if (field === 'name') ep.name = inputs[j].value;
      else if (field === 'url') ep.url = inputs[j].value;
      else if (field === 'key') ep.key = inputs[j].value;
    }
    if (ep.url || ep.key) endpoints.push(ep);
  }
  return endpoints;
}

function testProvider(id) {
  var btn = event && event.target;
  if (btn) { btn.disabled = true; btn.textContent = i18nText('provider.testing'); }
  _authFetch('/api/providers/test/' + id).then(function(r){return r.json();}).then(function(d){
    if (d.endpoints && d.endpoints.length > 0) {
      var lines = d.endpoints.map(function(ep) {
        var icon = ep.success ? '✅' : '❌';
        var latency = ep.latency_ms ? ep.latency_ms + 'ms' : '';
        var name = ep.name || ep.url;
        return icon + ' ' + name + (ep.success ? ' (' + latency + ')' : ' - ' + (ep.error || i18nText('status.failed')) + ' (' + latency + ')');
      });
      alert((d.success ? i18nText('provider.test_some_success') : i18nText('provider.test_all_failed')) + '\n\n' + lines.join('\n'));
    } else {
      alert(d.success ? i18nText('provider.test_success') : '? ' + i18nText('provider.test_failed_prefix') + (d.error||''));
    }
  }).catch(function(e){ alert('? ' + i18nText('provider.test_failed_prefix') + e.message); })
  .finally(function(){ if (btn) { btn.disabled = false; btn.textContent = i18nText('common.test'); } });
}

function fetchModels(idx) {
  var pid = document.getElementById('id_' + idx).value;
  var urlVal = document.getElementById('url_' + idx).value;
  var keyVal = document.getElementById('key_' + idx).value;
  var nameVal = document.getElementById('name_' + idx).value;
  var typeVal = document.getElementById('type_' + idx).value;
  var colorVal = document.getElementById('color_' + idx).value;
  var enVal = document.getElementById('en_' + idx).checked;
  var etVal = (document.getElementById('endpoint_type_' + idx) || {value:'auto'}).value;

  var btn = document.getElementById('fetchBtn_' + idx);
  var st  = document.getElementById('fetchStatus_' + idx);
  btn.disabled = true; btn.textContent = '...';
  st.textContent = i18nText('provider.connecting'); st.style.color = 'var(--text-muted)';

  var tmp = {
    id:pid||'tmp', name:nameVal, type:typeVal, base_url:urlVal, api_key:keyVal,
    api_keys: (document.getElementById('keys_' + idx).value || '').split('\n').map(function(s){ return s.trim(); }).filter(function(s){ return s.length > 0; }),
    endpoints: collectEndpoints(idx),
    model: (document.getElementById('model_' + idx) || {value:''}).value,
    color:colorVal, enabled:enVal, endpoint_type:etVal, models:[],
    display_name: (document.getElementById('display_name_' + idx) || {value:''}).value,
    capabilities: {},
    skip_proxy: document.getElementById('skip_proxy_' + idx) ? document.getElementById('skip_proxy_' + idx).checked : false,
    quality:'', extra:{}
  };
  document.querySelectorAll('#providerEditBody .cap-check').forEach(function(cb){ tmp.capabilities[cb.dataset.cap] = cb.checked; });

    _authFetch('/api/providers', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(tmp)})
    .then(function(){ return _authFetch('/api/providers/fetch-models/' + pid); })
    .then(function(r){ return r.json(); })
    .then(function(data){
      if (data.success) {
        st.textContent = i18nText('provider.fetch_success_prefix') + data.count + i18nText('provider.fetch_success_suffix') + (data.message ? ' ' + data.message : '');
        st.style.color = data.is_fallback ? '#f59e0b' : '#22c3a5';
        try { localStorage.setItem('igs_models_' + pid, JSON.stringify(data.models)); } catch(e){}
        loadProviders().then(function(){ renderProviderEdit(); });
      } else {
        var msg = data.detail || '拉取失败';
        if (data.provider_type === 'video') {
          msg += '\n💡 提示：视频模型通常需要手动输入模型名称';
        }
        st.textContent = '❌ ' + msg;
        st.style.color = '#f87171';
      }
    }).catch(function(e){
      st.textContent = '❌ ' + e.message; st.style.color = '#f87171';
    }).finally(function(){
      btn.disabled = false; btn.textContent = i18nText('provider.fetch_models');
    });
}

function reloadProviders() {
  _authFetch('/api/providers/reload', {method:'POST'}).then(function(){
    loadProviders().then(function(){ renderProviderEdit(); updatePrecisionResizeCapabilityUI(); });
    setStatus(i18nText('provider.reloaded'));
  });
}

// ═══════════════════════════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════════════════════════
function escHtml(s) {
  var d = document.createElement('div'); d.textContent = s||''; return d.innerHTML;
}
function escAttr(s) {
  return (s||'').replace(/'/g,'&#39;').replace(/"/g,'&quot;');
}
function setStatus(msg) {
  document.getElementById('statusLeft').textContent = msg;
}


// ═══════════════════════════════════════════════════════════════════
// 可拖拽分隔条（面板宽度调整）
// ═══════════════════════════════════════════════════════════════════
(function(){
  var dragTarget = null;
  var startX, startWidths = {};

  function onMouseDown(e) {
    var divider = e.currentTarget;
    dragTarget = divider;
    divider.classList.add('active');
    document.body.classList.add('dragging-divider');

    startX = e.clientX;

    var layout = divider.parentElement;
    var leftEl = layout.querySelector('.generate-left');
    var centerEl = layout.querySelector('.generate-center');
    var previewEl = layout.querySelector('.generate-preview');

    startWidths = {
      left: leftEl ? leftEl.getBoundingClientRect().width : 0,
      center: centerEl ? centerEl.getBoundingClientRect().width : 0,
      preview: previewEl ? previewEl.getBoundingClientRect().width : 0,
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    e.preventDefault();
  }

  function onMouseMove(e) {
    if (!dragTarget) return;
    var dx = e.clientX - startX;
    var layout = dragTarget.parentElement;
    var leftEl = layout.querySelector('.generate-left');
    var centerEl = layout.querySelector('.generate-center');
    var previewEl = layout.querySelector('.generate-preview');

    var prev = dragTarget.dataset.prev;
    var next = dragTarget.dataset.next;

    if (prev === 'left' && next === 'center') {
      var newLeft = Math.max(180, startWidths.left + dx);
      var newCenter = Math.max(300, startWidths.center - dx);
      if (leftEl) leftEl.style.width = newLeft + 'px';
      // center 是 flex:1, 让内容自行适配
    } else if (prev === 'center' && next === 'preview') {
      // 预览面板是 flex:1 自适应的，不需要改宽度
    }
  }

  function onMouseUp() {
    dragTarget = null;
    document.querySelectorAll('.divider-drag').forEach(function(d){ d.classList.remove('active'); });
    document.body.classList.remove('dragging-divider');
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }

  // 绑定所有分隔条
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('.divider-drag').forEach(function(d){
      d.addEventListener('mousedown', onMouseDown);
    });
  });
})();


// ═══════════════════════════════════════════════════════════════════
// 图库: 选择模式 + 批量删除
// ═══════════════════════════════════════════════════════════════════
var gallerySelectMode = false;
var selectedGalleryItems = [];
var allGalleryIds = [];

function toggleGallerySelectMode() {
  gallerySelectMode = !gallerySelectMode;
  var btn = document.getElementById('btnGallerySelect');
  if (gallerySelectMode) {
    btn.textContent = i18nText('gallery.exit_select');
    btn.style.borderColor = 'var(--accent)';
    btn.style.color = 'var(--accent)';
    btn.classList.add('active');
    showGalleryToolbar(true);
  } else {
    btn.textContent = i18nText('library.select_mode');
    btn.style.borderColor = '';
    btn.style.color = '';
    btn.classList.remove('active');
    deselectAllGallery();
    showGalleryToolbar(false);
  }
  loadGallery(); // 重新渲染，切换点击行为
}
function showGalleryToolbar(show) {
  document.getElementById('btnSelAll').classList.toggle('hidden', !show);
  document.getElementById('btnSelNone').classList.toggle('hidden', !show);
  document.getElementById('btnGalleryRename').classList.toggle('hidden', !show);
  document.getElementById('btnPushToRef').classList.toggle('hidden', !show || activeMediaTab !== 'image');
  document.getElementById('btnDlSelected').classList.toggle('hidden', !show);
  document.getElementById('btnDelSelected').classList.toggle('hidden', !show);
}
function selectAllGallery() {
  var visIds = [];
  var els = document.querySelectorAll('#galleryGrid .gallery-item');
  for (var i = 0; i < els.length; i++) {
    visIds.push(els[i].getAttribute('data-id'));
  }
  selectedGalleryItems = visIds;
  updateGallerySelectionUI();
}
function deselectAllGallery() { selectedGalleryItems = []; updateGallerySelectionUI(); }
function toggleGalleryItem(id, el) {
  if (!gallerySelectMode) return;
  event.stopPropagation(); event.preventDefault();
  var idx = selectedGalleryItems.indexOf(id);
  if (idx !== -1) { selectedGalleryItems.splice(idx, 1); el.classList.remove('selected'); }
  else { selectedGalleryItems.push(id); el.classList.add('selected'); }
  updateGallerySelectionUI();
}
function updateGallerySelectionUI() {
  document.getElementById('selGalleryCount').textContent = selectedGalleryItems.length;
  document.getElementById('dlGalleryCount').textContent = selectedGalleryItems.length;
  for (var i = 0; i < allGalleryIds.length; i++) {
    (function(id){ var item = document.querySelector('.gallery-item[data-id="'+id+'"]'); if(item) item.classList.toggle('selected', selectedGalleryItems.indexOf(id)!==-1); })(allGalleryIds[i]);
  }
}
function batchDownloadGallery() {
  if (!selectedGalleryItems.length) { alert('Please select images to download'); return; }
  setStatus('Preparing download...');
  _authFetch('/api/gallery/batch-download', { method:'POST', body:JSON.stringify(selectedGalleryItems) })
    .then(function(r){
      if (!r.ok) throw new Error('Server error ' + r.status);
      return r.blob();
    })
    .then(function(blob){
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'image_gen_studio_' + new Date().toISOString().slice(0,19).replace(/[:-]/g,'') + '.zip';
      document.body.appendChild(a);
      a.click();
      setTimeout(function(){ URL.revokeObjectURL(url); a.remove(); }, 1000);
      setStatus('Download started: ' + selectedGalleryItems.length + ' images');
    })
    .catch(function(e){ alert('Download failed: ' + e.message); });
}
function deleteSelectedGallery() {
  if (!selectedGalleryItems.length) { alert(i18nText('gallery.delete_select')); return; }
  if (!confirm(i18nText('gallery.delete_confirm_prefix') + selectedGalleryItems.length + i18nText('gallery.delete_confirm_suffix'))) return;
  _authFetch('/api/gallery/batch-delete', { method:'POST', body:JSON.stringify(selectedGalleryItems) })
    .then(function(r){return r.json();}).then(function(d){ setStatus(i18nText('gallery.deleted_prefix') + d.total_deleted + i18nText('gallery.deleted_suffix')); selectedGalleryItems=[]; loadGallery(); })
    .catch(function(e){ alert(i18nText('common.delete_failed_colon')+e.message); });
}

// loadGallery 已合并到上方，支持选择模式和灯箱两种点击行为


// ═══════════════════════════════════════════════════════════════════
// 日志系统
// ═══════════════════════════════════════════════════════════════════
var currentLogCategory = '';
function openLogModal(){ document.getElementById('logModal').classList.add('show'); loadLogs(); }
function closeLogModal(){ document.getElementById('logModal').classList.remove('show'); }
function filterLog(cat){ currentLogCategory=cat; document.querySelectorAll('.log-filter-btn').forEach(function(b){b.classList.toggle('active',b.dataset.cat===cat);}); loadLogs(); }
function loadLogs(){
  var body=document.getElementById('logBody'); body.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:30px;font-size:12px;">' + i18nText('common.loading') + '</div>';
  var url='/api/logs?limit=100'; if(currentLogCategory) url+='&category='+currentLogCategory;
  fetch(url).then(function(r){return r.json();}).then(function(d){
    var items=d.items||[];
    if(!items.length){ body.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:40px;font-size:13px;">' + i18nText('logs.empty') + '</div>'; return; }
    var html='';
    for(var i=0;i<items.length;i++){(function(entry){
      var cls='log-cat-'+(entry.category||'system');
      var detailHtml='';
      if(entry.details&&Object.keys(entry.details).length) detailHtml='<div class="log-detail">'+escHtml(JSON.stringify(entry.details,null,2))+'</div>';
      html+='<div class="log-entry"><div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'+
        '<span class="log-ts">'+escHtml(entry.ts)+'</span>'+
        '<span class="log-cat '+cls+'">'+entry.category+'</span>'+
        '<span class="log-msg">'+escHtml(entry.message)+'</span></div>'+detailHtml+'</div>';
    })(items[i]);}
    body.innerHTML=html;
  }).catch(function(e){ body.innerHTML='<div style="text-align:center;color:#f87171;padding:40px;">' + i18nText('common.load_failed') + '</div>'; });
}
function clearLogs(){ if(!confirm(i18nText('logs.clear_confirm')))return;   _authFetch('/api/logs',{method:'DELETE'}).then(function(){loadLogs();setStatus(i18nText('logs.cleared'));}); }


// ═══════════════════════════════════════════════════════════════════
// 主题系统（8 套预设）
// ═══════════════════════════════════════════════════════════════════
var THEME_PRESETS=[
  {name:'Apple Mono',description:'清爽浅色，接近 macOS 工具界面。',id:'apple-mono',vars:{'--bg-base':'#eef1f5','--bg-surface':'#f7f8fa','--bg-card':'#ffffff','--bg-card-hover':'#f3f6fa','--border':'#dfe4eb','--border-light':'#cfd7e3','--accent':'#0a7cff','--accent-glow':'rgba(10,124,255,0.14)','--accent-2':'#00a884','--accent-3':'#5b63e6','--accent-yellow':'#b7791f','--text-primary':'#111827','--text-secondary':'#667085','--text-muted':'#98a2b3'},colors:['#eef1f5','#ffffff','#0a7cff','#00a884']},
  {name:'深空控制台',description:'GenBox 默认深色，适合长时间操作。',id:'default',vars:{'--bg-base':'#0c0e14','--bg-surface':'#12151e','--bg-card':'#181c28','--bg-card-hover':'#1e2233','--border':'#262d3f','--border-light':'#2f3750','--accent':'#5b8def','--accent-glow':'rgba(91,141,239,0.25)','--accent-2':'#22d3a5','--accent-3':'#a78bfa','--accent-yellow':'#fbbf24','--text-primary':'#e2e8f0','--text-secondary':'#8892aa','--text-muted':'#4b5568'},colors:['#0c0e14','#181c28','#5b8def','#22d3a5']},
  {name:'石墨工作台',description:'低干扰黑灰，突出图片与任务状态。',id:'graphite',vars:{'--bg-base':'#090a0c','--bg-surface':'#101216','--bg-card':'#17191e','--bg-card-hover':'#20232a','--border':'#282c34','--border-light':'#373c46','--accent':'#dbe4f0','--accent-glow':'rgba(219,228,240,0.12)','--accent-2':'#7dd3fc','--accent-3':'#a3e635','--accent-yellow':'#facc15','--text-primary':'#f4f6f8','--text-secondary':'#a7b0bf','--text-muted':'#667085'},colors:['#090a0c','#17191e','#dbe4f0','#7dd3fc']},
  {name:'云端白板',description:'中性高亮浅色，适合白天和办公环境。',id:'cloud',vars:{'--bg-base':'#f4f6f8','--bg-surface':'#fafbfc','--bg-card':'#ffffff','--bg-card-hover':'#f1f4f7','--border':'#d8dee7','--border-light':'#c6cfdb','--accent':'#315efb','--accent-glow':'rgba(49,94,251,0.12)','--accent-2':'#008f72','--accent-3':'#7c3aed','--accent-yellow':'#b7791f','--text-primary':'#17202e','--text-secondary':'#536174','--text-muted':'#8a97a8'},colors:['#f4f6f8','#ffffff','#315efb','#008f72']},
  {name:'鎏金夜幕',description:'黑曜底色配克制鎏金，沉稳而不浮夸。',id:'gilded-night',vars:{'--bg-base':'#11100e','--bg-surface':'#181612','--bg-card':'#211e18','--bg-card-hover':'#2a261e','--border':'#393329','--border-light':'#504735','--accent':'#c9a45b','--accent-glow':'rgba(201,164,91,0.18)','--accent-2':'#8fa69a','--accent-3':'#b8a98b','--accent-yellow':'#d3ae62','--text-primary':'#f2ede3','--text-secondary':'#bdb3a1','--text-muted':'#756d60'},colors:['#11100e','#211e18','#c9a45b','#8fa69a']},
  {name:'香槟鎏金',description:'暖白与香槟金，适合精致明亮的办公场景。',id:'champagne',vars:{'--bg-base':'#f2eee6','--bg-surface':'#faf7f1','--bg-card':'#fffdf8','--bg-card-hover':'#f7f1e7','--border':'#ddd3c2','--border-light':'#cbbda7','--accent':'#9a7437','--accent-glow':'rgba(154,116,55,0.14)','--accent-2':'#52766b','--accent-3':'#735f8f','--accent-yellow':'#9a7437','--text-primary':'#29251f','--text-secondary':'#6e6558','--text-muted':'#9b9182'},colors:['#f2eee6','#fffdf8','#9a7437','#52766b']},
  {name:'雾银中灰',description:'柔和中灰与冷蓝，克制、清晰、耐久。',id:'mist-gray',vars:{'--bg-base':'#dfe2e5','--bg-surface':'#e9ebed','--bg-card':'#f4f5f6','--bg-card-hover':'#e8ebee','--border':'#c6cbd0','--border-light':'#adb4bb','--accent':'#496b8a','--accent-glow':'rgba(73,107,138,0.14)','--accent-2':'#4f786d','--accent-3':'#706582','--accent-yellow':'#8d7138','--text-primary':'#252a2f','--text-secondary':'#5d656d','--text-muted':'#858d95'},colors:['#dfe2e5','#f4f5f6','#496b8a','#4f786d']},
  {name:'钛灰控制台',description:'中深钛灰与钢蓝，适合专业监控与管理。',id:'titanium',vars:{'--bg-base':'#24272b','--bg-surface':'#2c3035','--bg-card':'#34393f','--bg-card-hover':'#3d434a','--border':'#4a5159','--border-light':'#5b646e','--accent':'#8eabc4','--accent-glow':'rgba(142,171,196,0.18)','--accent-2':'#83ad9d','--accent-3':'#aaa0bd','--accent-yellow':'#c4a568','--text-primary':'#f0f2f4','--text-secondary':'#b8bec5','--text-muted':'#858d96'},colors:['#24272b','#34393f','#8eabc4','#83ad9d']},
  {name:'古籍雅黄',description:'宣纸暖黄与朱砂点色，温润而易读。',id:'classic-book',vars:{'--bg-base':'#e8ddc3','--bg-surface':'#f0e7d2','--bg-card':'#f7f0df','--bg-card-hover':'#eee3cb','--border':'#d1c19f','--border-light':'#bca982','--accent':'#8b3f32','--accent-glow':'rgba(139,63,50,0.13)','--accent-2':'#536b4f','--accent-3':'#665b78','--accent-yellow':'#8a682b','--text-primary':'#30291f','--text-secondary':'#6d604d','--text-muted':'#95866f'},colors:['#e8ddc3','#f7f0df','#8b3f32','#536b4f']},
  {name:'水墨宣纸',description:'墨色层次配青绿点染，留白清雅耐看。',id:'ink-wash',vars:{'--bg-base':'#e8e9e5','--bg-surface':'#f1f2ee','--bg-card':'#fafaf6','--bg-card-hover':'#eceee9','--border':'#cfd2cc','--border-light':'#b6bbb4','--accent':'#315e58','--accent-glow':'rgba(49,94,88,0.14)','--accent-2':'#667b58','--accent-3':'#655f73','--accent-yellow':'#8a6f3e','--text-primary':'#222724','--text-secondary':'#59615c','--text-muted':'#858d87'},colors:['#e8e9e5','#fafaf6','#315e58','#667b58']}
];
var NAV_STYLE_PRESETS=[['a','Apple Mono'],['b','Circuit Precision'],['c','Soft Glass'],['d','Fluent Air'],['e','Material Prism'],['f','Creative Spectrum'],['g','Cloud Jade'],['h','Aurora Link']];
function renderNavStylePresets(){var c=document.getElementById('navStylePresets');if(!c)return;var active=localStorage.getItem('igs_nav_style')||'c';c.innerHTML=NAV_STYLE_PRESETS.map(function(p){return '<button type="button" class="nav-style-preset '+(p[0]===active?'active':'')+'" onclick="applyNavStyle(\''+p[0]+'\')"><span>' + i18nText('workspace.scheme_prefix') + ' ' + p[0].toUpperCase() + '</span><strong>'+p[1]+'</strong></button>';}).join('');}
function applyNavStyle(id){document.body.className=document.body.className.replace(/nav-style-[a-h]/g,'').trim();document.body.classList.add('nav-style-'+id);localStorage.setItem('igs_nav_style',id);renderNavStylePresets();}
var CREATOR_WORKBENCH_COPY={
  image:{multi:[i18nText('creator.image_multi_title'),i18nText('creator.image_multi_hint')],single:[i18nText('creator.single_image_title'),i18nText('creator.single_image_hint')],precision:[i18nText('creator.precision_edit_title'),i18nText('creator.precision_edit_hint')]},
  video:{multi:[i18nText('video.multi_title'),i18nText('video.multi_hint')],single:[i18nText('video.single_title'),i18nText('video.single_hint')]}
};
var CREATOR_WORKBENCH_COPY_EN={
  image:{multi:['Multi-model image comparison','Run the same prompt across models and compare results.'],single:['Single-model image workspace','One model, a larger prompt, fewer distractions, one screen.'],precision:['Precise image edit','Mark exactly what to change on the image.']},
  video:{multi:['Multi-model video comparison','Submit to multiple video models and compare results together.'],single:['Single-model video workspace','One model with core controls and a large input area on one screen.']}
};
function renderCreatorProviderPickers(){
  if(!Array.isArray(allProviders))allProviders=[];
  if(!Array.isArray(selectedProviders))selectedProviders=[];
  if(!Array.isArray(videoProviders))videoProviders=[];
  if(!Array.isArray(selectedVideoProviderIds))selectedVideoProviderIds=[];
  var imagePicker=document.getElementById('imageSingleProvider');
  if(imagePicker){
    var imageProviders=allProviders.filter(function(provider){return provider.type==='image'&&provider.enabled!==false;});
    imagePicker.innerHTML=imageProviders.map(function(provider){return '<option value="'+escAttr(provider.id)+'">'+escHtml(provider.name||provider.id)+'</option>';}).join('');
    var imageId=selectedProviders[0]||(imageProviders[0]&&imageProviders[0].id)||'';
    if(imageId){imagePicker.value=imageId;if((localStorage.getItem('igs_image_workbench')||'multi')==='single')selectedProviders=[imageId];}
  }
  var videoPicker=document.getElementById('videoSingleProvider');
  if(videoPicker){
    videoPicker.innerHTML=videoProviders.map(function(provider){return '<option value="'+escAttr(provider.id)+'">'+escHtml(provider.name||provider.id)+'</option>';}).join('');
    var videoId=selectedVideoProviderIds[0]||(videoProviders[0]&&videoProviders[0].id)||'';
    if(videoId){videoPicker.value=videoId;if((localStorage.getItem('igs_video_workbench')||'multi')==='single')selectedVideoProviderIds=[videoId];}
  }
}
function selectSingleCreatorProvider(kind,id){
  if(!id)return;
  if(kind==='image'){selectedProviders=[id];renderProviderList();}
  else {selectedVideoProviderIds=[id];renderVideoProviderCards();}
  renderCreatorProviderPickers();
  if(kind==='image')updateInpaintAvailability();
}

function sendToImageToImage(e) {
  e.stopPropagation();
  if (!lightboxCurrentSrc) { alert(i18nText('image.unavailable')); return; }
  var imgUrl = lightboxCurrentSrc;
  window._pendingI2IPrompt = lightboxCurrentPrompt || '';
  closeLightbox(e);
  if (window.dockNav) { window.dockNav.switchPage('generate'); }

  var fname = imgUrl.split('/').pop();
  _authFetch('/api/gallery/image/' + fname + '/base64')
    .then(function(r) {
      if (!r.ok) throw new Error(i18nText('image.data_failed'));
      return r.json();
    })
    .then(function(d) {
      uploadedImageData = d.data;
      uploadedImageDataList = [d.data];
      setTimeout(function() {
        switchSubTab('i2i');
        var preview = document.getElementById('uploadPreview');
        if (preview) { preview.src = d.data; preview.classList.remove('hidden'); }
        renderUploadedImagePreviews();
        var prompt = document.getElementById('txtPromptI2I');
        if (prompt && window._pendingI2IPrompt) prompt.value = window._pendingI2IPrompt;
        setStatus(i18nText('image.sent_i2i'));
      }, 300);
    })
    .catch(function(error) {
      alert(i18nText('image.load_failed') + error.message);
    });
}
function setCreatorWorkbenchMode(kind,mode){
  if(kind==='image'&&mode==='precision'){
    localStorage.setItem('igs_image_workbench','precision');
    var precisionPage=document.getElementById('pageGenerate');
    if(precisionPage){precisionPage.classList.remove('creator-single');precisionPage.classList.add('precision-workbench');}
    switchSubTab('precision_edit');
  }else{
    if(mode!=='single')mode='multi';
    var normalPage=document.getElementById(kind==='image'?'pageGenerate':'pageVideo');
    if(normalPage)normalPage.classList.remove('precision-workbench');
    if(kind==='image'&&currentMode==='precision_edit'){ cancelPrecisionQuickStart(); switchSubTab('t2i'); }
  }
  if(kind==='image')setPrecisionFocusMode(mode==='precision');
  localStorage.setItem('igs_'+kind+'_workbench',mode);
  var page=document.getElementById(kind==='image'?'pageGenerate':'pageVideo');
  if(page)page.classList.toggle('creator-single',mode==='single');
  var copy=(getUiLanguage()==='en'?CREATOR_WORKBENCH_COPY_EN:CREATOR_WORKBENCH_COPY)[kind][mode];
  var title=document.getElementById(kind+'WorkbenchTitle');
  var hint=document.getElementById(kind+'WorkbenchHint');
  var precisionHelp=kind==='image'?document.getElementById('precisionWorkbenchHelp'):null;
  if(title)title.textContent=copy[0];
  if(hint){hint.textContent=mode==='precision'?'':copy[1];hint.classList.toggle('hidden',mode==='precision');}
  if(precisionHelp)precisionHelp.classList.toggle('hidden',mode!=='precision');
  if(mode==='precision')bindPrecisionWorkbenchHelp();else setPrecisionWorkbenchHelp(false,false,true);
  var multi=document.getElementById(kind+'ModeMulti');
  var single=document.getElementById(kind+'ModeSingle');
  var precision=document.getElementById(kind+'ModePrecision');
  if(multi)multi.classList.toggle('active',mode==='multi');
  if(single)single.classList.toggle('active',mode==='single');
  if(precision)precision.classList.toggle('active',mode==='precision');
  if(kind==='image' && mode==='precision') renderPrecisionEditModelPicker();
  renderCreatorProviderPickers();
  if(mode==='single'){
    var picker=document.getElementById(kind+'SingleProvider');
    if(picker&&picker.value)selectSingleCreatorProvider(kind,picker.value);
  }
  if(getVisibleAppPage()===(kind==='image'?'generate':'video'))updateAppRoute(kind==='image'?'generate':'video');
}
var creatorToolHintTimer=null;
function setCreatorToolRailCollapsed(collapsed){
  var row=document.getElementById('creatorCanvasRow');
  var button=document.getElementById('creatorToolRailToggle');
  if(row)row.classList.toggle('tools-collapsed',!!collapsed);
  if(button){
    button.innerHTML=collapsed?'<span class="creator-tool-handle-icon" aria-hidden="true">⚙</span><span class="creator-tool-handle-text">' + i18nText('creator.tools') + '</span><span class="creator-tool-handle-arrow" aria-hidden="true">‹</span>':'<span aria-hidden="true">›</span><span>' + i18nText('creator.collapse_tools') + '</span>';
    button.setAttribute('aria-expanded',collapsed?'false':'true');
    button.setAttribute('aria-label',collapsed?i18nText('creator.expand_tools'):i18nText('creator.collapse_tools'));
    button.title=collapsed?i18nText('creator.expand_tools'):i18nText('creator.collapse_tools');
  }
  if(row){
    clearTimeout(creatorToolHintTimer);
    row.classList.remove('tools-attention');
    if(collapsed){
      requestAnimationFrame(function(){row.classList.add('tools-attention');});
      creatorToolHintTimer=setTimeout(function(){row.classList.remove('tools-attention');},2600);
    }
  }
  localStorage.setItem('igs_creator_tools_collapsed',collapsed?'yes':'no');
}
function toggleCreatorToolRail(){
  var row=document.getElementById('creatorCanvasRow');
  setCreatorToolRailCollapsed(!row||!row.classList.contains('tools-collapsed'));
}
function showCreatorTaskMonitor(expanded){
  var monitor=document.getElementById('creatorTaskMonitor');
  if(!monitor)return;
  monitor.classList.toggle('expanded',!!expanded);
  if(precisionFocusState.active){
    precisionFocusState.taskCollapsed=!expanded;
    if(expanded)precisionFocusState.taskHasActivity=false;
  }
  var button=document.getElementById('creatorTaskToggle');
  if(button){button.textContent=expanded?i18nText('creator.collapse'):i18nText('creator.expand');button.setAttribute('aria-expanded',expanded?'true':'false');}
  if(precisionFocusState.active)updatePrecisionFocusControls();
}
function toggleCreatorTaskMonitor(){
  var monitor=document.getElementById('creatorTaskMonitor');
  showCreatorTaskMonitor(!monitor||!monitor.classList.contains('expanded'));
}
function mountCreatorGenerateAction(mode){
  var action=document.getElementById('creatorGenerateAction');
  var header=document.getElementById('creatorGenerateHeader');
  var target=document.getElementById(mode==='i2i'?'panelI2I':mode==='precision_edit'?'panelPrecisionEdit':mode==='inpaint'?'panelVAR':'panelT2I');
  if(!action||!header||!target)return;
  var actionTarget=mode==='precision_edit'?document.getElementById('precisionGalleryCommandBar')||target:target;
  header.classList.toggle('precision-action-header',mode==='precision_edit');
  target.insertBefore(header,target.firstChild);
  actionTarget.appendChild(action);
  var promptModeButton=document.getElementById('btnModeNewbie');
  var promptModeGroup=promptModeButton&&promptModeButton.parentElement;
  if(promptModeGroup)promptModeGroup.classList.toggle('hidden',mode==='inpaint'||mode==='precision_edit');
  var title=document.getElementById('creatorGenerateActionTitle');
  var hint=document.getElementById('creatorGenerateActionHint');
  var button=document.getElementById('btnGen');
  var taskIsActive=!!genCurrentGenId||genCancelRequested;
  if(mode==='i2i'){
    if(title)title.textContent=i18nText('creator.i2i_settings');
    if(hint)hint.textContent=i18nText('creator.i2i_hint');
    if(button&&!taskIsActive)button.innerHTML=i18nText('creator.generate_image');
  }else if(mode==='precision_edit'){
    if(title)title.textContent=i18nText('creator.precision_edit');
    if(hint)hint.textContent=i18nText('creator.precision_edit_canvas_hint');
    if(button&&!taskIsActive)button.innerHTML=i18nText('creator.generate_image');
  }else if(mode==='inpaint'){
    if(title)title.textContent=i18nText('creator.inpaint_settings');
    if(hint)hint.textContent=i18nText('creator.inpaint_hint');
    if(button&&!taskIsActive)button.innerHTML=i18nText('creator.generate_image');
  }else{
    if(title)title.textContent=i18nText('creator.prompt_title');
    if(hint)hint.textContent=i18nText('creator.prompt_hint');
    if(button&&!taskIsActive)button.innerHTML=i18nText('creator.generate_image');
  }
}

function openPrecisionGalleryPicker(returnFocus){
  if (typeof closePrecisionDocsDialog === 'function') closePrecisionDocsDialog(false);
  var hadDirty=precisionEditSourceImageData&&precisionSourceHasDirtyState();
  if(!preparePrecisionSourceReplacement())return false;
  var requestGeneration=++precisionSourceLoadGeneration;
  var opener=returnFocus&&typeof returnFocus.focus==='function'?returnFocus:document.activeElement;
  setStatus(i18nText('creator.precision_edit_loading_gallery'));
  _authFetch('/api/preview/images').then(function(r){
    if(requestGeneration!==precisionSourceLoadGeneration)return null;
    if(!r.ok)throw new Error(i18nText('common.load_failed'));
    return r.json();
  }).then(function(data){
    if(!data)return;
    if(requestGeneration!==precisionSourceLoadGeneration)return;
    var items=data.items||[];
    if(!items.length){alert(i18nText('creator.precision_edit_gallery_empty'));return;}
    var overlay=document.createElement('div');
    overlay.id='precisionGalleryOverlay';
    overlay.className='precision-gallery-overlay';
    overlay.innerHTML='<div class="precision-gallery-dialog" role="dialog" aria-modal="true" aria-labelledby="precisionGalleryTitle"><div class="precision-gallery-heading"><strong id="precisionGalleryTitle">'+escHtml(i18nText('creator.precision_edit_from_gallery'))+'</strong><button type="button" class="btn-ghost" id="precisionGalleryClose" aria-label="'+escAttr(i18nText('common.close'))+'">✕</button></div><div class="precision-gallery-grid" id="precisionGalleryGrid"></div></div>';
    document.body.appendChild(overlay);
    var dialog=overlay.querySelector('.precision-gallery-dialog');
    var closeButton=document.getElementById('precisionGalleryClose');
    function closeGalleryPicker(){
      overlay.remove();
      if(opener&&typeof opener.focus==='function')opener.focus();
    }
    closeButton.onclick=closeGalleryPicker;
    overlay.onclick=function(e){if(e.target===overlay)closeGalleryPicker();};
    overlay.addEventListener('keydown',function(event){
      if(event.key==='Escape'){
        event.preventDefault();
        closeGalleryPicker();
        return;
      }
      if(event.key!=='Tab'||!dialog)return;
      var focusable=Array.prototype.slice.call(dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(function(node){return !node.disabled;});
      if(!focusable.length){event.preventDefault();return;}
      var first=focusable[0];
      var last=focusable[focusable.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    });
    var grid=document.getElementById('precisionGalleryGrid');
    items.forEach(function(item){
      var button=document.createElement('button');
      button.type='button';button.className='precision-gallery-item';
      button.innerHTML='<img src="'+escAttr(item.data)+'" alt=""><span>'+escHtml((item.prompt||item.filename||'').substring(0,50))+'</span>';
      button.onclick=function(){
        if(requestGeneration!==precisionSourceLoadGeneration||precisionSourceTaskIsActive())return;
        if(!hadDirty&&precisionEditSourceImageData&&precisionSourceHasDirtyState()&&!preparePrecisionSourceReplacement())return;
        setCreatorWorkbenchMode('image','precision');
        var source = item.data || item.gallery_url || item.url || item.src || '';
        if (!source) return;
        loadPrecisionEditSourceImage(source,item.prompt||'',{generation:requestGeneration,onLoaded:function(){setStatus(i18nText('creator.precision_edit_gallery_loaded'));}});
        overlay.remove();
      };
      grid.appendChild(button);
    });
    if(closeButton&&typeof closeButton.focus==='function')closeButton.focus();
  }).catch(function(error){if(requestGeneration===precisionSourceLoadGeneration)alert(i18nText('common.load_failed_prefix')+error.message);});
  return true;
}
function initializeImageWorkbenchLayout(){
  var page=document.getElementById('pageGenerate');
  var center=page&&page.querySelector('.generate-center');
  var preview=document.getElementById('previewPanel');
  var bottomRow=page&&page.querySelector('.generate-bottom-row');
  if(!page||!center||!preview||!bottomRow||document.getElementById('creatorCanvasRow'))return;
  var canvasRow=document.createElement('div');
  canvasRow.id='creatorCanvasRow';
  canvasRow.className='creator-canvas-row';
  center.insertBefore(canvasRow,preview);
  canvasRow.appendChild(preview);
  var rail=document.createElement('aside');
  rail.id='creatorToolRail';
  rail.className='creator-tool-rail';
  rail.innerHTML='<div class="creator-panel-heading"><div><strong>' + i18nText('creator.tools') + '</strong><span>' + i18nText('creator.tools_hint') + '</span></div><button id="creatorToolRailToggle" type="button" onclick="toggleCreatorToolRail()" aria-expanded="true">' + i18nText('creator.collapse') + '</button></div><section class="creator-tool-section"><div class="creator-tool-title">' + i18nText('creator.creation_mode') + '</div><div id="creatorModeTools"></div></section><section class="creator-tool-section"><div class="creator-tool-title">' + i18nText('creator.assist_tools') + '</div><div id="creatorAssistTools"></div></section><section class="creator-tool-section creator-quick-section"><div id="creatorQuickTools"></div></section>';
  canvasRow.appendChild(rail);
  var modeTools=document.getElementById('creatorModeTools');
  var assistTools=document.getElementById('creatorAssistTools');
  var quickTools=document.getElementById('creatorQuickTools');
  var subTabs=document.getElementById('subTabT2I');
  var promptModes=document.getElementById('btnModeNewbie');
  var enhance=document.getElementById('chkEnhance');
  var continuous=document.getElementById('chkContinuous');
  var upscale=document.getElementById('upscaleOpts');
  var quickCard=document.getElementById('quickCard');
  // 一级创作标签和二级提示词模式会挂到当前输入面板标题下。
  if(enhance&&enhance.parentElement&&enhance.parentElement.parentElement)assistTools.appendChild(enhance.parentElement.parentElement);
  if(continuous&&continuous.parentElement&&continuous.parentElement.parentElement)assistTools.appendChild(continuous.parentElement.parentElement);
  if(upscale)assistTools.appendChild(upscale);
  if(quickCard)quickTools.appendChild(quickCard);
  var actionCard=bottomRow.querySelector('.generate-input-col > .glass-card');
  var generateButton=document.getElementById('btnGen');
  var stopButton=document.getElementById('btnStopGen');
  if(actionCard&&generateButton&&stopButton){
    var header=document.createElement('div');
    header.id='creatorGenerateHeader';
    header.className='creator-generate-header';
    header.innerHTML='<strong id="creatorGenerateActionTitle">' + i18nText('creator.prompt_title') + '</strong><span id="creatorGenerateActionHint">' + i18nText('creator.prompt_hint') + '</span>';
    if(subTabs&&subTabs.parentElement)header.appendChild(subTabs.parentElement);
    if(promptModes&&promptModes.parentElement)header.appendChild(promptModes.parentElement);
    var action=document.createElement('div');
    action.id='creatorGenerateAction';
    action.className='creator-generate-action';
    action.appendChild(generateButton);
    action.appendChild(stopButton);
    actionCard.remove();
    document.getElementById('panelT2I').insertBefore(header,document.getElementById('panelT2I').firstChild);
    document.getElementById('panelT2I').appendChild(action);
  }
  mountCreatorGenerateAction(currentMode);
  var monitor=document.createElement('section');
  monitor.id='creatorTaskMonitor';
  monitor.className='creator-task-monitor';
  monitor.innerHTML='<div class="creator-task-heading" onclick="toggleCreatorTaskMonitor()"><div><strong>' + i18nText('creator.task_monitor') + '</strong><span id="creatorTaskSummary">' + i18nText('creator.task_summary') + '</span></div><button id="creatorTaskToggle" type="button" aria-expanded="false">' + i18nText('creator.expand') + '</button></div><div class="creator-task-body"><div class="creator-progress-pane" id="creatorProgressPane"></div><div class="creator-provider-pane"><div class="creator-task-label">' + i18nText('creator.model_tasks') + '</div><div id="perProviderSection"></div></div><div class="creator-log-pane"><div class="creator-task-label">' + i18nText('creator.runtime_logs') + ' <span id="genLogCount"></span></div><div id="previewLogDock"></div><div id="genLogWrap"><div id="genLogArea"></div></div></div></div>';
  center.insertBefore(monitor,bottomRow);
  var progress=document.getElementById('progressBox');
  var previewLogs=document.getElementById('previewLogSection');
  if(progress)document.getElementById('creatorProgressPane').appendChild(progress);
  if(previewLogs){previewLogs.classList.add('creator-preview-logs');document.getElementById('previewLogDock').appendChild(previewLogs);}
  bottomRow.classList.add('creator-input-row');
  setCreatorToolRailCollapsed(localStorage.getItem('igs_creator_tools_collapsed')==='yes');
  showCreatorTaskMonitor(false);
  if(isPrecisionFocusActive())setPrecisionFocusPreviewCollapsed(true);
}
function setContinuousGeneration(enabled){
  if(!enabled)window.continuousSessionId=null;
  localStorage.setItem('igs_continuous_generation',enabled?'on':'off');
  var label=document.getElementById('continuousModeLabel');
  if(label)label.textContent=enabled?i18nText('creator.keep_recent'):i18nText('creator.independent');
  setStatus(enabled?i18nText('creator.keep_recent_status'):i18nText('creator.independent_status'));
}
function initializeCreatorWorkbenches(){
  setCreatorWorkbenchMode('image',localStorage.getItem('igs_image_workbench')||'multi');
  setCreatorWorkbenchMode('video',localStorage.getItem('igs_video_workbench')||'multi');
  var continuous=document.getElementById('chkContinuous');
  if(continuous){
    continuous.checked=localStorage.getItem('igs_continuous_generation')==='on';
    setContinuousGeneration(continuous.checked);
  }
}
var UI_FONT_OPTIONS=[['compact',i18nText('workspace.font_compact')],['standard',i18nText('workspace.font_standard')],['comfortable',i18nText('workspace.font_comfortable')]];
var WORKSPACE_FEATURES=[
  {id:'dashboard',label:i18nText('nav.dashboard'),required:true,selectors:['#navDashboard','.dock-item[data-page="dashboard"]']},
  {id:'generate',label:i18nText('nav.images'),selectors:['#navGen','.dock-item[data-page="generate"]']},
  {id:'video',label:i18nText('nav.video'),selectors:['#navVideo','.dock-item[data-page="video"]']},
  {id:'gallery',label:i18nText('nav.library'),selectors:['#navGallery','.dock-item[data-page="gallery"]']},
  {id:'history',label:i18nText('nav.history'),selectors:['#navHistory','.dock-item[data-page="history"]']},
  {id:'extensions',label:i18nText('nav.extensions'),selectors:['#navExtensions','.dock-item[data-page="extensions"]']},
  {id:'models',label:i18nText('nav.models'),selectors:['.sidebar .nav-item[onclick^="openProviderModal()"]','.dock-item[onclick^="openProviderModal()"]']},
  {id:'prompt',label:i18nText('creator.prompt_optimization'),selectors:['.sidebar .nav-item[onclick*="openProviderModal(\'llm\')"]']},
  {id:'logs',label:i18nText('nav.logs'),selectors:['.sidebar .nav-item[onclick^="openLogModal()"]','.dock-item[onclick^="openLogModal()"]']},
  {id:'refresh',label:i18nText('nav.refresh'),selectors:['.sidebar .nav-item[onclick^="location.reload()"]','.dock-item[onclick^="location.reload()"]']},
  {id:'guide',label:i18nText('nav.guide'),required:true,selectors:['.sidebar .nav-item[onclick^="openOnboardingGuide()"]','.dock-item[onclick^="openOnboardingGuide()"]']},
  {id:'theme',label:i18nText('nav.appearance'),required:true,selectors:['.sidebar .nav-item[onclick^="openThemeModal()"]','.dock-item[onclick^="openThemeModal()"]']}
];
var WORKSPACE_PRESETS={
  full:['dashboard','generate','video','gallery','history','extensions','models','prompt','logs','refresh','theme'],
  create:['dashboard','generate','video','gallery','history','models','prompt','theme'],
  media:['dashboard','gallery','history','extensions','logs','theme'],
  simple:['dashboard','generate','gallery','history','theme']
};
var WORKSPACE_PRESET_LABELS=[['full',i18nText('workspace.mode_full')],['create',i18nText('workspace.mode_create')],['media',i18nText('workspace.mode_media')],['simple',i18nText('workspace.mode_simple')],['custom',i18nText('workspace.mode_custom')]];
function applyFontSize(size){
  if(!UI_FONT_OPTIONS.some(function(option){return option[0]===size;}))size='standard';
  document.body.classList.remove('ui-font-compact','ui-font-standard','ui-font-comfortable');
  document.body.classList.add('ui-font-'+size);
  localStorage.setItem('igs_font_size',size);
  renderPersonalizationControls();
}
function getWorkspaceSelection(mode){
  if(mode==='custom'){
    try{return JSON.parse(localStorage.getItem('igs_workspace_custom')||'[]');}catch(error){return [];}
  }
  return WORKSPACE_PRESETS[mode]||WORKSPACE_PRESETS.full;
}
function applyWorkspace(mode,selection){
  if(!WORKSPACE_PRESET_LABELS.some(function(option){return option[0]===mode;}))mode='full';
  var visible=selection||getWorkspaceSelection(mode);
  WORKSPACE_FEATURES.forEach(function(feature){
    var show=feature.required||visible.indexOf(feature.id)!==-1;
    feature.selectors.forEach(function(selector){
      document.querySelectorAll(selector).forEach(function(element){element.classList.toggle('workspace-hidden',!show);});
    });
  });
  document.querySelectorAll('.dock-sep').forEach(function(separator){
    var before=separator.previousElementSibling;
    var after=separator.nextElementSibling;
    var hasBefore=false;var hasAfter=false;
    while(before){if(!before.classList.contains('workspace-hidden')&&before.classList.contains('dock-item')){hasBefore=true;break;}before=before.previousElementSibling;}
    while(after){if(!after.classList.contains('workspace-hidden')&&after.classList.contains('dock-item')){hasAfter=true;break;}after=after.nextElementSibling;}
    separator.classList.toggle('workspace-hidden',!(hasBefore&&hasAfter));
  });
  localStorage.setItem('igs_workspace_mode',mode);
  renderPersonalizationControls();
}
function setWorkspacePreset(mode){
  if(mode==='custom'){
    var currentMode=localStorage.getItem('igs_workspace_mode')||'full';
    var current=getWorkspaceSelection(currentMode);
    if(!localStorage.getItem('igs_workspace_custom'))localStorage.setItem('igs_workspace_custom',JSON.stringify(current));
  }
  applyWorkspace(mode);
}
function toggleWorkspaceFeature(id,checked){
  var selected=getWorkspaceSelection('custom');
  if(checked&&selected.indexOf(id)===-1)selected.push(id);
  if(!checked)selected=selected.filter(function(item){return item!==id;});
  localStorage.setItem('igs_workspace_custom',JSON.stringify(selected));
  applyWorkspace('custom',selected);
}
function resetWorkspaceSettings(){
  localStorage.removeItem('igs_workspace_custom');
  applyFontSize('standard');
  applyWorkspace('full');
}
function renderPersonalizationControls(){
  var fontContainer=document.getElementById('fontSizeOptions');
  var workspaceContainer=document.getElementById('workspacePresets');
  var featureContainer=document.getElementById('workspaceFeatureList');
  if(!fontContainer||!workspaceContainer||!featureContainer)return;
  var activeFont=localStorage.getItem('igs_font_size')||'standard';
  var activeMode=localStorage.getItem('igs_workspace_mode')||'full';
  var selected=getWorkspaceSelection(activeMode);
  fontContainer.innerHTML=UI_FONT_OPTIONS.map(function(option){return '<button type="button" class="setting-choice '+(option[0]===activeFont?'active':'')+'" onclick="applyFontSize(\''+option[0]+'\')">'+option[1]+'</button>';}).join('');
  workspaceContainer.innerHTML=WORKSPACE_PRESET_LABELS.map(function(option){return '<button type="button" class="setting-choice '+(option[0]===activeMode?'active':'')+'" onclick="setWorkspacePreset(\''+option[0]+'\')">'+option[1]+'</button>';}).join('')+'<button type="button" class="setting-choice" onclick="resetWorkspaceSettings()">' + i18nText('workspace.reset_default') + '</button>';
  featureContainer.innerHTML=WORKSPACE_FEATURES.map(function(feature){var checked=feature.required||selected.indexOf(feature.id)!==-1;return '<label class="workspace-feature '+(feature.required?'is-required':'')+'"><input type="checkbox" '+(checked?'checked ':'')+(feature.required?'disabled ':'')+'onchange="toggleWorkspaceFeature(\''+feature.id+'\',this.checked)"><span>'+feature.label+'</span></label>';}).join('');
}
function openThemeModal(){document.getElementById('themeModal').classList.add('show');renderNavStylePresets();renderPersonalizationControls();renderThemePresets();}
function closeThemeModal(){document.getElementById('themeModal').classList.remove('show');}
function renderThemePresets(){
  var c=document.getElementById('themePresets'); var activeId=localStorage.getItem('igs_theme')||'default'; var h='';
  for(var i=0;i<THEME_PRESETS.length;i++){(function(p){
    var isActive=p.id===activeId; var dots=p.colors.map(function(c){return'<div class="theme-preview-dot" style="background:'+c+';"></div>';}).join('');
    h+='<button type="button" class="theme-preset'+(isActive?' active':'')+'" onclick="applyTheme(\''+p.id+'\')"><div class="theme-preset-head"><span>'+p.name+'</span>'+(isActive?'<strong>'+i18nText('appearance.current')+'</strong>':'')+'</div><p>'+p.description+'</p><div class="theme-preview">'+dots+'</div></button>';
  })(THEME_PRESETS[i]);}
  c.innerHTML=h;
}
function themeHexToRgba(hex, alpha){
  var value=(hex||'').replace('#','');
  if(value.length===3)value=value.split('').map(function(char){return char+char;}).join('');
  if(!/^[0-9a-f]{6}$/i.test(value))return hex;
  return 'rgba('+parseInt(value.slice(0,2),16)+','+parseInt(value.slice(2,4),16)+','+parseInt(value.slice(4,6),16)+','+alpha+')';
}
function applyTheme(id){
  var preset=null;
  for(var i=0;i<THEME_PRESETS.length;i++){if(THEME_PRESETS[i].id===id){preset=THEME_PRESETS[i];break;}}
  if(!preset)return;
  var root=document.documentElement;
  var vars=preset.vars;
  for(var key in vars)root.style.setProperty(key,vars[key]);
  var base=vars['--bg-base'];
  var surface=vars['--bg-surface'];
  var card=vars['--bg-card'];
  var darkIds=['default','graphite','gilded-night','titanium'];
  var isDark=darkIds.indexOf(id)!==-1;
  document.body.classList.toggle('theme-dark',isDark);
  document.body.classList.toggle('theme-light',!isDark);
  document.body.setAttribute('data-theme',id);
  root.style.colorScheme=isDark?'dark':'light';
  root.style.setProperty('--bg-gradient','linear-gradient(145deg,'+base+' 0%,'+surface+' 100%)');
  root.style.setProperty('--bg-card-solid',card);
  root.style.setProperty('--bg-elevated',card);
  root.style.setProperty('--bg-grouped',base);
  root.style.setProperty('--bg-inset',isDark?'rgba(255,255,255,.035)':'rgba(0,0,0,.035)');
  root.style.setProperty('--glass-bg',themeHexToRgba(card,isDark?0.82:0.72));
  root.style.setProperty('--glass-bg-heavy',themeHexToRgba(card,isDark?0.94:0.9));
  root.style.setProperty('--glass-border',isDark?'rgba(255,255,255,.11)':'rgba(255,255,255,.55)');
  root.style.setProperty('--glass-overlay',isDark?'rgba(2,4,9,.66)':'rgba(17,24,39,.38)');
  root.style.setProperty('--border-strong',isDark?'rgba(255,255,255,.16)':'rgba(0,0,0,.12)');
  root.style.setProperty('--border-focus',themeHexToRgba(vars['--accent'],0.48));
  root.style.setProperty('--accent-light',themeHexToRgba(vars['--accent'],isDark?0.16:0.09));
  root.style.setProperty('--glass-shadow',isDark?'0 10px 30px rgba(0,0,0,.28),inset 0 1px rgba(255,255,255,.035)':'0 2px 8px rgba(15,23,42,.05),0 12px 34px rgba(15,23,42,.08)');
  root.style.setProperty('--glass-shadow-lg',isDark?'0 18px 54px rgba(0,0,0,.42),inset 0 1px rgba(255,255,255,.045)':'0 8px 24px rgba(15,23,42,.08),0 24px 64px rgba(15,23,42,.12)');
  root.style.setProperty('--shadow-xs',isDark?'0 1px 2px rgba(0,0,0,.18)':'0 1px 2px rgba(15,23,42,.04)');
  root.style.setProperty('--shadow-sm',isDark?'0 2px 6px rgba(0,0,0,.22)':'0 1px 3px rgba(15,23,42,.06)');
  root.style.setProperty('--shadow-md',isDark?'0 6px 18px rgba(0,0,0,.3)':'0 2px 8px rgba(15,23,42,.08)');
  root.style.setProperty('--shadow-lg',isDark?'0 12px 32px rgba(0,0,0,.36)':'0 4px 16px rgba(15,23,42,.1)');
  root.style.setProperty('--shadow-xl',isDark?'0 18px 48px rgba(0,0,0,.42)':'0 8px 32px rgba(15,23,42,.12)');
  root.style.setProperty('--shadow-2xl',isDark?'0 24px 72px rgba(0,0,0,.52)':'0 16px 48px rgba(15,23,42,.16)');
  localStorage.setItem('igs_theme',id);
  renderThemePresets();
  setStatus(i18nText('theme.switched_prefix') + preset.name);
}
function getUiLanguage(){
  try{
    if(window.GenBoxI18n&&typeof window.GenBoxI18n.language==='function'){
      var lang=window.GenBoxI18n.language();
      if(lang==='en'||lang==='zh-CN')return lang;
    }
  }catch(error){}
  try{
    return localStorage.getItem('igs_language')==='en'?'en':'zh-CN';
  }catch(error2){}
  return document.documentElement&&document.documentElement.lang==='en'?'en':'zh-CN';
}
function initializeUiLanguage(){
  var language=getUiLanguage();
  document.documentElement.lang=language;
  var select=document.getElementById('languageSelect');
  if(select)select.value=language;
  GenBoxI18n.apply(document.body);
}
function setUiLanguage(language){
  GenBoxI18n.setLanguage(language);
  updatePrecisionGuidanceSummary();
}
(function(){
  var initializeUi=function(){
    initializeUiLanguage();
    var s=localStorage.getItem('igs_theme')||'apple-mono';
    if(!THEME_PRESETS.some(function(theme){return theme.id===s;})){s='apple-mono';localStorage.setItem('igs_theme',s);}
    applyTheme(s);
    applyNavStyle(localStorage.getItem('igs_nav_style')||'c');
    applyFontSize(localStorage.getItem('igs_font_size')||'standard');
    applyWorkspace(localStorage.getItem('igs_workspace_mode')||'full');
    initializeCreatorWorkbenches();
    initializeImageWorkbenchLayout();
    // Render the session gallery's empty state before an image is loaded so the
    // reserved lower area communicates its purpose instead of appearing blank.
    renderPrecisionSessionShowcase([]);
    initializeDockAutoHide();
    initializeAppRouting();
    try {
      if(sessionStorage.getItem('igs_reopen_onboarding')==='1'){
        sessionStorage.removeItem('igs_reopen_onboarding');
        setTimeout(openOnboardingGuide,120);
      }
    } catch(error) {}
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initializeUi,{once:true});
  else setTimeout(initializeUi,0);
})();


// ═══════════════════════════════════════════════════════════════════
// 提示词模式：新手/专业
// ═══════════════════════════════════════════════════════════════════
var promptMode = 'newbie';
function setPromptMode(mode){
  promptMode = mode;
  document.getElementById('btnModeNewbie').classList.toggle('btn-secondary', mode==='newbie');
  document.getElementById('btnModeNewbie').classList.toggle('btn-ghost', mode!=='newbie');
  document.getElementById('btnModeNewbie').style.borderColor = mode==='newbie' ? 'var(--accent)' : '';
  document.getElementById('btnModeNewbie').style.color = mode==='newbie' ? 'var(--accent)' : '';
  document.getElementById('btnModePro').classList.toggle('btn-secondary', mode==='pro');
  document.getElementById('btnModePro').classList.toggle('btn-ghost', mode!=='pro');
  document.getElementById('btnModePro').style.borderColor = mode==='pro' ? 'var(--accent)' : '';
  document.getElementById('btnModePro').style.color = mode==='pro' ? 'var(--accent)' : '';
  document.getElementById('promptNewbie').classList.toggle('hidden', mode!=='newbie');
  document.getElementById('promptPro').classList.toggle('hidden', mode!=='pro');
}

function getFinalPrompt(){
  if(promptMode==='pro'){
    var sys = document.getElementById('txtSysPrompt').value.trim();
    var user = document.getElementById('txtUserPrompt').value.trim();
    if(!user) return '';
    return sys ? (sys + '\n\n' + user) : user;
  }
  return document.getElementById('txtPrompt').value.trim();
}


// ═══════════════════════════════════════════════════════════════════
// LLM Provider 设置
// ═══════════════════════════════════════════════════════════════════
var selectedLLMProvider = '';
function openLLMSettings(){
  document.getElementById('llmModal').classList.add('show');
  loadLLMProviders();
}
function closeLLMModal(){ document.getElementById('llmModal').classList.remove('show'); }
function loadLLMProviders(){
  var list = document.getElementById('llmProviderList');
  _authFetch('/api/providers').then(function(r){return r.json();}).then(function(d){
    var providers = (d.providers || []).filter(function(p){ return p.type === 'llm'; });
    if(!providers.length){
      list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:30px;font-size:12px;">' + i18nText('llm.no_provider') + '</div>';
      return;
    }
    var activeId = localStorage.getItem('igs_llm_provider') || '';
    var h = '';
    for(var i=0;i<providers.length;i++){(function(p){
      var isActive = p.id === activeId;
      h += '<div class="llm-provider-card'+(isActive?' active':'')+'" onclick="selectLLMProvider(\''+p.id+'\')">'+
        '<div>'+
          '<div style="font-size:13px;font-weight:600;color:var(--text-primary);">'+escHtml(p.name)+'</div>'+
          '<div style="font-size:11px;color:var(--text-muted);margin-top:2px;">'+escHtml(p.model || p.id)+'</div>'+
        '</div>'+
        (isActive ? '<span style="color:var(--accent);font-size:12px;">✓ 已选</span>' : '<span style="color:var(--text-muted);font-size:11px;">点击选择</span>')+
      '</div>';
    })(providers[i]);}
    list.innerHTML = h;
  });
}
function selectLLMProvider(id){
  localStorage.setItem('igs_llm_provider', id);
  loadLLMProviders();
  setStatus(i18nText('llm.selected_prefix') + id);
}

// ═══════════════════════════════════════════════════════════════════
// LLM 预览优化
// ═══════════════════════════════════════════════════════════════════
var llmPreviewData = null;
var llmOriginalPrompt = ''; // 存储优化前的原始提示词
function previewLLMOptimize(){
  var prompt = document.getElementById('txtPrompt').value.trim();
  if(!prompt){ alert(i18nText('llm.prompt_required')); return; }
  llmOriginalPrompt = prompt; // 保存原始提示词
  var btn = document.getElementById('btnPreviewLLM');
  var box = document.getElementById('llmPreviewBox');
  btn.textContent = i18nText('llm.optimizing');
  btn.disabled = true;
  box.style.display = 'block';
  document.getElementById('llmPreviewError').style.display = 'none';

  var llmId = localStorage.getItem('igs_llm_provider') || undefined;
  _authFetch('/api/llm/optimize', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({prompt: prompt, llm_provider_id: llmId})
  }).then(function(r){ return r.json(); }).then(function(d){
    llmPreviewData = d;
    document.getElementById('llmPreviewOriginal').textContent = d.original;
    document.getElementById('llmPreviewOptimized').textContent = d.optimized;
    if(d.error){
      var errEl = document.getElementById('llmPreviewError');
      errEl.textContent = '⚠️ ' + d.error;
      errEl.style.display = 'block';
    }
    btn.textContent = i18nText('llm.reoptimize');
    btn.disabled = false;
  }).catch(function(e){
    document.getElementById('llmPreviewError').textContent = i18nText('llm.request_failed_prefix') + e.message;
    document.getElementById('llmPreviewError').style.display = 'block';
    btn.textContent = i18nText('creator.optimize');
    btn.disabled = false;
  });
}
function insertLLMPreview(){
  if(!llmPreviewData || !llmPreviewData.optimized) return;
  document.getElementById('txtPrompt').value = llmPreviewData.optimized;
  closeLLMPreview();
  setStatus(i18nText('llm.inserted'));
}
function closeLLMPreview(){
  document.getElementById('llmPreviewBox').style.display = 'none';
  llmPreviewData = null;
}
function undoLLMOptimize(){
  if(llmOriginalPrompt){
    document.getElementById('txtPrompt').value = llmOriginalPrompt;
    llmOriginalPrompt = '';
    setStatus(i18nText('llm.undo_done'));
  }
}


// ═══════════════════════════════════════════════════════════════════
// 图库: 重命名 + 推送图生图
// ═══════════════════════════════════════════════════════════════════
function galleryStartRename() {
  if (!selectedGalleryItems.length) { alert(i18nText('gallery.rename_select')); return; }
  if (selectedGalleryItems.length > 1) { alert(i18nText('gallery.rename_single')); return; }
  var oldId = selectedGalleryItems[0];
  // 提取当前模型名（下划线前的部分）
  var currentName = oldId.split('_')[0] || '';
  var newName = prompt(i18nText('gallery.rename_prompt'), currentName);
  if (!newName || newName === currentName) return;
  _authFetch('/api/gallery/rename', {
    method: 'POST',
    body: JSON.stringify({old_id: oldId, new_name: newName})
  }).then(function(r){
    if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || '重命名失败'); });
    return r.json();
  }).then(function(d){
    setStatus(i18nText('gallery.renamed_prefix') + oldId + ' ? ' + d.new_id);
    var idx = selectedGalleryItems.indexOf(oldId);
    if (idx !== -1) selectedGalleryItems[idx] = d.new_id;
    // Update grouped preview image paths
    Object.keys(groupedPreviews).forEach(function(rp) {
      var group = groupedPreviews[rp];
      for (var i = 0; i < group.images.length; i++) {
        var img = group.images[i];
        if (img.fname && img.fname.indexOf(oldId) === 0) {
          var newFname = d.new_id + img.fname.substring(oldId.length);
          img.fname = newFname;
          img.src = '/api/gallery/image/' + newFname;
        }
      }
    });
    renderGroupedPreviews();
    loadGallery();
  }).catch(function(e){ alert(i18nText('gallery.rename_failed_prefix') + e.message); });
}

function pushGalleryToReference() {
  if (!selectedGalleryItems.length) { alert(i18nText('gallery.push_select')); return; }
  if (selectedGalleryItems.length > 1) { alert(i18nText('gallery.push_single')); return; }
  var itemId = selectedGalleryItems[0];
  // 从 DOM 获取文件名
  var el = document.querySelector('.gallery-item[data-id="' + itemId + '"]');
  var fname = el ? el.getAttribute('data-fname') : '';
  if (!fname) { alert(i18nText('gallery.file_name_missing')); return; }

  setStatus(i18nText('gallery.loading_reference'));
  _authFetch('/api/gallery/image/' + fname + '/base64')
    .then(function(r){
      if (!r.ok) throw new Error('获取图片数据失败');
      return r.json();
    })
    .then(function(d){
      // 设置为参考图并切换到图生图模式
      uploadedImageData = d.data;
      switchSubTab('i2i');
      switchNav('generate', document.getElementById('navGen'));
      // 显示预览
      var p = document.getElementById('uploadPreview');
      p.src = d.data;
      p.classList.remove('hidden');
      // 取消图库选择模式
      toggleGallerySelectMode();
      setStatus(i18nText('gallery.pushed_to_reference'));
    })
    .catch(function(e){ alert(i18nText('gallery.push_failed_prefix') + e.message); });
}

// ═══════════════════════════════════════════════════════════════════
// 视频生成功能
// ═══════════════════════════════════════════════════════════════════
var videoProviders = [];
var currentVideoMode = 'ti2vid';  // ti2vid | i2vid | keyframes
var videoImageRole = 'first_frame';
var videoImages = [];  // base64 array
var kfImages = [];  // keyframes images
var videoPollTimer = null;
var videoElapsedTimer = null;
var videoStartTime = 0;
var currentVideoTaskId = null;
var videoHistoryItems = [];  // session video list
var selectedVideoProviderIds = [];  // multi-provider selection

// 视频分组预览状态
var videoPreviewGroups = {};  // { provider_id: [ {task_id, video_url, video_url_local, prompt, provider_id, ...} ] }
var videoGroupNavIdx = {};    // { provider_id: current index }
var videoActivePollTasks = {}; // { task_id: {provider_id, ...} } 跟踪活跃轮询任务
var videoPreviewPlaceholders = {}; // { provider_id: { cardEl, ... } } 视频生成中的占位卡片

// ═══════════════════════════════════════════════════════════════════
// 视频实时日志
// ═══════════════════════════════════════════════════════════════════
function videoLog(msg, type) {
  var wrap = document.getElementById('videoLogWrap');
  var area = document.getElementById('videoLogArea');
  if (!wrap || !area) return;
  wrap.style.display = 'block';
  var ts = new Date().toLocaleTimeString();
  var colors = { info: 'var(--text-muted)', ok: '#22c55e', warn: '#f59e0b', error: '#ef4444' };
  var color = colors[type] || colors.info;
  var prefix = type === 'ok' ? '\u2714' : type === 'error' ? '\u2718' : type === 'warn' ? '\u26A0' : '\u25B8';
  var line = document.createElement('div');
  line.style.cssText = 'color:' + color + ';';
  line.textContent = '[' + ts + '] ' + prefix + ' ' + msg;
  area.appendChild(line);
  _smartScroll(area);
}

function clearVideoLog() {
  var area = document.getElementById('videoLogArea');
  if (area) area.innerHTML = '';
  var hasActiveTasks = videoPollTimer !== null || Object.keys(videoActivePollTasks || {}).length > 0;
  if (hasActiveTasks) {
    document.querySelectorAll('[id^="vlog_"]').forEach(function(el) { el.innerHTML = ''; });
  } else {
    var section = document.getElementById('videoPerProviderSection');
    if (section) { section.style.display = 'none'; section.innerHTML = ''; }
  }
}

function videoLogProvider(providerId, msg, type) {
  var mini = document.getElementById('vlog_' + providerId);
  if (mini) {
    mini.style.display = 'block';
    var ts = new Date().toLocaleTimeString();
    var colors = { info: 'var(--text-muted)', ok: '#22c55e', warn: '#f59e0b', error: '#ef4444' };
    var color = colors[type] || colors.info;
    var prefix = type === 'ok' ? '\u2714' : type === 'error' ? '\u2718' : type === 'warn' ? '\u26A0' : '\u25B8';
    var line = document.createElement('div');
    line.style.cssText = 'color:' + color + ';';
    // 增加详细度: 时间 + 阶段 + 消息
    var stage = '';
    if (msg.indexOf('创建') !== -1) stage = '[提交] ';
    else if (msg.indexOf('开始') !== -1) stage = '[生成] ';
    else if (msg.indexOf(i18nText('common.done')) !== -1) stage = '[完成] ';
    else if (msg.indexOf(i18nText('status.failed')) !== -1 || msg.indexOf('出错') !== -1) stage = '[错误] ';
    else if (msg.indexOf('轮询') !== -1) stage = '[轮询] ';
    line.textContent = '[' + ts + '] ' + stage + prefix + ' ' + msg;
    mini.appendChild(line);
    _smartScroll(mini);
  }
  videoLog(msg, type);
}

// Video provider drag sort
var videoDragProviderId = null;

function onVideoProviderDragStart(e, pid) {
  videoDragProviderId = pid;
  e.dataTransfer.effectAllowed = 'move';
  document.getElementById('vcard_' + pid).classList.add('dragging');
}

function onVideoProviderDragOver(e, pid) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  document.getElementById('vcard_' + pid).classList.add('drag-over');
}

function onVideoProviderDrop(e, pid) {
  e.preventDefault();
  if (!videoDragProviderId || videoDragProviderId === pid) return;
  var fromId = videoDragProviderId;
  var toId = pid;
  var fromIdx = videoProviders.findIndex(function(p){ return p.id === fromId; });
  var toIdx = videoProviders.findIndex(function(p){ return p.id === toId; });
  if (fromIdx < 0 || toIdx < 0) return;
  var item = videoProviders.splice(fromIdx, 1)[0];
  videoProviders.splice(toIdx, 0, item);
  // Update selectedVideoProviderIds order too
  var selFrom = selectedVideoProviderIds.indexOf(fromId);
  var selTo = selectedVideoProviderIds.indexOf(toId);
  if (selFrom >= 0 && selTo >= 0) {
    selectedVideoProviderIds.splice(selFrom, 1);
    selectedVideoProviderIds.splice(selTo, 0, fromId);
  }
  saveProviderOrder();
  renderVideoProviderCards();
}

function resetVideoDragStyle() {
  videoDragProviderId = null;
  document.querySelectorAll('.dragging, .drag-over').forEach(function(el){ el.classList.remove('dragging', 'drag-over'); });
}

function loadVideoProviders() {
  var container=document.getElementById('videoProviderCards');
  _authFetch('/api/providers').then(function(r){
    if(!r.ok)throw new Error('HTTP '+r.status);
    return r.json();
  }).then(function(data){
    videoProviders = (data.providers || []).filter(function(p){ return p.type === 'video'; });
    if(!Array.isArray(selectedVideoProviderIds))selectedVideoProviderIds=[];
    if((localStorage.getItem('igs_video_workbench')||'multi')==='single'){
      var selectedVideo=selectedVideoProviderIds[0];
      if(!videoProviders.some(function(provider){return provider.id===selectedVideo;}))selectedVideo=videoProviders[0]&&videoProviders[0].id;
      selectedVideoProviderIds=selectedVideo?[selectedVideo]:[];
    }
    renderVideoProviderCards();
    renderCreatorProviderPickers();
  }).catch(function(error){
    videoProviders=[];
    selectedVideoProviderIds=[];
    renderCreatorProviderPickers();
    if(container)container.innerHTML='<div class="empty-state">' + i18nText('video.models_load_failed_hint') + '</div>';
    updateVideoGenerateButton();
    setStatus(i18nText('video.models_load_failed_prefix') + error.message);
    console.error('loadVideoProviders failed',error);
  });
}

// 全局视频设置状态（尺寸/FPS/帧数在全局生效，模型按 Provider 卡片独立）
var videoGlobalSettings = {
  size: '1152x768', fps: 24, frames: 121,
  customW: 1152, customH: 768,
  steps: null, seed: null
};

function getVideoProviderCapabilities(p) {
  var caps = p.model_capabilities || {};
  var allModels = p.models && p.models.length > 0 ? p.models : (p.model ? [p.model] : []);
  var capSet = {};
  // Fallback: derive capabilities from model name
  allModels.forEach(function(m) {
    var mc = caps[m] || [];
    if (mc.length === 0) {
      var ml = m.toLowerCase();
      if (ml.indexOf('t2v') !== -1 && ml.indexOf('i2v') === -1 && ml.indexOf('interpolation') === -1) mc.push('t2v', 'ti2vid');
      if (ml.indexOf('i2v') !== -1) mc.push('i2v');
      if (ml.indexOf('interpolation') !== -1) mc.push('keyframes');
    }
    mc.forEach(function(c) { capSet[c] = true; });
  });
  return capSet;
}

function filterModelsByType(models, providerType) {
  if (!models || !models.length) return models;
  return models.filter(function(m) {
    var ml = m.toLowerCase();
    if (providerType === 'image') {
      // 排除视频模型
      if (ml.indexOf('t2v') !== -1 || ml.indexOf('i2v') !== -1 || ml.indexOf('r2v') !== -1) return false;
      if (ml.indexOf('veo_') !== -1) return false;
      if (ml.indexOf('interpolation') !== -1) return false;
      if (ml.indexOf('video') !== -1 && ml.indexOf('image') === -1) return false;
      // 排除 LLM/文本模型（非生图模型）
      if ((ml.indexOf('gpt-4') !== -1 || ml.indexOf('gpt-5') !== -1 || ml.indexOf('grok-4') !== -1) && ml.indexOf('image') === -1) return false;
      if (ml.indexOf('reasoning') !== -1 || ml.indexOf('chat') !== -1 || ml.indexOf('text-') === 0) return false;
      if (ml === 'auto') return false;
      if (ml.indexOf('codex') !== -1 && ml.indexOf('image') === -1) return false;
      if (ml.indexOf('-mini') !== -1 && ml.indexOf('image') === -1 && ml.indexOf('gemini') === -1) return false;
      return true;
    }
    if (providerType === 'video') {
      // 生视频模型：包含 t2v, i2v, r2v, veo_, interpolation, video
      if (ml.indexOf('t2v') !== -1 || ml.indexOf('i2v') !== -1 || ml.indexOf('r2v') !== -1) return true;
      if (ml.indexOf('veo_') !== -1 || ml.indexOf('veo-') !== -1) return true;
      if (ml.indexOf('interpolation') !== -1) return true;
      if (ml.indexOf('video') !== -1) return true;
      // 主流视频模型厂商关键词
      if (ml.indexOf('seedance') !== -1 || ml.indexOf('doubao') !== -1) return true;
      if (ml.indexOf('sora') !== -1) return true;
      if (ml.indexOf('kling') !== -1) return true;
      if (ml.indexOf('hailuo') !== -1 || ml.indexOf('minimax') !== -1) return true;
      if (ml.indexOf('wanx') !== -1 || ml.indexOf('wan2') !== -1) return true;
      if (ml.indexOf('hunyuan') !== -1) return true;
      if (ml.indexOf('gen-3') !== -1 || ml.indexOf('gen3') !== -1) return true;
      return false;
    }
    if (providerType === 'llm') {
      // LLM 模型：排除图片和视频模型
      if (ml.indexOf('t2v') !== -1 || ml.indexOf('i2v') !== -1 || ml.indexOf('r2v') !== -1) return false;
      if (ml.indexOf('veo_') !== -1) return false;
      if (ml.indexOf('interpolation') !== -1) return false;
      if (ml.indexOf('-4k') !== -1 || ml.indexOf('-2k') !== -1) return false;
      if (ml.indexOf('upsample') !== -1) return false;
      return true;
    }
    return true;
  });
}

function groupVideoModels(models) {
  var groups = {};
  var order = [];
  for (var i = 0; i < models.length; i++) {
    var m = models[i];
    var ml = m.toLowerCase();
    var cat;
    if (ml.indexOf('upsample') !== -1 || (ml.indexOf('-4k') !== -1 && ml.indexOf('veo') === -1)) {
      cat = i18nText('video.category.upsample');
    } else if (ml.indexOf('i2v') !== -1) {
      if (ml.indexOf('veo_3') !== -1) cat = i18nText('video.category.veo3_i2v');
      else if (ml.indexOf('veo_2') !== -1) cat = i18nText('video.category.veo2_i2v');
      else cat = i18nText('video.category.i2v');
    } else if (ml.indexOf('r2v') !== -1) {
      cat = i18nText('video.category.veo3_r2v');
    } else if (ml.indexOf('interpolation') !== -1) {
      cat = i18nText('video.category.interpolation');
    } else if (ml.indexOf('t2v') !== -1 || ml.indexOf('veo_') !== -1) {
      if (ml.indexOf('veo_3') !== -1) cat = i18nText('video.category.veo3_t2v');
      else if (ml.indexOf('veo_2') !== -1) cat = i18nText('video.category.veo2_t2v');
      else cat = i18nText('video.category.t2v');
    } else if (ml.indexOf('seedance') !== -1 || ml.indexOf('doubao') !== -1) {
      cat = i18nText('video.category.seedance');
    } else if (ml.indexOf('kling') !== -1) {
      cat = i18nText('video.category.kling');
    } else if (ml.indexOf('hailuo') !== -1 || ml.indexOf('minimax') !== -1) {
      cat = i18nText('video.category.hailuo');
    } else if (ml.indexOf('wanx') !== -1 || ml.indexOf('wan2') !== -1) {
      cat = i18nText('video.category.wan');
    } else if (ml.indexOf('hunyuan') !== -1) {
      cat = i18nText('video.category.hunyuan');
    } else if (ml.indexOf('sora') !== -1) {
      cat = i18nText('video.category.sora');
    } else {
      cat = i18nText('common.other');
    }
    if (!groups[cat]) { groups[cat] = []; order.push(cat); }
    groups[cat].push(m);
  }
  return { groups: groups, order: order };
}

function groupImageModels(models) {
  var groups = {};
  var order = [];
  for (var i = 0; i < models.length; i++) {
    var m = models[i];
    var ml = m.toLowerCase();
    var cat;
    if (ml.indexOf('imagen') !== -1) {
      cat = 'Imagen';
    } else if (ml.indexOf('gemini-3.1-flash') !== -1 || ml.indexOf('gemini-3_1-flash') !== -1) {
      cat = 'Gemini 3.1 Flash 图片';
    } else if (ml.indexOf('gemini-3.0-pro') !== -1 || ml.indexOf('gemini-3_0-pro') !== -1) {
      cat = 'Gemini 3.0 Pro 图片';
    } else if (ml.indexOf('gemini-2.5') !== -1 || ml.indexOf('gemini-2_5') !== -1) {
      cat = 'Gemini 2.5 Flash 图片';
    } else if (ml.indexOf('gemini') !== -1) {
      cat = 'Gemini 其他';
    } else {
      cat = '其他';
    }
    if (!groups[cat]) { groups[cat] = []; order.push(cat); }
    groups[cat].push(m);
  }
  return { groups: groups, order: order };
}

function buildModelOptsGrouped(models, selectedModel, groupFn) {
  var result = groupFn(models);
  var html = '';
  for (var g = 0; g < result.order.length; g++) {
    var cat = result.order[g];
    var catModels = result.groups[cat];
    html += '<optgroup label="' + escHtml(cat) + ' (' + catModels.length + ')">';
    for (var m = 0; m < catModels.length; m++) {
      var md = catModels[m];
      html += '<option value="' + escAttr(md) + '"' + (selectedModel === md ? ' selected' : '') + '>' + escHtml(md) + '</option>';
    }
    html += '</optgroup>';
  }
  return html;
}

function isModelMatchMode(modelName, mode) {
  var ml = (modelName || '').toLowerCase();
  // 排除纯图片模型（含 image 但不含 video）
  if (ml.indexOf('image') !== -1 && ml.indexOf('video') === -1) return false;
  if (mode === 'ti2vid') {
    // T2V or universal models (no disambiguation needed)
    if (ml.indexOf('t2v') !== -1 && ml.indexOf('i2v') === -1 && ml.indexOf('interpolation') === -1) return true;
    if (ml.indexOf('r2v') !== -1) return true;
    // 含 video 关键词的通用模型（如 agnes-video-v2.0）也匹配
    if (ml.indexOf('video') !== -1) return true;
    return false;
  }
  if (mode === 'i2vid') {
    if (ml.indexOf('i2v') !== -1) return true;
    return false;
  }
  if (mode === 'keyframes') {
    if (ml.indexOf('interpolation') !== -1) return true;
    return false;
  }
  return true;
}

function renderVideoProviderCards() {
  var container = document.getElementById('videoProviderCards');
  if (!container) return;
  if (!videoProviders || videoProviders.length === 0) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px 0;">' + i18nText('video.no_provider') + '</div>';
    return;
  }
  var html = '';
  var activeMode = currentVideoMode || 'ti2vid';
  for (var i = 0; i < videoProviders.length; i++) {
    (function(p, idx) {
      var isSelected = selectedVideoProviderIds.indexOf(p.id) !== -1;
      var cardBg = isSelected ? 'var(--bg-card)' : 'var(--bg-surface)';
      var borderColor = isSelected ? p.color : 'var(--border)';
      var allModels = p.models && p.models.length > 0 ? p.models : (p.model ? [p.model] : []);
      // Filter models by current sub-tab mode
      var filteredModels = allModels.filter(function(m) { return isModelMatchMode(m, activeMode); });
      // If no filtered models, show all (no restriction)
      if (filteredModels.length === 0) filteredModels = allModels;
      var modelOpts = filteredModels.length > 3
        ? buildModelOptsGrouped(filteredModels, '', groupVideoModels)
        : filteredModels.map(function(m){ return '<option value="' + escAttr(m) + '">' + escHtml(m) + '</option>'; }).join('');
      var capSet = getVideoProviderCapabilities(p);
      var capBadges = '';
      if (capSet['t2v'] || capSet['ti2vid']) {
        capBadges += '<span style="font-size:9px;padding:1px 4px;border-radius:3px;background:var(--accent);color:#fff;margin-right:3px;">T2V</span>';
      }
      if (capSet['i2v']) {
        capBadges += '<span style="font-size:9px;padding:1px 4px;border-radius:3px;background:#9b59b6;color:#fff;margin-right:3px;">I2V</span>';
      }
      if (capSet['keyframes']) {
        capBadges += '<span style="font-size:9px;padding:1px 4px;border-radius:3px;background:#e67e22;color:#fff;margin-right:3px;">KF</span>';
      }
      html += '<div id="vcard_' + p.id + '" draggable="true" ondragstart="onVideoProviderDragStart(event, \'' + p.id + '\')" ondragover="onVideoProviderDragOver(event, \'' + p.id + '\')" ondrop="onVideoProviderDrop(event, \'' + p.id + '\')" ondragend="resetVideoDragStyle()" style="margin-bottom:8px;border-radius:8px;border:1px solid ' + borderColor + ';background:' + cardBg + ';padding:10px;transition:all 0.2s;">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">' +
          '<div style="display:flex;align-items:center;gap:6px;">' +
            '<input type="checkbox" id="vcheck_' + p.id + '" onclick="toggleVideoProvider(\'' + p.id + '\')" ' + (isSelected ? 'checked' : '') + ' style="cursor:pointer;width:14px;height:14px;accent-color:' + p.color + ';">' +
            '<span style="width:7px;height:7px;border-radius:50%;background:' + p.color + ';display:inline-block;"></span>' +
            (p.id.indexOf('gemini') !== -1
              ? '<span style="font-size:12px;font-weight:700;background:linear-gradient(90deg,#4285f4,#ea4335,#fbbc04,#34a853);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">Gemini Video</span>' +
                '<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:var(--accent);color:#fff;margin-left:4px;">' + i18nText('video.recommended') + '</span>'
              : '<span style="font-size:12px;font-weight:600;color:var(--text-primary);">' + escHtml(getProviderDisplayName(p.id)) + '</span>' +
                '<span style="font-size:10px;color:var(--text-muted);">' + escHtml(p.name) + '</span>'
            ) +
          '</div>' +
          '<div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">' +
            capBadges +
            '<button onclick="refreshProviderModels(\'' + p.id + '\')" title="' + i18nText('provider.fetch_models') + '" style="font-size:10px;padding:2px 6px;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-secondary);cursor:pointer;">&#8635;</button>' +
          '</div>' +
        '</div>' +
        '<div style="display:flex;gap:4px;margin-bottom:6px;">' +
          '<div style="flex:1;">' +
            '<div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">' + i18nText('creator.model') + ' <span style="color:var(--accent);font-size:9px;">(' + (activeMode === 'ti2vid' ? i18nText('video.t2v') : activeMode === 'i2vid' ? i18nText('video.i2v') : i18nText('video.keyframes')) + ')</span></div>' +
            '<select id="vmodel_' + p.id + '" onchange="onVideoModelChange()" ' + (!isSelected ? 'disabled' : '') + ' style="width:100%;font-size:11px;padding:5px 8px;background:var(--bg-base);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);' + (!isSelected ? 'opacity:0.5;' : '') + '">' +
              (modelOpts || i18nText('provider.no_models_html')) +
            '</select>' +
          '</div>' +
        '</div>' +
      '</div>';
    })(videoProviders[i], i);
  }
  html = '<div style="font-size:10px;color:var(--text-muted);margin-bottom:8px;">' + i18nText('video.multi_submit_hint') + '</div>' + html;
  container.innerHTML = html;
  updateVideoGenerateButton();
  
  // 初始化时根据当前选中的模型更新参数UI
  setTimeout(function() {
    if (selectedVideoProviderIds.length > 0) {
      var firstSelectedId = selectedVideoProviderIds[0];
      var modelSelect = document.getElementById('vmodel_' + firstSelectedId);
      if (modelSelect && modelSelect.value) {
        console.log('[VideoSpec] 初始化模型参数:', modelSelect.value);
        updateVideoUIByModelSpec(modelSelect.value);
      }
    }
  }, 100);
}

function toggleVideoProvider(vpid) {
  var mode=localStorage.getItem('igs_video_workbench')||'multi';
  if(mode==='single') selectedVideoProviderIds=[vpid];
  else {
    var idx = selectedVideoProviderIds.indexOf(vpid);
    if (idx !== -1) selectedVideoProviderIds.splice(idx, 1);
    else selectedVideoProviderIds.push(vpid);
  }
  renderVideoProviderCards();
  renderCreatorProviderPickers();
}

function updateVideoGenerateButton() {
  var btn = document.getElementById('videoGenBtn');
  if (!btn) return;
  var count = selectedVideoProviderIds.length;
  if (count === 0) {
    btn.textContent = i18nText('video.choose_provider');
    btn.disabled = true;
  } else if (count === 1) {
    btn.textContent = i18nText('video.generate');
    btn.disabled = false;
  } else {
    btn.textContent = i18nText('video.submit_multi_prefix') + count + i18nText('video.submit_multi_suffix');
    btn.disabled = false;
  }
}



// ── 视频模型参数约束缓存 ──
var _videoModelSpecCache = {};

/**
 * 获取视频模型参数约束
 * @param {string} modelName - 模型名称
 * @returns {Promise<object>} 模型参数约束
 */
async function getVideoModelSpec(modelName) {
  if (!modelName) return null;
  if (_videoModelSpecCache[modelName]) {
    return _videoModelSpecCache[modelName];
  }
  try {
    const resp = await fetch(`/api/video/model-spec/${encodeURIComponent(modelName)}`);
    if (!resp.ok) return null;
    const data = await resp.json();
    _videoModelSpecCache[modelName] = data.spec;
    return data.spec;
  } catch (e) {
    console.warn('获取视频模型参数失败:', e);
    return null;
  }
}

/**
 * 根据模型参数约束动态更新UI选项
 * @param {string} modelName - 模型名称
 */
async function updateVideoUIByModelSpec(modelName) {
  const spec = await getVideoModelSpec(modelName);
  if (!spec) return;
  
  console.log('[VideoSpec] 模型参数约束:', modelName, spec);
  
  // 更新分辨率选项
  const sizeSelect = document.getElementById('videoSize');
  if (sizeSelect && spec.resolutions && spec.resolutions.length > 0) {
    const currentVal = sizeSelect.value;
    sizeSelect.innerHTML = '';
    
    // 分辨率名称映射
    const resNames = {
      '480p': '480p (SD)', '720p': '720p (HD)', '768p': '768p',
      '1080p': '1080p (Full HD)', '2K': '2K', '4K': '4K (Ultra HD)'
    };
    
    spec.resolutions.forEach(res => {
      const opt = document.createElement('option');
      opt.value = res === '4K' ? '3840x2160' : res === '2K' ? '2048x1024' : 
                  res === '1080p' ? '1920x1080' : res === '720p' ? '1280x720' : 
                  res === '768p' ? '1024x768' : res === '480p' ? '854x480' : res;
      opt.textContent = resNames[res] || res;
      sizeSelect.appendChild(opt);
    });
    
    // 添加自定义选项
    const customOpt = document.createElement('option');
    customOpt.value = 'custom';
    customOpt.textContent = i18nText('common.custom');
    sizeSelect.appendChild(customOpt);
    
    // 尝试保持当前选择
    if ([...sizeSelect.options].some(o => o.value === currentVal)) {
      sizeSelect.value = currentVal;
    }
  }
  
  // 更新帧数范围提示
  const framesInput = document.getElementById('videoFrames');
  if (framesInput && spec.duration_options && spec.fps_options && spec.fps_options.length > 0) {
    const fps = spec.fps_options[0]; // 使用第一个可用FPS
    const minFrames = Math.max(spec.min_frames || 9, fps + 1);
    const maxFrames = spec.max_frames || 441;
    framesInput.min = minFrames;
    framesInput.max = maxFrames;
    framesInput.placeholder = `${minFrames}-${maxFrames}`;
    
    // 更新帧数规则提示
    const ruleHint = framesInput.parentElement.querySelector('.text-xs.text-muted');
    if (ruleHint) {
      ruleHint.textContent = spec.frame_rule || i18nText('video.unlimited');
    }
  }
  
  // 更新FPS选项
  const fpsSelect = document.getElementById('videoFPS');
  if (fpsSelect && spec.fps_options && spec.fps_options.length > 0) {
    const currentFps = fpsSelect.value;
    fpsSelect.innerHTML = '';
    spec.fps_options.forEach(fps => {
      const opt = document.createElement('option');
      opt.value = fps;
      opt.textContent = `${fps} fps`;
      fpsSelect.appendChild(opt);
    });
    if (spec.fps_options.includes(parseInt(currentFps))) {
      fpsSelect.value = currentFps;
    }
  }
  
  // 更新时长按钮
  const durationBtns = document.querySelectorAll('.sub-tab[onclick*="setVideoDuration"]');
  if (durationBtns.length > 0 && spec.duration_options && spec.fps_options) {
    const fps = spec.fps_options[0] || 24;
    durationBtns.forEach(btn => {
      const onclick = btn.getAttribute('onclick');
      const match = onclick && onclick.match(/setVideoDuration\((\d+),(\d+)/);
      if (match) {
        const frames = parseInt(match[1]);
        const duration = Math.round((frames - 1) / fps);
        btn.textContent = `${duration}${i18nText('video.seconds_unit')}`;
      }
    });
  }
  
  // 更新推理步数
  const stepsInput = document.getElementById('videoSteps');
  const stepsGroup = stepsInput ? stepsInput.closest('[data-field="steps"]') || stepsInput.parentElement : null;
  if (stepsGroup) {
    if (spec.inference_steps_range) {
      stepsGroup.style.display = '';
      const [min, max, defaultVal] = spec.inference_steps_range;
      stepsInput.min = min;
      stepsInput.max = max;
      stepsInput.placeholder = `默认${defaultVal}`;
    } else {
      stepsGroup.style.display = 'none';
    }
  }
  
  // 更新负面提示词
  const negPromptInput = document.getElementById('videoNegPrompt');
  const negPromptGroup = negPromptInput ? negPromptInput.closest('[data-field="negPrompt"]') || negPromptInput.parentElement : null;
  if (negPromptGroup) {
    negPromptGroup.style.display = spec.supports_negative_prompt ? '' : 'none';
  }
  
  // 更新种子输入
  const seedInput = document.getElementById('videoSeed');
  const seedGroup = seedInput ? seedInput.closest('[data-field="seed"]') || seedInput.parentElement : null;
  if (seedGroup) {
    seedGroup.style.display = spec.supports_seed ? '' : 'none';
  }
}


function onVideoModelChange(event) {
  // 根据选中的视频模型自动调整推荐参数
  var sel = event && event.target;
  if (!sel) return;
  var val = sel.value || '';
  // 根据模型名推断推荐尺寸
  var sizeMap = {
    'landscape': '1152x768',
    'portrait': '768x1152',
    'square': '1024x1024',
    'four_three': '1024x768',
    'three_four': '768x1024',
    '2k': '2048x1024',
    '4k': '3840x2160',
    'ultra': '1920x1080'
  };
  var sizeSel = document.getElementById('videoSize');
  var customSize = document.getElementById('videoCustomSize');
  var wInput = document.getElementById('videoWidth');
  var hInput = document.getElementById('videoHeight');
  if (sizeSel && wInput && hInput) {
    var matched = false;
    for (var key in sizeMap) {
      if (val.toLowerCase().indexOf(key) !== -1) {
        var parts = sizeMap[key].split('x');
        wInput.value = parts[0];
        hInput.value = parts[1];
        sizeSel.value = 'custom';
        if (customSize) customSize.style.display = 'flex';
        matched = true;
        break;
      }
    }
    if (!matched && val.indexOf('ultra') !== -1) {
      wInput.value = 1920; hInput.value = 1080;
      sizeSel.value = 'custom';
      if (customSize) customSize.style.display = 'flex';
    }
  }
  
  // 根据模型参数约束动态更新UI
  updateVideoUIByModelSpec(val);
}

function onVideoSizeChange() {
  var sel = document.getElementById('videoSize');
  var custom = document.getElementById('videoCustomSize');
  if (sel.value === 'custom') {
    custom.style.display = 'flex';
  } else {
    custom.style.display = 'none';
  }
}

function getVideoDimensions() {
  var sel = document.getElementById('videoSize');
  if (sel.value === 'custom') {
    return {
      width: parseInt(document.getElementById('videoCustomW').value) || 1152,
      height: parseInt(document.getElementById('videoCustomH').value) || 768
    };
  }
  var parts = sel.value.split('x');
  return { width: parseInt(parts[0]), height: parseInt(parts[1]) };
}

function setVideoDuration(frames, fps, el) {
  document.getElementById('videoFrames').value = frames;
  document.getElementById('videoFPS').value = fps;
  // toggle active
  el.parentElement.querySelectorAll('.sub-tab').forEach(function(t){ t.classList.remove('active'); });
  el.classList.add('active');
}

function toggleVideoAdvanced() {
  var adv = document.getElementById('videoAdvanced');
  var chevron = document.getElementById('videoAdvChevron');
  if (adv.style.display === 'none') {
    adv.style.display = 'block';
    chevron.textContent = '▼';
  } else {
    adv.style.display = 'none';
    chevron.textContent = '▶';
  }
}

function refreshProviderModels(vpid) {
  var prov = videoProviders.find(function(p){ return p.id === vpid; });
  if (!prov || !prov.models_url) return;
  var btn = document.querySelector('#vcard_' + vpid + ' button[onclick*="refresh"]');
  if (btn) { btn.textContent = '...'; btn.disabled = true; }
  fetch(prov.models_url).then(function(r){ return r.json(); }).then(function(data) {
    var models = data.models || data.items || [];
    prov.models = models;
    prov.model_capabilities = data.model_capabilities || prov.model_capabilities || {};
    var sel = document.getElementById('vmodel_' + vpid);
    if (sel) {
      sel.innerHTML = models.map(function(m){ return '<option value="' + m + '">' + m + '</option>'; }).join('') || i18nText('provider.no_models_html');
    }
    renderVideoProviderCards();
    setStatus(prov.name + ' ' + i18nText('provider.fetch_success_suffix') + ' (' + models.length + ')');
  }).catch(function(e) {
    if (btn) { btn.innerHTML = '&#8635;'; btn.disabled = false; }
    setStatus(i18nText('provider.fetch_failed') + ': ' + e.message);
  });
}

function switchVideoSubTab(mode) {
  currentVideoMode = mode;

  document.getElementById('vSubTabTi2vid').classList.toggle('active', mode === 'ti2vid');
  document.getElementById('vSubTabI2vid').classList.toggle('active', mode === 'i2vid');
  document.getElementById('vSubTabKeyframes').classList.toggle('active', mode === 'keyframes');

  document.getElementById('videoI2VPanel').style.display = (mode === 'i2vid') ? 'block' : 'none';
  document.getElementById('videoKeyframesPanel').style.display = (mode === 'keyframes') ? 'block' : 'none';

  // 切出 i2vid 时清空残留图片，防止误传
  if (mode !== 'i2vid' && videoImages.length > 0) {
    videoImages = [];
    document.getElementById('videoImagePreview').innerHTML = '';
  }
  if (mode !== 'keyframes' && kfImages.length > 0) {
    kfImages = [];
    document.getElementById('kfImagePreview').innerHTML = '';
  }
  
  // Capability warning: warn if selected providers don't support this mode
  if (mode === 'i2vid') {
    var unsupported = selectedVideoProviderIds.filter(function(vpid) {
      var prov = videoProviders.find(function(p){ return p.id === vpid; });
      if (!prov) return true;
      var caps = getVideoProviderCapabilities(prov);
      return !caps['i2v'];
    });
    if (unsupported.length > 0) {
      setStatus(i18nText('video.unsupported_i2v'));
    }
  }
  if (mode === 'keyframes') {
    var unsupported = selectedVideoProviderIds.filter(function(vpid) {
      var prov = videoProviders.find(function(p){ return p.id === vpid; });
      if (!prov) return true;
      var caps = getVideoProviderCapabilities(prov);
      return !caps['keyframes'];
    });
    if (unsupported.length > 0) {
      setStatus(i18nText('video.unsupported_keyframes'));
    }
  }
  renderVideoProviderCards();
  if(getVisibleAppPage()==='video')updateAppRoute('video');
}

function setVideoImageRole(role, el) {
  videoImageRole = role;
  el.parentElement.querySelectorAll('.sub-tab').forEach(function(t){ t.classList.remove('active'); });
  el.classList.add('active');
}

// 图片上传处理
function handleVideoFileSelect(evt) {
  var files = evt.target.files;
  for (var i = 0; i < files.length; i++) {
    readVideoImageFile(files[i]);
  }
}

function handleVideoDrop(evt) {
  evt.preventDefault();
  evt.currentTarget.classList.remove('dragover');
  var files = evt.dataTransfer.files;
  for (var i = 0; i < files.length; i++) {
    if (files[i].type.startsWith('image/')) readVideoImageFile(files[i]);
  }
}

function readVideoImageFile(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    videoImages.push(e.target.result);
    renderVideoImagePreview();
  };
  reader.readAsDataURL(file);
}

function renderVideoImagePreview() {
  var container = document.getElementById('videoImagePreview');
  container.innerHTML = '';
  videoImages.forEach(function(img, idx) {
    var div = document.createElement('div');
    div.style.cssText = 'position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden;border:1px solid var(--border);';
    div.innerHTML = '<img src="' + img + '" style="width:100%;height:100%;object-fit:cover;">' +
      '<div onclick="removeVideoImage(' + idx + ')" style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,0.7);color:#fff;width:18px;height:18px;border-radius:50%;text-align:center;line-height:18px;font-size:11px;cursor:pointer;">✕</div>' +
      '<div style="position:absolute;bottom:2px;left:2px;font-size:9px;background:rgba(0,0,0,0.7);color:#fff;padding:1px 4px;border-radius:3px;">' + (idx === 0 ? '首' : idx === videoImages.length-1 && videoImages.length > 1 ? '尾' : '图' + (idx+1)) + '</div>';
    container.appendChild(div);
  });
}

function removeVideoImage(idx) {
  videoImages.splice(idx, 1);
  renderVideoImagePreview();
}

// 关键帧图片处理
function handleKfFileSelect(evt) {
  var files = evt.target.files;
  for (var i = 0; i < files.length; i++) {
    readKfImageFile(files[i]);
  }
}

function handleKfDrop(evt) {
  evt.preventDefault();
  evt.currentTarget.classList.remove('dragover');
  var files = evt.dataTransfer.files;
  for (var i = 0; i < files.length; i++) {
    if (files[i].type.startsWith('image/')) readKfImageFile(files[i]);
  }
}

function readKfImageFile(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    kfImages.push(e.target.result);
    renderKfImagePreview();
  };
  reader.readAsDataURL(file);
}

function renderKfImagePreview() {
  var container = document.getElementById('kfImagePreview');
  container.innerHTML = '';
  kfImages.forEach(function(img, idx) {
    var div = document.createElement('div');
    div.style.cssText = 'position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden;border:1px solid var(--border);';
    div.innerHTML = '<img src="' + img + '" style="width:100%;height:100%;object-fit:cover;">' +
      '<div onclick="removeKfImage(' + idx + ')" style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,0.7);color:#fff;width:18px;height:18px;border-radius:50%;text-align:center;line-height:18px;font-size:11px;cursor:pointer;">✕</div>' +
      '<div style="position:absolute;bottom:2px;left:2px;font-size:9px;background:rgba(0,0,0,0.7);color:#fff;padding:1px 4px;border-radius:3px;">帧' + (idx+1) + '</div>';
    container.appendChild(div);
  });
}

function removeKfImage(idx) {
  kfImages.splice(idx, 1);
  renderKfImagePreview();
}

// 从图库取图弹窗
function openVideoPreviewPicker() {
  // 简单实现：直接拉取图库图片列表
  setStatus(i18nText('video.loading_gallery_images'));
  _authFetch('/api/preview/images').then(function(r){ return r.json(); }).then(function(data){
    var items = data.items || [];
    if (items.length === 0) {
      alert(i18nText('video.gallery_empty'));
      return;
    }
    showVideoImagePickerModal(items);
  }).catch(function(e){ alert(i18nText('common.load_failed_prefix') + e.message); });
}

function showVideoImagePickerModal(items) {
  // 创建临时弹窗
  var overlay = document.createElement('div');
  overlay.id = 'videoPickerOverlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
  var box = document.createElement('div');
  box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:20px;max-width:600px;width:90%;max-height:70vh;overflow-y:auto;';
  box.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><h3 style="font-size:14px;font-weight:700;">' + i18nText('video.pick_image_title') + '</h3><button onclick="document.getElementById(\'videoPickerOverlay\').remove()" style="background:none;border:none;color:var(--text-secondary);font-size:18px;cursor:pointer;">?</button></div>' +
    '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;" id="videoPickerGrid"></div>';
  overlay.appendChild(box);
  document.body.appendChild(overlay);

  var grid = document.getElementById('videoPickerGrid');
  items.forEach(function(item) {
    var card = document.createElement('div');
    card.style.cssText = 'border-radius:8px;overflow:hidden;border:2px solid var(--border);cursor:pointer;transition:border-color 0.15s;';
    card.innerHTML = '<img src="' + item.data + '" style="width:100%;height:90px;object-fit:cover;">' +
      '<div style="font-size:9px;color:var(--text-muted);padding:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + (item.prompt || item.filename).substring(0, 30) + '</div>';
    card.onmouseover = function() { card.style.borderColor = 'var(--accent)'; };
    card.onmouseout = function() { card.style.borderColor = 'var(--border)'; };
    card.onclick = function() {
      // 添加到当前图片列表
      if (currentVideoMode === 'keyframes') {
        kfImages.push(item.data);
        renderKfImagePreview();
      } else {
        videoImages.push(item.data);
        renderVideoImagePreview();
      }
      document.getElementById('videoPickerOverlay').remove();
      setStatus(i18nText('video.image_added'));
    };
    grid.appendChild(card);
  });
}

// 生成视频
function startVideoGenerate() {
  var prompt = document.getElementById('videoPrompt').value.trim();
  if (!prompt) { alert(i18nText('video.prompt_required')); return; }

  // Multi-provider: collect selected providers and models
  if (selectedVideoProviderIds.length === 0) {
    alert(i18nText('video.provider_required'));
    return;
  }
  var tasksToGenerate = [];
  for (var vi = 0; vi < selectedVideoProviderIds.length; vi++) {
    (function(vpid) {
      var sel = document.getElementById('vmodel_' + vpid);
      if (!sel || sel.disabled || !sel.value) return;
      tasksToGenerate.push({ provider_id: vpid, model: sel.value });
    })(selectedVideoProviderIds[vi]);
  }
  if (tasksToGenerate.length === 0) {
    alert(i18nText('video.model_required'));
    return;
  }

  var dims = getVideoDimensions();
  var frames = parseInt(document.getElementById('videoFrames').value) || 121;
  var fps = parseInt(document.getElementById('videoFPS').value) || 24;
  var steps = document.getElementById('videoSteps').value ? parseInt(document.getElementById('videoSteps').value) : null;
  var seed = document.getElementById('videoSeed').value ? parseInt(document.getElementById('videoSeed').value) : null;
  var negPrompt = document.getElementById('videoNegPrompt').value.trim() || null;

  // 确定模式和图片
  var mode = currentVideoMode;
  var images = null;
  var imageRole = null;

  // 确定模式和图片 - 按当前子标签决定
  // 注意: ti2vid 模式永不发送图片，避免误传上一轮 i2vid 的残留图片
  if (mode === 'keyframes') {
    if (kfImages.length > 0) images = kfImages;
  } else if (mode === 'i2vid') {
    if (videoImages.length > 0) {
      images = videoImages;
      imageRole = videoImageRole;
    }
  }

  // 8n+1 校验
  if ((frames - 1) % 8 !== 0) {
    var corrected = Math.round((frames - 1) / 8) * 8 + 1;
    if (!confirm(i18nText('video.frames_adjust_confirm_prefix') + frames + i18nText('video.frames_adjust_confirm_middle') + corrected + i18nText('video.frames_adjust_confirm_suffix'))) return;
    frames = corrected;
    document.getElementById('videoFrames').value = frames;
  }

  // 禁用按钮并显示进度
  var btn = document.getElementById('videoGenBtn');
  btn.disabled = true;
  btn.textContent = '\u23F3 \u63D0\u4EA4\u4E2D...';
  document.getElementById('videoProgressBar').style.display = 'block';
  var fill = document.getElementById('videoProgressFill');
  fill.style.width = '0%';
  fill.style.background = '';
  fill.className = 'video-progress-marquee';
  document.getElementById('videoProgressText').textContent = '0%';
  document.getElementById('videoElapsed').textContent = '\u5DF2\u7528\u65F6 0s';
  clearVideoLog();
  renderVideoPerProviderBars();
  // 重置预览分组
  videoPreviewGroups = {};
  videoGroupNavIdx = {};
  videoLog('\u5F00\u59CB\u751F\u6210\u89C6\u9891 - ' + tasksToGenerate.length + ' \u4E2A Provider', 'info');
  videoLog('\u751F\u6210\u8BF7\u6C42\u5DF2\u51C6\u5907', 'info');
  videoLog('\u53C2\u6570: ' + dims.width + 'x' + dims.height + ', ' + frames + '\u5E27, ' + fps + 'fps', 'info');

  // 创建视频预览占位卡片
  createVideoPreviewPlaceholders(tasksToGenerate);

  var submittedCount = 0;
  var totalTasks = tasksToGenerate.length;
  var startTime = Date.now();
  videoStartTime = startTime;
  var allTaskData = [];

  startVideoElapsedTimer();

  function submitNextTask() {
    if (submittedCount >= totalTasks) {
      videoLog('\u5168\u90E8\u63D0\u4EA4\u5B8C\u6210\uFF0C\u5F00\u59CB\u8F6E\u8BE2\u72B6\u6001...', 'info');
      startVideoPolling(allTaskData, startTime);
      return;
    }
    var task = tasksToGenerate[submittedCount];
    var payload = {
      prompt: prompt,
      provider_id: task.provider_id,
      model: task.model,
      mode: mode,
      width: dims.width,
      height: dims.height,
      num_frames: frames,
      frame_rate: fps,
    };
    if (images) payload.image = images;
    if (imageRole) payload.image_role = imageRole;
    if (steps) payload.num_inference_steps = steps;
    if (seed !== null) payload.seed = seed;
    if (negPrompt) payload.negative_prompt = negPrompt;

    submittedCount++;
    btn.textContent = '\u23F3 \u5411 ' + submittedCount + '/' + totalTasks + ' \u63D0\u4EA4...';
    document.getElementById('videoTaskStatus').textContent = '\u5DF2\u63D0\u4EA4 ' + submittedCount + '/' + totalTasks;
    var vprogFill = document.getElementById('vprog_fill_' + task.provider_id);
    if (vprogFill) { vprogFill.style.width = '0%'; vprogFill.classList.remove('complete', 'marquee'); }
    var labelEl = document.getElementById('vprog_label_' + task.provider_id);
    if (labelEl) labelEl.textContent = '\u63D0\u4EA4\u4E2D...';
    videoLogProvider(task.provider_id, '\u5F00\u59CB\u751F\u6210 - \u6A21\u578B: ' + task.model + ', \u89C4\u683C: ' + payload.width + 'x' + payload.height + ', ' + payload.num_frames + '\u5E27', 'info');

  _authFetch('/api/video/generate', {
    method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || '\u8BF7\u6C42\u5931\u8D25'); });
      return r.json();
    }).then(function(data) {
      data.provider_id = task.provider_id;
      allTaskData.push(data);
      videoHistoryItems.unshift(data);
      renderVideoHistory();
      videoLogProvider(task.provider_id, '\u4EFB\u52A1\u5DF2\u521B\u5EFA - ID: ' + data.task_id.substring(0, 12) + '..., \u72B6\u6001: ' + (data.status || '\u63D0\u4EA4\u4E2D'), 'ok');
      var vprogFill2 = document.getElementById('vprog_fill_' + task.provider_id);
      if (vprogFill2) { vprogFill2.classList.add('marquee'); }
      var labelEl2 = document.getElementById('vprog_label_' + task.provider_id);
      if (labelEl2) labelEl2.textContent = '\u7B49\u5F85\u4E2D (\u5DF2\u521B\u5EFA)';
      // Gemini 可能立即返回 completed + video_url，直接渲染预览
      if (data.status === 'completed' && data.video_url) {
        // 移除占位卡片
        removeVideoPreviewPlaceholder(task.provider_id);
        if (!videoPreviewGroups[task.provider_id]) videoPreviewGroups[task.provider_id] = [];
        videoPreviewGroups[task.provider_id].push({
          task_id: data.task_id,
          video_url: data.video_url || '',
          video_url_local: data.video_url_local || '',
          prompt: prompt,
          provider_id: task.provider_id,
          elapsed_seconds: 0,
          status: 'completed',
        });
        videoGroupNavIdx[task.provider_id] = 0;
        renderVideoGroupedPreview();
      }
      if (!currentVideoTaskId) currentVideoTaskId = data.task_id;
      submitNextTask();
    }).catch(function(e) {
      submittedCount--;
      btn.textContent = '\u23F3 \u5411 ' + submittedCount + '/' + totalTasks + ' \u63D0\u4EA4...';
      videoLogProvider(task.provider_id, '\u2718 \u63D0\u4EA4\u5931\u8D25: ' + e.message + ' (\u6A21\u578B: ' + task.model + ')', 'error');
      var labelEl3 = document.getElementById('vprog_label_' + task.provider_id);
      if (labelEl3) labelEl3.textContent = '\u2718 \u63D0\u4EA4\u5931\u8D25';
      if (submittedCount >= totalTasks && allTaskData.length > 0) {
        videoLog('\u5DF2\u63D0\u4EA4\u90E8\u5206\u4EFB\u52A1\uFF0C\u5F00\u59CB\u8F6E\u8BE2 (' + allTaskData.length + '/' + totalTasks + ')...', 'warn');
        startVideoPolling(allTaskData, startTime);
      } else if (allTaskData.length === 0) {
        stopVideoElapsedTimer();
        btn.disabled = false;
        btn.textContent = '\u{1F680} \u751F\u6210\u89C6\u9891';
      }
    });
  }

  submitNextTask();
}



function startVideoElapsedTimer() {
  stopVideoElapsedTimer();
  videoElapsedTimer = setInterval(function() {
    var elapsed = Math.round((Date.now() - videoStartTime) / 1000);
    var el = document.getElementById('videoElapsed');
    if (el) el.textContent = '\u5DF2\u7528\u65F6 ' + elapsed + 's';
  }, 1000);
}

function stopVideoElapsedTimer() {
  if (videoElapsedTimer) { clearInterval(videoElapsedTimer); videoElapsedTimer = null; }
}

function startVideoPolling(allTaskData, startTime) {
  if (!startTime) startTime = Date.now();
  videoStartTime = startTime;
  if (videoPollTimer) clearInterval(videoPollTimer);

  videoActivePollTasks = {};
  videoProgressMaxLogged = {};
  videoProgressStageLogged = {};

  allTaskData.forEach(function(item) {
    if (item.task_id && item.status !== 'completed' && item.status !== 'failed' && item.status !== 'error') {
      videoActivePollTasks[item.task_id] = { provider_id: item.provider_id || 'unknown' };
    }
  });

  var completedCount = 0;
  var totalToComplete = allTaskData.length;
  var pollRound = 0;
  var taskProgressMap = {};  // task_id -> progress

  function updateGlobalProgress() {
    var activeIds = Object.keys(videoActivePollTasks);
    var activeCount = activeIds.length;
    var totalPct = 0;
    var count = 0;
    activeIds.forEach(function(atid) {
      var p = taskProgressMap[atid];
      if (p !== undefined) { totalPct += p; count++; }
    });
    var avg = count > 0 ? Math.round(totalPct / count) : 0;
    var fill = document.getElementById('videoProgressFill');
    if (fill) {
      fill.style.width = avg + '%';
      fill.style.background = '';
      fill.className = avg >= 100 && activeCount === 0 ? 'video-progress-solid' : 'video-progress-marquee';
    }
    document.getElementById('videoProgressText').textContent = avg + '%';
  }

  videoPollTimer = setInterval(function() {
    var activeIds = Object.keys(videoActivePollTasks);
    pollRound++;

    if (activeIds.length === 0) {
      clearInterval(videoPollTimer);
      videoPollTimer = null;
      stopVideoElapsedTimer();
      var fillDone = document.getElementById('videoProgressFill');
      if (fillDone) { fillDone.style.background = ''; fillDone.className = 'video-progress-solid'; fillDone.style.width = '100%'; }
      document.getElementById('videoProgressText').textContent = '100%';
      var btn = document.getElementById('videoGenBtn');
      btn.disabled = false;
      btn.textContent = '\u{1F680} \u751F\u6210\u89C6\u9891';
      updateVideoGenerateButton();
      var totalElapsed = Math.round((Date.now() - startTime) / 1000);
      setStatus('\u89C6\u9891\u751F\u6210\u5B8C\u6210! (' + completedCount + '/' + totalToComplete + ' \u4E2A\u4EFB\u52A1, \u5171\u8017\u65F6 ' + totalElapsed + 's)');
      videoLog('\u2714 \u5168\u90E8\u4EFB\u52A1\u5B8C\u6210! \u5171\u8017\u65F6 ' + totalElapsed + 's', 'ok');
      return;
    }

    videoLog('\u8F6E\u8BE2 #' + pollRound + ' - \u8FDB\u884C\u4E2D: ' + activeIds.length + ', \u5B8C\u6210: ' + completedCount + '/' + totalToComplete, 'info');

    activeIds.forEach(function(tid) {
      _authFetch('/api/video/status/' + tid).then(function(r) {
        if (!r.ok) return;
        return r.json();
      }).then(function(data) {
        if (!data) return;
        var status = data.status || '';
        var progress = data.progress || 0;
        var elapsed = data.elapsed_seconds || 0;
        var provId = videoActivePollTasks[tid] ? videoActivePollTasks[tid].provider_id : 'unknown';

        taskProgressMap[tid] = progress;
        updateGlobalProgress();

        // 更新视频占位卡片状态
        updateVideoPreviewPlaceholderStatus(provId, '[' + (data.stage || 'processing') + '] ' + Math.round(progress) + '%', progress);

        var progFillEl = document.getElementById('vprog_fill_' + provId);
        if (progFillEl) {
          progFillEl.style.width = progress + '%';
          progFillEl.classList.remove('complete');
          progFillEl.classList.add('marquee');
        }
        var progLabel = document.getElementById('vprog_label_' + provId);
        if (progLabel) {
          var stageLabel = data.stage || 'processing';
          progLabel.textContent = '[' + stageLabel + '] ' + Math.round(progress) + '%' + (elapsed ? ' (' + Math.round(elapsed) + 's)' : '');
        }
        // 每 20% 或 stage 变化时记录详细日志
        if (!videoProgressMaxLogged) videoProgressMaxLogged = {};
        var prev = videoProgressMaxLogged[provId] || -1;
        var stageNow = data.stage || '';
        var prevStage = videoProgressStageLogged ? videoProgressStageLogged[provId] || '' : '';
        if (!videoProgressStageLogged) videoProgressStageLogged = {};
        if (progress >= 100 || (progress - prev >= 20) || (stageNow && stageNow !== prevStage)) {
          videoProgressMaxLogged[provId] = Math.max(prev, Math.floor(progress / 20) * 20);
          videoProgressStageLogged[provId] = stageNow;
          var extras = '';
          if (data.current_step && data.total_steps) extras = ' (step ' + data.current_step + '/' + data.total_steps + ')';
          else if (data.progress_detail) extras = ' ' + data.progress_detail;
          if (status !== 'completed' && status !== 'failed' && status !== 'error' && status !== 'cancelled' && status !== 'timeout') {
            videoLogProvider(provId, '处理中 ' + Math.round(progress) + '% (' + stageLabel + ')' + extras + ' ' + Math.round(elapsed) + 's', 'info');
          }
        }

        if (status === 'completed') {
          delete videoActivePollTasks[tid];
          completedCount++;
          if (progFillEl) { progFillEl.style.width = '100%'; progFillEl.classList.remove('marquee'); progFillEl.classList.add('complete'); }
          var labelCompleted = document.getElementById('vprog_label_' + provId);
          if (labelCompleted) labelCompleted.textContent = '\u2714 \u5B8C\u6210 ' + Math.round(elapsed) + 's';
          videoLogProvider(provId, '\u751F\u6210\u5B8C\u6210! \u8017\u65F6 ' + Math.round(elapsed) + 's', 'ok');

          // 移除占位卡片
          removeVideoPreviewPlaceholder(provId);

          if (!videoPreviewGroups[provId]) videoPreviewGroups[provId] = [];
          videoPreviewGroups[provId].push({
            task_id: tid,
            video_url: data.video_url || '',
            video_url_local: data.video_url_local || '',
            prompt: data.prompt || '',
            provider_id: provId,
            elapsed_seconds: elapsed,
            status: 'completed',
          });
          videoGroupNavIdx[provId] = 0;
          renderVideoGroupedPreview();

          for (var hi = 0; hi < videoHistoryItems.length; hi++) {
            if (videoHistoryItems[hi].task_id === tid) {
              videoHistoryItems[hi] = data;
              break;
            }
          }
          renderVideoHistory();
        } else if (status === 'failed' || status === 'error' || status === 'cancelled' || status === 'timeout') {
          delete videoActivePollTasks[tid];
          completedCount++;
          var errMsg = data.error || status;
          var progFillFail = document.getElementById('vprog_fill_' + provId);
          if (progFillFail) { progFillFail.style.width = '0%'; progFillFail.classList.remove('marquee', 'complete'); }
          var labelFailed = document.getElementById('vprog_label_' + provId);
          if (labelFailed) labelFailed.textContent = '\u2718 \u5931\u8D25: ' + errMsg.substring(0, 30);
          videoLogProvider(provId, '\u2718 \u751F\u6210\u5931\u8D25: ' + errMsg + ' (\u8017\u65F6 ' + Math.round(elapsed) + 's)', 'error');

          // 移除占位卡片
          removeVideoPreviewPlaceholder(provId);

          if (!videoPreviewGroups[provId]) videoPreviewGroups[provId] = [];
          videoPreviewGroups[provId].push({
            task_id: tid,
            video_url: '',
            video_url_local: '',
            prompt: data.prompt || '',
            provider_id: provId,
            elapsed_seconds: elapsed,
            status: status,
            error: errMsg,
          });
          renderVideoGroupedPreview();

          for (var hi2 = 0; hi2 < videoHistoryItems.length; hi2++) {
            if (videoHistoryItems[hi2].task_id === tid) {
              videoHistoryItems[hi2] = data;
              break;
            }
          }
          renderVideoHistory();
        }
      }).catch(function(e) { /* single poll failure */ });
    });
  }, 5000);
}



function renderVideoHistory() {
  var container = document.getElementById('videoHistoryList');
  if (videoHistoryItems.length === 0) {
    container.innerHTML = '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:20px;">' + i18nText('video.none') + '</div>';
    return;
  }
  // Group by provider_id
  var groups = {};
  videoHistoryItems.forEach(function(item) {
    var pid = item.provider_id || 'unknown';
    if (!groups[pid]) groups[pid] = [];
    groups[pid].push(item);
  });
  
  var html = '';
  Object.keys(groups).forEach(function(pid) {
    var items = groups[pid];
    var prov = videoProviders.find(function(p){ return p.id === pid; });
    var provColor = prov ? prov.color : 'var(--accent)';
    var provName = prov ? (prov.name || pid) : pid;
    html += '<div style="font-size:10px;font-weight:600;color:' + provColor + ';padding:4px 0 2px 0;margin-top:4px;">' + provName + ' (' + items.length + ')</div>';
    items.forEach(function(item) {
      var promptShort = (item.prompt || '').substring(0, 40);
      var statusIcon = item.status === 'completed' ? '✅' : '⏳';
      var elapsed = item.elapsed_seconds ? Math.round(item.elapsed_seconds) + 's' : '';
      var taskId = item.task_id ? item.task_id.substring(0, 8) : '';
      html += '<div onclick="playVideoItem(\'' + (item.video_url_local || item.video_url || '') + '\')" style="background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;padding:6px 8px;margin-bottom:4px;cursor:pointer;transition:border-color 0.15s;" onmouseover="this.style.borderColor=\'' + provColor + '\';" onmouseout="this.style.borderColor=\'var(--border)\';">' +
        '<div style="display:flex;align-items:center;gap:4px;">' +
          '<span>' + statusIcon + '</span>' +
          '<span style="font-size:10px;color:var(--text-primary);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + promptShort + '</span>' +
          '<span style="font-size:9px;color:var(--text-muted);">' + elapsed + '</span>' +
        '</div>' +
      '</div>';
    });
  });
  container.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════
// 各模型独立进度条和日志（生成按钮下方）
// ═══════════════════════════════════════════════════════════════════
function renderVideoPerProviderBars() {
  var container = document.getElementById('videoPerProviderSection');
  if (!container) return;
  var html = '';
  selectedVideoProviderIds.forEach(function(pid) {
    var prov = videoProviders.find(function(p) { return p.id === pid; });
    var name = prov ? (prov.name || pid) : pid;
    var color = prov ? prov.color : 'var(--accent)';
    html +=
      '<div style="margin-bottom:14px;border:1px solid var(--border);border-radius:8px;padding:10px;background:var(--bg-surface);">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">' +
          '<span style="font-size:12px;font-weight:700;color:' + color + ';">' + name + '</span>' +
          '<span id="vprog_label_' + pid + '" style="font-size:10px;color:var(--text-muted);">等待中...</span>' +
        '</div>' +
        '<div style="background:var(--border);border-radius:4px;overflow:hidden;height:6px;margin-bottom:6px;">' +
          '<div class="vprog-fill" id="vprog_fill_' + pid + '" style="height:100%;width:0%;"></div>' +
        '</div>' +
        '<div id="vlog_' + pid + '" style="max-height:90px;overflow-y:auto;background:var(--bg-base);border:1px solid var(--border);border-radius:4px;padding:5px 7px;font-family:monospace;font-size:10px;line-height:1.6;color:var(--text-muted);">' +
          '<div style="color:var(--text-muted);">[系统] 等待提交...</div>' +
        '</div>' +
      '</div>';
  });
  container.innerHTML = html;
  container.style.display = 'block';
}

// ═══════════════════════════════════════════════════════════════════
// 视频分组预览渲染（仿图片实时预览）
// ═══════════════════════════════════════════════════════════════════
function renderVideoGroupedPreview() {
  var container = document.getElementById('videoPreviewResults');
  var emptyEl = document.getElementById('videoPreviewEmpty');
  var countEl = document.getElementById('videoResultCount');
  if (!container) return;

  var allItems = [];
  Object.keys(videoPreviewGroups).forEach(function(pid) {
    allItems = allItems.concat(videoPreviewGroups[pid]);
  });

  if (allItems.length === 0) {
    container.style.display = 'none';
    if (emptyEl) emptyEl.style.display = 'flex';
    if (countEl) countEl.textContent = '';
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';
  container.style.display = 'flex';
  if (countEl) countEl.textContent = allItems.length + ' ' + i18nText('video.result_count_unit');
  container.innerHTML = '';

  var groupKeys = Object.keys(videoPreviewGroups);

  for (var g = 0; g < groupKeys.length; g++) {
    (function(provId, items) {
      var prov = videoProviders.find(function(p){ return p.id === provId; });
      var provColor = prov ? prov.color : '#5b8def';
      var provName = prov ? (prov.display_name || prov.name || provId) : provId;
      var navIdx = videoGroupNavIdx[provId] || 0;

      var groupCard = document.createElement('div');
      groupCard.className = 'fade-in';
      groupCard.style.cssText = 'padding:14px;background:var(--bg-surface);border-radius:12px;border:1px solid var(--border);';

      // ── 标题栏 ──
      var header = document.createElement('div');
      header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;';
      var completedItems = items.filter(function(i){ return i.status === 'completed'; });
      var failedItems = items.filter(function(i){ return i.status !== 'completed'; });
      var statusText = '';
      if (failedItems.length > 0) statusText += '<span style="color:#ef4444;">✗ ' + failedItems.length + ' 失败</span> ';
      if (completedItems.length > 0) statusText += '<span style="color:#22c55e;">✓ ' + completedItems.length + ' 完成</span>';

      header.innerHTML =
        '<div style="display:flex;align-items:center;gap:8px;">' +
          '<span style="width:8px;height:8px;border-radius:50%;background:' + provColor + ';display:inline-block;flex-shrink:0;"></span>' +
          '<span style="font-weight:700;font-size:13px;color:var(--text-primary);">' + escHtml(provName) + '</span>' +
          '<span style="font-size:10px;color:var(--text-muted);">' + statusText + '</span>' +
        '</div>';
      if (completedItems.length > 1) {
        header.innerHTML +=
          '<div style="display:flex;align-items:center;gap:6px;">' +
            '<span id="vgrp_cnt_' + provId + '" style="font-size:11px;color:var(--text-muted);">' + (navIdx+1) + ' / ' + completedItems.length + '</span>' +
            '<div style="display:flex;gap:4px;">' +
              '<button onclick="videoGroupNav(\'' + provId + '\',-1)" style="width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;">‹</button>' +
              '<button onclick="videoGroupNav(\'' + provId + '\',1)" style="width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;">›</button>' +
            '</div>' +
          '</div>';
      }
      groupCard.appendChild(header);

      // ── 视频播放区域 ──
      var viewerWrap = document.createElement('div');
      viewerWrap.id = 'vgrp_viewer_' + provId;
      viewerWrap.style.cssText = 'position:relative;display:flex;align-items:center;justify-content:center;min-height:200px;overflow:hidden;border-radius:10px;background:#000;';

      function renderVideoItem() {
        viewerWrap.innerHTML = '';
        var cur = completedItems[videoGroupNavIdx[provId] || 0];
        if (!cur) { viewerWrap.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:20px;">' + i18nText('video.no_completed') + '</div>'; return; }

        var cntEl = document.getElementById('vgrp_cnt_' + provId);
        if (cntEl) cntEl.textContent = ((videoGroupNavIdx[provId]||0)+1) + ' / ' + completedItems.length;

        if (completedItems.length > 1) {
          var btnP = document.createElement('button');
          btnP.style.cssText = 'position:absolute;left:8px;top:50%;transform:translateY(-50%);z-index:5;width:34px;height:34px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
          btnP.innerHTML = '‹';
          btnP.onclick = function(e){ e.stopPropagation(); videoGroupNav(provId,-1); };
          viewerWrap.appendChild(btnP);

          var btnN = document.createElement('button');
          btnN.style.cssText = 'position:absolute;right:8px;top:50%;transform:translateY(-50%);z-index:5;width:34px;height:34px;border-radius:50%;border:none;background:rgba(0,0,0,0.6);color:#fff;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
          btnN.innerHTML = '›';
          btnN.onclick = function(e){ e.stopPropagation(); videoGroupNav(provId,1); };
          viewerWrap.appendChild(btnN);
        }

        var videoEl = document.createElement('video');
        var videoSrc = cur.video_url_local || cur.video_url;
        if (!videoSrc) {
          viewerWrap.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:20px;text-align:center;">' + i18nText('video.missing_url') + '</div>';
          return;
        }
        videoEl.src = videoSrc;
        videoEl.controls = true;
        videoEl.loop = true;
        videoEl.style.cssText = 'width:100%;max-height:40vh;border-radius:8px;background:#000;';
        viewerWrap.appendChild(videoEl);

        // 自动播放
        videoEl.play().catch(function(){});
      }
      renderVideoItem();
      groupCard.appendChild(viewerWrap);

      // ── 操作按钮 ──
      var btnRow = document.createElement('div');
      btnRow.style.cssText = 'display:flex;gap:6px;margin-top:8px;';
      var curItem = completedItems[videoGroupNavIdx[provId] || 0];
      if (curItem) {
        var videoSrc = curItem.video_url_local || curItem.video_url || '';
        btnRow.innerHTML =
          '<button class="btn-secondary" style="flex:1;font-size:11px;padding:6px;" onclick="downloadVideoFromSrc(\'' + videoSrc.replace(/'/g, "\\'") + '\')">⬇️ 下载</button>' +
          '<button class="btn-secondary" style="flex:1;font-size:11px;padding:6px;" onclick="pushVideoToGalleryFromSrc(\'' + videoSrc.replace(/'/g, "\\'") + '\')">🖼 推到图库</button>';
      }
      groupCard.appendChild(btnRow);

      // ── 耗时信息 ──
      if (curItem && curItem.elapsed_seconds) {
        var info = document.createElement('div');
        info.style.cssText = 'font-size:10px;color:var(--text-muted);margin-top:6px;text-align:right;';
        info.textContent = '⏱ ' + Math.round(curItem.elapsed_seconds) + 's';
        groupCard.appendChild(info);
      }

      // ── 失败信息 ──
      if (failedItems.length > 0) {
        failedItems.forEach(function(fi) {
          var errDiv = document.createElement('div');
          errDiv.style.cssText = 'font-size:11px;color:#ef4444;background:rgba(239,68,68,0.08);padding:6px 10px;border-radius:6px;margin-top:6px;display:flex;align-items:flex-start;gap:6px;';
          errDiv.innerHTML = '<span style="flex-shrink:0;">?</span><span>' + escHtml(fi.error || i18nText('video.generation_failed')) + '</span>';
          groupCard.appendChild(errDiv);
        });
      }

      // ── 缩略图条 ──
      if (completedItems.length > 1) {
        var thumbRow = document.createElement('div');
        thumbRow.id = 'vgrp_thumbs_' + provId;
        thumbRow.style.cssText = 'display:flex;gap:8px;margin-top:10px;overflow-x:auto;padding-bottom:2px;';
        for (var ti = 0; ti < completedItems.length; ti++) {
          (function(ti) {
            var tItem = completedItems[ti];
            var isActive = ti === (videoGroupNavIdx[provId] || 0);
            var wrap = document.createElement('div');
            wrap.style.cssText = 'width:80px;height:50px;border-radius:6px;overflow:hidden;cursor:pointer;flex-shrink:0;border:2px solid ' + (isActive ? provColor : 'transparent') + ';opacity:' + (isActive ? '1' : '0.5') + ';transition:all 0.15s;position:relative;background:#000;';
            var vid = document.createElement('video');
            vid.src = tItem.video_url_local || tItem.video_url;
            vid.muted = true;
            vid.style.cssText = 'width:100%;height:100%;object-fit:cover;';
            wrap.appendChild(vid);
            wrap.onclick = function() {
              videoGroupNavIdx[provId] = ti;
              renderVideoItem();
              // 更新缩略图高亮
              var thumbs = thumbRow.children;
              for (var k = 0; k < thumbs.length; k++) {
                thumbs[k].style.borderColor = k === ti ? provColor : 'transparent';
                thumbs[k].style.opacity = k === ti ? '1' : '0.5';
              }
              var cntEl2 = document.getElementById('vgrp_cnt_' + provId);
              if (cntEl2) cntEl2.textContent = (ti+1) + ' / ' + completedItems.length;
            };
            thumbRow.appendChild(wrap);
          })(ti);
        }
        groupCard.appendChild(thumbRow);
      }

      container.appendChild(groupCard);
    })(groupKeys[g], videoPreviewGroups[groupKeys[g]]);
  }
}

// 全局视频组导航
function videoGroupNav(provId, dir) {
  var items = videoPreviewGroups[provId];
  if (!items || items.length === 0) return;
  var completedItems = items.filter(function(i){ return i.status === 'completed'; });
  if (completedItems.length === 0) return;
  var cur = videoGroupNavIdx[provId] || 0;
  videoGroupNavIdx[provId] = (cur + dir + completedItems.length) % completedItems.length;
  renderVideoGroupedPreview();
}

// 从指定 src 下载视频
function downloadVideoFromSrc(src) {
  if (!src) { alert(i18nText('video.no_downloadable')); return; }
  var a = document.createElement('a');
  a.href = src;
  a.download = 'video_' + Date.now() + '.mp4';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// 从指定 src 推到图库
function pushVideoToGalleryFromSrc(src) {
  if (!src) return;
  var video = document.createElement('video');
  video.src = src;
  video.currentTime = 0.5;
  video.onloadeddata = function() {
    var canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    var b64 = canvas.toDataURL('image/png');
    _authFetch('/api/gallery/rename', {
      method: 'POST',
      body: JSON.stringify({ old_name: 'video_frame', new_name: 'video_frame_' + Date.now() }),
    }).catch(function(){});
    alert(i18nText('video.first_frame_pushed'));
  };
  video.load();
}

function playVideoItem(url) {
  if (!url) return;
  // 如果分组预览中有这个视频，直接定位到对应组
  var found = false;
  Object.keys(videoPreviewGroups).forEach(function(pid) {
    videoPreviewGroups[pid].forEach(function(item, idx) {
      if ((item.video_url_local || item.video_url) === url) {
        videoGroupNavIdx[pid] = idx;
        found = true;
      }
    });
  });
  if (found) {
    renderVideoGroupedPreview();
    return;
  }
  // 兼容旧逻辑
  var emptyEl = document.getElementById('videoPreviewEmpty');
  if (emptyEl) emptyEl.style.display = 'none';
  var container = document.getElementById('videoPreviewResults');
  container.style.display = 'flex';
  container.innerHTML = '<div style="width:100%;border-radius:10px;overflow:hidden;background:#000;"><video src="' + url + '" controls loop autoplay style="width:100%;max-height:40vh;border-radius:10px;"></video></div>';
}

function downloadVideo() {
  // 从分组预览获取当前视频 src
  var src = '';
  Object.keys(videoPreviewGroups).forEach(function(pid) {
    var items = videoPreviewGroups[pid].filter(function(i){ return i.status === 'completed'; });
    var idx = videoGroupNavIdx[pid] || 0;
    if (items[idx]) src = items[idx].video_url_local || items[idx].video_url || '';
  });
  if (!src) { alert(i18nText('video.no_downloadable')); return; }
  downloadVideoFromSrc(src);
}

function pushVideoToGallery() {
  var src = '';
  Object.keys(videoPreviewGroups).forEach(function(pid) {
    var items = videoPreviewGroups[pid].filter(function(i){ return i.status === 'completed'; });
    var idx = videoGroupNavIdx[pid] || 0;
    if (items[idx]) src = items[idx].video_url_local || items[idx].video_url || '';
  });
  if (!src) { alert(i18nText('video.none')); return; }
  pushVideoToGalleryFromSrc(src);
}

// ═══════════════════════════════════════════════════════════════════
// 视频生成占位卡片（loading 动效）
// ═══════════════════════════════════════════════════════════════════
function createVideoPreviewPlaceholders(tasks) {
  var container = document.getElementById('videoPreviewResults');
  var emptyEl = document.getElementById('videoPreviewEmpty');
  if (!container) return;
  if (emptyEl) emptyEl.style.display = 'none';
  container.style.display = 'flex';
  container.innerHTML = '';

  // 清理旧占位符
  videoPreviewPlaceholders = {};

  for (var i = 0; i < tasks.length; i++) {
    var task = tasks[i];
    var prov = videoProviders.find(function(p){ return p.id === task.provider_id; });
    var provColor = prov ? prov.color : '#5b8def';
    var provName = prov ? (prov.display_name || prov.name || task.provider_id) : task.provider_id;

    var card = document.createElement('div');
    card.className = 'fade-in prev-card generating';
    card.id = 'vprev_ph_' + task.provider_id;

    // 占位区：转圈动效（和图片预览一样的 4:3 比例）
    var ph = document.createElement('div');
    ph.className = 'prev-placeholder';
    ph.innerHTML = '<div class="spinner"></div><div class="ph-text">' + escHtml(provName) + '</div>';
    card.appendChild(ph);

    // 底部信息
    var footer = document.createElement('div');
    footer.className = 'prev-footer';
    footer.innerHTML =
      '<div style="display:flex;align-items:center;gap:5px;">' +
        '<span class="provider-dot" style="background:' + provColor + ';"></span>' +
        '<span class="provider-name">' + escHtml(provName) + '</span>' +
        '<span style="font-size:9px;color:var(--text-muted);">' + escHtml(task.model) + '</span>' +
      '</div>' +
      '<span class="elapsed-badge" id="vph_elapsed_' + task.provider_id + '">排队中</span>';
    card.appendChild(footer);

    container.appendChild(card);

    videoPreviewPlaceholders[task.provider_id] = {
      cardEl: card,
      provColor: provColor,
      provName: provName,
    };
  }
}

function removeVideoPreviewPlaceholder(provId) {
  var ph = videoPreviewPlaceholders[provId];
  if (ph && ph.cardEl && ph.cardEl.parentNode) {
    ph.cardEl.remove();
  }
  delete videoPreviewPlaceholders[provId];
}

function updateVideoPreviewPlaceholderStatus(provId, text, progress) {
  var statusEl = document.getElementById('vph_elapsed_' + provId);
  if (statusEl) statusEl.textContent = text;
}
