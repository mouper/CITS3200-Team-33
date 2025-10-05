/**
 * Service Worker for YouTube URL Scraping and Metadata Processing
 * - Prioritises top-of-page videos first (lower `top` value = higher priority).
 * - Sends per-URL result messages back to clients so UI updates dynamically.
 */

// Configuration
const CONFIG = {
  SERVER_URL: "http://127.0.0.1:5050", // Adjust as needed
  BATCH_SIZE: 10,
  PROCESSING_DELAY: 1000, // ms between batches (shorter for more responsiveness)
  MAX_RETRIES: 3,
};

// State management (queue items: { url, top, timestamp, retries, id })
let urlQueue = [];
let isProcessing = false;
let retryCount = 0;

// ID generator for queue items (helps dedupe items with same URL but different DOM instances)
let nextQueueId = 1;

// --- lifecycle events ---
self.addEventListener("install", () => {
  console.log("[Service Worker] Installing...");
  self.skipWaiting();
});
self.addEventListener("activate", () => {
  console.log("[Service Worker] Activating...");
  self.clients.claim();
});

// --- helpers ---
function now() {
  return Date.now();
}

// Reorder queue by priority: smaller top = higher priority. If top missing, treat as large value.
function reorderQueue() {
  urlQueue.sort((a, b) => {
    const at = typeof a.top === "number" ? a.top : Number.POSITIVE_INFINITY;
    const bt = typeof b.top === "number" ? b.top : Number.POSITIVE_INFINITY;
    if (at !== bt) return at - bt;
    // fallback: earlier timestamp first
    return a.timestamp - b.timestamp;
  });
}

// Send status update to all open clients (content scripts / popup)
async function broadcastToClients(message) {
  try {
    const clients = await self.clients.matchAll({ includeUncontrolled: true });
    clients.forEach((c) => {
      try {
        c.postMessage(message);
      } catch (e) {
        // ignore per-client failures
      }
    });
  } catch (e) {
    console.error("[Service Worker] broadcast error:", e);
  }
}

// Persist categorized videos map in chrome.storage.local
async function saveCategorizedVideo(url, metadata) {
  return new Promise((resolve) => {
    chrome.storage.local.get(["categorizedVideos"], (res) => {
      const store = res.categorizedVideos || {};
      store[url] = metadata;
      chrome.storage.local.set({ categorizedVideos: store }, () => resolve());
    });
  });
}

// --- message handler from content scripts ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("[Service Worker] Received message:", request.action);

  switch (request.action) {
    case "processVideoUrls": {
      // Expect request.urls to be array of either strings OR objects { url, top, timestamp }
      chrome.storage.local.get(["mellowEnabled"], (result) => {
        const isEnabled =
          result.mellowEnabled !== undefined ? Boolean(result.mellowEnabled) : true;

        if (!isEnabled) {
          console.log("[Service Worker] Extension disabled, ignoring video URLs");
          sendResponse({ success: true, ignored: true });
          return;
        }

        const incoming = Array.isArray(request.urls) ? request.urls : [];
        handleVideoUrls(incoming, request.timestamp || now());
        sendResponse({ success: true });
      });
      return true; // keep channel open for async response
    }

    case "getProcessingStatus":
      sendResponse({
        queueLength: urlQueue.length,
        isProcessing,
        retryCount,
      });
      break;

    case "clearQueue":
      urlQueue = [];
      stopProcessing();
      sendResponse({ success: true });
      break;

    case "getCategorizationProgress":
      handleGetProgress(sendResponse);
      return true;

    case "getCategorizedVideos":
      handleGetCategorizedVideos(sendResponse);
      return true;

    case "forceCategorization":
      handleForceCategorization(sendResponse);
      return true;

    default:
      sendResponse({ success: false, error: "Unknown action" });
  }

  return true;
});

/**
 * Handle incoming video URLs from content script
 * incomingUrls items can be:
 * - string URL
 * - { url: string, top: number, timestamp?: number }
 */
function handleVideoUrls(incomingUrls, timestamp = now()) {
  const normalized = incomingUrls.map((it) => {
    if (typeof it === "string") return { url: it, top: undefined, timestamp };
    return {
      url: it.url,
      top: typeof it.top === "number" ? it.top : undefined,
      timestamp: it.timestamp || timestamp,
    };
  });

  // Add URLs to queue with deduplication
  for (const item of normalized) {
    // Skip if exact URL already in queue
    const exists = urlQueue.some((q) => q.url === item.url);
    if (!exists) {
      urlQueue.push({
        id: nextQueueId++,
        url: item.url,
        top: item.top,
        timestamp: item.timestamp,
        retries: 0,
      });
    }
  }

  // Reorder so top-of-page items come first
  reorderQueue();

  // Notify clients of queue update (so UI can show immediate feedback)
  broadcastToClients({ action: "queueUpdated", queueLength: urlQueue.length }).catch?.(console.error);

  // Start processing if not already started
  if (!isProcessing) {
    processUrlQueue().catch(console.error);
  }
}

/**
 * Process the URL queue by sending batches to the server
 * Always takes highest-priority (front) items first.
 */
async function processUrlQueue() {
  if (isProcessing || urlQueue.length === 0) return;
  isProcessing = true;
  console.log(`[Service Worker] Starting processing. Queue length: ${urlQueue.length}`);

  try {
    while (urlQueue.length > 0) {
      // Always ensure the queue is sorted before slicing a batch
      reorderQueue();
      const batchItems = urlQueue.splice(0, CONFIG.BATCH_SIZE);

      console.log(`[Service Worker] Processing batch of ${batchItems.length} URLs`);

      try {
        // send batch and get per-URL results if server provides them
        const serverResult = await sendUrlsToServer(batchItems);

        // Expect serverResult to be an object with per-URL info; if not, mark all succeeded
        if (serverResult && typeof serverResult === "object" && Array.isArray(serverResult.results)) {
          // Server returns array of { url, success, metadata? , error? }
          for (const r of serverResult.results) {
            if (r && r.success) {
              // persist & notify client
              await saveCategorizedVideo(r.url, r.metadata || { serverRaw: r });
              broadcastToClients({ action: "urlProcessed", url: r.url, metadata: r.metadata || null }).catch?.(console.error);
            } else {
              // server indicated failure for this URL - retry if allowed
              handleFailedUrlInBatch(r.url, batchItems);
            }
          }
        } else {
          // Generic success - assume server handled all
          for (const item of batchItems) {
            await saveCategorizedVideo(item.url, { serverRaw: serverResult || null });
            broadcastToClients({ action: "urlProcessed", url: item.url, metadata: serverResult || null }).catch?.(console.error);
          }
        }

        retryCount = 0; // reset global retry counter on success

        // short delay before next batch to avoid overwhelming server
        if (urlQueue.length > 0) {
          await sleep(CONFIG.PROCESSING_DELAY);
        }
      } catch (batchError) {
        console.error("[Service Worker] Error processing batch:", batchError);

        // Increment retry for each URL in batch and requeue if under limit
        for (const item of batchItems) {
          item.retries = (item.retries || 0) + 1;
          if (item.retries < CONFIG.MAX_RETRIES) {
            urlQueue.push(item);
          } else {
            console.warn(`[Service Worker] Max retries exceeded for URL: ${item.url}`);
            broadcastToClients({ action: "urlFailed", url: item.url, error: "Max retries exceeded" }).catch?.(console.error);
          }
        }

        retryCount++;

        // Exponential backoff (bounded)
        const backoffDelay = Math.min(1000 * Math.pow(2, retryCount), 30000);
        await sleep(backoffDelay);
      }
    }
  } finally {
    isProcessing = false;
    console.log("[Service Worker] Finished processing URL queue");
    broadcastToClients({ action: "processingFinished", queueLength: urlQueue.length }).catch?.(console.error);
  }
}

function stopProcessing() {
  if (isProcessing) {
    console.log("[Service Worker] Stopping queue processing");
  }
  isProcessing = false;
}

// Requeue / handle failed single URL as reported by server
function handleFailedUrlInBatch(url, batchItems) {
  const item = batchItems.find((b) => b.url === url);
  if (!item) return;
  item.retries = (item.retries || 0) + 1;
  if (item.retries < CONFIG.MAX_RETRIES) {
    urlQueue.push(item);
    broadcastToClients({ action: "urlRequeued", url }).catch?.(console.error);
  } else {
    broadcastToClients({ action: "urlFailed", url, error: "Max retries exceeded" }).catch?.(console.error);
  }
}

// --- send batch payload to server ---
async function sendUrlsToServer(urlBatchItems) {
  // prepare payload, preserving order (highest priority first)
  const payload = {
    urls: urlBatchItems.map((item) => item.url),
    timestamp: now(),
    source: "extension_scraper",
  };

  console.log("[Service Worker] Sending URLs to server:", payload);

  try {
    const response = await fetch(`${CONFIG.SERVER_URL}/api/metadata/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

// --- helpers used by server-data endpoints ---
async function handleGetProgress(sendResponse) {
  try {
    const response = await fetch(`${CONFIG.SERVER_URL}/api/metadata/categorization-progress`);
    if (response.ok) {
      const data = await response.json();
      sendResponse({ success: true, data });
    } else {
      sendResponse({ success: false, error: `Server responded with status: ${response.status}` });
    }
  } catch (error) {
    console.error("[Service Worker] Error getting categorization progress:", error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleGetCategorizedVideos(sendResponse) {
  try {
    const response = await fetch(`${CONFIG.SERVER_URL}/api/metadata/categorized-videos`);
    if (response.ok) {
      const data = await response.json();
      sendResponse({ success: true, data });
    } else {
      sendResponse({ success: false, error: `Server responded with status: ${response.status}` });
    }
  } catch (error) {
    console.error("[Service Worker] Error getting categorized videos:", error);
    sendResponse({ success: false, error: error.message });
  }
}

async function handleForceCategorization(sendResponse) {
  try {
    // Start the background categorizer if not already running
    const startResponse = await fetch(`${CONFIG.SERVER_URL}/api/classifier/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    
    if (startResponse.ok) {
      console.log("[Service Worker] Forced categorization start successful");
      sendResponse({ success: true });
    } else {
      console.warn("[Service Worker] Failed to start categorization:", startResponse.status);
      sendResponse({ success: false, error: `Failed to start categorization: ${startResponse.status}` });
    }
  } catch (error) {
    console.error("[Service Worker] Error forcing categorization:", error);
    sendResponse({ success: false, error: error.message });
  }
}

// --- periodic cleanup of old queued items ---
setInterval(() => {
  const nowTs = now();
  const maxAge = 30 * 60 * 1000; // 30 minutes
  urlQueue = urlQueue.filter((item) => nowTs - item.timestamp < maxAge);
  if (urlQueue.length > 0 && !isProcessing) {
    processUrlQueue().catch(console.error);
  }
}, 5 * 60 * 1000);

// small sleep helper
function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
}
