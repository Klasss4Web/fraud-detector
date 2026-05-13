"""
Observability Dashboard with interactive plots for monitoring LLM usage and metrics.
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/plots", response_class=HTMLResponse)
def get_observability_plots():
    """
    Get the observability dashboard with interactive plots.

    Includes:
    - Request volume over time
    - Error rates
    - Latency distribution
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Observability Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }
            h1 { color: #1a1a2e; margin-bottom: 20px; }
            .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
            .plot-container { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .plot-container h2 { margin-top: 0; color: #333; font-size: 1.1em; }
            .chart-wrapper { height: 250px; }
            .loading { text-align: center; padding: 40px; color: #666; }
        </style>
    </head>
    <body>
        <h1>Observability Dashboard</h1>
        <div class="dashboard">
            <div class="plot-container">
                <h2>Request Volume (24h)</h2>
                <div class="chart-wrapper"><canvas id="requestChart"></canvas></div>
            </div>
            <div class="plot-container">
                <h2>Error Rate</h2>
                <div class="chart-wrapper"><canvas id="errorChart"></canvas></div>
            </div>
            <div class="plot-container">
                <h2>Latency Distribution</h2>
                <div class="chart-wrapper"><canvas id="latencyChart"></canvas></div>
            </div>
        </div>
        <script>
            // Sample data - in production, fetch from /api/v1/observability/metrics
            const hours = Array.from({length: 24}, (_, i) => `${i}:00`);
            
            new Chart(document.getElementById('requestChart'), {
                type: 'line',
                data: {
                    labels: hours,
                    datasets: [{
                        label: 'Requests',
                        data: hours.map(() => Math.floor(Math.random() * 100) + 20),
                        borderColor: '#4f46e5',
                        tension: 0.3,
                        fill: true,
                        backgroundColor: 'rgba(79, 70, 229, 0.1)'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
            
            new Chart(document.getElementById('errorChart'), {
                type: 'bar',
                data: {
                    labels: hours,
                    datasets: [{
                        label: 'Errors',
                        data: hours.map(() => Math.floor(Math.random() * 5)),
                        backgroundColor: '#ef4444'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
            
            new Chart(document.getElementById('latencyChart'), {
                type: 'bar',
                data: {
                    labels: ['<100ms', '100-250ms', '250-500ms', '500ms-1s', '>1s'],
                    datasets: [{
                        label: 'Requests',
                        data: [150, 80, 30, 10, 2],
                        backgroundColor: ['#22c55e', '#84cc16', '#eab308', '#f97316', '#ef4444']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/dashboard", response_class=HTMLResponse)
def get_full_dashboard():
    """
    Get the complete observability dashboard with LLM usage tracking.

    Features:
    - Real-time metrics fetched from API
    - LLM token usage by operation
    - Cost breakdown
    - Agent performance
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fraud Detection - Observability Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background: #0f172a; 
                color: #e2e8f0;
            }
            h1 { color: #f1f5f9; margin-bottom: 8px; }
            .subtitle { color: #94a3b8; margin-bottom: 24px; }
            .tabs { display: flex; gap: 8px; margin-bottom: 20px; }
            .tab { 
                padding: 10px 20px; 
                background: #1e293b; 
                border: none; 
                color: #94a3b8; 
                border-radius: 8px; 
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
            }
            .tab:hover { background: #334155; }
            .tab.active { background: #3b82f6; color: white; }
            .dashboard { display: none; }
            .dashboard.active { display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; }
            .card { 
                background: #1e293b; 
                padding: 20px; 
                border-radius: 12px; 
                border: 1px solid #334155;
            }
            .card h2 { margin-top: 0; color: #f1f5f9; font-size: 1rem; font-weight: 600; }
            .card.full-width { grid-column: 1 / -1; }
            .chart-wrapper { height: 280px; }
            .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
            .stat-card { 
                background: #1e293b; 
                padding: 16px; 
                border-radius: 10px; 
                border: 1px solid #334155;
            }
            .stat-label { color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
            .stat-value { color: #f1f5f9; font-size: 28px; font-weight: 700; margin-top: 4px; }
            .stat-change { font-size: 12px; margin-top: 4px; }
            .stat-change.positive { color: #22c55e; }
            .stat-change.negative { color: #ef4444; }
            .loading { text-align: center; padding: 60px; color: #64748b; }
            .table-wrapper { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; font-size: 13px; }
            th { text-align: left; padding: 12px 8px; color: #94a3b8; font-weight: 500; border-bottom: 1px solid #334155; }
            td { padding: 12px 8px; border-bottom: 1px solid #1e293b; }
            tr:hover { background: #334155; }
            .badge { 
                display: inline-block; 
                padding: 2px 8px; 
                border-radius: 4px; 
                font-size: 11px; 
                font-weight: 500;
            }
            .badge-success { background: #166534; color: #86efac; }
            .badge-warning { background: #854d0e; color: #fde047; }
            .badge-error { background: #991b1b; color: #fca5a5; }
            .refresh-btn {
                padding: 8px 16px;
                background: #3b82f6;
                border: none;
                color: white;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                margin-left: auto;
            }
            .refresh-btn:hover { background: #2563eb; }
            .header { display: flex; align-items: center; margin-bottom: 20px; }
            .header h1 { margin: 0; }
            .time-filter { 
                display: flex; 
                gap: 4px; 
                margin-left: 20px;
                background: #1e293b;
                padding: 4px;
                border-radius: 6px;
            }
            .time-btn {
                padding: 6px 12px;
                background: transparent;
                border: none;
                color: #94a3b8;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }
            .time-btn.active { background: #334155; color: #f1f5f9; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>Observability Dashboard</h1>
                <p class="subtitle">Monitor LLM usage, costs, and system performance</p>
            </div>
            <div class="time-filter">
                <button class="time-btn" data-hours="1">1H</button>
                <button class="time-btn" data-hours="6">6H</button>
                <button class="time-btn active" data-hours="24">24H</button>
                <button class="time-btn" data-hours="168">7D</button>
            </div>
            <button class="refresh-btn" onclick="refreshData()">Refresh</button>
        </div>
        
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-label">Total LLM Calls</div>
                <div class="stat-value" id="totalCalls">-</div>
                <div class="stat-change positive" id="callsChange">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Tokens</div>
                <div class="stat-value" id="totalTokens">-</div>
                <div class="stat-change" id="tokensBreakdown">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Cost</div>
                <div class="stat-value" id="totalCost">-</div>
                <div class="stat-change" id="avgCost">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Latency</div>
                <div class="stat-value" id="avgLatency">-</div>
                <div class="stat-change" id="latencyRange">-</div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" data-tab="llm">LLM Usage</button>
            <button class="tab" data-tab="operations">By Operation</button>
            <button class="tab" data-tab="costs">Cost Analysis</button>
            <button class="tab" data-tab="recent">Recent Calls</button>
        </div>
        
        <!-- LLM Usage Tab -->
        <div class="dashboard active" id="llm-tab">
            <div class="card">
                <h2>Tokens by Operation</h2>
                <div class="chart-wrapper"><canvas id="tokensByOpChart"></canvas></div>
            </div>
            <div class="card">
                <h2>Tokens by Model</h2>
                <div class="chart-wrapper"><canvas id="tokensByModelChart"></canvas></div>
            </div>
            <div class="card">
                <h2>Hourly Token Usage</h2>
                <div class="chart-wrapper"><canvas id="hourlyTokensChart"></canvas></div>
            </div>
            <div class="card">
                <h2>Tokens by Agent</h2>
                <div class="chart-wrapper"><canvas id="tokensByAgentChart"></canvas></div>
            </div>
        </div>
        
        <!-- Operations Tab -->
        <div class="dashboard" id="operations-tab">
            <div class="card full-width">
                <h2>Token Usage by Operation</h2>
                <div class="table-wrapper">
                    <table id="operationsTable">
                        <thead>
                            <tr>
                                <th>Operation</th>
                                <th>Calls</th>
                                <th>Input Tokens</th>
                                <th>Output Tokens</th>
                                <th>Total Tokens</th>
                                <th>Total Cost</th>
                                <th>Avg Tokens/Call</th>
                                <th>Avg Latency</th>
                                <th>Success Rate</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Costs Tab -->
        <div class="dashboard" id="costs-tab">
            <div class="card">
                <h2>Cost by Model</h2>
                <div class="chart-wrapper"><canvas id="costByModelChart"></canvas></div>
            </div>
            <div class="card">
                <h2>Cost by Operation</h2>
                <div class="chart-wrapper"><canvas id="costByOpChart"></canvas></div>
            </div>
            <div class="card full-width">
                <h2>Cost Breakdown</h2>
                <div class="table-wrapper">
                    <table id="costTable">
                        <thead>
                            <tr>
                                <th>Category</th>
                                <th>Item</th>
                                <th>Calls</th>
                                <th>Tokens</th>
                                <th>Cost (USD)</th>
                                <th>% of Total</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Recent Calls Tab -->
        <div class="dashboard" id="recent-tab">
            <div class="card full-width">
                <h2>Recent LLM Calls</h2>
                <div class="table-wrapper">
                    <table id="recentCallsTable">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Model</th>
                                <th>Agent</th>
                                <th>Operation</th>
                                <th>Input</th>
                                <th>Output</th>
                                <th>Total</th>
                                <th>Cost</th>
                                <th>Latency</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <script>
            let charts = {};
            let currentHours = 24;
            const API_BASE = '/api/v1/observability';
            
            // Tab switching
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.dashboard').forEach(d => d.classList.remove('active'));
                    tab.classList.add('active');
                    document.getElementById(tab.dataset.tab + '-tab').classList.add('active');
                });
            });
            
            // Time filter
            document.querySelectorAll('.time-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    currentHours = parseInt(btn.dataset.hours);
                    refreshData();
                });
            });
            
            function formatNumber(num) {
                if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
                if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
                return num.toString();
            }
            
            function formatCost(cost) {
                return '$' + cost.toFixed(4);
            }
            
            function formatTime(timestamp) {
                const date = new Date(timestamp);
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            
            async function fetchData(endpoint) {
                try {
                    const response = await fetch(endpoint);
                    if (!response.ok) throw new Error('API error');
                    return await response.json();
                } catch (error) {
                    console.error('Fetch error:', error);
                    return null;
                }
            }
            
            async function updateStats() {
                const data = await fetchData(`${API_BASE}/llm/usage?hours=${currentHours}`);
                if (!data) return;
                
                document.getElementById('totalCalls').textContent = formatNumber(data.total_calls);
                document.getElementById('callsChange').textContent = `${data.success_rate * 100}% success rate`;
                document.getElementById('callsChange').className = 'stat-change ' + (data.success_rate > 0.95 ? 'positive' : 'negative');
                
                document.getElementById('totalTokens').textContent = formatNumber(data.tokens?.total || 0);
                document.getElementById('tokensBreakdown').textContent = 
                    `${formatNumber(data.tokens?.input || 0)} in / ${formatNumber(data.tokens?.output || 0)} out`;
                
                document.getElementById('totalCost').textContent = formatCost(data.cost?.total_usd || 0);
                document.getElementById('avgCost').textContent = `Avg: ${formatCost(data.cost?.avg_per_call_usd || 0)}/call`;
                
                document.getElementById('avgLatency').textContent = `${Math.round(data.latency?.avg_ms || 0)}ms`;
                document.getElementById('latencyRange').textContent = 
                    `${Math.round(data.latency?.min_ms || 0)} - ${Math.round(data.latency?.max_ms || 0)}ms`;
            }
            
            async function updateLLMCharts() {
                const data = await fetchData(`${API_BASE}/llm/usage?hours=${currentHours}`);
                if (!data) return;
                
                const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
                
                // Tokens by Operation
                const opLabels = data.by_operation?.map(o => o.operation) || [];
                const opTokens = data.by_operation?.map(o => o.total_tokens) || [];
                
                if (charts.tokensByOp) charts.tokensByOp.destroy();
                charts.tokensByOp = new Chart(document.getElementById('tokensByOpChart'), {
                    type: 'doughnut',
                    data: {
                        labels: opLabels,
                        datasets: [{
                            data: opTokens,
                            backgroundColor: colors.slice(0, opLabels.length),
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 12 } }
                        }
                    }
                });
                
                // Tokens by Model
                const modelLabels = data.by_model?.map(m => m.model) || [];
                const modelTokens = data.by_model?.map(m => m.total_tokens) || [];
                
                if (charts.tokensByModel) charts.tokensByModel.destroy();
                charts.tokensByModel = new Chart(document.getElementById('tokensByModelChart'), {
                    type: 'bar',
                    data: {
                        labels: modelLabels,
                        datasets: [{
                            label: 'Tokens',
                            data: modelTokens,
                            backgroundColor: '#3b82f6',
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                        }
                    }
                });
                
                // Tokens by Agent
                const agentLabels = data.by_agent?.map(a => a.agent_name) || [];
                const agentTokens = data.by_agent?.map(a => a.total_tokens) || [];
                
                if (charts.tokensByAgent) charts.tokensByAgent.destroy();
                charts.tokensByAgent = new Chart(document.getElementById('tokensByAgentChart'), {
                    type: 'bar',
                    data: {
                        labels: agentLabels,
                        datasets: [{
                            label: 'Tokens',
                            data: agentTokens,
                            backgroundColor: '#22c55e',
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                            y: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                        }
                    }
                });
            }
            
            async function updateHourlyChart() {
                const data = await fetchData(`${API_BASE}/llm/usage/hourly?hours=${Math.min(currentHours, 168)}`);
                if (!data) return;
                
                const labels = data.map(h => h.hour.split(' ')[1] || h.hour);
                const tokens = data.map(h => h.tokens);
                const calls = data.map(h => h.calls);
                
                if (charts.hourlyTokens) charts.hourlyTokens.destroy();
                charts.hourlyTokens = new Chart(document.getElementById('hourlyTokensChart'), {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Tokens',
                                data: tokens,
                                borderColor: '#3b82f6',
                                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                fill: true,
                                tension: 0.3,
                                yAxisID: 'y'
                            },
                            {
                                label: 'Calls',
                                data: calls,
                                borderColor: '#22c55e',
                                borderDash: [5, 5],
                                tension: 0.3,
                                yAxisID: 'y1'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        plugins: { legend: { labels: { color: '#94a3b8' } } },
                        scales: {
                            y: { type: 'linear', position: 'left', grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                            y1: { type: 'linear', position: 'right', grid: { display: false }, ticks: { color: '#94a3b8' } },
                            x: { grid: { display: false }, ticks: { color: '#94a3b8', maxTicksLimit: 12 } }
                        }
                    }
                });
            }
            
            async function updateOperationsTable() {
                const data = await fetchData(`${API_BASE}/llm/usage/by-operation?hours=${currentHours}`);
                if (!data) return;
                
                const tbody = document.querySelector('#operationsTable tbody');
                tbody.innerHTML = data.map(op => `
                    <tr>
                        <td><strong>${op.operation}</strong></td>
                        <td>${formatNumber(op.total_calls)}</td>
                        <td>${formatNumber(op.total_input_tokens)}</td>
                        <td>${formatNumber(op.total_output_tokens)}</td>
                        <td>${formatNumber(op.total_tokens)}</td>
                        <td>${formatCost(op.total_cost)}</td>
                        <td>${Math.round(op.avg_tokens_per_call)}</td>
                        <td>${Math.round(op.avg_latency_ms)}ms</td>
                        <td>
                            <span class="badge ${op.success_rate > 0.95 ? 'badge-success' : op.success_rate > 0.8 ? 'badge-warning' : 'badge-error'}">
                                ${(op.success_rate * 100).toFixed(1)}%
                            </span>
                        </td>
                    </tr>
                `).join('');
            }
            
            async function updateCostCharts() {
                const data = await fetchData(`${API_BASE}/llm/usage/cost-breakdown?hours=${currentHours}`);
                if (!data) return;
                
                const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
                
                // Cost by Model
                if (charts.costByModel) charts.costByModel.destroy();
                charts.costByModel = new Chart(document.getElementById('costByModelChart'), {
                    type: 'pie',
                    data: {
                        labels: data.by_model.map(m => m.model),
                        datasets: [{
                            data: data.by_model.map(m => m.cost),
                            backgroundColor: colors,
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 12 } } }
                    }
                });
                
                // Cost by Operation
                if (charts.costByOp) charts.costByOp.destroy();
                charts.costByOp = new Chart(document.getElementById('costByOpChart'), {
                    type: 'pie',
                    data: {
                        labels: data.by_operation.map(o => o.operation),
                        datasets: [{
                            data: data.by_operation.map(o => o.cost),
                            backgroundColor: colors,
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 12 } } }
                    }
                });
                
                // Cost Table
                const tbody = document.querySelector('#costTable tbody');
                let rows = [];
                
                data.by_model.forEach(m => {
                    rows.push(`<tr>
                        <td>Model</td>
                        <td>${m.model}</td>
                        <td>${formatNumber(m.calls)}</td>
                        <td>${formatNumber(m.tokens)}</td>
                        <td>${formatCost(m.cost)}</td>
                        <td>${m.percentage}%</td>
                    </tr>`);
                });
                
                data.by_operation.forEach(o => {
                    rows.push(`<tr>
                        <td>Operation</td>
                        <td>${o.operation}</td>
                        <td>${formatNumber(o.calls)}</td>
                        <td>${formatNumber(o.tokens)}</td>
                        <td>${formatCost(o.cost)}</td>
                        <td>${o.percentage}%</td>
                    </tr>`);
                });
                
                tbody.innerHTML = rows.join('');
            }
            
            async function updateRecentCalls() {
                const data = await fetchData(`${API_BASE}/llm/usage/recent?limit=50`);
                if (!data) return;
                
                const tbody = document.querySelector('#recentCallsTable tbody');
                tbody.innerHTML = data.map(call => `
                    <tr>
                        <td>${formatTime(call.timestamp)}</td>
                        <td>${call.model}</td>
                        <td>${call.agent_name}</td>
                        <td>${call.operation}</td>
                        <td>${formatNumber(call.input_tokens)}</td>
                        <td>${formatNumber(call.output_tokens)}</td>
                        <td>${formatNumber(call.total_tokens)}</td>
                        <td>${formatCost(call.total_cost)}</td>
                        <td>${Math.round(call.latency_ms)}ms</td>
                        <td>
                            <span class="badge ${call.success ? 'badge-success' : 'badge-error'}">
                                ${call.success ? 'OK' : 'Error'}
                            </span>
                        </td>
                    </tr>
                `).join('');
            }
            
            async function refreshData() {
                await Promise.all([
                    updateStats(),
                    updateLLMCharts(),
                    updateHourlyChart(),
                    updateOperationsTable(),
                    updateCostCharts(),
                    updateRecentCalls()
                ]);
            }
            
            // Initial load
            refreshData();
            
            // Auto-refresh every 30 seconds
            setInterval(refreshData, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/dashboard/llm", response_class=HTMLResponse)
def get_llm_dashboard():
    """
    Dedicated LLM token usage dashboard.

    Shows detailed token usage metrics by operation with real-time updates.
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LLM Token Usage Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 0; 
                padding: 24px; 
                background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                min-height: 100vh;
                color: #e2e8f0;
            }
            .header { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-bottom: 24px;
            }
            h1 { margin: 0; font-size: 1.75rem; color: #f8fafc; }
            .controls { display: flex; gap: 12px; }
            select, button {
                padding: 8px 16px;
                border-radius: 8px;
                border: 1px solid #475569;
                background: #1e293b;
                color: #e2e8f0;
                font-size: 14px;
                cursor: pointer;
            }
            button:hover { background: #334155; }
            .metrics-row {
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }
            .metric-card {
                background: rgba(30, 41, 59, 0.8);
                backdrop-filter: blur(10px);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 20px;
            }
            .metric-label { 
                font-size: 12px; 
                color: #94a3b8; 
                text-transform: uppercase; 
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }
            .metric-value { 
                font-size: 32px; 
                font-weight: 700; 
                color: #f8fafc;
                line-height: 1;
            }
            .metric-detail { 
                font-size: 12px; 
                color: #64748b; 
                margin-top: 8px;
            }
            .charts-grid {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                margin-bottom: 24px;
            }
            .chart-card {
                background: rgba(30, 41, 59, 0.8);
                backdrop-filter: blur(10px);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 20px;
            }
            .chart-title {
                font-size: 14px;
                font-weight: 600;
                color: #f1f5f9;
                margin-bottom: 16px;
            }
            .chart-wrapper { height: 300px; }
            .operations-table {
                background: rgba(30, 41, 59, 0.8);
                backdrop-filter: blur(10px);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 20px;
                overflow: hidden;
            }
            table { width: 100%; border-collapse: collapse; }
            th { 
                text-align: left; 
                padding: 12px 16px; 
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #64748b;
                border-bottom: 1px solid #334155;
            }
            td { 
                padding: 14px 16px; 
                font-size: 13px;
                border-bottom: 1px solid rgba(51, 65, 85, 0.5);
            }
            tr:hover { background: rgba(51, 65, 85, 0.3); }
            .op-name { font-weight: 600; color: #f1f5f9; }
            .token-bar {
                height: 8px;
                background: #1e293b;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 4px;
            }
            .token-bar-fill {
                height: 100%;
                border-radius: 4px;
                transition: width 0.5s ease;
            }
            .input-bar { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
            .output-bar { background: linear-gradient(90deg, #22c55e, #4ade80); }
            .cost-badge {
                display: inline-block;
                padding: 4px 10px;
                background: rgba(59, 130, 246, 0.2);
                color: #60a5fa;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }
            .latency-badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }
            .latency-fast { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
            .latency-medium { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
            .latency-slow { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>LLM Token Usage by Operation</h1>
            <div class="controls">
                <select id="timeRange" onchange="refreshData()">
                    <option value="1">Last 1 Hour</option>
                    <option value="6">Last 6 Hours</option>
                    <option value="24" selected>Last 24 Hours</option>
                    <option value="168">Last 7 Days</option>
                </select>
                <button onclick="refreshData()">Refresh</button>
            </div>
        </div>
        
        <div class="metrics-row" id="metricsRow">
            <div class="metric-card">
                <div class="metric-label">Total Operations</div>
                <div class="metric-value" id="totalOps">-</div>
                <div class="metric-detail" id="uniqueOps">Loading...</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Calls</div>
                <div class="metric-value" id="totalCalls">-</div>
                <div class="metric-detail" id="successRate">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Input Tokens</div>
                <div class="metric-value" id="inputTokens">-</div>
                <div class="metric-detail" id="avgInput">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Output Tokens</div>
                <div class="metric-value" id="outputTokens">-</div>
                <div class="metric-detail" id="avgOutput">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Cost</div>
                <div class="metric-value" id="totalCost">-</div>
                <div class="metric-detail" id="avgCost">-</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">Token Distribution by Operation</div>
                <div class="chart-wrapper"><canvas id="tokenDistChart"></canvas></div>
            </div>
            <div class="chart-card">
                <div class="chart-title">Input vs Output Ratio</div>
                <div class="chart-wrapper"><canvas id="ioRatioChart"></canvas></div>
            </div>
        </div>
        
        <div class="operations-table">
            <div class="chart-title">Detailed Operation Metrics</div>
            <table>
                <thead>
                    <tr>
                        <th>Operation</th>
                        <th>Calls</th>
                        <th>Input Tokens</th>
                        <th>Output Tokens</th>
                        <th>Total</th>
                        <th>Cost</th>
                        <th>Avg Latency</th>
                        <th>Models Used</th>
                    </tr>
                </thead>
                <tbody id="opsTableBody"></tbody>
            </table>
        </div>
        
        <script>
            let charts = {};
            const API_BASE = '/api/v1/observability';
            
            function formatNumber(num) {
                if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
                if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
                return num.toLocaleString();
            }
            
            function formatCost(cost) { return '$' + cost.toFixed(4); }
            
            function getLatencyClass(ms) {
                if (ms < 500) return 'latency-fast';
                if (ms < 2000) return 'latency-medium';
                return 'latency-slow';
            }
            
            async function fetchData(endpoint) {
                try {
                    const response = await fetch(endpoint);
                    return response.ok ? await response.json() : null;
                } catch (e) {
                    console.error('Fetch error:', e);
                    return null;
                }
            }
            
            async function refreshData() {
                const hours = document.getElementById('timeRange').value;
                const data = await fetchData(`${API_BASE}/llm/usage/by-operation?hours=${hours}`);
                if (!data || data.length === 0) {
                    document.getElementById('opsTableBody').innerHTML = 
                        '<tr><td colspan="8" style="text-align:center;color:#64748b;padding:40px;">No data available</td></tr>';
                    return;
                }
                
                // Calculate totals
                const totals = data.reduce((acc, op) => ({
                    calls: acc.calls + op.total_calls,
                    input: acc.input + op.total_input_tokens,
                    output: acc.output + op.total_output_tokens,
                    total: acc.total + op.total_tokens,
                    cost: acc.cost + op.total_cost,
                }), { calls: 0, input: 0, output: 0, total: 0, cost: 0 });
                
                // Update metrics
                document.getElementById('totalOps').textContent = data.length;
                document.getElementById('uniqueOps').textContent = `${data.length} unique operations`;
                document.getElementById('totalCalls').textContent = formatNumber(totals.calls);
                document.getElementById('successRate').textContent = 
                    `${(data.reduce((sum, o) => sum + o.success_rate, 0) / data.length * 100).toFixed(1)}% success`;
                document.getElementById('inputTokens').textContent = formatNumber(totals.input);
                document.getElementById('avgInput').textContent = `Avg: ${formatNumber(Math.round(totals.input / totals.calls))}/call`;
                document.getElementById('outputTokens').textContent = formatNumber(totals.output);
                document.getElementById('avgOutput').textContent = `Avg: ${formatNumber(Math.round(totals.output / totals.calls))}/call`;
                document.getElementById('totalCost').textContent = formatCost(totals.cost);
                document.getElementById('avgCost').textContent = `Avg: ${formatCost(totals.cost / totals.calls)}/call`;
                
                // Update charts
                const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];
                const maxTokens = Math.max(...data.map(d => d.total_tokens));
                
                // Token Distribution Chart
                if (charts.tokenDist) charts.tokenDist.destroy();
                charts.tokenDist = new Chart(document.getElementById('tokenDistChart'), {
                    type: 'bar',
                    data: {
                        labels: data.map(d => d.operation),
                        datasets: [
                            {
                                label: 'Input',
                                data: data.map(d => d.total_input_tokens),
                                backgroundColor: '#3b82f6',
                                borderRadius: 4
                            },
                            {
                                label: 'Output',
                                data: data.map(d => d.total_output_tokens),
                                backgroundColor: '#22c55e',
                                borderRadius: 4
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: '#94a3b8' } } },
                        scales: {
                            x: { stacked: true, grid: { display: false }, ticks: { color: '#94a3b8' } },
                            y: { stacked: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }
                        }
                    }
                });
                
                // IO Ratio Chart
                if (charts.ioRatio) charts.ioRatio.destroy();
                charts.ioRatio = new Chart(document.getElementById('ioRatioChart'), {
                    type: 'doughnut',
                    data: {
                        labels: ['Input Tokens', 'Output Tokens'],
                        datasets: [{
                            data: [totals.input, totals.output],
                            backgroundColor: ['#3b82f6', '#22c55e'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '65%',
                        plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } }
                    }
                });
                
                // Update table
                document.getElementById('opsTableBody').innerHTML = data.map((op, i) => `
                    <tr>
                        <td class="op-name">${op.operation}</td>
                        <td>${formatNumber(op.total_calls)}</td>
                        <td>
                            ${formatNumber(op.total_input_tokens)}
                            <div class="token-bar">
                                <div class="token-bar-fill input-bar" style="width: ${(op.total_input_tokens / maxTokens * 100)}%"></div>
                            </div>
                        </td>
                        <td>
                            ${formatNumber(op.total_output_tokens)}
                            <div class="token-bar">
                                <div class="token-bar-fill output-bar" style="width: ${(op.total_output_tokens / maxTokens * 100)}%"></div>
                            </div>
                        </td>
                        <td><strong>${formatNumber(op.total_tokens)}</strong></td>
                        <td><span class="cost-badge">${formatCost(op.total_cost)}</span></td>
                        <td><span class="latency-badge ${getLatencyClass(op.avg_latency_ms)}">${Math.round(op.avg_latency_ms)}ms</span></td>
                        <td style="font-size:11px;color:#94a3b8">${op.models_used.join(', ')}</td>
                    </tr>
                `).join('');
            }
            
            refreshData();
            setInterval(refreshData, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
