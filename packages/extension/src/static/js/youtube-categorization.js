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
    this.processedUrls = new Set();
    this.scrapeInterval = null;
    this.isScraping = false;
    this.scrapeDelay = 500;
    this.maxUrlsPerBatch = 10;

    // Categorization state
    this.videoCategories = new Map(); // video_id -> category
    this.overlayedVideos = new Set(); // Track videos that already have overlays
    this.tempOverlayedVideos = new Set(); // Track videos with temporary overlays
    this.unblockedSections = new Set(); // Track sections user has unblocked
    
    // DOM observer
    this.domObserverTimeout = null;

    this.init();

    // Watch behavior tracking
    this.currentVideoId = null;
    this.currentCategory = null;
    this.watchStartTime = null;
    this.watchStartLogged = false;
    this.lastWatchLogTime = null;
    this.watchTrackingInterval = null;
  }

  async init() {
    if (!this.isYouTubePage()) {
      return;
    }

    console.log("[YouTube Categorization] Initializing on YouTube page");

    // Inject CSS
    this.injectStyles();

    // Setup navigation listener
    this.setupNavigationListener();

    // Setup message listener
    this.setupMessageListener();

    // Setup theme change listener
    this.setupThemeChangeListener();

    // Check if extension is enabled before starting
    const isEnabled = await this.isExtensionEnabled();
    console.log("[YouTube Categorization] Extension enabled:", isEnabled);

    if (isEnabled) {
      this.startExtension();
    } else {
      console.log(
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

  setupThemeChangeListener() {
    // Listen for theme changes
    if (window.matchMedia) {
      const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const lightModeQuery = window.matchMedia('(prefers-color-scheme: light)');
      
      const handleThemeChange = () => {
        const theme = this.getThemePreference();
        console.log(`[YouTube Categorization] Theme changed to: ${theme}`);
        
        // Update overlay colors based on theme
        this.updateOverlayColors(theme);
      };
      
      darkModeQuery.addEventListener('change', handleThemeChange);
      lightModeQuery.addEventListener('change', handleThemeChange);
      
      console.log(`[YouTube Categorization] Theme change listener setup complete`);
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
    
    console.log(`[YouTube Categorization] Updated ${overlays.length} overlays for ${theme} theme`);
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
    console.log("[YouTube Categorization] Starting extension functionality");

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
    console.log("[YouTube Categorization] Stopping extension functionality");

    // Stop scraping
    this.stopScraping();


    // Clear all category labels
    this.clearAllCategoryLabels();

    // Stop intervals (progressCheckInterval no longer used in fixed-duration approach)

    if (this.watchTrackingInterval) {
      clearInterval(this.watchTrackingInterval);
      this.watchTrackingInterval = null;
    }

    // Reset state
    this.processedUrls.clear();
    this.videoCategories.clear();
    this.overlayedVideos.clear();
    this.tempOverlayedVideos.clear();
    this.unblockedSections.clear();
  }

  setupExtensionStateListener() {
    // Listen for changes to the extension enabled state
    chrome.storage.onChanged.addListener((changes, namespace) => {
      if (namespace === "local" && changes.mellowEnabled) {
        const newState = Boolean(changes.mellowEnabled.newValue);
        console.log(
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

  clearAllCategoryLabels() {
    // Remove all category overlays from the page
    const overlays = document.querySelectorAll(".mellow-category-overlay");
    overlays.forEach((overlay) => overlay.remove());

    // Reset video container styles
    const containers = document.querySelectorAll(
      '[style*="pointer-events: none"]'
    );
    containers.forEach((container) => {
      container.style.pointerEvents = "";
      container.style.userSelect = "";
    });

    console.log(
      `[YouTube Categorization] Cleared ${overlays.length} category labels`
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
      console.log(
        "[YouTube Categorization] Navigation detected, restarting and clearing cache"
      );

      // Clear local state
      this.restartScraping();

      // Immediately apply any existing category overlays to new page
      setTimeout(() => {
        console.log("[YouTube Categorization] Applying overlays after navigation");
        this.refreshCategoriesAndApplyLabels();
      }, 1000); // Wait 1 second for page to load

      // Instruct background to clear any queued URLs
      chrome.runtime.sendMessage({ action: "clearQueue" }, () => {
        if (chrome.runtime.lastError) {
          console.warn(
            "[YouTube Categorization] Background clearQueue error:",
            chrome.runtime.lastError
          );
        }
      });

      // Ask backend to clear metadata cache for fresh page
      try {
        const res = await fetch(
          "http://127.0.0.1:5050/api/metadata/clear-cache",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: "page_navigate" }),
          }
        );
        if (!res.ok) {
          console.warn(
            "[YouTube Categorization] Failed to clear backend cache:",
            res.status
          );
        }
      } catch (error) {
        console.warn(
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
    const observer = new MutationObserver(() => handleUrlChange());
    observer.observe(document.body || document, {
      subtree: true,
      childList: true,
    });

    // Fallback interval check in case MutationObserver misses changes
    setInterval(() => handleUrlChange(), 1000);
  }

  setupMessageListener() {
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
        }
      }
    );
  }

  startScraping() {
    if (this.isScraping) {
      return;
    }

    this.isScraping = true;
    console.log("[YouTube Categorization] Starting URL scraping");

    this.scrapeInterval = setInterval(() => {
      this.scrapeUrls();
    }, this.scrapeDelay);

    setTimeout(() => this.scrapeUrls(), 200);
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
    console.log("[YouTube Categorization] Stopped URL scraping");
  }

  restartScraping() {
    this.stopScraping();
    this.processedUrls.clear();
    setTimeout(() => this.startScraping(), 1000);
  }

  scrapeUrls() {
    try {
      const urls = this.extractVideoUrls();
      const newUrls = urls.filter((url) => !this.processedUrls.has(url));

      if (newUrls.length > 0) {
        console.log(
          `[YouTube Categorization] Found ${newUrls.length} new video URLs`
        );

        // Reset stable count since we found new videos
        this.stableCount = 0;
        this.lastScrapedCount = this.processedUrls.size + newUrls.length;

        const batches = this.chunkArray(newUrls, this.maxUrlsPerBatch);

        batches.forEach((batch, index) => {
          setTimeout(() => {
            this.sendUrlsToBackground(batch);
          }, index * 200);
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
      console.warn(
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
          console.log(
            `[YouTube Categorization] Successfully sent ${urls.length} URLs for processing`
          );
        }
      }
    );
  }



  startScrollDetection() {
    let scrollTimeout;
    
    window.addEventListener('scroll', () => {
      const currentScrollY = window.scrollY;
      
      // Clear existing timeout
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }
      
      // Debounce scroll events
      scrollTimeout = setTimeout(() => {
        // Check if user scrolled down significantly
        if (currentScrollY > this.lastScrollY + 500) {
          this.lastScrollY = currentScrollY;
          this.onNewVideosLoaded();
        }
      }, 200);
    });
  }

  onNewVideosLoaded() {
    // Count new videos that appeared
    const currentVideoCount = this.countVisibleVideos();
    if (currentVideoCount > this.pendingVideosCount + 5) { // At least 5 new videos
      console.log("[YouTube Categorization] New videos detected on scroll");
      this.pendingVideosCount = currentVideoCount;
    }
  }

  countVisibleVideos() {
    const thumbnailSelectors = [
      "img[src*='i.ytimg.com/vi/']",
      "img[src*='yt3.ggpht.com']"
    ];
    
    let count = 0;
    thumbnailSelectors.forEach(selector => {
      count += document.querySelectorAll(selector).length;
    });
    
    return count;
  }


  applyFiltersAndLabels() {
    console.log("[YouTube Categorization] Applying filters and labels");
    
    try {
      // Apply category labels immediately
      this.addCategoryLabels();
      
      // Apply overlays immediately for better perceived performance
      this.applyCategoryLabels();
      
      // Apply any blocking filters after a short delay
      setTimeout(() => {
        console.log("[YouTube Categorization] Applying category labels to DOM");
        this.applyCategoryLabels();
      }, 50);
      
      // Apply again after a longer delay to catch any late-loading content
      setTimeout(() => {
        console.log("[YouTube Categorization] Second pass - applying category labels");
        this.refreshCategoriesAndApplyLabels();
      }, 300);
      
      // Third pass for very dynamic content
      setTimeout(() => {
        console.log("[YouTube Categorization] Third pass - applying category labels");
        this.refreshCategoriesAndApplyLabels();
      }, 1000);
    } catch (error) {
      console.error("[YouTube Categorization] Error applying filters and labels:", error);
    }
  }


  startPeriodicLabelRefresh() {
    // Refresh labels every 0.5 seconds to handle YouTube's dynamic DOM changes
    setInterval(async () => {
      // Only refresh if extension is enabled
      const isEnabled = await this.isExtensionEnabled();
      if (!isEnabled) return;

      // Always try to fetch and apply categories, even if we don't have any yet
      this.refreshCategoriesAndApplyLabels();
    }, 500); // Check every 0.5 seconds
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
            console.log(`[YouTube Categorization] Updated categories: ${previousSize} -> ${this.videoCategories.size}`);
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
        console.log("[YouTube Categorization] DOM mutation detected new videos");
        
        // Immediately apply temporary overlays to new videos
        this.applyTemporaryOverlaysToNewElements(newVideoElements);
        
        // If we have categories, also apply final overlays
        if (this.videoCategories.size > 0) {
          console.log("[YouTube Categorization] Applying final overlays to new videos");
          // Debounce the application to avoid excessive calls
          clearTimeout(this.domObserverTimeout);
          this.domObserverTimeout = setTimeout(() => {
            this.applyCategoryLabels();
          }, 50);
        }
      }
    });

    // Start observing the document with the configured parameters
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    console.log("[YouTube Categorization] DOM observer started");
  }

  applyTemporaryOverlaysToNewElements(newVideoElements) {
    console.log(`[YouTube Categorization] Applying temporary overlays to ${newVideoElements.length} new elements`);
    
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
    ];

    newVideoElements.forEach((element) => {
      thumbnailSelectors.forEach((selector) => {
        const thumbnails = element.querySelectorAll ? element.querySelectorAll(selector) : [];
        
        thumbnails.forEach((thumbnail) => {
          const videoId = this.extractVideoIdFromThumbnail(thumbnail);
          if (videoId && !this.tempOverlayedVideos.has(videoId) && !this.overlayedVideos.has(videoId)) {
            console.log(`[YouTube Categorization] Adding temporary overlay for video ${videoId}`);
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
      console.log(`[YouTube Categorization] Could not find video container for video ${videoId}`);
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
      <div class="loading-text">Categorizing...</div>
    `;
    
    overlay.appendChild(loadingContent);

    // Disable interactions on the video container itself
    videoContainer.style.pointerEvents = 'none';
    videoContainer.style.userSelect = 'none';
    
    // Store original styles to restore later
    overlay.setAttribute('data-original-pointer-events', videoContainer.style.pointerEvents || 'auto');
    overlay.setAttribute('data-original-user-select', videoContainer.style.userSelect || 'auto');

    // Make container relative if it isn't already
    if (getComputedStyle(videoContainer).position === 'static') {
      videoContainer.style.position = 'relative';
    }

    // Append the overlay to the video container
    videoContainer.appendChild(overlay);
    
    console.log(`[YouTube Categorization] Temporary overlay added for video ${videoId}`);
  }

  removeTemporaryOverlay(videoId) {
    console.log(`[YouTube Categorization] Removing temporary overlay for video ${videoId}`);
    
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
        
        console.log(`[YouTube Categorization] Restored pointer events for video container`);
      }
      
      tempOverlay.remove();
      console.log(`[YouTube Categorization] Successfully removed temporary overlay for video ${videoId}`);
    } else {
      console.log(`[YouTube Categorization] No temporary overlay found for video ${videoId}`);
    }
  }


  async addCategoryLabels() {
    try {
      console.log("[YouTube Categorization] Fetching categorized videos...");
      // Get categorized videos via service worker
      chrome.runtime.sendMessage(
        {
          action: "getCategorizedVideos",
        },
        (response) => {
          if (response && response.success) {
            console.log(
              `[YouTube Categorization] Received ${response.data.length} categorized videos`
            );
            this.videoCategories = new Map(
              response.data.map((item) => [item.video_id, item.category])
            );
            console.log(
              "[YouTube Categorization] Video categories map:",
              Array.from(this.videoCategories.entries())
            );
            this.applyCategoryLabels();
          } else {
            console.error(
              "[YouTube Categorization] Error fetching categorized videos:",
              response?.error
            );
          }
        }
      );
    } catch (error) {
      console.error(
        "[YouTube Categorization] Error fetching categorized videos:",
        error
      );
    }
  }

  applyCategoryLabels() {
    console.log(
      `[YouTube Categorization] Starting applyCategoryLabels for ${this.videoCategories.size} categorized videos`
    );
    
    if (this.videoCategories.size === 0) {
      console.log("[YouTube Categorization] No categorized videos to apply labels to");
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
    ];

    let totalThumbnails = 0;
    let labelsAdded = 0;

    thumbnailSelectors.forEach((selector) => {
      const thumbnails = document.querySelectorAll(selector);
      totalThumbnails += thumbnails.length;
      console.log(
        `[YouTube Categorization] Found ${thumbnails.length} thumbnails with selector: ${selector}`
      );

      thumbnails.forEach((thumbnail) => {
        const videoId = this.extractVideoIdFromThumbnail(thumbnail);
        if (videoId) {
          console.log(`[YouTube Categorization] Found video ID: ${videoId}`);
          if (this.videoCategories.has(videoId)) {
            const category = this.videoCategories.get(videoId);
            console.log(
              `[YouTube Categorization] Adding BLOCKING OVERLAY "${category}" for video ${videoId}`
            );
            this.addCategoryLabelToThumbnail(thumbnail, category);
            labelsAdded++;
          } else {
            console.log(
              `[YouTube Categorization] No category found for video ${videoId}`
            );
          }
        } else {
          console.log(
            `[YouTube Categorization] Could not extract video ID from thumbnail`
          );
        }
      });
    });

    console.log(
      `[YouTube Categorization] Applied ${labelsAdded} labels out of ${totalThumbnails} thumbnails`
    );

    console.log("[YouTube Categorization] applyCategoryLabels completed successfully");
  }

  async applySectionBlocking() {
    console.log("[YouTube Categorization] Checking for sections to block (Shorts/Playables)");
    
    // Find all potential section containers - simplified approach
    const allRichShelves = document.querySelectorAll('ytd-rich-shelf-renderer');
    console.log(`[YouTube Categorization] Found ${allRichShelves.length} rich shelf renderers`);
    
    allRichShelves.forEach((shelf, index) => {
      console.log(`[YouTube Categorization] Analyzing shelf ${index + 1}/${allRichShelves.length}`);
      this.checkAndBlockSection(shelf);
    });

    // Also check for the specific contents div you mentioned
    const contentsDivs = document.querySelectorAll('#contents.style-scope.ytd-rich-shelf-renderer');
    console.log(`[YouTube Categorization] Found ${contentsDivs.length} contents divs`);
    
    contentsDivs.forEach((contentsDiv, index) => {
      console.log(`[YouTube Categorization] Analyzing contents div ${index + 1}/${contentsDivs.length}`);
      // Get the parent rich shelf renderer
      const parentShelf = contentsDiv.closest('ytd-rich-shelf-renderer');
      if (parentShelf) {
        this.checkAndBlockSection(parentShelf);
      }
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
    
    console.log(`[YouTube Categorization] Checking section ${sectionId}, unblocked sections:`, Array.from(this.unblockedSections));
    
    // Check if user has previously unblocked this section
    if (this.unblockedSections.has(sectionId)) {
      console.log(`[YouTube Categorization] Section ${sectionType} (${sectionId}) was previously unblocked by user, skipping`);
      return;
    }

    console.log(`[YouTube Categorization] Blocking ${sectionType} section (${sectionId})`);
    this.applySectionOverlay(sectionElement, sectionType, sectionId);
  }

  identifySectionType(sectionElement) {
    console.log(`[YouTube Categorization] Identifying section type for element:`, sectionElement);
    
    // Check various indicators to identify section type
    const sectionText = sectionElement.textContent.toLowerCase();
    const sectionHTML = sectionElement.innerHTML.toLowerCase();
    
    console.log(`[YouTube Categorization] Section text preview: "${sectionText.substring(0, 100)}..."`);
    
    // Check for Shorts indicators
    const hasShorts = sectionHTML.includes('shorts') || 
        sectionText.includes('shorts') ||
        sectionElement.hasAttribute('is-shorts') ||
        sectionElement.querySelector('[aria-label*="Shorts"]') ||
        sectionElement.querySelector('[title*="Shorts"]');
        
    if (hasShorts) {
      console.log(`[YouTube Categorization] Identified as Shorts section`);
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
      console.log(`[YouTube Categorization] Identified as Playables section`);
      return 'Playables';
    }

    // Check if it's a rich shelf with short-form content
    if (sectionElement.matches('ytd-rich-shelf-renderer')) {
      const videos = sectionElement.querySelectorAll('[href*="/shorts/"]');
      if (videos.length > 0) {
        console.log(`[YouTube Categorization] Identified as Shorts section (contains ${videos.length} shorts links)`);
        return 'Shorts';
      }
    }

    // Check for any section title/header that might indicate content type
    const titleElements = sectionElement.querySelectorAll('h2, h3, [role="heading"], .title, .header');
    titleElements.forEach(titleEl => {
      const titleText = titleEl.textContent.toLowerCase();
      console.log(`[YouTube Categorization] Found title element: "${titleText}"`);
      if (titleText.includes('shorts')) {
        console.log(`[YouTube Categorization] Identified as Shorts section from title`);
        return 'Shorts';
      }
      if (titleText.includes('playables') || titleText.includes('games')) {
        console.log(`[YouTube Categorization] Identified as Playables section from title`);
        return 'Playables';
      }
    });

    console.log(`[YouTube Categorization] Could not identify section type`);
    return null; // Unknown or non-blockable section
  }

  getSectionId(sectionElement, sectionType) {
    // Create a more stable identifier that doesn't change when overlay is applied
    // Use the element's position in the DOM and its content to create a stable ID
    
    // Get the element's position in the document
    const allSections = document.querySelectorAll('ytd-rich-shelf-renderer');
    const sectionIndex = Array.from(allSections).indexOf(sectionElement);
    
    // Get a stable content identifier (first few characters of text content)
    const textContent = sectionElement.textContent || '';
    const contentHash = textContent.substring(0, 50).replace(/\s+/g, '').toLowerCase();
    
    // Create ID based on section type, index, and content
    const stableId = `${sectionType.toLowerCase()}-${sectionIndex}-${contentHash.substring(0, 10)}`;
    
    console.log(`[YouTube Categorization] Generated section ID: ${stableId} for ${sectionType} section at index ${sectionIndex}`);
    return stableId;
  }


  applySectionOverlay(sectionElement, sectionType, sectionId) {
    // Check if already has an overlay
    if (sectionElement.querySelector('.mellow-section-overlay')) {
      console.log(`[YouTube Categorization] Section already has overlay, skipping`);
      return;
    }

    console.log(`[YouTube Categorization] Applying blocking overlay to ${sectionType} section (ID: ${sectionId})`);

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
      console.log(`[YouTube Categorization] Show Anyway button clicked for ${sectionType} section`);
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      
      try {
        // Track this section as unblocked by user
        this.unblockedSections.add(sectionId);
        console.log(`[YouTube Categorization] Added section ${sectionId} to unblocked sections. Current unblocked:`, Array.from(this.unblockedSections));
        
        // Remove the overlay
        overlay.remove();
        
        // Re-enable interactions with the section
        sectionElement.style.pointerEvents = 'auto';
        sectionElement.style.userSelect = 'auto';
        
        console.log(`[YouTube Categorization] Successfully unblocked ${sectionType} section`);
      } catch (error) {
        console.error(`[YouTube Categorization] Error unblocking section:`, error);
      }
      
      return false;
    }, true);

    // Add mousedown handler to ensure button works
    showButton.addEventListener('mousedown', (e) => {
      console.log(`[YouTube Categorization] Show Anyway button mousedown for ${sectionType} section`);
      e.stopPropagation();
    }, true);

    // Disable interactions with the section
    sectionElement.style.pointerEvents = 'none';
    sectionElement.style.userSelect = 'none';

    // Add overlay click prevention (but allow button clicks through)
    overlay.addEventListener('click', (e) => {
      // Don't prevent clicks on the button
      if (e.target === showButton || showButton.contains(e.target)) {
        console.log(`[YouTube Categorization] Allowing button click through`);
        return;
      }
      
      console.log(`[YouTube Categorization] Preventing overlay click`);
      e.preventDefault();
      e.stopPropagation();
      return false;
    }, true);

    // Append overlay to section
    sectionElement.appendChild(overlay);

    console.log(`[YouTube Categorization] Successfully blocked ${sectionType} section with working button`);
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
          console.log(
            `[YouTube Categorization] Found category "${category}" for video ${videoId}, checking if should block`
          );

          // Check if this video should be blocked
          const shouldBlock = await this.shouldBlockVideo(videoId, category);

          if (shouldBlock) {
            console.log(
              `[YouTube Categorization] Video ${videoId} should be blocked, calling logBlockedVideo`
            );
            this.logBlockedVideo(videoId, category);
          }
        }
      }
    } catch (error) {
      console.warn(
        `[YouTube Categorization] Could not check blocking status for video ${videoId}:`,
        error
      );
    }
  }

  async addCategoryLabelToThumbnail(thumbnail, category) {
    // Extract video ID to track which videos we've already processed
    const videoId = this.extractVideoIdFromThumbnail(thumbnail);
    if (!videoId) {
      console.log(
        `[YouTube Categorization] Could not extract video ID for overlay`
      );
      return;
    }

    // Use probabilistic filter to decide whether to block this video
    const shouldBlock = await this.shouldBlockVideo(videoId, category);

    console.log(
      `[YouTube Categorization] Filter decision for video ${videoId} (${category}): ${
        shouldBlock ? "BLOCKED" : "ALLOWED"
      }`
    );

    // If video should be blocked, call logBlockedVideo regardless of overlay status
    if (shouldBlock) {
      console.log(
        `[YouTube Categorization] Video ${videoId} should be blocked, calling logBlockedVideo`
      );
      this.logBlockedVideo(videoId, category);
    }

    // Check if we've already added a final overlay for this video
    if (this.overlayedVideos.has(videoId)) {
      console.log(
        `[YouTube Categorization] Video ${videoId} already has final overlay, skipping overlay creation`
      );
      return;
    }

    // If video has a temporary overlay, remove it and replace with final overlay
    if (this.tempOverlayedVideos.has(videoId)) {
      console.log(
        `[YouTube Categorization] Replacing temporary overlay with final overlay for video ${videoId}`
      );
      this.removeTemporaryOverlay(videoId);
      this.tempOverlayedVideos.delete(videoId);
    }

    // If video should not be blocked, just remove any temporary overlay and don't add final overlay
    if (!shouldBlock) {
      console.log(
        `[YouTube Categorization] Video ${videoId} is allowed - removing temporary overlay if exists`
      );
      this.removeTemporaryOverlay(videoId);
      this.tempOverlayedVideos.delete(videoId);
      return;
    }

    console.log(
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
        console.log(
          `[YouTube Categorization] Using legacy container: ${videoContainer.tagName}`
        );
      } else {
        console.log(
          `[YouTube Categorization] No suitable container found, skipping`
        );
        return;
      }
    } else {
      console.log(
        `[YouTube Categorization] Using yt-lockup-view-model container`
      );
    }

    // Simple visibility check - if container is hidden, skip this video
    const containerStyle = window.getComputedStyle(videoContainer);
    if (containerStyle.display === "none" || videoContainer.offsetWidth === 0) {
      console.log(
        `[YouTube Categorization] Container is hidden, skipping this video`
      );
      return;
    }

    console.log(
      `[YouTube Categorization] Using container (${videoContainer.offsetWidth}x${videoContainer.offsetHeight})`
    );

    // Remove any existing overlays first
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

    console.log(
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
          console.log(
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

      console.log(
        `[YouTube Categorization] BLOCKED video ${videoId} (${category}) - interactions disabled`
      );
    } else {
      // For unblocked videos: allow interactions to pass through
      // The overlay has pointer-events: none so clicks go through to the video
      videoContainer.style.pointerEvents = "auto";
      videoContainer.style.userSelect = "auto";

      console.log(
        `[YouTube Categorization] ALLOWED video ${videoId} (${category}) - interactions enabled`
      );
    }

    // Mark this video as processed
    this.overlayedVideos.add(videoId);

    // Check if overlay is visible
    const checkVisibility = () => {
      const isVisible = overlay.offsetWidth > 0 && overlay.offsetHeight > 0;
      console.log(
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
      setTimeout(() => checkVisibility(), 100);
    }
  }


  tryImageOverlay(container, category, videoId, shouldBlock = false) {
    console.log(`[YouTube Categorization] Trying image overlay approach...`);

    // Find the actual image element
    const imgElement = container.querySelector("img");
    if (!imgElement) {
      console.log(`[YouTube Categorization] No image found in container`);
      return;
    }

    console.log(
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
      console.log(`[YouTube Categorization] No visible parent found for image`);
      return;
    }

    console.log(
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
      console.log(
        `[YouTube Categorization] Image overlay "${category}" visible: ${isVisible} (${overlay.offsetWidth}x${overlay.offsetHeight})`
      );

      if (isVisible) {
        // Success! Mark this video as overlayed and disable interactions
        this.overlayedVideos.add(videoId);
        console.log(
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
      console.warn(
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
    // Log a blocked video using the new categorization approach
    try {
      console.log(`[YouTube Categorization] ===== LOGGING BLOCKED VIDEO =====`);
      console.log(
        `[YouTube Categorization] Logging blocked video: ${videoId} (${category})`
      );

      // Get video metadata to extract duration
      const metadata = await this.getVideoMetadata(videoId);
      console.log(
        `[YouTube Categorization] Got metadata for ${videoId}:`,
        metadata
      );

      // Use the new categorization approach with should_block=True
      console.log(
        `[YouTube Categorization] Sending POST request to categorization API for ${videoId}`
      );
      const response = await fetch("http://127.0.0.1:5050/api/categorised/", {
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

      console.log(
        `[YouTube Categorization] Categorization API response status: ${response.status} for ${videoId}`
      );

      if (response.ok) {
        const responseData = await response.json();
        console.log(
          `[YouTube Categorization] Successfully categorized and blocked video: ${videoId}`,
          responseData
        );
      } else {
        console.warn(
          `[YouTube Categorization] Failed to categorize and block video: ${videoId}`,
          response.status
        );
      }
    } catch (error) {
      console.error(
        `[YouTube Categorization] Error categorizing and blocking video: ${videoId}`,
        error
      );
    }
  }

  async getVideoMetadata(videoId) {
    // Get video metadata from the server
    try {
      const response = await fetch(
        `http://127.0.0.1:5050/api/metadata/${videoId}`
      );
      if (response.ok) {
        const data = await response.json();
        return data.metadata;
      }
    } catch (error) {
      console.warn(
        `[YouTube Categorization] Could not fetch metadata for ${videoId}:`,
        error
      );
    }
    return null;
  }

  async shouldBlockVideo(videoId, category) {
    // Use the probabilistic filter to decide whether to block a video
    console.log(
      `[YouTube Categorization] Making filter request for ${videoId} (${category})`
    );
    try {
      const response = await fetch("http://127.0.0.1:5050/api/filter/decide", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          category: category,
          video_id: videoId,
        }),
      });

      console.log(
        `[YouTube Categorization] Filter response status: ${response.status} for ${videoId}`
      );

      if (response.ok) {
        const data = await response.json();
        console.log(
          `[YouTube Categorization] Filter decision for ${videoId} (${category}):`,
          data
        );
        console.log(
          `[YouTube Categorization] Should block: ${data.should_filter} for ${videoId}`
        );
        return data.should_filter;
      } else {
        console.warn(
          `[YouTube Categorization] Failed to get filter decision for ${videoId}:`,
          response.status
        );
        // Default to NOT blocking if filter is unavailable - let user decide
        console.log(
          `[YouTube Categorization] Defaulting to ALLOW for ${videoId} due to API error`
        );
        return false;
      }
    } catch (error) {
      console.error(
        `[YouTube Categorization] Error getting filter decision for ${videoId}:`,
        error
      );
      // Default to NOT blocking if filter is unavailable - let user decide
      console.log(
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
        console.log(
          `[YouTube Categorization] Updated filter state for ${videoId} (${category}):`,
          data
        );
        return data;
      } else {
        console.warn(
          `[YouTube Categorization] Failed to update filter state for ${videoId}:`,
          response.status
        );
      }
    } catch (error) {
      console.error(
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
    }, 5000); // Check every 5 seconds
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

      // Get category for current video
      this.currentCategory = await this.getVideoCategory(videoId);

      console.log(
        `[YouTube Categorization] Started tracking video ${videoId} (${this.currentCategory})`
      );

      await this.logWatchStart(videoId);
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
      const response = await fetch("http://127.0.0.1:5050/api/watched/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: videoId,
          start_time: Math.floor(startTimeMs / 1000),
        }),
      });

      if (!response.ok) {
        console.warn(
          `[YouTube Categorization] Failed to log watch start for ${videoId}:`,
          response.status
        );
      } else {
        this.watchStartLogged = true;
        this.lastWatchLogTime = startTimeMs;
      }
    } catch (error) {
      console.warn(
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

    if (this.lastWatchLogTime !== null) {
      const lastSeconds = Math.floor(this.lastWatchLogTime / 1000);
      if (endSeconds <= lastSeconds) {
        return;
      }
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
        console.warn(
          `[YouTube Categorization] Failed to log watch progress for ${videoId}:`,
          response.status
        );
      } else {
        this.lastWatchLogTime = endTimeMs;
      }
    } catch (error) {
      console.warn(
        `[YouTube Categorization] Error logging watch progress for ${videoId}:`,
        error
      );
    }
  }

  async getVideoCategory(videoId) {
    // Get category for a video from the categorized database
    try {
      const response = await fetch(
        `http://127.0.0.1:5050/api/categorised/${videoId}`
      );
      if (response.ok) {
        const data = await response.json();
        return data.category;
      }
    } catch (error) {
      console.warn(
        `[YouTube Categorization] Could not fetch category for ${videoId}:`,
        error
      );
    }
    return null;
  }
}

// Initialize the categorization manager
const youtubeCategorizationManager = new YouTubeCategorizationManager();
