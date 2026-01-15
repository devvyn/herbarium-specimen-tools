/**
 * Vue.js Mobile App for Herbarium Review
 */

const { createApp } = Vue;

createApp({
    data() {
        return {
            // Authentication
            isAuthenticated: false,
            username: '',
            password: '',
            loginError: '',

            // UI State
            loading: false,
            currentView: 'queue',
            showStats: false,
            imageZoomed: false,
            actionLoading: false,

            // OCR Overlay State
            showOcrRegions: false,
            hoverRegion: null,
            highlightedRegionIndex: null,
            imageWidth: 1000,
            imageHeight: 1000,
            imageLoaded: false,
            tooltipX: 0,
            tooltipY: 0,

            // Region Selection for Re-extraction
            regionSelectionMode: false,
            selectedRegionIndices: [],

            // Contextual Action Menu
            showRegionMenu: false,
            selectedRegion: null,
            regionMenuX: 0,
            regionMenuY: 0,

            // Data
            queue: [],
            currentSpecimen: null,
            stats: {},

            // Filters
            filters: {
                status: '',
                priority: '',
                limit: 50,
                offset: 0,
            },

            // Pagination
            hasMore: false,

            // Toast notifications
            toast: {
                show: false,
                message: '',
                type: 'info',
            },
            toastTimeout: null,

            // Network status
            isOnline: navigator.onLine,
        };
    },

    async mounted() {
        // Check for existing session or saved username
        const token = localStorage.getItem('auth_token');
        const savedUsername = localStorage.getItem('herbarium_username');

        if (token) {
            this.isAuthenticated = true;
            await this.initialize();
        } else if (savedUsername) {
            // Auto-login with saved username
            this.username = savedUsername;
            await this.login();
        }

        // Add keyboard shortcuts
        this.setupKeyboardShortcuts();

        // Add iOS touch handling
        this.setupTouchHandling();

        // Listen for online/offline events (accessibility)
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.showToast('Connection restored', 'success');
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showToast('Working offline', 'info');
        });
    },

    computed: {
        /**
         * Check if current specimen has OCR regions
         */
        hasOcrRegions() {
            return this.currentSpecimen?.ocr_regions?.length > 0;
        },

        /**
         * Tooltip positioning style
         */
        tooltipStyle() {
            return {
                left: this.tooltipX + 'px',
                top: this.tooltipY + 'px',
            };
        },

        /**
         * Check if any regions are selected for re-extraction
         */
        hasSelectedRegions() {
            return this.selectedRegionIndices.length > 0;
        },

        /**
         * Check if specimen has pending region re-extraction requests
         */
        hasPendingReextractionRegions() {
            return this.currentSpecimen?.review?.reextraction_regions?.length > 0;
        },

        /**
         * Get count of pending re-extraction regions
         */
        pendingReextractionCount() {
            return this.currentSpecimen?.review?.reextraction_regions?.length || 0;
        },

        /**
         * Suggest fields that might use the selected region's text
         * Based on the region's zone and low-confidence fields
         */
        suggestedFieldsForRegion() {
            if (!this.selectedRegion || !this.currentSpecimen?.fields) return {};

            const fields = this.currentSpecimen.fields;
            const zone = this.selectedRegion.zone;
            const text = this.selectedRegion.text.toLowerCase();

            // Get low confidence fields (< 0.8) or empty fields
            const suggestions = {};
            for (const [name, field] of Object.entries(fields)) {
                const confidence = field.confidence || 0;
                const isEmpty = !field.value && !field.corrected_value;

                // Suggest if low confidence, empty, or zone matches typical location
                if (confidence < 0.8 || isEmpty) {
                    suggestions[name] = field;
                }
            }

            // Limit to 5 most relevant suggestions
            return Object.fromEntries(Object.entries(suggestions).slice(0, 5));
        },
    },

    methods: {
        /**
         * Initialization
         */
        async initialize() {
            try {
                this.loading = true;
                await this.loadQueue();
                await this.loadStatistics();
            } catch (error) {
                this.showToast(`Error loading data: ${error.message}`, 'error');
            } finally {
                this.loading = false;
            }
        },

        /**
         * Authentication
         */
        async login() {
            try {
                this.loginError = '';
                await herbariumAPI.login(this.username);
                // Save username for auto-login next time
                localStorage.setItem('herbarium_username', this.username);
                this.isAuthenticated = true;
                await this.initialize();
            } catch (error) {
                this.loginError = error.message || 'Login failed';
            }
        },

        logout() {
            herbariumAPI.logout();
            this.isAuthenticated = false;
            this.currentView = 'queue';
        },

        /**
         * Queue Management
         */
        async loadQueue() {
            // Reset pagination when filters change (prevents empty results bug)
            this.filters.offset = 0;

            try {
                const data = await herbariumAPI.getQueue(this.filters);
                this.queue = data.specimens;
                this.hasMore = data.pagination.has_more;
            } catch (error) {
                this.showToast(`Error loading queue: ${error.message}`, 'error');
            }
        },

        async loadMore() {
            this.filters.offset += this.filters.limit;
            try {
                const data = await herbariumAPI.getQueue(this.filters);
                this.queue = [...this.queue, ...data.specimens];
                this.hasMore = data.pagination.has_more;
            } catch (error) {
                this.showToast(`Error loading more: ${error.message}`, 'error');
            }
        },

        async loadStatistics() {
            try {
                this.stats = await herbariumAPI.getStatistics();
            } catch (error) {
                console.error('Error loading statistics:', error);
            }
        },

        /**
         * Specimen Details
         */
        async openSpecimen(specimenId) {
            try {
                this.loading = true;
                const data = await herbariumAPI.getSpecimen(specimenId);
                this.currentSpecimen = data.specimen;

                // Initialize corrected_value for each field
                for (const [fieldName, fieldData] of Object.entries(this.currentSpecimen.fields)) {
                    if (!fieldData.corrected_value && fieldData.value) {
                        fieldData.corrected_value = fieldData.value;
                    }
                }

                this.currentView = 'specimen';
                this.imageZoomed = false;
                this.imageLoaded = false;  // Reset for new image

                // Reset OCR overlay state for new specimen
                this.showOcrRegions = false;
                this.highlightedRegionIndex = null;
                this.hoverRegion = null;
                this.regionSelectionMode = false;
                this.selectedRegionIndices = [];
            } catch (error) {
                this.showToast(`Error loading specimen: ${error.message}`, 'error');
            } finally {
                this.loading = false;
            }
        },

        /**
         * Quick Actions
         */
        async quickAction(action) {
            if (!this.currentSpecimen || this.actionLoading) return;

            // Confirmation dialogs for accessibility (WCAG 3.3.4 Error Prevention)
            const confirmationMessages = {
                approve: 'Approve for DwC export? Data will be included in final dataset.',
                reject: 'Reject specimen? Data will be excluded from export.',
                flag: 'Flag for expert review? Specimen will be marked for senior staff.',
                reextract: 'Request re-extraction? Image OK but extraction needs re-running.'
            };

            const shouldProceed = confirm(confirmationMessages[action]);
            if (!shouldProceed) {
                return; // User cancelled
            }

            try {
                this.actionLoading = true;
                const specimenId = this.currentSpecimen.id;
                const reviewNotes = this.currentSpecimen.review.review_notes || '';

                if (action === 'approve') {
                    await herbariumAPI.approveSpecimen(specimenId);
                    this.showToast('Approved for export', 'success');
                } else if (action === 'reject') {
                    await herbariumAPI.rejectSpecimen(specimenId, reviewNotes);
                    this.showToast('Rejected - excluded from export', 'info');
                } else if (action === 'flag') {
                    await herbariumAPI.flagSpecimen(specimenId, reviewNotes);
                    this.showToast('Flagged for expert review', 'warning');
                } else if (action === 'reextract') {
                    await herbariumAPI.requestReextraction(specimenId, reviewNotes);
                    this.showToast('Re-extraction requested', 'info');
                }

                // Refresh queue and go back
                await this.loadQueue();
                await this.loadStatistics();
                this.currentView = 'queue';
            } catch (error) {
                this.showToast(`Action failed: ${error.message}`, 'error');
            } finally {
                this.actionLoading = false;
            }
        },

        /**
         * Field Editing
         */
        async saveFieldCorrection(fieldName, fieldData) {
            if (!this.currentSpecimen || !fieldData.corrected_value) return;

            try {
                const acceptSuggestion = fieldData.corrected_value === fieldData.value;
                await herbariumAPI.updateField(
                    this.currentSpecimen.id,
                    fieldName,
                    fieldData.corrected_value,
                    acceptSuggestion
                );
                this.showToast(`${this.formatFieldName(fieldName)} updated`, 'success');
            } catch (error) {
                this.showToast(`Error saving field: ${error.message}`, 'error');
            }
        },

        async acceptSuggestion(fieldName, fieldData) {
            fieldData.corrected_value = fieldData.value;
            await this.saveFieldCorrection(fieldName, fieldData);
        },

        async updatePriority() {
            if (!this.currentSpecimen) return;

            try {
                await herbariumAPI.updateSpecimen(this.currentSpecimen.id, {
                    priority: this.currentSpecimen.review.priority,
                });
                this.showToast('Priority updated', 'success');
            } catch (error) {
                this.showToast(`Error updating priority: ${error.message}`, 'error');
            }
        },

        async saveNotes() {
            if (!this.currentSpecimen) return;

            try {
                await herbariumAPI.updateSpecimen(this.currentSpecimen.id, {
                    notes: this.currentSpecimen.review.notes,
                });
                this.showToast('DwC notes saved', 'success');
            } catch (error) {
                this.showToast(`Error saving notes: ${error.message}`, 'error');
            }
        },

        async saveReviewNotes() {
            if (!this.currentSpecimen) return;

            try {
                await herbariumAPI.updateSpecimen(this.currentSpecimen.id, {
                    review_notes: this.currentSpecimen.review.review_notes,
                });
                this.showToast('Review feedback saved', 'success');
            } catch (error) {
                this.showToast(`Error saving feedback: ${error.message}`, 'error');
            }
        },

        /**
         * Image Viewer
         */
        toggleImageZoom() {
            this.imageZoomed = !this.imageZoomed;
        },

        getImageUrl(specimenId) {
            return herbariumAPI.getImageUrl(specimenId);
        },

        /**
         * OCR Overlay
         */
        toggleOcrOverlay() {
            this.showOcrRegions = !this.showOcrRegions;
            this.highlightedRegionIndex = null;
            this.hoverRegion = null;

            // Set viewBox after SVG renders
            if (this.showOcrRegions) {
                this.$nextTick(() => {
                    this.updateSvgViewBox();
                });
            }
        },

        onImageLoad(event) {
            // Capture actual rendered image dimensions for SVG viewBox
            const img = event.target;
            this.imageWidth = img.naturalWidth || img.width || 1000;
            this.imageHeight = img.naturalHeight || img.height || 1000;
            this.imageLoaded = true;

            // Set viewBox on next tick after SVG renders
            // (Vue lowercases :viewBox to viewbox, breaking SVG coordinate transform)
            this.$nextTick(() => {
                this.updateSvgViewBox();
            });
        },

        updateSvgViewBox() {
            // Manually set viewBox with correct camelCase
            // Required because Vue's template compiler lowercases SVG attributes
            const svg = this.$refs.ocrOverlay;
            if (svg) {
                svg.setAttribute('viewBox', `0 0 ${this.imageWidth} ${this.imageHeight}`);
            }
        },

        showRegionTooltip(region, event) {
            // Position menu near click point
            const container = this.$refs.imageContainer;
            if (container) {
                const rect = container.getBoundingClientRect();
                this.regionMenuX = event.clientX - rect.left;
                this.regionMenuY = event.clientY - rect.top;
            }

            // Find and highlight this region
            const index = this.currentSpecimen.ocr_regions.indexOf(region);
            this.highlightedRegionIndex = index;
            this.selectedRegion = region;
            this.showRegionMenu = true;
        },

        closeRegionMenu() {
            this.showRegionMenu = false;
            this.selectedRegion = null;
            this.highlightedRegionIndex = null;
        },

        async copyRegionText() {
            if (!this.selectedRegion) return;
            try {
                await navigator.clipboard.writeText(this.selectedRegion.text);
                this.showToast('Copied to clipboard', 'success');
            } catch (e) {
                // Fallback for older browsers
                this.showToast(`OCR: "${this.selectedRegion.text}"`, 'info');
            }
            this.closeRegionMenu();
        },

        useRegionAsFieldValue(fieldName) {
            if (!this.selectedRegion || !this.currentSpecimen?.fields?.[fieldName]) return;

            const field = this.currentSpecimen.fields[fieldName];
            field.corrected_value = this.selectedRegion.text;
            field.reviewed = true;

            this.showToast(`Set ${fieldName} to "${this.selectedRegion.text}"`, 'success');
            this.closeRegionMenu();
        },

        markRegionForReextraction() {
            if (!this.selectedRegion) return;

            const index = this.currentSpecimen.ocr_regions.indexOf(this.selectedRegion);
            if (index !== -1 && !this.selectedRegionIndices.includes(index)) {
                this.selectedRegionIndices.push(index);
                this.showToast('Region marked for re-extraction', 'info');
            }
            this.closeRegionMenu();
        },

        highlightMatchingRegions(fieldValue) {
            if (!this.showOcrRegions || !this.hasOcrRegions || !fieldValue) return;

            // Find regions whose text matches or contains the field value
            const searchValue = fieldValue.toLowerCase().trim();
            const regions = this.currentSpecimen.ocr_regions;

            // Try exact match first, then partial match
            let matchIndex = regions.findIndex(r =>
                r.text.toLowerCase().trim() === searchValue
            );

            if (matchIndex === -1) {
                // Try partial match
                matchIndex = regions.findIndex(r =>
                    r.text.toLowerCase().includes(searchValue) ||
                    searchValue.includes(r.text.toLowerCase())
                );
            }

            if (matchIndex !== -1) {
                this.highlightedRegionIndex = matchIndex;
                this.showToast(`Found: "${regions[matchIndex].text}"`, 'info');

                // Scroll to image if needed
                const imageContainer = this.$refs.imageContainer;
                if (imageContainer) {
                    imageContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }

                // Clear highlight after animation
                setTimeout(() => {
                    this.highlightedRegionIndex = null;
                }, 2500);
            } else {
                this.showToast('No matching OCR region found', 'warning');
            }
        },

        /**
         * Region Selection for Re-extraction
         */
        toggleRegionSelectionMode() {
            this.regionSelectionMode = !this.regionSelectionMode;
            if (!this.regionSelectionMode) {
                // Clear selection when exiting selection mode
                this.selectedRegionIndices = [];
            } else {
                // Ensure OCR overlay is visible in selection mode
                this.showOcrRegions = true;
            }
        },

        toggleRegionSelection(index) {
            if (!this.regionSelectionMode) return;

            const idx = this.selectedRegionIndices.indexOf(index);
            if (idx === -1) {
                // Add to selection
                this.selectedRegionIndices.push(index);
            } else {
                // Remove from selection
                this.selectedRegionIndices.splice(idx, 1);
            }
        },

        isRegionSelected(index) {
            return this.selectedRegionIndices.includes(index);
        },

        isRegionPendingReextraction(index) {
            const pending = this.currentSpecimen?.review?.reextraction_regions || [];
            return pending.some(r => r.region_index === index);
        },

        async submitRegionReextraction() {
            if (!this.hasSelectedRegions || this.actionLoading) return;

            const notes = prompt('Optional notes about what needs re-extraction:');

            try {
                this.actionLoading = true;
                const result = await herbariumAPI.requestRegionReextraction(
                    this.currentSpecimen.id,
                    this.selectedRegionIndices,
                    notes
                );

                this.showToast(
                    `${result.regions_queued} region(s) queued for re-extraction`,
                    'success'
                );

                // Update local state
                if (!this.currentSpecimen.review.reextraction_regions) {
                    this.currentSpecimen.review.reextraction_regions = [];
                }

                // Refresh specimen to get updated state
                const data = await herbariumAPI.getSpecimen(this.currentSpecimen.id);
                this.currentSpecimen = data.specimen;

                // Exit selection mode
                this.regionSelectionMode = false;
                this.selectedRegionIndices = [];

            } catch (error) {
                this.showToast(`Error: ${error.message}`, 'error');
            } finally {
                this.actionLoading = false;
            }
        },

        async clearPendingReextractions() {
            if (!this.hasPendingReextractionRegions || this.actionLoading) return;

            if (!confirm('Clear all pending region re-extraction requests?')) return;

            try {
                this.actionLoading = true;
                await herbariumAPI.clearReextractionRegions(this.currentSpecimen.id);

                this.showToast('Pending re-extractions cleared', 'info');

                // Refresh specimen
                const data = await herbariumAPI.getSpecimen(this.currentSpecimen.id);
                this.currentSpecimen = data.specimen;

            } catch (error) {
                this.showToast(`Error: ${error.message}`, 'error');
            } finally {
                this.actionLoading = false;
            }
        },

        /**
         * UI Helpers
         */
        getPriorityClass(priority) {
            return `priority-${priority.toLowerCase()}`;
        },

        getConfidenceClass(confidence) {
            if (confidence >= 0.8) return 'high';
            if (confidence >= 0.7) return 'medium';  // Aligned with low-confidence highlight threshold
            return 'low';
        },

        formatFieldName(fieldName) {
            // Convert camelCase to Title Case
            return fieldName
                .replace(/([A-Z])/g, ' $1')
                .replace(/^./, str => str.toUpperCase())
                .trim();
        },

        formatModelName(model) {
            if (!model) return 'Unknown';
            // Extract the model name from full path (e.g., "qwen/qwen-2.5-vl-72b-instruct:free" → "qwen-2.5-vl-72b")
            const parts = model.split('/');
            const name = parts[parts.length - 1];
            // Remove :free or :paid suffix
            return name.replace(/:(free|paid)$/, '').replace('-instruct', '');
        },

        formatDate(timestamp) {
            if (!timestamp) return 'Unknown';
            try {
                const date = new Date(timestamp);
                return date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                });
            } catch {
                return timestamp;
            }
        },

        showToast(message, type = 'info') {
            this.toast = {
                show: true,
                message,
                type,
            };

            // Clear existing timeout
            if (this.toastTimeout) {
                clearTimeout(this.toastTimeout);
            }

            // Extended timeout for accessibility (WCAG 2.2.1)
            this.toastTimeout = setTimeout(() => {
                this.dismissToast();
            }, 10000); // 3s → 10s for users with cognitive disabilities
        },

        dismissToast() {
            this.toast.show = false;
            if (this.toastTimeout) {
                clearTimeout(this.toastTimeout);
                this.toastTimeout = null;
            }
        },

        /**
         * Keyboard Shortcuts
         */
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Only in specimen view
                if (this.currentView !== 'specimen' || !this.currentSpecimen) return;

                // Prevent shortcuts when typing in inputs
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

                if (e.key === 'a') {
                    e.preventDefault();
                    this.quickAction('approve');
                } else if (e.key === 'r') {
                    e.preventDefault();
                    this.quickAction('reject');
                } else if (e.key === 'f') {
                    e.preventDefault();
                    this.quickAction('flag');
                }
            });
        },

        /**
         * Touch Handling for iOS
         */
        setupTouchHandling() {
            // Prevent pull-to-refresh on iOS
            let lastTouchY = 0;
            let preventPullToRefresh = false;

            document.addEventListener('touchstart', (e) => {
                if (e.touches.length !== 1) return;
                lastTouchY = e.touches[0].clientY;
                preventPullToRefresh = window.pageYOffset === 0;
            }, { passive: false });

            document.addEventListener('touchmove', (e) => {
                const touchY = e.touches[0].clientY;
                const touchYDelta = touchY - lastTouchY;
                lastTouchY = touchY;

                if (preventPullToRefresh && touchYDelta > 0) {
                    e.preventDefault();
                }
            }, { passive: false });
        },
    },
}).mount('#app');
