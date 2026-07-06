/* ===== AI 晨报 — 前端逻辑 ===== */

// DOM 引用
const datePicker      = document.getElementById('datePicker');
const fetchBtn        = document.getElementById('fetchBtn');
const loadingEl       = document.getElementById('loading');
const emptyStateEl    = document.getElementById('emptyState');
const overviewSec     = document.getElementById('overviewSection');
const overviewText    = document.getElementById('overviewText');
const categoriesEl    = document.getElementById('categoriesContainer');
const batchFooter     = document.getElementById('batchFooter');
const batchInfo       = document.getElementById('batchInfo');
const uiToggleBtn     = document.getElementById('uiToggleBtn');
const mastheadSubtitle = document.getElementById('mastheadSubtitle');
const bottomSection   = document.getElementById('bottomSection');
const backToTopBtn    = document.getElementById('backToTop');

const CATEGORY_ORDER = ['大模型', '工具', '公司动态', '政策', '研究', '其他'];

// ---- 主题切换 V1 → V2 → V3 → V4 → V1 ----
const THEME_KEY = 'ai-morning-brief-theme';
const THEMES = ['v1', 'v2', 'v3', 'v4', 'v5'];
const THEME_LABELS = { v1: '报纸排版', v2: '刊体排版', v3: '速读排版', v4: '融合排版', v5: '经典排版' };
const THEME_CLASSES = { v2: 'theme-v2', v3: 'theme-v3', v4: 'theme-v4', v5: 'theme-v5' };

function getCurrentTheme() {
  for (const t of ['v5', 'v4', 'v3', 'v2']) {
    if (document.body.classList.contains(THEME_CLASSES[t])) return t;
  }
  return 'v1';
}

function isV4() { return document.body.classList.contains('theme-v4'); }
function isV5() { return document.body.classList.contains('theme-v5'); }

function applyTheme(theme) {
  document.body.classList.remove('theme-v2', 'theme-v3', 'theme-v4');
  if (theme !== 'v1') document.body.classList.add(THEME_CLASSES[theme]);
  const idx = THEMES.indexOf(theme);
  const next = THEMES[(idx + 1) % THEMES.length];
  uiToggleBtn.textContent = THEME_LABELS[next];
  // V4 专属元素显示/隐藏
  bottomSection.style.display = isV4() ? '' : 'none';
  // 刷新当前内容以应用 V4 特殊渲染
  updateMasthead(datePicker.value);
  // 如果已有数据，重新渲染
  if (categoriesEl.innerHTML) {
    if (lastBriefData) renderBrief(lastBriefData);
  }
}

uiToggleBtn.addEventListener('click', () => {
  const current = getCurrentTheme();
  const idx = THEMES.indexOf(current);
  const next = THEMES[(idx + 1) % THEMES.length];
  applyTheme(next);
  localStorage.setItem(THEME_KEY, next);
});

const savedTheme = localStorage.getItem(THEME_KEY);
applyTheme(savedTheme && THEMES.includes(savedTheme) ? savedTheme : 'v2');

// ---- 数据状态 ----
function setDataState(hasData) {
  document.body.classList.toggle('has-data', hasData);
  document.body.classList.toggle('no-data', !hasData);
}

// ---- 刊头副标题 ----
function updateMasthead(dateStr) {
  const theme = getCurrentTheme();
  if (theme === 'v1') { mastheadSubtitle.style.display = 'none'; return; }
  mastheadSubtitle.style.display = '';
  const d = new Date(dateStr);
  const fmt = (theme === 'v3')
    ? `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`
    : `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日`;
  mastheadSubtitle.textContent = `${fmt} · 每天5分钟，和世界AI对齐`;
}

// V5 也显示刊头副标题
function isMastheadTheme() {
  const t = getCurrentTheme();
  return t === 'v2' || t === 'v3' || t === 'v4' || t === 'v5';
}

// ---- 回到顶部 ----
window.addEventListener('scroll', () => {
  if (!isV4()) return;
  backToTopBtn.style.display = window.scrollY > 400 ? '' : 'none';
});
backToTopBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

// ---- 数据高亮（V4 专属） ----
function highlightData(text) {
  if (!isV4()) return esc(text);
  // 先转义 HTML
  const safe = esc(text);
  // 再用正则包裹关键数字
  return safe.replace(/(\d+\.?\d*\s*[万亿百千%％]+(?:[-–—]\d+\.?\d*\s*[万亿百千%％]*)?)/g,
    '<span class="data-highlight">$1</span>');
}

// ---- 初始化 ----
datePicker.value = todayStr();
let lastBriefData = null;
loadBrief(datePicker.value);
datePicker.addEventListener('change', () => {
  loadBrief(datePicker.value);
  updateFetchBtnState();
});
updateFetchBtnState();
fetchBtn.addEventListener('click', fetchAndReload);

/* ---------- 核心函数 ---------- */

// 检查选择的日期是否是今天
function isToday(dateStr) {
  const selected = new Date(dateStr);
  const today = new Date();
  return selected.getFullYear() === today.getFullYear() &&
         selected.getMonth() === today.getMonth() &&
         selected.getDate() === today.getDate();
}

// 更新"获取今日资讯"按钮状态
function updateFetchBtnState() {
  if (isToday(datePicker.value)) {
    fetchBtn.disabled = false;
    fetchBtn.textContent = '获取今日资讯';
    fetchBtn.title = '获取今日资讯';
  } else {
    fetchBtn.disabled = true;
    fetchBtn.textContent = '仅今日可获取';
    fetchBtn.title = '历史日期无法获取，请选择今天';
  }
}

async function fetchAndReload() {
  fetchBtn.disabled = true;
  fetchBtn.textContent = '获取中…';
  showLoading(true);
  try {
    const res = await fetch('/api/fetch', { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await res.json();
    datePicker.value = todayStr();
    await loadBrief(datePicker.value);
  } catch (e) {
    alert('获取资讯失败：' + e.message);
    showLoading(false);
  } finally {
    fetchBtn.disabled = false;
    fetchBtn.textContent = '获取今日资讯';
  }
}

async function loadBrief(date) {
  showLoading(true);
  try {
    const res = await fetch(`/api/brief?date=${date}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    lastBriefData = data;
    renderBrief(data);
    updateMasthead(date);
  } catch (e) {
    renderError(e.message);
  } finally {
    showLoading(false);
  }
}

function renderBrief(data) {
  const hasData = data.articles && data.articles.length > 0;
  setDataState(hasData);

  if (!hasData) {
    overviewSec.style.display = 'none';
    categoriesEl.innerHTML = '';
    batchFooter.style.display = 'none';
    emptyStateEl.style.display = '';
    return;
  }

  emptyStateEl.style.display = 'none';

  if (data.overview) {
    overviewText.textContent = data.overview;
    overviewSec.style.display = '';
  } else {
    overviewSec.style.display = 'none';
  }

  const grouped = {};
  for (const a of data.articles) {
    const cat = a.category || '其他';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(a);
  }

  categoriesEl.innerHTML = '';
  const orderedCats = CATEGORY_ORDER.filter(c => grouped[c]);
  for (const cat of Object.keys(grouped)) {
    if (!orderedCats.includes(cat)) orderedCats.push(cat);
  }

  const v4 = isV4();

  for (const cat of orderedCats) {
    const section = document.createElement('section');
    section.className = 'category-section';

    const header = document.createElement('div');
    header.className = 'category-header';
    const tag = document.createElement('span');
    tag.className = `category-tag tag-${cat}`;
    tag.textContent = `${cat} · ${grouped[cat].length}条`;
    header.appendChild(tag);
    section.appendChild(header);

    for (const a of grouped[cat]) {
      const card = document.createElement('article');
      card.className = 'article-card';

      const dateStr = a.publish_date || '';
      const domain = a.source_domain || '';
      const tier = a.source_tier || '';
      const tierLabels = {
        firsthand: '一手', authoritative: '权威', vertical: '垂直',
        research: '研究', chinese: '中文', aggregator: '转载',
      };
      const tierLabel = tierLabels[tier] || '转载';

      // V4：分类标签 + 数据高亮 + 操作图标
      const catTagHtml = v4
        ? `<span class="article-cat-tag">${esc(cat)}</span>` : '';

      const summaryHtml = v4
        ? highlightData(a.summary)
        : esc(a.summary);

      const actionsHtml = '';  // 操作图标暂不显示

      // 统一来源信息格式：tier · source_name · domain · date
      const metaParts = [];
      if (tierLabel) metaParts.push(tierLabel);
      if (a.source_name) {
        // 去掉"来源："前缀，避免重复
        const cleanSource = a.source_name.replace(/^来源[:：]\s*/, '');
        metaParts.push(cleanSource);
      }
      if (domain) metaParts.push(domain);
      if (dateStr) metaParts.push(dateStr);

      const metaHtml = metaParts.length > 0
        ? metaParts.join(' · ')
        : '';

      card.innerHTML = `
        <div>${catTagHtml}<h3 class="article-title">${esc(a.title)}</h3></div>
        <p class="article-summary">${summaryHtml}</p>
        <div class="article-meta">
          ${metaHtml ? `<span>${metaHtml}</span>` : ''}
          <a class="article-source" href="${esc(a.source_url)}" target="_blank" rel="noopener">
            原文链接 <span class="external-icon">↗</span>
          </a>
        </div>
        ${actionsHtml}
      `;
      section.appendChild(card);
    }
    categoriesEl.appendChild(section);
  }

  if (data.fetch_timestamp) {
    batchInfo.textContent = `本批次抓取于 ${data.fetch_timestamp} · 共 ${data.article_count} 条`;
    batchFooter.style.display = '';
  } else {
    batchFooter.style.display = 'none';
  }

  // V4 底部模块
  bottomSection.style.display = v4 ? '' : 'none';
}

function renderError(msg) {
  setDataState(false);
  overviewSec.style.display = 'none';
  categoriesEl.innerHTML = `<p style="text-align:center;color:#ef4444;padding:40px;">加载失败：${esc(msg)}</p>`;
  batchFooter.style.display = 'none';
  emptyStateEl.style.display = 'none';
}

/* ---------- V4 操作函数 ---------- */

function copySummary(btn) {
  const card = btn.closest('.article-card');
  const title = card.querySelector('.article-title').textContent;
  const summary = card.querySelector('.article-summary').textContent;
  navigator.clipboard.writeText(title + '\n' + summary).then(() => {
    btn.textContent = '已复制';
    setTimeout(() => btn.textContent = '复制', 1500);
  });
}

function bookmarkArticle(btn) {
  btn.textContent = '已收藏';
  btn.style.color = '#8B4D52';
  btn.style.borderColor = '#8B4D52';
  setTimeout(() => { btn.textContent = '收藏'; btn.style.color = ''; btn.style.borderColor = ''; }, 2000);
}

/* ---------- 工具函数 ---------- */

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function showLoading(visible) {
  loadingEl.style.display = visible ? '' : 'none';
}

function esc(str) {
  if (!str) return '';
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}
