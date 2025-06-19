/*
Service Worker for Locomotion Data Standardization Documentation
Created: 2025-06-19 with user permission
Purpose: Advanced caching strategy for optimal performance and offline capability

Features:
- Intelligent caching with cache-first strategy for static assets
- Network-first for documentation content
- Offline fallback pages
- Cache versioning and cleanup
- Performance monitoring
*/

const CACHE_NAME = 'locomotion-docs-v1.0.0';
const STATIC_CACHE = 'locomotion-static-v1.0.0';
const DYNAMIC_CACHE = 'locomotion-dynamic-v1.0.0';

// Assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/getting_started/',
  '/stylesheets/extra.css',
  '/javascripts/enhanced-interactivity.js',
  '/assets/images/favicon.png',
  '/offline.html' // Offline fallback page
];

// Cache strategies
const CACHE_STRATEGIES = {
  static: {
    pattern: /\.(css|js|png|jpg|jpeg|gif|svg|woff|woff2|eot|ttf|ico)$/,
    strategy: 'cacheFirst',
    maxAge: 365 * 24 * 60 * 60 * 1000, // 1 year
    maxEntries: 100
  },
  docs: {
    pattern: /\/(docs|getting_started|tutorials|reference|examples)\//,
    strategy: 'networkFirst',
    maxAge: 24 * 60 * 60 * 1000, // 1 day
    maxEntries: 200
  },
  api: {
    pattern: /\/api\//,
    strategy: 'networkFirst',
    maxAge: 60 * 60 * 1000, // 1 hour
    maxEntries: 50
  }
};

// Performance metrics
const performanceMetrics = {
  cacheHits: 0,
  cacheMisses: 0,
  networkRequests: 0,
  totalRequests: 0
};

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('Service Worker: Installation complete');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('Service Worker: Installation failed', err);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            // Delete old caches
            if (cacheName !== CACHE_NAME && 
                cacheName !== STATIC_CACHE && 
                cacheName !== DYNAMIC_CACHE) {
              console.log('Service Worker: Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('Service Worker: Activation complete');
        return self.clients.claim();
      })
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip external requests
  if (!url.origin.includes(self.location.origin) && 
      !url.origin.includes('locomotion-data-standardization')) {
    return;
  }
  
  performanceMetrics.totalRequests++;
  
  // Determine cache strategy
  const strategy = getCacheStrategy(request.url);
  
  event.respondWith(
    handleRequest(request, strategy)
      .catch(err => {
        console.error('Service Worker: Request failed', err);
        return getOfflineFallback(request);
      })
  );
});

// Determine appropriate cache strategy based on URL
function getCacheStrategy(url) {
  for (const [name, config] of Object.entries(CACHE_STRATEGIES)) {
    if (config.pattern.test(url)) {
      return { name, ...config };
    }
  }
  
  // Default strategy for documentation pages
  return {
    name: 'default',
    strategy: 'networkFirst',
    maxAge: 60 * 60 * 1000, // 1 hour
    maxEntries: 100
  };
}

// Handle request based on strategy
async function handleRequest(request, strategy) {
  const cacheName = strategy.name === 'static' ? STATIC_CACHE : DYNAMIC_CACHE;
  
  switch (strategy.strategy) {
    case 'cacheFirst':
      return cacheFirst(request, cacheName, strategy);
    
    case 'networkFirst':
      return networkFirst(request, cacheName, strategy);
    
    case 'staleWhileRevalidate':
      return staleWhileRevalidate(request, cacheName, strategy);
    
    default:
      return networkFirst(request, cacheName, strategy);
  }
}

// Cache-first strategy (for static assets)
async function cacheFirst(request, cacheName, strategy) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    performanceMetrics.cacheHits++;
    
    // Check if cache is still valid
    const cacheDate = new Date(cachedResponse.headers.get('date') || 0);
    const isExpired = Date.now() - cacheDate.getTime() > strategy.maxAge;
    
    if (!isExpired) {
      return cachedResponse;
    }
  }
  
  // Fetch from network and cache
  performanceMetrics.networkRequests++;
  performanceMetrics.cacheMisses++;
  
  const networkResponse = await fetch(request);
  
  if (networkResponse.ok) {
    await cacheResponse(cache, request, networkResponse.clone(), strategy);
  }
  
  return networkResponse;
}

// Network-first strategy (for documentation content)
async function networkFirst(request, cacheName, strategy) {
  const cache = await caches.open(cacheName);
  
  try {
    performanceMetrics.networkRequests++;
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      await cacheResponse(cache, request, networkResponse.clone(), strategy);
      return networkResponse;
    }
    
    throw new Error('Network response not ok');
    
  } catch (error) {
    // Fall back to cache
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      performanceMetrics.cacheHits++;
      return cachedResponse;
    }
    
    performanceMetrics.cacheMisses++;
    throw error;
  }
}

// Stale-while-revalidate strategy
async function staleWhileRevalidate(request, cacheName, strategy) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  // Start network request in background
  const networkResponsePromise = fetch(request)
    .then(response => {
      if (response.ok) {
        cacheResponse(cache, request, response.clone(), strategy);
      }
      return response;
    })
    .catch(() => null);
  
  // Return cached response immediately if available
  if (cachedResponse) {
    performanceMetrics.cacheHits++;
    return cachedResponse;
  }
  
  // Wait for network if no cache
  performanceMetrics.networkRequests++;
  performanceMetrics.cacheMisses++;
  return networkResponsePromise;
}

// Cache response with size and age management
async function cacheResponse(cache, request, response, strategy) {
  // Don't cache non-ok responses
  if (!response.ok) return;
  
  // Add cache metadata
  const responseWithMetadata = new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: {
      ...response.headers,
      'sw-cached': Date.now().toString(),
      'sw-strategy': strategy.name
    }
  });
  
  await cache.put(request, responseWithMetadata);
  
  // Clean up old entries if cache is too large
  await cleanupCache(cache, strategy.maxEntries);
}

// Clean up cache when it gets too large
async function cleanupCache(cache, maxEntries) {
  const keys = await cache.keys();
  
  if (keys.length > maxEntries) {
    // Remove oldest entries
    const sortedKeys = keys.sort((a, b) => {
      const aDate = a.headers?.get('sw-cached') || 0;
      const bDate = b.headers?.get('sw-cached') || 0;
      return aDate - bDate;
    });
    
    const keysToDelete = sortedKeys.slice(0, keys.length - maxEntries);
    await Promise.all(keysToDelete.map(key => cache.delete(key)));
  }
}

// Get offline fallback
async function getOfflineFallback(request) {
  const cache = await caches.open(STATIC_CACHE);
  
  // Return offline page for navigation requests
  if (request.mode === 'navigate') {
    const offlinePage = await cache.match('/offline.html');
    if (offlinePage) {
      return offlinePage;
    }
  }
  
  // Return cached version if available
  const cachedResponse = await cache.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // Return generic offline response
  return new Response(
    JSON.stringify({
      error: 'Offline',
      message: 'You are currently offline. Please check your connection.',
      timestamp: new Date().toISOString()
    }),
    {
      status: 503,
      statusText: 'Service Unavailable',
      headers: {
        'Content-Type': 'application/json'
      }
    }
  );
}

// Performance monitoring and reporting
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'GET_PERFORMANCE_METRICS') {
    event.ports[0].postMessage({
      type: 'PERFORMANCE_METRICS',
      data: {
        ...performanceMetrics,
        cacheHitRate: performanceMetrics.totalRequests > 0 
          ? (performanceMetrics.cacheHits / performanceMetrics.totalRequests * 100).toFixed(2)
          : 0
      }
    });
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    clearAllCaches().then(() => {
      event.ports[0].postMessage({
        type: 'CACHE_CLEARED',
        success: true
      });
    });
  }
});

// Clear all caches
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(cacheNames.map(name => caches.delete(name)));
  
  // Reset metrics
  performanceMetrics.cacheHits = 0;
  performanceMetrics.cacheMisses = 0;
  performanceMetrics.networkRequests = 0;
  performanceMetrics.totalRequests = 0;
}

// Background sync for analytics
self.addEventListener('sync', event => {
  if (event.tag === 'performance-sync') {
    event.waitUntil(syncPerformanceData());
  }
});

// Sync performance data when online
async function syncPerformanceData() {
  try {
    // Send performance metrics to analytics endpoint
    await fetch('/api/analytics/performance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        metrics: performanceMetrics,
        timestamp: Date.now(),
        userAgent: navigator.userAgent
      })
    });
  } catch (error) {
    console.log('Performance sync failed, will retry later');
  }
}

console.log('Service Worker: Loaded and ready');