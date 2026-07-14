
// ═══════════════════════════════════════════════════════════════════
// 全局状态
// ═══════════════════════════════════════════════════════════════════
var allProviders = [];
var selectedProviders = [];
var currentMode = 't2i';
var uploadedImageData = null;
var continuousSessionId = null;
var currentResults = {};   // 当前生成结果，用于灯箱/对比
var currentGroupTimings = {}; // 当前分组耗时 {pid: {total, images: []}}
var quickPrompts = {};
var lastGenContext = null; // 上次生图上下文，用于单模型重试

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
      var f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    });
  }

  // 拖拽上传 (变形模式)
  var zoneVar = document.getElementById('uploadZoneVar');
  if (zoneVar) {
    zoneVar.addEventListener('dragover', function(e){ e.preventDefault(); zoneVar.classList.add('dragover'); });
    zoneVar.addEventListener('dragleave', function(){ zoneVar.classList.remove('dragover'); });
    zoneVar.addEventListener('drop', function(e){
      e.preventDefault();
      zoneVar.classList.remove('dragover');
      var f = e.dataTransfer.files[0];
      if (f) handleFileVar(f);
    });
  }

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
function updateDockHandle(){
  var handle=document.getElementById('dockRevealHandle');
  if(!handle)return;
  var visible=document.body.classList.contains('dock-revealed')||document.body.classList.contains('dock-pinned');
  handle.setAttribute('aria-expanded',visible?'true':'false');
  handle.setAttribute('aria-label',visible?i18nText('dock.collapse'):i18nText('dock.expand'));
  handle.title=visible?i18nText('dock.collapse'):i18nText('dock.expand');
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
function toggleDockPinned(){
  if(!document.body.classList.contains('dock-auto-hide'))return;
  dockPinned=!dockPinned;
  document.body.classList.toggle('dock-pinned',dockPinned);
  if(dockPinned)revealDock();
  else scheduleDockHide(120);
  updateDockHandle();
}
function setDockPageMode(name){
  document.body.classList.add('dock-auto-hide');
  dockPinned=false;
  document.body.classList.remove('dock-pinned');
  scheduleDockHide(180);
  updateDockHandle();
}
function initializeDockAutoHide(){
  var dock=document.getElementById('macDock');
  var zone=document.getElementById('dockRevealZone');
  var handle=document.getElementById('dockRevealHandle');
  if(!dock||dock.dataset.autoHideReady==='yes')return;
  dock.dataset.autoHideReady='yes';
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
    setCreatorWorkbenchMode('image',parts[2]==='single'?'single':'multi');
    switchSubTab(['t2i','i2i','variation'].indexOf(parts[1])!==-1?parts[1]:'t2i');
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
  '21:9-2k':  [2560, 1092],  // 超宽银幕 2K
  '16:9-4k':  [4096, 2304],
  '9:16-4k':  [2304, 4096],
};

function setRatio(el, ratio) {
  // 更新选中状态
  document.querySelectorAll('#ratioGrid .ratio-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  document.getElementById('selRatio').value = ratio;

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
  currentMode = mode;
  document.getElementById('panelT2I').classList.toggle('hidden', mode !== 't2i');
  document.getElementById('panelI2I').classList.toggle('hidden', mode !== 'i2i');
  document.getElementById('panelVAR').classList.toggle('hidden', mode !== 'variation');
  document.getElementById('subTabT2I').classList.toggle('active', mode === 't2i');
  document.getElementById('subTabI2I').classList.toggle('active', mode === 'i2i');
  document.getElementById('subTabVAR').classList.toggle('active', mode === 'variation');
  document.getElementById('strengthGroup').style.display = mode === 'i2i' ? '' : 'none';
  document.getElementById('quickCard').style.display = mode === 't2i' ? '' : 'none';
  mountCreatorGenerateAction(mode);
  hideEnhance();
  if(getVisibleAppPage()==='generate')updateAppRoute('generate');
}

// ═══════════════════════════════════════════════════════════════════
// Provider 加载
// ═══════════════════════════════════════════════════════════════════
function loadProviders() {
  return _authFetch('/api/providers').then(function(r){ return r.json(); }).then(function(data){
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
    loadModelDropdown();  // 更新模型下拉列表
    setStatus(i18nText('provider.loaded_prefix') + allProviders.filter(function(p){return p.type==='image';}).length + i18nText('provider.image_count'));
  }).catch(function(e){ if (e.message !== 'AUTH_REQUIRED') setStatus(i18nText('provider.load_failed')); });
}

function onImageModelChange(pid, newModel) {
  for (var i = 0; i < allProviders.length; i++) {
    if (allProviders[i].id === pid) {
      allProviders[i].model = newModel;
      break;
    }
  }
}

function renderProviderList() {
  var container = document.getElementById('providerList');
  var html = '';
  var imageProviders = allProviders.filter(function(p){ return p.type === 'image'; });

  for (var i = 0; i < imageProviders.length; i++) {
    (function(p, idx){
      var sel = selectedProviders.indexOf(p.id) !== -1;
      var configured = p.api_key || p.has_key;
      var disabled = !p.enabled || !configured;

      var allModels = p.models && p.models.length > 0 ? p.models : (p.model ? [p.model] : []);
      // 过滤掉非生图模型（视频模型 + LLM模型）
      var filteredModels = filterModelsByType(allModels, 'image');
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
              'onclick="' + (disabled ? '' : 'toggleProvider(\'' + p.id + '\')') + '" data-id="' + p.id + '">' +
        '<div class="provider-dot" style="background:' + (p.color || '#5b8def') + ';"></div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div class="provider-name">' + escHtml(p.name) + '</div>' +
        '</div>' +
        '<label class="provider-checkbox" onclick="event.stopPropagation();' + (disabled ? '' : 'toggleProvider(\'' + p.id + '\')') + '">' +
          '<input type="checkbox" ' + (sel ? 'checked' : '') + ' ' + (disabled ? 'disabled' : '') + '>' +
          '<span class="provider-checkmark"></span>' +
        '</label>' +
      '</div>' +
      '<div style="padding:2px 0 6px 22px;">' +
        '<select onchange="onImageModelChange(\'' + p.id + '\', this.value)" ' + (!sel ? 'disabled' : '') + ' style="width:100%;font-size:11px;padding:4px 8px;background:var(--bg-base);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);' + (!sel ? 'opacity:0.5;' : '') + '">' +
          (modelOpts || i18nText('provider.no_models_html')) +
        '</select>' +
      '</div>';
    })(imageProviders[i], i);
  }

  container.innerHTML = html || i18nText('provider.no_models_add_html');
  updateSelCount();
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
function handleFileSelect(e) { var f = e.target.files[0]; if(f) handleFile(f); }
function handleFile(f) {
  if (!f.type.startsWith('image/')) { alert(i18nText('upload.image_required')); return; }
  if (f.size > 10*1024*1024) { alert(i18nText('upload.image_too_large')); return; }
  var reader = new FileReader();
  reader.onload = function(e2) {
    uploadedImageData = e2.target.result;
    var p = document.getElementById('uploadPreview');
    p.src = uploadedImageData;
    p.classList.remove('hidden');
    var ph = document.getElementById('uploadPlaceholder');
    if (ph) ph.style.display = 'none';
  };
  reader.readAsDataURL(f);
}

// ── 变形模式文件上传 ──
var variationImageData = null;
function handleFileSelectVar(e) { var f = e.target.files[0]; if(f) handleFileVar(f); }
function handleFileVar(f) {
  if (!f.type.startsWith('image/')) { alert(i18nText('upload.image_required')); return; }
  if (f.size > 10*1024*1024) { alert(i18nText('upload.image_too_large')); return; }
  var reader = new FileReader();
  reader.onload = function(e2) {
    variationImageData = e2.target.result;
    var p = document.getElementById('uploadPreviewVar');
    p.src = variationImageData;
    p.classList.remove('hidden');
  };
  reader.readAsDataURL(f);
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
var genDisplayedResults = {};
var genStartTs = 0;
var genTimerInterval = null;

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
        var statusText = s.status === 'queued' ? i18nText('status.queuing') : s.status === 'generating' ? i18nText('status.generating') + '...' : s.status === 'completed' ? '? ' + (s.result ? s.result.elapsed_seconds : '') + 's' : i18nText('status.failed_icon');
        var statusColor = s.status === 'completed' ? '#22c55e' : s.status === 'failed' ? '#ef4444' : s.status === 'generating' ? 'var(--accent)' : 'var(--text-muted)';
        var fillClass = s.status === 'generating' ? 'vprog-fill marquee' : s.status === 'completed' ? 'vprog-fill complete' : 'vprog-fill';

        html += '<div style="margin-bottom:6px;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">';
        html += '<span style="font-size:10px;color:var(--text-muted);">#' + (parseInt(it.key.split('_').pop()) + 1) + '</span>';
        html += '<span id="gprog_label_' + it.key + '" style="font-size:10px;color:' + statusColor + ';">' + statusText + '</span>';
        html += '</div>';
        html += '<div style="background:var(--border);border-radius:3px;overflow:hidden;height:4px;margin-bottom:3px;">';
        html += '<div class="' + fillClass + '" id="gprog_fill_' + it.key + '" style="width:' + s.progress + '%;"></div>';
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

function retryProvider(key, realPid) {
  if (!lastGenContext) { alert(i18nText('result.retry_missing')); return; }

  var pid = realPid || key.replace(/_\d+$/, '');
  var providerInfo = findProvider(pid) || { name: pid };
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
    payload.strength = lastGenContext.strength;
  }

  _authFetch('/api/generate', {
    method: 'POST',
    body: JSON.stringify(payload)
  }).then(function(r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
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

function startGenPolling(genId) {
  genCurrentGenId = genId;
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
    _authFetch('/api/generate/status/' + genId).then(function(r) { return r.json(); }).then(function(data) {
      var pfill = document.getElementById('progressFill');
      var ptxt = document.getElementById('progressText');
      if (pfill) pfill.style.width = data.progress + '%';

      // 更新进度文本
      if (ptxt && data.status !== 'completed') {
        var states = data.provider_states || {};
        var names = Object.keys(states).map(function(k) { return states[k].name || k; });
        var generating = Object.values(states).filter(function(s) { return s.status === 'generating'; });
        var done = Object.values(states).filter(function(s) { return s.status === 'completed' || s.status === 'failed'; });
        if (generating.length > 0) {
          if (ptxt) ptxt.textContent = generating.map(function(s) { return s.name || s.model; }).join(', ') + i18nText('status.generating_prefix') + done.length + '/' + names.length + i18nText('status.complete_paren');
        } else if (done.length < names.length) {
          if (ptxt) ptxt.textContent = i18nText('status.queued_prefix') + done.length + '/' + names.length + i18nText('status.complete_paren');
        }
      }

      if (data.provider_states) {
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

      // 任务完成
      if (data.status === 'completed') {
        stopGenPolling();
        var elapsedEl = document.getElementById('elapsedSeconds');
        if (elapsedEl && data.elapsed_seconds !== undefined) elapsedEl.textContent = data.elapsed_seconds.toFixed(1);
        currentResults = data.results || {};
        currentGroupTimings = data.group_timings || {};
        if (data.continuous_id) window.continuousSessionId = data.continuous_id;
        if (data.enhanced_prompt) showEnhanceResult(data.enhanced_prompt);
        if (data.llm_error && !data.enhanced_prompt) showEnhanceResult('⚠️ ' + data.llm_error);
        // 最终刷新完整预览
        showResults(currentResults, '', currentGroupTimings);
        var pfill2 = document.getElementById('progressFill');
        if (pfill2) pfill2.style.width = '100%';
        var okCount = Object.values(currentResults).filter(function(r) { return r.success; }).length;
        var totalProviders = Object.keys(data.provider_states || {}).length;
        if (ptxt) ptxt.textContent = i18nText('result.complete_prefix') + okCount + '/' + totalProviders + i18nText('result.success_suffix');
        setStatus(i18nText('result.complete_middle') + okCount + '/' + totalProviders + i18nText('result.success_middle') + (data.elapsed_seconds || 0) + 's');
        loadGallery();
        var btn = document.getElementById('btnGen');
        if (btn) { btn.disabled = false; btn.innerHTML = i18nText('creator.generate_image_sparkle'); }
        var closeBtn = document.getElementById('progressCloseBtn');
        if (closeBtn) closeBtn.style.display = 'inline-block';
        var logWrap = document.getElementById('genLogWrap');
        if (logWrap) { var cnt = document.getElementById('genLogCount'); if (cnt) cnt.textContent = i18nText('common.done'); }
      }
    }).catch(function(e) {
      console.error('Poll error:', e);
    });
  }, 1500);
}

function stopGenPolling() {
  if (genPollTimer) { clearInterval(genPollTimer); genPollTimer = null; }
  if (genTimerInterval) { clearInterval(genTimerInterval); genTimerInterval = null; }
}

function doGenerate() {
  // ── 变形模式：直接调用 /api/images/variations ──
  if (currentMode === 'variation') {
    doVariation();
    return;
  }

  var prompt = '';
  var systemPrompt = null;
  if (currentMode === 't2i') {
    prompt = getFinalPrompt();
    if (promptMode === 'pro') {
      systemPrompt = document.getElementById('txtSysPrompt').value.trim();
    }
  } else {
    prompt = document.getElementById('txtPromptI2I').value.trim();
    if (!prompt && !uploadedImageData) { alert(i18nText('creator.reference_or_prompt')); return; }
    if (!uploadedImageData) { alert(i18nText('creator.reference_required')); return; }
  }
  if (!prompt) { alert(i18nText('creator.prompt_required')); return; }
  if (!selectedProviders.length) { alert(i18nText('creator.model_required')); return; }

  var btn = document.getElementById('btnGen');
  btn.disabled = true;
  btn.innerHTML = i18nText('status.submitting_html');

  var pbox = document.getElementById('progressBox');
  var ptxt = document.getElementById('progressText');
  var pfill = document.getElementById('progressFill');
  var elapsedEl = document.getElementById('elapsedSeconds');
  var perSection = document.getElementById('perProviderSection');
  var logWrap = document.getElementById('genLogWrap');
  var logArea = document.getElementById('genLogArea');
  var logCount = document.getElementById('genLogCount');
  pbox.classList.remove('hidden');
  showCreatorTaskMonitor(true);
  ptxt.textContent = i18nText('status.submitting');
  pfill.style.width = '5%';
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
  var genRatio = currentSettings.ratio || '1:1';
  var genW = currentSettings.w || 1024;
  var genH = currentSettings.h || 1024;
  var genQty = currentSettings.qty || 1;

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
    size: genSize,
    quality: genQuality || undefined,
    continuous: document.getElementById('chkContinuous').checked,
    system_prompt: systemPrompt,
    continuous_id: window.continuousSessionId || null,
    quantities: qtyMap,
  };
  if (currentMode === 'i2i' && uploadedImageData) {
    payload.image_data = uploadedImageData;
    payload.strength = parseFloat(document.getElementById('selStrength').value);
  }
  // 尺寸自适应参数
  if (document.getElementById('chkUpscale').checked) {
    payload.upscale_to = document.getElementById('upscaleSize').value;
    payload.upscale_method = document.getElementById('upscaleMethod').value;
    payload.upscale_ratio = document.getElementById('upscaleRatio').value;
  }

  // 保存生图上下文，用于单模型重试
  lastGenContext = {
    prompt: prompt,
    system_prompt: systemPrompt,
    mode: currentMode,
    size: genSize,
    quality: genQuality,
    image_data: uploadedImageData,
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
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(data) {
    clearInterval(timerInterval);
    pfill.style.width = '15%';
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
    btn.disabled = false;
    btn.innerHTML = i18nText('creator.generate_image_sparkle');
  });
}

// ── 变形模式提交 ──
function doVariation() {
  if (!variationImageData) { alert(i18nText('creator.source_required')); return; }
  if (!selectedProviders.length) { alert(i18nText('creator.image_model_required')); return; }

  var btn = document.getElementById('btnGen');
  btn.disabled = true;
  btn.innerHTML = i18nText('status.submitting_html');

  var pbox = document.getElementById('progressBox');
  var ptxt = document.getElementById('progressText');
  var pfill = document.getElementById('progressFill');
  var elapsedEl = document.getElementById('elapsedSeconds');
  pbox.classList.remove('hidden');
  showCreatorTaskMonitor(true);
  ptxt.textContent = i18nText('variation.generating');
  pfill.style.width = '10%';
  elapsedEl.textContent = '0.0';

  genStartTs = Date.now();
  var timerInterval = setInterval(function() {
    var elapsed = ((Date.now() - genStartTs) / 1000).toFixed(1);
    elapsedEl.textContent = elapsed;
  }, 200);

  var payload = {
    image_data: variationImageData,
    provider_id: selectedProviders[0] || '',
    size: document.getElementById('varSize').value,
    n: parseInt(document.getElementById('varCount').value) || 1,
  };

  _authFetch('/api/images/variations', {
    method: 'POST',
    body: JSON.stringify(payload)
  }).then(function(r) {
    clearInterval(timerInterval);
    if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || 'HTTP ' + r.status); });
    return r.json();
  }).then(function(data) {
    clearInterval(timerInterval);
    pfill.style.width = '100%';
    ptxt.textContent = i18nText('variation.complete_prefix') + (data.images || []).length + i18nText('result.image_count_suffix');
    elapsedEl.textContent = ((Date.now() - genStartTs) / 1000).toFixed(1);
    btn.disabled = false;
    btn.innerHTML = i18nText('creator.generate_image_sparkle');
    // 将结果追加到预览区（使用 local_path）
    var provId = data.provider_id || selectedProviders[0] || 'variation';
    if (data.images && data.images.length) {
      data.images.forEach(function(img, idx) {
        var localPath = img.local_path || '';
        if (localPath) {
          addResultToPreview(provId + '_' + idx, {
            local_path: localPath,
            model: provId,
            prompt: i18nText('variation.variant'),
            seq: idx,
          });
        }
      });
    }
    setStatus(i18nText('variation.complete'));
  }).catch(function(e) {
    clearInterval(timerInterval);
    pbox.classList.add('hidden');
    alert(i18nText('variation.failed') + e.message);
    setStatus(i18nText('variation.failed') + e.message);
    btn.disabled = false;
    btn.innerHTML = i18nText('creator.generate_image_sparkle');
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
  if (lb && img) {
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

function sendToImageToImage(e) {
  e.stopPropagation();
  if (!lightboxCurrentSrc) { alert(i18nText('image.unavailable')); return; }
  var imgUrl = lightboxCurrentSrc;
  window._pendingI2IPrompt = lightboxCurrentPrompt || '';
  closeLightbox(e);
  if (window.dockNav) { window.dockNav.switchPage('generate'); }

  // 从 URL 获取 base64 数据
  var fname = imgUrl.split('/').pop();
  _authFetch('/api/gallery/image/' + fname + '/base64')
    .then(function(r) {
      if (!r.ok) throw new Error(i18nText('image.data_failed'));
      return r.json();
    })
    .then(function(d) {
      window.uploadedImageData = d.data;
      setTimeout(function() {
        if (typeof switchSubTab === 'function') {
          switchSubTab('i2i');
        }
        var p = document.getElementById('uploadPreview');
        if (p) { p.src = d.data; p.classList.remove('hidden'); }
        if (window._pendingI2IPrompt) {
          var ta = document.getElementById('txtPromptI2I');
          if (ta) ta.value = window._pendingI2IPrompt;
        }
        setStatus(i18nText('image.sent_i2i'));
      }, 300);
    })
    .catch(function(e) {
      alert(i18nText('image.load_failed') + e.message);
    });
}

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
  if (!item) { console.error('[Gallery] item not found:', itemId); alert(i18nText('image.open_missing')); return; }
  if (!item.local_path) { console.error('[Gallery] local_path invalid:', item); alert(i18nText('image.open_invalid')); return; }
  var f = item.local_path.split(/[\\/]/).pop();
  var pInfo = findProvider(item.model) || {name: item.model, color: '#5b8def'};
  var src = '/api/gallery/image/' + encodeURIComponent(f);
  var prompt = item.prompt || '';
  console.log('[Gallery] 打开灯箱:', { id: itemId, file: f, src: src, prompt: prompt.substring(0, 50) });
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
            '<button onclick="_testMirrors()" style="padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">🔍 测速</button>' +
            '<button onclick="applyGlobalUpdate()" style="padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer;">立即更新</button>' +
            '</div>' + notes;
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

function _testMirrors() {
  var content = document.getElementById('updateContent');
  if (content) content.innerHTML = '<span style="color:var(--text-muted);">' + i18nText('update.testing_mirrors') + '</span>';

  _authFetch('/api/update/mirrors')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var html = '<div style="margin-bottom:6px;font-weight:600;color:var(--text-primary);">GitHub 代理线路测速</div>';
      html += '<div style="display:flex;flex-direction:column;gap:4px;">';
      for (var i = 0; i < d.mirrors.length; i++) {
        var m = d.mirrors[i];
        var color = m.available ? (m.latency_ms < 1000 ? '#22c55e' : '#f59e0b') : '#ef4444';
        var status = m.available ? m.latency_ms + 'ms' : '不可用';
        html += '<div style="display:flex;align-items:center;gap:6px;font-size:10px;">';
        html += '<span style="width:12px;height:12px;border-radius:50%;background:' + color + ';flex-shrink:0;"></span>';
        html += '<span style="flex:1;color:var(--text-secondary);">' + escHtml(m.name) + '</span>';
        html += '<span style="color:' + color + ';">' + status + '</span>';
        if (m.available) {
          html += '<button onclick="_applyUpdate(null, \'' + escHtml(m.url) + '\')" style="padding:2px 6px;font-size:9px;border-radius:4px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;">使用此线路更新</button>';
        }
        html += '</div>';
      }
      html += '</div>';
      html += '<button onclick="_checkForUpdates()" style="margin-top:8px;padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">返回</button>';
      if (content) content.innerHTML = html;
    })
    .catch(function(e) {
      if (content) content.innerHTML = '<span style="color:#ef4444;">? ' + i18nText('update.speed_test_failed_prefix') + escHtml(e.message) + '</span>';
    });
}

var _globalUpdateData = null;

function _formatUpdateVersion(version) {
  var value = String(version || '');
  return /^v/i.test(value) ? value : 'v' + value;
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
    downloadLink.href = 'https://github.com/liwei9745/GenBox/releases/tag/' + encodeURIComponent(d.latest_version);
    applyBtn.textContent = i18nText('update.apply');
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
  _applyUpdate(d.download_url || null);
}

function toggleUpdateCheck(el) {
  localStorage.setItem('genbox_update_check', el.checked ? 'on' : 'off');
  if (el.checked) checkGlobalUpdate();
  else { _globalUpdateData = { disabled: true }; renderUpdateBadge(_globalUpdateData); }
}

function _applyUpdate(downloadUrl, mirrorUrl) {
  var badge = document.getElementById('updateStatusBadge');
  var content = document.getElementById('updateContent');
  var globalBtn = document.getElementById('updateApplyBtn');
  var globalStatus = document.getElementById('updateModalStatus');
  if (badge) { badge.textContent = i18nText('update.updating'); badge.style.background = '#3b82f622'; badge.style.color = '#3b82f6'; }
  if (content) content.innerHTML = '<span style="color:#3b82f6;">? ' + i18nText('update.updating_message') + '</span>';
  if (globalBtn) { globalBtn.disabled = true; globalBtn.textContent = i18nText('update.updating'); }
  if (globalStatus) { globalStatus.classList.remove('hidden'); globalStatus.textContent = i18nText('update.updating_message'); }

  if (!downloadUrl && _globalUpdateData) downloadUrl = _globalUpdateData.download_url || null;
  var url = '/api/update/apply';
  var params = [];
  if (downloadUrl) params.push('download_url=' + encodeURIComponent(downloadUrl));
  if (mirrorUrl) params.push('mirror=' + encodeURIComponent(mirrorUrl));
  if (params.length) url += '?' + params.join('&');

  _authFetch(url, { method: 'POST' })
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (d.ok || d.success) {
        if (badge) { badge.textContent = i18nText('update.success'); badge.style.background = '#22c55e22'; badge.style.color = '#22c55e'; }
        if (content) content.innerHTML = '<span style="color:#22c55e;">? ' + escHtml(d.message || i18nText('update.success')) + '</span>';
        if (globalBtn) globalBtn.textContent = i18nText('update.success');
        if (globalStatus) globalStatus.textContent = d.message || i18nText('update.success');
        if (d.restart) {
          if (content) content.innerHTML += '<br><span style="color:var(--text-muted);font-size:10px;">' + i18nText('update.restart_soon') + '</span>';
          if (globalStatus) globalStatus.textContent += ' ' + i18nText('update.restart_soon');
          setTimeout(function(){ location.reload(); }, 3000);
        }
      } else {
        if (badge) { badge.textContent = i18nText('update.failed'); badge.style.background = '#ef444422'; badge.style.color = '#ef4444'; }
        if (content) content.innerHTML = '<span style="color:#ef4444;">? ' + escHtml(d.error || i18nText('update.failed')) + '</span>';
        if (globalBtn) { globalBtn.disabled = false; globalBtn.textContent = i18nText('update.retry'); }
        if (globalStatus) globalStatus.textContent = d.error || i18nText('update.failed');
      }
    })
    .catch(function(e) {
      if (badge) { badge.textContent = i18nText('update.failed'); badge.style.background = '#ef444422'; badge.style.color = '#ef4444'; }
      if (content) content.innerHTML = '<span style="color:#ef4444;">? ' + i18nText('update.failed_prefix') + escHtml(e.message) + '</span>';
      if (globalBtn) { globalBtn.disabled = false; globalBtn.textContent = i18nText('update.retry'); }
      if (globalStatus) globalStatus.textContent = i18nText('update.failed_prefix') + e.message;
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
var _adminKey = localStorage.getItem('igs_admin_key') || '';

function _authFetch(url, opts) {
  opts = opts || {};
  if (!opts.headers) opts.headers = {};
  if (_adminKey) opts.headers['X-Admin-Key'] = _adminKey;
  if (opts.body && !opts.headers['Content-Type']) opts.headers['Content-Type'] = 'application/json';
  return fetch(url, opts).then(function(r) {
    if (r.status === 401) {
      _showLogin();
      throw new Error('AUTH_REQUIRED');
    }
    return r;
  });
}

function _showLogin() {
  document.getElementById('loginPage').style.display = 'flex';
  document.getElementById('loginKeyInput').focus();
}
function _hideLogin() {
  document.getElementById('loginPage').style.display = 'none';
}
function doLogin() {
  var key = document.getElementById('loginKeyInput').value.trim();
  if (!key) return;
  _adminKey = key;
  fetch('/api/providers', {headers: {'X-Admin-Key': key}}).then(function(r) {
    if (r.status === 401) {
      document.getElementById('loginError').style.display = 'block';
      return;
    }
    localStorage.setItem('igs_admin_key', key);
    _hideLogin();
    loadProviders();
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
function checkSetupWizard() {
  fetch('/api/setup/status').then(function(r){ return r.json(); }).then(function(d){
    if (d.needs_first_run) {
      // 首次启动：生成密钥并显示欢迎页
      fetch('/api/setup/first-run', {method:'POST'}).then(function(r){return r.json();}).then(function(data){
        _adminKey = data.admin_key;
        localStorage.setItem('igs_admin_key', data.admin_key);
        _showWelcome(data.admin_key);
      });
    } else if (d.prod_mode && !d.has_admin_key) {
      // 生产模式但无密钥（理论上不会到这里）
      _showLogin();
    } else if (d.prod_mode && _adminKey) {
      // 生产模式有密钥：验证是否有效
      fetch('/api/providers', {headers: {'X-Admin-Key': _adminKey}}).then(function(r) {
        if (r.status === 401) {
          localStorage.removeItem('igs_admin_key');
          _adminKey = '';
          _showLogin();
        }
      });
    }
    // dev 模式：不做任何事
  }).catch(function(){});
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
      var keyVal = p.api_key_masked || '';
      var keyPlaceholder = p.has_key ? (keyVal || i18nText('provider.masked_configured')) : i18nText('provider.api_key_placeholder');
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
  var capChecks = document.querySelectorAll('.cap-check');
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
    quality: '', extra: {}
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

  var tmp = { id:pid||'tmp', name:nameVal, type:typeVal, base_url:urlVal, api_key:keyVal, model:'', color:colorVal, enabled:enVal, endpoint_type:etVal, models:[], quality:'', extra:{} };

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
    loadProviders().then(function(){ renderProviderEdit(); });
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
  image:{multi:[i18nText('creator.image_multi_title'),i18nText('creator.image_multi_hint')],single:[i18nText('creator.single_image_title'),i18nText('creator.single_image_hint')]},
  video:{multi:[i18nText('video.multi_title'),i18nText('video.multi_hint')],single:[i18nText('video.single_title'),i18nText('video.single_hint')]}
};
var CREATOR_WORKBENCH_COPY_EN={
  image:{multi:['Multi-model image comparison','Run the same prompt across models and compare results.'],single:['Single-model image workspace','One model, a larger prompt, fewer distractions, one screen.']},
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
}
function setCreatorWorkbenchMode(kind,mode){
  if(mode!=='single')mode='multi';
  localStorage.setItem('igs_'+kind+'_workbench',mode);
  var page=document.getElementById(kind==='image'?'pageGenerate':'pageVideo');
  if(page)page.classList.toggle('creator-single',mode==='single');
  var copy=(getUiLanguage()==='en'?CREATOR_WORKBENCH_COPY_EN:CREATOR_WORKBENCH_COPY)[kind][mode];
  var title=document.getElementById(kind+'WorkbenchTitle');
  var hint=document.getElementById(kind+'WorkbenchHint');
  if(title)title.textContent=copy[0];
  if(hint)hint.textContent=copy[1];
  var multi=document.getElementById(kind+'ModeMulti');
  var single=document.getElementById(kind+'ModeSingle');
  if(multi)multi.classList.toggle('active',mode==='multi');
  if(single)single.classList.toggle('active',mode==='single');
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
  var button=document.getElementById('creatorTaskToggle');
  if(button){button.textContent=expanded?i18nText('creator.collapse'):i18nText('creator.expand');button.setAttribute('aria-expanded',expanded?'true':'false');}
}
function toggleCreatorTaskMonitor(){
  var monitor=document.getElementById('creatorTaskMonitor');
  showCreatorTaskMonitor(!monitor||!monitor.classList.contains('expanded'));
}
function mountCreatorGenerateAction(mode){
  var action=document.getElementById('creatorGenerateAction');
  var header=document.getElementById('creatorGenerateHeader');
  var target=document.getElementById(mode==='i2i'?'panelI2I':mode==='variation'?'panelVAR':'panelT2I');
  if(!action||!header||!target)return;
  target.insertBefore(header,target.firstChild);
  target.appendChild(action);
  var title=document.getElementById('creatorGenerateActionTitle');
  var hint=document.getElementById('creatorGenerateActionHint');
  var button=document.getElementById('btnGen');
  if(mode==='i2i'){
    if(title)title.textContent=i18nText('creator.i2i_settings');
    if(hint)hint.textContent=i18nText('creator.i2i_hint');
    if(button)button.innerHTML=i18nText('creator.generate_image');
  }else if(mode==='variation'){
    if(title)title.textContent=i18nText('creator.variation_settings');
    if(hint)hint.textContent=i18nText('creator.variation_hint');
    if(button)button.innerHTML=i18nText('creator.generate_variation');
  }else{
    if(title)title.textContent=i18nText('creator.prompt_title');
    if(hint)hint.textContent=i18nText('creator.prompt_hint');
    if(button)button.innerHTML=i18nText('creator.generate_image');
  }
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
  if(subTabs&&subTabs.parentElement)modeTools.appendChild(subTabs.parentElement);
  if(promptModes&&promptModes.parentElement)modeTools.appendChild(promptModes.parentElement);
  if(enhance&&enhance.parentElement&&enhance.parentElement.parentElement)assistTools.appendChild(enhance.parentElement.parentElement);
  if(continuous&&continuous.parentElement&&continuous.parentElement.parentElement)assistTools.appendChild(continuous.parentElement.parentElement);
  if(upscale)assistTools.appendChild(upscale);
  if(quickCard)quickTools.appendChild(quickCard);
  var actionCard=bottomRow.querySelector('.generate-input-col > .glass-card');
  var generateButton=document.getElementById('btnGen');
  if(actionCard&&generateButton){
    var header=document.createElement('div');
    header.id='creatorGenerateHeader';
    header.className='creator-generate-header';
    header.innerHTML='<strong id="creatorGenerateActionTitle">' + i18nText('creator.prompt_title') + '</strong><span id="creatorGenerateActionHint">' + i18nText('creator.prompt_hint') + '</span>';
    var action=document.createElement('div');
    action.id='creatorGenerateAction';
    action.className='creator-generate-action';
    action.appendChild(generateButton);
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
      if (ml.indexOf('gpt-5') !== -1 && ml.indexOf('image') === -1) return false;
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
  videoLog('\u63D0\u793A\u8BCD: ' + prompt.substring(0, 80) + (prompt.length > 80 ? '...' : ''), 'info');
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
