const API = '/api';
let currentTenderId = null;
let currentDocId = null;
let currentSourceId = null;
let currentSubmissionId = null;
let chatHistory = [];
let currentPreviewContent = '';
let searchTimeout = null;
let currentPage = 1;
let currentStatus = 'all';
let tenders = [];
let allTenders = [];

const App = {
  // Navigation
  showPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.getElementById('page-' + page)?.classList.add('active');
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
    this.loadPage(page);
  },

  loadPage(page) {
    switch (page) {
      case 'dashboard': this.loadDashboard(); break;
      case 'tenders': this.loadTenders(); break;
      case 'documents': this.loadDocuments(); break;
      case 'pipeline': this.loadPipeline(); break;
      case 'sources': this.loadSources(); break;
      case 'ai-writer': this.loadWriterTenders(); break;
    }
  },

  // Dashboard
  async loadDashboard() {
    const [stats, tenders, notifs] = await Promise.all([
      this.api('/tenders/stats'),
      this.api('/tenders?per_page=5'),
      this.api('/notifications?limit=8')
    ]);
    document.getElementById('statTotal').textContent = stats.total || 0;
    document.getElementById('statUnread').textContent = stats.unread || 0;
    document.getElementById('statClosing').textContent = stats.closing_soon || 0;
    document.getElementById('statWon').textContent = (stats.by_status?.won || 0);

    const recentEl = document.getElementById('recentTenders');
    recentEl.innerHTML = tenders.tenders?.length
      ? tenders.tenders.map(t => `
        <div class="tender-mini-item" onclick="App.openTenderDetail(${t.id})">
          <div style="flex:1">
            <div class="tender-mini-title">${t.title}</div>
            <div class="tender-mini-meta">${t.issuing_body || ''} ${t.closing_date ? '• Closes ' + this.formatDate(t.closing_date) : ''}</div>
          </div>
          <span class="status-badge status-${t.status}">${t.status}</span>
        </div>`).join('')
      : '<div class="empty-state"><p>No tenders yet. Add your first tender!</p></div>';

    this.renderNotifications(notifs, 'recentNotifications');
    this.updateNotifBadge(notifs.unread_count);
  },

  // Tenders
  async loadTenders(page = 1) {
    currentPage = page;
    const search = document.getElementById('tenderSearch')?.value || '';
    const data = await this.api(`/tenders?page=${page}&per_page=15&status=${currentStatus}&search=${encodeURIComponent(search)}`);
    this.renderTenders(data);
  },

  renderTenders(data) {
    const el = document.getElementById('tendersList');
    if (!data.tenders?.length) {
      el.innerHTML = '<div class="empty-state"><h3>No tenders found</h3><p>Add a tender or configure sources to start tracking.</p></div>';
      document.getElementById('tendersFooter').innerHTML = '';
      return;
    }
    el.innerHTML = data.tenders.map(t => this.tenderCard(t)).join('');
    this.renderPagination(data);
  },

  tenderCard(t) {
    const daysLeft = t.days_until_closing;
    const urgentBadge = (daysLeft !== null && daysLeft <= 7 && daysLeft >= 0)
      ? `<span class="urgent-badge">⏰ ${daysLeft}d left</span>` : '';
    return `
    <div class="tender-card ${!t.is_read ? 'unread' : ''}" onclick="App.openTenderDetail(${t.id})">
      <div class="tender-card-header">
        <div class="tender-card-title">${t.title}</div>
        <div style="display:flex;gap:0.4rem;align-items:center;flex-shrink:0">
          ${urgentBadge}
          <span class="status-badge status-${t.status}">${t.status}</span>
        </div>
      </div>
      ${t.description ? `<div class="tender-card-desc">${t.description}</div>` : ''}
      <div class="tender-card-body">
        ${t.issuing_body ? `<span class="tender-card-meta">🏢 ${t.issuing_body}</span>` : ''}
        ${t.value ? `<span class="tender-card-meta">💰 ${t.value}</span>` : ''}
        ${t.closing_date ? `<span class="tender-card-meta ${daysLeft !== null && daysLeft <= 7 ? 'closing-soon' : ''}">📅 ${this.formatDate(t.closing_date)}</span>` : ''}
        ${t.reference_number ? `<span class="tender-card-meta">🔢 ${t.reference_number}</span>` : ''}
        ${t.document_count > 0 ? `<span class="tender-card-meta">📎 ${t.document_count} docs</span>` : ''}
        <div class="tender-card-actions" onclick="event.stopPropagation()">
          <button class="btn btn-sm btn-secondary" onclick="App.editTender(${t.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="App.deleteTender(${t.id})">Delete</button>
        </div>
      </div>
    </div>`;
  },

  renderPagination(data) {
    const el = document.getElementById('tendersFooter');
    if (data.pages <= 1) { el.innerHTML = ''; return; }
    let html = '';
    for (let i = 1; i <= data.pages; i++) {
      html += `<button class="page-btn ${i === data.page ? 'active' : ''}" onclick="App.loadTenders(${i})">${i}</button>`;
    }
    el.innerHTML = html;
  },

  debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => this.loadTenders(1), 400);
  },

  // Tender CRUD
  openAddTenderModal(prefill = {}) {
    currentTenderId = null;
    document.getElementById('tenderModalTitle').textContent = 'Add Tender';
    ['title','ref','issuer','category','value','url','desc','notes'].forEach(f => {
      const el = document.getElementById('tf-' + f);
      if (el) el.value = prefill[f] || '';
    });
    document.getElementById('tf-status').value = prefill.status || 'new';
    if (prefill.closing_date) document.getElementById('tf-closing').value = prefill.closing_date.slice(0,16);
    if (prefill.published_date) document.getElementById('tf-published').value = prefill.published_date.slice(0,16);
    this.openModal('tenderModal');
  },

  async editTender(id) {
    const t = await this.api(`/tenders/${id}`);
    currentTenderId = id;
    document.getElementById('tenderModalTitle').textContent = 'Edit Tender';
    document.getElementById('tf-title').value = t.title || '';
    document.getElementById('tf-ref').value = t.reference_number || '';
    document.getElementById('tf-issuer').value = t.issuing_body || '';
    document.getElementById('tf-category').value = t.category || '';
    document.getElementById('tf-value').value = t.value || '';
    document.getElementById('tf-url').value = t.source_url || '';
    document.getElementById('tf-desc').value = t.description || '';
    document.getElementById('tf-notes').value = t.notes || '';
    document.getElementById('tf-status').value = t.status || 'new';
    if (t.closing_date) document.getElementById('tf-closing').value = t.closing_date.slice(0,16);
    if (t.published_date) document.getElementById('tf-published').value = t.published_date.slice(0,16);
    this.openModal('tenderModal');
  },

  async saveTender() {
    const title = document.getElementById('tf-title').value.trim();
    if (!title) { this.toast('Title is required', 'error'); return; }
    const body = {
      title,
      reference_number: document.getElementById('tf-ref').value,
      issuing_body: document.getElementById('tf-issuer').value,
      category: document.getElementById('tf-category').value,
      value: document.getElementById('tf-value').value,
      source_url: document.getElementById('tf-url').value,
      description: document.getElementById('tf-desc').value,
      notes: document.getElementById('tf-notes').value,
      status: document.getElementById('tf-status').value,
      closing_date: document.getElementById('tf-closing').value || null,
      published_date: document.getElementById('tf-published').value || null,
    };
    if (currentTenderId) {
      await this.api(`/tenders/${currentTenderId}`, 'PUT', body);
      this.toast('Tender updated', 'success');
    } else {
      await this.api('/tenders', 'POST', body);
      this.toast('Tender added', 'success');
    }
    this.closeModal();
    this.loadTenders();
  },

  async deleteTender(id) {
    if (!confirm('Delete this tender?')) return;
    await this.api(`/tenders/${id}`, 'DELETE');
    this.toast('Tender deleted', 'info');
    this.loadTenders();
  },

  // Tender Detail
  async openTenderDetail(id) {
    currentTenderId = id;
    const t = await this.api(`/tenders/${id}`);
    if (!t.is_read) {
      this.api(`/tenders/${id}`, 'PUT', { is_read: true });
    }
    document.getElementById('detailTitle').textContent = t.title;
    document.getElementById('detailMeta').innerHTML = `
      <span class="status-badge status-${t.status}">${t.status}</span>
      ${t.reference_number ? `<span class="tender-card-meta">📋 ${t.reference_number}</span>` : ''}
      ${t.closing_date ? `<span class="tender-card-meta">📅 Closes ${this.formatDate(t.closing_date)}</span>` : ''}
    `;

    // Overview tab
    document.getElementById('detailOverview').innerHTML = `
      <div class="detail-overview-grid">
        ${t.issuing_body ? `<div class="detail-field"><div class="detail-field-label">Issuing Body</div><div class="detail-field-value">${t.issuing_body}</div></div>` : ''}
        ${t.category ? `<div class="detail-field"><div class="detail-field-label">Category</div><div class="detail-field-value">${t.category}</div></div>` : ''}
        ${t.value ? `<div class="detail-field"><div class="detail-field-label">Value</div><div class="detail-field-value">${t.value}</div></div>` : ''}
        ${t.published_date ? `<div class="detail-field"><div class="detail-field-label">Published</div><div class="detail-field-value">${this.formatDate(t.published_date)}</div></div>` : ''}
        ${t.closing_date ? `<div class="detail-field"><div class="detail-field-label">Closing Date</div><div class="detail-field-value ${t.days_until_closing !== null && t.days_until_closing <= 7 ? 'closing-soon' : ''}">${this.formatDate(t.closing_date)}</div></div>` : ''}
        ${t.source_url ? `<div class="detail-field"><div class="detail-field-label">Source</div><div class="detail-field-value"><a href="${t.source_url}" target="_blank" class="link-btn">View Original</a></div></div>` : ''}
      </div>
      ${t.description ? `<div class="detail-description">${t.description}</div>` : ''}
      ${t.notes ? `<div class="detail-notes"><h4>Notes</h4><p>${t.notes}</p></div>` : ''}
    `;

    // Documents tab
    document.getElementById('detailDocuments').innerHTML = t.documents?.length
      ? t.documents.map(d => this.docCardMini(d)).join('')
      : '<p style="color:var(--text-muted);font-size:0.9rem">No documents yet.</p>';

    // Submissions tab
    document.getElementById('detailSubmissions').innerHTML = t.submissions?.length
      ? t.submissions.map(s => `
        <div class="pipeline-card" onclick="App.editSubmission(${s.id})">
          <div class="pipeline-card-title">${s.title}</div>
          <div class="pipeline-card-value">${s.bid_value || ''}</div>
          <span class="status-badge status-${s.status}">${s.status}</span>
        </div>`).join('')
      : '<p style="color:var(--text-muted);font-size:0.9rem">No submissions yet.</p>';

    document.getElementById('detailAI').innerHTML = '<p style="color:var(--text-muted);font-size:0.9rem">Click "Generate AI Analysis" to analyze this tender.</p>';

    // Reset tabs
    document.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.detail-tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector('.detail-tab[data-tab="overview"]').classList.add('active');
    document.getElementById('detailTab-overview').classList.add('active');

    this.openModal('tenderDetailModal');
  },

  docCardMini(d) {
    return `<div class="pipeline-card" onclick="App.openDocEditor(${d.id})">
      <div class="pipeline-card-title">${d.name}</div>
      <div class="pipeline-card-tender">${d.doc_type} ${d.has_file ? '• Has file' : ''}</div>
      ${d.ai_summary ? `<div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.4rem">${d.ai_summary.slice(0,100)}...</div>` : ''}
    </div>`;
  },

  editCurrentTender() {
    this.closeModal();
    this.editTender(currentTenderId);
  },

  async analyzeTender() {
    const el = document.getElementById('detailAI');
    el.innerHTML = '<div class="loading"><div class="spinner"></div>Analyzing with AI...</div>';
    const res = await this.api(`/ai/analyze-tender/${currentTenderId}`, 'POST');
    el.innerHTML = res.summary ? `<div class="ai-analysis-content">${res.summary}</div>` : `<p class="error">${res.error || 'Analysis failed'}</p>`;
  },

  // Extract from text
  openExtractModal() {
    document.getElementById('extractText').value = '';
    document.getElementById('extractResult').style.display = 'none';
    document.getElementById('saveExtractedBtn').style.display = 'none';
    this._extractedData = null;
    this.openModal('extractModal');
  },

  async extractTender() {
    const text = document.getElementById('extractText').value.trim();
    if (!text) { this.toast('Please paste tender text first', 'error'); return; }
    document.getElementById('extractBtn').textContent = 'Extracting...';
    document.getElementById('extractBtn').disabled = true;
    const data = await this.api('/ai/extract-tender', 'POST', { text });
    document.getElementById('extractBtn').textContent = 'Extract with AI';
    document.getElementById('extractBtn').disabled = false;

    if (data.error) { this.toast(data.error, 'error'); return; }
    this._extractedData = data;
    const resultEl = document.getElementById('extractResult');
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<strong>Extracted Information:</strong><br>` +
      Object.entries(data).filter(([k, v]) => v && k !== 'key_requirements' && k !== 'evaluation_criteria' && k !== 'eligibility_criteria')
        .map(([k, v]) => `<div class="field"><span class="field-label">${k.replace(/_/g, ' ')}:</span><span>${Array.isArray(v) ? v.join(', ') : v}</span></div>`)
        .join('');
    document.getElementById('saveExtractedBtn').style.display = 'block';
  },

  saveExtractedTender() {
    const d = this._extractedData;
    if (!d) return;
    this.closeModal();
    this.openAddTenderModal({
      title: d.title || 'Extracted Tender',
      ref: d.reference_number || '',
      issuer: d.issuing_body || '',
      category: d.category || '',
      value: d.value || '',
      desc: d.description || '',
      closing_date: d.closing_date || null,
      published_date: d.published_date || null,
    });
  },

  // Documents
  async loadDocuments() {
    const docs = await this.api('/documents');
    const el = document.getElementById('documentsList');
    if (!docs.length) {
      el.innerHTML = '<div class="empty-state"><h3>No documents yet</h3><p>Upload files or create AI-generated documents.</p></div>';
      return;
    }
    el.innerHTML = docs.map(d => `
      <div class="doc-card">
        <div class="doc-card-header">
          <div class="doc-card-title">${d.name}</div>
          <span class="doc-type-badge">${d.doc_type}</span>
        </div>
        ${d.ai_summary ? `<div class="doc-card-summary">${d.ai_summary}</div>` : d.content ? `<div class="doc-card-summary">${d.content.slice(0,150)}...</div>` : ''}
        <div class="doc-card-footer">
          <span class="doc-card-meta">${this.formatDate(d.created_at)}</span>
          <button class="btn btn-sm btn-secondary" onclick="App.openDocEditor(${d.id})">Edit</button>
          <button class="btn btn-sm btn-secondary" onclick="App.downloadDocById(${d.id}, 'docx')">DOCX</button>
          <button class="btn btn-sm btn-secondary" onclick="App.downloadDocById(${d.id}, 'pdf')">PDF</button>
          <button class="btn btn-sm btn-danger" onclick="App.deleteDocument(${d.id})">Del</button>
        </div>
      </div>`).join('');
  },

  openNewDocModal() {
    currentDocId = null;
    document.getElementById('docEditorName').value = '';
    document.getElementById('docEditorContent').value = '';
    document.getElementById('docEditorPreview').innerHTML = '';
    document.getElementById('docEditorImproveInput').value = '';
    this.openModal('docEditorModal');
  },

  async openDocEditor(id) {
    const doc = await this.api(`/documents/${id}`);
    currentDocId = id;
    document.getElementById('docEditorName').value = doc.name;
    document.getElementById('docEditorContent').value = doc.content || '';
    this.renderMarkdown(doc.content || '', 'docEditorPreview');
    document.getElementById('docEditorImproveInput').value = '';
    this.openModal('docEditorModal');
  },

  async saveDocEditor() {
    const name = document.getElementById('docEditorName').value.trim();
    const content = document.getElementById('docEditorContent').value;
    if (!name) { this.toast('Document name required', 'error'); return; }
    if (currentDocId) {
      await this.api(`/documents/${currentDocId}`, 'PUT', { name, content });
      this.toast('Document saved', 'success');
    } else {
      const doc = await this.api('/documents', 'POST', { name, content });
      currentDocId = doc.id;
      this.toast('Document created', 'success');
    }
    this.loadDocuments();
  },

  async improveDocument() {
    const instruction = document.getElementById('docEditorImproveInput').value.trim();
    if (!instruction) { this.toast('Enter improvement instruction', 'error'); return; }
    if (!currentDocId) {
      this.toast('Save the document first', 'error'); return;
    }
    this.toast('Improving document with AI...', 'info');
    const res = await this.api(`/ai/improve-document/${currentDocId}`, 'POST', { instruction });
    if (res.content) {
      document.getElementById('docEditorContent').value = res.content;
      this.renderMarkdown(res.content, 'docEditorPreview');
      this.toast('Document improved!', 'success');
    } else if (res.error) {
      this.toast(res.error, 'error');
    }
  },

  downloadCurrentDoc(fmt) {
    if (currentDocId) {
      window.open(`/api/documents/${currentDocId}/download?format=${fmt}`, '_blank');
    }
  },

  downloadDocById(id, fmt) {
    window.open(`/api/documents/${id}/download?format=${fmt}`, '_blank');
  },

  async deleteDocument(id) {
    if (!confirm('Delete this document?')) return;
    await this.api(`/documents/${id}`, 'DELETE');
    this.toast('Document deleted', 'info');
    this.loadDocuments();
  },

  // Upload
  openUploadModal(tenderId = null) {
    document.getElementById('fileInput').value = '';
    document.getElementById('uploadFileInfo').style.display = 'none';
    this._uploadFile = null;
    this.openModal('uploadModal');
    this.loadTenderSelectForUpload(tenderId);
  },

  openUploadToCurrentTender() {
    this.closeModal();
    setTimeout(() => this.openUploadModal(currentTenderId), 100);
  },

  async loadTenderSelectForUpload(selectedId = null) {
    const data = await this.api('/tenders?per_page=100');
    const sel = document.getElementById('uploadTenderSelect');
    sel.innerHTML = '<option value="">No tender</option>' +
      (data.tenders || []).map(t => `<option value="${t.id}" ${t.id == selectedId ? 'selected' : ''}>${t.title.slice(0,60)}</option>`).join('');
  },

  handleFileSelect(input) {
    const file = input.files[0];
    if (!file) return;
    this._uploadFile = file;
    const info = document.getElementById('uploadFileInfo');
    info.style.display = 'flex';
    info.innerHTML = `📎 ${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
  },

  async uploadFile() {
    if (!this._uploadFile) { this.toast('Please select a file', 'error'); return; }
    const formData = new FormData();
    formData.append('file', this._uploadFile);
    const tenderId = document.getElementById('uploadTenderSelect').value;
    if (tenderId) formData.append('tender_id', tenderId);
    formData.append('doc_type', document.getElementById('uploadDocType').value);
    formData.append('analyze', document.getElementById('uploadAnalyze').checked ? 'true' : 'false');

    document.getElementById('uploadBtn').textContent = 'Uploading...';
    document.getElementById('uploadBtn').disabled = true;

    try {
      const resp = await fetch('/api/documents/upload', { method: 'POST', body: formData });
      const data = await resp.json();
      document.getElementById('uploadBtn').textContent = 'Upload & Analyze';
      document.getElementById('uploadBtn').disabled = false;
      if (data.error) { this.toast(data.error, 'error'); return; }
      this.toast('File uploaded successfully!', 'success');
      this.closeModal();
      this.loadDocuments();
    } catch (e) {
      document.getElementById('uploadBtn').textContent = 'Upload & Analyze';
      document.getElementById('uploadBtn').disabled = false;
      this.toast('Upload failed', 'error');
    }
  },

  // AI Writer
  async loadWriterTenders() {
    const data = await this.api('/tenders?per_page=100');
    const sel = document.getElementById('writerTenderSelect');
    sel.innerHTML = '<option value="">No tender context</option>' +
      (data.tenders || []).map(t => `<option value="${t.id}">${t.title.slice(0,50)}</option>`).join('');
  },

  setPrompt(text) {
    document.getElementById('chatInput').value = text;
    document.getElementById('chatInput').focus();
  },

  async sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    const tenderId = document.getElementById('writerTenderSelect').value;
    chatHistory.push({ role: 'user', content: msg });
    this.renderChatMessage('user', msg);

    document.getElementById('sendBtn').disabled = true;
    const typing = document.createElement('div');
    typing.className = 'chat-msg ai';
    typing.id = 'typing';
    typing.innerHTML = `<div class="chat-msg-avatar">AI</div><div class="chat-msg-content">Thinking...</div>`;
    document.getElementById('chatMessages').appendChild(typing);
    this.scrollChat();

    const res = await this.api('/ai/chat', 'POST', {
      messages: chatHistory,
      tender_id: tenderId ? parseInt(tenderId) : null
    });

    document.getElementById('typing')?.remove();
    document.getElementById('sendBtn').disabled = false;

    if (res.response) {
      chatHistory.push({ role: 'assistant', content: res.response });
      this.renderChatMessage('ai', res.response);
      currentPreviewContent = res.response;
      this.renderMarkdown(res.response, 'docPreviewContent');
    } else {
      this.renderChatMessage('ai', res.error || 'Something went wrong. Check your API key.');
    }
    this.scrollChat();
  },

  renderChatMessage(role, content) {
    const el = document.createElement('div');
    el.className = `chat-msg ${role}`;
    const formattedContent = this.formatChatContent(content);
    el.innerHTML = `
      <div class="chat-msg-avatar">${role === 'ai' ? 'AI' : 'You'}</div>
      <div class="chat-msg-content">${formattedContent}</div>`;
    const chatMessages = document.getElementById('chatMessages');
    const welcome = chatMessages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
    chatMessages.appendChild(el);
  },

  formatChatContent(text) {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  },

  scrollChat() {
    const el = document.getElementById('chatMessages');
    el.scrollTop = el.scrollHeight;
  },

  saveAIDocument() {
    const name = document.getElementById('docPreviewName').value.trim();
    const content = currentPreviewContent;
    if (!name) { this.toast('Enter a document name first', 'error'); return; }
    if (!content) { this.toast('No content to save', 'error'); return; }
    const tenderId = document.getElementById('writerTenderSelect').value;
    this.api('/documents', 'POST', {
      name, content,
      tender_id: tenderId ? parseInt(tenderId) : null,
      doc_type: document.getElementById('docTypeSelect').value
    }).then(() => this.toast('Document saved!', 'success'));
  },

  downloadDoc(fmt) {
    if (!currentPreviewContent) { this.toast('No content to download', 'error'); return; }
    const name = document.getElementById('docPreviewName').value || 'document';
    const blob = new Blob([currentPreviewContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = `/api/documents/0/download?format=${fmt}`;
    this.toast('Save the document first to download', 'info');
  },

  openAIWriteForCurrentTender() {
    this.closeModal();
    this.showPage('ai-writer');
    setTimeout(() => {
      const sel = document.getElementById('writerTenderSelect');
      if (currentTenderId) sel.value = currentTenderId;
    }, 100);
  },

  // Pipeline
  async loadPipeline() {
    const data = await this.api('/submissions/pipeline');
    const statuses = ['draft', 'review', 'submitted', 'won', 'lost'];
    for (const status of statuses) {
      const items = data[status] || [];
      document.getElementById(`count-${status}`).textContent = items.length;
      const el = document.getElementById(`col-${status}`);
      if (!items.length) {
        el.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--text-muted);font-size:0.85rem">No submissions</div>';
        continue;
      }
      el.innerHTML = items.map(s => `
        <div class="pipeline-card">
          <div class="pipeline-card-title">${s.title}</div>
          ${s.bid_value ? `<div class="pipeline-card-value">${s.bid_value}</div>` : ''}
          ${s.lead_contact ? `<div class="pipeline-card-tender">👤 ${s.lead_contact}</div>` : ''}
          <div class="pipeline-card-actions">
            <button class="btn btn-sm btn-secondary" onclick="App.editSubmission(${s.id})">Edit</button>
            <button class="btn btn-sm btn-danger" onclick="App.deleteSubmission(${s.id})">Del</button>
          </div>
        </div>`).join('');
    }
  },

  async openAddSubmissionModal(tenderId = null) {
    currentSubmissionId = null;
    document.getElementById('submissionModalTitle').textContent = 'New Submission';
    ['title','value','lead','team','notes'].forEach(f => {
      document.getElementById('subf-' + f).value = '';
    });
    document.getElementById('subf-status').value = 'draft';
    await this.loadTenderSelectForSubmission(tenderId);
    this.openModal('submissionModal');
  },

  openAddSubmissionFromDetail() {
    this.closeModal();
    setTimeout(() => this.openAddSubmissionModal(currentTenderId), 100);
  },

  async loadTenderSelectForSubmission(selectedId = null) {
    const data = await this.api('/tenders?per_page=100');
    const sel = document.getElementById('subf-tender');
    sel.innerHTML = (data.tenders || []).map(t =>
      `<option value="${t.id}" ${t.id == selectedId ? 'selected' : ''}>${t.title.slice(0,60)}</option>`
    ).join('');
  },

  async editSubmission(id) {
    const s = await this.api(`/submissions/${id}`);
    currentSubmissionId = id;
    document.getElementById('submissionModalTitle').textContent = 'Edit Submission';
    document.getElementById('subf-title').value = s.title;
    document.getElementById('subf-status').value = s.status;
    document.getElementById('subf-value').value = s.bid_value || '';
    document.getElementById('subf-lead').value = s.lead_contact || '';
    document.getElementById('subf-team').value = s.team_members || '';
    document.getElementById('subf-notes').value = s.notes || '';
    await this.loadTenderSelectForSubmission(s.tender_id);
    this.openModal('submissionModal');
  },

  async saveSubmission() {
    const title = document.getElementById('subf-title').value.trim();
    if (!title) { this.toast('Title required', 'error'); return; }
    const body = {
      title,
      tender_id: parseInt(document.getElementById('subf-tender').value),
      status: document.getElementById('subf-status').value,
      bid_value: document.getElementById('subf-value').value,
      lead_contact: document.getElementById('subf-lead').value,
      team_members: document.getElementById('subf-team').value,
      notes: document.getElementById('subf-notes').value,
    };
    if (currentSubmissionId) {
      await this.api(`/submissions/${currentSubmissionId}`, 'PUT', body);
      this.toast('Submission updated', 'success');
    } else {
      await this.api('/submissions', 'POST', body);
      this.toast('Submission created', 'success');
    }
    this.closeModal();
    this.loadPipeline();
  },

  async deleteSubmission(id) {
    if (!confirm('Delete this submission?')) return;
    await this.api(`/submissions/${id}`, 'DELETE');
    this.toast('Submission deleted', 'info');
    this.loadPipeline();
  },

  // Sources
  async loadSources() {
    const sources = await this.api('/sources');
    const el = document.getElementById('sourcesList');
    if (!sources.length) {
      el.innerHTML = '<div class="empty-state"><h3>No sources configured</h3><p>Add RSS feeds or websites to monitor for new tenders.</p></div>';
      return;
    }
    el.innerHTML = sources.map(s => `
      <div class="source-card">
        <div class="source-status ${s.is_active ? 'active' : 'inactive'}"></div>
        <div class="source-info">
          <div class="source-name">${s.name}</div>
          <div class="source-url">${s.url}</div>
          <div class="source-meta">${s.source_type.toUpperCase()} · Check every ${s.check_interval_hours}h · Last checked: ${s.last_checked ? this.timeAgo(s.last_checked) : 'Never'}</div>
          ${s.keywords ? `<div class="source-meta">Keywords: ${s.keywords}</div>` : ''}
        </div>
        <div class="source-actions">
          <button class="btn btn-sm btn-secondary" onclick="App.checkSource(${s.id})">Check Now</button>
          <button class="btn btn-sm btn-secondary" onclick="App.editSource(${s.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="App.deleteSource(${s.id})">Del</button>
        </div>
      </div>`).join('');
  },

  openAddSourceModal() {
    currentSourceId = null;
    document.getElementById('sourceModalTitle').textContent = 'Add Source';
    ['name','url','keywords'].forEach(f => document.getElementById('sf-' + f).value = '');
    document.getElementById('sf-type').value = 'rss';
    document.getElementById('sf-interval').value = '24';
    this.openModal('sourceModal');
  },

  async editSource(id) {
    const s = await this.api(`/sources`);
    const source = s.find(x => x.id === id);
    if (!source) return;
    currentSourceId = id;
    document.getElementById('sourceModalTitle').textContent = 'Edit Source';
    document.getElementById('sf-name').value = source.name;
    document.getElementById('sf-url').value = source.url;
    document.getElementById('sf-type').value = source.source_type;
    document.getElementById('sf-keywords').value = source.keywords || '';
    document.getElementById('sf-interval').value = source.check_interval_hours;
    this.openModal('sourceModal');
  },

  async saveSource() {
    const name = document.getElementById('sf-name').value.trim();
    const url = document.getElementById('sf-url').value.trim();
    if (!name || !url) { this.toast('Name and URL required', 'error'); return; }
    const body = {
      name, url,
      source_type: document.getElementById('sf-type').value,
      keywords: document.getElementById('sf-keywords').value,
      check_interval_hours: parseInt(document.getElementById('sf-interval').value),
    };
    if (currentSourceId) {
      await this.api(`/sources/${currentSourceId}`, 'PUT', body);
      this.toast('Source updated', 'success');
    } else {
      await this.api('/sources', 'POST', body);
      this.toast('Source added', 'success');
    }
    this.closeModal();
    this.loadSources();
  },

  async deleteSource(id) {
    if (!confirm('Delete this source?')) return;
    await this.api(`/sources/${id}`, 'DELETE');
    this.toast('Source deleted', 'info');
    this.loadSources();
  },

  async checkSource(id) {
    this.toast('Checking source for new tenders...', 'info');
    const res = await this.api(`/sources/${id}/check`, 'POST');
    this.toast(`Found ${res.count} new tender(s)`, res.count > 0 ? 'success' : 'info');
    this.loadSources();
    if (res.count > 0) this.loadTenders();
  },

  async checkAllSources() {
    this.toast('Checking all sources...', 'info');
    const res = await this.api('/sources/check-all', 'POST');
    this.toast(`Found ${res.total_added} new tender(s)`, res.total_added > 0 ? 'success' : 'info');
    this.loadSources();
  },

  // Notifications
  async loadNotifications() {
    const data = await this.api('/notifications?limit=30');
    this.renderNotifications(data, 'notifPanelList');
    this.updateNotifBadge(data.unread_count);
  },

  renderNotifications(data, containerId) {
    const el = document.getElementById(containerId);
    const notifs = data.notifications || [];
    if (!notifs.length) {
      el.innerHTML = '<p style="text-align:center;padding:1rem;color:var(--text-muted);font-size:0.85rem">No notifications</p>';
      return;
    }
    el.innerHTML = notifs.map(n => `
      <div class="notif-item ${!n.is_read ? 'unread' : ''}" onclick="App.handleNotifClick(${n.tender_id}, ${n.id})">
        <div class="notif-dot-sm ${n.notification_type}"></div>
        <div style="flex:1"><div>${n.message}</div></div>
        <span class="notif-time">${this.timeAgo(n.created_at)}</span>
      </div>`).join('');
  },

  async handleNotifClick(tenderId, notifId) {
    await this.api(`/notifications/${notifId}/read`, 'POST');
    if (tenderId) {
      this.closeNotifPanel();
      this.showPage('tenders');
      setTimeout(() => this.openTenderDetail(tenderId), 200);
    }
  },

  async markAllNotifRead() {
    await this.api('/notifications/mark-read', 'POST');
    this.updateNotifBadge(0);
    this.loadNotifications();
    this.toast('All notifications marked as read', 'info');
  },

  updateNotifBadge(count) {
    const badge = document.getElementById('notifBadge');
    const dot = document.getElementById('notifDot');
    const unreadBadge = document.getElementById('unreadBadge');
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline' : 'none';
    dot.style.display = count > 0 ? 'block' : 'none';
    if (unreadBadge) {
      unreadBadge.textContent = count;
      unreadBadge.style.display = count > 0 ? 'inline' : 'none';
    }
  },

  openNotifPanel() {
    document.getElementById('notifPanel').classList.add('open');
    document.getElementById('notifPanelOverlay').classList.add('active');
    this.loadNotifications();
  },

  closeNotifPanel() {
    document.getElementById('notifPanel').classList.remove('open');
    document.getElementById('notifPanelOverlay').classList.remove('active');
  },

  // Modals
  openModal(id) {
    document.getElementById('modalOverlay').classList.add('active');
    document.getElementById(id).classList.add('active');
  },

  closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
  },

  // API helper
  async api(path, method = 'GET', body = null) {
    const opts = { method, headers: {} };
    if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    try {
      const res = await fetch(API + path, opts);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  },

  // Toast
  toast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    el.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${msg}</span>`;
    document.getElementById('toastContainer').appendChild(el);
    setTimeout(() => el.remove(), 4000);
  },

  // Markdown renderer
  renderMarkdown(text, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    let html = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^- (.*$)/gm, '<li>$1</li>')
      .replace(/^(\d+)\. (.*$)/gm, '<li>$1. $2</li>')
      .replace(/(<li>.*<\/li>\n?)+/g, s => `<ul>${s}</ul>`)
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
    el.innerHTML = `<div class="markdown-preview">${html}</div>`;
  },

  // Date helpers
  formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return dateStr; }
  },

  timeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = Math.floor((new Date() - new Date(dateStr)) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return `${Math.floor(diff/86400)}d ago`;
  },

  init() {
    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        this.showPage(link.dataset.page);
      });
    });

    // Status filter
    document.getElementById('statusFilter')?.addEventListener('click', e => {
      const tab = e.target.closest('.filter-tab');
      if (!tab) return;
      document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentStatus = tab.dataset.status;
      this.loadTenders(1);
    });

    // Sidebar toggle
    document.getElementById('sidebarToggle')?.addEventListener('click', () => {
      document.getElementById('sidebar').classList.toggle('collapsed');
    });

    // Notification button
    document.getElementById('notifBtn')?.addEventListener('click', () => this.openNotifPanel());

    // Detail tabs
    document.querySelectorAll('.detail-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.detail-tab-content').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`detailTab-${tab.dataset.tab}`)?.classList.add('active');
      });
    });

    // Enter key for chat
    document.getElementById('chatInput')?.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendChat();
      }
    });

    // Doc editor live preview
    document.getElementById('docEditorContent')?.addEventListener('input', e => {
      this.renderMarkdown(e.target.value, 'docEditorPreview');
    });

    // Load initial page
    this.showPage('dashboard');

    // Poll for notifications every 30s
    setInterval(() => {
      this.api('/notifications?limit=1&unread_only=true').then(data => {
        this.updateNotifBadge(data.unread_count || 0);
      });
    }, 30000);
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
