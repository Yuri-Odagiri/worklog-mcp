class SimpleWorklogViewer {
    constructor() {
        this.entries = [];
        this.users = {};
        this.eventSource = null;
        this.currentSearch = '';
        this.currentUserSearch = '';
        this.currentTab = 'worklogs';
        this.usersData = [];
        this.init();
    }
    
    async init() {
        try {
            await this.loadUsers();
            await this.load();
            this.setupSSE();
            this.setupKeyboardShortcuts();
        } catch (error) {
            this.showError('初期化に失敗しました: ' + error.message);
        }
    }
    
    async load(search = '') {
        try {
            const url = search ? 
                `/api/entries?search=${encodeURIComponent(search)}&limit=50` : 
                '/api/entries?limit=50';
            
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.entries = data.entries;
            this.currentSearch = search;
            this.render();
            
        } catch (error) {
            this.showError('データ読み込みエラー: ' + error.message);
        }
    }
    
    async loadUsers() {
        try {
            const response = await fetch('/api/users');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const users = await response.json();
            this.users = {};
            users.forEach(user => {
                this.users[user.user_id] = user;
            });
        } catch (error) {
            console.error('ユーザー読み込みエラー:', error);
        }
    }
    
    setupSSE() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        this.eventSource = new EventSource('/events');
        
        this.eventSource.onopen = () => {
            this.updateConnectionStatus('connected', '🟢 リアルタイム更新中');
        };
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleSSEEvent(data);
            } catch (error) {
                console.error('SSEイベント処理エラー:', error);
            }
        };
        
        this.eventSource.onerror = () => {
            this.updateConnectionStatus('disconnected', '🔴 接続エラー');
            // 5秒後に再接続を試行
            setTimeout(() => this.setupSSE(), 5000);
        };
    }
    
    handleSSEEvent(event) {
        switch (event.type) {
            case 'connected':
                this.updateConnectionStatus('connected', '🟢 接続完了');
                break;
            case 'entry_created':
                this.addNewEntry(event.data);
                break;
            case 'entry_deleted':
                this.removeEntry(event.data.id);
                break;
            case 'entries_truncated':
                this.entries = [];
                this.render();
                let message = `${event.data.deleted_count} 件の分報が削除されました`;
                if (event.data.users_deleted > 0) {
                    message += `（${event.data.users_deleted} 件のユーザー情報も削除）`;
                }
                if (event.data.avatars_deleted > 0) {
                    message += `（${event.data.avatars_deleted} 件のアバター画像も削除）`;
                }
                this.showNotification(message);
                break;
            case 'avatar_updated':
                this.handleAvatarUpdate(event.data);
                break;
            case 'ping':
                // Keep-alive応答（何もしない）
                break;
        }
    }
    
    addNewEntry(entryData) {
        // 検索中でない場合のみ新エントリーを追加
        if (!this.currentSearch) {
            this.entries.unshift(entryData);
            // 最大100件に制限
            if (this.entries.length > 100) {
                this.entries = this.entries.slice(0, 100);
            }
            this.render();
            this.showNotification('新しい投稿がありました');
        }
    }
    
    removeEntry(entryId) {
        // エントリーをリストから削除
        this.entries = this.entries.filter(entry => entry.id !== entryId);
        this.render();
        this.showNotification('分報が削除されました');
    }
    
    render() {
        const container = document.getElementById('entries-container');
        
        // サマリ情報を更新
        this.updateSummary();
        
        if (this.entries.length === 0) {
            container.innerHTML = `
                <div class="no-entries">
                    ${this.currentSearch ? 
                        `「${this.currentSearch}」に該当する投稿が見つかりませんでした。` : 
                        '投稿がまだありません。'}
                </div>
            `;
            return;
        }
        
        container.innerHTML = '';
        
        this.entries.forEach(entry => {
            const entryElement = this.createEntryElement(entry);
            container.appendChild(entryElement);
        });
    }
    
    createEntryElement(entry) {
        const div = document.createElement('div');
        div.className = 'entry';
        div.dataset.entryId = entry.id;
        
        const user = this.users[entry.user_id];
        const userName = user ? user.name : entry.user_name || entry.user_id;
        const userRole = user ? user.role : '';
        const themeColor = user ? user.theme_color : 'Blue';
        const date = new Date(entry.created_at);
        const formattedDate = this.formatDate(date);
        
        // 返信機能は削除されました
        
        // テーマカラーを淡い色に変換
        const lightColor = this.getThemeColorStyle(themeColor);
        
        // アバター画像URLを構築
        const avatarUrl = this.getAvatarUrl(entry.user_avatar_path || '', entry.user_id);
        
        div.innerHTML = `
            <img src="${avatarUrl}" alt="${this.escapeHtml(userName)}" class="avatar" 
                 data-user-id="${entry.user_id}"
                 onerror="this.outerHTML='<div class=\\'avatar error\\'>👤</div>'"
                 style="border-color: ${lightColor.border};">
            <div class="entry-content">
                <div class="entry-header" style="border-bottom-color: ${lightColor.border};">
                    <div>
                        <span class="user-name" style="color: ${lightColor.text};">${this.escapeHtml(userName)}</span>
                        ${userRole ? `<span class="user-role" style="background-color: ${lightColor.background}; color: ${lightColor.text};">${this.escapeHtml(userRole)}</span>` : ''}
                    </div>
                    <span class="timestamp">${formattedDate}</span>
                </div>
                <div class="content markdown-content">${this.renderMarkdown(entry.markdown_content)}</div>
            </div>
            <button class="delete-btn" onclick="app.confirmDeleteEntry('${entry.id}')" title="削除">🗑️</button>
        `;
        
        return div;
    }
    
    getThemeColorStyle(color) {
        // 白基調の背景に適した淡い色合いのマッピング
        const colorMap = {
            'Red': {
                background: '#ffeaea',
                border: '#ffb3b3',
                text: '#d63384'
            },
            'Blue': {
                background: '#e7f3ff',
                border: '#91c5f7',
                text: '#0066cc'
            },
            'Green': {
                background: '#e8f5e8',
                border: '#95d982',
                text: '#157347'
            },
            'Yellow': {
                background: '#fff8e1',
                border: '#ffcc80',
                text: '#b8860b'
            },
            'Purple': {
                background: '#f3e8ff',
                border: '#c084fc',
                text: '#7c3aed'
            },
            'Orange': {
                background: '#fff4e6',
                border: '#ffb366',
                text: '#e67700'
            },
            'Pink': {
                background: '#fce7f3',
                border: '#f9a8d4',
                text: '#db2777'
            },
            'Cyan': {
                background: '#e0f8ff',
                border: '#7dd3fc',
                text: '#0891b2'
            }
        };
        
        return colorMap[color] || colorMap['Blue'];
    }
    
    updateConnectionStatus(status, text) {
        const statusElement = document.getElementById('status');
        statusElement.textContent = text;
        statusElement.className = `status ${status}`;
    }
    
    updateSummary() {
        const summaryElement = document.getElementById('summary');
        
        if (this.entries.length === 0) {
            summaryElement.innerHTML = '';
            return;
        }
        
        // ユーザー数を計算
        const uniqueUsers = new Set(this.entries.map(entry => entry.user_id));
        const userCount = uniqueUsers.size;
        
        // 今日の投稿数を計算
        const today = new Date().toDateString();
        const todayPosts = this.entries.filter(entry => {
            const entryDate = new Date(entry.created_at).toDateString();
            return entryDate === today;
        }).length;
        
        // 最新投稿時間を計算
        const latestEntry = this.entries[0]; // 既に時系列でソートされている
        const timeSinceLatest = latestEntry ? this.formatDate(new Date(latestEntry.created_at)) : '';
        
        summaryElement.innerHTML = `
            <div class="stat">📊 投稿数: ${this.entries.length}件</div>
            <div class="stat">👥 メンバー: ${userCount}人</div>
            <div class="stat">📅 今日: ${todayPosts}件</div>
            ${timeSinceLatest ? `<div class="stat">⏰ 最新: ${timeSinceLatest}</div>` : ''}
        `;
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey || event.metaKey) {
                switch (event.key) {
                    case 'r':
                        event.preventDefault();
                        this.load(this.currentSearch);
                        break;
                    case 'f':
                        event.preventDefault();
                        document.getElementById('search').focus();
                        break;
                }
            }
        });
        
        // 検索欄でEnterキー
        document.getElementById('search').addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                this.search();
            }
        });
        
        // ユーザー検索欄でEnterキー
        document.getElementById('user-search').addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                this.searchUsers();
            }
        });
    }
    
    search() {
        const query = document.getElementById('search').value.trim();
        this.load(query);
    }
    
    formatDate(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'たった今';
        if (diffMins < 60) return `${diffMins}分前`;
        if (diffHours < 24) return `${diffHours}時間前`;
        if (diffDays < 7) return `${diffDays}日前`;
        
        return date.toLocaleString('ja-JP', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML.replace(/\n/g, '<br>');
    }
    
    renderMarkdown(markdown) {
        if (!markdown) return '';
        
        try {
            // Markdownを設定
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false // DOMPurifyを使用するため
            });
            
            // MarkdownをHTMLに変換
            const rawHtml = marked.parse(markdown);
            
            // DOMPurifyで安全なHTMLにサニタイズ
            const cleanHtml = DOMPurify.sanitize(rawHtml, {
                ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'del', 's', 'code', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr'],
                ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'target', 'rel'],
                ALLOW_DATA_ATTR: false
            });
            
            return cleanHtml;
        } catch (error) {
            console.error('Markdownレンダリングエラー:', error);
            // エラーの場合は元のテキストをエスケープして表示
            return this.escapeHtml(markdown);
        }
    }
    
    showError(message) {
        const container = document.getElementById('entries-container');
        container.innerHTML = `
            <div class="error">
                ❌ ${this.escapeHtml(message)}
            </div>
        `;
    }
    
    showNotification(message) {
        // 簡単な通知表示（ブラウザ通知APIは使用しない）
        console.log('通知:', message);
        
        // ページタイトルを一時的に変更して通知
        const originalTitle = document.title;
        document.title = `🔔 ${message}`;
        setTimeout(() => {
            document.title = originalTitle;
        }, 3000);
    }
    
    async confirmDeleteEntry(entryId) {
        if (confirm('この分報を削除しますか？\n削除は元に戻せません。')) {
            try {
                await this.deleteEntry(entryId);
            } catch (error) {
                console.error('削除エラー:', error);
                alert('削除に失敗しました: ' + error.message);
            }
        }
    }
    
    async deleteEntry(entryId) {
        try {
            const response = await fetch(`/api/entries/${entryId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            // エントリーをUIから削除
            const entryElement = document.querySelector(`[data-entry-id="${entryId}"]`);
            if (entryElement) {
                entryElement.remove();
            }
            
            this.showNotification('分報を削除しました');
            
        } catch (error) {
            throw error;
        }
    }
    
    async confirmTruncateAll() {
        // 削除オプション選択のモーダル表示
        const deleteOption = await this.showDeleteOptionsModal();
        if (!deleteOption) return; // キャンセルされた場合
        
        // 最終確認
        const confirmed = confirm(
            deleteOption === 'worklogs_only' 
                ? '全ての分報を削除しますか？\n（ユーザー情報は保持されます）\n\nこの操作は元に戻せません。'
                : '全ての分報とユーザー情報を削除しますか？\n\nこの操作は元に戻せません。'
        );
        
        if (confirmed) {
            try {
                await this.truncateAllEntries(deleteOption);
            } catch (error) {
                console.error('全削除エラー:', error);
                alert('全削除に失敗しました: ' + error.message);
            }
        }
    }
    
    async truncateAllEntries(deleteOption = 'worklogs_only') {
        try {
            const response = await fetch('/api/entries', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    delete_option: deleteOption
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            // UIをクリア
            this.entries = [];
            this.render();
            
            this.showNotification(result.message || '全ての分報を削除しました');
            
        } catch (error) {
            throw error;
        }
    }

    showDeleteOptionsModal() {
        return new Promise((resolve) => {
            // モーダルHTML作成
            const modal = document.createElement('div');
            modal.className = 'delete-modal-overlay';
            modal.innerHTML = `
                <div class="delete-modal">
                    <h3>削除オプションを選択してください</h3>
                    <div class="delete-options">
                        <label class="delete-option">
                            <input type="radio" name="deleteOption" value="worklogs_only" checked>
                            <span>分報のみ削除</span>
                            <small>分報データのみを削除し、ユーザー情報は保持します</small>
                        </label>
                        <label class="delete-option">
                            <input type="radio" name="deleteOption" value="full_reset">
                            <span>完全リセット</span>
                            <small>分報データとユーザー情報を全て削除します</small>
                        </label>
                    </div>
                    <div class="modal-buttons">
                        <button type="button" class="cancel-btn">キャンセル</button>
                        <button type="button" class="confirm-btn">決定</button>
                    </div>
                </div>
            `;
            
            // モーダルをDOMに追加
            document.body.appendChild(modal);
            
            // イベントリスナー設定
            modal.querySelector('.cancel-btn').onclick = () => {
                document.body.removeChild(modal);
                resolve(null);
            };
            
            modal.querySelector('.confirm-btn').onclick = () => {
                const selectedOption = modal.querySelector('input[name="deleteOption"]:checked').value;
                document.body.removeChild(modal);
                resolve(selectedOption);
            };
            
            // モーダル外クリックでキャンセル
            modal.onclick = (e) => {
                if (e.target === modal) {
                    document.body.removeChild(modal);
                    resolve(null);
                }
            };
        });
    }
    
    /**
     * アバターパスからWebアクセス可能なURLを生成
     */
    getAvatarUrl(avatarPath, userId) {
        if (!avatarPath) {
            // 動的アバター生成: ファイルではなくSVGデータURLを返す
            return this.generateDynamicAvatar(userId);
        }
        
        // ファイル名だけを抽出
        const fileName = avatarPath.split('/').pop();
        return `/avatar/${fileName}`;
    }

    /**
     * 動的にグラデーションアバターを生成（SVG Data URL）
     */
    generateDynamicAvatar(userId) {
        // ユーザーのテーマカラーを取得（存在しない場合はBlueをデフォルト）
        const user = this.users[userId];
        const themeColor = user ? user.theme_color : 'Blue';
        
        // テーマカラーから基本色を取得
        const baseColor = this.getThemeBaseColor(themeColor);
        
        // user_idから決定的な種値を生成（文字の合計値を使用）
        let seed = 0;
        for (let i = 0; i < userId.length; i++) {
            seed += userId.charCodeAt(i);
        }
        
        // 種値を使って色のバリエーションを生成
        const hue = baseColor.hue + (seed % 60) - 30; // ±30度の範囲で色相を調整
        const saturation = Math.max(40, Math.min(80, baseColor.saturation + (seed % 20) - 10)); // 彩度調整
        
        // グラデーションの開始色と終了色を計算
        const startColor = `hsl(${hue}, ${saturation}%, 75%)`;
        const endColor = `hsl(${hue}, ${saturation}%, 45%)`;
        
        // SVGグラデーションアバターを生成
        const svg = `
            <svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <radialGradient id="avatarGradient_${userId}" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="${startColor}" stop-opacity="0.9"/>
                        <stop offset="70%" stop-color="${endColor}" stop-opacity="0.8"/>
                        <stop offset="100%" stop-color="${endColor}" stop-opacity="0.6"/>
                    </radialGradient>
                </defs>
                <circle cx="256" cy="256" r="246" fill="url(#avatarGradient_${userId})" stroke="${endColor}" stroke-width="4"/>
            </svg>
        `;
        
        // SVGをData URLに変換
        const dataUrl = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg)));
        return dataUrl;
    }

    /**
     * テーマカラーから基本HSL値を取得
     */
    getThemeBaseColor(themeColor) {
        const colorMap = {
            'Red': { hue: 0, saturation: 70 },
            'Blue': { hue: 210, saturation: 65 },
            'Green': { hue: 120, saturation: 60 },
            'Yellow': { hue: 45, saturation: 75 },
            'Purple': { hue: 270, saturation: 65 },
            'Orange': { hue: 30, saturation: 80 },
            'Pink': { hue: 330, saturation: 70 },
            'Cyan': { hue: 180, saturation: 65 }
        };
        
        return colorMap[themeColor] || colorMap['Blue']; // デフォルトはBlue
    }
    
    /**
     * アバター更新イベントを処理
     */
    handleAvatarUpdate(data) {
        const { user_id, avatar_path } = data;
        
        // ユーザー情報を更新
        if (this.users[user_id]) {
            this.users[user_id].avatar_path = avatar_path;
        }
        
        // 表示中の全ての該当ユーザーのアバター画像を更新
        const avatarElements = document.querySelectorAll(`img.avatar[data-user-id="${user_id}"]`);
        const newAvatarUrl = this.getAvatarUrl(avatar_path, user_id);
        
        avatarElements.forEach(img => {
            // 新しいURLで画像を更新
            img.src = newAvatarUrl;
            
            // 視覚的な更新フィードバック
            img.style.opacity = '0.5';
            img.onload = () => {
                img.style.opacity = '1';
                img.style.transition = 'opacity 0.3s ease';
            };
        });
        
        // 通知表示
        const userName = this.users[user_id]?.name || user_id;
        this.showNotification(`${userName} のアバターが AI生成版に更新されました`);
    }
    
    /**
     * タブ切り替え機能
     */
    switchTab(tabName) {
        this.currentTab = tabName;
        
        // タブボタンのアクティブ状態を更新
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // タブコンテンツの表示/非表示を更新
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`tab-${tabName}`).classList.add('active');
        
        // タブに応じてデータを読み込み
        if (tabName === 'users') {
            this.renderUsers();
        } else if (tabName === 'worklogs') {
            // 分報タブの場合は既に読み込み済み（既存のロジックを使用）
        }
    }
    
    /**
     * ユーザー検索機能
     */
    searchUsers() {
        const query = document.getElementById('user-search').value.trim();
        this.currentUserSearch = query;
        this.renderUsers();
    }
    
    /**
     * ユーザーデータの再読み込み
     */
    async loadUsers() {
        if (this.currentTab === 'users') {
            this.usersData = []; // キャッシュをクリア
            await this.renderUsers();
        }
    }
    
    /**
     * ユーザー一覧表示
     */
    async renderUsers() {
        const container = document.getElementById('users-container');
        
        try {
            // ユーザーデータが未取得の場合は取得
            if (this.usersData.length === 0) {
                await this.loadUsersData();
            }
            
            let filteredUsers = this.usersData;
            
            // 検索フィルター適用
            if (this.currentUserSearch) {
                const query = this.currentUserSearch.toLowerCase();
                filteredUsers = this.usersData.filter(user => 
                    user.name.toLowerCase().includes(query) ||
                    (user.role && user.role.toLowerCase().includes(query))
                );
            }
            
            if (filteredUsers.length === 0) {
                container.innerHTML = `
                    <div class="no-entries">
                        ${this.currentUserSearch ? 
                            `「${this.currentUserSearch}」に該当するユーザーが見つかりませんでした。` : 
                            'ユーザーが登録されていません。'}
                    </div>
                `;
                return;
            }
            
            // ユーザーカードのHTML生成
            const usersGrid = document.createElement('div');
            usersGrid.className = 'users-grid';
            
            for (const user of filteredUsers) {
                const userCard = await this.createUserCard(user);
                usersGrid.appendChild(userCard);
            }
            
            container.innerHTML = '';
            container.appendChild(usersGrid);
            
        } catch (error) {
            container.innerHTML = `
                <div class="error">
                    ❌ ユーザー情報の読み込みに失敗しました: ${this.escapeHtml(error.message)}
                </div>
            `;
        }
    }
    
    /**
     * ユーザーデータの詳細情報を取得
     */
    async loadUsersData() {
        try {
            const response = await fetch('/api/users');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            this.usersData = await response.json();
        } catch (error) {
            console.error('ユーザーデータ読み込みエラー:', error);
            throw error;
        }
    }
    
    /**
     * ユーザーカード要素を作成
     */
    async createUserCard(user) {
        const card = document.createElement('div');
        card.className = 'user-card';
        
        // ユーザーの活動統計を計算
        const stats = this.calculateUserStats(user.user_id);
        
        // テーマカラースタイル取得
        const themeStyle = this.getThemeColorStyle(user.theme_color);
        
        // アバターURL取得
        const avatarUrl = this.getAvatarUrl(user.avatar_path || '', user.user_id);
        
        // 登録日時と最終アクティブ時間をフォーマット
        const createdDate = new Date(user.created_at);
        const lastActiveDate = new Date(user.last_active);
        
        card.innerHTML = `
            <div class="user-card-header">
                <img src="${avatarUrl}" alt="${this.escapeHtml(user.name)}" class="user-card-avatar" 
                     style="border-color: ${themeStyle.border};"
                     onerror="this.outerHTML='<div class=\\'user-card-avatar error\\'>👤</div>'">
                <div class="user-card-info">
                    <h3 style="color: ${themeStyle.text};">${this.escapeHtml(user.name)}</h3>
                    <div class="user-card-id">ID: ${this.escapeHtml(user.user_id)}</div>
                    ${user.role ? `<div class="user-card-role" style="background-color: ${themeStyle.background}; color: ${themeStyle.text};">${this.escapeHtml(user.role)}</div>` : ''}
                    <div class="user-card-theme">テーマ: ${user.theme_color}</div>
                </div>
            </div>
            
            <div class="user-card-details">
                ${user.personality ? `
                    <div class="user-detail-section">
                        <div class="user-detail-label">性格・特徴</div>
                        <div class="user-detail-content">${this.escapeHtml(user.personality)}</div>
                    </div>
                ` : ''}
                ${user.appearance ? `
                    <div class="user-detail-section">
                        <div class="user-detail-label">外見・スタイル</div>
                        <div class="user-detail-content">${this.escapeHtml(user.appearance)}</div>
                    </div>
                ` : ''}
            </div>
            
            <div class="user-card-stats">
                <div class="user-stat">
                    <span class="user-stat-value">${stats.totalPosts}</span>
                    <span class="user-stat-label">総投稿数</span>
                </div>
                <div class="user-stat">
                    <span class="user-stat-value">${stats.todayPosts}</span>
                    <span class="user-stat-label">今日の投稿</span>
                </div>
            </div>
            
            <div class="user-activity">
                <div class="user-activity-item">
                    <span class="user-activity-label">登録日時</span>
                    <span class="user-activity-value">${this.formatDate(createdDate)}</span>
                </div>
                <div class="user-activity-item">
                    <span class="user-activity-label">最終アクティブ</span>
                    <span class="user-activity-value">${this.formatDate(lastActiveDate)}</span>
                </div>
                ${stats.lastPostTime ? `
                    <div class="user-activity-item">
                        <span class="user-activity-label">最新投稿</span>
                        <span class="user-activity-value">${this.formatDate(stats.lastPostTime)}</span>
                    </div>
                ` : ''}
            </div>
        `;
        
        return card;
    }
    
    /**
     * ユーザーの活動統計を計算
     */
    calculateUserStats(userId) {
        const userEntries = this.entries.filter(entry => entry.user_id === userId);
        
        // 今日の投稿数
        const today = new Date().toDateString();
        const todayPosts = userEntries.filter(entry => {
            const entryDate = new Date(entry.created_at).toDateString();
            return entryDate === today;
        }).length;
        
        // 最新投稿時間
        const lastPost = userEntries.length > 0 ? userEntries[0] : null;
        const lastPostTime = lastPost ? new Date(lastPost.created_at) : null;
        
        return {
            totalPosts: userEntries.length,
            todayPosts: todayPosts,
            lastPostTime: lastPostTime
        };
    }
}

// アプリケーション起動
const app = new SimpleWorklogViewer();