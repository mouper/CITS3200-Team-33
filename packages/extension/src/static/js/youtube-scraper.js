/**
 * YouTube URL Scraper Content Script
 * 
 * This script runs on YouTube pages and continuously monitors for recommended videos,
 * extracting their URLs and sending them to the background script for metadata processing.
 */

class YouTubeScraper {
    constructor() {
        this.processedUrls = new Set();
        this.scrapeInterval = null;
        this.isScraping = false;
        this.scrapeDelay = 2000; // 2 seconds between scrapes
        this.maxUrlsPerBatch = 30; // Limit batch size to avoid overwhelming the API
        
        this.init();
    }

    init() {
        // Only run on YouTube pages
        if (!this.isYouTubePage()) {
            return;
        }

        console.log('[YouTube Scraper] Initializing on YouTube page');
        
        // Start scraping when page loads
        this.startScraping();
        
        // Listen for navigation changes (YouTube is SPA)
        this.setupNavigationListener();
        
        // Listen for messages from background script
        this.setupMessageListener();
    }

    isYouTubePage() {
        return window.location.hostname.includes('youtube.com') || 
               window.location.hostname.includes('youtu.be');
    }

    setupNavigationListener() {
        // YouTube uses pushState for navigation, so we need to detect URL changes
        let currentUrl = window.location.href;
        
        const checkUrlChange = () => {
            if (window.location.href !== currentUrl) {
                currentUrl = window.location.href;
                console.log('[YouTube Scraper] Navigation detected, restarting scraper');
                this.restartScraping();
            }
        };

        // Check for URL changes every 500ms
        setInterval(checkUrlChange, 500);
    }

    setupMessageListener() {
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            if (request.action === 'startScraping') {
                this.startScraping();
                sendResponse({ success: true });
            } else if (request.action === 'stopScraping') {
                this.stopScraping();
                sendResponse({ success: true });
            } else if (request.action === 'getScrapingStatus') {
                sendResponse({ 
                    isScraping: this.isScraping,
                    processedCount: this.processedUrls.size 
                });
            }
        });
    }

    startScraping() {
        if (this.isScraping) {
            return;
        }

        this.isScraping = true;
        console.log('[YouTube Scraper] Starting URL scraping');

        // Start the scraping loop
        this.scrapeInterval = setInterval(() => {
            this.scrapeUrls();
        }, this.scrapeDelay);

        // Do an initial scrape
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
        console.log('[YouTube Scraper] Stopped URL scraping');
    }

    restartScraping() {
        this.stopScraping();
        // Clear processed URLs on navigation to new page
        this.processedUrls.clear();
        setTimeout(() => this.startScraping(), 1000);
    }

    scrapeUrls() {
        try {
            const urls = this.extractVideoUrls();
            const newUrls = urls.filter(url => !this.processedUrls.has(url));
            
            if (newUrls.length > 0) {
                console.log(`[YouTube Scraper] Found ${newUrls.length} new video URLs`);
                
                // Process in batches to avoid overwhelming the API
                const batches = this.chunkArray(newUrls, this.maxUrlsPerBatch);
                
                batches.forEach((batch, index) => {
                    setTimeout(() => {
                        this.sendUrlsToBackground(batch);
                    }, index * 1000); // Stagger batches by 1 second
                });
                
                // Mark URLs as processed
                newUrls.forEach(url => this.processedUrls.add(url));
            }
        } catch (error) {
            console.error('[YouTube Scraper] Error during URL scraping:', error);
        }
    }

    extractVideoUrls() {
        const urls = new Set();
        
        // Multiple selectors to catch different YouTube video link formats
        const selectors = [
            'a[href*="/watch?v="]',
            'a[href*="youtu.be/"]',
            'a[href*="/shorts/"]',
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
            // Handle relative URLs
            if (href.startsWith('/')) {
                href = `https://www.youtube.com${href}`;
            }
            
            // Extract video ID from various YouTube URL formats
            const videoId = this.extractVideoId(href);
            if (videoId) {
                return `https://www.youtube.com/watch?v=${videoId}`;
            }
            
            return null;
        } catch (error) {
            console.warn('[YouTube Scraper] Error normalizing URL:', href, error);
            return null;
        }
    }

    extractVideoId(url) {
        const patterns = [
            /[?&]v=([a-zA-Z0-9_-]{11})/,  // watch?v=VIDEOID
            /youtu\.be\/([a-zA-Z0-9_-]{11})/,  // youtu.be/VIDEOID
            /\/shorts\/([a-zA-Z0-9_-]{11})/,  // /shorts/VIDEOID
            /\/embed\/([a-zA-Z0-9_-]{11})/   // /embed/VIDEOID
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
                console.error('[YouTube Scraper] Error sending URLs to background:', chrome.runtime.lastError);
            } else if (response && response.success) {
                console.log(`[YouTube Scraper] Successfully sent ${urls.length} URLs for processing`);
            }
        });
    }

    chunkArray(array, chunkSize) {
        const chunks = [];
        for (let i = 0; i < array.length; i += chunkSize) {
            chunks.push(array.slice(i, i + chunkSize));
        }
        return chunks;
    }
}

// Initialize the scraper when the script loads
const youtubeScraper = new YouTubeScraper();
