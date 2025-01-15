class TableManager {
    constructor(tableId, options = {}) {
        this.tableId = tableId;
        this.pageSize = options.pageSize || 10;
        this.currentPage = 1;
        this.init();
    }

    init() {
        this.table = document.getElementById(this.tableId);
        this.pagination = document.getElementById(`${this.tableId}Pagination`);
        this.pageSizeBox = document.getElementById(`${this.tableId}_pageSize`);
        this.updatePagination();
        this.attachEventListeners();
    }

    updatePagination() {
        const rows = Array.from(this.table.querySelector('tbody').rows);
        const pageCount = Math.ceil(rows.length / this.pageSize);
        
        // Sort rows by date in descending order
        rows.sort((a, b) => new Date(b.cells[0].textContent) - new Date(a.cells[0].textContent));

        rows.forEach((row, index) => {
            row.style.display = 
                (Math.floor(index / this.pageSize) + 1 === this.currentPage) 
                ? '' 
                : 'none';
        });

        this.pagination.innerHTML = this.generatePaginationHTML(pageCount);
    }

    generatePaginationHTML(pageCount) {
        let html = '';
        for(let i = 1; i <= pageCount; i++) {
            html += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>`;
        }
        return html;
    }

    attachEventListeners() {
        if (this.pageSizeBox) {
            this.pageSizeBox.addEventListener('change', (e) => {
                this.pageSize = parseInt(e.target.value);
                this.currentPage = 1;
                this.updatePagination();
            });
        }

        this.pagination.addEventListener('click', (e) => {
            if(e.target.tagName === 'A') {
                e.preventDefault();
                this.currentPage = parseInt(e.target.dataset.page);
                this.updatePagination();
            }
        });

        if (this.tableId === 'logTable') {
            document.getElementById('logTypeFilter').addEventListener('change', () => this.filterLogs());
            document.getElementById('logDateFilter').addEventListener('change', () => this.filterLogs());
        }
    }

    filterLogs() {
        const typeFilter = document.getElementById('logTypeFilter').value;
        const dateFilter = document.getElementById('logDateFilter').value;
        const rows = Array.from(this.table.querySelector('tbody').rows);

        rows.forEach(row => {
            const type = row.cells[1].textContent;
            const date = row.cells[0].textContent.split(' ')[0];
            const matchesType = !typeFilter || type === typeFilter;
            const matchesDate = !dateFilter || date === dateFilter;

            row.style.display = matchesType && matchesDate ? '' : 'none';
        });

        this.updatePagination();
    }
}

// Initialize table managers
document.addEventListener('DOMContentLoaded', function() {
    new TableManager('webhookTable', { pageSize: 10 });
    new TableManager('positionTable', { pageSize: 10 });
    new TableManager('closedPositionTable', { pageSize: 10 });
    new TableManager('logTable', { pageSize: 10 });
});

// WebSocket connection
const socket = io();

// Real-time updates
socket.on('update', function(data) {
    toastr.success(`Webhook ${data.id} status: ${data.status}`);
    location.reload();
});

socket.on('webhook_received', function(data) {
    toastr.success(`New webhook received: ${data.webhook_id}`);
    setTimeout(() => {
        location.reload();
    }, 1000); // Delay to ensure toast is visible before reload
});

socket.on('price_update', function(data) {
    Object.entries(data.prices).forEach(([symbol, priceData]) => {
        document.querySelectorAll(`tr[id^="position-"]`).forEach(row => {
            if (row.cells[0].textContent === symbol) {
                const currentPrice = row.querySelector('.current-price');
                const pl = row.querySelector('.position-pl');
                const rrElement = row.querySelector('.position-rr');
                const type = row.cells[1].textContent;
                const price = type.toLowerCase().includes('buy') ? priceData.bid : priceData.ask;
                
                currentPrice.innerHTML = `${price} <span class="badge ${priceData.change >= 0 ? 'bg-success' : 'bg-danger'}">${priceData.change >= 0 ? '▲' : '▼'}</span>`;
                
                // Calculate P/L
                const entry = parseFloat(row.cells[3].textContent);
                const volume = parseFloat(row.cells[2].textContent);
                const profit = type.toLowerCase().includes('buy') 
                    ? (price - entry) * volume * 100000
                    : (entry - price) * volume * 100000;
                
                pl.textContent = profit.toFixed(2);
                pl.className = `position-pl ${profit >= 0 ? 'text-success' : 'text-danger'}`;

                // Calculate R/R
                const sl = parseFloat(row.cells[5].textContent);
                const tp = parseFloat(row.cells[6].textContent);
                const rrValue = ((tp - entry) / (entry - sl)).toFixed(2);
                rrElement.textContent = rrValue;
            }
        });
    });
});

// View Webhook Details
function viewWebhookDetails(webhookId) {
    fetch(`/api/webhook/${webhookId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('webhookRequest').textContent = JSON.stringify(data, null, 2);
            document.getElementById('mt5Response').textContent = data.error_message || "Success";
            new bootstrap.Modal(document.getElementById('webhookDetailModal')).show();
        })
        .catch(error => console.error('Error:', error));
}