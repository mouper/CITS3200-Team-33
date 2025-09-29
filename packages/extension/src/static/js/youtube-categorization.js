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
        this.scrapeDelay = 2000;
        this.maxUrlsPerBatch = 10;
        
        // Categorization state
        this.isCategorizing = false;
        this.categorizationOverlay = null;
        this.progressCheckInterval = null;
        this.videoCategories = new Map(); // video_id -> category
        this.lastScrapedCount = 0;
        this.stableCount = 0; // How many times the count has been stable
        this.overlayedVideos = new Set(); // Track videos that already have overlays
        this.categorizerComplete = false; // Track if categorizer is done
        this.overlaysApplied = false; // Track if overlays have been applied
        
        this.init();
        
        // Watch behavior tracking
        this.currentVideoId = null;
        this.currentCategory = null;
        this.watchStartTime = null;
        this.watchTrackingInterval = null;
    }

    async init() {
        if (!this.isYouTubePage()) {
            return;
        }

        console.log('[YouTube Categorization] Initializing on YouTube page');
        
        // Inject CSS
        this.injectStyles();
        
        // Setup navigation listener
        this.setupNavigationListener();
        
        // Setup message listener
        this.setupMessageListener();
        
        // Check if extension is enabled before starting
        const isEnabled = await this.isExtensionEnabled();
        console.log('[YouTube Categorization] Extension enabled:', isEnabled);
        
        if (isEnabled) {
            this.startExtension();
        } else {
            console.log('[YouTube Categorization] Extension is disabled, not starting');
        }
        
        // Listen for extension enable/disable changes
        this.setupExtensionStateListener();
    }

    isYouTubePage() {
        return window.location.hostname.includes('youtube.com') || 
               window.location.hostname.includes('youtu.be');
    }

    async isExtensionEnabled() {
        return new Promise((resolve) => {
            chrome.storage.local.get(['mellowEnabled'], (result) => {
                // Default to true if not set (first time usage)
                resolve(result.mellowEnabled !== undefined ? Boolean(result.mellowEnabled) : true);
            });
        });
    }

    startExtension() {
        console.log('[YouTube Categorization] Starting extension functionality');
        
        // Start scraping
        this.startScraping();
        
        // Check for existing categorization progress
        this.checkCategorizationStatus();
        
        // Start periodic progress checking (even when overlay is not visible)
        this.startPeriodicProgressCheck();
        
        // Start periodic label refresh to handle YouTube's dynamic DOM
        this.startPeriodicLabelRefresh();
        
        // Start watch behavior tracking
        this.startWatchTracking();
    }

    stopExtension() {
        console.log('[YouTube Categorization] Stopping extension functionality');
        
        // Stop scraping
        this.stopScraping();
        
        // Hide any overlays
        this.hideCategorizationOverlay();
        
        // Clear all category labels
        this.clearAllCategoryLabels();
        
        // Stop intervals
        if (this.progressCheckInterval) {
            clearInterval(this.progressCheckInterval);
            this.progressCheckInterval = null;
        }
        
        if (this.watchTrackingInterval) {
            clearInterval(this.watchTrackingInterval);
            this.watchTrackingInterval = null;
        }
        
        // Reset state
        this.processedUrls.clear();
        this.videoCategories.clear();
        this.overlayedVideos.clear();
        this.isCategorizing = false;
        this.categorizerComplete = false;
        this.overlaysApplied = false;
    }

    setupExtensionStateListener() {
        // Listen for changes to the extension enabled state
        chrome.storage.onChanged.addListener((changes, namespace) => {
            if (namespace === 'local' && changes.mellowEnabled) {
                const newState = Boolean(changes.mellowEnabled.newValue);
                console.log('[YouTube Categorization] Extension state changed:', newState);
                
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
        const overlays = document.querySelectorAll('.mellow-category-overlay');
        overlays.forEach(overlay => overlay.remove());
        
        // Reset video container styles
        const containers = document.querySelectorAll('[style*="pointer-events: none"]');
        containers.forEach(container => {
            container.style.pointerEvents = '';
            container.style.userSelect = '';
        });
        
        console.log(`[YouTube Categorization] Cleared ${overlays.length} category labels`);
    }

    injectStyles() {
        const styleId = 'mellow-categorization-styles';
        if (document.getElementById(styleId)) {
            return;
        }

        const link = document.createElement('link');
        link.id = styleId;
        link.rel = 'stylesheet';
        link.href = chrome.runtime.getURL('static/css/youtube-categorization.css');
        document.head.appendChild(link);
    }

    setupNavigationListener() {
        let currentUrl = window.location.href;
        
        const checkUrlChange = () => {
            if (window.location.href !== currentUrl) {
                currentUrl = window.location.href;
                console.log('[YouTube Categorization] Navigation detected, restarting');
                this.restartScraping();
            }
        };

        setInterval(checkUrlChange, 500);
    }

    setupMessageListener() {
        chrome.runtime.onMessage.addListener(async (request, sender, sendResponse) => {
            if (request.action === 'startScraping') {
                // Only start if extension is enabled
                const isEnabled = await this.isExtensionEnabled();
                if (isEnabled) {
                    this.startScraping();
                }
                sendResponse({ success: true });
            } else if (request.action === 'stopScraping') {
                this.stopScraping();
                sendResponse({ success: true });
            } else if (request.action === 'getScrapingStatus') {
                sendResponse({ 
                    isScraping: this.isScraping,
                    processedCount: this.processedUrls.size,
                    isCategorizing: this.isCategorizing
                });
            } else if (request.action === 'categorizationComplete') {
                this.handleCategorizationComplete(request.categories);
                sendResponse({ success: true });
            }
        });
    }

    startScraping() {
        if (this.isScraping) {
            return;
        }

        this.isScraping = true;
        console.log('[YouTube Categorization] Starting URL scraping');

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
        console.log('[YouTube Categorization] Stopped URL scraping');
    }

    restartScraping() {
        this.stopScraping();
        this.processedUrls.clear();
        setTimeout(() => this.startScraping(), 1000);
    }

    scrapeUrls() {
        try {
            const urls = this.extractVideoUrls();
            const newUrls = urls.filter(url => !this.processedUrls.has(url));
            
            if (newUrls.length > 0) {
                console.log(`[YouTube Categorization] Found ${newUrls.length} new video URLs`);
                
                // Show categorization overlay if not already showing
                if (!this.isCategorizing) {
                    this.showCategorizationOverlay();
                }
                
                // Reset stable count since we found new videos
                this.stableCount = 0;
                this.lastScrapedCount = this.processedUrls.size + newUrls.length;
                
                const batches = this.chunkArray(newUrls, this.maxUrlsPerBatch);
                
                batches.forEach((batch, index) => {
                    setTimeout(() => {
                        this.sendUrlsToBackground(batch);
                    }, index * 1000);
                });
                
                newUrls.forEach(url => this.processedUrls.add(url));
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
            console.error('[YouTube Categorization] Error during URL scraping:', error);
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
            'ytd-playlist-video-renderer a[href*="/watch?v="]'
        ];

        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                const href = element.getAttribute('href');
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
            if (href.startsWith('/')) {
                href = `https://www.youtube.com${href}`;
            }
            
            const videoId = this.extractVideoId(href);
            if (videoId) {
                return `https://www.youtube.com/watch?v=${videoId}`;
            }
            
            return null;
        } catch (error) {
            console.warn('[YouTube Categorization] Error normalizing URL:', href, error);
            return null;
        }
    }

    extractVideoId(url) {
        const patterns = [
            /[?&]v=([a-zA-Z0-9_-]{11})/,
            /youtu\.be\/([a-zA-Z0-9_-]{11})/,
            /\/shorts\/([a-zA-Z0-9_-]{11})/,
            /\/embed\/([a-zA-Z0-9_-]{11})/
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
        chrome.runtime.sendMessage({
            action: 'processVideoUrls',
            urls: urls,
            timestamp: Date.now()
        }, (response) => {
            if (chrome.runtime.lastError) {
                console.error('[YouTube Categorization] Error sending URLs to background:', chrome.runtime.lastError);
            } else if (response && response.success) {
                console.log(`[YouTube Categorization] Successfully sent ${urls.length} URLs for processing`);
            }
        });
    }

    showCategorizationOverlay() {
        if (this.categorizationOverlay) {
            console.log('[YouTube Categorization] Overlay already visible');
            return;
        }

        console.log('[YouTube Categorization] Showing categorization overlay');
        this.isCategorizing = true;
        
        const overlay = document.createElement('div');
        overlay.className = 'mellow-categorization-overlay';
        overlay.innerHTML = `
            <div class="mellow-categorization-content">
                <h1 class="mellow-categorization-title">Categorizing Videos</h1>
                <p class="mellow-categorization-subtitle">Analyzing content to help you make informed viewing choices</p>
                
                <div class="mellow-progress-container">
                    <div class="mellow-progress-bar">
                        <div class="mellow-progress-fill" id="mellow-progress-fill"></div>
                    </div>
                    <div class="mellow-progress-text" id="mellow-progress-text">Starting analysis...</div>
                </div>
                
                <div class="mellow-processing-stats">
                    <div class="mellow-stat">
                        <div class="mellow-stat-number" id="mellow-videos-found">0</div>
                        <div class="mellow-stat-label">Videos Found</div>
                    </div>
                    <div class="mellow-stat">
                        <div class="mellow-stat-number" id="mellow-videos-processed">0</div>
                        <div class="mellow-stat-label">Processed</div>
                    </div>
                    <div class="mellow-stat">
                        <div class="mellow-stat-number" id="mellow-videos-categorized">0</div>
                        <div class="mellow-stat-label">Categorized</div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        this.categorizationOverlay = overlay;

        // Start monitoring progress (if not already running)
        if (!this.progressCheckInterval) {
            this.startProgressMonitoring();
        }
    }

    startProgressMonitoring() {
        this.progressCheckInterval = setInterval(() => {
            this.checkCategorizationProgress();
        }, 2000); // Check every 2 seconds
    }

    startPeriodicProgressCheck() {
        // Check for new videos to process every 5 seconds, even when overlay is hidden
        setInterval(async () => {
            // Only check if extension is enabled
            const isEnabled = await this.isExtensionEnabled();
            if (!isEnabled) return;
            
            if (!this.categorizationOverlay) {
                // Only check if overlay is not already visible
                chrome.runtime.sendMessage({
                    action: 'getCategorizationProgress'
                }, (response) => {
                    if (response && response.success && response.data.unprocessedVideos > 0) {
                        console.log(`[YouTube Categorization] Found ${response.data.unprocessedVideos} unprocessed videos, showing overlay`);
                        this.showCategorizationOverlay();
                        this.updateProgressDisplay(response.data);
                    }
                });
            }
        }, 5000); // Check every 5 seconds
    }

    startPeriodicLabelRefresh() {
        // Refresh labels every 10 seconds to handle YouTube's dynamic DOM changes
        setInterval(async () => {
            // Only refresh if extension is enabled
            const isEnabled = await this.isExtensionEnabled();
            if (!isEnabled) return;
            
            if (this.videoCategories.size > 0) {
                console.log('[YouTube Categorization] Refreshing labels...');
                this.applyCategoryLabels();
            }
        }, 10000); // Check every 10 seconds
    }

    async checkCategorizationProgress() {
        try {
            // Use chrome.runtime.sendMessage to communicate with service worker
            chrome.runtime.sendMessage({
                action: 'getCategorizationProgress'
            }, (response) => {
                if (response && response.success) {
                    this.updateProgressDisplay(response.data);
                } else {
                    console.warn('[YouTube Categorization] Error getting progress:', response?.error);
                }
            });
        } catch (error) {
            console.warn('[YouTube Categorization] Error checking progress:', error);
        }
    }

    updateProgressDisplay(data) {
        const { totalVideos, processedVideos, categorizedVideos, progress, isComplete, freshCount, unprocessedVideos } = data;
        
        // Debug the progress data
        console.log('[YouTube Categorization] Progress data:', {
            totalVideos,
            processedVideos,
            categorizedVideos,
            progress,
            isComplete,
            freshCount,
            unprocessedVideos,
            pendingInCategorizer: data.pendingInCategorizer,
            categorizerRunning: data.categorizerRunning
        });
        
        // Show overlay if there are videos to process and it's not currently showing
        if (unprocessedVideos > 0 && !this.categorizationOverlay) {
            console.log('[YouTube Categorization] New videos to process, showing overlay');
            this.categorizerComplete = false;
            this.overlaysApplied = false;
            this.showCategorizationOverlay();
        }
        
        if (!this.categorizationOverlay) {
            return;
        }
        
        // Update progress bar
        const progressFill = document.getElementById('mellow-progress-fill');
        const progressText = document.getElementById('mellow-progress-text');
        
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }
        
        if (progressText) {
            if (isComplete) {
                progressText.textContent = 'Categorization complete!';
            } else if (data.pendingInCategorizer > 0) {
                progressText.textContent = `Categorizing ${data.pendingInCategorizer} videos... ${progress.toFixed(1)}%`;
            } else if (freshCount > 0) {
                progressText.textContent = `Preparing ${freshCount} videos... ${progress.toFixed(1)}%`;
            } else if (data.categorizerRunning) {
                progressText.textContent = `Categorizer running... ${progress.toFixed(1)}%`;
            } else {
                progressText.textContent = `Starting analysis... ${progress.toFixed(1)}%`;
            }
        }

        // Update stats
        const videosFound = document.getElementById('mellow-videos-found');
        const videosProcessed = document.getElementById('mellow-videos-processed');
        const videosCategorized = document.getElementById('mellow-videos-categorized');
        
        if (videosFound) videosFound.textContent = totalVideos;
        if (videosProcessed) videosProcessed.textContent = processedVideos;
        if (videosCategorized) videosCategorized.textContent = categorizedVideos;

        // Check if categorization is truly complete based on categorizer status
        // isComplete now properly accounts for categorizer pending_count
        console.log('[YouTube Categorization] Completion check:', {
            isComplete,
            pendingInCategorizer: data.pendingInCategorizer,
            unprocessedVideos,
            categorizerRunning: data.categorizerRunning,
            currentCategorizerComplete: this.categorizerComplete,
            currentOverlaysApplied: this.overlaysApplied
        });
        
        if (isComplete) {
            console.log('[YouTube Categorization] Categorizer reports completion - applying labels');
            this.categorizerComplete = true;
            this.addCategoryLabels();
        } else if (data.pendingInCategorizer !== undefined && data.pendingInCategorizer === 0 && unprocessedVideos === 0) {
            console.log('[YouTube Categorization] No pending videos in categorizer - applying labels');
            this.categorizerComplete = true;
            this.addCategoryLabels();
        } else {
            // Reset completion if we have pending videos
            if (data.pendingInCategorizer > 0 || unprocessedVideos > 0) {
                console.log('[YouTube Categorization] Still processing videos - keeping overlay visible');
                this.categorizerComplete = false;
                this.overlaysApplied = false;
            }
        }
        
        // Only hide overlay when both categorizer is complete AND overlays are applied
        if (this.categorizerComplete && this.overlaysApplied) {
            console.log('[YouTube Categorization] Both categorizer complete and overlays applied - hiding progress overlay');
            this.hideCategorizationOverlay();
        }
    }

    hideCategorizationOverlay() {
        if (this.categorizationOverlay) {
            this.categorizationOverlay.classList.add('complete');
            setTimeout(() => {
                if (this.categorizationOverlay) {
                    this.categorizationOverlay.remove();
                    this.categorizationOverlay = null;
                }
            }, 500);
        }
        
        if (this.progressCheckInterval) {
            clearInterval(this.progressCheckInterval);
            this.progressCheckInterval = null;
        }
        
        this.isCategorizing = false;
    }

    async addCategoryLabels() {
        try {
            console.log('[YouTube Categorization] Fetching categorized videos...');
            // Get categorized videos via service worker
            chrome.runtime.sendMessage({
                action: 'getCategorizedVideos'
            }, (response) => {
                if (response && response.success) {
                    console.log(`[YouTube Categorization] Received ${response.data.length} categorized videos`);
                    this.videoCategories = new Map(response.data.map(item => [item.video_id, item.category]));
                    console.log('[YouTube Categorization] Video categories map:', Array.from(this.videoCategories.entries()));
                    this.applyCategoryLabels();
                } else {
                    console.error('[YouTube Categorization] Error fetching categorized videos:', response?.error);
                }
            });
        } catch (error) {
            console.error('[YouTube Categorization] Error fetching categorized videos:', error);
        }
    }

    applyCategoryLabels() {
        console.log(`[YouTube Categorization] Applying labels for ${this.videoCategories.size} categorized videos`);
        
        // Find all video thumbnails and add category labels
        const thumbnailSelectors = [
            // Modern YouTube layout with yt-lockup-view-model
            '.yt-lockup-view-model #thumbnail',
            '.yt-lockup-view-model a[href*="/watch?v="]',
            // Legacy YouTube selectors
            'ytd-video-renderer #thumbnail',
            'ytd-compact-video-renderer #thumbnail', 
            'ytd-rich-item-renderer #thumbnail',
            'ytd-grid-video-renderer #thumbnail',
            'ytd-playlist-video-renderer #thumbnail',
            // Additional selectors for different YouTube layouts
            'ytd-video-renderer ytd-thumbnail',
            'ytd-compact-video-renderer ytd-thumbnail',
            'ytd-rich-item-renderer ytd-thumbnail',
            'ytd-grid-video-renderer ytd-thumbnail',
            'ytd-playlist-video-renderer ytd-thumbnail'
        ];

        let totalThumbnails = 0;
        let labelsAdded = 0;

        thumbnailSelectors.forEach(selector => {
            const thumbnails = document.querySelectorAll(selector);
            totalThumbnails += thumbnails.length;
            console.log(`[YouTube Categorization] Found ${thumbnails.length} thumbnails with selector: ${selector}`);
            
            thumbnails.forEach(thumbnail => {
                const videoId = this.extractVideoIdFromThumbnail(thumbnail);
                if (videoId) {
                    console.log(`[YouTube Categorization] Found video ID: ${videoId}`);
                    if (this.videoCategories.has(videoId)) {
                        const category = this.videoCategories.get(videoId);
                        console.log(`[YouTube Categorization] Adding BLOCKING OVERLAY "${category}" for video ${videoId}`);
                        this.addCategoryLabelToThumbnail(thumbnail, category);
                        labelsAdded++;
                    } else {
                        console.log(`[YouTube Categorization] No category found for video ${videoId}`);
                    }
                    
                    // Always check if this video should be blocked based on its current category
                    this.checkAndBlockVideo(videoId, thumbnail);
                } else {
                    console.log(`[YouTube Categorization] Could not extract video ID from thumbnail`);
                }
            });
        });

        console.log(`[YouTube Categorization] Applied ${labelsAdded} labels out of ${totalThumbnails} thumbnails`);
        
        // Only mark overlays as applied if the categorizer is actually complete
        // Don't mark complete if there are videos that could still be categorized
        if (this.categorizerComplete) {
            this.overlaysApplied = true;
            console.log('[YouTube Categorization] Overlay application complete (categorizer is done)');
            
            // Check if we can hide the progress overlay now
            if (this.categorizerComplete && this.overlaysApplied) {
                console.log('[YouTube Categorization] Both categorizer complete and overlays applied - hiding progress overlay');
                this.hideCategorizationOverlay();
            }
        } else {
            console.log('[YouTube Categorization] Overlay application done but categorizer still processing - keeping overlay visible');
        }
    }

    extractVideoIdFromThumbnail(thumbnail) {
        // Try to find video ID from the thumbnail's parent element or href
        const link = thumbnail.closest('a[href*="/watch?v="]');
        if (link) {
            const href = link.getAttribute('href');
            return this.extractVideoId(href);
        }
        return null;
    }

    async checkAndBlockVideo(videoId, thumbnail) {
        // Check if this video should be blocked based on its current category
        try {
            // Get the current category for this video
            const response = await fetch(`http://127.0.0.1:5050/api/categorised/${videoId}`);
            if (response.ok) {
                const data = await response.json();
                const category = data.category;
                
                if (category) {
                    console.log(`[YouTube Categorization] Found category "${category}" for video ${videoId}, checking if should block`);
                    
                    // Check if this video should be blocked
                    const shouldBlock = await this.shouldBlockVideo(videoId, category);
                    
                    if (shouldBlock) {
                        console.log(`[YouTube Categorization] Video ${videoId} should be blocked, calling logBlockedVideo`);
                        this.logBlockedVideo(videoId, category);
                    }
                }
            }
        } catch (error) {
            console.warn(`[YouTube Categorization] Could not check blocking status for video ${videoId}:`, error);
        }
    }

    async addCategoryLabelToThumbnail(thumbnail, category) {
        // Extract video ID to track which videos we've already processed
        const videoId = this.extractVideoIdFromThumbnail(thumbnail);
        if (!videoId) {
            console.log(`[YouTube Categorization] Could not extract video ID for overlay`);
            return;
        }
        
        // Use probabilistic filter to decide whether to block this video
        const shouldBlock = await this.shouldBlockVideo(videoId, category);
        
        console.log(`[YouTube Categorization] Filter decision for video ${videoId} (${category}): ${shouldBlock ? 'BLOCKED' : 'ALLOWED'}`);
        
        // If video should be blocked, call logBlockedVideo regardless of overlay status
        if (shouldBlock) {
            console.log(`[YouTube Categorization] Video ${videoId} should be blocked, calling logBlockedVideo`);
            this.logBlockedVideo(videoId, category);
        }
        
        // Check if we've already added an overlay for this video
        if (this.overlayedVideos.has(videoId)) {
            console.log(`[YouTube Categorization] Video ${videoId} already has overlay, skipping overlay creation`);
            return;
        }
        
        console.log(`[YouTube Categorization] About to add overlay for video ${videoId} - shouldBlock: ${shouldBlock}`);
        
        // Always show the category overlay, but only block interactions if filtered
        await this.addCategoryOverlay(thumbnail, category, videoId, shouldBlock);
    }

    async addCategoryOverlay(thumbnail, category, videoId, shouldBlock) {
        // Find the video container
        let videoContainer = thumbnail.closest('.yt-lockup-view-model');
        
        if (!videoContainer) {
            // Fallback to legacy containers for older YouTube layouts
            videoContainer = thumbnail.closest('ytd-rich-item-renderer, ytd-video-renderer, ytd-compact-video-renderer, ytd-grid-video-renderer');
            if (videoContainer) {
                console.log(`[YouTube Categorization] Using legacy container: ${videoContainer.tagName}`);
            } else {
                console.log(`[YouTube Categorization] No suitable container found, skipping`);
                return;
            }
        } else {
            console.log(`[YouTube Categorization] Using yt-lockup-view-model container`);
        }
        
        // Simple visibility check - if container is hidden, skip this video
        const containerStyle = window.getComputedStyle(videoContainer);
        if (containerStyle.display === 'none' || videoContainer.offsetWidth === 0) {
            console.log(`[YouTube Categorization] Container is hidden, skipping this video`);
            return;
        }
        
        console.log(`[YouTube Categorization] Using container (${videoContainer.offsetWidth}x${videoContainer.offsetHeight})`);
        
        // Remove any existing overlays first
        const existingOverlays = videoContainer.querySelectorAll('.mellow-category-overlay');
        existingOverlays.forEach(overlay => overlay.remove());

        // Ensure the video container has relative positioning
        videoContainer.style.position = 'relative';
        videoContainer.style.overflow = 'visible';
        
        // Create the category overlay
        const overlay = document.createElement('div');
        overlay.className = `mellow-category-overlay ${shouldBlock ? 'blocked' : 'unblocked'}`;
        overlay.textContent = category;
        
        console.log(`[YouTube Categorization] Creating overlay for video ${videoId} with class: ${overlay.className}`);
        
        // For smaller containers (thumbnails), adjust the overlay styling
        const isSmallContainer = videoContainer.offsetWidth < 200;
        const fontSize = isSmallContainer ? '14px' : '18px';
        const padding = isSmallContainer ? '8px' : '15px';
        
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
            videoContainer.style.pointerEvents = 'none';
            videoContainer.style.userSelect = 'none';
            
            // Add click prevention to the overlay
            overlay.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log(`[YouTube Categorization] Blocked click on video ${videoId} (${category})`);
                return false;
            }, true);
            
            overlay.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }, true);
            
            overlay.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }, true);
            
            console.log(`[YouTube Categorization] BLOCKED video ${videoId} (${category}) - interactions disabled`);
        } else {
            // For unblocked videos: allow interactions to pass through
            // The overlay has pointer-events: none so clicks go through to the video
            videoContainer.style.pointerEvents = 'auto';
            videoContainer.style.userSelect = 'auto';
            
            console.log(`[YouTube Categorization] ALLOWED video ${videoId} (${category}) - interactions enabled`);
        }
        
        // Mark this video as processed
        this.overlayedVideos.add(videoId);
        
        // Check if overlay is visible
        const checkVisibility = () => {
            const isVisible = overlay.offsetWidth > 0 && overlay.offsetHeight > 0;
            console.log(`[YouTube Categorization] Added ${shouldBlock ? 'BLOCKING' : 'LABEL'} overlay "${category}" to container (visible: ${isVisible}, width: ${overlay.offsetWidth}, height: ${overlay.offsetHeight})`);
            return isVisible;
        };
        
        // Check immediately and also after a short delay to handle rendering
        if (!checkVisibility()) {
            setTimeout(() => checkVisibility(), 100);
        }
    }

    createTestOverlay(container, category, videoId) {
        // Don't create test overlays anymore - let's focus on making real overlays work
        console.log(`[YouTube Categorization] Skipping test overlay - focusing on real overlay fixes`);
        
        // Try a different approach - find the actual image element and overlay on that
        this.tryImageOverlay(container, category, videoId);
    }
    
    tryImageOverlay(container, category, videoId) {
        console.log(`[YouTube Categorization] Trying image overlay approach...`);
        
        // Find the actual image element
        const imgElement = container.querySelector('img');
        if (!imgElement) {
            console.log(`[YouTube Categorization] No image found in container`);
            return;
        }
        
        console.log(`[YouTube Categorization] Found image:`, imgElement, `(${imgElement.offsetWidth}x${imgElement.offsetHeight})`);
        
        // Get the image's parent container
        let imageContainer = imgElement.parentElement;
        while (imageContainer && imageContainer.offsetWidth === 0) {
            imageContainer = imageContainer.parentElement;
        }
        
        if (!imageContainer) {
            console.log(`[YouTube Categorization] No visible parent found for image`);
            return;
        }
        
        console.log(`[YouTube Categorization] Using image container:`, imageContainer, `(${imageContainer.offsetWidth}x${imageContainer.offsetHeight})`);
        
        // Remove existing overlays from this container
        const existingOverlays = imageContainer.querySelectorAll('.mellow-category-overlay');
        existingOverlays.forEach(overlay => overlay.remove());
        
        // Create overlay on image container
        const overlay = document.createElement('div');
        overlay.className = 'mellow-category-overlay';
        overlay.textContent = category;
        
        // Make container relative
        imageContainer.style.position = 'relative';
        
        overlay.style.cssText = `
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            background: rgba(0, 0, 0, 0.85) !important;
            color: white !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 14px !important;
            font-weight: bold !important;
            z-index: 9999 !important;
            text-align: center !important;
            padding: 8px !important;
            box-sizing: border-box !important;
            word-wrap: break-word !important;
            text-transform: capitalize !important;
            pointer-events: auto !important;
            border: 2px solid rgba(255, 255, 255, 0.3) !important;
            cursor: default !important;
        `;
        
        imageContainer.appendChild(overlay);
        
        // Check if this worked
        setTimeout(() => {
            const isVisible = overlay.offsetWidth > 0 && overlay.offsetHeight > 0;
            console.log(`[YouTube Categorization] Image overlay "${category}" visible: ${isVisible} (${overlay.offsetWidth}x${overlay.offsetHeight})`);
            
            if (isVisible) {
                // Success! Mark this video as overlayed and disable interactions
                this.overlayedVideos.add(videoId);
                console.log(`[YouTube Categorization] Successfully overlayed video ${videoId}`);
                
                const videoContainer = container.closest('.yt-lockup-view-model, ytd-rich-item-renderer, ytd-video-renderer, ytd-compact-video-renderer');
                if (videoContainer) {
                    videoContainer.style.pointerEvents = 'none';
                    videoContainer.style.userSelect = 'none';
                }
            }
        }, 50);
    }


    async checkCategorizationStatus() {
        // Check if there are already categorized videos on page load
        try {
            chrome.runtime.sendMessage({
                action: 'getCategorizedVideos'
            }, (response) => {
                if (response && response.success && response.data.length > 0) {
                    this.videoCategories = new Map(response.data.map(item => [item.video_id, item.category]));
                    this.applyCategoryLabels();
                }
            });
        } catch (error) {
            console.warn('[YouTube Categorization] Error checking initial categorization status:', error);
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
            console.log(`[YouTube Categorization] Logging blocked video: ${videoId} (${category})`);
            
            // Get video metadata to extract duration
            const metadata = await this.getVideoMetadata(videoId);
            console.log(`[YouTube Categorization] Got metadata for ${videoId}:`, metadata);
            
            // Use the new categorization approach with should_block=True
            console.log(`[YouTube Categorization] Sending POST request to categorization API for ${videoId}`);
            const response = await fetch('http://127.0.0.1:5050/api/categorised/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_id: videoId,
                    category: category,
                    should_block: true,
                    duration: metadata?.metadata?.duration,
                    metadata_json: metadata ? JSON.stringify(metadata) : null
                })
            });
            
            console.log(`[YouTube Categorization] Categorization API response status: ${response.status} for ${videoId}`);
            
            if (response.ok) {
                const responseData = await response.json();
                console.log(`[YouTube Categorization] Successfully categorized and blocked video: ${videoId}`, responseData);
            } else {
                console.warn(`[YouTube Categorization] Failed to categorize and block video: ${videoId}`, response.status);
            }
        } catch (error) {
            console.error(`[YouTube Categorization] Error categorizing and blocking video: ${videoId}`, error);
        }
    }

    async getVideoMetadata(videoId) {
        // Get video metadata from the server
        try {
            const response = await fetch(`http://127.0.0.1:5050/api/metadata/${videoId}`);
            if (response.ok) {
                const data = await response.json();
                return data.metadata;
            }
        } catch (error) {
            console.warn(`[YouTube Categorization] Could not fetch metadata for ${videoId}:`, error);
        }
        return null;
    }

    async shouldBlockVideo(videoId, category) {
        // Use the probabilistic filter to decide whether to block a video
        console.log(`[YouTube Categorization] Making filter request for ${videoId} (${category})`);
        try {
            const response = await fetch('http://127.0.0.1:5050/api/filter/decide', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    category: category,
                    video_id: videoId
                })
            });
            
            console.log(`[YouTube Categorization] Filter response status: ${response.status} for ${videoId}`);
            
            if (response.ok) {
                const data = await response.json();
                console.log(`[YouTube Categorization] Filter decision for ${videoId} (${category}):`, data);
                console.log(`[YouTube Categorization] Should block: ${data.should_filter} for ${videoId}`);
                return data.should_filter;
            } else {
                console.warn(`[YouTube Categorization] Failed to get filter decision for ${videoId}:`, response.status);
                // Default to NOT blocking if filter is unavailable - let user decide
                console.log(`[YouTube Categorization] Defaulting to ALLOW for ${videoId} due to API error`);
                return false;
            }
        } catch (error) {
            console.error(`[YouTube Categorization] Error getting filter decision for ${videoId}:`, error);
            // Default to NOT blocking if filter is unavailable - let user decide
            console.log(`[YouTube Categorization] Defaulting to ALLOW for ${videoId} due to network error`);
            return false;
        }
    }

    async updateFilterState(videoId, category, watched, watchtimeMins) {
        // Update the probabilistic filter state based on user watch behavior
        try {
            const response = await fetch('http://127.0.0.1:5050/api/filter/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    category: category,
                    watched: watched,
                    watchtime_mins: watchtimeMins
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log(`[YouTube Categorization] Updated filter state for ${videoId} (${category}):`, data);
                return data;
            } else {
                console.warn(`[YouTube Categorization] Failed to update filter state for ${videoId}:`, response.status);
            }
        } catch (error) {
            console.error(`[YouTube Categorization] Error updating filter state for ${videoId}:`, error);
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
                // Log the previous video watch time
                const watchTimeMins = (Date.now() - this.watchStartTime) / (1000 * 60);
                await this.updateFilterState(this.currentVideoId, this.currentCategory, true, watchTimeMins);
            }
            
            // Start tracking new video
            this.currentVideoId = videoId;
            this.watchStartTime = Date.now();
            
            // Get category for current video
            this.currentCategory = await this.getVideoCategory(videoId);
            
            console.log(`[YouTube Categorization] Started tracking video ${videoId} (${this.currentCategory})`);
        } else if (!videoId && this.currentVideoId) {
            // Left video page
            if (this.currentCategory && this.watchStartTime) {
                const watchTimeMins = (Date.now() - this.watchStartTime) / (1000 * 60);
                await this.updateFilterState(this.currentVideoId, this.currentCategory, true, watchTimeMins);
            }
            
            this.currentVideoId = null;
            this.currentCategory = null;
            this.watchStartTime = null;
        }
    }

    async getVideoCategory(videoId) {
        // Get category for a video from the categorized database
        try {
            const response = await fetch(`http://127.0.0.1:5050/api/categorised/${videoId}`);
            if (response.ok) {
                const data = await response.json();
                return data.category;
            }
        } catch (error) {
            console.warn(`[YouTube Categorization] Could not fetch category for ${videoId}:`, error);
        }
        return null;
    }
}

// Initialize the categorization manager
const youtubeCategorizationManager = new YouTubeCategorizationManager();
