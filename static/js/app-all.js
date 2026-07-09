
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
  "🎬 风格": [
    {label: "电影感画面", en: "Cinematic lighting, 21:9 widescreen, 8K HDR, volumetric lighting, film grain"},
    {label: "赛博朋克城市", en: "Cyberpunk neon city at night, rain reflections, hyper-realistic, Unreal Engine 5"},
    {label: "商业产品摄影", en: "Studio product photography, white background, soft box lighting, commercial grade"},
    {label: "油画风格", en: "Oil painting style, classical, Renaissance technique, rich textures"},
    {label: "水彩插画", en: "Watercolor illustration, soft gradients, delicate brushwork"},
    {label: "动漫风格", en: "Anime style, vibrant colors, Studio Ghibli inspired, detailed background"},
    {label: "像素艺术", en: "Pixel art, 16-bit, retro gaming aesthetic, nostalgic"},
    {label: "低多边形3D", en: "Low-poly 3D render, geometric, clean, minimal design"}
  ],
  "👘 古风": [
    {label: "仙侠古风", en: "Xianxia fantasy, ethereal beauty in flowing hanfu, ice lotus glow cyan light, cinematic"},
    {label: "大唐宫廷", en: "Tang dynasty palace scene, silk robes, traditional architecture, golden hour light"},
    {label: "水墨山水", en: "Ancient Chinese landscape painting style, mountains and mist, ink wash"},
    {label: "清朝宫廷", en: "Qing Dynasty court portrait, ornate costumes, detailed embroidery"},
    {label: "古风战士", en: "Fantasy warrior in ancient Chinese armor, dramatic pose, epic battle scene"}
  ],
  "🌿 自然": [
    {label: "日出山景", en: "Misty mountain landscape at sunrise, golden light, aerial drone view"},
    {label: "热带海滩日落", en: "Tropical beach at sunset, palm trees, crystal clear water, photorealistic"},
    {label: "樱花满开", en: "Cherry blossom trees in full bloom, traditional Japanese garden, spring"},
    {label: "极光雪山", en: "Northern lights over snowy mountains, aurora borealis, night sky"},
    {label: "秋日森林", en: "Autumn forest path, golden leaves, soft overcast lighting, peaceful"}
  ],
  "🏙 建筑": [
    {label: "未来城市", en: "Futuristic cityscape, flying vehicles, holographic billboards, night"},
    {label: "中世纪城堡", en: "Medieval European castle on cliff, storm clouds, dramatic lighting"},
    {label: "现代极简建筑", en: "Minimalist modern architecture, white concrete, geometric forms, sunlight"},
    {label: "古代遗迹", en: "Ancient ruins overgrown with vegetation, mysterious atmosphere, moss"},
    {label: "夜市街景", en: "Bustling Asian night market, street food stalls, warm lantern light"}
  ],
  "🎭 人像": [
    {label: "专业人像摄影", en: "Professional portrait photography, studio lighting, shallow depth of field"},
    {label: "时尚大片", en: "Fashion editorial, editorial makeup, high-end magazine cover style"},
    {label: "街拍风格", en: "Candid street photography, natural lighting, urban environment"},
    {label: "复古胶片", en: "Vintage film photography aesthetic, grain, warm tones, nostalgic"},
    {label: "精致五官特写", en: "Close-up beauty shot, dramatic eye detail, glossy lips, luxury cosmetics"}
  ],
  "🚀 科幻": [
    {label: "飞船驾驶舱", en: "Spaceship interior bridge, holographic displays, alien planet view through windows"},
    {label: "仿生人", en: "Robot android in futuristic city, chrome reflections, blue hour lighting"},
    {label: "外星地表", en: "Alien planet surface, bioluminescent flora, twin moons in sky"},
    {label: "深空站", en: "Deep space station orbiting distant nebula, realistic sci-fi design"},
    {label: "复古未来主义", en: "Retro-futuristic 1950s sci-fi aesthetic, chrome appliances, atomic age"}
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
function switchNav(name, el) {
  document.getElementById('pageGenerate').classList.toggle('hidden', name !== 'generate');
  document.getElementById('pageVideo').classList.toggle('hidden', name !== 'video');
  document.getElementById('pageGallery').classList.toggle('hidden', name !== 'gallery');
  document.getElementById('pageHistory').classList.toggle('hidden', name !== 'history');
  document.getElementById('pageDashboard').classList.toggle('hidden', name !== 'dashboard');

  document.querySelectorAll('.nav-item').forEach(function(n){ n.classList.remove('active'); });
  if (el) el.classList.add('active');

  document.querySelectorAll('.dock-item[data-page]').forEach(function(d){ d.classList.remove('active'); });
  var dockTarget = document.querySelector('.dock-item[data-page="' + name + '"]');
  if (dockTarget) dockTarget.classList.add('active');

  if (name === 'gallery') loadGallery();
  if (name === 'history') loadHistory();
  if (name === 'video') loadVideoProviders();
  if (name === 'dashboard') loadDashboard();
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
  optGlobal.textContent = '🌐 全局（对所有模型生效）';
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
    var label = modelKey === '_global' ? '全局' : modelKey;
    var toast = document.getElementById('saveSettingsToast');
    if (toast) {
      toast.textContent = '✅ 已保存「' + label + '」的图像设置';
      toast.classList.remove('hidden');
      setTimeout(function(){ toast.classList.add('hidden'); }, 2500);
    }
    setStatus('✅ 已保存「' + label + '」的图像设置');
  } catch(e) {
    var toast2 = document.getElementById('saveSettingsToast');
    if (toast2) {
      toast2.textContent = '❌ 保存失败';
      toast2.style.color = '#ef4444';
      toast2.style.background = 'rgba(239,68,68,0.08)';
      toast2.style.borderColor = 'rgba(239,68,68,0.2)';
      toast2.classList.remove('hidden');
      setTimeout(function(){ toast2.classList.add('hidden'); toast2.style.color=''; toast2.style.background=''; toast2.style.borderColor=''; }, 2500);
    }
    setStatus('❌ 保存失败');
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
  hideEnhance();
}

// ═══════════════════════════════════════════════════════════════════
// Provider 加载
// ═══════════════════════════════════════════════════════════════════
function loadProviders() {
  return _authFetch('/api/providers').then(function(r){ return r.json(); }).then(function(data){
    allProviders = data.providers || [];
    loadProviderOrder();
    renderProviderList();
    loadModelDropdown();  // 更新模型下拉列表
    setStatus('Provider 已加载 · ' + allProviders.filter(function(p){return p.type==='image';}).length + ' 个生图模型');
  }).catch(function(e){ if (e.message !== 'AUTH_REQUIRED') setStatus('Provider 加载失败'); });
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
          (modelOpts || '<option value="">无可用模型</option>') +
        '</select>' +
      '</div>';
    })(imageProviders[i], i);
  }

  container.innerHTML = html || '<div style="color:var(--text-muted);font-size:12px;padding:8px 0;">暂无模型，<a href="#" onclick="openProviderModal();return false;" style="color:var(--accent);">去添加</a></div>';
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
      if (qBtn) all[p.id].quality = qBtn.title === '自动' ? '' : qBtn.title === '低' ? 'low' : qBtn.title === '中' ? 'medium' : 'high';
      var rBtn = qCard.querySelector('.pratio-btn.active');
      if (rBtn) all[p.id].ratio = rBtn.title;
    }
  }
  try {
    localStorage.setItem('genbox_provider_settings', JSON.stringify(all));
    setStatus('✅ 模型设置已保存');
  } catch(e) { setStatus('❌ 保存失败'); }
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
  var idx = selectedProviders.indexOf(id);
  if (idx !== -1) selectedProviders.splice(idx, 1);
  else selectedProviders.push(id);
  renderProviderList();
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

  for (var cat in QUICK_PROMPTS) {
    var section = document.createElement('div');
    section.className = 'quick-section';
    section.setAttribute('data-cat', cat);

    var tagsId = 'qt_' + cat.replace(/[^a-z]/gi,'_');
    var items = pickRandomItems(QUICK_PROMPTS[cat], 3);

    section.innerHTML =
      '<div class="quick-section-header">' +
        '<div class="quick-section-title"><span>' + cat + '</span><span style="font-size:10px;color:var(--text-muted);font-weight:400;">(' + QUICK_PROMPTS[cat].length + ')</span></div>' +
        '<div style="display:flex;align-items:center;gap:4px;">' +
          '<button class="quick-refresh" onclick="event.stopPropagation();shuffleQuickCategory(\'' + escHtml(cat).replace(/'/g,"\\'") + '\')">🔄 换一组</button>' +
          '<span class="quick-chevron open" onclick="toggleQuickSection(this.parentElement.parentElement)">▼</span>' +
        '</div>' +
      '</div>' +
      '<div class="quick-tags" id="' + tagsId + '">' +
        items.map(function(t){
          var words = t.en.split(',').map(function(w){ return w.trim(); }).filter(function(w){ return w.length > 0; });
          return '<div class="quick-item">' +
            '<div class="quick-item-label">' + escHtml(t.label) + '</div>' +
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

  var tagsEl = data.el.querySelector('.quick-tags');
  tagsEl.innerHTML = newItems.map(function(t){
    var words = t.en.split(',').map(function(w){ return w.trim(); }).filter(function(w){ return w.length > 0; });
    return '<div class="quick-item">' +
      '<div class="quick-item-label">' + escHtml(t.label) + '</div>' +
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
  if (!f.type.startsWith('image/')) { alert('请选择图片文件'); return; }
  if (f.size > 10*1024*1024) { alert('图片不能超过 10MB'); return; }
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
  if (!f.type.startsWith('image/')) { alert('请选择图片文件'); return; }
  if (f.size > 10*1024*1024) { alert('图片不能超过 10MB'); return; }
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
    if (failedCount > 0) html += '<span style="font-size:10px;color:#ef4444;">' + failedCount + ' 失败</span>';
    html += '</div>';
    html += '<span style="font-size:10px;color:' + (groupStatus === 'completed' ? '#22c55e' : groupStatus === 'failed' ? '#ef4444' : groupStatus === 'generating' ? 'var(--accent)' : 'var(--text-muted') + ';">' + statusIcon + ' ' + (groupStatus === 'completed' ? '完成' : groupStatus === 'generating' ? '生成中' : groupStatus === 'failed' ? '失败' : '排队') + '</span>';
    html += '</div>';

    // 组内容（可折叠）
    if (!isCollapsed) {
      html += '<div style="padding:8px 10px;">';
      items.forEach(function(it) {
        var s = it.state;
        var statusText = s.status === 'queued' ? '排队中' : s.status === 'generating' ? '生成中...' : s.status === 'completed' ? '✔ ' + (s.result ? s.result.elapsed_seconds : '') + 's' : '✗ 失败';
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
      '<span class="elapsed-badge" id="prev_elapsed_' + key + '">排队中</span>';
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
  if (cnt) cnt.textContent = totalCount + ' 张成功';

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
    oldPh.innerHTML = '<div style="font-size:20px;">⚠</div><div class="ph-text" style="color:#ef4444;">失败</div>';
    oldPh.style.animation = 'none';
  }

  var elapsedBadge = card.querySelector('.elapsed-badge');
  if (elapsedBadge) { elapsedBadge.textContent = '✗ 失败'; elapsedBadge.style.color = '#ef4444'; }

  // 添加重试按钮
  var retryBtn = document.createElement('button');
  retryBtn.className = 'prev-retry-btn';
  retryBtn.innerHTML = '🔄 重试';
  retryBtn.title = '仅重试此模型';
  retryBtn.onclick = function(e) {
    e.stopPropagation();
    retryProvider(key, ph.realPid);
  };
  card.appendChild(retryBtn);

  ph.state = 'failed';
}

function retryProvider(key, realPid) {
  if (!lastGenContext) { alert('没有可重试的上下文，请重新生成'); return; }

  var pid = realPid || key.replace(/_\d+$/, '');
  var pInfo = findProvider(pid) || { name: pid };
  if (!confirm('仅重试「' + pInfo.name + '」？')) return;

  // 找到上一次这个 provider 的 seq（如果有多个）
  var seq = 0;
  if (key.indexOf('_') !== -1) {
    var parts = key.split('_');
    seq = parseInt(parts[parts.length - 1]) || 0;
  }

  var btn = document.getElementById('btnGen');
  if (btn) { btn.disabled = true; btn.innerHTML = '🔄 重试中...'; }

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
      setStatus('重试已提交: ' + pInfo.name);
      startGenPolling(data.generation_id);
    }
  }).catch(function(e) {
    alert('重试失败: ' + e.message);
    if (btn) { btn.disabled = false; btn.innerHTML = '✨ 生成图片'; }
  });
}

// ═══════════════════════════════════════════════════════════════════
//  Preview: Grouped Preview (persistent, per-model)
// ═══════════════════════════════════════════════════════════════════

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
          if (ptxt) ptxt.textContent = generating.map(function(s) { return s.name || s.model; }).join(', ') + ' 生成中... (' + done.length + '/' + names.length + ' 完成)';
        } else if (done.length < names.length) {
          if (ptxt) ptxt.textContent = '排队中... (' + done.length + '/' + names.length + ' 完成)';
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
            markPreviewPlaceholderFailed(key, s.error || (s.result && s.result.error) || '失败');
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
        if (ptxt) ptxt.textContent = '生成完成! ' + okCount + '/' + totalProviders + ' 成功';
        setStatus('生成完成 · ' + okCount + '/' + totalProviders + ' 成功 · ' + (data.elapsed_seconds || 0) + 's');
        loadGallery();
        var btn = document.getElementById('btnGen');
        if (btn) { btn.disabled = false; btn.innerHTML = '✨ 生成图片'; }
        var closeBtn = document.getElementById('progressCloseBtn');
        if (closeBtn) closeBtn.style.display = 'inline-block';
        var logWrap = document.getElementById('genLogWrap');
        if (logWrap) { var cnt = document.getElementById('genLogCount'); if (cnt) cnt.textContent = '完成'; }
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
    if (!prompt && !uploadedImageData) { alert('请上传参考图片或输入修改提示词'); return; }
    if (!uploadedImageData) { alert('请先上传参考图片'); return; }
  }
  if (!prompt) { alert('请输入提示词'); return; }
  if (!selectedProviders.length) { alert('请至少选择一个模型'); return; }

  var btn = document.getElementById('btnGen');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin" style="display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;vertical-align:middle;margin-right:4px;"></span>提交中...';

  var pbox = document.getElementById('progressBox');
  var ptxt = document.getElementById('progressText');
  var pfill = document.getElementById('progressFill');
  var elapsedEl = document.getElementById('elapsedSeconds');
  var perSection = document.getElementById('perProviderSection');
  var logWrap = document.getElementById('genLogWrap');
  var logArea = document.getElementById('genLogArea');
  var logCount = document.getElementById('genLogCount');
  pbox.classList.remove('hidden');
  ptxt.textContent = '正在提交...';
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
    ptxt.textContent = '任务已提交，队列处理中...';
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
    alert('提交失败: ' + e.message);
    setStatus('提交失败: ' + e.message);
    btn.disabled = false;
    btn.innerHTML = '✨ 生成图片';
  });
}

// ── 变形模式提交 ──
function doVariation() {
  if (!variationImageData) { alert('请先上传源图片'); return; }
  if (!selectedProviders.length) { alert('请至少选择一个生图模型'); return; }

  var btn = document.getElementById('btnGen');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin" style="display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;vertical-align:middle;margin-right:4px;"></span>提交中...';

  var pbox = document.getElementById('progressBox');
  var ptxt = document.getElementById('progressText');
  var pfill = document.getElementById('progressFill');
  var elapsedEl = document.getElementById('elapsedSeconds');
  pbox.classList.remove('hidden');
  ptxt.textContent = '正在生成变形...';
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
    ptxt.textContent = '变形完成！共 ' + (data.images || []).length + ' 张';
    elapsedEl.textContent = ((Date.now() - genStartTs) / 1000).toFixed(1);
    btn.disabled = false;
    btn.innerHTML = '✨ 生成图片';
    // 将结果追加到预览区（使用 local_path）
    var provId = data.provider_id || selectedProviders[0] || 'variation';
    if (data.images && data.images.length) {
      data.images.forEach(function(img, idx) {
        var localPath = img.local_path || '';
        if (localPath) {
          addResultToPreview(provId + '_' + idx, {
            local_path: localPath,
            model: provId,
            prompt: '变形变体',
            seq: idx,
          });
        }
      });
    }
    setStatus('变形完成');
  }).catch(function(e) {
    clearInterval(timerInterval);
    pbox.classList.add('hidden');
    alert('变形失败: ' + e.message);
    setStatus('变形失败: ' + e.message);
    btn.disabled = false;
    btn.innerHTML = '✨ 生成图片';
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
    setStatus('已复制到剪贴板');
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
  if (cnt) cnt.textContent = totalCount + ' 张成功' + (failedCount > 0 ? ' · ' + failedCount + ' 张失败' : '');

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
    if (lbLabel) lbLabel.textContent = '📝 生图提示词';
    lb.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
}

function copyLightboxPrompt() {
  if (lightboxCurrentPrompt) {
    navigator.clipboard.writeText(lightboxCurrentPrompt).then(function(){
      setStatus('已复制提示词到剪贴板');
    });
  }
}

// ═══════════════════════════════════════════════════════════════════
// 快捷操作：发送到图生图/生视频
// ═══════════════════════════════════════════════════════════════════
var lightboxCurrentSrc = '';

function sendToImageToImage(e) {
  e.stopPropagation();
  if (!lightboxCurrentSrc) { alert('无法获取图片'); return; }
  var imgUrl = lightboxCurrentSrc;
  window._pendingI2IPrompt = lightboxCurrentPrompt || '';
  closeLightbox(e);
  if (window.dockNav) { window.dockNav.switchPage('generate'); }

  // 从 URL 获取 base64 数据
  var fname = imgUrl.split('/').pop();
  _authFetch('/api/gallery/image/' + fname + '/base64')
    .then(function(r) {
      if (!r.ok) throw new Error('获取图片数据失败');
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
        setStatus('已发送到图生图模式');
      }, 300);
    })
    .catch(function(e) {
      alert('加载图片失败: ' + e.message);
    });
}

function sendToVideo(e) {
  e.stopPropagation();
  if (!lightboxCurrentSrc) { alert('无法获取图片'); return; }
  var imgUrl = lightboxCurrentSrc;
  window._pendingI2VPrompt = lightboxCurrentPrompt || '';
  closeLightbox(e);
  if (window.dockNav) { window.dockNav.switchPage('video'); }

  // 从 URL 获取 base64 数据
  var fname = imgUrl.split('/').pop();
  _authFetch('/api/gallery/image/' + fname + '/base64')
    .then(function(r) {
      if (!r.ok) throw new Error('获取图片数据失败');
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
        setStatus('已发送到图生视频模式');
      }, 300);
    })
    .catch(function(e) {
      alert('加载图片失败: ' + e.message);
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
  if (keys.length < 2) { alert('至少需要 2 个成功结果才能对比'); return; }
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
  var opts = '<option value="">所有 Provider</option>';
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
  var h = '';
  var inSelectMode = document.getElementById('btnGallerySelect') && document.getElementById('btnGallerySelect').classList.contains('active');
  for (var i = 0; i < sorted.length; i++) {
    (function(item){
      var f = item.local_path.split(/[\\/]/).pop();
      var pInfo = findProvider(item.model) || {name: item.model, color: '#5b8def'};
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
      if (isVideo) {
        typeIcon = '<div class="vid-play"><div class="vid-play-btn"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></div></div>';
        badgesHtml = '';
        var durationHtml = item.duration ? '<div class="vid-duration">' + item.duration + 's</div>' : '';
        var promptShort = (item.prompt || '').length > 40 ? (item.prompt || '').substring(0, 40) + '...' : (item.prompt || '未命名视频');
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
  if (!item || !item.video_url) { alert('无法播放视频'); return; }
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
    lbDl.textContent = '⬇ 下载视频';
    lbDl.classList.remove('hidden');
  }
  if (lbInfo) lbInfo.textContent = item.model || '';
  lightboxCurrentPrompt = item.prompt || '';
  if (lbPrompt) lbPrompt.textContent = item.prompt || '';
  if (lbPromptBox) lbPromptBox.style.display = item.prompt ? 'block' : 'none';
  var lbLabel = lbPromptBox ? lbPromptBox.querySelector('.lb-prompt-label') : null;
  if (lbLabel) lbLabel.textContent = '📝 生视频提示词';
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
  if (!item) { console.error('[Gallery] 未找到图片数据 itemId:', itemId); alert('无法打开图片：未找到数据'); return; }
  if (!item.local_path) { console.error('[Gallery] local_path 为空:', item); alert('无法打开图片：路径无效'); return; }
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
  var opts = '<option value="">所有 Provider</option>';
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
  el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">加载中...</div>';
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
      var scoreLabel = scTotal >= 80 ? '优秀' : scTotal >= 50 ? '良好' : '待优化';

      var html = '';

      // ── 评分卡片 ──
      html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:16px;">';
      html += _dashCard('🏆 综合评分', '<div style="font-size:36px;font-weight:800;color:' + scoreColor + ';">' + scTotal + '</div><div style="font-size:11px;color:var(--text-muted);">' + scoreLabel + '</div>', scoreColor);
      html += _dashCard('🖼 图片生成', '<div style="font-size:28px;font-weight:700;color:var(--accent);">' + (stImg.total || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">成功 ' + (stImg.success || 0) + ' / 失败 ' + (stImg.failed || 0) + '</div>');
      html += _dashCard('🎬 视频生成', '<div style="font-size:28px;font-weight:700;color:var(--accent-2);">' + (stVid.total || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">成功 ' + (stVid.success || 0) + ' / 失败 ' + (stVid.failed || 0) + '</div>');
      html += _dashCard('⏱ 平均耗时', '<div style="font-size:28px;font-weight:700;color:var(--accent);">' + (stImg.avg_time || 0) + 's</div><div style="font-size:11px;color:var(--text-muted);">图片生成</div>');
      html += '</div>';

      // ── 评分详情 + 系统信息 ──
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">';
      html += '<div class="glass-card" style="padding:16px;display:flex;flex-direction:column;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">🏆 评分详情</div>';
      html += '<div style="flex:1;display:flex;flex-direction:column;justify-content:space-between;">';
      html += _scoreBar('连通性', scConn, 40, '#5b8def');
      html += _scoreBar('配置完整', scConf, 30, '#22d3a5');
      html += _scoreBar('磁盘空间', scDisk, 15, '#a78bfa');
      html += _scoreBar('依赖状态', scDep, 15, '#f59e0b');
      var totalScore = scConn + scConf + scDisk + scDep;
      var totalMax = 100;
      var scoreColor = totalScore >= 80 ? '#22c55e' : totalScore >= 50 ? '#f59e0b' : '#ef4444';
      html += '<div style="display:flex;align-items:center;justify-content:space-between;padding-top:8px;border-top:1px solid var(--border);margin-top:4px;">';
      html += '<span style="font-size:11px;color:var(--text-muted);">综合评分</span>';
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
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">💻 系统信息</div>';
      html += _infoRow('操作系统', '<span style="font-weight:600;">' + escHtml(s.os || '-') + '</span>');
      html += _infoRow('架构', escHtml(s.arch || '-') + ' (' + escHtml(s.machine || '-') + ')');
      html += _infoRow('主机名', escHtml(s.hostname || '-'));
      html += _infoRow('Python', escHtml(s.python || '-'));
      html += _infoRow('运行时间', _fmtUptime(s.uptime_seconds || 0));
      html += _infoRow('磁盘空间', diskFree + ' GB 可用 / ' + diskTotal + ' GB');
      html += _infoRow('磁盘使用率', '<div style="flex:1;margin-left:10px;"><div style="height:6px;border-radius:3px;background:var(--bg-base);overflow:hidden;"><div style="height:100%;width:' + diskPct + '%;background:' + (diskPct > 90 ? '#ef4444' : diskPct > 70 ? '#f59e0b' : '#22c55e') + ';border-radius:3px;"></div></div></div><span style="font-size:11px;margin-left:6px;">' + diskPct + '%</span>');
      html += _infoRow('图库', galleryCount + ' 张 · ' + gallerySize);
      html += _infoRow('视频库', videoCount + ' 个 · ' + videoSize);
      html += '</div>';
      html += '</div>';

      // ── Provider 概览（分组） ──
      html += _renderProviderGroups(providers);

      // ── 最近活动 + 宿主机资源 ──
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">';

      // Left: 最近活动
      html += '<div class="glass-card" style="padding:16px;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">📋 最近活动</div>';
      if (logs.length === 0) {
        html += '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">暂无活动记录</div>';
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
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">💻 宿主机资源</div>';
      html += '<div id="hostResPanel" style="display:flex;flex-direction:column;gap:8px;">';
      html += '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:11px;">加载中...</div>';
      html += '</div>';
      html += '</div>';

      html += '</div>';

      // ── 快捷导航 ──
      html += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">';
      html += _quickNav('✨', '生图', "switchNav('generate',document.getElementById('navGen'))");
      html += _quickNav('🎬', '生视频', "switchNav('video',document.getElementById('navVideo'))");
      html += _quickNav('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>', '媒体库', "switchNav('gallery',document.getElementById('navGallery'))");
      html += _quickNav('📜', '历史', "switchNav('history',document.getElementById('navHistory'))");
      html += '</div>';

      el.innerHTML = html;
      _loadIpInfo();
      _loadHostResources();
    })
    .catch(function(e) {
      el.innerHTML = '<div style="text-align:center;padding:40px;color:#ef4444;">加载失败: ' + escHtml(e.message) + '</div>';
    });
}

function _renderProviderGroups(providers) {
  // 两级分类 - 根据 capabilities 字段或关键字推断能力
  var cats = {
    '🎨 生图模型': { '文生图': [], '图生图': [] },
    '🎬 生视频模型': { '文生视频': [], '图生视频': [] },
    '🤖 LLM模型': { '_flat': [] }
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
      cats['🤖 LLM模型']['_flat'].push(p);
    } else if (ptype === 'video') {
      cats['🎬 生视频模型']['文生视频'].push(p);
      if (hasI2V) {
        cats['🎬 生视频模型']['图生视频'].push(p);
      }
    } else {
      // image 类型 → 文生图 + 图生图
      cats['🎨 生图模型']['文生图'].push(p);
      if (hasI2I) {
        cats['🎨 生图模型']['图生图'].push(p);
      }
      // 同时有 video 模型 → 归入生视频
      var hasT2V = modelStr.indexOf('t2v') !== -1 || modelStr.indexOf('veo_') !== -1;
      if (hasT2V || hasI2V) {
        cats['🎬 生视频模型']['文生视频'].push(p);
        if (hasI2V) {
          cats['🎬 生视频模型']['图生视频'].push(p);
        }
      }
    }
  }

  function _renderProviderCard(p) {
    var statusDot = p.configured ? (p.enabled ? '#22c55e' : '#f59e0b') : '#6b7280';
    var statusText = p.configured ? (p.enabled ? '已启用' : '已禁用') : '未配置';
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

  var html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">';

  // ── Left: Provider 概览 ──
  html += '<div class="glass-card" style="padding:16px;min-width:0;overflow:hidden;">';
  html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">';
  html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);">🔌 模型 Provider</div>';
  html += '<button onclick="runConnectivityTest()" id="connTestBtn" style="font-size:11px;padding:4px 12px;border-radius:6px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;transition:all 0.2s;">⚡ 一键连通性检测</button>';
  html += '</div>';

  var catKeys = ['🎨 生图模型', '🎬 生视频模型', '🤖 LLM模型'];
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
  html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:14px;">🌐 本机 IP 信息</div>';
  html += '<div id="ipInfoPanel" style="display:flex;flex-direction:column;gap:10px;">';
  html += '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:11px;">加载中...</div>';
  html += '</div>';
  html += '</div>';

  html += '</div>';
  return html;
}

function runConnectivityTest() {
  var btn = document.getElementById('connTestBtn');
  if (btn) { btn.textContent = '⏳ 检测中...'; btn.disabled = true; btn.style.opacity = '0.6'; }

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
              msEl.textContent = '无地址';
              msEl.style.color = '#6b7280';
            } else {
              msEl.textContent = '不通';
              msEl.style.color = '#ef4444';
            }
          }
          card.style.borderColor = r.status === 'ok' ? (r.ms < 500 ? '#22c55e40' : '#f59e0b40') : '#ef444440';
        }
      }
      if (btn) { btn.textContent = '✅ 检测完成'; setTimeout(function(){ btn.textContent = '⚡ 一键连通性检测'; btn.disabled = false; btn.style.opacity = '1'; }, 2000); }
    })
    .catch(function() {
      if (btn) { btn.textContent = '❌ 检测失败'; setTimeout(function(){ btn.textContent = '⚡ 一键连通性检测'; btn.disabled = false; btn.style.opacity = '1'; }, 2000); }
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
      html += '<button onclick="toggleIpVisibility(this)" data-real="' + escAttr(ip) + '" data-shown="1" style="font-size:11px;padding:2px 6px;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-muted);cursor:pointer;transition:all 0.15s;" title="显示/隐藏 IP">👁</button>';
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
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">基础物理画像</div>';
      function _ipRow(label, val, color) {
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:10px;border-bottom:1px solid var(--border);">' +
          '<span style="color:var(--text-muted);">' + label + '</span>' +
          '<span style="color:' + (color || 'var(--text-primary)') + ';font-weight:600;max-width:55%;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escHtml(String(val)) + '">' + escHtml(String(val)) + '</span></div>';
      }
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px;">';
      html += _ipRow('IP 原生性', nativeType, isNative ? '#22c55e' : '#f59e0b');
      html += _ipRow('业务标记', ispType.replace(/.*[（(]/, '').replace(/[）)].*/, '') || '-', ispFlag === 'hosting' ? '#f59e0b' : '#22c55e');
      html += _ipRow('运营类型', ispType, ispFlag === 'hosting' ? '#f59e0b' : '#22c55e');
      html += _ipRow('归属机构', org);
      html += '</div></div>';

      // Section 2: ISP 网络底层
      html += '<div style="padding:12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);">';
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">ISP 网络底层</div>';
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px;">';
      html += _ipRow('ASN', asn, '#5b8def');
      html += _ipRow('解析时区', timezone);
      html += _ipRow('偏移量 (Drift)', driftKm + ' km', hasDrift ? '#ef4444' : '#22c55e');
      html += _ipRow('反向 DNS (rDNS)', rdns === 'None' ? 'None' : rdns);
      html += '</div></div>';

      // Section 3: 风险深度检测
      html += '<div style="padding:12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);">';
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">风险深度检测</div>';
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px;">';
      var spamColor = threatListed ? '#ef4444' : '#22c55e';
      var spamText = threatListed ? '⚠ 已入库 (危险)' : '✅ 纯净无异常';
      html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:10px;border-bottom:1px solid var(--border);"><span style="color:var(--text-muted);">Spamhaus 情报</span><span style="color:' + spamColor + ';font-weight:600;">' + spamText + '</span></div>';
      var proxyText = ispWarning || (ispFlag === 'hosting' ? '数据中心特征' : '未配置 rDNS (骨干网/基站中性特征)');
      html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:10px;border-bottom:1px solid var(--border);"><span style="color:var(--text-muted);">代理/机房特征</span><span style="color:' + (ispFlag === 'hosting' ? '#f59e0b' : '#22c55e') + ';font-weight:600;font-size:10px;max-width:55%;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escHtml(proxyText) + '">' + escHtml(proxyText) + '</span></div>';
      html += _ipRow('数据源', dataSource);
      html += '</div></div>';

      html += '</div>';

      // ── Network Health Brief Section ──
      var netTips = [];
      if (ispFlag === 'hosting') {
        netTips.push('⚠️ 数据中心 IP 特征识别 · 部分 AI 服务可能限制请求');
      }
      if (threatListed) {
        netTips.push('🚨 Spamhaus 黑名单命中 · 高风险操作建议更换 IP');
      }
      if (hasDrift) {
        netTips.push('🌍 地理偏移 ' + driftKm + 'km · 时区差异影响服务匹配');
      }
      if (rdns === 'None') {
        netTips.push('🔍 无 rDNS 记录 · 反垃圾系统信任评分降低');
      }
      netTips.push('📊 网络环境综合评估：' + (ispFlag === 'hosting' ? '需优化' : '良好'));
      netTips.push('🛡️ 建议：定期检测 IP 信誉 · 独享代理避免污染');
      netTips.push('⚡ TCP 延迟 ' + (tcpRtt !== null ? tcpRtt + 'ms' : '未检测') + ' · ' + (tcpRtt !== null && tcpRtt < 200 ? '链路质量优秀' : tcpRtt !== null && tcpRtt < 500 ? '链路质量一般' : '待评估'));
      netTips.push('🔐 数据源：' + (dataSource || '边缘计算直出') + ' · 时效性 24h');

      var netTipText = netTips.join('　　　');

      // 计算综合网络评分
      var netScore = 100;
      if (ispFlag === 'hosting') netScore -= 25;
      if (threatListed) netScore -= 30;
      if (hasDrift) netScore -= 10;
      if (rdns === 'None') netScore -= 15;
      var netGrade = netScore >= 80 ? 'A' : netScore >= 60 ? 'B' : netScore >= 40 ? 'C' : 'D';
      var netColor = netScore >= 80 ? '#22c55e' : netScore >= 60 ? '#f59e0b' : '#ef4444';
      var netLabel = netScore >= 80 ? '优秀' : netScore >= 60 ? '良好' : netScore >= 40 ? '一般' : '较差';

      html += '<div style="padding:12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);display:flex;flex-direction:column;">';
      html += '<div style="font-size:11px;font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:0.3px;">🌐 网络体检简报</div>';

      // Score row
      html += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;padding:6px 8px;border-radius:6px;background:var(--bg-base);border:1px solid var(--border);">';
      html += '<span style="font-size:20px;font-weight:800;color:' + netColor + ';">' + netGrade + '</span>';
      html += '<div style="flex:1;">';
      html += '<div style="font-size:10px;font-weight:600;color:' + netColor + ';">' + netLabel + ' (' + netScore + '分)</div>';
      html += '<div style="font-size:9px;color:var(--text-muted);">' + escHtml(country) + ' · ' + escHtml(ispType) + ' · ' + escHtml(asn) + '</div>';
      html += '</div>';
      html += '<div style="text-align:right;">';
      html += '<div style="font-size:9px;color:var(--text-muted);">Spamhaus</div>';
      html += '<div style="font-size:10px;font-weight:600;color:' + (threatListed ? '#ef4444' : '#22c55e') + ';">' + (threatListed ? '已入库' : '纯净') + '</div>';
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
      panel.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:11px;">IP 信息加载失败</div>';
    });
}

function toggleIpVisibility(btn) {
  var ipEl = document.getElementById('ipValue');
  if (!ipEl) return;
  var shown = btn.dataset.shown === '1';
  if (shown) {
    ipEl.textContent = '***.***.***.***';
    btn.dataset.shown = '0';
  } else {
    ipEl.textContent = btn.dataset.real;
    btn.dataset.shown = '1';
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
      html += _resBar('CPU', d.cpu_percent + '% · ' + d.cpu_count + '核' + (d.cpu_count_physical ? '/' + d.cpu_count_physical + '物理' : '') + (d.cpu_freq_mhz ? ' · ' + d.cpu_freq_mhz + 'MHz' : ''), d.cpu_percent, cpuColor);
      // Memory
      html += _resBar('内存', d.mem_used_gb + ' / ' + d.mem_total_gb + ' GB · 可用 ' + d.mem_available_gb + ' GB', d.mem_percent, memColor);
      // Swap
      if (d.swap_total_gb > 0) {
        html += _resBar('Swap', d.swap_used_gb + ' / ' + d.swap_total_gb + ' GB', d.swap_percent, swapColor);
      }
      // Disk
      html += _resBar('磁盘', d.disk_used_gb + ' / ' + d.disk_total_gb + ' GB · 空闲 ' + d.disk_free_gb + ' GB', d.disk_percent, diskColor);

      // Network IO
      html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);">';
      html += '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">网络 I/O</div>';
      html += '<div style="display:flex;gap:8px;">';
      html += '<div style="flex:1;text-align:center;padding:4px;border-radius:6px;background:var(--bg-base);">';
      html += '<div style="font-size:12px;font-weight:700;color:#22c55e;">↑ ' + d.net_sent_mb + ' MB</div>';
      html += '<div style="font-size:8px;color:var(--text-muted);">发送</div>';
      html += '</div>';
      html += '<div style="flex:1;text-align:center;padding:4px;border-radius:6px;background:var(--bg-base);">';
      html += '<div style="font-size:12px;font-weight:700;color:#5b8def;">↓ ' + d.net_recv_mb + ' MB</div>';
      html += '<div style="font-size:8px;color:var(--text-muted);">接收</div>';
      html += '</div>';
      html += '</div></div>';

      // Uptime
      var upSec = d.uptime_seconds || 0;
      var upDays = Math.floor(upSec / 86400);
      var upHours = Math.floor((upSec % 86400) / 3600);
      var upMins = Math.floor((upSec % 3600) / 60);
      var upStr = (upDays > 0 ? upDays + '天 ' : '') + upHours + '时 ' + upMins + '分';
      html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;font-size:10px;">';
      html += '<span style="color:var(--text-muted);">运行时间</span>';
      html += '<span style="color:var(--text-primary);font-weight:600;">' + upStr + '</span>';
      html += '</div>';

      // Top processes
      if (d.top_processes && d.top_processes.length > 0) {
        html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);">';
        html += '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Top 进程</div>';
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
      panel.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:11px;">资源信息加载失败</div>';
    });
}

function _loadNetStatus() {
  var bar = document.getElementById('netStatusBar');
  if (!bar) return;
  bar.innerHTML = '<span style="font-size:10px;color:var(--text-muted);">检测中...</span>';

  _authFetch('/api/dashboard/network')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var results = d.results || {};
      var names = ['OpenAI', 'Gemini', 'Anthropic', 'Agnes', 'Qwen', 'Zhipu', 'Volcengine', 'Baidu', 'Tencent', 'Moonshot', 'DeepSeek', 'MiniMax'];
      var html = '<span title="TCP 连接耗时（非 API 响应时间），用于判断网络可达性" style="font-size:9px;color:var(--text-muted);padding:2px 6px;border-radius:8px;background:var(--bg-base);border:1px solid var(--border);cursor:help;">🌐 网络连通</span>';
      for (var i = 0; i < names.length; i++) {
        var n = names[i];
        var r = results[n] || {status:'error', ms:0};
        var dot = r.status === 'ok' ? (r.ms < 800 ? '#22c55e' : r.ms < 2000 ? '#f59e0b' : '#ef4444') : '#ef4444';
        var label = r.status === 'ok' ? r.ms + 'ms' : '✗';
        html += '<div title="' + n + (r.status === 'ok' ? ' TCP连接 ' + r.ms + 'ms' : ' 不可达') + '" style="display:flex;align-items:center;gap:3px;padding:3px 8px;border-radius:12px;background:var(--bg-base);border:1px solid var(--border);font-size:10px;">';
        html += '<span style="width:6px;height:6px;border-radius:50%;background:' + dot + ';flex-shrink:0;"></span>';
        html += '<span style="color:var(--text-secondary);">' + n + '</span>';
        html += '<span style="color:' + dot + ';font-weight:600;font-variant-numeric:tabular-nums;">' + label + '</span>';
        html += '</div>';
      }
      bar.innerHTML = html;
    })
    .catch(function() {
      bar.innerHTML = '<span style="font-size:10px;color:#ef4444;">网络检测失败</span>';
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
  return '<div class="glass-card" style="padding:14px;text-align:center;cursor:pointer;transition:transform 0.15s;" onclick="' + onclick + '" onmouseover="this.style.transform=\'translateY(-2px)\'" onmouseout="this.style.transform=\'none\'">' +
    '<div style="font-size:24px;margin-bottom:4px;">' + icon + '</div>' +
    '<div style="font-size:12px;font-weight:600;color:var(--text-primary);">' + label + '</div>' +
  '</div>';
}

function serverControl(action) {
  if (action === 'stop') {
    if (!confirm('确定要停止服务器吗？')) return;
  }
  if (action === 'restart') {
    if (!confirm('确定要重启服务器吗？')) return;
  }
  _authFetch('/api/server/control?action=' + action)
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (action === 'stop') {
        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--text-muted);font-size:16px;">⏹ 服务器已停止</div>';
      } else if (action === 'restart') {
        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--text-muted);font-size:16px;">🔄 服务器重启中，请稍候...</div>';
        setTimeout(function(){ location.reload(); }, 5000);
      }
    })
    .catch(function(e) {
      alert('操作失败: ' + e.message);
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
      h.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:60px;font-size:13px;">暂无历史记录</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < items.length; i++) {
      (function(item){
        var isVideo = item.type === 'video';
        var ok = 0;
        for (var k in item.results) { if (item.results[k].success) ok++; }
        var modeTag = isVideo ? '🎬 视频' : (item.mode === 'i2i' ? '🖼 图生图' : '📝 文生图');
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
            '<span style="color:' + (ok === item.providers.length ? '#22c3a5' : '#fbbf24') + ';">' + ok + '/' + item.providers.length + ' 成功</span>' +
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
    h.innerHTML = '<div style="text-align:center;color:#f87171;padding:40px;">加载失败</div>';
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
          badge.textContent = '未启用';
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
        badge.textContent = '未启用';
        badge.style.background = '#6b728022';
        badge.style.color = '#6b7280';
      }
    }
    var result = document.getElementById('proxyTestResult');
    if (result) result.innerHTML = '<span style="color:#22c55e;">✓ 代理配置已保存</span>';
  });
}

function testProxyConfig() {
  var btn = document.getElementById('proxyTestBtn');
  var result = document.getElementById('proxyTestResult');
  if (btn) { btn.textContent = '⏳ 测试中...'; btn.disabled = true; }
  if (result) result.innerHTML = '<span style="color:var(--text-muted);">正在测试代理连通性...</span>';

  _authFetch('/api/proxy/test', { method: 'POST' })
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (btn) { btn.textContent = '测试连接'; btn.disabled = false; }
      if (!d.ok) {
        var msgs = [];
        var keys = Object.keys(d.results || {});
        for (var i = 0; i < keys.length; i++) {
          var r = d.results[keys[i]];
          msgs.push(keys[i] + ': ' + (r.status === 'ok' ? r.ms + 'ms ✓' : '✗ ' + (r.error || '不通')));
        }
        if (result) result.innerHTML = '<span style="color:#f59e0b;">⚠ 部分不通</span><br>' + msgs.join('<br>');
      } else {
        var msgs2 = [];
        var keys2 = Object.keys(d.results || {});
        for (var j = 0; j < keys2.length; j++) {
          var r2 = d.results[keys2[j]];
          msgs2.push(keys2[j] + ': ' + r2.ms + 'ms ✓');
        }
        if (result) result.innerHTML = '<span style="color:#22c55e;">✓ 代理连通正常</span><br>' + msgs2.join('<br>');
      }
    })
    .catch(function(e) {
      if (btn) { btn.textContent = '测试连接'; btn.disabled = false; }
      if (result) result.innerHTML = '<span style="color:#ef4444;">✗ 测试失败: ' + escHtml(e.message) + '</span>';
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
        platformEl.textContent = '当前: v' + d.current_version + ' | ' + (typeLabel[d.update_type] || d.update_type);
      }
      // 检查更新
      _checkForUpdates();
    })
    .catch(function() {
      var el = document.getElementById('updateContent');
      if (el) el.innerHTML = '<span style="color:var(--text-muted);">无法获取更新信息</span>';
    });
}

function _checkForUpdates() {
  var badge = document.getElementById('updateStatusBadge');
  var content = document.getElementById('updateContent');
  if (badge) { badge.textContent = '检测中...'; badge.style.background = '#6b728022'; badge.style.color = '#6b7280'; }
  if (content) content.innerHTML = '<span style="color:var(--text-muted);">正在检查更新...</span>';

  _authFetch('/api/update/check')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (d.available) {
        if (badge) { badge.textContent = '有新版本'; badge.style.background = '#f59e0b22'; badge.style.color = '#f59e0b'; }
        var notes = d.release_notes ? '<div style="margin:6px 0;padding:8px;border-radius:6px;background:var(--bg-card);max-height:120px;overflow-y:auto;white-space:pre-wrap;font-size:10px;color:var(--text-secondary);">' + escHtml(d.release_notes) + '</div>' : '';
        if (content) {
          content.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">' +
            '<span style="color:#f59e0b;font-weight:600;">⬆ v' + d.latest_version + ' 可用</span>' +
            '<button onclick="_testMirrors()" style="padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">🔍 测速</button>' +
            '<button onclick="_applyUpdate()" style="padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer;">立即更新</button>' +
            '</div>' + notes;
        }
      } else {
        if (badge) { badge.textContent = '已是最新'; badge.style.background = '#22c55e22'; badge.style.color = '#22c55e'; }
        if (content) content.innerHTML = '<span style="color:#22c55e;">✓ 已是最新版本</span> <button onclick="_checkForUpdates()" style="margin-left:8px;padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">重新检测</button>';
      }
    })
    .catch(function(e) {
      if (badge) { badge.textContent = '检测失败'; badge.style.background = '#ef444422'; badge.style.color = '#ef4444'; }
      if (content) content.innerHTML = '<span style="color:#ef4444;">✗ 检测失败: ' + escHtml(e.message) + '</span>';
    });
}

function _testMirrors() {
  var content = document.getElementById('updateContent');
  if (content) content.innerHTML = '<span style="color:var(--text-muted);">正在测试 GitHub 代理线路...</span>';

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
          html += '<button onclick="_applyUpdate(\'' + escHtml(m.url) + '\')" style="padding:2px 6px;font-size:9px;border-radius:4px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;">使用此线路更新</button>';
        }
        html += '</div>';
      }
      html += '</div>';
      html += '<button onclick="_checkForUpdates()" style="margin-top:8px;padding:3px 8px;font-size:10px;border-radius:5px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;">返回</button>';
      if (content) content.innerHTML = html;
    })
    .catch(function(e) {
      if (content) content.innerHTML = '<span style="color:#ef4444;">✗ 测速失败: ' + escHtml(e.message) + '</span>';
    });
}

function _applyUpdate(downloadUrl) {
  var badge = document.getElementById('updateStatusBadge');
  var content = document.getElementById('updateContent');
  if (badge) { badge.textContent = '更新中...'; badge.style.background = '#3b82f622'; badge.style.color = '#3b82f6'; }
  if (content) content.innerHTML = '<span style="color:#3b82f6;">⏳ 正在更新，请勿关闭页面...</span>';

  var url = '/api/update/apply';
  if (downloadUrl) url += '?download_url=' + encodeURIComponent(downloadUrl);

  _authFetch(url, { method: 'POST' })
    .then(function(r){ return r.json(); })
    .then(function(d) {
      if (d.ok) {
        if (badge) { badge.textContent = '更新成功'; badge.style.background = '#22c55e22'; badge.style.color = '#22c55e'; }
        if (content) content.innerHTML = '<span style="color:#22c55e;">✓ ' + escHtml(d.message || '更新成功') + '</span>';
        if (d.restart) {
          if (content) content.innerHTML += '<br><span style="color:var(--text-muted);font-size:10px;">服务将在 3 秒后重启...</span>';
          setTimeout(function(){ location.reload(); }, 3000);
        }
      } else {
        if (badge) { badge.textContent = '更新失败'; badge.style.background = '#ef444422'; badge.style.color = '#ef4444'; }
        if (content) content.innerHTML = '<span style="color:#ef4444;">✗ ' + escHtml(d.error || '更新失败') + '</span>';
      }
    })
    .catch(function(e) {
      if (badge) { badge.textContent = '更新失败'; badge.style.background = '#ef444422'; badge.style.color = '#ef4444'; }
      if (content) content.innerHTML = '<span style="color:#ef4444;">✗ 更新失败: ' + escHtml(e.message) + '</span>';
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
    setStatus('密钥已复制到剪贴板');
  });
}
function confirmWelcome() {
  document.getElementById('welcomePage').style.display = 'none';
  // 首次设置向导
  document.getElementById('setupWizard').style.display = 'flex';
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
  document.getElementById('setupWizard').style.display = 'none';
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
  if (llmKey) saves.push(saveWizardProvider('llm-default', '提示词优化', 'llm', llmUrl || '', llmKey, '#a855f7'));

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
  html += '<input type="checkbox" id="proxyEnabled" style="accent-color:var(--accent);width:14px;height:14px;"> 启用代理';
  html += '</label>';
  html += '<select id="proxyType" style="padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<option value="http">HTTP</option>';
  html += '<option value="socks5">SOCKS5</option>';
  html += '</select>';
  html += '<input type="text" id="proxyHost" placeholder="主机 IP" style="width:120px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);" value="127.0.0.1">';
  html += '<input type="number" id="proxyPort" placeholder="端口" style="width:70px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);" value="10808">';
  html += '<input type="text" id="proxyUser" placeholder="用户名(可选)" style="width:100px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
  html += '<input type="password" id="proxyPass" placeholder="密码(可选)" style="width:100px;padding:5px 8px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-primary);">';
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
  html += '<div id="updateContent" style="font-size:11px;color:var(--text-muted);">正在检查更新...</div>';
  html += '</div>';

  // 加载更新信息
  _loadUpdateInfo();

  var groups = [
    { type: 'image', icon: '🎨', title: '生图模型', hint: '用于生成图片的模型，如 Stable Diffusion、Midjourney、Flux 等', accent: '#22c55e' },
    { type: 'video', icon: '🎬', title: '生视频模型', hint: '用于生成视频的模型，如 Gemini Veo、Sora 等', accent: '#3b82f6' },
    { type: 'llm', icon: '🤖', title: '提示词优化', hint: '用于优化提示词的大语言模型，如 GPT-4o、Claude 等', accent: '#f59e0b' },
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
      var modelOpts = '';
      if (p.models && p.models.length) {
        var filteredModels = filterModelsByType(p.models, p.type);
        var groupFn = p.type === 'video' ? groupVideoModels : (p.type === 'image' ? groupImageModels : null);
        modelOpts = (groupFn && filteredModels.length > 3)
          ? buildModelOptsGrouped(filteredModels, p.model || '', groupFn)
          : filteredModels.map(function(m){ return '<option value="' + escAttr(m) + '"' + (p.model===m?' selected':'') + '>' + escHtml(m) + '</option>'; }).join('');
        if (filteredModels.length === 0 && p.models.length > 0) {
          modelOpts = '<option value="" disabled>无匹配当前类型的模型 (共' + p.models.length + '个)</option>';
        }
      } else {
        modelOpts = '<option value="" disabled>请先拉取模型</option>';
        if (p.model) modelOpts = '<option value="' + escAttr(p.model) + '" selected>' + escHtml(p.model) + ' (手动)</option>' + modelOpts;
      }
      var keyVal = p.api_key_masked || '';
      var keyPlaceholder = p.has_key ? (keyVal || '•••••••••• (已配置)') : '留空使用 .env 或手动输入';
      var statusColor = p.enabled ? '#22c55e' : '#6b7280';
      var statusTitle = p.enabled ? '已启用' : '已禁用';

      // 单个 Provider 卡片
      html += '<div style="margin-bottom:8px;border:1px solid ' + (isOpen ? group.accent : 'var(--border)') + ';border-radius:8px;background:var(--bg-card);overflow:hidden;transition:border-color 0.2s;">' +
        // 摘要行（始终显示，点击展开）
        '<div style="display:flex;align-items:center;padding:10px 12px;cursor:pointer;gap:8px;" onclick="toggleProviderEdit(' + idx + ')">' +
          '<input type="color" class="color-dot" value="' + (p.color||'#5b8def') + '" id="color_' + idx + '" onclick="event.stopPropagation();" style="width:22px;height:22px;border-radius:6px;border:none;cursor:pointer;flex-shrink:0;">' +
          '<div style="flex:1;min-width:0;">' +
            '<div style="display:flex;align-items:center;gap:6px;">' +
              '<span style="font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(p.name) + '</span>' +
              '<span style="width:5px;height:5px;border-radius:50%;background:' + statusColor + ';flex-shrink:0;" title="' + statusTitle + '"></span>' +
              (p.key_count > 1 ? '<span style="font-size:9px;padding:1px 5px;border-radius:6px;background:#3b82f622;color:#3b82f6;font-weight:600;flex-shrink:0;" title="' + p.key_count + ' 个 API Key 轮询">🔑×' + p.key_count + '</span>' : '') +
            '</div>' +
            '<div style="font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
              escHtml(p.model || '未选模型') + (p.base_url ? ' · ' + escHtml(p.base_url.replace(/^https?:\/\//, '').substring(0, 30)) : '') +
            '</div>' +
          '</div>' +
          '<div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">' +
            '<button onclick="event.stopPropagation();testProvider(\'' + p.id + '\')" style="font-size:9px;padding:3px 8px;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-secondary);cursor:pointer;white-space:nowrap;">测试</button>' +
            '<button onclick="event.stopPropagation();deleteProvider(\'' + p.id + '\')" style="font-size:9px;padding:3px 8px;border-radius:4px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;white-space:nowrap;">删除</button>' +
            '<span style="font-size:10px;color:var(--text-muted);transition:transform 0.2s;display:inline-block;transform:rotate(' + (isOpen ? '90' : '0') + 'deg);">▶</span>' +
          '</div>' +
        '</div>';

      // 展开的编辑区
      if (isOpen) {
        html += '<div style="padding:0 12px 12px;border-top:1px solid var(--border);">' +
          '<div style="padding-top:10px;">' +
            // 名称 + 类型
            '<div style="display:flex;gap:6px;margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="显示名称" value="' + escHtml(p.name) + '" id="name_' + idx + '">' +
              '<select class="modal-input" style="width:88px;padding:6px 8px;font-size:11px;" id="type_' + idx + '" onchange="updateCapsSection(' + idx + ')">' +
                '<option value="image" ' + (p.type==='image'?'selected':'') + '>🎨 生图</option>' +
                '<option value="video" ' + (p.type==='video'?'selected':'') + '>🎬 生视频</option>' +
                '<option value="llm" ' + (p.type==='llm'?'selected':'') + '>🤖 LLM</option>' +
              '</select>' +
            '</div>' +
            // 看板显示名
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">' +
              '<span style="font-size:10px;color:var(--text-muted);white-space:nowrap;">看板名</span>' +
              '<input type="text" class="modal-input" style="flex:1;padding:5px 8px;font-size:11px;" placeholder="留空使用上方名称" value="' + escHtml(p.display_name || '') + '" id="display_name_' + idx + '">' +
            '</div>' +
            // Provider ID
            '<div style="margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="width:100%;padding:6px 10px;font-size:11px;box-sizing:border-box;" placeholder="Provider ID (唯一标识)" value="' + escHtml(p.id) + '" id="id_' + idx + '" ' + (p.id?'readonly style="padding:6px 10px;font-size:11px;background:var(--bg-surface);box-sizing:border-box;"':'') + '>' +
            '</div>' +
            // URL + API Key
            '<div style="display:flex;gap:6px;margin-bottom:8px;">' +
              '<input type="text" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="Base URL" value="' + escHtml(p.base_url) + '" id="url_' + idx + '">' +
              '<input type="password" class="modal-input" style="flex:1;padding:6px 10px;font-size:11px;" placeholder="' + keyPlaceholder + '" value="' + escHtml(keyVal) + '" id="key_' + idx + '">' +
            '</div>' +
            // 多账号轮询（api_keys）
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">🔄 多账号轮询（可选，每行一个 Key）</span>' +
                (p.keypool ? '<span style="font-size:9px;padding:2px 6px;border-radius:8px;background:' + (p.keypool.available_keys > 0 ? '#22c55e22;color:#22c55e' : '#ef444422;color:#ef4444') + ';font-weight:600;">' + p.keypool.available_keys + '/' + p.keypool.total_keys + ' 可用</span>' : '') +
              '</div>' +
              '<textarea class="modal-input" id="keys_' + idx + '" rows="3" style="width:100%;padding:6px 10px;font-size:10px;font-family:monospace;resize:vertical;box-sizing:border-box;" placeholder="sk-xxx1&#10;sk-xxx2&#10;sk-xxx3&#10;（留空则使用上方单个 API Key）">' + escHtml((p.api_keys || []).join('\n')) + '</textarea>' +
              (p.keypool && p.keypool.keys ? '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">' + p.keypool.keys.map(function(k,i){ return '<span style="font-size:9px;padding:2px 6px;border-radius:6px;border:1px solid ' + (k.available ? '#22c55e44' : '#ef444444') + ';background:' + (k.available ? '#22c55e11' : '#ef444411') + ';color:' + (k.available ? '#22c55e' : '#ef4444') + ';" title="连续失败:' + k.fail_count + ' 成功:' + k.total_calls + '">' + (k.available ? '🟢' : '🔴') + ' ' + escHtml(k.key) + (k.cooldown_remaining > 0 ? ' ⏳' + Math.ceil(k.cooldown_remaining) + 's' : '') + '</span>'; }).join('') + '</div>' : '') +
            '</div>' +
            // 多端点（endpoints）
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">🌐 多端点容灾（可选，端点失效自动切换）</span>' +
                '<span id="epCount_' + idx + '" style="font-size:9px;color:var(--text-muted);">' + (p.endpoints ? p.endpoints.length : 0) + ' 个端点</span>' +
              '</div>' +
              '<div id="epList_' + idx + '" style="display:flex;flex-direction:column;gap:6px;">' +
                (p.endpoints || []).map(function(ep, ei) {
                  return '<div class="ep-item" style="border-radius:8px;border:1px solid var(--border);background:var(--bg-base);padding:8px 10px;">' +
                    // Row 1: Name + controls
                    '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">' +
                      '<span style="font-size:9px;color:var(--text-muted);flex-shrink:0;">#' + (ei+1) + '</span>' +
                      '<input type="text" placeholder="端点备注名（如：主站、备用）" value="' + escAttr(ep.name || '') + '" data-ep-idx="' + ei + '" data-field="name" style="flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-weight:500;">' +
                      '<label style="display:flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);cursor:pointer;flex-shrink:0;" title="启用/禁用此端点">' +
                        '<input type="checkbox" ' + (ep.enabled !== false ? 'checked' : '') + ' data-ep-idx="' + ei + '" data-field="enabled" style="accent-color:#22c55e;width:13px;height:13px;">' +
                        '<span>启用</span>' +
                      '</label>' +
                      '<button onclick="removeEndpoint(' + idx + ',' + ei + ')" title="删除此端点" style="font-size:10px;padding:3px 7px;border-radius:5px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;flex-shrink:0;">✕</button>' +
                    '</div>' +
                    // Row 2: URL + Key
                    '<div style="display:flex;gap:6px;">' +
                      '<input type="text" placeholder="URL（如 https://api.example.com/v1）" value="' + escAttr(ep.url || '') + '" data-ep-idx="' + ei + '" data-field="url" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
                      '<input type="password" placeholder="API Key" value="' + escAttr(ep.key || '') + '" data-ep-idx="' + ei + '" data-field="key" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
                    '</div>' +
                  '</div>';
                }).join('') +
              '</div>' +
              '<button onclick="addEndpoint(' + idx + ')" style="margin-top:6px;font-size:10px;padding:4px 10px;border-radius:6px;border:1px dashed var(--border);background:transparent;color:var(--accent);cursor:pointer;display:flex;align-items:center;gap:4px;">+ 添加端点</button>' +
            '</div>' +
            // 模型选择
            '<div style="margin-bottom:8px;">' +
              '<div style="display:flex;gap:6px;align-items:center;margin-bottom:3px;">' +
                '<span style="font-size:10px;color:var(--text-muted);">默认模型</span>' +
                '<span style="font-size:9px;color:var(--accent);">↻ 从上游拉取</span>' +
                (p.models && p.models.length ? '<span style="font-size:9px;color:var(--text-muted);">(' + filterModelsByType(p.models, p.type).length + '/' + p.models.length + ' 匹配' + p.type + ')</span>' : '') +
              '</div>' +
              '<div style="display:flex;gap:6px;">' +
                '<select class="modal-input" style="flex:1;padding:6px 8px;font-size:11px;" id="model_' + idx + '">' + modelOpts + '</select>' +
                '<button class="btn-secondary" onclick="fetchModels(' + idx + ')" id="fetchBtn_' + idx + '" style="flex-shrink:0;padding:6px 10px;font-size:10px;">↻ 拉取</button>' +
              '</div>' +
              '<div id="fetchStatus_' + idx + '" style="font-size:10px;color:var(--text-muted);margin-top:2px;"></div>' +
            '</div>' +
            // 能力声明（根据类型显示不同选项）
            '<div id="capsSection_' + idx + '" style="margin-bottom:8px;">' +
              (p.type === 'llm' ? '' :
                '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">🎯 模型能力（勾选此项支持的功能）</div>' +
                '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
                  (p.type === 'image' ?
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="t2i" ' + ((p.capabilities && p.capabilities.t2i !== false) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> 文生图' +
                    '</label>' +
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="i2i" ' + ((p.capabilities && p.capabilities.i2i) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> 图生图' +
                    '</label>'
                  :
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="t2v" ' + ((p.capabilities && p.capabilities.t2v) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> 文生视频' +
                    '</label>' +
                    '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
                      '<input type="checkbox" class="cap-check" data-cap="i2v" ' + ((p.capabilities && p.capabilities.i2v) ? 'checked' : '') + ' style="accent-color:var(--accent);width:13px;height:13px;"> 图生视频' +
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

  body.innerHTML = html || '<div style="color:var(--text-muted);text-align:center;padding:40px;font-size:13px;">暂无 Provider，点击上方 [+ 添加] 创建</div>';
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
    quality: '', extra: {}
  };
  _authFetch('/api/providers', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(p)
  }).then(function(r){ return r.json(); }).then(function(data){
    setStatus('Provider "' + p.name + '" 已保存');
    loadProviders().then(function(){
      renderProviderEdit();
    });
  }).catch(function(e){ if (e.message !== 'AUTH_REQUIRED') setStatus('保存失败: ' + e.message); });
}

function updateCapsSection(idx) {
  var type = document.getElementById('type_' + idx).value;
  var section = document.getElementById('capsSection_' + idx);
  if (!section) return;

  if (type === 'llm') {
    section.innerHTML = '';
  } else if (type === 'image') {
    section.innerHTML =
      '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">🎯 模型能力（勾选此项支持的功能）</div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="t2i" checked style="accent-color:var(--accent);width:13px;height:13px;"> 文生图' +
        '</label>' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="i2i" style="accent-color:var(--accent);width:13px;height:13px;"> 图生图' +
        '</label>' +
      '</div>' +
      '<div style="font-size:9px;color:var(--text-muted);margin-top:3px;">留空则自动根据模型名称和协议推断</div>';
  } else if (type === 'video') {
    section.innerHTML =
      '<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">🎯 模型能力（勾选此项支持的功能）</div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="t2v" checked style="accent-color:var(--accent);width:13px;height:13px;"> 文生视频' +
        '</label>' +
        '<label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--text-secondary);cursor:pointer;">' +
          '<input type="checkbox" class="cap-check" data-cap="i2v" style="accent-color:var(--accent);width:13px;height:13px;"> 图生视频' +
        '</label>' +
      '</div>' +
      '<div style="font-size:9px;color:var(--text-muted);margin-top:3px;">留空则自动根据模型名称和协议推断</div>';
  }
}

function deleteProvider(id) {
  if (!confirm('确定删除 "' + id + '"？')) return;
  _authFetch('/api/providers/' + id, {method:'DELETE'}).then(function(r){return r.json();}).then(function(){
    setStatus('已删除: ' + id);
    loadProviders().then(function(){
      renderProviderEdit();
    });
  }).catch(function(e){ setStatus('删除失败: ' + e.message); });
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
      '<input type="text" placeholder="端点备注名（如：主站、备用）" data-ep-idx="' + ei + '" data-field="name" style="flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-weight:500;">' +
      '<label style="display:flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);cursor:pointer;flex-shrink:0;" title="启用/禁用此端点">' +
        '<input type="checkbox" checked data-ep-idx="' + ei + '" data-field="enabled" style="accent-color:#22c55e;width:13px;height:13px;">' +
        '<span>启用</span>' +
      '</label>' +
      '<button onclick="removeEndpoint(' + idx + ',' + ei + ')" title="删除此端点" style="font-size:10px;padding:3px 7px;border-radius:5px;border:1px solid #f8717133;background:transparent;color:#f87171;cursor:pointer;flex-shrink:0;">✕</button>' +
    '</div>' +
    '<div style="display:flex;gap:6px;">' +
      '<input type="text" placeholder="URL（如 https://api.example.com/v1）" data-ep-idx="' + ei + '" data-field="url" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
      '<input type="password" placeholder="API Key" data-ep-idx="' + ei + '" data-field="key" style="flex:1;padding:5px 8px;border:1px solid var(--border);border-radius:5px;background:var(--bg-card);color:var(--text-primary);font-size:11px;font-family:monospace;">' +
    '</div>';
  list.appendChild(div);
  // Focus the name input
  var nameInput = div.querySelector('[data-field="name"]');
  if (nameInput) nameInput.focus();
  var cnt = document.getElementById('epCount_' + idx);
  if (cnt) cnt.textContent = list.children.length + ' 个端点';
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
  if (cnt) cnt.textContent = remaining.length + ' 个端点';
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
  if (btn) { btn.disabled = true; btn.textContent = '测试中...'; }
  _authFetch('/api/providers/test/' + id).then(function(r){return r.json();}).then(function(d){
    if (d.endpoints && d.endpoints.length > 0) {
      var lines = d.endpoints.map(function(ep) {
        var icon = ep.success ? '✅' : '❌';
        var latency = ep.latency_ms ? ep.latency_ms + 'ms' : '';
        var name = ep.name || ep.url;
        return icon + ' ' + name + (ep.success ? ' (' + latency + ')' : ' - ' + (ep.error || '失败') + ' (' + latency + ')');
      });
      alert((d.success ? '✅ 至少一个端点可用' : '❌ 所有端点失败') + '\n\n' + lines.join('\n'));
    } else {
      alert(d.success ? '✅ 测试成功!' : '❌ 失败: ' + (d.error||''));
    }
  }).catch(function(e){ alert('❌ 测试失败: ' + e.message); })
  .finally(function(){ if (btn) { btn.disabled = false; btn.textContent = '测试'; } });
}

function fetchModels(idx) {
  var pid = document.getElementById('id_' + idx).value;
  var urlVal = document.getElementById('url_' + idx).value;
  var keyVal = document.getElementById('key_' + idx).value;
  var nameVal = document.getElementById('name_' + idx).value;
  var typeVal = document.getElementById('type_' + idx).value;
  var colorVal = document.getElementById('color_' + idx).value;
  var enVal = document.getElementById('en_' + idx).checked;

  var btn = document.getElementById('fetchBtn_' + idx);
  var st  = document.getElementById('fetchStatus_' + idx);
  btn.disabled = true; btn.textContent = '...';
  st.textContent = '连接中...'; st.style.color = 'var(--text-muted)';

  var tmp = { id:pid||'tmp', name:nameVal, type:typeVal, base_url:urlVal, api_key:keyVal, model:'', color:colorVal, enabled:enVal, models:[], quality:'', extra:{} };

    _authFetch('/api/providers', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(tmp)})
    .then(function(){ return _authFetch('/api/providers/fetch-models/' + pid); })
    .then(function(r){ return r.json(); })
    .then(function(data){
      if (data.success) {
        st.textContent = '✅ 拉取成功 ' + data.count + ' 个模型' + (data.is_fallback ? ' (推荐列表)' : '');
        st.style.color = '#22c3a5';
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
      btn.disabled = false; btn.textContent = '↻ 拉取';
    });
}

function reloadProviders() {
  _authFetch('/api/providers/reload', {method:'POST'}).then(function(){
    loadProviders().then(function(){ renderProviderEdit(); });
    setStatus('配置已重新加载');
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
    btn.textContent = '✕ 退出选择';
    btn.style.borderColor = 'var(--accent)';
    btn.style.color = 'var(--accent)';
    btn.classList.add('active');
    showGalleryToolbar(true);
  } else {
    btn.textContent = '☑ 选择模式';
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
  if (!selectedGalleryItems.length) { alert('请先选择要删除的图片'); return; }
  if (!confirm('确定删除选中的 ' + selectedGalleryItems.length + ' 张图片？此操作不可撤销。')) return;
  _authFetch('/api/gallery/batch-delete', { method:'POST', body:JSON.stringify(selectedGalleryItems) })
    .then(function(r){return r.json();}).then(function(d){ setStatus('已删除 '+d.total_deleted+' 张图片'); selectedGalleryItems=[]; loadGallery(); })
    .catch(function(e){ alert('删除失败: '+e.message); });
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
  var body=document.getElementById('logBody'); body.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:30px;font-size:12px;">加载中...</div>';
  var url='/api/logs?limit=100'; if(currentLogCategory) url+='&category='+currentLogCategory;
  fetch(url).then(function(r){return r.json();}).then(function(d){
    var items=d.items||[];
    if(!items.length){ body.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:40px;font-size:13px;">📋 暂无日志</div>'; return; }
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
  }).catch(function(e){ body.innerHTML='<div style="text-align:center;color:#f87171;padding:40px;">加载失败</div>'; });
}
function clearLogs(){ if(!confirm('确定清空所有日志？'))return;   _authFetch('/api/logs',{method:'DELETE'}).then(function(){loadLogs();setStatus('日志已清空');}); }


// ═══════════════════════════════════════════════════════════════════
// 主题系统（8 套预设）
// ═══════════════════════════════════════════════════════════════════
var THEME_PRESETS=[
  {name:'🌌 深空蓝（默认）',id:'default',vars:{'--bg-base':'#0c0e14','--bg-surface':'#12151e','--bg-card':'#181c28','--bg-card-hover':'#1e2233','--border':'#262d3f','--border-light':'#2f3750','--accent':'#5b8def','--accent-glow':'rgba(91,141,239,0.25)','--accent-2':'#22d3a5','--accent-3':'#a78bfa','--accent-yellow':'#fbbf24','--text-primary':'#e2e8f0','--text-secondary':'#8892aa','--text-muted':'#4b5568'},colors:['#0c0e14','#181c28','#5b8def','#22d3a5']},
  {name:'🖤 墨夜黑',id:'midnight',vars:{'--bg-base':'#08090c','--bg-surface':'#0e1015','--bg-card':'#14161e','--bg-card-hover':'#1a1d27','--border':'#1e222e','--border-light':'#282d3b','--accent':'#e2e8f0','--accent-glow':'rgba(226,232,240,0.12)','--accent-2':'#94a3b8','--accent-3':'#cbd5e1','--accent-yellow':'#fbbf24','--text-primary':'#f1f5f9','--text-secondary':'#94a3b8','--text-muted':'#475569'},colors:['#08090c','#14161e','#e2e8f0','#94a3b8']},
  {name:'💚 极光绿',id:'aurora',vars:{'--bg-base':'#070a08','--bg-surface':'#0c100d','--bg-card':'#121814','--bg-card-hover':'#182019','--border':'#1a241d','--border-light':'#253329','--accent':'#34d399','--accent-glow':'rgba(52,211,153,0.2)','--accent-2':'#60a5fa','--accent-3':'#c084fc','--accent-yellow':'#fbbf24','--text-primary':'#ecfdf5','--text-secondary':'#86efac','--text-muted':'#4ade80'},colors:['#070a08','#121814','#34d399','#60a5fa']},
  {name:'🔥 琥珀橙',id:'amber',vars:{'--bg-base':'#0c0a07','--bg-surface':'#13100b','--bg-card':'#1c170f','--bg-card-hover':'#261f15','--border':'#2e2518','--border-light':'#3d3120','--accent':'#f59e0b','--accent-glow':'rgba(245,158,11,0.2)','--accent-2':'#fb923c','--accent-3':'#f472b6','--accent-yellow':'#fcd34d','--text-primary':'#fef3c7','--text-secondary':'#fcd34d','--text-muted':'#92400e'},colors:['#0c0a07','#1c170f','#f59e0b','#fb923c']},
  {name:'💜 赛博紫',id:'cyber',vars:{'--bg-base':'#0a0612','--bg-surface':'#110b1c','--bg-card':'#181028','--bg-card-hover':'#20163a','--border':'#2a1e42','--border-light':'#3d2d5c','--accent':'#a78bfa','--accent-glow':'rgba(167,139,250,0.2)','--accent-2':'#f472b6','--accent-3':'#38bdf8','--accent-yellow':'#facc15','--text-primary':'#ede9fe','--text-secondary':'#c4b5fd','--text-muted':'#7c3aed'},colors:['#0a0612','#181028','#a78bfa','#f472b6']},
  {name:'❄️ 冰川白',id:'glacier',vars:{'--bg-base':'#e8edf2','--bg-surface':'#f0f4f8','--bg-card':'#ffffff','--bg-card-hover':'#f8fafc','--border':'#d1d9e6','--border-light':'#bcc8dc','--accent':'#2563eb','--accent-glow':'rgba(37,99,235,0.12)','--accent-2':'#059669','--accent-3':'#7c3aed','--accent-yellow':'#d97706','--text-primary':'#1e293b','--text-secondary':'#475569','--text-muted':'#94a3b8'},colors:['#e8edf2','#ffffff','#2563eb','#059669']},
  {name:'🌸 樱花粉',id:'sakura',vars:{'--bg-base':'#120a0e','--bg-surface':'#1a1020','--bg-card':'#24182c','--bg-card-hover':'#2e2040','--border':'#3a2848','--border-light':'#4e3658','--accent':'#f472b6','--accent-glow':'rgba(244,114,182,0.2)','--accent-2':'#fb7185','--accent-3':'#a78bfa','--accent-yellow':'#fbbf24','--text-primary':'#fce7f3','--text-secondary':'#f9a8d4','--text-muted':'#be185d'},colors:['#120a0e','#24182c','#f472b6','#fb7185']},
  {name:'🏝 海洋蓝',id:'ocean',vars:{'--bg-base':'#041215','--bg-surface':'#091a1f','--bg-card':'#0c232b','--bg-card-hover':'#10303a','--border':'#153845','--border-light':'#1c4d5e','--accent':'#38bdf8','--accent-glow':'rgba(56,189,248,0.18)','--accent-2':'#2dd4bf','--accent-3':'#818cf8','--accent-yellow':'#fbbf24','--text-primary':'#e0f2fe','--text-secondary':'#7dd3fc','--text-muted':'#0369a1'},colors:['#041215','#0c232b','#38bdf8','#2dd4bf']}
];
function openThemeModal(){document.getElementById('themeModal').classList.add('show');renderThemePresets();}
function closeThemeModal(){document.getElementById('themeModal').classList.remove('show');}
function renderThemePresets(){
  var c=document.getElementById('themePresets'); var activeId=localStorage.getItem('igs_theme')||'default'; var h='';
  for(var i=0;i<THEME_PRESETS.length;i++){(function(p){
    var isActive=p.id===activeId; var dots=p.colors.map(function(c){return'<div class="theme-preview-dot" style="background:'+c+';"></div>';}).join('');
    h+='<div class="theme-preset'+(isActive?' active':'')+'" onclick="applyTheme(\''+p.id+'\')"><div style="display:flex;align-items:center;justify-content:space-between;"><span style="font-size:13px;font-weight:600;color:var(--text-primary);">'+p.name+'</span>'+(isActive?'<span style="font-size:10px;color:var(--accent);">✓ 当前使用</span>':'')+'</div><div class="theme-preview">'+dots+'</div></div>';
  })(THEME_PRESETS[i]);}
  c.innerHTML=h;
}
function applyTheme(id){
  var preset=null;
  for(var i=0;i<THEME_PRESETS.length;i++){if(THEME_PRESETS[i].id===id){preset=THEME_PRESETS[i];break;}}
  if(!preset)return; var root=document.documentElement; var vars=preset.vars;
  for(var key in vars) root.style.setProperty(key,vars[key]);
  localStorage.setItem('igs_theme',id); renderThemePresets(); setStatus('已切换主题: '+preset.name);
}
(function(){ var s=localStorage.getItem('igs_theme'); if(s&&s!=='default') applyTheme(s); })();


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
      list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:30px;font-size:12px;">暂无 LLM Provider，请先在 Provider 设置中添加</div>';
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
  setStatus('已选择 LLM Provider: ' + id);
}

// ═══════════════════════════════════════════════════════════════════
// LLM 预览优化
// ═══════════════════════════════════════════════════════════════════
var llmPreviewData = null;
var llmOriginalPrompt = ''; // 存储优化前的原始提示词
function previewLLMOptimize(){
  var prompt = document.getElementById('txtPrompt').value.trim();
  if(!prompt){ alert('请先输入提示词'); return; }
  llmOriginalPrompt = prompt; // 保存原始提示词
  var btn = document.getElementById('btnPreviewLLM');
  var box = document.getElementById('llmPreviewBox');
  btn.textContent = '⏳ 优化中...';
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
    btn.textContent = '✨ 重新优化';
    btn.disabled = false;
  }).catch(function(e){
    document.getElementById('llmPreviewError').textContent = '⚠️ 请求失败: ' + e.message;
    document.getElementById('llmPreviewError').style.display = 'block';
    btn.textContent = '✨ 点击优化';
    btn.disabled = false;
  });
}
function insertLLMPreview(){
  if(!llmPreviewData || !llmPreviewData.optimized) return;
  document.getElementById('txtPrompt').value = llmPreviewData.optimized;
  closeLLMPreview();
  setStatus('已插入优化后的提示词');
}
function closeLLMPreview(){
  document.getElementById('llmPreviewBox').style.display = 'none';
  llmPreviewData = null;
}
function undoLLMOptimize(){
  if(llmOriginalPrompt){
    document.getElementById('txtPrompt').value = llmOriginalPrompt;
    llmOriginalPrompt = '';
    setStatus('已撤销优化，恢复原始提示词');
  }
}


// ═══════════════════════════════════════════════════════════════════
// 图库: 重命名 + 推送图生图
// ═══════════════════════════════════════════════════════════════════
function galleryStartRename() {
  if (!selectedGalleryItems.length) { alert('请先选择要重命名的图片'); return; }
  if (selectedGalleryItems.length > 1) { alert('重命名仅支持单张，请只选一张'); return; }
  var oldId = selectedGalleryItems[0];
  // 提取当前模型名（下划线前的部分）
  var currentName = oldId.split('_')[0] || '';
  var newName = prompt('输入新名称（仅字母数字下划线中文）：', currentName);
  if (!newName || newName === currentName) return;
  _authFetch('/api/gallery/rename', {
    method: 'POST',
    body: JSON.stringify({old_id: oldId, new_name: newName})
  }).then(function(r){
    if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || '重命名失败'); });
    return r.json();
  }).then(function(d){
    setStatus('已重命名: ' + oldId + ' → ' + d.new_id);
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
  }).catch(function(e){ alert('重命名失败: ' + e.message); });
}

function pushGalleryToReference() {
  if (!selectedGalleryItems.length) { alert('请先选择要推送的图片'); return; }
  if (selectedGalleryItems.length > 1) { alert('推送仅支持单张，请只选一张'); return; }
  var itemId = selectedGalleryItems[0];
  // 从 DOM 获取文件名
  var el = document.querySelector('.gallery-item[data-id="' + itemId + '"]');
  var fname = el ? el.getAttribute('data-fname') : '';
  if (!fname) { alert('无法获取图片文件名'); return; }

  setStatus('正在加载参考图片...');
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
      setStatus('已推送到参考图片区域，可以输入修改提示词后生图');
    })
    .catch(function(e){ alert('推送失败: ' + e.message); });
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
    else if (msg.indexOf('完成') !== -1) stage = '[完成] ';
    else if (msg.indexOf('失败') !== -1 || msg.indexOf('出错') !== -1) stage = '[错误] ';
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
  _authFetch('/api/providers').then(function(r){ return r.json(); }).then(function(data){
    videoProviders = (data.providers || []).filter(function(p){ return p.type === 'video'; });
    renderVideoProviderCards();
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
      if (ml.indexOf('veo_') !== -1) return true;
      if (ml.indexOf('interpolation') !== -1) return true;
      if (ml.indexOf('video') !== -1) return true;
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
      cat = '视频放大 (Upsample)';
    } else if (ml.indexOf('i2v') !== -1) {
      if (ml.indexOf('veo_3') !== -1) cat = 'Veo 3.x 图生视频 (I2V)';
      else if (ml.indexOf('veo_2') !== -1) cat = 'Veo 2.x 图生视频 (I2V)';
      else cat = '图生视频 (I2V)';
    } else if (ml.indexOf('r2v') !== -1) {
      cat = 'Veo 3.x 多图视频 (R2V)';
    } else if (ml.indexOf('interpolation') !== -1) {
      cat = '插帧 (Interpolation)';
    } else if (ml.indexOf('t2v') !== -1 || ml.indexOf('veo_') !== -1) {
      if (ml.indexOf('veo_3') !== -1) cat = 'Veo 3.x 文生视频 (T2V)';
      else if (ml.indexOf('veo_2') !== -1) cat = 'Veo 2.x 文生视频 (T2V)';
      else cat = '文生视频 (T2V)';
    } else {
      cat = '其他';
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
    container.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px 0;">&#35831;&#20808;&#22312;&#35774;&#32622;&#20013;&#28155;&#21152;&#35270;&#39057; Provider</div>';
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
                '<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:var(--accent);color:#fff;margin-left:4px;">\u63A8\u8350</span>'
              : '<span style="font-size:12px;font-weight:600;color:var(--text-primary);">' + escHtml(getProviderDisplayName(p.id)) + '</span>' +
                '<span style="font-size:10px;color:var(--text-muted);">' + escHtml(p.name) + '</span>'
            ) +
          '</div>' +
          '<div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">' +
            capBadges +
            '<button onclick="refreshProviderModels(\'' + p.id + '\')" title="&#21047;&#26032;&#27169;&#22411;" style="font-size:10px;padding:2px 6px;border-radius:4px;border:1px solid var(--border);background:var(--bg-surface);color:var(--text-secondary);cursor:pointer;">&#8635;</button>' +
          '</div>' +
        '</div>' +
        '<div style="display:flex;gap:4px;margin-bottom:6px;">' +
          '<div style="flex:1;">' +
            '<div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">&#27169;&#22411; <span style="color:var(--accent);font-size:9px;">(' + (activeMode === 'ti2vid' ? '\u6587\u751F\u89C6\u9891' : activeMode === 'i2vid' ? '\u56FE\u751F\u89C6\u9891' : '\u5173\u952E\u5E27') + ')</span></div>' +
            '<select id="vmodel_' + p.id + '" onchange="onVideoModelChange()" ' + (!isSelected ? 'disabled' : '') + ' style="width:100%;font-size:11px;padding:5px 8px;background:var(--bg-base);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);' + (!isSelected ? 'opacity:0.5;' : '') + '">' +
              (modelOpts || '<option value="">&#26080;&#21487;&#29992;&#27169;&#22411;</option>') +
            '</select>' +
          '</div>' +
        '</div>' +
      '</div>';
    })(videoProviders[i], i);
  }
  html = '<div style="font-size:10px;color:var(--text-muted);margin-bottom:8px;">&#21452;&#20987;&#22810;&#20010; Provider &#21487;&#21516;&#26102;&#21521;&#22810;&#20010;&#27169;&#22411;&#25552;&#20132;&#20219;&#52;</div>' + html;
  container.innerHTML = html;
  updateVideoGenerateButton();
}

function toggleVideoProvider(vpid) {
  var idx = selectedVideoProviderIds.indexOf(vpid);
  if (idx !== -1) {
    selectedVideoProviderIds.splice(idx, 1);
  } else {
    selectedVideoProviderIds.push(vpid);
  }
  renderVideoProviderCards();
}

function updateVideoGenerateButton() {
  var btn = document.getElementById('videoGenBtn');
  if (!btn) return;
  var count = selectedVideoProviderIds.length;
  if (count === 0) {
    btn.textContent = '\u{1F680} \u9009\u62E9 Provider \u540E\u751F\u6210';
    btn.disabled = true;
  } else if (count === 1) {
    btn.textContent = '\u{1F680} \u751F\u6210\u89C6\u9891';
    btn.disabled = false;
  } else {
    btn.textContent = '\u{1F680} \u540C\u65F6\u5411 ' + count + ' \u4E2A Provider \u63D0\u4EA4';
    btn.disabled = false;
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
      sel.innerHTML = models.map(function(m){ return '<option value="' + m + '">' + m + '</option>'; }).join('') || '<option value="">无可用模型</option>';
    }
    renderVideoProviderCards();
    setStatus(prov.name + ' 模型已刷新 (' + models.length + '个)');
  }).catch(function(e) {
    if (btn) { btn.textContent = '↻'; btn.disabled = false; }
    setStatus('模型刷新失败: ' + e.message);
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
      setStatus('⚠ 部分选中 Provider 不支持图生视频模式');
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
      setStatus('⚠ 部分选中 Provider 不支持关键帧模式');
    }
  }
  renderVideoProviderCards();
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
  setStatus('正在加载图库图片...');
  _authFetch('/api/preview/images').then(function(r){ return r.json(); }).then(function(data){
    var items = data.items || [];
    if (items.length === 0) {
      alert('图库暂无图片，请先生成图片');
      return;
    }
    showVideoImagePickerModal(items);
  }).catch(function(e){ alert('加载失败: ' + e.message); });
}

function showVideoImagePickerModal(items) {
  // 创建临时弹窗
  var overlay = document.createElement('div');
  overlay.id = 'videoPickerOverlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
  var box = document.createElement('div');
  box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:20px;max-width:600px;width:90%;max-height:70vh;overflow-y:auto;';
  box.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><h3 style="font-size:14px;font-weight:700;">🎯 选择图片</h3><button onclick="document.getElementById(\'videoPickerOverlay\').remove()" style="background:none;border:none;color:var(--text-secondary);font-size:18px;cursor:pointer;">✕</button></div>' +
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
      setStatus('已添加图片');
    };
    grid.appendChild(card);
  });
}

// 生成视频
function startVideoGenerate() {
  var prompt = document.getElementById('videoPrompt').value.trim();
  if (!prompt) { alert('请输入视频提示词'); return; }

  // Multi-provider: collect selected providers and models
  if (selectedVideoProviderIds.length === 0) {
    alert('请先选择至少一个视频 Provider');
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
    alert('请为每个选中的 Provider 选择视频模型');
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
    if (!confirm('帧数 ' + frames + ' 不符合 8n+1 规则，已修正为 ' + corrected + '。继续吗？')) return;
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
    container.innerHTML = '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:20px;">暂无视频</div>';
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
  if (countEl) countEl.textContent = allItems.length + ' 个结果';
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
        if (!cur) { viewerWrap.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:20px;">无完成的视频</div>'; return; }

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
          viewerWrap.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:20px;text-align:center;">⚠ 视频地址为空，可能仍在处理中或下载失败</div>';
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
          errDiv.innerHTML = '<span style="flex-shrink:0;">⚠</span><span>' + escHtml(fi.error || '生成失败') + '</span>';
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
  if (!src) { alert('没有视频可下载'); return; }
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
    alert('视频首帧已推送');
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
  if (!src) { alert('没有视频可下载'); return; }
  downloadVideoFromSrc(src);
}

function pushVideoToGallery() {
  var src = '';
  Object.keys(videoPreviewGroups).forEach(function(pid) {
    var items = videoPreviewGroups[pid].filter(function(i){ return i.status === 'completed'; });
    var idx = videoGroupNavIdx[pid] || 0;
    if (items[idx]) src = items[idx].video_url_local || items[idx].video_url || '';
  });
  if (!src) { alert('没有视频'); return; }
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
