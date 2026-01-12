/**
 * Error tracking and telemetry for Herbarium Review App
 * Captures errors with specimen context and OCR overlay state
 *
 * Cross-pollinated from simulacrum-stories project
 * Enhanced with Vue.js context and OCR metrics
 */

(function() {
  'use strict';

  const PROJECT_ID = 'herbarium-review';
  const MAX_STORED = 100;
  const STORAGE_KEY = 'herbarium-error-queue';
  const TELEMETRY_KEY = 'herbarium-telemetry';

  // Get current specimen context from Vue app
  function getSpecimenContext() {
    try {
      const app = document.querySelector('#app')?.__vue_app__;
      if (!app) return null;

      const state = app._instance?.proxy;
      if (!state) return null;

      return {
        specimenId: state.currentSpecimen?.id || null,
        currentView: state.currentView,
        showOcrRegions: state.showOcrRegions,
        regionSelectionMode: state.regionSelectionMode,
        selectedRegionCount: state.selectedRegionIndices?.length || 0,
        imageLoaded: state.imageLoaded,
        queuePosition: state.queue?.findIndex(s => s.id === state.currentSpecimen?.id) ?? -1,
        queueLength: state.queue?.length || 0
      };
    } catch (e) {
      return { error: 'Failed to extract Vue state' };
    }
  }

  // Get OCR overlay metrics
  function getOcrMetrics() {
    try {
      const overlay = document.querySelector('.ocr-overlay');
      const image = document.querySelector('.specimen-image');
      const regions = document.querySelectorAll('.ocr-region');

      if (!overlay || !image) return null;

      const overlayRect = overlay.getBoundingClientRect();
      const imageRect = image.getBoundingClientRect();

      return {
        regionCount: regions.length,
        overlayVisible: overlay.offsetParent !== null,
        alignment: {
          xOffset: Math.abs(overlayRect.x - imageRect.x),
          yOffset: Math.abs(overlayRect.y - imageRect.y),
          widthDiff: Math.abs(overlayRect.width - imageRect.width),
          heightDiff: Math.abs(overlayRect.height - imageRect.height)
        }
      };
    } catch (e) {
      return null;
    }
  }

  // Queue error for later reporting
  function queueError(error) {
    try {
      const queue = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      queue.push({
        ...error,
        project: PROJECT_ID,
        timestamp: new Date().toISOString(),
        specimen: getSpecimenContext(),
        ocr: getOcrMetrics()
      });

      // Keep queue bounded
      while (queue.length > MAX_STORED) queue.shift();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    } catch (e) {
      // localStorage not available, skip
    }
  }

  // Log telemetry event (non-error)
  function logTelemetry(eventType, data) {
    try {
      const telemetry = JSON.parse(localStorage.getItem(TELEMETRY_KEY) || '[]');
      telemetry.push({
        eventType,
        data,
        project: PROJECT_ID,
        timestamp: new Date().toISOString(),
        specimen: getSpecimenContext()
      });

      // Keep bounded
      while (telemetry.length > MAX_STORED * 2) telemetry.shift();
      localStorage.setItem(TELEMETRY_KEY, JSON.stringify(telemetry));
    } catch (e) {
      // Skip if localStorage unavailable
    }
  }

  // Report error (queue locally)
  function reportError(error) {
    const payload = {
      message: error.message || String(error),
      stack: error.stack || null,
      type: error.type || 'error',
      url: window.location.href,
      userAgent: navigator.userAgent
    };

    // Queue locally
    queueError(payload);

    // Log to console in dev
    if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') {
      console.error('[ErrorTracker]', payload.message, payload);
    }
  }

  // Capture unhandled errors
  window.addEventListener('error', (event) => {
    // Skip browser extension errors
    if (event.filename && event.filename.includes('extension')) return;

    reportError({
      message: event.message,
      stack: event.error ? event.error.stack : `${event.filename}:${event.lineno}:${event.colno}`,
      type: 'uncaught'
    });
  });

  // Capture unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    reportError({
      message: event.reason ? (event.reason.message || String(event.reason)) : 'Unhandled rejection',
      stack: event.reason ? event.reason.stack : null,
      type: 'promise'
    });
  });

  // Track OCR overlay interactions
  function trackOcrInteraction(action, details) {
    logTelemetry('ocr_interaction', {
      action,
      ...details,
      ocr: getOcrMetrics()
    });
  }

  // Expose API globally
  window.herbariumTracker = {
    // Manual error reporting
    reportError: function(message, extra) {
      reportError({
        message: message,
        type: 'manual',
        extra: extra
      });
    },

    // Telemetry logging
    log: logTelemetry,

    // OCR interaction tracking
    trackOcr: trackOcrInteraction,

    // Get current context (for debugging)
    getContext: function() {
      return {
        specimen: getSpecimenContext(),
        ocr: getOcrMetrics()
      };
    },

    // Export error queue (for diagnostic script)
    exportErrors: function() {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    },

    // Export telemetry (for diagnostic script)
    exportTelemetry: function() {
      return JSON.parse(localStorage.getItem(TELEMETRY_KEY) || '[]');
    },

    // Clear stored data
    clear: function() {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(TELEMETRY_KEY);
      console.log('[ErrorTracker] Cleared stored data');
    },

    // Get summary stats
    stats: function() {
      const errors = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      const telemetry = JSON.parse(localStorage.getItem(TELEMETRY_KEY) || '[]');
      return {
        errorCount: errors.length,
        telemetryCount: telemetry.length,
        oldestError: errors[0]?.timestamp || null,
        newestError: errors[errors.length - 1]?.timestamp || null,
        errorTypes: errors.reduce((acc, e) => {
          acc[e.type] = (acc[e.type] || 0) + 1;
          return acc;
        }, {})
      };
    }
  };

  // Also expose legacy API for compatibility
  window.reportError = window.herbariumTracker.reportError;

  console.log('[ErrorTracker] Initialized for', PROJECT_ID);
})();
