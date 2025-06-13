/**
 * JAGAPADI v2.0 - AI Deteksi Hama Padi (Flask Version)
 * Modified for Raspberry Pi + Flask backend
 */

class JagaPadiApp {
    constructor() {
        console.log('🌾 JAGAPADI v2.0 - Flask Edition for Raspberry Pi');
        
        // Application states
        this.currentState = 'initial';
        this.isConnected = false;
        this.currentFile = null;
        this.selectedBase64 = null;
        this.processingStartTime = 0;
        this.currentResults = null;
        
        // UI state
        this.sidebarOpen = false;
        this.isDarkMode = this.loadTheme();
        this.history = [];
        this.todayStats = { detections: 0, accuracy: 0 };
        
        // DOM Elements
        this.elements = this.initializeElements();
        
        // Initialize app
        this.initializeEventListeners();
        this.initializeTouchFeedback();
        this.applyTheme();
        this.loadPersistedData();
        this.updateStatusBar();
        this.setState('initial');
        this.checkConnectionStatus(); // Check initial connection
        
        console.log('✅ JAGAPADI v2.0 Flask Edition initialized');
    }

    initializeElements() {
        return {
            // Header & Navigation
            toggleSidebar: document.getElementById('toggleSidebar'),
            darkModeBtn: document.getElementById('darkModeBtn'),
            sidebar: document.getElementById('sidebar'),
            sidebarOverlay: document.getElementById('sidebarOverlay'),
            
            // Connection elements
            connectBtn: document.getElementById('btn-connect'),
            statusIndicator: document.getElementById('statusIndicator'),
            statusText: document.getElementById('statusText'),
            mainConnectionStatus: document.getElementById('mainConnectionStatus'),
            mainStatusDot: document.getElementById('mainStatusDot'),
            mainStatusText: document.getElementById('mainStatusText'),
            
            // Preview area
            previewContainer: document.getElementById('previewContainer'),
            emptyState: document.getElementById('emptyState'),
            previewContent: document.getElementById('previewContent'),
            previewImage: document.getElementById('previewImage'),
            fileInput: document.getElementById('fileInput'),
            
            // Processing overlay
            processingOverlay: document.getElementById('processingOverlay'),
            processingText: document.getElementById('processingText'),
            progressBar: document.getElementById('progressBar'),
            
            // Results overlay
            resultsOverlay: document.getElementById('resultsOverlay'),
            resultsCount: document.getElementById('resultsCount'),
            
            // Action buttons (state-based)
            actionSection: document.getElementById('actionSection'),
            initialActions: document.getElementById('initialActions'),
            imageReadyActions: document.getElementById('imageReadyActions'),
            processingActions: document.getElementById('processingActions'),
            resultsActions: document.getElementById('resultsActions'),
            
            // Individual buttons
            cameraBtn: document.getElementById('cameraBtn'),
            fileBtn: document.getElementById('fileBtn'),
            changeImageBtn: document.getElementById('changeImageBtn'),
            detectBtn: document.getElementById('detectBtn'),
            newDetectionBtn: document.getElementById('newDetectionBtn'),
            viewDetailsBtn: document.getElementById('viewDetailsBtn'),
            
            // Results panel
            resultsPanel: document.getElementById('resultsPanel'),
            detectionCount: document.getElementById('detectionCount'),
            confidenceLevel: document.getElementById('confidenceLevel'),
            processingTimeResult: document.getElementById('processingTimeResult'),
            detectionDetails: document.getElementById('detectionDetails'),
            recommendationsList: document.getElementById('recommendationsList'),
            
            // Statistics
            todayDetections: document.getElementById('todayDetections'),
            todayAccuracy: document.getElementById('todayAccuracy'),
            
            // History
            historyList: document.getElementById('historyList'),
            historyModal: document.getElementById('historyModal'),
            historyModalBody: document.getElementById('historyModalBody'),
            closeHistoryModal: document.getElementById('closeHistoryModal'),
            
            // Auth modal
            authModal: document.getElementById('authModal'),
            passwordInput: document.getElementById('passwordInput'),
            confirmAuthBtn: document.getElementById('confirmAuthBtn'),
            cancelAuthBtn: document.getElementById('cancelAuthBtn'),
            
            // Notification & Status
            notification: document.getElementById('notification'),
            statusBar: document.getElementById('statusBar'),
            globalStatus: document.getElementById('globalStatus'),
            statusTime: document.getElementById('statusTime')
        };
    }

    initializeEventListeners() {
        const { elements } = this;

        // === NAVIGATION EVENTS ===
        elements.toggleSidebar?.addEventListener('click', () => this.toggleSidebar());
        elements.darkModeBtn?.addEventListener('click', () => this.toggleDarkMode());
        elements.sidebarOverlay?.addEventListener('click', () => this.closeSidebar());

        // === CONNECTION EVENTS ===
        elements.connectBtn?.addEventListener('click', () => {
            if (this.isConnected) {
                this.disconnect();
            } else {
                this.showAuthModal();
            }
        });

        // === CAMERA & FILE EVENTS ===
        elements.cameraBtn?.addEventListener('click', () => this.handleCameraAction());
        elements.fileBtn?.addEventListener('click', () => this.handleFileAction());
        elements.changeImageBtn?.addEventListener('click', () => this.handleChangeImage());
        elements.fileInput?.addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));

        // === DETECTION EVENTS ===
        elements.detectBtn?.addEventListener('click', () => this.startDetection());
        elements.newDetectionBtn?.addEventListener('click', () => this.startNewDetection());
        elements.viewDetailsBtn?.addEventListener('click', () => this.showResultsDetail());

        // === AUTH MODAL EVENTS ===
        elements.confirmAuthBtn?.addEventListener('click', () => this.connect());
        elements.cancelAuthBtn?.addEventListener('click', () => this.hideAuthModal());
        elements.passwordInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.connect();
        });

        // === HISTORY MODAL EVENTS ===
        elements.closeHistoryModal?.addEventListener('click', () => this.hideHistoryModal());
        
        // Close modals on background click
        elements.authModal?.addEventListener('click', (e) => {
            if (e.target === elements.authModal) this.hideAuthModal();
        });
        elements.historyModal?.addEventListener('click', (e) => {
            if (e.target === elements.historyModal) this.hideHistoryModal();
        });

        // === KEYBOARD SHORTCUTS ===
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        
        // === WINDOW EVENTS ===
        window.addEventListener('resize', () => this.handleResize());
        window.addEventListener('beforeunload', () => this.cleanup());
    }

    // === FLASK API METHODS ===
    async checkConnectionStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.connected && data.authenticated) {
                this.isConnected = true;
                this.setConnectionState('connected');
            } else {
                this.isConnected = false;
                this.setConnectionState('disconnected');
            }
            
            this.updateButtonStates();
        } catch (error) {
            console.log('Connection check failed, assuming disconnected');
            this.isConnected = false;
            this.setConnectionState('disconnected');
            this.updateButtonStates();
        }
    }

    async connect() {
        const password = this.elements.passwordInput?.value;
        
        if (!password) {
            this.showNotification('Masukkan password!', 'error');
            return;
        }

        try {
            this.setConnectionState('connecting');
            
            const response = await fetch('/api/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ password })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.isConnected = true;
                this.setConnectionState('connected');
                this.updateButtonStates();
                this.hideAuthModal();
                this.showNotification(result.message, 'success');
            } else {
                this.setConnectionState('disconnected');
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Connection error:', error);
            this.setConnectionState('disconnected');
            this.showNotification('Gagal terhubung ke server', 'error');
        }
    }

    async disconnect() {
        try {
            const response = await fetch('/api/disconnect', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            this.isConnected = false;
            this.setConnectionState('disconnected');
            this.updateButtonStates();
            
            // Reset to initial state if not processing
            if (this.currentState !== 'processing') {
                this.setState('initial');
            }
            
            this.showNotification(result.message || 'Terputus dari server', 'info');
        } catch (error) {
            console.error('Disconnect error:', error);
            this.isConnected = false;
            this.setConnectionState('disconnected');
            this.updateButtonStates();
            this.showNotification('Terputus dari server', 'info');
        }
    }

    async startDetection() {
        if (!this.currentFile) {
            this.showNotification('Tidak ada gambar untuk dianalisis', 'error');
            return;
        }

        if (!this.isConnected) {
            this.showNotification('Hubungkan ke server terlebih dahulu', 'error');
            return;
        }

        this.processingStartTime = Date.now();
        this.setState('processing');

        try {
            // Create FormData untuk upload file
            const formData = new FormData();
            formData.append('file', this.currentFile);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            const processingTime = ((Date.now() - this.processingStartTime) / 1000).toFixed(1);
            
            if (result.success) {
                // Display result image if provided
                if (result.result_image && this.elements.previewImage) {
                    this.elements.previewImage.src = result.result_image;
                }
                
                // Generate demo results (in production, this would come from server)
                const demoResults = this.generateDemoResults();
                this.currentResults = demoResults;
                
                this.displayResults(demoResults, processingTime);
                
                // Add to history
                this.addToHistory({
                    filename: this.currentFile.name,
                    timestamp: new Date(),
                    results: demoResults,
                    processingTime: processingTime,
                    resultImage: result.result_image || this.selectedBase64
                });
                
                this.setState('results');
                this.showNotification('Deteksi berhasil!', 'success');
            } else {
                this.showNotification(result.message, 'error');
                this.setState('imageReady');
            }
        } catch (error) {
            console.error('Detection error:', error);
            this.showNotification('Gagal menganalisis gambar', 'error');
            this.setState('imageReady');
        }
    }

    async loadHistory() {
        try {
            const response = await fetch('/api/history');
            const historyData = await response.json();
            
            // Convert timestamp strings back to Date objects
            return historyData.map(item => ({
                ...item,
                timestamp: new Date(item.timestamp || item.waktu) // Handle both formats
            }));
        } catch (error) {
            console.log('Failed to load history from server, using local storage');
            return this.loadHistoryFromStorage();
        }
    }

    loadHistoryFromStorage() {
        try {
            const saved = localStorage.getItem('jagapadi-history');
            const history = saved ? JSON.parse(saved) : [];
            
            return history.map(item => ({
                ...item,
                timestamp: new Date(item.timestamp)
            }));
        } catch (error) {
            console.log('LocalStorage not available, using empty history');
            return [];
        }
    }

    // === STATE MANAGEMENT (same as original) ===
    setState(newState) {
        console.log(`🔄 State change: ${this.currentState} → ${newState}`);
        
        const previousState = this.currentState;
        this.currentState = newState;
        
        this.hideAllActionGroups();
        
        switch (newState) {
            case 'initial':
                this.showInitialState();
                break;
            case 'imageReady':
                this.showImageReadyState();
                break;
            case 'processing':
                this.showProcessingState();
                break;
            case 'results':
                this.showResultsState();
                break;
            default:
                console.warn('Unknown state:', newState);
        }
        
        this.updateGlobalStatus();
        
        if (previousState !== newState) {
            this.animateStateTransition(previousState, newState);
        }
    }

    hideAllActionGroups() {
        const { elements } = this;
        elements.initialActions?.classList.add('hidden');
        elements.imageReadyActions?.classList.add('hidden');
        elements.processingActions?.classList.add('hidden');
        elements.resultsActions?.classList.add('hidden');
    }

    showInitialState() {
        const { elements } = this;
        
        elements.emptyState?.classList.remove('hidden');
        elements.previewContent?.classList.remove('show');
        elements.previewContent?.classList.add('hidden');
        elements.resultsPanel?.classList.add('hidden');
        
        elements.initialActions?.classList.remove('hidden');
        
        this.updateButtonStates();
        this.updateGlobalStatus('Siap untuk deteksi');
    }

    showImageReadyState() {
        const { elements } = this;
        
        elements.emptyState?.classList.add('hidden');
        elements.previewContent?.classList.remove('hidden');
        elements.previewContent?.classList.add('show');
        elements.resultsPanel?.classList.add('hidden');
        
        elements.processingOverlay?.classList.remove('show');
        elements.resultsOverlay?.classList.remove('show');
        
        elements.imageReadyActions?.classList.remove('hidden');
        
        this.updateGlobalStatus('Gambar siap untuk dianalisis');
    }

    showProcessingState() {
        const { elements } = this;
        
        elements.processingOverlay?.classList.add('show');
        elements.resultsOverlay?.classList.remove('show');
        
        elements.processingActions?.classList.remove('hidden');
        
        this.startProcessingAnimation();
        this.updateGlobalStatus('Menganalisis gambar...');
    }

    showResultsState() {
        const { elements } = this;
        
        elements.processingOverlay?.classList.remove('show');
        elements.resultsOverlay?.classList.add('show');
        elements.resultsPanel?.classList.remove('hidden');
        
        elements.resultsActions?.classList.remove('hidden');
        
        this.updateGlobalStatus('Deteksi selesai');
    }

    // === CAMERA & FILE HANDLING ===
    handleCameraAction() {
        if (!this.isConnected) {
            this.showNotification('Hubungkan ke server terlebih dahulu', 'warning');
            return;
        }
        
        // For Raspberry Pi, this could trigger camera capture
        // For now, fallback to file picker
        this.showNotification('Menggunakan file picker (kamera akan diimplementasikan)', 'info');
        this.handleFileAction();
    }

    handleFileAction() {
        if (!this.isConnected) {
            this.showNotification('Hubungkan ke server terlebih dahulu', 'warning');
            return;
        }
        
        this.elements.fileInput?.click();
    }

    handleChangeImage() {
        this.currentFile = null;
        this.selectedBase64 = null;
        this.currentResults = null;
        
        this.setState('initial');
        
        if (window.innerWidth <= 768) {
            this.closeSidebar();
        }
    }

    handleFileSelect(file) {
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            this.showNotification('Pilih file gambar yang valid', 'error');
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            this.showNotification('Ukuran file terlalu besar (maksimal 10MB)', 'error');
            return;
        }
        
        this.currentFile = file;
        this.loadImagePreview(file);
        
        if (window.innerWidth <= 768) {
            this.closeSidebar();
        }
    }

    loadImagePreview(file) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            this.selectedBase64 = e.target.result;
            
            if (this.elements.previewImage) {
                this.elements.previewImage.src = e.target.result;
                this.elements.previewImage.onload = () => {
                    this.setState('imageReady');
                };
            }
            
            this.showNotification(`Gambar ${file.name} berhasil dimuat`, 'success');
        };
        
        reader.onerror = () => {
            this.showNotification('Gagal memuat gambar', 'error');
            this.setState('initial');
        };
        
        reader.readAsDataURL(file);
    }

    // === CONNECTION MANAGEMENT ===
    setConnectionState(state) {
        const { elements } = this;
        
        elements.statusIndicator?.classList.remove('connected', 'connecting');
        elements.connectBtn?.classList.remove('connected', 'connecting');
        elements.mainStatusDot?.classList.remove('connected', 'connecting');
        
        switch(state) {
            case 'connected':
                if (elements.connectBtn) {
                    elements.connectBtn.textContent = 'Disconnect';
                    elements.connectBtn.classList.add('connected');
                }
                if (elements.statusIndicator) elements.statusIndicator.classList.add('connected');
                if (elements.statusText) elements.statusText.textContent = 'Terhubung';
                if (elements.mainStatusDot) elements.mainStatusDot.classList.add('connected');
                if (elements.mainStatusText) elements.mainStatusText.textContent = 'Server terhubung';
                break;
                
            case 'connecting':
                if (elements.connectBtn) {
                    elements.connectBtn.textContent = 'Menghubungkan...';
                    elements.connectBtn.classList.add('connecting');
                }
                if (elements.statusIndicator) elements.statusIndicator.classList.add('connecting');
                if (elements.statusText) elements.statusText.textContent = 'Menghubungkan...';
                if (elements.mainStatusDot) elements.mainStatusDot.classList.add('connecting');
                if (elements.mainStatusText) elements.mainStatusText.textContent = 'Menghubungkan...';
                break;
                
            case 'disconnected':
            default:
                if (elements.connectBtn) {
                    elements.connectBtn.textContent = 'Connect';
                }
                if (elements.statusText) elements.statusText.textContent = 'Tidak Terhubung';
                if (elements.mainStatusText) elements.mainStatusText.textContent = 'Hubungkan ke server';
                break;
        }
    }

    updateButtonStates() {
        const { elements } = this;
        const buttonsToUpdate = [
            elements.cameraBtn,
            elements.fileBtn,
            elements.detectBtn
        ];
        
        buttonsToUpdate.forEach(button => {
            if (button) {
                button.disabled = !this.isConnected;
            }
        });
    }

    // === OTHER METHODS (keep from original) ===
    initializeTouchFeedback() {
        const interactiveElements = document.querySelectorAll(
            'button, .history-item, .stat-item, .action-btn, .modal-btn'
        );
        
        interactiveElements.forEach(element => {
            element.classList.add('touch-feedback');
            
            element.addEventListener('touchstart', (e) => {
                element.style.transform = 'scale(0.98)';
            }, { passive: true });
            
            element.addEventListener('touchend', (e) => {
                setTimeout(() => {
                    element.style.transform = '';
                }, 150);
            }, { passive: true });
        });
    }

    generateDemoResults() {
        const pestTypes = [
            'Wereng Batang Coklat',
            'Penggerek Batang Padi',
            'Walang Sangit',
            'Ulat Grayak Padi'
        ];
        
        const detectionCount = Math.floor(Math.random() * 3) + 1;
        const detections = [];
        
        for (let i = 0; i < detectionCount; i++) {
            detections.push({
                name: pestTypes[Math.floor(Math.random() * pestTypes.length)],
                confidence: Math.floor(Math.random() * 20) + 80
            });
        }
        
        return {
            detections,
            totalDetections: detectionCount,
            avgConfidence: Math.floor(detections.reduce((sum, d) => sum + d.confidence, 0) / detectionCount),
            recommendations: this.generateRecommendations(detections)
        };
    }

    generateRecommendations(detections) {
        const baseRecommendations = [
            'Isolasi area yang terinfeksi segera',
            'Aplikasikan insektisida sesuai dosis anjuran',
            'Pantau perkembangan setiap 2-3 hari',
            'Perbaiki sistem drainase sawah'
        ];
        
        const specificRecommendations = {
            'Wereng Batang Coklat': ['Gunakan varietas tahan wereng', 'Aplikasikan Imidakloprid'],
            'Penggerek Batang Padi': ['Bersihkan tunggul padi', 'Tanam serempak'],
            'Walang Sangit': ['Pasang perangkap cahaya', 'Semprot pada pagi/sore hari'],
            'Ulat Grayak Padi': ['Gunakan Bacillus thuringiensis', 'Bersihkan gulma']
        };
        
        let recommendations = [...baseRecommendations];
        
        detections.forEach(detection => {
            if (specificRecommendations[detection.name]) {
                recommendations.push(...specificRecommendations[detection.name]);
            }
        });
        
        return [...new Set(recommendations)].slice(0, 6);
    }

    displayResults(results, processingTime) {
        const { elements } = this;
        
        if (elements.detectionCount) {
            elements.detectionCount.textContent = results.totalDetections;
        }
        if (elements.confidenceLevel) {
            elements.confidenceLevel.textContent = results.avgConfidence + '%';
        }
        if (elements.processingTimeResult) {
            elements.processingTimeResult.textContent = processingTime + 's';
        }
        if (elements.resultsCount) {
            elements.resultsCount.textContent = `${results.totalDetections} hama terdeteksi`;
        }
        
        if (elements.detectionDetails) {
            elements.detectionDetails.innerHTML = '';
            results.detections.forEach(detection => {
                const detectionElement = document.createElement('div');
                detectionElement.className = 'detection-item';
                detectionElement.innerHTML = `
                    <div class="detection-name">${detection.name}</div>
                    <div class="detection-confidence">${detection.confidence}%</div>
                `;
                elements.detectionDetails.appendChild(detectionElement);
            });
        }
        
        if (elements.recommendationsList) {
            elements.recommendationsList.innerHTML = '';
            results.recommendations.forEach(recommendation => {
                const li = document.createElement('li');
                li.textContent = recommendation;
                elements.recommendationsList.appendChild(li);
            });
        }
        
        this.updateTodayStats();
    }

    startProcessingAnimation() {
        const { elements } = this;
        
        if (elements.progressBar) {
            elements.progressBar.style.width = '0%';
            
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 15 + 5;
                if (progress > 100) progress = 100;
                
                elements.progressBar.style.width = progress + '%';
                
                if (progress >= 100 || this.currentState !== 'processing') {
                    clearInterval(interval);
                }
            }, 200);
        }
        
        this.animateProcessingText();
    }

    animateProcessingText() {
        const { elements } = this;
        if (!elements.processingText) return;
        
        const messages = [
            'Menganalisis gambar...',
            'Mendeteksi objek...',
            'Mengidentifikasi hama...',
            'Menghitung confidence...',
            'Menyiapkan hasil...'
        ];
        
        let index = 0;
        const interval = setInterval(() => {
            if (this.currentState !== 'processing') {
                clearInterval(interval);
                return;
            }
            
            elements.processingText.textContent = messages[index];
            index = (index + 1) % messages.length;
        }, 800);
    }

    startNewDetection() {
        this.handleChangeImage();
    }

    showResultsDetail() {
        if (!this.currentResults) return;
        
        this.elements.resultsPanel?.scrollIntoView({ behavior: 'smooth' });
        this.showNotification('Detail hasil ditampilkan di bawah', 'info');
    }

    // === HISTORY MANAGEMENT ===
    addToHistory(item) {
        const historyItem = {
            id: Date.now().toString(),
            filename: item.filename,
            timestamp: item.timestamp,
            results: item.results,
            processingTime: item.processingTime,
            resultImage: item.resultImage || this.selectedBase64
        };
        
        this.history.unshift(historyItem);
        
        if (this.history.length > 20) {
            this.history = this.history.slice(0, 20);
        }
        
        this.saveHistory();
        this.renderHistory();
    }

    renderHistory() {
        const { elements } = this;
        if (!elements.historyList) return;

        elements.historyList.innerHTML = '';

        if (this.history.length === 0) {
            elements.historyList.innerHTML = `
                <div style="
                    color: var(--text-muted); 
                    text-align: center; 
                    padding: 20px; 
                    font-size: 0.9rem;
                    font-style: italic;
                ">
                    Belum ada riwayat deteksi
                </div>
            `;
            return;
        }

        this.history.forEach((item) => {
            const historyElement = document.createElement('div');
            historyElement.className = 'history-item';
            
            const timeStr = item.timestamp.toLocaleTimeString('id-ID', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            const dateStr = item.timestamp.toLocaleDateString('id-ID', { 
                day: 'numeric', 
                month: 'short' 
            });
            
            const primaryPest = item.results?.detections?.[0]?.name || 'Tidak terdeteksi';
            
            historyElement.innerHTML = `
                <div class="history-thumbnail">🐛</div>
                <div class="history-info">
                    <h5>${primaryPest}</h5>
                    <p>${dateStr}, ${timeStr}</p>
                    <p>${item.results?.totalDetections || 0} deteksi • ${item.processingTime}s</p>
                </div>
            `;
            
            historyElement.addEventListener('click', () => {
                this.showHistoryDetail(item);
                if (window.innerWidth <= 768) {
                    this.closeSidebar();
                }
            });
            
            elements.historyList.appendChild(historyElement);
        });
    }

    showHistoryDetail(item) {
        // Implementation same as original
        const { elements } = this;
        if (!elements.historyModal || !elements.historyModalBody) return;
        
        const fullDateTime = item.timestamp.toLocaleString('id-ID', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        let detectionsHtml = '';
        if (item.results?.detections) {
            detectionsHtml = item.results.detections.map(detection => `
                <div class="detection-item">
                    <div class="detection-name">${detection.name}</div>
                    <div class="detection-confidence">${detection.confidence}%</div>
                </div>
            `).join('');
        }
        
        let recommendationsHtml = '';
        if (item.results?.recommendations) {
            recommendationsHtml = item.results.recommendations.map(rec => `
                <li>${rec}</li>
            `).join('');
        }
        
        elements.historyModalBody.innerHTML = `
            <div class="history-detail-content">
                <div class="detail-header">
                    <h4>📄 Informasi Deteksi</h4>
                    <div class="detail-info">
                        <p><strong>Tanggal:</strong> ${fullDateTime}</p>
                        <p><strong>File:</strong> ${item.filename}</p>
                        <p><strong>Session ID:</strong> #${item.id.slice(-6)}</p>
                        <p><strong>Waktu Proses:</strong> ${item.processingTime} detik</p>
                    </div>
                </div>

                <div class="detail-image">
                    <h4>🖼️ Hasil Deteksi</h4>
                    <div class="result-image-container">
                        <img src="${item.resultImage}" alt="Hasil Deteksi" class="modal-result-image" style="max-width: 100%; border-radius: 8px;">
                    </div>
                </div>

                <div class="detail-results">
                    <h4>🎯 Hasil Analisis</h4>
                    <div class="analysis-summary">
                        <div class="summary-item">
                            <span class="summary-label">Total Deteksi:</span>
                            <span class="summary-value">${item.results?.totalDetections || 0}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Rata-rata Keyakinan:</span>
                            <span class="summary-value">${item.results?.avgConfidence || 0}%</span>
                        </div>
                    </div>
                    
                    ${detectionsHtml ? `
                        <h5>🐛 Hama yang Terdeteksi:</h5>
                        <div class="detection-list">
                            ${detectionsHtml}
                        </div>
                    ` : '<p>Tidak ada hama yang terdeteksi.</p>'}
                </div>

                ${recommendationsHtml ? `
                    <div class="detail-recommendations">
                        <h4>💊 Rekomendasi Tindakan</h4>
                        <ul class="recommendations-list">
                            ${recommendationsHtml}
                        </ul>
                    </div>
                ` : ''}

                <div class="detail-actions">
                    <button class="action-btn secondary" onclick="app.downloadHistoryReport('${item.id}')">
                        <span class="btn-icon">📄</span>
                        <span class="btn-text">Unduh Laporan</span>
                    </button>
                    <button class="action-btn primary" onclick="app.rerunDetection('${item.id}')">
                        <span class="btn-icon">🔄</span>
                        <span class="btn-text">Deteksi Ulang</span>
                    </button>
                </div>
            </div>
        `;
        
        this.showModal(elements.historyModal);
    }

    hideHistoryModal() {
        this.hideModal(this.elements.historyModal);
    }

    downloadHistoryReport(itemId) {
        const item = this.history.find(h => h.id === itemId);
        if (!item) return;
        
        const report = this.generateTextReport(item);
        this.downloadTextFile(`laporan_deteksi_${item.id}.txt`, report);
        
        this.showNotification('Laporan berhasil diunduh', 'success');
    }

    rerunDetection(itemId) {
        const item = this.history.find(h => h.id === itemId);
        if (!item || !item.resultImage) return;
        
        this.selectedBase64 = item.resultImage;
        this.currentFile = { name: item.filename };
        
        if (this.elements.previewImage) {
            this.elements.previewImage.src = item.resultImage;
        }
        
        this.hideHistoryModal();
        this.setState('imageReady');
        
        this.showNotification('Gambar dimuat untuk deteksi ulang', 'info');
    }

    generateTextReport(item) {
        const timestamp = item.timestamp.toLocaleString('id-ID');
        
        let report = `
==========================================
        LAPORAN DETEKSI HAMA PADI
==========================================

Tanggal/Waktu    : ${timestamp}
File Gambar      : ${item.filename}
Session ID       : #${item.id}
Waktu Proses     : ${item.processingTime} detik

HASIL DETEKSI:
-----------------------------------------
Total Hama       : ${item.results?.totalDetections || 0}
Rata-rata Akurasi: ${item.results?.avgConfidence || 0}%

DETAIL HAMA TERDETEKSI:
`;

        if (item.results?.detections) {
            item.results.detections.forEach((detection, index) => {
                report += `${index + 1}. ${detection.name} (${detection.confidence}%)\n`;
            });
        } else {
            report += "Tidak ada hama yang terdeteksi.\n";
        }

        if (item.results?.recommendations) {
            report += `\nREKOMENDASI TINDAKAN:\n`;
            report += `-----------------------------------------\n`;
            item.results.recommendations.forEach((rec, index) => {
                report += `${index + 1}. ${rec}\n`;
            });
        }

        report += `\n==========================================\n`;
        report += `Laporan dibuat oleh JAGAPADI v2.0\n`;
        report += `AI Deteksi Hama Padi\n`;
        report += `==========================================\n`;

        return report;
    }

    downloadTextFile(filename, content) {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    async loadPersistedData() {
        this.history = await this.loadHistory();
        this.renderHistory();
        this.updateTodayStats();
        
        console.log(`📊 Loaded ${this.history.length} history items`);
    }

    saveHistory() {
        try {
            localStorage.setItem('jagapadi-history', JSON.stringify(this.history));
        } catch (error) {
            console.log('LocalStorage not available, history not saved');
        }
    }

    updateTodayStats() {
        const today = new Date().toDateString();
        const todayItems = this.history.filter(item => 
            item.timestamp.toDateString() === today
        );
        
        const totalDetections = todayItems.reduce((sum, item) => 
            sum + (item.results?.totalDetections || 0), 0
        );
        
        const avgAccuracy = todayItems.length > 0 
            ? Math.round(todayItems.reduce((sum, item) => 
                sum + (item.results?.avgConfidence || 0), 0
            ) / todayItems.length)
            : 0;
        
        this.todayStats = {
            detections: totalDetections,
            accuracy: avgAccuracy
        };
        
        if (this.elements.todayDetections) {
            this.elements.todayDetections.textContent = totalDetections;
        }
        if (this.elements.todayAccuracy) {
            this.elements.todayAccuracy.textContent = avgAccuracy + '%';
        }
    }

    // === MODAL MANAGEMENT ===
    showModal(modalElement) {
        if (modalElement) {
            modalElement.classList.add('show');
            modalElement.style.display = 'flex';
            
            const firstFocusable = modalElement.querySelector('button, input, textarea, select');
            if (firstFocusable) {
                firstFocusable.focus();
            }
        }
    }

    hideModal(modalElement) {
        if (modalElement) {
            modalElement.classList.remove('show');
            modalElement.style.display = 'none';
        }
    }

    showAuthModal() {
        this.showModal(this.elements.authModal);
        if (this.elements.passwordInput) {
            this.elements.passwordInput.focus();
        }
    }

    hideAuthModal() {
        this.hideModal(this.elements.authModal);
        if (this.elements.passwordInput) {
            this.elements.passwordInput.value = '';
        }
    }

    // === SIDEBAR MANAGEMENT ===
    toggleSidebar() {
        this.sidebarOpen = !this.sidebarOpen;
        const { sidebar, sidebarOverlay } = this.elements;
        
        if (this.sidebarOpen) {
            sidebar?.classList.add('open');
            sidebarOverlay?.classList.add('show');
        } else {
            this.closeSidebar();
        }
    }

    closeSidebar() {
        this.sidebarOpen = false;
        const { sidebar, sidebarOverlay } = this.elements;
        sidebar?.classList.remove('open');
        sidebarOverlay?.classList.remove('show');
    }

    // === THEME MANAGEMENT ===
    toggleDarkMode() {
        this.isDarkMode = !this.isDarkMode;
        this.applyTheme();
        this.saveTheme();
        this.showNotification(
            `Mode ${this.isDarkMode ? 'gelap' : 'terang'} diaktifkan`, 
            'info'
        );
    }

    applyTheme() {
        const { darkModeBtn } = this.elements;
        
        if (this.isDarkMode) {
            document.documentElement.setAttribute('data-theme', 'dark');
            if (darkModeBtn) darkModeBtn.textContent = '☀️';
        } else {
            document.documentElement.removeAttribute('data-theme');
            if (darkModeBtn) darkModeBtn.textContent = '🌓';
        }
    }

    loadTheme() {
        try {
            const saved = localStorage.getItem('jagapadi-dark-mode');
            return saved === 'true';
        } catch (error) {
            console.log('LocalStorage not available, using default theme');
            return false;
        }
    }

    saveTheme() {
        try {
            localStorage.setItem('jagapadi-dark-mode', this.isDarkMode.toString());
        } catch (error) {
            console.log('LocalStorage not available, theme not saved');
        }
    }

    // === NOTIFICATION SYSTEM ===
    showNotification(message, type = 'info') {
        const { notification } = this.elements;
        
        if (notification) {
            notification.textContent = message;
            notification.className = `notification ${type}`;
            notification.classList.add('show');

            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    // === STATUS & UI UPDATES ===
    updateGlobalStatus(message) {
        if (this.elements.globalStatus) {
            this.elements.globalStatus.textContent = message || 'Siap untuk deteksi';
        }
        console.log('📊 Status:', message);
    }

    updateStatusBar() {
        if (this.elements.statusTime) {
            const updateTime = () => {
                const now = new Date();
                this.elements.statusTime.textContent = now.toLocaleTimeString('id-ID');
            };
            
            updateTime();
            setInterval(updateTime, 1000);
        }
    }

    animateStateTransition(fromState, toState) {
        const container = this.elements.previewContainer;
        if (container) {
            container.style.transform = 'scale(0.98)';
            container.style.opacity = '0.8';
            
            setTimeout(() => {
                container.style.transform = '';
                container.style.opacity = '';
            }, 200);
        }
    }

    // === EVENT HANDLERS ===
    handleKeyboard(e) {
        if (e.key === 'Escape') {
            if (this.elements.historyModal?.classList.contains('show')) {
                this.hideHistoryModal();
            } else if (this.elements.authModal?.classList.contains('show')) {
                this.hideAuthModal();
            } else if (this.sidebarOpen) {
                this.closeSidebar();
            }
        }
        
        if (e.key === ' ' && e.target === document.body) {
            e.preventDefault();
            if (this.currentState === 'initial' && this.isConnected) {
                this.handleCameraAction();
            } else if (this.currentState === 'imageReady') {
                this.startDetection();
            }
        }
        
        if (e.key === 'Enter' && this.currentState === 'imageReady') {
            this.startDetection();
        }
    }

    handleResize() {
        if (window.innerWidth > 768 && this.sidebarOpen) {
            this.closeSidebar();
        }
    }

    cleanup() {
        this.saveHistory();
        this.saveTheme();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    updateStatus(message) {
        this.updateGlobalStatus(message);
    }
}

// === GLOBAL INITIALIZATION ===
let app = null;

// Legacy functions for backward compatibility
function tampilkanHasil(base64img) {
    if (app) {
        app.tampilkanHasil(base64img);
    }
}

function updateStatus(message) {
    if (app) {
        app.updateStatus(message);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    app = new JagaPadiApp();
    window.app = app;
});

// Export for use in other modules if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { JagaPadiApp, tampilkanHasil, updateStatus };
}

window.addEventListener('load', () => {
    console.log('🌾 JAGAPADI v2.0 Flask Edition loaded successfully!');
    console.log('📱 Ready for Raspberry Pi touchscreen');
});