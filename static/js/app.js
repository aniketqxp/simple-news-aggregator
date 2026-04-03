// Backend endpoint (relative for production deployment)
const BASE_NEWS_URL = '/fetch-news?q={query}';

let currentQuery = 'AI';
let articleCount = 15;
let currentAbortController = null;
const categoryData = {};

// DOM
const searchInput = document.getElementById('search-input');
const searchForm = document.getElementById('search-form');
const chipsContainer = document.getElementById('chips-container');
const refreshBtn = document.getElementById('refresh-btn');
const refreshIcon = document.getElementById('refresh-icon');
const newsGrid = document.getElementById('news-grid');
const loadingState = document.getElementById('loading-state');
const errorState = document.getElementById('error-state');
const currentTopicTitle = document.getElementById('current-topic-title');

const quickTopics = ['AI', 'Business', 'Finance', 'Soccer', 'Technology', 'Science', 'World'];

// Soft mesh gradient fallbacks — clearly decorative, never mistakable for "loading"
const MESH_FALLBACKS = [
    'radial-gradient(at 20% 30%, hsla(280,35%,45%,0.4) 0%, transparent 55%), radial-gradient(at 80% 70%, hsla(200,35%,45%,0.3) 0%, transparent 55%), linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    'radial-gradient(at 70% 20%, hsla(340,35%,50%,0.35) 0%, transparent 55%), radial-gradient(at 30% 80%, hsla(20,40%,45%,0.3) 0%, transparent 55%), linear-gradient(135deg, #1e1a2e 0%, #2a1a1e 100%)',
    'radial-gradient(at 25% 75%, hsla(160,30%,40%,0.35) 0%, transparent 55%), radial-gradient(at 85% 25%, hsla(220,35%,45%,0.3) 0%, transparent 55%), linear-gradient(135deg, #1a2420 0%, #1a1e28 100%)',
    'radial-gradient(at 60% 40%, hsla(40,40%,45%,0.35) 0%, transparent 55%), radial-gradient(at 20% 80%, hsla(300,30%,40%,0.25) 0%, transparent 55%), linear-gradient(135deg, #222018 0%, #1e1a24 100%)',
    'radial-gradient(at 80% 80%, hsla(250,35%,50%,0.3) 0%, transparent 55%), radial-gradient(at 20% 20%, hsla(180,30%,45%,0.3) 0%, transparent 55%), linear-gradient(135deg, #1a1a28 0%, #1a2422 100%)',
    'radial-gradient(at 50% 30%, hsla(10,40%,45%,0.35) 0%, transparent 55%), radial-gradient(at 50% 80%, hsla(260,30%,40%,0.25) 0%, transparent 55%), linear-gradient(135deg, #241a1a 0%, #1a1a24 100%)',
    'radial-gradient(at 30% 50%, hsla(120,25%,40%,0.3) 0%, transparent 55%), radial-gradient(at 70% 50%, hsla(60,35%,40%,0.25) 0%, transparent 55%), linear-gradient(135deg, #1a221a 0%, #22201a 100%)',
    'radial-gradient(at 40% 20%, hsla(320,35%,45%,0.35) 0%, transparent 55%), radial-gradient(at 60% 80%, hsla(180,30%,40%,0.25) 0%, transparent 55%), linear-gradient(135deg, #221a22 0%, #1a2222 100%)',
];

// Color Thief
let colorThief;
try { colorThief = new ColorThief(); } catch(e) { colorThief = null; }

// ========== XSS SANITIZATION ==========
function escapeHTML(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ========== CUSTOM DROPDOWN ==========
function createDropdown() {
    const container = document.getElementById('count-dropdown-container');
    const options = [5, 10, 15];
    
    container.innerHTML = `
        <div class="custom-dropdown" id="count-dropdown">
            <div class="dropdown-trigger" role="button" tabindex="0" aria-haspopup="listbox" aria-expanded="false" aria-label="Select number of results">
                <span class="text-zinc-500 font-medium">Results</span>
                <span class="dropdown-value text-zinc-200">${articleCount}</span>
                <svg class="w-3 h-3 text-zinc-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
            </div>
            <div class="dropdown-menu" role="listbox">
                ${options.map(n => `
                    <div class="dropdown-item ${n === articleCount ? 'active' : ''}" data-value="${n}" role="option" tabindex="0" aria-selected="${n === articleCount}">${n}</div>
                `).join('')}
            </div>
        </div>
    `;
    
    const dropdown = container.querySelector('.custom-dropdown');
    const trigger = dropdown.querySelector('.dropdown-trigger');
    const valueEl = dropdown.querySelector('.dropdown-value');
    const items = dropdown.querySelectorAll('.dropdown-item');
    
    function toggleDropdown(open) {
        const isOpen = open !== undefined ? open : !dropdown.classList.contains('open');
        dropdown.classList.toggle('open', isOpen);
        trigger.setAttribute('aria-expanded', isOpen);
    }
    
    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleDropdown();
    });
    
    // Keyboard support for trigger
    trigger.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            e.stopPropagation();
            toggleDropdown();
        } else if (e.key === 'Escape') {
            toggleDropdown(false);
        }
    });
    
    items.forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            selectItem(item);
        });
        // Keyboard support for items
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                e.stopPropagation();
                selectItem(item);
            } else if (e.key === 'Escape') {
                toggleDropdown(false);
                trigger.focus();
            }
        });
    });
    
    function selectItem(item) {
        const val = parseInt(item.dataset.value);
        articleCount = val;
        valueEl.textContent = val;
        items.forEach(i => {
            i.classList.remove('active');
            i.setAttribute('aria-selected', 'false');
        });
        item.classList.add('active');
        item.setAttribute('aria-selected', 'true');
        toggleDropdown(false);
        Object.keys(categoryData).forEach(key => delete categoryData[key]);
        fetchNews();
    }
    
    // Close on outside click
    document.addEventListener('click', () => toggleDropdown(false));
}

// ========== INIT ==========
function init() {
    createDropdown();
    renderChips();
    
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const val = searchInput.value.trim();
        if(val) {
            currentQuery = val;
            updateActiveChip();
            fetchNews();
        }
    });
    
    refreshBtn.addEventListener('click', () => fetchNews(true));
    searchInput.value = currentQuery;
    fetchNews();
}

// ========== CHIPS ==========
function renderChips() {
    chipsContainer.innerHTML = '';
    quickTopics.forEach(topic => {
        const btn = document.createElement('button');
        btn.textContent = topic;
        btn.setAttribute('role', 'tab');
        btn.setAttribute('aria-selected', topic.toLowerCase() === currentQuery.toLowerCase());
        const isActive = topic.toLowerCase() === currentQuery.toLowerCase();
        btn.className = isActive
            ? 'px-2.5 py-1 rounded-md text-[12px] font-medium transition-all duration-150 text-zinc-100 bg-zinc-800 border border-zinc-700'
            : 'px-2.5 py-1 rounded-md text-[12px] font-medium transition-all duration-150 text-zinc-500 hover:text-zinc-300 border border-transparent hover:border-zinc-800';
        btn.addEventListener('click', () => {
            currentQuery = topic;
            searchInput.value = topic;
            updateActiveChip();
            fetchNews();
        });
        chipsContainer.appendChild(btn);
    });
}

function updateActiveChip() {
    Array.from(chipsContainer.children).forEach(btn => {
        const isActive = btn.textContent.toLowerCase() === currentQuery.toLowerCase();
        btn.className = isActive
            ? 'px-2.5 py-1 rounded-md text-[12px] font-medium transition-all duration-150 text-zinc-100 bg-zinc-800 border border-zinc-700'
            : 'px-2.5 py-1 rounded-md text-[12px] font-medium transition-all duration-150 text-zinc-500 hover:text-zinc-300 border border-transparent hover:border-zinc-800';
        btn.setAttribute('aria-selected', isActive);
    });
    currentTopicTitle.textContent = currentQuery ? `${currentQuery}` : 'Top Stories';
}

// ========== TIME ==========
function getRelativeTime(pubDateStr) {
    const pubDate = new Date(pubDateStr);
    if(isNaN(pubDate.getTime())) return 'Recently';
    const now = new Date();
    const s = Math.floor((now - pubDate) / 1000);
    if (s < 60) return 'now';
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h`;
    const d = Math.floor(h / 24);
    if (d < 30) return `${d}d`;
    return pubDate.toLocaleDateString();
}

// ========== LOADING ==========
function showLoading() {
    refreshIcon.classList.add('animate-spin');
    newsGrid.innerHTML = '';
    newsGrid.classList.add('hidden');
    errorState.classList.add('hidden');
    loadingState.classList.remove('hidden');
}

function hideLoading() {
    refreshIcon.classList.remove('animate-spin');
    loadingState.classList.add('hidden');
    newsGrid.classList.remove('hidden');
}

// ========== FETCH ==========
async function fetchNews(forceRefresh = false) {
    currentTopicTitle.textContent = currentQuery || 'Top Stories';
    
    const banner = document.getElementById('status-banner');
    const bannerText = document.getElementById('status-banner-text');

    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    
    const normalizedQuery = currentQuery.toLowerCase();
    if (!forceRefresh && categoryData[normalizedQuery]) {
        hideLoading();
        renderNews(categoryData[normalizedQuery].slice(0, articleCount));
        return;
    }
    
    const controller = new AbortController();
    currentAbortController = controller;
    const fetchQuery = currentQuery;
    
    showLoading();
    banner.classList.add('hidden');
    
    try {
        const url = BASE_NEWS_URL.replace('{query}', encodeURIComponent(currentQuery));
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw new Error('Network response was not ok');
        const items = await response.json();
        
        // UI-level health check: if thumbnails are missing (likely rate-limited), surface the banner.
        const hasThumbnails = items.filter(i => i.thumbnail && i.thumbnail.length > 0);
        if (items.length > 0 && hasThumbnails.length < items.length / 2) {
            banner.classList.remove('hidden');
            bannerText.textContent = 'Image extraction is currently restricted by news providers or rate limits. Headlines and sources remain live.';
        } else {
            banner.classList.add('hidden');
        }

        categoryData[normalizedQuery] = items;
        if (fetchQuery !== currentQuery) return;
        renderNews(items.slice(0, articleCount));
    } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('Error fetching news:', err);
        errorState.classList.remove('hidden');
    } finally {
        if (fetchQuery === currentQuery) hideLoading();
    }
}

// ========== COLOR THIEF ==========
function applyColorThief(imgEl, cardEl) {
    if (!colorThief || !imgEl.complete || imgEl.naturalWidth === 0) return;
    try {
        const [r, g, b] = colorThief.getColor(imgEl);
        cardEl.style.borderTopColor = `rgba(${r},${g},${b},0.5)`;
        cardEl.style.borderTopWidth = '2px';
        cardEl.dataset.accentR = r;
        cardEl.dataset.accentG = g;
        cardEl.dataset.accentB = b;
    } catch(e) { /* cross-origin — skip */ }
}

// ========== RENDER ==========
function renderNews(items) {
    newsGrid.innerHTML = '';
    
    if(items.length === 0) {
        newsGrid.innerHTML = `
            <div class="col-span-full py-16 flex flex-col items-center justify-center text-center">
                <p class="text-zinc-500 text-[13px]">No results for "${escapeHTML(currentQuery)}"</p>
            </div>`;
        return;
    }
    
    items.forEach((item, index) => {
        const title = item.title || 'Untitled';
        const link = item.link || '#';
        const pubDate = item.pubDate || new Date().toISOString();
        const sourceName = item.source || '';
        let imgSrc = item.thumbnail;
        const snippet = item.snippet;
        const logoSrc = item.logo;
        
        // Parse publisher from title
        let publisher = '';
        let cleanTitle = title;
        const titleParts = title.split(' - ');
        if(titleParts.length > 1) {
            const p = titleParts[titleParts.length - 1];
            if (p.length < 45) { publisher = p; titleParts.pop(); cleanTitle = titleParts.join(' - '); }
        }
        if (!publisher && sourceName) publisher = sourceName;

        const relativeTime = getRelativeTime(pubDate);
        
        // Enhance google proxy
        if(imgSrc && imgSrc.includes('googleusercontent.com') && imgSrc.includes('-w') && imgSrc.includes('-h')) {
            imgSrc = imgSrc.replace(/-w\d+-h\d+(-?)/, '-w800-h500$1');
        }
        
        // Proxy route
        let proxiedSrc = '';
        const hasRealImage = imgSrc && imgSrc.startsWith('http');
        if (hasRealImage) {
            const encoded = btoa(imgSrc).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            proxiedSrc = `/proxy-image?url=${encoded}`;
        }
        
        const delay = index * 25;
        const meshBg = MESH_FALLBACKS[index % MESH_FALLBACKS.length];
        
        // Build card
        const card = document.createElement('a');
        card.href = link;
        card.target = '_blank';
        card.rel = 'noopener noreferrer';
        card.className = 'news-card animate-fade-in-up';
        card.style.animationDelay = `${delay}ms`;
        card.style.height = '340px';
        card.setAttribute('aria-label', escapeHTML(cleanTitle));
        
        // Hover glow
        card.addEventListener('mouseenter', function() {
            const r = this.dataset.accentR, g = this.dataset.accentG, b = this.dataset.accentB;
            if (r) {
                this.style.boxShadow = `0 8px 40px rgba(${r},${g},${b},0.12), 0 0 0 1px rgba(${r},${g},${b},0.1)`;
                this.style.borderColor = `rgba(${r},${g},${b},0.3)`;
                this.style.borderTopColor = `rgba(${r},${g},${b},0.6)`;
                this.style.borderTopWidth = '2px';
            }
        });
        card.addEventListener('mouseleave', function() {
            this.style.boxShadow = '';
            const r = this.dataset.accentR;
            if (r) {
                this.style.borderColor = '#27272a';
                this.style.borderTopColor = `rgba(${this.dataset.accentR},${this.dataset.accentG},${this.dataset.accentB},0.5)`;
                this.style.borderTopWidth = '2px';
            } else {
                this.style.borderColor = '#27272a';
            }
            this.style.transform = '';
        });
        
        card.innerHTML = `
            <!-- Background (mesh gradient fallback is always present) -->
            <div style="position:absolute;inset:0;background:${meshBg};"></div>
            
            <!-- Hero Image (if available) -->
            ${hasRealImage ? `<img src="${proxiedSrc}" alt="" crossorigin="anonymous" class="card-image" onerror="this.style.display='none';">` : ''}
            
            <!-- Gradient scrim -->
            <div class="card-scrim"></div>
            
            <!-- Content overlay -->
            <div class="card-content">
                <!-- Publisher + Time -->
                <div class="flex items-center justify-between mb-1.5">
                    <div class="flex items-center space-x-1.5 min-w-0">
                        ${logoSrc ? `<img src="${escapeHTML(logoSrc)}" alt="" class="w-3.5 h-3.5 rounded-sm flex-shrink-0 opacity-80" onerror="this.style.display='none'">` : ''}
                        <span class="text-[11px] text-zinc-400 font-medium truncate">${escapeHTML(publisher)}</span>
                    </div>
                    <span class="text-[10px] text-zinc-500 flex-shrink-0 ml-2 tabular-nums">${escapeHTML(relativeTime)}</span>
                </div>
                
                <!-- Headline -->
                <h3 class="text-[14px] font-semibold text-white leading-snug line-clamp-2" style="text-shadow: 0 1px 3px rgba(0,0,0,0.3);">
                    ${escapeHTML(cleanTitle)}
                </h3>
                
                <!-- Snippet: slides up on hover -->
                ${snippet ? `
                <div class="card-snippet">
                    <p class="text-[11px] text-zinc-400 leading-relaxed line-clamp-2 mt-2">
                        ${escapeHTML(snippet)}
                    </p>
                </div>` : ''}
            </div>
        `;
        
        // Color Thief after image loads
        if (hasRealImage) {
            const img = card.querySelector('.card-image');
            if (img) {
                if (img.complete && img.naturalWidth > 0) {
                    applyColorThief(img, card);
                } else {
                    img.addEventListener('load', () => applyColorThief(img, card));
                }
            }
        }
        
        newsGrid.appendChild(card);
    });
}

window.addEventListener('DOMContentLoaded', init);
