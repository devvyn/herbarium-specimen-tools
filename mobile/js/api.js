/**
 * API Client for Herbarium Mobile Review
 *
 * Handles authentication, API calls, and local storage.
 */

const API_BASE_URL = window.location.origin + '/api/v1';

class HerbariumAPI {
    constructor() {
        this.token = localStorage.getItem('auth_token');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
    }

    /**
     * Set authorization headers
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    /**
     * Make API request
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers = this.getHeaders();

        const response = await fetch(url, {
            ...options,
            headers: {
                ...headers,
                ...options.headers,
            },
        });

        if (!response.ok) {
            if (response.status === 401) {
                // Token expired, clear auth
                this.logout();
                throw new Error('Your session has expired. Please log in again.');
            }

            const error = await response.json().catch(() => ({}));
            let errorMessage = error.detail;

            // Provide human-readable error messages (accessibility)
            if (!errorMessage) {
                switch (response.status) {
                    case 404:
                        errorMessage = 'The requested specimen was not found.';
                        break;
                    case 403:
                        errorMessage = 'You do not have permission to perform this action.';
                        break;
                    case 429:
                        errorMessage = 'Too many requests. Please try again in a few minutes.';
                        break;
                    case 500:
                        errorMessage = 'A server error occurred. Please try again later.';
                        break;
                    case 503:
                        errorMessage = 'The service is temporarily unavailable. Please try again later.';
                        break;
                    default:
                        errorMessage = `An error occurred (Error ${response.status}). Please try again.`;
                }
            }

            throw new Error(errorMessage);
        }

        return response.json();
    }

    /**
     * Authentication
     */
    async login(username) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username }),
        });

        this.token = data.access_token;
        this.user = data.user;

        localStorage.setItem('auth_token', this.token);
        localStorage.setItem('user', JSON.stringify(this.user));

        return data;
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
    }

    isAuthenticated() {
        return !!this.token;
    }

    getCurrentUser() {
        return this.user;
    }

    /**
     * Review Queue
     */
    async getQueue(filters = {}) {
        const params = new URLSearchParams();

        if (filters.status) params.append('status', filters.status);
        if (filters.priority) params.append('priority', filters.priority);
        if (filters.flagged_only) params.append('flagged_only', 'true');
        if (filters.limit) params.append('limit', filters.limit);
        if (filters.offset) params.append('offset', filters.offset);

        return this.request(`/queue?${params.toString()}`);
    }

    /**
     * Specimen Details
     */
    async getSpecimen(specimenId) {
        return this.request(`/specimen/${specimenId}`);
    }

    /**
     * Update Specimen
     */
    async updateSpecimen(specimenId, updates) {
        return this.request(`/specimen/${specimenId}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
        });
    }

    /**
     * Update Single Field
     */
    async updateField(specimenId, fieldName, value, acceptSuggestion = true) {
        return this.request(`/specimen/${specimenId}/field/${fieldName}`, {
            method: 'POST',
            body: JSON.stringify({
                field: fieldName,
                value: value,
                accept_suggestion: acceptSuggestion,
            }),
        });
    }

    /**
     * Quick Actions
     */
    async approveSpecimen(specimenId) {
        return this.request(`/specimen/${specimenId}/approve`, {
            method: 'POST',
        });
    }

    async rejectSpecimen(specimenId, notes = null) {
        return this.request(`/specimen/${specimenId}/reject?notes=${encodeURIComponent(notes || '')}`, {
            method: 'POST',
        });
    }

    async flagSpecimen(specimenId, notes = null) {
        return this.request(`/specimen/${specimenId}/flag?notes=${encodeURIComponent(notes || '')}`, {
            method: 'POST',
        });
    }

    async requestReextraction(specimenId, notes = null) {
        return this.request(`/specimen/${specimenId}/request-reextraction?notes=${encodeURIComponent(notes || '')}`, {
            method: 'POST',
        });
    }

    /**
     * Request re-extraction for specific OCR regions
     */
    async requestRegionReextraction(specimenId, regionIndices, notes = null) {
        return this.request(`/specimen/${specimenId}/request-region-reextraction`, {
            method: 'POST',
            body: JSON.stringify({
                region_indices: regionIndices,
                notes: notes || '',
            }),
        });
    }

    /**
     * Clear all pending region re-extraction requests
     */
    async clearReextractionRegions(specimenId) {
        return this.request(`/specimen/${specimenId}/reextraction-regions`, {
            method: 'DELETE',
        });
    }

    /**
     * Statistics
     */
    async getStatistics() {
        return this.request('/statistics');
    }

    /**
     * Image URLs
     */
    getImageUrl(specimenId) {
        return `${API_BASE_URL}/images/${specimenId}`;
    }

    getThumbnailUrl(specimenId) {
        return `${API_BASE_URL}/images/${specimenId}/thumb`;
    }

    /**
     * Offline Sync
     */
    async downloadBatch(filters = {}) {
        return this.request('/sync/download', {
            method: 'POST',
            body: JSON.stringify({
                status: filters.status || 'PENDING',
                priority: filters.priority,
                limit: filters.limit || 50,
            }),
        });
    }

    async uploadBatch(updates) {
        return this.request('/sync/upload', {
            method: 'POST',
            body: JSON.stringify(updates),
        });
    }
}

// Export singleton instance
window.herbariumAPI = new HerbariumAPI();
