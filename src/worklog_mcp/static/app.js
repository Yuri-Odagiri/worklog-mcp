class SimpleWorklogViewer {
    constructor() {
        this.entries = [];
        this.users = {};
        this.eventSource = null;
        this.currentSearch = '';
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
                this.showNotification(`${event.data.deleted_count} 件の分報が削除されました`);
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
        
        // 返信の場合は特別なスタイル
        const isReply = entry.related_entry_id;
        if (isReply) {
            div.classList.add('thread-reply');
        }
        
        // テーマカラーを淡い色に変換
        const lightColor = this.getThemeColorStyle(themeColor);
        
        // アバター画像URLを構築
        const avatarUrl = `/avatar/${entry.user_id}.png`;
        
        div.innerHTML = `
            <img src="${avatarUrl}" alt="${this.escapeHtml(userName)}" class="avatar" 
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
                <div class="content">${this.escapeHtml(entry.markdown_content)}</div>
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
        const confirmed = confirm(
            '全ての分報を削除しますか？\n' +
            'この操作は元に戻せません。\n' +
            '本当に削除する場合は「OK」を押してください。'
        );
        
        if (confirmed) {
            const doubleConfirmed = confirm(
                '本当によろしいですか？\n' +
                '全データが完全に削除されます。'
            );
            
            if (doubleConfirmed) {
                try {
                    await this.truncateAllEntries();
                } catch (error) {
                    console.error('全削除エラー:', error);
                    alert('全削除に失敗しました: ' + error.message);
                }
            }
        }
    }
    
    async truncateAllEntries() {
        try {
            const response = await fetch('/api/entries', {
                method: 'DELETE'
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
}

// アプリケーション起動
const app = new SimpleWorklogViewer();