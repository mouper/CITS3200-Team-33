/**
 * Service Worker for YouTube URL Scraping and Metadata Processing
 */

// Configuration
const CONFIG = {
  SERVER_URL: "http://127.0.0.1:5050", // Adjust based on your server setup
  BATCH_SIZE: 10,
  PROCESSING_DELAY: 2000, // 2 seconds between batches
  MAX_RETRIES: 3,
};

// State management
let urlQueue = [];
let isProcessing = false;
let retryCount = 0;

// MV3 background entry
self.addEventListener("install", () => {
  console.log("[Service Worker] Installing...");
  self.skipWaiting();
});

self.addEventListener("activate", () => {
  console.log("[Service Worker] Activating...");
  self.clients.claim();
});

// Message handling
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("[Service Worker] Received message:", request.action);

  switch (request.action) {
    case "processVideoUrls":
      // Check if extension is enabled before processing
      chrome.storage.local.get(["mellowEnabled"], (result) => {
        // Default to true if not set (first time usage)
        const isEnabled =
          result.mellowEnabled !== undefined
            ? Boolean(result.mellowEnabled)
            : true;
        if (isEnabled) {
          handleVideoUrls(request.urls, request.timestamp);
          sendResponse({ success: true });
        } else {
          console.log(
            "[Service Worker] Extension disabled, ignoring video URLs"
          );
          sendResponse({ success: true, ignored: true });
        }
      });
      return true; // Keep message channel open for async response

    case "getProcessingStatus":
      sendResponse({
        queueLength: urlQueue.length,
        isProcessing: isProcessing,
        retryCount: retryCount,
      });
      break;

    case "clearQueue":
      urlQueue = [];
      stopProcessing();
      sendResponse({ success: true });
      break;

    case "getCategorizationProgress":
      handleGetProgress(sendResponse);
      return true; // Keep message channel open for async response

    case "getCategorizedVideos":
      handleGetCategorizedVideos(sendResponse);
      return true; // Keep message channel open for async response

    default:
      sendResponse({ success: false, error: "Unknown action" });
  }

  return true; // Keep message channel open for async response
});

/**
 * Handle incoming video URLs from content script
 */
function handleVideoUrls(urls, timestamp) {
  console.log(`[Service Worker] Received ${urls.length} URLs for processing`);

  // Add URLs to queue with deduplication
  urls.forEach((url) => {
    if (!urlQueue.some((item) => item.url === url)) {
      urlQueue.push({
        url: url,
        timestamp: timestamp,
        retries: 0,
      });
    }
  });

  // Start processing if not already running
  if (!isProcessing) {
    processUrlQueue();
  }
}

/**
 * Process the URL queue by sending batches to the server
 */
async function processUrlQueue() {
  if (isProcessing || urlQueue.length === 0) {
    return;
  }

  isProcessing = true;
  console.log(`[Service Worker] Processing ${urlQueue.length} URLs in queue`);

  try {
    while (urlQueue.length > 0) {
      // Take a batch of URLs
      const batch = urlQueue.splice(0, CONFIG.BATCH_SIZE);

      console.log(`[Service Worker] Processing batch of ${batch.length} URLs`);

      try {
        await sendUrlsToServer(batch);
        retryCount = 0; // Reset retry count on success

        // Wait before processing next batch
        if (urlQueue.length > 0) {
          await new Promise((resolve) =>
            setTimeout(resolve, CONFIG.PROCESSING_DELAY)
          );
        }
      } catch (error) {
        console.error("[Service Worker] Error processing batch:", error);

        // Retry failed URLs
        batch.forEach((item) => {
          item.retries++;
          if (item.retries < CONFIG.MAX_RETRIES) {
            urlQueue.push(item);
          } else {
            console.warn(
              `[Service Worker] Max retries exceeded for URL: ${item.url}`
            );
          }
        });

        retryCount++;

        // Exponential backoff on retry
        const backoffDelay = Math.min(1000 * Math.pow(2, retryCount), 30000);
        await new Promise((resolve) => setTimeout(resolve, backoffDelay));
      }
    }
  } finally {
    isProcessing = false;
    console.log("[Service Worker] Finished processing URL queue");
  }
}

function stopProcessing() {
  if (isProcessing) {
    console.log("[Service Worker] Stopping queue processing");
  }
  isProcessing = false;
}

/**
 * Send URLs to the server for metadata processing
 */
async function sendUrlsToServer(urlBatch) {
  const payload = {
    urls: urlBatch.map((item) => item.url),
    timestamp: Date.now(),
    source: "extension_scraper",
  };

  console.log("[Service Worker] Sending URLs to server:", payload);

  try {
    const response = await fetch(`${CONFIG.SERVER_URL}/api/metadata/batch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Server responded with status: ${response.status}`);
    }

    const result = await response.json();
    console.log("[Service Worker] Server response:", result);

    return result;
  } catch (error) {
    console.error("[Service Worker] Failed to send URLs to server:", error);
    throw error;
  }
}

/**
 * Handle getting categorization progress
 */
async function handleGetProgress(sendResponse) {
  try {
    const response = await fetch(
      `${CONFIG.SERVER_URL}/api/metadata/categorization-progress`
    );
    if (response.ok) {
      const data = await response.json();
      sendResponse({ success: true, data: data });
    } else {
      sendResponse({
        success: false,
        error: `Server responded with status: ${response.status}`,
      });
    }
  } catch (error) {
    console.error(
      "[Service Worker] Error getting categorization progress:",
      error
    );
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle getting categorized videos
 */
async function handleGetCategorizedVideos(sendResponse) {
  try {
    const response = await fetch(
      `${CONFIG.SERVER_URL}/api/metadata/categorized-videos`
    );
    if (response.ok) {
      const data = await response.json();
      sendResponse({ success: true, data: data });
    } else {
      sendResponse({
        success: false,
        error: `Server responded with status: ${response.status}`,
      });
    }
  } catch (error) {
    console.error("[Service Worker] Error getting categorized videos:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Periodic cleanup of old URLs in queue
 */
setInterval(() => {
  const now = Date.now();
  const maxAge = 30 * 60 * 1000; // 30 minutes

  urlQueue = urlQueue.filter((item) => {
    const age = now - item.timestamp;
    return age < maxAge;
  });

  if (urlQueue.length > 0 && !isProcessing) {
    processUrlQueue();
  }
}, 5 * 60 * 1000); // Check every 5 minutes
