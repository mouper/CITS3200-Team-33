/**
 * Enhanced YouTube Content Script with Categorization UI
 *
 * This script handles:
 * 1. URL scraping from YouTube pages
 * 2. Categorization progress overlay
 * 3. Category labels on video thumbnails
 */

class YouTubeCategorizationManager {
  constructor() {
    // Performance optimization: disable console logs in production
    this.DEBUG = false; // Set to true for development debugging
    
    this.processedUrls = new Set();
    this.scrapeInterval = null;
    this.isScraping = false;
    this.scrapeDelay = 2000; // Increased from 1000ms to 2000ms to reduce CPU usage
    this.maxUrlsPerBatch = 10;

    // Categorization state
    this.videoCategories = new Map(); // video_id -> category
    this.overlayedVideos = new Set(); // Track videos that already have overlays
    this.tempOverlayedVideos = new Set(); // Track videos with temporary overlays
    this.unblockedSections = new Set(); // Track sections user has unblocked
    
    // DOM observer
    this.domObserverTimeout = null;
    this.domObserver = null;
    this.urlCheckInterval = null;
    this.labelRefreshInterval = null;
    
    // Performance optimization caches
    this._cachedVideoCount = null;
    this._lastCountTime = 0;
    this._videoCategoryCache = new Map(); // Cache for video categories
    this._loggedBlockedVideos = new Set(); // Cache for logged blocked videos to prevent duplicates

    this.init();

    // Watch behavior tracking
    this.currentVideoId = null;
    this.currentCategory = null;
    this.watchStartTime = null;
    this.watchStartLogged = false;
    this.lastWatchLogTime = null;
    this.watchTrackingInterval = null;
  }

  // Performance-optimized logging helper
  debugLog(...args) {
    if (this.DEBUG) {
      console.log(...args);
    }
  }

  debugWarn(...args) {
    if (this.DEBUG) {
      console.warn(...args);
    }
  }

  debugError(...args) {
    if (this.DEBUG) {
      console.error(...args);
    }
  }

  async init() {
    if (!this.isYouTubePage()) {
      return;
    }

    this.debugLog("[YouTube Categorization] Initializing on YouTube page");

    // Inject CSS
    this.injectStyles();

    // Setup navigation listener
    this.setupNavigationListener();

    // Setup message listener
    this.setupMessageListener();

    // Setup theme change listener
    this.setupThemeChangeListener();

    // Start periodic memory cleanup (runs every 24 hours)
    this.startMemoryCleanup();

    // Check if extension is enabled before starting
    const isEnabled = await this.isExtensionEnabled();
    this.debugLog("[YouTube Categorization] Extension enabled:", isEnabled);

    if (isEnabled) {
      this.startExtension();
    } else {
      this.debugLog(
        "[YouTube Categorization] Extension is disabled, not starting"
      );
    }

    // Listen for extension enable/disable changes
    this.setupExtensionStateListener();
  }

  isYouTubePage() {
    return (
      window.location.hostname.includes("youtube.com") ||
      window.location.hostname.includes("youtu.be")
    );
  }

  // Theme detection methods
  getThemePreference() {
    // Method 1: Check CSS media query
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    
    // Method 2: Check system theme via CSS custom properties
    const rootStyles = getComputedStyle(document.documentElement);
    const colorScheme = rootStyles.getPropertyValue('color-scheme');
    if (colorScheme.includes('dark')) return 'dark';
    if (colorScheme.includes('light')) return 'light';
    
    // Method 3: Check YouTube's theme (if available)
    const body = document.body;
    if (body.classList.contains('dark')) return 'dark';
    if (body.classList.contains('light')) return 'light';
    
    // Method 4: Check for dark mode indicators
    const htmlElement = document.documentElement;
    if (htmlElement.getAttribute('dark') === 'true') return 'dark';
    if (htmlElement.getAttribute('light') === 'true') return 'light';
    
    // Fallback: Check background color
    const bgColor = getComputedStyle(document.body).backgroundColor;
    const rgb = bgColor.match(/\d+/g);
    if (rgb) {
      const brightness = (parseInt(rgb[0]) + parseInt(rgb[1]) + parseInt(rgb[2])) / 3;
      return brightness < 128 ? 'dark' : 'light';
    }
    
    return 'unknown';
  }

  isDarkMode() {
    return this.getThemePreference() === 'dark';
  }

  // Network request helper with retry logic
  async makeNetworkRequest(url, options = {}, maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        this.debugLog(`[YouTube Categorization] Making request to ${url} (attempt ${attempt}/${maxRetries})`);
        const response = await fetch(url, options);
        
        if (response.ok) {
          this.debugLog(`[YouTube Categorization] Request successful on attempt ${attempt}`);
          return response;
        } else {
          this.debugWarn(`[YouTube Categorization] Request failed with status ${response.status} on attempt ${attempt}`);
          if (attempt === maxRetries) {
            throw new Error(`Request failed with status ${response.status}`);
          }
        }
      } catch (error) {
        this.debugWarn(`[YouTube Categorization] Request failed on attempt ${attempt}:`, error.message);
        
        if (error.message.includes('ERR_NETWORK_CHANGED') || 
            error.message.includes('ERR_INTERNET_DISCONNECTED') ||
            error.message.includes('ERR_CONNECTION_REFUSED')) {
          
          if (attempt === maxRetries) {
            console.error(`[YouTube Categorization] Network request failed after ${maxRetries} attempts:`, error);
            throw error;
          }
          
          // Wait before retrying (exponential backoff)
          const delay = Math.min(1000 * Math.pow(2, attempt - 1), 4000);
          this.debugLog(`[YouTube Categorization] Waiting ${delay}ms before retry...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        } else {
          // Non-network errors don't retry
          throw error;
        }
      }
    }
  }

  setupThemeChangeListener() {
    // Listen for theme changes
    if (window.matchMedia) {
      const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const lightModeQuery = window.matchMedia('(prefers-color-scheme: light)');
      
      const handleThemeChange = () => {
        const theme = this.getThemePreference();
        this.debugLog(`[YouTube Categorization] Theme changed to: ${theme}`);
        
        // Update overlay colors based on theme
        this.updateOverlayColors(theme);
      };
      
      darkModeQuery.addEventListener('change', handleThemeChange);
      lightModeQuery.addEventListener('change', handleThemeChange);
      
      this.debugLog(`[YouTube Categorization] Theme change listener setup complete`);
    }
  }

  updateOverlayColors(theme) {
    // Update existing overlays with new theme colors
    const overlays = document.querySelectorAll('.mellow-category-overlay');
    overlays.forEach(overlay => {
      if (theme === 'dark') {
        overlay.style.backgroundColor = '#0f0f10';
        overlay.style.color = '#ffffff';
        overlay.style.borderColor = '#0f0f10';
      } else if (theme === 'light') {
        overlay.style.backgroundColor = '#ffffff';
        overlay.style.color = '#000000';
        overlay.style.borderColor = '#e0e0e0';
      }
    });
    
    this.debugLog(`[YouTube Categorization] Updated ${overlays.length} overlays for ${theme} theme`);
  }

  async isExtensionEnabled() {
    return new Promise((resolve) => {
      chrome.storage.local.get(["mellowEnabled"], (result) => {
        // Default to true if not set (first time usage)
        resolve(
          result.mellowEnabled !== undefined
            ? Boolean(result.mellowEnabled)
            : true
        );
      });
    });
  }

  startExtension() {
    this.debugLog("[YouTube Categorization] Starting extension functionality");

    // Start scraping
    this.startScraping();


    // Check for existing categorization progress
    this.checkCategorizationStatus();

    // Start scroll detection for new video loading
    this.startScrollDetection();

    // Start periodic label refresh to handle YouTube's dynamic DOM
    this.startPeriodicLabelRefresh();

    // Start DOM mutation observer for immediate overlay application
    this.startDOMObserver();

    // Start watch behavior tracking
    this.startWatchTracking();
  }

  stopExtension() {
    this.debugLog("[YouTube Categorization] Stopping extension functionality");

    // Stop scraping
    this.stopScraping();


    // Clear all category labels
    this.clearAllCategoryLabels();

    // Stop intervals (progressCheckInterval no longer used in fixed-duration approach)
    if (this.labelRefreshInterval) {
      clearInterval(this.labelRefreshInterval);
      this.labelRefreshInterval = null;
    }
    if (this.urlCheckInterval) {
      clearInterval(this.urlCheckInterval);
      this.urlCheckInterval = null;
    }
    if (this.watchTrackingInterval) {
      clearInterval(this.watchTrackingInterval);
      this.watchTrackingInterval = null;
    }
    if (this.domObserver) {
      this.domObserver.disconnect();
      this.domObserver = null;
    }

    // Reset state
    this.processedUrls.clear();
    this.videoCategories.clear();
    this.overlayedVideos.clear();
    this.tempOverlayedVideos.clear();
    this.unblockedSections.clear();
    this._loggedBlockedVideos.clear();
  }

  setupExtensionStateListener() {
    // Listen for changes to the extension enabled state
    chrome.storage.onChanged.addListener((changes, namespace) => {
      if (namespace === "local" && changes.mellowEnabled) {
        const newState = Boolean(changes.mellowEnabled.newValue);
        this.debugLog(
          "[YouTube Categorization] Extension state changed:",
          newState
        );

        if (newState) {
          this.startExtension();
        } else {
          this.stopExtension();
        }
      }
    });
  }

  restoreAllInteractions() {
    this.debugLog(`[YouTube Categorization] Restoring all interactions across the page`);
    
    // Find all video containers that might have disabled interactions
    const allContainers = document.querySelectorAll(
      'ytd-video-renderer, ytd-rich-item-renderer, ytd-compact-video-renderer, ytd-grid-video-renderer, ytd-playlist-video-renderer, .yt-lockup-view-model'
    );
    
    let restoredCount = 0;
    allContainers.forEach((container) => {
      const computedStyle = getComputedStyle(container);
      if (computedStyle.pointerEvents === 'none') {
        container.style.pointerEvents = 'auto';
        container.style.userSelect = 'auto';
        restoredCount++;
      }
    });
    
    // Also check for any elements with inline disabled styles
    const disabledElements = document.querySelectorAll('[style*="pointer-events: none"]');
    disabledElements.forEach((element) => {
      element.style.pointerEvents = 'auto';
      element.style.userSelect = 'auto';
      restoredCount++;
    });
    
    this.debugLog(`[YouTube Categorization] Restored interactions for ${restoredCount} elements`);
    return restoredCount;
  }

  clearAllCategoryLabels() {
    const overlays = document.querySelectorAll(".mellow-category-overlay");
    overlays.forEach((overlay) => {
      // Restore pointer events before removing overlay
      const videoContainer = overlay.parentElement;
      if (videoContainer) {
        const originalPointerEvents = overlay.getAttribute('data-original-pointer-events') || 'auto';
        const originalUserSelect = overlay.getAttribute('data-original-user-select') || 'auto';
        
        videoContainer.style.pointerEvents = originalPointerEvents;
        videoContainer.style.userSelect = originalUserSelect;
        
        this.debugLog(`[YouTube Categorization] Restored interactions for container`);
      }
      overlay.remove();
    });

    // Reset any remaining video container styles that might have been missed
    const containers = document.querySelectorAll(
      '[style*="pointer-events: none"]'
    );
    containers.forEach((container) => {
      container.style.pointerEvents = "auto";
      container.style.userSelect = "auto";
      this.debugLog(`[YouTube Categorization] Reset missed container interactions`);
    });

    // Clear tracking sets
    this.overlayedVideos.clear();
    this.tempOverlayedVideos.clear();
    this.unblockedSections.clear();
    this._loggedBlockedVideos.clear();

    // Comprehensive restoration as final safety net
    this.restoreAllInteractions();

    this.debugLog(
      `[YouTube Categorization] Cleared ${overlays.length} overlays and reset all interactions`
    );
  }

  injectStyles() {
    const styleId = "mellow-categorization-styles";
    if (document.getElementById(styleId)) {
      return;
    }

    const link = document.createElement("link");
    link.id = styleId;
    link.rel = "stylesheet";
    link.href = chrome.runtime.getURL("static/css/youtube-categorization.css");
    document.head.appendChild(link);
  }

  setupNavigationListener() {
    let currentUrl = window.location.href;
    let pendingForcedRefresh = false;

    const handleUrlChange = async ({ force = false } = {}) => {
      const newUrl = window.location.href;
      const hasUrlChanged = newUrl !== currentUrl;
      if (!hasUrlChanged && !force) {
        return;
      }

      currentUrl = newUrl;
      this.debugLog(
        "[YouTube Categorization] Navigation detected, restarting and clearing cache"
      );

      // Clear local state
      this.restartScraping();
      this._loggedBlockedVideos.clear();
      
      // Immediately apply any existing category overlays to new page
      setTimeout(() => {
        this.debugLog("[YouTube Categorization] Applying overlays after navigation");
        this.refreshCategoriesAndApplyLabels();
      }, 1000); // Wait 1 second for page to load

      // Instruct background to clear any queued URLs
      chrome.runtime.sendMessage({ action: "clearQueue" }, () => {
        if (chrome.runtime.lastError) {
          this.debugWarn(
            "[YouTube Categorization] Background clearQueue error:",
            chrome.runtime.lastError
          );
        }
      });

      // Ask backend to clear metadata cache for fresh page
      try {
        const res = await this.makeNetworkRequest(
          "http://127.0.0.1:5050/api/metadata/clear-cache",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: "page_navigate" }),
          }
        );
        this.debugLog("[YouTube Categorization] Metadata cache cleared");
      } catch (error) {
        this.debugWarn(
          "[YouTube Categorization] Error clearing backend cache:",
          error
        );
      }
    };

    const scheduleForcedRefresh = () => {
      if (pendingForcedRefresh) {
        return;
      }
      pendingForcedRefresh = true;
      setTimeout(() => {
        pendingForcedRefresh = false;
        handleUrlChange({ force: true });
      }, 0);
    };

    window.addEventListener("yt-navigate-start", scheduleForcedRefresh);
    window.addEventListener("yt-navigate-finish", scheduleForcedRefresh);
    window.addEventListener("popstate", scheduleForcedRefresh);

    if (!window.__MELLOW_HISTORY_WRAPPED__) {
      const wrapHistoryMethod = (method) => {
        const original = history[method];
        if (typeof original !== "function") {
          return;
        }
        history[method] = function historyPatchedMethod(...args) {
          const result = original.apply(this, args);
          scheduleForcedRefresh();
          return result;
        };
      };

      wrapHistoryMethod("pushState");
      wrapHistoryMethod("replaceState");
      window.__MELLOW_HISTORY_WRAPPED__ = true;
    }

    // MutationObserver fallback for non-YouTube navigation events
    this.domObserver = new MutationObserver(() => handleUrlChange());
    this.domObserver.observe(document.body || document, {
      subtree: true,
      childList: true,
    });

    // Fallback interval check in case MutationObserver misses changes (further reduced frequency)
    this.urlCheckInterval = setInterval(() => handleUrlChange(), 15000);
  }

  startMemoryCleanup() {
    // Periodic memory cleanup to prevent unbounded growth
    // Runs every 12 hours to limit memory usage during long browsing sessions
    const CLEANUP_INTERVAL = 12 * 60 * 60 * 1000; // 12 hours in milliseconds
    const MAX_CACHE_SIZE = 500; // Keep last 500 entries

    const performCleanup = () => {
      this.debugLog('[Memory Cleanup] Starting periodic memory cleanup...');
      
      // Clean processedUrls
      if (this.processedUrls.size > MAX_CACHE_SIZE) {
        const urls = Array.from(this.processedUrls);
        this.processedUrls = new Set(urls.slice(-MAX_CACHE_SIZE));
        this.debugLog(`[Memory Cleanup] Trimmed processedUrls from ${urls.length} to ${this.processedUrls.size}`);
      }
      
      // Clean videoCategories
      if (this.videoCategories.size > MAX_CACHE_SIZE) {
        const entries = Array.from(this.videoCategories.entries());
        this.videoCategories = new Map(entries.slice(-MAX_CACHE_SIZE));
        this.debugLog(`[Memory Cleanup] Trimmed videoCategories from ${entries.length} to ${this.videoCategories.size}`);
      }
      
      // Clean overlayedVideos
      if (this.overlayedVideos.size > MAX_CACHE_SIZE) {
        const videos = Array.from(this.overlayedVideos);
        this.overlayedVideos = new Set(videos.slice(-MAX_CACHE_SIZE));
        this.debugLog(`[Memory Cleanup] Trimmed overlayedVideos from ${videos.length} to ${this.overlayedVideos.size}`);
      }
      
      // Clean tempOverlayedVideos
      if (this.tempOverlayedVideos.size > MAX_CACHE_SIZE) {
        const tempVideos = Array.from(this.tempOverlayedVideos);
        this.tempOverlayedVideos = new Set(tempVideos.slice(-MAX_CACHE_SIZE));
        this.debugLog(`[Memory Cleanup] Trimmed tempOverlayedVideos from ${tempVideos.length} to ${this.tempOverlayedVideos.size}`);
      }
      
      // Clean _videoCategoryCache
      if (this._videoCategoryCache.size > MAX_CACHE_SIZE) {
        const cacheEntries = Array.from(this._videoCategoryCache.entries());
        this._videoCategoryCache = new Map(cacheEntries.slice(-MAX_CACHE_SIZE));
        this.debugLog(`[Memory Cleanup] Trimmed _videoCategoryCache from ${cacheEntries.length} to ${this._videoCategoryCache.size}`);
      }
      
      // Clean _loggedBlockedVideos
      if (this._loggedBlockedVideos.size > MAX_CACHE_SIZE) {
        const loggedVideos = Array.from(this._loggedBlockedVideos);
        this._loggedBlockedVideos = new Set(loggedVideos.slice(-MAX_CACHE_SIZE));
        this.debugLog(`[Memory Cleanup] Trimmed _loggedBlockedVideos from ${loggedVideos.length} to ${this._loggedBlockedVideos.size}`);
      }
      
      // Clean unblockedSections
      if (this.unblockedSections.size > MAX_CACHE_SIZE) {
        const sections = Array.from(this.unblockedSections);
        this.unblockedSections = new Set(sections.slice(-MAX_CACHE_SIZE));
        this.debugLog(`[Memory Cleanup] Trimmed unblockedSections from ${sections.length} to ${this.unblockedSections.size}`);
      }
      
      this.debugLog('[Memory Cleanup] Cleanup complete:', {
        processedUrls: this.processedUrls.size,
        videoCategories: this.videoCategories.size,
        overlayedVideos: this.overlayedVideos.size,
        tempOverlayedVideos: this.tempOverlayedVideos.size,
        videoCategoryCache: this._videoCategoryCache.size,
        loggedBlockedVideos: this._loggedBlockedVideos.size,
        unblockedSections: this.unblockedSections.size
      });
    };

    // Run cleanup every 24 hours
    setInterval(performCleanup, CLEANUP_INTERVAL);
    
    this.debugLog('[Memory Cleanup] Scheduled to run every 24 hours');
  }

  setupMessageListener() {
    // Debounce settings changes to prevent rapid successive calls
    let settingsChangeTimeout = null;
    
    chrome.runtime.onMessage.addListener(
      async (request, sender, sendResponse) => {
        if (request.action === "startScraping") {
          // Only start if extension is enabled
          const isEnabled = await this.isExtensionEnabled();
          if (isEnabled) {
            this.startScraping();
          }
          sendResponse({ success: true });
        } else if (request.action === "stopScraping") {
          this.stopScraping();
          sendResponse({ success: true });
        } else if (request.action === "getScrapingStatus") {
          sendResponse({
            isScraping: this.isScraping,
            processedCount: this.processedUrls.size,
          });
        } else if (request.action === "categorizationComplete") {
          this.handleCategorizationComplete(request.categories);
          sendResponse({ success: true });
        } else if (request.action === "settingsChanged") {
          // Category settings changed - debounce to prevent rapid successive calls
          if (settingsChangeTimeout) {
            clearTimeout(settingsChangeTimeout);
          }
          
          settingsChangeTimeout = setTimeout(() => {
            this.debugLog("[YouTube Categorization] Settings changed, clearing overlay caches");
            this.overlayedVideos.clear();
            this.tempOverlayedVideos.clear();
            this._loggedBlockedVideos.clear();
            // Clear existing overlays from DOM
            document.querySelectorAll('.mellow-category-overlay').forEach(el => el.remove());
            // Re-evaluate all videos with new settings
            this.refreshCategoriesAndApplyLabels();
          }, 100); // Small delay to batch multiple rapid changes
          
          sendResponse({ success: true });
        }
      }
    );
  }

  startScraping() {
    if (this.isScraping) {
      return;
    }

    this.isScraping = true;
    this.debugLog("[YouTube Categorization] Starting URL scraping");

    this.scrapeInterval = setInterval(() => {
      this.scrapeUrls();
    }, this.scrapeDelay);

    setTimeout(() => this.scrapeUrls(), 1000);
  }

  stopScraping() {
    if (!this.isScraping) {
      return;
    }

    this.isScraping = false;
    if (this.scrapeInterval) {
      clearInterval(this.scrapeInterval);
      this.scrapeInterval = null;
    }
    this.debugLog("[YouTube Categorization] Stopped URL scraping");
  }

  restartScraping() {
    this.stopScraping();
    this.processedUrls.clear();
    setTimeout(() => this.startScraping(), 1500);
  }

  scrapeUrls() {
    try {
      const urls = this.extractVideoUrls();
      const newUrls = urls.filter((url) => !this.processedUrls.has(url));

      if (newUrls.length > 0) {
        this.debugLog(
          `[YouTube Categorization] Found ${newUrls.length} new video URLs`
        );

        // Reset stable count since we found new videos
        this.stableCount = 0;
        this.lastScrapedCount = this.processedUrls.size + newUrls.length;

        const batches = this.chunkArray(newUrls, this.maxUrlsPerBatch);

        batches.forEach((batch, index) => {
          setTimeout(() => {
            this.sendUrlsToBackground(batch);
          }, index * 1000); // Increased from 500ms to 1000ms to reduce load
        });

        newUrls.forEach((url) => this.processedUrls.add(url));
      } else {
        // No new videos found
        if (this.lastScrapedCount === this.processedUrls.size) {
          this.stableCount++;
        } else {
          this.stableCount = 0;
          this.lastScrapedCount = this.processedUrls.size;
        }
      }
    } catch (error) {
      console.error(
        "[YouTube Categorization] Error during URL scraping:",
        error
      );
    }
  }

  extractVideoUrls() {
    const urls = new Set();

    const selectors = [
      // Modern YouTube layout
      '.yt-lockup-view-model a[href*="/watch?v="]',
      // General selectors
      'a[href*="/watch?v="]',
      'a[href*="youtu.be/"]',
      'a[href*="/shorts/"]',
      // Legacy YouTube selectors
      'ytd-video-renderer a[href*="/watch?v="]',
      'ytd-compact-video-renderer a[href*="/watch?v="]',
      'ytd-rich-item-renderer a[href*="/watch?v="]',
      'ytd-grid-video-renderer a[href*="/watch?v="]',
      'ytd-playlist-video-renderer a[href*="/watch?v="]',
    ];

    selectors.forEach((selector) => {
      const elements = document.querySelectorAll(selector);
      elements.forEach((element) => {
        const href = element.getAttribute("href");
        if (href) {
          const fullUrl = this.normalizeUrl(href);
          if (fullUrl) {
            urls.add(fullUrl);
          }
        }
      });
    });

    return Array.from(urls);
  }

  normalizeUrl(href) {
    try {
      if (href.startsWith("/")) {
        href = `https://www.youtube.com${href}`;
      }

      const videoId = this.extractVideoId(href);
      if (videoId) {
        return `https://www.youtube.com/watch?v=${videoId}`;
      }

      return null;
    } catch (error) {
      this.debugWarn(
        "[YouTube Categorization] Error normalizing URL:",
        href,
        error
      );
      return null;
    }
  }

  extractVideoId(url) {
    const patterns = [
      /[?&]v=([a-zA-Z0-9_-]{11})/,
      /youtu\.be\/([a-zA-Z0-9_-]{11})/,
      /\/shorts\/([a-zA-Z0-9_-]{11})/,
      /\/embed\/([a-zA-Z0-9_-]{11})/,
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) {
        return match[1];
      }
    }

    return null;
  }

  sendUrlsToBackground(urls) {
    chrome.runtime.sendMessage(
      {
        action: "processVideoUrls",
        urls: urls,
        timestamp: Date.now(),
      },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error(
            "[YouTube Categorization] Error sending URLs to background:",
            chrome.runtime.lastError
          );
        } else if (response && response.success) {
          this.debugLog(
            `[YouTube Categorization] Successfully sent ${urls.length} URLs for processing`
          );
        }
      }
    );
  }



  startScrollDetection() {
    let scrollTimeout;
    let lastScrollTime = 0;
    
    window.addEventListener('scroll', () => {
      const currentScrollY = window.scrollY;
      const now = Date.now();
      
      // Throttle scroll events to maximum once per 500ms
      if (now - lastScrollTime < 500) {
        return;
      }
      lastScrollTime = now;
      
      // Clear existing timeout
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }
      
      // Debounce scroll events (increased debounce time)
      scrollTimeout = setTimeout(() => {
        // Check if user scrolled down significantly
        if (currentScrollY > this.lastScrollY + 500) {
          this.lastScrollY = currentScrollY;
          this.debugLog("[YouTube Categorization] User scrolled down, checking for new videos");
          this.onNewVideosLoaded();
        }
      }, 1000);
    });
  }

  onNewVideosLoaded() {
    // Count new videos that appeared
    const currentVideoCount = this.countVisibleVideos();
    if (currentVideoCount > this.pendingVideosCount + 5) { // At least 5 new videos
      this.debugLog("[YouTube Categorization] New videos detected on scroll");
      this.pendingVideosCount = currentVideoCount;
    }
  }

  countVisibleVideos() {
    // Cache the count to avoid repeated DOM queries
    if (this._cachedVideoCount && Date.now() - this._lastCountTime < 1000) {
      return this._cachedVideoCount;
    }
    
    const thumbnailSelectors = [
      "img[src*='i.ytimg.com/vi/']",
      "img[src*='yt3.ggpht.com']"
    ];
    
    let count = 0;
    thumbnailSelectors.forEach(selector => {
      count += document.querySelectorAll(selector).length;
    });
    
    this._cachedVideoCount = count;
    this._lastCountTime = Date.now();
    return count;
  }


  applyFiltersAndLabels() {
    this.debugLog("[YouTube Categorization] Applying filters and labels");
    
    try {
      // Apply category labels immediately
      this.addCategoryLabels();
      
      // Apply overlays immediately for better perceived performance
        this.applyCategoryLabels();
      
      // Apply any blocking filters after a short delay (optimized to single pass)
      setTimeout(() => {
        this.debugLog("[YouTube Categorization] Applying category labels to DOM");
        this.applyCategoryLabels();
      }, 100); // Increased from 50ms to 100ms
      
      // Single delayed pass for late-loading content (reduced from 3 passes to 1)
      setTimeout(() => {
        this.debugLog("[YouTube Categorization] Delayed pass - applying category labels");
        this.refreshCategoriesAndApplyLabels();
      }, 800); // Reduced from 1000ms to 800ms
    } catch (error) {
      console.error("[YouTube Categorization] Error applying filters and labels:", error);
    }
  }


  startPeriodicLabelRefresh() {
    // Refresh labels every 3 seconds to handle YouTube's dynamic DOM changes
    this.labelRefreshInterval = setInterval(async () => {
      // Only refresh if extension is enabled
      const isEnabled = await this.isExtensionEnabled();
      if (!isEnabled) return;

      // Always try to fetch and apply categories, even on video pages
      // This is necessary to update temporary overlays on sidebar videos
      this.refreshCategoriesAndApplyLabels();
    }, 1000); // Check every second (1000ms)
  }

  refreshCategoriesAndApplyLabels() {
    // Fetch latest categorized videos and apply labels
      chrome.runtime.sendMessage(
        {
        action: "getCategorizedVideos",
        },
        (response) => {
        if (response && response.success && response.data.length > 0) {
          const previousSize = this.videoCategories.size;
          this.videoCategories = new Map(
            response.data.map((item) => [item.video_id, item.category])
          );
          
          // Log if we got new categories
          if (this.videoCategories.size !== previousSize) {
            this.debugLog(`[YouTube Categorization] Updated categories: ${previousSize} -> ${this.videoCategories.size}`);
          }
          
          // Always apply labels when we have categories
          this.applyCategoryLabels();
        } else if (this.videoCategories.size > 0) {
          // Even if fetch failed, apply existing categories
          this.applyCategoryLabels();
        }
      }
    );
  }

  startDOMObserver() {
    // Create a MutationObserver to watch for new video elements
    const observer = new MutationObserver((mutations) => {
      let hasNewVideos = false;
      const newVideoElements = [];
      
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              // Check if the added node contains video thumbnails
              const hasVideoThumbnails = node.querySelector && (
                node.querySelector('img[src*="i.ytimg.com/vi/"]') ||
                node.querySelector('a[href*="/watch?v="]') ||
                node.matches && (
                  node.matches('ytd-video-renderer') ||
                  node.matches('ytd-rich-item-renderer') ||
                  node.matches('.yt-lockup-view-model')
                )
              );
              
              if (hasVideoThumbnails) {
                hasNewVideos = true;
                newVideoElements.push(node);
              }
            }
          });
        }
      });
      
      if (hasNewVideos) {
        this.debugLog("[YouTube Categorization] DOM mutation detected new videos");
        
        // Immediately apply temporary overlays to new videos
        this.applyTemporaryOverlaysToNewElements(newVideoElements);
        
        // If we have categories, also apply final overlays
        if (this.videoCategories.size > 0) {
          this.debugLog("[YouTube Categorization] Applying final overlays to new videos");
          // Debounce the application to avoid excessive calls (increased debounce time)
        clearTimeout(this.domObserverTimeout);
        this.domObserverTimeout = setTimeout(() => {
          this.applyCategoryLabels();
          }, 1000);
        }
      }
    });

    // Start observing the document with the configured parameters
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    this.debugLog("[YouTube Categorization] DOM observer started");
  }

  async applyTemporaryOverlaysToNewElements(newVideoElements) {
    // Check if extension is enabled before applying temporary overlays
    const isEnabled = await this.isExtensionEnabled();
    if (!isEnabled) {
      this.debugLog("[YouTube Categorization] Extension disabled, skipping temporary overlays");
      return;
    }
    
    this.debugLog(`[YouTube Categorization] Applying temporary overlays to ${newVideoElements.length} new elements`);
    
    const thumbnailSelectors = [
      // Modern YouTube layout with yt-lockup-view-model
      ".yt-lockup-view-model #thumbnail",
      '.yt-lockup-view-model a[href*="/watch?v="]',
      // Legacy YouTube selectors
      "ytd-video-renderer #thumbnail",
      "ytd-compact-video-renderer #thumbnail",
      "ytd-rich-item-renderer #thumbnail",
      "ytd-grid-video-renderer #thumbnail",
      "ytd-playlist-video-renderer #thumbnail",
      // Additional selectors for different YouTube layouts
      "ytd-video-renderer ytd-thumbnail",
      "ytd-compact-video-renderer ytd-thumbnail",
      "ytd-rich-item-renderer ytd-thumbnail",
      "ytd-grid-video-renderer ytd-thumbnail",
      "ytd-playlist-video-renderer ytd-thumbnail",
      "ytm-video-renderer #thumbnail",
      "ytm-compact-video-renderer #thumbnail",
      "ytm-rich-item-renderer #thumbnail",
      "ytm-grid-video-renderer #thumbnail",
      "ytmd-playlist-video-renderer #thumbnail",
      "ytm-video-renderer ytm-thumbnail",
      "ytm-compact-video-renderer ytm-thumbnail",
      "ytm-rich-item-renderer ytm-thumbnail",
      "ytm-grid-video-renderer ytm-thumbnail",
      "ytm-playlist-video-renderer ytm-thumbnail",
    ];

    newVideoElements.forEach((element) => {
      thumbnailSelectors.forEach((selector) => {
        const thumbnails = element.querySelectorAll ? element.querySelectorAll(selector) : [];
        
        thumbnails.forEach((thumbnail) => {
          const videoId = this.extractVideoIdFromThumbnail(thumbnail);
          if (videoId && !this.tempOverlayedVideos.has(videoId) && !this.overlayedVideos.has(videoId)) {
            this.debugLog(`[YouTube Categorization] Adding temporary overlay for video ${videoId}`);
            this.addTemporaryOverlay(thumbnail, videoId);
            this.tempOverlayedVideos.add(videoId);
          }
        });
      });
    });
  }

  addTemporaryOverlay(thumbnail, videoId) {
    // Find the video container
    let videoContainer = thumbnail.closest(".yt-lockup-view-model");
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytd-video-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytd-rich-item-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytd-compact-video-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytd-grid-video-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytd-playlist-video-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytm-video-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytm-rich-item-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytm-compact-video-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytm-grid-video-renderer");
    }
    if (!videoContainer) {
      videoContainer = thumbnail.closest("ytm-playlist-video-renderer");
    }

    if (!videoContainer) {
      this.debugLog(`[YouTube Categorization] Could not find video container for video ${videoId}`);
      return;
    }

    // Create temporary overlay
    const overlay = document.createElement("div");
    overlay.className = "mellow-category-overlay temp-categorizing";
    overlay.setAttribute("data-video-id", videoId);
    
    // Create loading content
    const loadingContent = document.createElement("div");
    loadingContent.className = "temp-loading-content";
    loadingContent.innerHTML = `
      <div class="loading-spinner"></div>
      <div class="loading-text">Categorising...</div>
    `;
    
    overlay.appendChild(loadingContent);

    // Disable interactions on the video container itself
    const originalPointerEvents = getComputedStyle(videoContainer).pointerEvents;
    const originalUserSelect = getComputedStyle(videoContainer).userSelect;
    
    videoContainer.style.pointerEvents = 'none';
    videoContainer.style.userSelect = 'none';
    
    // Store original styles to restore later
    overlay.setAttribute('data-original-pointer-events', originalPointerEvents);
    overlay.setAttribute('data-original-user-select', originalUserSelect);

    // Make container relative if it isn't already
    if (getComputedStyle(videoContainer).position === 'static') {
      videoContainer.style.position = 'relative';
    }

    // Append the overlay to the video container
    videoContainer.appendChild(overlay);
    
    this.debugLog(`[YouTube Categorization] Temporary overlay added for video ${videoId}`);
  }

  removeTemporaryOverlay(videoId) {
    this.debugLog(`[YouTube Categorization] Removing temporary overlay for video ${videoId}`);
    
    // Find and remove temporary overlay by video ID
    const tempOverlay = document.querySelector(`.mellow-category-overlay.temp-categorizing[data-video-id="${videoId}"]`);
    if (tempOverlay) {
      // Find the video container to restore its pointer events
      const videoContainer = tempOverlay.parentElement;
      if (videoContainer) {
        // Restore original pointer events
        const originalPointerEvents = tempOverlay.getAttribute('data-original-pointer-events') || 'auto';
        const originalUserSelect = tempOverlay.getAttribute('data-original-user-select') || 'auto';
        
        videoContainer.style.pointerEvents = originalPointerEvents;
        videoContainer.style.userSelect = originalUserSelect;
        
        this.debugLog(`[YouTube Categorization] Restored pointer events: ${originalPointerEvents}, user-select: ${originalUserSelect}`);
      }
      
      tempOverlay.remove();
      this.debugLog(`[YouTube Categorization] Successfully removed temporary overlay for video ${videoId}`);
    } else {
      this.debugLog(`[YouTube Categorization] No temporary overlay found for video ${videoId}`);
    }
  }


  async addCategoryLabels() {
    try {
      this.debugLog("[YouTube Categorization] Fetching categorized videos...");
      // Get categorized videos via service worker
      chrome.runtime.sendMessage(
        {
          action: "getCategorizedVideos",
        },
        (response) => {
          if (response && response.success) {
            this.debugLog(
              `[YouTube Categorization] Received ${response.data.length} categorized videos`
            );
            this.videoCategories = new Map(
              response.data.map((item) => [item.video_id, item.category])
            );
            this.debugLog(
              "[YouTube Categorization] Video categories map:",
              Array.from(this.videoCategories.entries())
            );
            this.applyCategoryLabels();
          } else {
            this.debugError(
              "[YouTube Categorization] Error fetching categorized videos:",
              response?.error
            );
          }
        }
      );
    } catch (error) {
      this.debugError(
        "[YouTube Categorization] Error fetching categorized videos:",
        error
      );
    }
  }

  applyCategoryLabels() {
    this.debugLog(
      `[YouTube Categorization] Starting applyCategoryLabels for ${this.videoCategories.size} categorized videos`
    );
    
    if (this.videoCategories.size === 0) {
      this.debugLog("[YouTube Categorization] No categorized videos to apply labels to");
      return;
    }

    // Also check for and block entire sections (Shorts/Playables)
    this.applySectionBlocking();

    // Find all video thumbnails and add category labels
    const thumbnailSelectors = [
      // Modern YouTube layout with yt-lockup-view-model
      ".yt-lockup-view-model #thumbnail",
      '.yt-lockup-view-model a[href*="/watch?v="]',
      // Legacy YouTube selectors
      "ytd-video-renderer #thumbnail",
      "ytd-compact-video-renderer #thumbnail",
      "ytd-rich-item-renderer #thumbnail",
      "ytd-grid-video-renderer #thumbnail",
      "ytd-playlist-video-renderer #thumbnail",
      // Additional selectors for different YouTube layouts
      "ytd-video-renderer ytd-thumbnail",
      "ytd-compact-video-renderer ytd-thumbnail",
      "ytd-rich-item-renderer ytd-thumbnail",
      "ytd-grid-video-renderer ytd-thumbnail",
      "ytd-playlist-video-renderer ytd-thumbnail",
      "ytm-video-renderer #thumbnail",
      "ytm-compact-video-renderer #thumbnail",
      "ytm-rich-item-renderer #thumbnail",
      "ytm-grid-video-renderer #thumbnail",
      "ytmd-playlist-video-renderer #thumbnail",
      "ytm-video-renderer ytm-thumbnail",
      "ytm-compact-video-renderer ytm-thumbnail",
      "ytm-rich-item-renderer ytm-thumbnail",
      "ytm-grid-video-renderer ytm-thumbnail",
      "ytm-playlist-video-renderer ytm-thumbnail",
    ];

    let totalThumbnails = 0;
    let labelsAdded = 0;

    thumbnailSelectors.forEach((selector) => {
      const thumbnails = document.querySelectorAll(selector);
      totalThumbnails += thumbnails.length;
      this.debugLog(
        `[YouTube Categorization] Found ${thumbnails.length} thumbnails with selector: ${selector}`
      );

      thumbnails.forEach((thumbnail) => {
        const videoId = this.extractVideoIdFromThumbnail(thumbnail);
        if (videoId) {
          this.debugLog(`[YouTube Categorization] Found video ID: ${videoId}`);
          if (this.videoCategories.has(videoId)) {
            const category = this.videoCategories.get(videoId);
            this.debugLog(
              `[YouTube Categorization] Adding BLOCKING OVERLAY "${category}" for video ${videoId}`
            );
            this.addCategoryLabelToThumbnail(thumbnail, category);
            labelsAdded++;
          } else {
            this.debugLog(
              `[YouTube Categorization] No category found for video ${videoId}`
            );
          }
        } else {
          this.debugLog(
            `[YouTube Categorization] Could not extract video ID from thumbnail`
          );
        }
      });
    });

    this.debugLog(
      `[YouTube Categorization] Applied ${labelsAdded} labels out of ${totalThumbnails} thumbnails`
    );

    this.debugLog("[YouTube Categorization] applyCategoryLabels completed successfully");
  }

  async applySectionBlocking() {
    this.debugLog("[YouTube Categorization] Checking for sections to block (Shorts/Playables)");
    
    // Find all potential section containers - check both rich-shelf and reel-shelf
    const allRichShelves = document.querySelectorAll('ytd-rich-shelf-renderer');
    this.debugLog(`[YouTube Categorization] Found ${allRichShelves.length} rich shelf renderers`);
    
    allRichShelves.forEach((shelf, index) => {
      this.debugLog(`[YouTube Categorization] Analyzing rich shelf ${index + 1}/${allRichShelves.length}`);
      this.checkAndBlockSection(shelf);
    });

    // Also check for reel-shelf-renderer (Shorts sections on video pages)
    const allReelShelves = document.querySelectorAll('ytd-reel-shelf-renderer');
    this.debugLog(`[YouTube Categorization] Found ${allReelShelves.length} reel shelf renderers`);
    
    allReelShelves.forEach((shelf, index) => {
      this.debugLog(`[YouTube Categorization] Analyzing reel shelf ${index + 1}/${allReelShelves.length}`);
      this.checkAndBlockSection(shelf);
    });

    // Also check for ytm-rich-shelf-renderer (YouTube Music sections)
    const allYTMRichShelves = document.querySelectorAll('ytm-rich-shelf-renderer');
    this.debugLog(`[YouTube Categorization] Found ${allYTMRichShelves.length} YouTube Music rich shelf renderers`);
    
    allYTMRichShelves.forEach((shelf, index) => {
      this.debugLog(`[YouTube Categorization] Analyzing YouTube Music rich shelf ${index + 1}/${allYTMRichShelves.length}`);
      this.checkAndBlockSection(shelf);
    });
  }

  checkAndBlockSection(sectionElement) {
    // Check if this section should be blocked based on content analysis
    const sectionType = this.identifySectionType(sectionElement);
    
    if (!sectionType) {
      return; // Not a section we want to block
    }

    // Create a unique identifier for this section
    const sectionId = this.getSectionId(sectionElement, sectionType);
    
    this.debugLog(`[YouTube Categorization] Checking section ${sectionId}, unblocked sections:`, Array.from(this.unblockedSections));
    
    // Check if user has previously unblocked this section
    if (this.unblockedSections.has(sectionId)) {
      this.debugLog(`[YouTube Categorization] Section ${sectionType} (${sectionId}) was previously unblocked by user, skipping`);
      return;
    }

    this.debugLog(`[YouTube Categorization] Blocking ${sectionType} section (${sectionId})`);
    this.applySectionOverlay(sectionElement, sectionType, sectionId);
  }

  identifySectionType(sectionElement) {
    this.debugLog(`[YouTube Categorization] Identifying section type for element:`, sectionElement);
    
    // Check if it's a reel-shelf-renderer (always Shorts)
    if (sectionElement.matches('ytd-reel-shelf-renderer')) {
      this.debugLog(`[YouTube Categorization] Identified as Shorts section (reel-shelf-renderer)`);
      return 'Shorts';
    }
    
    // Check various indicators to identify section type
    const sectionText = sectionElement.textContent.toLowerCase();
    const sectionHTML = sectionElement.innerHTML.toLowerCase();
    
    this.debugLog(`[YouTube Categorization] Section text preview: "${sectionText.substring(0, 100)}..."`);
    
    // Check for Shorts indicators
    const hasShorts = sectionHTML.includes('shorts') || 
        sectionText.includes('shorts') ||
        sectionElement.hasAttribute('is-shorts') ||
        sectionElement.querySelector('[aria-label*="Shorts"]') ||
        sectionElement.querySelector('[title*="Shorts"]');
        
    if (hasShorts) {
      this.debugLog(`[YouTube Categorization] Identified as Shorts section`);
      return 'Shorts';
    }
    
    // Check for Playables/Games indicators
    const hasPlayables = sectionHTML.includes('playables') || 
        sectionText.includes('playables') ||
        sectionHTML.includes('games') || 
        sectionText.includes('games') ||
        sectionElement.querySelector('[aria-label*="Playables"]') ||
        sectionElement.querySelector('[title*="Playables"]') ||
        sectionElement.querySelector('[aria-label*="Games"]');
        
    if (hasPlayables) {
      this.debugLog(`[YouTube Categorization] Identified as Playables section`);
      return 'Playables';
    }

    // Check if it's a rich shelf with short-form content (YouTube or YouTube Music)
    if (sectionElement.matches('ytd-rich-shelf-renderer') || sectionElement.matches('ytm-rich-shelf-renderer')) {
      const videos = sectionElement.querySelectorAll('[href*="/shorts/"]');
      if (videos.length > 0) {
        this.debugLog(`[YouTube Categorization] Identified as Shorts section (contains ${videos.length} shorts links)`);
        return 'Shorts';
      }
    }

    // Check for any section title/header that might indicate content type
    const titleElements = sectionElement.querySelectorAll('h2, h3, [role="heading"], .title, .header');
    titleElements.forEach(titleEl => {
      const titleText = titleEl.textContent.toLowerCase();
      this.debugLog(`[YouTube Categorization] Found title element: "${titleText}"`);
      if (titleText.includes('shorts')) {
        this.debugLog(`[YouTube Categorization] Identified as Shorts section from title`);
        return 'Shorts';
      }
      if (titleText.includes('playables') || titleText.includes('games')) {
        this.debugLog(`[YouTube Categorization] Identified as Playables section from title`);
        return 'Playables';
      }
    });

    this.debugLog(`[YouTube Categorization] Could not identify section type`);
    return null; // Unknown or non-blockable section
  }

  getSectionId(sectionElement, sectionType) {
    // Create a more stable identifier that doesn't change when overlay is applied
    // Use the element's position in the DOM and its content to create a stable ID
    
    // Get the element's position in the document
    // Check both rich-shelf and reel-shelf renderers
    let allSections;
    let sectionIndex;
    
    if (sectionElement.matches('ytd-reel-shelf-renderer')) {
      allSections = document.querySelectorAll('ytd-reel-shelf-renderer');
      sectionIndex = Array.from(allSections).indexOf(sectionElement);
    } else if (sectionElement.matches('ytm-rich-shelf-renderer')) {
      allSections = document.querySelectorAll('ytm-rich-shelf-renderer');
      sectionIndex = Array.from(allSections).indexOf(sectionElement);
    } else {
      allSections = document.querySelectorAll('ytd-rich-shelf-renderer');
      sectionIndex = Array.from(allSections).indexOf(sectionElement);
    }
    
    // Get a stable content identifier (first few characters of text content)
    const textContent = sectionElement.textContent || '';
    const contentHash = textContent.substring(0, 50).replace(/\s+/g, '').toLowerCase();
    
    // Create ID based on section type, index, and content
    const stableId = `${sectionType.toLowerCase()}-${sectionIndex}-${contentHash.substring(0, 10)}`;
    
    this.debugLog(`[YouTube Categorization] Generated section ID: ${stableId} for ${sectionType} section at index ${sectionIndex}`);
    return stableId;
  }


  applySectionOverlay(sectionElement, sectionType, sectionId) {
    // Check if already has an overlay
    if (sectionElement.querySelector('.mellow-section-overlay')) {
      this.debugLog(`[YouTube Categorization] Section already has overlay, skipping`);
      return;
    }

    this.debugLog(`[YouTube Categorization] Applying blocking overlay to ${sectionType} section (ID: ${sectionId})`);

    // Ensure the section has relative positioning
    sectionElement.style.position = 'relative';
    sectionElement.style.overflow = 'visible';

    // Create the section blocking overlay
    const overlay = document.createElement('div');
    overlay.className = 'mellow-section-overlay blocked';
    overlay.setAttribute('data-section-id', sectionId);
    
    // Create content container
    const contentDiv = document.createElement('div');
    contentDiv.className = 'mellow-section-overlay-content';
    
    // Create main text: "Shorts/Playables Section Blocked by [icon] Mellow"
    const mainText = document.createElement('div');
    mainText.className = 'main-text';
    
    // Add proper icon structure
    const iconBox = document.createElement('div');
    iconBox.className = 'icon-box';
    const iconImg = document.createElement('img');
    iconImg.className = 'icon-svg';
    iconImg.src = chrome.runtime.getURL('static/assets/category.svg');
    iconImg.alt = '';
    iconBox.appendChild(iconImg);
    
    const textBefore = document.createTextNode(`${sectionType} Section Blocked by `);
    const textAfter = document.createTextNode(' Mellow');
    mainText.appendChild(textBefore);
    mainText.appendChild(iconBox);
    mainText.appendChild(textAfter);
    
    // Create button
    const showButton = document.createElement('button');
    showButton.className = 'mellow-show-section-btn';
    showButton.textContent = 'Show Anyway';
    
    // Assemble the overlay
    contentDiv.appendChild(mainText);
    contentDiv.appendChild(showButton);
    overlay.appendChild(contentDiv);

    // Add click handler for "Show Anyway" button BEFORE adding to DOM
    showButton.addEventListener('click', (e) => {
      this.debugLog(`[YouTube Categorization] Show Anyway button clicked for ${sectionType} section`);
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      
      try {
        // Track this section as unblocked by user
        this.unblockedSections.add(sectionId);
        this.debugLog(`[YouTube Categorization] Added section ${sectionId} to unblocked sections. Current unblocked:`, Array.from(this.unblockedSections));
        
        // Remove the overlay
        overlay.remove();
        
        // Re-enable interactions with the section
        sectionElement.style.pointerEvents = 'auto';
        sectionElement.style.userSelect = 'auto';
        
        this.debugLog(`[YouTube Categorization] Successfully unblocked ${sectionType} section`);
      } catch (error) {
        console.error(`[YouTube Categorization] Error unblocking section:`, error);
      }
      
      return false;
    }, true);

    // Add mousedown handler to ensure button works
    showButton.addEventListener('mousedown', (e) => {
      this.debugLog(`[YouTube Categorization] Show Anyway button mousedown for ${sectionType} section`);
      e.stopPropagation();
    }, true);

    // Disable interactions with the section
    sectionElement.style.pointerEvents = 'none';
    sectionElement.style.userSelect = 'none';

    // Add overlay click prevention (but allow button clicks through)
    overlay.addEventListener('click', (e) => {
      // Don't prevent clicks on the button
      if (e.target === showButton || showButton.contains(e.target)) {
        this.debugLog(`[YouTube Categorization] Allowing button click through`);
        return;
      }
      
      this.debugLog(`[YouTube Categorization] Preventing overlay click`);
      e.preventDefault();
      e.stopPropagation();
      return false;
    }, true);

    // Append overlay to section
    sectionElement.appendChild(overlay);

    this.debugLog(`[YouTube Categorization] Successfully blocked ${sectionType} section with working button`);
  }

  extractVideoIdFromThumbnail(thumbnail) {
    // Try to find video ID from the thumbnail's parent element or href
    const link = thumbnail.closest('a[href*="/watch?v="]');
    if (link) {
      const href = link.getAttribute("href");
      return this.extractVideoId(href);
    }
    return null;
  }

  async checkAndBlockVideo(videoId, thumbnail) {
    // Check if this video should be blocked based on its current category
    try {
      // Get the current category for this video
      const response = await fetch(
        `http://127.0.0.1:5050/api/categorised/${videoId}`
      );
      if (response.ok) {
        const data = await response.json();
        const category = data.category;

        if (category) {
          this.debugLog(
            `[YouTube Categorization] Found category "${category}" for video ${videoId}, checking if should block`
          );

          // Check if this video should be blocked
          const shouldBlock = await this.shouldBlockVideo(videoId, category);

          if (shouldBlock) {
            this.debugLog(
              `[YouTube Categorization] Video ${videoId} should be blocked, calling logBlockedVideo`
            );
            this.logBlockedVideo(videoId, category);
          }
        }
      }
    } catch (error) {
      this.debugWarn(
        `[YouTube Categorization] Could not check blocking status for video ${videoId}:`,
        error
      );
    }
  }

  async addCategoryLabelToThumbnail(thumbnail, category) {
    // Extract video ID to track which videos we've already processed
    const videoId = this.extractVideoIdFromThumbnail(thumbnail);
    if (!videoId) {
      this.debugLog(
        `[YouTube Categorization] Could not extract video ID for overlay`
      );
      return;
    }

    // PERFORMANCE FIX: Check if we've already processed this video BEFORE making API call
    // This prevents hundreds of unnecessary API requests for videos that are already filtered
    if (this.overlayedVideos.has(videoId)) {
      this.debugLog(
        `[YouTube Categorization] Video ${videoId} already has final overlay, skipping API call and overlay creation`
      );
      return;
    }

    // Use probabilistic filter to decide whether to block this video
    const shouldBlock = await this.shouldBlockVideo(videoId, category);

    this.debugLog(
      `[YouTube Categorization] Filter decision for video ${videoId} (${category}): ${
        shouldBlock ? "BLOCKED" : "ALLOWED"
      }`
    );

    // If video has a temporary overlay, remove it and replace with final overlay
    if (this.tempOverlayedVideos.has(videoId)) {
      this.debugLog(
        `[YouTube Categorization] Replacing temporary overlay with final overlay for video ${videoId}`
      );
      this.removeTemporaryOverlay(videoId);
      this.tempOverlayedVideos.delete(videoId);
    }

    // If video should not be blocked, just remove any temporary overlay and don't add final overlay
    if (!shouldBlock) {
      this.debugLog(
        `[YouTube Categorization] Video ${videoId} is allowed - removing temporary overlay if exists`
      );
      this.removeTemporaryOverlay(videoId);
      this.tempOverlayedVideos.delete(videoId);
      // Mark as processed to prevent re-processing
      this.overlayedVideos.add(videoId);
      return;
    }

    this.debugLog(
      `[YouTube Categorization] Adding final overlay for video ${videoId} - shouldBlock: ${shouldBlock}`
    );

    // Add the final category overlay for blocked videos
    await this.addCategoryOverlay(thumbnail, category, videoId, shouldBlock);
  }

  async addCategoryOverlay(thumbnail, category, videoId, shouldBlock) {
    // Find the video container
    let videoContainer = thumbnail.closest(".yt-lockup-view-model");

    if (!videoContainer) {
      // Fallback to legacy containers for older YouTube layouts
      videoContainer = thumbnail.closest(
        "ytd-rich-item-renderer, ytd-video-renderer, ytd-compact-video-renderer, ytd-grid-video-renderer"
      );
      if (videoContainer) {
        this.debugLog(
          `[YouTube Categorization] Using legacy container: ${videoContainer.tagName}`
        );
      } else {
        this.debugLog(
          `[YouTube Categorization] No suitable container found, skipping`
        );
        return;
      }
    } else {
    this.debugLog(
      `[YouTube Categorization] Using yt-lockup-view-model container`
    );
  }

  // Simple visibility check - if container is hidden, skip this video
  // BUT: Check this BEFORE removing existing overlays to avoid removing overlays when window is resized
  const containerStyle = window.getComputedStyle(videoContainer);
  if (containerStyle.display === "none" || videoContainer.offsetWidth === 0) {
    this.debugLog(
      `[YouTube Categorization] Container is hidden or too small (${videoContainer.offsetWidth}px), skipping to preserve existing overlays`
    );
    return;
  }

  this.debugLog(
    `[YouTube Categorization] Using container (${videoContainer.offsetWidth}x${videoContainer.offsetHeight})`
  );

  // Remove any existing overlays first (AFTER visibility check)
  const existingOverlays = videoContainer.querySelectorAll(
    ".mellow-category-overlay"
  );
  existingOverlays.forEach((overlay) => overlay.remove());

    // Ensure the video container has relative positioning
    videoContainer.style.position = "relative";
    videoContainer.style.overflow = "visible";

    // Create the category overlay
    const overlay = document.createElement("div");
    overlay.className = `mellow-category-overlay ${
      shouldBlock ? "blocked" : "unblocked"
    }`;
    
     // Create structured content for blocked videos
     if (shouldBlock) {
       // Main text: "Blocked by [icon] Mellow"
       const mainText = document.createElement("div");
       mainText.className = "main-text";
       
       // Add proper icon structure
       const iconBox = document.createElement("div");
       iconBox.className = "icon-box";
       const iconImg = document.createElement("img");
       iconImg.className = "icon-svg";
       iconImg.src = chrome.runtime.getURL("static/assets/category.svg");
       iconImg.alt = "";
       iconBox.appendChild(iconImg);
       
       const textBefore = document.createTextNode("Blocked by ");
       const textAfter = document.createTextNode(" Mellow");
       mainText.appendChild(textBefore);
       mainText.appendChild(iconBox);
       mainText.appendChild(textAfter);
       
       // Sub text: "Category: [category name]"
       const subText = document.createElement("div");
       subText.className = "sub-text";
       subText.textContent = `Category: ${category}`;
       
       overlay.appendChild(mainText);
       overlay.appendChild(subText);
     } else {
       // For unblocked videos, keep the simple category text
       overlay.textContent = category;
     }

    this.debugLog(
      `[YouTube Categorization] Creating overlay for video ${videoId} with class: ${overlay.className}`
    );

    // For smaller containers (thumbnails), adjust the overlay styling
    const isSmallContainer = videoContainer.offsetWidth < 200;
    const fontSize = isSmallContainer ? "14px" : "18px";
    const padding = isSmallContainer ? "8px" : "15px";

    // Apply additional inline styles for sizing
    overlay.style.cssText = `
            font-size: ${fontSize} !important;
            padding: ${padding} !important;
        `;

    // Append the overlay to the video container
    videoContainer.appendChild(overlay);

    // Handle interactions based on whether video is blocked
    if (shouldBlock) {
      // For blocked videos: disable interactions on the video container
      // The overlay will catch clicks and prevent them from reaching the video
      videoContainer.style.pointerEvents = "none";
      videoContainer.style.userSelect = "none";

      // Log this blocked video to the database
      this.logBlockedVideo(videoId, category);

      // Add click prevention to the overlay
      overlay.addEventListener(
        "click",
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.debugLog(
            `[YouTube Categorization] Blocked click on video ${videoId} (${category})`
          );
          return false;
        },
        true
      );

      overlay.addEventListener(
        "mousedown",
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          return false;
        },
        true
      );

      overlay.addEventListener(
        "contextmenu",
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          return false;
        },
        true
      );

      this.debugLog(
        `[YouTube Categorization] BLOCKED video ${videoId} (${category}) - interactions disabled`
      );
    } else {
      // For unblocked videos: allow interactions to pass through
      // The overlay has pointer-events: none so clicks go through to the video
      videoContainer.style.pointerEvents = "auto";
      videoContainer.style.userSelect = "auto";

      this.debugLog(
        `[YouTube Categorization] ALLOWED video ${videoId} (${category}) - interactions enabled`
      );
    }

    // Mark this video as processed
    this.overlayedVideos.add(videoId);

    // Check if overlay is visible
    const checkVisibility = () => {
      const isVisible = overlay.offsetWidth > 0 && overlay.offsetHeight > 0;
      this.debugLog(
        `[YouTube Categorization] Added ${
          shouldBlock ? "BLOCKING" : "LABEL"
        } overlay "${category}" to container (visible: ${isVisible}, width: ${
          overlay.offsetWidth
        }, height: ${overlay.offsetHeight})`
      );
      return isVisible;
    };

    // Check immediately and also after a short delay to handle rendering
    if (!checkVisibility()) {
      setTimeout(() => checkVisibility(), 200);
    }
  }


  tryImageOverlay(container, category, videoId, shouldBlock = false) {
    this.debugLog(`[YouTube Categorization] Trying image overlay approach...`);

    // Find the actual image element
    const imgElement = container.querySelector("img");
    if (!imgElement) {
      this.debugLog(`[YouTube Categorization] No image found in container`);
      return;
    }

    this.debugLog(
      `[YouTube Categorization] Found image:`,
      imgElement,
      `(${imgElement.offsetWidth}x${imgElement.offsetHeight})`
    );

    // Get the image's parent container
    let imageContainer = imgElement.parentElement;
    while (imageContainer && imageContainer.offsetWidth === 0) {
      imageContainer = imageContainer.parentElement;
    }

    if (!imageContainer) {
      this.debugLog(`[YouTube Categorization] No visible parent found for image`);
      return;
    }

    this.debugLog(
      `[YouTube Categorization] Using image container:`,
      imageContainer,
      `(${imageContainer.offsetWidth}x${imageContainer.offsetHeight})`
    );

    // Remove existing overlays from this container
    const existingOverlays = imageContainer.querySelectorAll(
      ".mellow-category-overlay"
    );
    existingOverlays.forEach((overlay) => overlay.remove());

    // Create overlay on image container
    const overlay = document.createElement("div");
    overlay.className = `mellow-category-overlay ${shouldBlock ? "blocked" : "unblocked"}`;
    
    // Create structured content for blocked videos
    if (shouldBlock) {
      // Main text: "Blocked by [icon] Mellow"
      const mainText = document.createElement("div");
      mainText.className = "main-text";
      
      // Add proper icon structure
      const iconBox = document.createElement("div");
      iconBox.className = "icon-box";
      const iconImg = document.createElement("img");
      iconImg.className = "icon-svg";
      iconImg.src = chrome.runtime.getURL("static/assets/category.svg");
      iconImg.alt = "";
      iconBox.appendChild(iconImg);
      
      const textBefore = document.createTextNode("Blocked by ");
      const textAfter = document.createTextNode(" Mellow");
      mainText.appendChild(textBefore);
      mainText.appendChild(iconBox);
      mainText.appendChild(textAfter);
      
      // Sub text: "Category: [category name]"
      const subText = document.createElement("div");
      subText.className = "sub-text";
      subText.textContent = `Category: ${category}`;
      
      overlay.appendChild(mainText);
      overlay.appendChild(subText);
    } else {
      // For unblocked videos, keep the simple category text
      overlay.textContent = category;
    }

    // Make container relative
    imageContainer.style.position = "relative";


    imageContainer.appendChild(overlay);

    // Check if this worked
    setTimeout(() => {
      const isVisible = overlay.offsetWidth > 0 && overlay.offsetHeight > 0;
      this.debugLog(
        `[YouTube Categorization] Image overlay "${category}" visible: ${isVisible} (${overlay.offsetWidth}x${overlay.offsetHeight})`
      );

      if (isVisible) {
        // Success! Mark this video as overlayed and disable interactions
        this.overlayedVideos.add(videoId);
        this.debugLog(
          `[YouTube Categorization] Successfully overlayed video ${videoId}`
        );

        const videoContainer = container.closest(
          ".yt-lockup-view-model, ytd-rich-item-renderer, ytd-video-renderer, ytd-compact-video-renderer"
        );
        if (videoContainer) {
          videoContainer.style.pointerEvents = "none";
          videoContainer.style.userSelect = "none";
        }
      }
    }, 50);
  }

  async checkCategorizationStatus() {
    // Check if there are already categorized videos on page load
    try {
      chrome.runtime.sendMessage(
        {
          action: "getCategorizedVideos",
        },
        (response) => {
          if (response && response.success && response.data.length > 0) {
            this.videoCategories = new Map(
              response.data.map((item) => [item.video_id, item.category])
            );
            this.applyCategoryLabels();
          }
        }
      );
    } catch (error) {
      this.debugWarn(
        "[YouTube Categorization] Error checking initial categorization status:",
        error
      );
    }
  }

  chunkArray(array, chunkSize) {
    const chunks = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }

  async logBlockedVideo(videoId, category) {
    // Prevent duplicate logging of the same video
    if (this._loggedBlockedVideos.has(videoId)) {
      this.debugLog(`[YouTube Categorization] Video ${videoId} already logged as blocked, skipping`);
      return;
    }

    // Log a blocked video using the new categorization approach
    try {
      this.debugLog(`[YouTube Categorization] ===== LOGGING BLOCKED VIDEO =====`);
      this.debugLog(
        `[YouTube Categorization] Logging blocked video: ${videoId} (${category})`
      );

      // Mark as logged to prevent duplicates
      this._loggedBlockedVideos.add(videoId);

      // Get video metadata to extract duration (only if not already cached)
      const metadata = await this.getVideoMetadata(videoId);
      this.debugLog(
        `[YouTube Categorization] Got metadata for ${videoId}:`,
        metadata
      );

      // Use the new categorization approach with should_block=True
      this.debugLog(
        `[YouTube Categorization] Sending POST request to categorization API for ${videoId}`
      );
      const response = await this.makeNetworkRequest("http://127.0.0.1:5050/api/categorised/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          video_id: videoId,
          category: category,
          should_block: true,
          duration: metadata?.metadata?.duration,
          metadata_json: metadata ? JSON.stringify(metadata) : null,
        }),
      });

      this.debugLog(
        `[YouTube Categorization] Categorization API response status: ${response.status} for ${videoId}`
      );

      if (response.ok) {
        const responseData = await response.json();
        this.debugLog(
          `[YouTube Categorization] Successfully categorized and blocked video: ${videoId}`,
          responseData
        );
      } else {
        this.debugWarn(
          `[YouTube Categorization] Failed to categorise and block video: ${videoId}`,
          response.status
        );
      }
    } catch (error) {
      this.debugError(
        `[YouTube Categorization] Error categorising and blocking video: ${videoId}`,
        error
      );
    }
  }

  async getVideoMetadata(videoId) {
    // Get video metadata from the server
    try {
      const response = await this.makeNetworkRequest(
        `http://127.0.0.1:5050/api/metadata/${videoId}`
      );
      if (response.ok) {
        const data = await response.json();
        return data.metadata;
      } else if (response.status === 404) {
        // Video metadata not found - this is normal for new videos
        this.debugLog(`[YouTube Categorization] Metadata not found for ${videoId} (404) - this is normal for new videos`);
        return null;
      }
    } catch (error) {
      this.debugWarn(
        `[YouTube Categorization] Could not fetch metadata for ${videoId}:`,
        error
      );
    }
    return null;
  }

  async shouldBlockVideo(videoId, category) {
    // Use the probabilistic filter to decide whether to block a video
    this.debugLog(
      `[YouTube Categorization] Making filter request for ${videoId} (${category})`
    );
    try {
      const response = await this.makeNetworkRequest("http://127.0.0.1:5050/api/filter/decide", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          category: category,
          video_id: videoId,
        }),
      });

      this.debugLog(
        `[YouTube Categorization] Filter response status: ${response.status} for ${videoId}`
      );

      if (response.ok) {
        const data = await response.json();
        this.debugLog(
          `[YouTube Categorization] Filter decision for ${videoId} (${category}):`,
          data
        );
        this.debugLog(
          `[YouTube Categorization] Should block: ${data.should_filter} for ${videoId}`
        );
        return data.should_filter;
      } else {
        this.debugWarn(
          `[YouTube Categorization] Failed to get filter decision for ${videoId}:`,
          response.status
        );
        // Default to NOT blocking if filter is unavailable - let user decide
        this.debugLog(
          `[YouTube Categorization] Defaulting to ALLOW for ${videoId} due to API error`
        );
        return false;
      }
    } catch (error) {
      this.debugError(
        `[YouTube Categorization] Error getting filter decision for ${videoId}:`,
        error
      );
      // Default to NOT blocking if filter is unavailable - let user decide
      this.debugLog(
        `[YouTube Categorization] Defaulting to ALLOW for ${videoId} due to network error`
      );
      return false;
    }
  }

  async updateFilterState(videoId, category, watched, watchtimeMins) {
    // Update the probabilistic filter state based on user watch behavior
    try {
      const response = await fetch("http://127.0.0.1:5050/api/filter/update", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          category: category,
          watched: watched,
          watchtime_mins: watchtimeMins,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        this.debugLog(
          `[YouTube Categorization] Updated filter state for ${videoId} (${category}):`,
          data
        );
        return data;
      } else {
        this.debugWarn(
          `[YouTube Categorization] Failed to update filter state for ${videoId}:`,
          response.status
        );
      }
    } catch (error) {
      this.debugError(
        `[YouTube Categorization] Error updating filter state for ${videoId}:`,
        error
      );
    }
    return null;
  }

  startWatchTracking() {
    // Track when user starts watching a video
    this.watchTrackingInterval = setInterval(() => {
      this.checkCurrentVideo();
    }, 20000); // Increased from 10 seconds to 30 seconds to reduce CPU usage
  }

  async checkCurrentVideo() {
    // Check if we're on a video page and get the current video info
    const videoId = this.extractVideoId(window.location.href);

    if (videoId && videoId !== this.currentVideoId) {
      // New video detected
      if (this.currentVideoId && this.currentCategory && this.watchStartTime) {
        await this.handleVideoEnd();
      }

      // Start tracking new video
      this.currentVideoId = videoId;
      this.watchStartTime = Date.now();
      this.watchStartLogged = false;
      this.lastWatchLogTime = null;

      // Get category for current video (with caching to reduce API calls)
      if (!this.currentCategory) {
      this.currentCategory = await this.getVideoCategory(videoId);
      }

      this.debugLog(
        `[YouTube Categorization] Started tracking video ${videoId} (${this.currentCategory})`
      );

      // Only log watch start once per video
      if (!this.watchStartLogged) {
      await this.logWatchStart(videoId);
        this.watchStartLogged = true;
      }
    } else if (!videoId && this.currentVideoId) {
      // Left video page
      await this.handleVideoEnd();

      this.currentVideoId = null;
      this.currentCategory = null;
      this.watchStartTime = null;
      this.watchStartLogged = false;
      this.lastWatchLogTime = null;
    }
  }

  async handleVideoEnd() {
    if (!this.currentVideoId || !this.watchStartTime) {
      return;
    }

    const now = Date.now();
    if (!this.watchStartLogged) {
      await this.logWatchStart(this.currentVideoId, this.watchStartTime);
    }

    await this.logWatchProgress(this.currentVideoId, this.watchStartTime, now);

    if (this.currentCategory) {
      const watchTimeMins = (now - this.watchStartTime) / (1000 * 60);
      await this.updateFilterState(
        this.currentVideoId,
        this.currentCategory,
        true,
        watchTimeMins
      );
    }
  }

  async logWatchStart(videoId, startTimeMs = Date.now()) {
    try {
      const startSeconds = Math.floor(startTimeMs / 1000);
      const response = await fetch("http://127.0.0.1:5050/api/watched/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: videoId,
          start_time: startSeconds,
          end_time: startSeconds,  // FIXED: Send end_time same as start_time initially
        }),
      });

      if (!response.ok) {
        this.debugWarn(
          `[YouTube Categorization] Failed to log watch start for ${videoId}:`,
          response.status
        );
      } else {
        this.watchStartLogged = true;
        this.lastWatchLogTime = startTimeMs;
      }
    } catch (error) {
      this.debugWarn(
        `[YouTube Categorization] Error logging watch start for ${videoId}:`,
        error
      );
    }
  }

  async logWatchProgress(videoId, startTimeMs, endTimeMs) {
    if (!videoId) {
      return;
    }

    const endSeconds = Math.floor(endTimeMs / 1000);

    // Prevent logging backwards in time
    if (this.lastWatchLogTime !== null) {
      const lastSeconds = Math.floor(this.lastWatchLogTime / 1000);
      if (endSeconds <= lastSeconds) {
        return;
      }
    }

    // Verify startTimeMs matches the stored watchStartTime for this session
    // This prevents accidental creation of duplicate rows
    if (this.watchStartTime && Math.abs(startTimeMs - this.watchStartTime) > 1000) {
      this.debugWarn(
        `[YouTube Categorization] Start time mismatch for ${videoId}: ` +
        `expected ${this.watchStartTime}, got ${startTimeMs}. Using stored value.`
      );
      startTimeMs = this.watchStartTime;
    }

    try {
      const response = await fetch("http://127.0.0.1:5050/api/watched/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: videoId,
          start_time: Math.floor(startTimeMs / 1000),
          end_time: endSeconds,
        }),
      });

      if (!response.ok) {
        this.debugWarn(
          `[YouTube Categorization] Failed to log watch progress for ${videoId}:`,
          response.status
        );
      } else {
        this.lastWatchLogTime = endTimeMs;
      }
    } catch (error) {
      this.debugWarn(
        `[YouTube Categorization] Error logging watch progress for ${videoId}:`,
        error
      );
    }
  }

  async getVideoCategory(videoId) {
    // Check cache first to reduce API calls
    if (this._videoCategoryCache.has(videoId)) {
      return this._videoCategoryCache.get(videoId);
    }

    // Get category for a video from the categorized database
    try {
      const response = await fetch(
        `http://127.0.0.1:5050/api/categorised/${videoId}`
      );
      if (response.ok) {
        const data = await response.json();
        const category = data.category;
        // Cache the result
        this._videoCategoryCache.set(videoId, category);
        return category;
      }
    } catch (error) {
      this.debugWarn(
        `[YouTube Categorization] Could not fetch category for ${videoId}:`,
        error
      );
    }
    return null;
  }
}

// Initialize the categorization manager
const youtubeCategorizationManager = new YouTubeCategorizationManager();
