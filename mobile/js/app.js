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
            loading: true,
            currentView: 'queue',
            showStats: false,
            imageZoomed: false,
            actionLoading: false,

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
        // Check authentication
        if (herbariumAPI.isAuthenticated()) {
            this.isAuthenticated = true;
            await this.initialize();
        } else {
            this.loading = false;
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
                await herbariumAPI.login(this.username, this.password);
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
                approve: 'Approve this specimen? This will mark it as reviewed and approved.',
                reject: 'Reject this specimen? This action can be reversed later.',
                flag: 'Flag this specimen for expert review?'
            };

            const shouldProceed = confirm(confirmationMessages[action]);
            if (!shouldProceed) {
                return; // User cancelled
            }

            try {
                this.actionLoading = true;
                const specimenId = this.currentSpecimen.id;

                if (action === 'approve') {
                    await herbariumAPI.approveSpecimen(specimenId);
                    this.showToast('Specimen approved', 'success');
                } else if (action === 'reject') {
                    await herbariumAPI.rejectSpecimen(specimenId, this.currentSpecimen.review.notes);
                    this.showToast('Specimen rejected', 'info');
                } else if (action === 'flag') {
                    await herbariumAPI.flagSpecimen(specimenId, this.currentSpecimen.review.notes);
                    this.showToast('Specimen flagged', 'warning');
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
                this.showToast('Notes saved', 'success');
            } catch (error) {
                this.showToast(`Error saving notes: ${error.message}`, 'error');
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
         * UI Helpers
         */
        getPriorityClass(priority) {
            return `priority-${priority.toLowerCase()}`;
        },

        getConfidenceClass(confidence) {
            if (confidence >= 0.8) return 'high';
            if (confidence >= 0.5) return 'medium';
            return 'low';
        },

        formatFieldName(fieldName) {
            // Convert camelCase to Title Case
            return fieldName
                .replace(/([A-Z])/g, ' $1')
                .replace(/^./, str => str.toUpperCase())
                .trim();
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
