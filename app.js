// Local FastAPI backend endpoint for fetching news
const BASE_NEWS_URL = 'http://127.0.0.1:8000/fetch-news?q={query}';

let currentQuery = 'Technology';
let articleCount = 20;
let currentAbortController = null;

// Memory Cache for instantaneous topic switching
const categoryData = {};

// DOM Elements
const searchInput = document.getElementById('search-input');
const searchForm = document.getElementById('search-form');
const chipsContainer = document.getElementById('chips-container');
const countSelect = document.getElementById('count-select');
const refreshBtn = document.getElementById('refresh-btn');
const refreshIcon = document.getElementById('refresh-icon');
const refreshBtnMobile = document.getElementById('refresh-btn-mobile');
const refreshIconMobile = document.getElementById('refresh-icon-mobile');
const newsGrid = document.getElementById('news-grid');
const loadingState = document.getElementById('loading-state');
const errorState = document.getElementById('error-state');
const currentTopicTitle = document.getElementById('current-topic-title');

const quickTopics = ['AI', 'Business', 'Finance', 'Soccer', 'Technology', 'Science', 'World'];

// CSS gradient fallbacks — these NEVER fail because they're pure CSS, no network needed
const GRADIENT_FALLBACKS = [
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
    'linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)',
    'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)',
    'linear-gradient(135deg, #f5576c 0%, #f093fb 100%)',
    'linear-gradient(135deg, #5ee7df 0%, #b490ca 100%)',
];

// Init
function init() {
    renderChips();
    
    // Event listeners
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const val = searchInput.value.trim();
        if(val) {
            currentQuery = val;
            updateActiveChip();
            fetchNews();
        }
    });
    
    countSelect.addEventListener('change', (e) => {
        articleCount = parseInt(e.target.value);
        // Clear cache so it fetches new amount
        Object.keys(categoryData).forEach(key => delete categoryData[key]);
        fetchNews();
    });
    
    refreshBtn.addEventListener('click', () => fetchNews(true));
    if(refreshBtnMobile) {
        refreshBtnMobile.addEventListener('click', () => fetchNews(true));
    }
    
    // Initial UI state
    searchInput.value = currentQuery;
    
    // Fetch initial news
    fetchNews();
}

function renderChips() {
    chipsContainer.innerHTML = '';
    quickTopics.forEach(topic => {
        const btn = document.createElement('button');
        btn.textContent = topic;
        
        // Base classes
        const isActive = topic.toLowerCase() === currentQuery.toLowerCase();
        btn.className = `px-5 py-2 rounded-full text-sm font-semibold transition-all duration-300 border ${
            isActive 
            ? 'bg-primary text-white border-primary shadow-lg shadow-primary/40 tracking-wide' 
            : 'bg-white/5 text-gray-300 border-white/10 hover:bg-white/15 hover:text-white hover:border-white/20'
        }`;
        
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
        if(btn.textContent.toLowerCase() === currentQuery.toLowerCase()) {
            btn.className = 'px-5 py-2 rounded-full text-sm font-semibold transition-all duration-300 border bg-primary text-white border-primary shadow-lg shadow-primary/40 tracking-wide';
        } else {
            btn.className = 'px-5 py-2 rounded-full text-sm font-semibold transition-all duration-300 border bg-white/5 text-gray-300 border-white/10 hover:bg-white/15 hover:text-white hover:border-white/20';
        }
    });
    currentTopicTitle.textContent = currentQuery ? `${currentQuery} News` : 'Top Stories';
}

function getRelativeTime(pubDateStr) {
    const pubDate = new Date(pubDateStr);
    if(isNaN(pubDate.getTime())) return 'Recently';
    
    const now = new Date();
    const diffInSeconds = Math.floor((now - pubDate) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) return `${diffInMinutes} min${diffInMinutes > 1 ? 's' : ''} ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 30) return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    
    return pubDate.toLocaleDateString();
}

function showLoading() {
    refreshIcon.classList.add('animate-spin');
    if(refreshIconMobile) refreshIconMobile.classList.add('animate-spin');
    newsGrid.innerHTML = ''; // Clear old content so stale results never show
    newsGrid.classList.add('hidden');
    errorState.classList.add('hidden');
    loadingState.classList.remove('hidden');
}

function hideLoading() {
    refreshIcon.classList.remove('animate-spin');
    if(refreshIconMobile) refreshIconMobile.classList.remove('animate-spin');
    loadingState.classList.add('hidden');
    newsGrid.classList.remove('hidden');
}

async function fetchNews(forceRefresh = false) {
    currentTopicTitle.textContent = currentQuery ? `${currentQuery} News` : 'Top Stories';
    
    // Always abort any in-flight request first, even if we're about to load from cache.
    // This prevents stale background fetches from completing and causing confusion.
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    
    // Check Memory Cache
    const normalizedQuery = currentQuery.toLowerCase();
    if (!forceRefresh && categoryData[normalizedQuery]) {
        // Render instantly from cache — no loading state needed
        hideLoading();
        renderNews(categoryData[normalizedQuery].slice(0, articleCount));
        return;
    }
    
    // Create a new controller for this request
    const controller = new AbortController();
    currentAbortController = controller;
    const fetchQuery = currentQuery; // snapshot for staleness check
    
    showLoading();
    
    try {
        const url = BASE_NEWS_URL.replace('{query}', encodeURIComponent(currentQuery));
        const response = await fetch(url, { signal: controller.signal });
        
        if (!response.ok) throw new Error('Network response was not ok');
        
        const items = await response.json();
        
        // Save to cache regardless
        categoryData[normalizedQuery] = items;
        
        // Staleness check: if user switched away during fetch, don't render
        if (fetchQuery !== currentQuery) {
            return;
        }
        
        renderNews(items.slice(0, articleCount));
        
    } catch (err) {
        if (err.name === 'AbortError') {
            // Silently ignore — the new fetch will handle UI
            return;
        }
        console.error('Error fetching news:', err);
        errorState.classList.remove('hidden');
    } finally {
        // Only touch UI if this is still the active request
        if (fetchQuery === currentQuery) {
            hideLoading();
        }
    }
}

// parseHTMLDescription moved to FastAPI backend

function renderNews(items) {
    newsGrid.innerHTML = '';
    
    if(items.length === 0) {
        newsGrid.innerHTML = `
            <div class="col-span-full py-20 flex flex-col items-center justify-center text-center">
                <div class="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mb-6 border border-white/10 shadow-inner">
                    <svg class="w-10 h-10 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path>
                    </svg>
                </div>
                <h3 class="text-2xl font-bold text-white mb-3">No articles found</h3>
                <p class="text-gray-400 max-w-sm">We couldn't find any recent articles for "<span class="text-gray-200 font-medium">${currentQuery}</span>". Try searching for a different topic.</p>
            </div>
        `;
        return;
    }
    
    items.forEach((item, index) => {
        const title = item.title || 'Untitled Story';
        const link = item.link || '#';
        const pubDate = item.pubDate || new Date().toISOString();
        const sourceName = item.source || '';
        let imgSrc = item.thumbnail;
        const snippet = item.snippet;
        const logoSrc = item.logo;
        
        let publisher = 'Unknown Publisher';
        
        // Extract exact publisher from title (Usually formatted as 'Headline - Publisher')
        let cleanTitle = title;
        const titleParts = title.split(' - ');
        if(titleParts.length > 1) {
            const possiblePublisher = titleParts[titleParts.length - 1];
            if (possiblePublisher.length < 45) {
                publisher = possiblePublisher;
                titleParts.pop();
                cleanTitle = titleParts.join(' - ');
            }
        }
        
        // Fallback to source tag
        if (publisher === 'Unknown Publisher' && sourceName) {
            publisher = sourceName;
        }

        const relativeTime = getRelativeTime(pubDate);
        
        // Enhance image resolution by tweaking Google image proxy parameters
        if(imgSrc.includes('googleusercontent.com') && imgSrc.includes('-w') && imgSrc.includes('-h')) {
            imgSrc = imgSrc.replace(/-w\d+-h\d+(-?)/, '-w800-h400$1');
        }
        
        // Calculate animation delay for a cascading stagger effect
        const delay = (index % articleCount) * 50;
        
        const card = document.createElement('a');
        card.href = link;
        card.target = '_blank';
        card.rel = 'noopener noreferrer';
        card.className = "group flex flex-col bg-card backdrop-blur-xl rounded-2xl border border-white/5 overflow-hidden hover:border-white/20 hover:shadow-2xl hover:shadow-primary/20 hover:bg-white/5 transition-all duration-500 animate-fade-in-up block";
        card.style.animationDelay = `${delay}ms`;
        
        // The gradient is always the fallback — pure CSS, can never fail
        const gradient = GRADIENT_FALLBACKS[index % GRADIENT_FALLBACKS.length];
        
        // If no real thumbnail, don't even render an img tag — just show the gradient
        const hasRealImage = imgSrc && imgSrc.startsWith('http');
        
        card.innerHTML = `
            <div class="relative w-full h-56 overflow-hidden flex-shrink-0" style="background:${gradient};">
                ${hasRealImage ? `<img src="${imgSrc}" alt="" class="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-700 ease-out"
                     onerror="this.style.display='none';"
                >` : ''}
                
                <!-- Overlay Gradients -->
                <div class="absolute inset-0 bg-gradient-to-t from-darker via-darker/50 to-transparent opacity-90 group-hover:opacity-75 transition-opacity duration-300"></div>
                
                <!-- Publisher Tag Top Right -->
                <div class="absolute top-4 right-4 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 flex items-center space-x-2 shadow-xl z-20">
                    <img src="${logoSrc}" alt="Logo" class="w-4 h-4 rounded-sm" onerror="this.style.display='none'">
                    <span class="text-[10px] font-bold text-gray-200 tracking-wider uppercase">${publisher}</span>
                </div>
            </div>
            
            <div class="p-6 flex flex-col flex-grow relative bg-card/60 backdrop-blur-2xl">
                <!-- Time indicator -->
                <div class="flex items-center space-x-2 text-primary/80 text-[11px] font-semibold mb-3 tracking-widest uppercase">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <span>${relativeTime}</span>
                </div>
                
                <!-- Headline -->
                <h3 class="text-lg font-bold text-white mb-4 leading-snug group-hover:text-primary transition-colors line-clamp-3">
                    ${cleanTitle}
                </h3>
                
                <!-- Snippet -->
                <div class="mt-auto">
                    <p class="text-[13px] text-gray-400/90 line-clamp-4 leading-relaxed border-l-[3px] border-white/5 pl-4 italic">
                        "${snippet}"
                    </p>
                </div>
                
                <!-- Hover indicator line -->
                <div class="absolute bottom-0 left-0 w-0 h-1 bg-gradient-to-r from-primary to-indigo-500 group-hover:w-full transition-all duration-500 ease-out"></div>
            </div>
        `;
        
        newsGrid.appendChild(card);
    });
}

// Ensure init fires
window.addEventListener('DOMContentLoaded', init);
