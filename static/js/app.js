(function(){
'use strict';

/* ═══════════════════════════════════════════════════════════════════
   Utility Functions
   ═══════════════════════════════════════════════════════════════════ */

function escHtml(s) {
  var d = document.createElement('div'); d.textContent = s||''; return d.innerHTML;
}
function escAttr(s) {
  return (s||'').replace(/'/g,'&#39;').replace(/"/g,'&quot;');
}
function setStatus(msg) {
  document.getElementById('statusLeft').textContent = msg;
}

window.escHtml = escHtml;
window.escAttr = escAttr;
window.setStatus = setStatus;

/* ═══════════════════════════════════════════════════════════════════
   Global State
   ═══════════════════════════════════════════════════════════════════ */
window.allProviders = [];
window.selectedProviders = [];
window.currentMode = 't2i';
window.uploadedImageData = null;
window.continuousSessionId = null;
window.currentResults = {};
window.currentGroupTimings = {};
window.quickPrompts = {};
window.providerQuantities = {};

window.previewImages = [];
window.previewIndex = 0;
window.previewGroups = {};
window.failedGroups = {};
window.lightboxZoom = 1;

window.onQtyChange = function(sel) {
  var v = parseInt(sel.value);
  if (isNaN(v) || v < 1) v = 1;
  if (v > 4) v = 4;
  sel.value = v;
  window.providerQuantities[sel.dataset.pid] = v;
};

window.adjustQty = function(pid, delta) {
  var input = document.querySelector('.provider-qty[data-pid="' + pid + '"]');
  if (!input) return;
  var v = parseInt(input.value) + delta;
  if (isNaN(v) || v < 1) v = 1;
  if (v > 4) v = 4;
  input.value = v;
  window.providerQuantities[pid] = v;
};

/* ═══════════════════════════════════════════════════════════════════
   Quick Prompts Data
   ═══════════════════════════════════════════════════════════════════ */
window.QUICK_PROMPTS = {
  "\u{1F3AC} \u98CE\u683C": [
    {label: "\u7535\u5F71\u611F\u753B\u9762", en: "Cinematic lighting, 21:9 widescreen, 8K HDR, volumetric lighting, film grain"},
    {label: "\u8D5B\u535A\u6717\u514B\u57CE\u5E02", en: "Cyberpunk neon city at night, rain reflections, hyper-realistic, Unreal Engine 5"},
    {label: "\u5546\u4E1A\u4EA7\u54C1\u6444\u5F71", en: "Studio product photography, white background, soft box lighting, commercial grade"},
    {label: "\u6CB9\u753B\u98CE\u683C", en: "Oil painting style, classical, Renaissance technique, rich textures"},
    {label: "\u6C34\u5F69\u63D2\u753B", en: "Watercolor illustration, soft gradients, delicate brushwork"},
    {label: "\u52A8\u6F2B\u98CE\u683C", en: "Anime style, vibrant colors, Studio Ghibli inspired, detailed background"},
    {label: "\u50CF\u7D20\u827A\u672F", en: "Pixel art, 16-bit, retro gaming aesthetic, nostalgic"},
    {label: "\u4F4E\u591A\u8FB9\u5F623D", en: "Low-poly 3D render, geometric, clean, minimal design"}
  ],
  "\u{1F458} \u53E4\u98CE": [
    {label: "\u4ED9\u4FA0\u53E4\u98CE", en: "Xianxia fantasy, ethereal beauty in flowing hanfu, ice lotus glow cyan light, cinematic"},
    {label: "\u5927\u5510\u5BAB\u5EF7", en: "Tang dynasty palace scene, silk robes, traditional architecture, golden hour light"},
    {label: "\u6C34\u58A8\u5C71\u6C34", en: "Ancient Chinese landscape painting style, mountains and mist, ink wash"},
    {label: "\u6E05\u671D\u5BAB\u5EF7", en: "Qing Dynasty court portrait, ornate costumes, detailed embroidery"},
    {label: "\u53E4\u98CE\u6218\u58EB", en: "Fantasy warrior in ancient Chinese armor, dramatic pose, epic battle scene"}
  ],
  "\u{1F33F} \u81EA\u7136": [
    {label: "\u65E5\u51FA\u5C71\u666F", en: "Misty mountain landscape at sunrise, golden light, aerial drone view"},
    {label: "\u70ED\u5E26\u6D77\u6EE9\u65E5\u843D", en: "Tropical beach at sunset, palm trees, crystal clear water, photorealistic"},
    {label: "\u6A31\u82B1\u6EE1\u5F00", en: "Cherry blossom trees in full bloom, traditional Japanese garden, spring"},
    {label: "\u6781\u5149\u96EA\u5C71", en: "Northern lights over snowy mountains, aurora borealis, night sky"},
    {label: "\u79CB\u65E5\u68EE\u6797", en: "Autumn forest path, golden leaves, soft overcast lighting, peaceful"}
  ],
  "\u{1F3D9} \u5EFA\u7B51": [
    {label: "\u672A\u6765\u57CE\u5E02", en: "Futuristic cityscape, flying vehicles, holographic billboards, night"},
    {label: "\u4E2D\u4E16\u7EAA\u57CE\u5821", en: "Medieval European castle on cliff, storm clouds, dramatic lighting"},
    {label: "\u73B0\u4EE3\u6781\u7B80\u5EFA\u7B51", en: "Minimalist modern architecture, white concrete, geometric forms, sunlight"},
    {label: "\u53E4\u4EE3\u9057\u8FF9", en: "Ancient ruins overgrown with vegetation, mysterious atmosphere, moss"},
    {label: "\u591C\u5E02\u8857\u666F", en: "Bustling Asian night market, street food stalls, warm lantern light"}
  ],
  "\u{1F3AD} \u4EBA\u50CF": [
    {label: "\u4E13\u4E1A\u4EBA\u50CF\u6444\u5F71", en: "Professional portrait photography, studio lighting, shallow depth of field"},
    {label: "\u65F6\u5C1A\u5927\u7247", en: "Fashion editorial, editorial makeup, high-end magazine cover style"},
    {label: "\u8857\u62CD\u98CE\u683C", en: "Candid street photography, natural lighting, urban environment"},
    {label: "\u590D\u53E4\u80F6\u7247", en: "Vintage film photography aesthetic, grain, warm tones, nostalgic"},
    {label: "\u7CBE\u81F4\u4E94\u5B98\u7279\u5199", en: "Close-up beauty shot, dramatic eye detail, glossy lips, luxury cosmetics"}
  ],
  "\u{1F680} \u79D1\u5E7B": [
    {label: "\u98DE\u8239\u9A7E\u9A76\u8231", en: "Spaceship interior bridge, holographic displays, alien planet view through windows"},
    {label: "\u4EFF\u751F\u4EBA", en: "Robot android in futuristic city, chrome reflections, blue hour lighting"},
    {label: "\u5916\u661F\u5730\u8868", en: "Alien planet surface, bioluminescent flora, twin moons in sky"},
    {label: "\u6DF1\u7A7A\u7AD9", en: "Deep space station orbiting distant nebula, realistic sci-fi design"},
    {label: "\u590D\u53E4\u672A\u6765\u4E3B\u4E49", en: "Retro-futuristic 1950s sci-fi aesthetic, chrome appliances, atomic age"}
  ]
};

/* ═══════════════════════════════════════════════════════════════════
   Authentication
   ═══════════════════════════════════════════════════════════════════ */
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
    window.loadProviders();
  });
}
function _showWelcome(key) {
  document.getElementById('welcomeKeyText').textContent = key;
  document.getElementById('welcomePage').style.display = 'flex';
}
function copyWelcomeKey() {
  var key = document.getElementById('welcomeKeyText').textContent;
  navigator.clipboard.writeText(key).then(function() {
    setStatus('\u5BC6\u94A5\u5DF2\u590D\u5236\u5230\u526A\u8D34\u677F');
  });
}
function confirmWelcome() {
  document.getElementById('welcomePage').style.display = 'none';
  document.getElementById('setupWizard').style.display = 'flex';
}

/* ═══════════════════════════════════════════════════════════════════
   Setup Wizard
   ═══════════════════════════════════════════════════════════════════ */
function checkSetupWizard() {
  fetch('/api/setup/status').then(function(r){ return r.json(); }).then(function(d){
    if (d.needs_first_run) {
      fetch('/api/setup/first-run', {method:'POST'}).then(function(r){return r.json();}).then(function(data){
        _adminKey = data.admin_key;
        localStorage.setItem('igs_admin_key', data.admin_key);
        _showWelcome(data.admin_key);
      });
    } else if (d.prod_mode && !d.has_admin_key) {
      _showLogin();
    } else if (d.prod_mode && _adminKey) {
      fetch('/api/providers', {headers: {'X-Admin-Key': _adminKey}}).then(function(r) {
        if (r.status === 401) {
          localStorage.removeItem('igs_admin_key');
          _adminKey = '';
          _showLogin();
        }
      });
    }
  }).catch(function(){});
}
function closeSetupWizard() {
  document.getElementById('setupWizard').style.display = 'none';
}
function submitSetupWizard() {
  var saves = [];
  var gptUrl = document.getElementById('sw_gpt_url').value.trim();
  var gptKey = document.getElementById('sw_gpt_key').value.trim();
  var gemUrl = document.getElementById('sw_gem_url').value.trim();
  var gemKey = document.getElementById('sw_gem_key').value.trim();
  var qwenUrl = document.getElementById('sw_qwen_url').value.trim();
  var qwenKey = document.getElementById('sw_qwen_key').value.trim();
  var agnesVUrl = document.getElementById('sw_agnes_v_url').value.trim();
  var agnesVKey = document.getElementById('sw_agnes_v_key').value.trim();
  var gemVUrl = document.getElementById('sw_gem_v_url').value.trim();
  var gemVKey = document.getElementById('sw_gem_v_key').value.trim();
  var qwenVUrl = document.getElementById('sw_qwen_v_url').value.trim();
  var qwenVKey = document.getElementById('sw_qwen_v_key').value.trim();
  var llmUrl = document.getElementById('sw_llm_url').value.trim();
  var llmKey = document.getElementById('sw_llm_key').value.trim();

  if (gptKey) saves.push(saveWizardProvider('gpt-image', 'GPT Image 2', 'image', gptUrl || 'https://api.openai.com/v1', gptKey, '#22c55e'));
  if (gemKey) saves.push(saveWizardProvider('gemini', 'Gemini 3.1 Flash', 'image', gemUrl || '', gemKey, '#3b82f6'));
  if (qwenKey) saves.push(saveWizardProvider('qwen', 'Qwen2API', 'image', qwenUrl || '', qwenKey, '#f97316'));
  if (agnesVKey) saves.push(saveWizardProvider('agnes-video', 'Agnes Video', 'video', agnesVUrl || 'https://apihub.agnes-ai.com/v1', agnesVKey, '#ec4899'));
  if (gemVKey) saves.push(saveWizardProvider('gemini-video', 'Gemini Video', 'video', gemVUrl || '', gemVKey, '#6366f1'));
  if (qwenVKey) saves.push(saveWizardProvider('qwen-video', 'Qwen Video', 'video', qwenVUrl || '', qwenVKey, '#f97316'));
  if (llmKey) saves.push(saveWizardProvider('llm-default', '\u63D0\u793A\u8BCD\u4F18\u5316', 'llm', llmUrl || '', llmKey, '#a855f7'));

  if (!saves.length) { alert('\u8BF7\u81F3\u5C11\u586B\u5199\u4E00\u4E2A API Key'); return; }
  Promise.all(saves).then(function(){
    closeSetupWizard();
    window.loadProviders();
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

/* ═══════════════════════════════════════════════════════════════════
   Prompt Mode
   ═══════════════════════════════════════════════════════════════════ */
window.promptMode = 'newbie';
window.setPromptMode = function(mode){
  window.promptMode = mode;
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
};

window.getFinalPrompt = function(){
  if(window.promptMode==='pro'){
    var sys = document.getElementById('txtSysPrompt').value.trim();
    var user = document.getElementById('txtUserPrompt').value.trim();
    if(!user) return '';
    return sys ? (sys + '\n\n' + user) : user;
  }
  return document.getElementById('txtPrompt').value.trim();
};

/* ═══════════════════════════════════════════════════════════════════
   Theme System
   ═══════════════════════════════════════════════════════════════════ */
window.THEME_PRESETS=[
  {name:'\u{1F30C} \u6DF1\u7A7A\u84DD\uFF08\u9ED8\u8BA4\uFF09',id:'default',vars:{'--bg-base':'#0c0e14','--bg-surface':'#12151e','--bg-card':'#181c28','--bg-card-hover':'#1e2233','--border':'#262d3f','--border-light':'#2f3750','--accent':'#5b8def','--accent-glow':'rgba(91,141,239,0.25)','--accent-2':'#22d3a5','--accent-3':'#a78bfa','--accent-yellow':'#fbbf24','--text-primary':'#e2e8f0','--text-secondary':'#8892aa','--text-muted':'#4b5568'},colors:['#0c0e14','#181c28','#5b8def','#22d3a5']},
  {name:'\u{1F5A4} \u58A8\u591C\u9ED1',id:'midnight',vars:{'--bg-base':'#08090c','--bg-surface':'#0e1015','--bg-card':'#14161e','--bg-card-hover':'#1a1d27','--border':'#1e222e','--border-light':'#282d3b','--accent':'#e2e8f0','--accent-glow':'rgba(226,232,240,0.12)','--accent-2':'#94a3b8','--accent-3':'#cbd5e1','--accent-yellow':'#fbbf24','--text-primary':'#f1f5f9','--text-secondary':'#94a3b8','--text-muted':'#475569'},colors:['#08090c','#14161e','#e2e8f0','#94a3b8']},
  {name:'\u{1F49A} \u6781\u5149\u7EFF',id:'aurora',vars:{'--bg-base':'#070a08','--bg-surface':'#0c100d','--bg-card':'#121814','--bg-card-hover':'#182019','--border':'#1a241d','--border-light':'#253329','--accent':'#34d399','--accent-glow':'rgba(52,211,153,0.2)','--accent-2':'#60a5fa','--accent-3':'#c084fc','--accent-yellow':'#fbbf24','--text-primary':'#ecfdf5','--text-secondary':'#86efac','--text-muted':'#4ade80'},colors:['#070a08','#121814','#34d399','#60a5fa']},
  {name:'\u{1F525} \u7425\u73C0\u6A59',id:'amber',vars:{'--bg-base':'#0c0a07','--bg-surface':'#13100b','--bg-card':'#1c170f','--bg-card-hover':'#261f15','--border':'#2e2518','--border-light':'#3d3120','--accent':'#f59e0b','--accent-glow':'rgba(245,158,11,0.2)','--accent-2':'#fb923c','--accent-3':'#f472b6','--accent-yellow':'#fcd34d','--text-primary':'#fef3c7','--text-secondary':'#fcd34d','--text-muted':'#92400e'},colors:['#0c0a07','#1c170f','#f59e0b','#fb923c']},
  {name:'\u{1F49C} \u8D5B\u535A\u7D2B',id:'cyber',vars:{'--bg-base':'#0a0612','--bg-surface':'#110b1c','--bg-card':'#181028','--bg-card-hover':'#20163a','--border':'#2a1e42','--border-light':'#3d2d5c','--accent':'#a78bfa','--accent-glow':'rgba(167,139,250,0.2)','--accent-2':'#f472b6','--accent-3':'#38bdf8','--accent-yellow':'#facc15','--text-primary':'#ede9fe','--text-secondary':'#c4b5fd','--text-muted':'#7c3aed'},colors:['#0a0612','#181028','#a78bfa','#f472b6']},
  {name:'\u2744\uFE0F \u51B0\u5DDD\u767D',id:'glacier',vars:{'--bg-base':'#e8edf2','--bg-surface':'#f0f4f8','--bg-card':'#ffffff','--bg-card-hover':'#f8fafc','--border':'#d1d9e6','--border-light':'#bcc8dc','--accent':'#2563eb','--accent-glow':'rgba(37,99,235,0.12)','--accent-2':'#059669','--accent-3':'#7c3aed','--accent-yellow':'#d97706','--text-primary':'#1e293b','--text-secondary':'#475569','--text-muted':'#94a3b8'},colors:['#e8edf2','#ffffff','#2563eb','#059669']},
  {name:'\u{1F338} \u6A31\u82B1\u7C89',id:'sakura',vars:{'--bg-base':'#120a0e','--bg-surface':'#1a1020','--bg-card':'#24182c','--bg-card-hover':'#2e2040','--border':'#3a2848','--border-light':'#4e3658','--accent':'#f472b6','--accent-glow':'rgba(244,114,182,0.2)','--accent-2':'#fb7185','--accent-3':'#a78bfa','--accent-yellow':'#fbbf24','--text-primary':'#fce7f3','--text-secondary':'#f9a8d4','--text-muted':'#be185d'},colors:['#120a0e','#24182c','#f472b6','#fb7185']},
  {name:'\u{1F3DF} \u6D77\u6D0B\u84DD',id:'ocean',vars:{'--bg-base':'#041215','--bg-surface':'#091a1f','--bg-card':'#0c232b','--bg-card-hover':'#10303a','--border':'#153845','--border-light':'#1c4d5e','--accent':'#38bdf8','--accent-glow':'rgba(56,189,248,0.18)','--accent-2':'#2dd4bf','--accent-3':'#818cf8','--accent-yellow':'#fbbf24','--text-primary':'#e0f2fe','--text-secondary':'#7dd3fc','--text-muted':'#0369a1'},colors:['#041215','#0c232b','#38bdf8','#2dd4bf']}
];

window.openThemeModal = function(){document.getElementById('themeModal').classList.add('show');window.renderThemePresets();};
window.closeThemeModal = function(){document.getElementById('themeModal').classList.remove('show');};
window.renderThemePresets = function(){
  var c=document.getElementById('themePresets'); var activeId=localStorage.getItem('igs_theme')||'default'; var h='';
  for(var i=0;i<window.THEME_PRESETS.length;i++){(function(p){
    var isActive=p.id===activeId; var dots=p.colors.map(function(c){return'<div class="theme-preview-dot" style="background:'+c+';"></div>';}).join('');
    h+='<div class="theme-preset'+(isActive?' active':'')+'" onclick="applyTheme(\''+p.id+'\')"><div style="display:flex;align-items:center;justify-content:space-between;"><span style="font-size:13px;font-weight:600;color:var(--text-primary);">'+p.name+'</span>'+(isActive?'<span style="font-size:10px;color:var(--accent);">\u2713 \u5F53\u524D\u4F7F\u7528</span>':'')+'</div><div class="theme-preview">'+dots+'</div></div>';
  })(window.THEME_PRESETS[i]);}
  c.innerHTML=h;
};
window.applyTheme = function(id){
  var preset=null;
  for(var i=0;i<window.THEME_PRESETS.length;i++){if(window.THEME_PRESETS[i].id===id){preset=window.THEME_PRESETS[i];break;}}
  if(!preset)return; var root=document.documentElement; var vars=preset.vars;
  for(var key in vars) root.style.setProperty(key,vars[key]);
  localStorage.setItem('igs_theme',id); window.renderThemePresets(); setStatus('\u5DF2\u5207\u6362\u4E3B\u9898: '+preset.name);
};
(function(){ var s=localStorage.getItem('igs_theme'); if(s&&s!=='default') window.applyTheme(s); })();

/* ═══════════════════════════════════════════════════════════════════
   Log System
   ═══════════════════════════════════════════════════════════════════ */
window.currentLogCategory = '';
window.openLogModal = function(){ document.getElementById('logModal').classList.add('show'); window.loadLogs(); };
window.closeLogModal = function(){ document.getElementById('logModal').classList.remove('show'); };
window.filterLog = function(cat){ window.currentLogCategory=cat; document.querySelectorAll('.log-filter-btn').forEach(function(b){b.classList.toggle('active',b.dataset.cat===cat);}); window.loadLogs(); };
window.loadLogs = function(){
  var body=document.getElementById('logBody'); body.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:30px;font-size:12px;">\u52A0\u8F7D\u4E2D...</div>';
  var url='/api/logs?limit=100'; if(window.currentLogCategory) url+='&category='+window.currentLogCategory;
  fetch(url).then(function(r){return r.json();}).then(function(d){
    var items=d.items||[];
    if(!items.length){ body.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:40px;font-size:13px;">\u{1F4CB} \u6682\u65E0\u65E5\u5FD7</div>'; return; }
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
  }).catch(function(e){ body.innerHTML='<div style="text-align:center;color:#f87171;padding:40px;">\u52A0\u8F7D\u5931\u8D25</div>'; });
};
window.clearLogs = function(){ if(!confirm('\u786E\u5B9A\u6E05\u7A7A\u6240\u6709\u65E5\u5FD7\uFF1F'))return;   _authFetch('/api/logs',{method:'DELETE'}).then(function(){window.loadLogs();setStatus('\u65E5\u5FD7\u5DF2\u6E05\u7A7A');}); };

/* ═══════════════════════════════════════════════════════════════════
   LLM Provider Settings
   ═══════════════════════════════════════════════════════════════════ */
window.selectedLLMProvider = '';
window.openLLMSettings = function(){
  document.getElementById('llmModal').classList.add('show');
  window.loadLLMProviders();
};
window.closeLLMModal = function(){ document.getElementById('llmModal').classList.remove('show'); };
window.loadLLMProviders = function(){
  var list = document.getElementById('llmProviderList');
  _authFetch('/api/providers').then(function(r){return r.json();}).then(function(d){
    var providers = (d.providers || []).filter(function(p){ return p.type === 'llm'; });
    if(!providers.length){
      list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:30px;font-size:12px;">\u6682\u65E0 LLM Provider\uFF0C\u8BF7\u5148\u5728 Provider \u8BBE\u7F6E\u4E2D\u6DFB\u52A0</div>';
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
        (isActive ? '<span style="color:var(--accent);font-size:12px;">\u2713 \u5DF2\u9009</span>' : '<span style="color:var(--text-muted);font-size:11px;">\u70B9\u51FB\u9009\u62E9</span>')+
      '</div>';
    })(providers[i]);}
    list.innerHTML = h;
  });
};
window.selectLLMProvider = function(id){
  localStorage.setItem('igs_llm_provider', id);
  window.loadLLMProviders();
  setStatus('\u5DF2\u9009\u62E9 LLM Provider: ' + id);
};

/* ═══════════════════════════════════════════════════════════════════
   LLM Preview Optimize
   ═══════════════════════════════════════════════════════════════════ */
window.llmPreviewData = null;
window.llmOriginalPrompt = '';
window.previewLLMOptimize = function(){
  var prompt = document.getElementById('txtPrompt').value.trim();
  if(!prompt){ alert('\u8BF7\u5148\u8F93\u5165\u63D0\u793A\u8BCD'); return; }
  window.llmOriginalPrompt = prompt;
  var btn = document.getElementById('btnPreviewLLM');
  var box = document.getElementById('llmPreviewBox');
  btn.textContent = '\u23F3 \u4F18\u5316\u4E2D...';
  btn.disabled = true;
  box.style.display = 'block';
  document.getElementById('llmPreviewError').style.display = 'none';

  var llmId = localStorage.getItem('igs_llm_provider') || undefined;
  _authFetch('/api/llm/optimize', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({prompt: prompt, llm_provider_id: llmId})
  }).then(function(r){ return r.json(); }).then(function(d){
    window.llmPreviewData = d;
    document.getElementById('llmPreviewOriginal').textContent = d.original;
    document.getElementById('llmPreviewOptimized').textContent = d.optimized;
    if(d.error){
      var errEl = document.getElementById('llmPreviewError');
      errEl.textContent = '\u26A0\uFE0F ' + d.error;
      errEl.style.display = 'block';
    }
    btn.textContent = '\u2728 \u91CD\u65B0\u4F18\u5316';
    btn.disabled = false;
  }).catch(function(e){
    document.getElementById('llmPreviewError').textContent = '\u26A0\uFE0F \u8BF7\u6C42\u5931\u8D25: ' + e.message;
    document.getElementById('llmPreviewError').style.display = 'block';
    btn.textContent = '\u2728 \u70B9\u51FB\u4F18\u5316';
    btn.disabled = false;
  });
};
window.insertLLMPreview = function(){
  if(!window.llmPreviewData || !window.llmPreviewData.optimized) return;
  document.getElementById('txtPrompt').value = window.llmPreviewData.optimized;
  window.closeLLMPreview();
  setStatus('\u5DF2\u63D2\u5165\u4F18\u5316\u540E\u7684\u63D0\u793A\u8BCD');
};
window.closeLLMPreview = function(){
  document.getElementById('llmPreviewBox').style.display = 'none';
  window.llmPreviewData = null;
};
window.undoLLMOptimize = function(){
  if(window.llmOriginalPrompt){
    document.getElementById('txtPrompt').value = window.llmOriginalPrompt;
    window.llmOriginalPrompt = '';
    setStatus('\u5DF2\u64A4\u9500\u4F18\u5316\uFF0C\u6062\u590D\u539F\u59CB\u63D0\u793A\u8BCD');
  }
};

/* ═══════════════════════════════════════════════════════════════════
   Add Provider Type Modal
   ═══════════════════════════════════════════════════════════════════ */
window.openAddProviderTypeModal = function() {
  document.getElementById('addProviderTypeModal').style.display = 'flex';
};
window.closeAddProviderTypeModal = function() {
  document.getElementById('addProviderTypeModal').style.display = 'none';
};
window.addProviderWithType = function(type) {
  window.closeAddProviderTypeModal();
  var defaults = {
    image: { id:'', name:'\u65B0\u751F\u56FE Provider', type:'image', api_key:'', api_keys:[], base_url:'', model:'', models:[], color:'#22c55e', enabled:true },
    video: { id:'', name:'\u65B0\u751F\u89C6\u9891 Provider', type:'video', api_key:'', api_keys:[], base_url:'', model:'', models:[], color:'#3b82f6', enabled:true },
    llm:   { id:'', name:'\u65B0 LLM Provider', type:'llm', api_key:'', api_keys:[], base_url:'', model:'', models:[], color:'#a855f7', enabled:true }
  };
  window.allProviders.push(defaults[type] || defaults.image);
  window.providerEditOpenIdx = window.allProviders.length - 1;
  window.renderProviderEdit();
};

/* ═══════════════════════════════════════════════════════════════════
   Image Settings
   ═══════════════════════════════════════════════════════════════════ */
window.RATIO_SIZES = {
  '1:1':      [1024, 1024],
  '2:3':      [832,  1248],
  '3:2':      [1248, 832],
  '3:4':      [896,  1152],
  '4:3':      [1152, 896],
  '9:16':     [768,  1360],
  '16:9':     [1360, 768],
  '21:9':     [1536, 656],
  '1:1-2k':   [1536, 1536],
  '16:9-2k':  [2048, 1152],
  '9:16-2k':  [1152, 2048],
  '21:9-2k':  [2560, 1092],
  '16:9-4k':  [4096, 2304],
  '9:16-4k':  [2304, 4096],
};

window.setRatio = function(el, ratio) {
  document.querySelectorAll('#ratioGrid .ratio-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  document.getElementById('selRatio').value = ratio;
  if (ratio === 'auto') return;
  var sz = window.RATIO_SIZES[ratio];
  if (sz) {
    document.getElementById('inputW').value = sz[0];
    document.getElementById('inputH').value = sz[1];
  }
};

window.onSizeInput = function() {
  var w = parseInt(document.getElementById('inputW').value) || 1024;
  var h = parseInt(document.getElementById('inputH').value) || 1024;
  var matched = false;
  for (var ratio in window.RATIO_SIZES) {
    var sz = window.RATIO_SIZES[ratio];
    if (sz[0] === w && sz[1] === h) {
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
};

window.setQuality = function(el, val) {
  document.querySelectorAll('#qualityBtns .quality-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  document.getElementById('selQuality').value = val;
};

window.setQty = function(el, val) {
  document.querySelectorAll('#qtyBtns .qty-btn').forEach(function(b){ b.classList.remove('active'); });
  el.classList.add('active');
  document.getElementById('selQty').value = val;
};

window.loadModelDropdown = function() {
  var sel = document.getElementById('selModel');
  var currentVal = sel.value || '_global';
  sel.innerHTML = '';
  var optGlobal = document.createElement('option');
  optGlobal.value = '_global';
  optGlobal.textContent = '\u{1F310} \u5168\u5C40\uFF08\u5BF9\u6240\u6709\u6A21\u578B\u751F\u6548\uFF09';
  sel.appendChild(optGlobal);
  var models = [];
  for (var i = 0; i < window.allProviders.length; i++) {
    var p = window.allProviders[i];
    if (p.type === 'image' && p.enabled !== false) {
      var pModels = (p.models && p.models.length) ? p.models : [p.model || 'default'];
      var filtered = window.filterModelsByType(pModels, 'image');
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
  sel.value = currentVal;
};

window.onImageSettingsModelChange = function() {
  var modelVal = document.getElementById('selModel').value;
  window.loadImageSettings(modelVal);
};

window.loadImageSettings = function(modelKey) {
  var all = window.loadImageProviderSettings();
  var ps = all[modelKey] || all['_global'] || {};

  var q = ps.quality || '';
  document.querySelectorAll('#qualityBtns .quality-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.val === q);
  });
  document.getElementById('selQuality').value = q;

  var ratio = ps.ratio || '1:1';
  document.querySelectorAll('#ratioGrid .ratio-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.ratio === ratio);
  });
  document.getElementById('selRatio').value = ratio;

  if (ratio !== 'auto' && window.RATIO_SIZES[ratio]) {
    var sz = window.RATIO_SIZES[ratio];
    document.getElementById('inputW').value = sz[0];
    document.getElementById('inputH').value = sz[1];
  } else if (ps.w && ps.h) {
    document.getElementById('inputW').value = ps.w;
    document.getElementById('inputH').value = ps.h;
  }

  var qty = ps.qty || 1;
  document.querySelectorAll('#qtyBtns .qty-btn').forEach(function(b){
    b.classList.toggle('active', parseInt(b.dataset.val) === qty);
  });
  document.getElementById('selQty').value = qty;
};

window.saveImageSettings = function() {
  var modelKey = document.getElementById('selModel').value || '_global';
  var all = window.loadImageProviderSettings();
  all[modelKey] = {
    quality: document.getElementById('selQuality').value || '',
    ratio: document.getElementById('selRatio').value || '1:1',
    w: parseInt(document.getElementById('inputW').value) || 1024,
    h: parseInt(document.getElementById('inputH').value) || 1024,
    qty: parseInt(document.getElementById('selQty').value) || 1,
  };
  try {
    localStorage.setItem('genbox_image_settings', JSON.stringify(all));
    var label = modelKey === '_global' ? '\u5168\u5C40' : modelKey;
    setStatus('\u2705 \u5DF2\u4FDD\u5B58\u300C' + label + '\u300D\u7684\u56FE\u50CF\u8BBE\u7F6E');
  } catch(e) { setStatus('\u274C \u4FDD\u5B58\u5931\u8D25'); }
};

window.loadImageProviderSettings = function() {
  try {
    return JSON.parse(localStorage.getItem('genbox_image_settings') || '{}');
  } catch(e) { return {}; }
};

/* ═══════════════════════════════════════════════════════════════════
   filterModelsByType (shared utility)
   ═══════════════════════════════════════════════════════════════════ */
window.filterModelsByType = function(models, providerType) {
  if (!models || !models.length) return models;
  return models.filter(function(m) {
    var ml = m.toLowerCase();
    if (providerType === 'image') {
      if (ml.indexOf('t2v') !== -1 || ml.indexOf('i2v') !== -1 || ml.indexOf('r2v') !== -1) return false;
      if (ml.indexOf('veo_') !== -1) return false;
      if (ml.indexOf('interpolation') !== -1) return false;
      if (ml.indexOf('video') !== -1 && ml.indexOf('image') === -1) return false;
      if (ml.indexOf('gpt-5') !== -1 && ml.indexOf('image') === -1) return false;
      if (ml === 'auto') return false;
      if (ml.indexOf('codex') !== -1 && ml.indexOf('image') === -1) return false;
      if (ml.indexOf('-mini') !== -1 && ml.indexOf('image') === -1 && ml.indexOf('gemini') === -1) return false;
      return true;
    }
    if (providerType === 'video') {
      if (ml.indexOf('t2v') !== -1 || ml.indexOf('i2v') !== -1 || ml.indexOf('r2v') !== -1) return true;
      if (ml.indexOf('veo_') !== -1) return true;
      if (ml.indexOf('interpolation') !== -1) return true;
      if (ml.indexOf('video') !== -1) return true;
      return false;
    }
    if (providerType === 'llm') {
      if (ml.indexOf('t2v') !== -1 || ml.indexOf('i2v') !== -1 || ml.indexOf('r2v') !== -1) return false;
      if (ml.indexOf('veo_') !== -1) return false;
      if (ml.indexOf('interpolation') !== -1) return false;
      if (ml.indexOf('-4k') !== -1 || ml.indexOf('-2k') !== -1) return false;
      if (ml.indexOf('upsample') !== -1) return false;
      return true;
    }
    return true;
  });
};

window.groupVideoModels = function(models) {
  var groups = {};
  var order = [];
  for (var i = 0; i < models.length; i++) {
    var m = models[i];
    var ml = m.toLowerCase();
    var cat;
    if (ml.indexOf('upsample') !== -1 || (ml.indexOf('-4k') !== -1 && ml.indexOf('veo') === -1)) {
      cat = '\u89C6\u9891\u653E\u5927 (Upsample)';
    } else if (ml.indexOf('i2v') !== -1) {
      if (ml.indexOf('veo_3') !== -1) cat = 'Veo 3.x \u56FE\u751F\u89C6\u9891 (I2V)';
      else if (ml.indexOf('veo_2') !== -1) cat = 'Veo 2.x \u56FE\u751F\u89C6\u9891 (I2V)';
      else cat = '\u56FE\u751F\u89C6\u9891 (I2V)';
    } else if (ml.indexOf('r2v') !== -1) {
      cat = 'Veo 3.x \u591A\u56FE\u89C6\u9891 (R2V)';
    } else if (ml.indexOf('interpolation') !== -1) {
      cat = '\u63D2\u5E27 (Interpolation)';
    } else if (ml.indexOf('t2v') !== -1 || ml.indexOf('veo_') !== -1) {
      if (ml.indexOf('veo_3') !== -1) cat = 'Veo 3.x \u6587\u751F\u89C6\u9891 (T2V)';
      else if (ml.indexOf('veo_2') !== -1) cat = 'Veo 2.x \u6587\u751F\u89C6\u9891 (T2V)';
      else cat = '\u6587\u751F\u89C6\u9891 (T2V)';
    } else {
      cat = '\u5176\u4ED6';
    }
    if (!groups[cat]) { groups[cat] = []; order.push(cat); }
    groups[cat].push(m);
  }
  return { groups: groups, order: order };
};

window.groupImageModels = function(models) {
  var groups = {};
  var order = [];
  for (var i = 0; i < models.length; i++) {
    var m = models[i];
    var ml = m.toLowerCase();
    var cat;
    if (ml.indexOf('imagen') !== -1) {
      cat = 'Imagen';
    } else if (ml.indexOf('gemini-3.1-flash') !== -1 || ml.indexOf('gemini-3_1-flash') !== -1) {
      cat = 'Gemini 3.1 Flash \u56FE\u7247';
    } else if (ml.indexOf('gemini-3.0-pro') !== -1 || ml.indexOf('gemini-3_0-pro') !== -1) {
      cat = 'Gemini 3.0 Pro \u56FE\u7247';
    } else if (ml.indexOf('gemini-2.5') !== -1 || ml.indexOf('gemini-2_5') !== -1) {
      cat = 'Gemini 2.5 Flash \u56FE\u7247';
    } else if (ml.indexOf('gemini') !== -1) {
      cat = 'Gemini \u5176\u4ED6';
    } else {
      cat = '\u5176\u4ED6';
    }
    if (!groups[cat]) { groups[cat] = []; order.push(cat); }
    groups[cat].push(m);
  }
  return { groups: groups, order: order };
};

window.buildModelOptsGrouped = function(models, selectedModel, groupFn) {
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
};

/* ═══════════════════════════════════════════════════════════════════
   Navigation
   ═══════════════════════════════════════════════════════════════════ */
window.switchNav = function(name, el) {
  document.getElementById('pageGenerate').classList.toggle('hidden', name !== 'generate');
  document.getElementById('pageVideo').classList.toggle('hidden', name !== 'video');
  document.getElementById('pageGallery').classList.toggle('hidden', name !== 'gallery');
  document.getElementById('pageHistory').classList.toggle('hidden', name !== 'history');
  document.getElementById('pageDashboard').classList.toggle('hidden', name !== 'dashboard');

  document.querySelectorAll('.nav-item').forEach(function(n){ n.classList.remove('active'); });
  if (el) el.classList.add('active');

  if (name === 'gallery') window.loadGallery();
  if (name === 'history') window.loadHistory();
  if (name === 'video') window.loadVideoProviders();
  if (name === 'dashboard') window.loadDashboard();
};

/* ═══════════════════════════════════════════════════════════════════
   Divider Drag IIFE
   ═══════════════════════════════════════════════════════════════════ */
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
    } else if (prev === 'center' && next === 'preview') {
    }
  }

  function onMouseUp() {
    dragTarget = null;
    document.querySelectorAll('.divider-drag').forEach(function(d){ d.classList.remove('active'); });
    document.body.classList.remove('dragging-divider');
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }

  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('.divider-drag').forEach(function(d){
      d.addEventListener('mousedown', onMouseDown);
    });
  });
})();

/* ═══════════════════════════════════════════════════════════════════
   DOMContentLoaded Init
   ═══════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function() {
  window.loadProviders().then(function(){
    window.checkSetupWizard();
  });
  window.renderQuickPrompts();
  window.loadDashboard();

  var zone = document.getElementById('uploadZone');
  if (zone) {
    zone.addEventListener('dragover', function(e){ e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', function(){ zone.classList.remove('dragover'); });
    zone.addEventListener('drop', function(e){
      e.preventDefault();
      zone.classList.remove('dragover');
      var f = e.dataTransfer.files[0];
      if (f) window.handleFile(f);
    });
  }

  var zoneVar = document.getElementById('uploadZoneVar');
  if (zoneVar) {
    zoneVar.addEventListener('dragover', function(e){ e.preventDefault(); zoneVar.classList.add('dragover'); });
    zoneVar.addEventListener('dragleave', function(){ zoneVar.classList.remove('dragover'); });
    zoneVar.addEventListener('drop', function(e){
      e.preventDefault();
      zoneVar.classList.remove('dragover');
      var f = e.dataTransfer.files[0];
      if (f) window.handleFileVar(f);
    });
  }

  document.getElementById('quickSearch').addEventListener('input', function() {
    window.filterQuickPrompts(this.value);
  });

  document.getElementById('selStrength').addEventListener('input', function() {
    document.getElementById('strengthVal').textContent = this.value;
  });

  var selModel = document.getElementById('selModel');
  if (selModel) selModel.addEventListener('change', window.onImageSettingsModelChange);

  var chkUpscale = document.getElementById('chkUpscale');
  if (chkUpscale) chkUpscale.addEventListener('change', function() {
    document.getElementById('upscaleOpts').style.display = this.checked ? '' : 'none';
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      window.closeLightbox();
      window.closeCompare();
      window.closeProviderModal();
    }
    if (e.key === 'ArrowLeft' && window.previewImages.length > 1) window.previewPrev();
    if (e.key === 'ArrowRight' && window.previewImages.length > 1) window.previewNext();
  });
});

/* ═══════════════════════════════════════════════════════════════════
   Dashboard
   ═══════════════════════════════════════════════════════════════════ */
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

function _renderProviderGroups(providers) {
  var cats = {
    '🎨 生图模型': { '文生图': [], '图生图': [] },
    '🎬 生视频模型': { '文生视频': [], '图生视频': [] },
    '🤖 LLM模型': { '_flat': [] }
  };

  for (var i = 0; i < providers.length; i++) {
    var p = providers[i];
    var ptype = p.type || 'image';
    var modelStr = ((p.model || '') + ' ' + (p.models || []).join(' ')).toLowerCase();
    var providerId = (p.id || '').toLowerCase();
    var providerName = (p.name || '').toLowerCase();

    var hasI2I = ptype === 'image' || modelStr.indexOf('i2i') !== -1 || modelStr.indexOf('edit') !== -1;
    var hasI2V = modelStr.indexOf('i2v') !== -1
      || modelStr.indexOf('veo_3_1_i2v') !== -1
      || providerId === 'agnes' || providerName.indexOf('agnes') !== -1;

    if (ptype === 'llm') {
      cats['🤖 LLM模型']['_flat'].push(p);
    } else if (ptype === 'video') {
      cats['🎬 生视频模型']['文生视频'].push(p);
      if (hasI2V) {
        cats['🎬 生视频模型']['图生视频'].push(p);
      }
    } else {
      cats['🎨 生图模型']['文生图'].push(p);
      if (hasI2I) {
        cats['🎨 生图模型']['图生图'].push(p);
      }
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
    var h = '<div id="conn_card_' + p.id + '" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;background:var(--bg-base);border:1px solid var(--border);min-width:0;">';
    h += '<span style="width:8px;height:8px;border-radius:50%;background:' + statusDot + ';flex-shrink:0;"></span>';
    h += '<div style="flex:1;min-width:0;">';
    h += '<div style="font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(p.name) + '</div>';
    h += '<div style="font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(p.model || '-') + '</div>';
    h += '</div>';
    h += '<div style="text-align:right;flex-shrink:0;">';
    h += '<div style="font-size:10px;color:' + statusDot + ';">' + statusText + '</div>';
    h += '<div id="conn_ms_' + p.id + '" style="font-size:10px;color:var(--text-muted);"></div>';
    h += '</div>';
    h += '</div>';
    return h;
  }

  var html = '<div class="glass-card" style="padding:16px;margin-bottom:16px;">';
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
  return html;
}

window.runConnectivityTest = function() {
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
        var msEl = document.getElementById('conn_ms_' + pid);
        var card = document.getElementById('conn_card_' + pid);
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
        if (card) {
          card.style.borderColor = r.status === 'ok' ? (r.ms < 500 ? '#22c55e40' : '#f59e0b40') : '#ef444440';
        }
      }
      if (btn) { btn.textContent = '✅ 检测完成'; setTimeout(function(){ btn.textContent = '⚡ 一键连通性检测'; btn.disabled = false; btn.style.opacity = '1'; }, 2000); }
    })
    .catch(function() {
      if (btn) { btn.textContent = '❌ 检测失败'; setTimeout(function(){ btn.textContent = '⚡ 一键连通性检测'; btn.disabled = false; btn.style.opacity = '1'; }, 2000); }
    });
};

window.serverControl = function(action) {
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
};

/* ═══════════════════════════════════════════════════════════════════
   Page Switch Hook (for navigation.js dock)
   ═══════════════════════════════════════════════════════════════════ */
window.onPageSwitch = function(pageId) {
  if (pageId === 'gallery') window.loadGallery();
  if (pageId === 'history') window.loadHistory();
  if (pageId === 'video') window.loadVideoProviders();
  if (pageId === 'dashboard') window.loadDashboard();
};

window.loadDashboard = function() {
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

      html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:16px;">';
      html += _dashCard('🏆 综合评分', '<div style="font-size:36px;font-weight:800;color:' + scoreColor + ';">' + scTotal + '</div><div style="font-size:11px;color:var(--text-muted);">' + scoreLabel + '</div>', scoreColor);
      html += _dashCard('🖼 图片生成', '<div style="font-size:28px;font-weight:700;color:var(--accent);">' + (stImg.total || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">成功 ' + (stImg.success || 0) + ' / 失败 ' + (stImg.failed || 0) + '</div>');
      html += _dashCard('🎬 视频生成', '<div style="font-size:28px;font-weight:700;color:var(--accent-2);">' + (stVid.total || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">成功 ' + (stVid.success || 0) + ' / 失败 ' + (stVid.failed || 0) + '</div>');
      html += _dashCard('⏱ 平均耗时', '<div style="font-size:28px;font-weight:700;color:var(--accent);">' + (stImg.avg_time || 0) + 's</div><div style="font-size:11px;color:var(--text-muted);">图片生成</div>');
      html += '</div>';

      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">';
      html += '<div class="glass-card" style="padding:16px;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">🏆 评分详情</div>';
      html += _scoreBar('连通性', scConn, 40, '#5b8def');
      html += _scoreBar('配置完整', scConf, 30, '#22d3a5');
      html += _scoreBar('磁盘空间', scDisk, 15, '#a78bfa');
      html += _scoreBar('依赖状态', scDep, 15, '#f59e0b');
      html += '</div>';

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

      html += _renderProviderGroups(providers);

      html += '<div class="glass-card" style="padding:16px;margin-bottom:16px;">';
      html += '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:12px;">📋 最近活动</div>';
      if (logs.length === 0) {
        html += '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">暂无活动记录</div>';
      } else {
        html += '<div style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto;">';
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

      html += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">';
      html += _quickNav('✨', '生图', "switchNav('generate',document.getElementById('navGen'))");
      html += _quickNav('🎬', '生视频', "switchNav('video',document.getElementById('navVideo'))");
      html += _quickNav('🖼', '媒体库', "switchNav('gallery',document.getElementById('navGallery'))");
      html += _quickNav('📜', '历史', "switchNav('history',document.getElementById('navHistory'))");
      html += '</div>';

      el.innerHTML = html;
    })
    .catch(function(e) {
      el.innerHTML = '<div style="text-align:center;padding:40px;color:#ef4444;">加载失败: ' + escHtml(e.message) + '</div>';
    });
};

})();
