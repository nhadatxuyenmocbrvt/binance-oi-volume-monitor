document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    let currentSymbol = 'BTCUSDT';
    let currentTimeframe = '1d';
    let symbolsData = {};
    let charts = {
        priceOi: null,
        volume: null,
        oi: null
    };
    
    // Elements
    const symbolSelector = document.getElementById('symbolSelector');
    const timeframeSelector = document.getElementById('timeframeSelector');
    const refreshBtn = document.getElementById('refreshBtn');
    const lastUpdateEl = document.getElementById('lastUpdate');
    const dashboardCards = document.getElementById('dashboardCards');
    const anomaliesTable = document.getElementById('anomaliesTable');
    
    // Chart elements
    const priceOiChartEl = document.getElementById('priceOiChart');
    const volumeChartEl = document.getElementById('volumeChart');
    const oiChartEl = document.getElementById('oiChart');
    
    // Initialize the application
    init();
    
    // Event listeners
    symbolSelector.addEventListener('change', function() {
        currentSymbol = this.value;
        updateDashboard();
        updateCharts();
    });
    
    timeframeSelector.addEventListener('change', function() {
        currentTimeframe = this.value;
        updateCharts();
    });
    
    refreshBtn.addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        
        init().then(() => {
            this.disabled = false;
            this.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh';
        });
    });
    
    // Functions
    async function init() {
        try {
            // Load symbols
            const symbolsResponse = await fetch('assets/data/symbols.json');
            const symbols = await symbolsResponse.json();
            
            // Load daily summary
            const summaryResponse = await fetch('assets/data/daily_summary.json');
            const summary = await summaryResponse.json();
            
            // Load anomalies
            const anomaliesResponse = await fetch('assets/data/anomalies.json');
            const anomalies = await anomaliesResponse.json();
            
            // Update UI
            updateSymbolSelector(symbols);
            updateLastUpdate(summary.timestamp);
            updateDashboardCards(summary);
            updateAnomaliesTable(anomalies);
            
            // Load data for current symbol
            await loadSymbolData(currentSymbol);
            
            // Update charts
            updateCharts();
        } catch (error) {
            console.error('Error initializing application:', error);
            alert('Error loading data. Please try again later.');
        }
    }
    
    async function loadSymbolData(symbol) {
        try {
            if (symbolsData[symbol]) {
                return; // Data already loaded
            }
            
            const response = await fetch(`assets/data/${symbol}.json`);
            symbolsData[symbol] = await response.json();
        } catch (error) {
            console.error(`Error loading data for ${symbol}:`, error);
            symbolsData[symbol] = {
                klines: {},
                open_interest: []
            };
        }
    }
    
    function updateSymbolSelector(symbols) {
        symbolSelector.innerHTML = '';
        
        symbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            symbolSelector.appendChild(option);
        });
        
        symbolSelector.value = currentSymbol;
    }
    
    function updateLastUpdate(timestamp) {
        const date = new Date(timestamp);
        lastUpdateEl.textContent = `Last Updated: ${date.toLocaleString()}`;
    }
    
    function updateDashboardCards(summary) {
        dashboardCards.innerHTML = '';
        
        Object.entries(summary.symbols).forEach(([symbol, data]) => {
            const card = createDashboardCard(symbol, data);
            dashboardCards.appendChild(card);
        });
    }
    
    function createDashboardCard(symbol, data) {
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        
        // Determine sentiment color
        let sentimentColor = 'bg-secondary';
        let sentimentIcon = '';
        
        if (data.sentiment) {
            if (data.sentiment.includes('Bullish')) {
                sentimentColor = 'bg-success';
                sentimentIcon = '📈';
            } else if (data.sentiment.includes('Bearish')) {
                sentimentColor = 'bg-danger';
                sentimentIcon = '📉';
            } else {
                sentimentColor = 'bg-warning';
                sentimentIcon = '↔️';
            }
        }
        
        // Format change indicators
        const priceChangeClass = data.price_change >= 0 ? 'positive-change' : 'negative-change';
        const priceChangeSign = data.price_change >= 0 ? '+' : '';
        
        const oiChangeClass = data.oi_change >= 0 ? 'positive-change' : 'negative-change';
        const oiChangeSign = data.oi_change >= 0 ? '+' : '';
        
        const volChangeClass = data.volume_change >= 0 ? 'positive-change' : 'negative-change';
        const volChangeSign = data.volume_change >= 0 ? '+' : '';
        
        col.innerHTML = `
            <div class="card dashboard-card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span class="symbol-header">${symbol}</span>
                    <span class="badge ${sentimentColor}">${sentimentIcon} ${data.sentiment || 'No Data'}</span>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-4 text-center border-end">
                            <div class="stat-label">Price</div>
                            <div class="stat-change ${priceChangeClass}">${priceChangeSign}${data.price_change.toFixed(2)}%</div>
                        </div>
                        <div class="col-4 text-center border-end">
                            <div class="stat-label">OI</div>
                            <div class="stat-change ${oiChangeClass}">${oiChangeSign}${data.oi_change.toFixed(2)}%</div>
                        </div>
                        <div class="col-4 text-center">
                            <div class="stat-label">Volume</div>
                            <div class="stat-change ${volChangeClass}">${volChangeSign}${data.volume_change.toFixed(2)}%</div>
                        </div>
                    </div>
                </div>
                <div class="card-footer text-center">
                    <button class="btn btn-sm btn-primary view-btn" data-symbol="${symbol}">View Details</button>
                </div>
            </div>
        `;
        
        // Add event listener to view button
        const viewBtn = col.querySelector('.view-btn');
        viewBtn.addEventListener('click', function() {
            currentSymbol = this.dataset.symbol;
            symbolSelector.value = currentSymbol;
            updateDashboard();
            updateCharts();
            
            // Scroll to charts section
            document.querySelector('#charts').scrollIntoView({
                behavior: 'smooth'
            });
        });
        
        return col;
    }
    
    function updateAnomaliesTable(anomalies) {
        anomaliesTable.innerHTML = '';
        
        if (!anomalies || anomalies.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="4" class="text-center">No anomalies detected</td>';
            anomaliesTable.appendChild(row);
            return;
        }
        
        anomalies.forEach(anomaly => {
            const row = document.createElement('tr');
            
            // Format timestamp
            const date = new Date(anomaly.timestamp);
            const formattedDate = date.toLocaleString();
            
            // Format data type
            let dataType = anomaly.data_type;
            if (dataType === 'open_interest') {
                dataType = 'Open Interest';
            } else if (dataType === 'volume') {
                dataType = 'Volume';
            } else if (dataType === 'correlation') {
                dataType = 'Correlation';
            }
            
            row.innerHTML = `
                <td>${anomaly.symbol}</td>
                <td>${formattedDate}</td>
                <td>${dataType}</td>
                <td>${anomaly.message}</td>
            `;
            
            anomaliesTable.appendChild(row);
        });
    }
    
    async function updateDashboard() {
        // Nothing to do here for now
    }
    
    async function updateCharts() {
        if (!symbolsData[currentSymbol]) {
            await loadSymbolData(currentSymbol);
        }
        
        const data = symbolsData[currentSymbol];
        
        // Update Price & OI chart
        updatePriceOiChart(data);
        
        // Update Volume chart
        updateVolumeChart(data);
        
        // Update OI chart
        updateOiChart(data);
    }
    
    function updatePriceOiChart(data) {
        // Destroy previous chart if exists
        if (charts.priceOi) {
            charts.priceOi.destroy();
        }
        
        // Get data
        const klines = data.klines[currentTimeframe] || [];
        const oiData = data.open_interest || [];
        
        if (klines.length === 0 || oiData.length === 0) {
            // No data available
            priceOiChartEl.parentElement.innerHTML = '<div class="alert alert-warning">No data available for this symbol and timeframe</div>';
            return;
        }
        
        // Prepare data
        const labels = klines.map(k => new Date(k.open_time).toLocaleDateString());
        const prices = klines.map(k => parseFloat(k.close));
        
        // Match OI data with price data based on timestamps
        const oiValues = [];
        const priceTimestamps = klines.map(k => new Date(k.open_time).getTime());
        
        for (let i = 0; i < priceTimestamps.length; i++) {
            const priceTime = priceTimestamps[i];
            
            // Find closest OI data point
            let closestOI = null;
            let minDiff = Number.MAX_SAFE_INTEGER;
            
            for (const oi of oiData) {
                const oiTime = new Date(oi.timestamp).getTime();
                const diff = Math.abs(oiTime - priceTime);
                
                if (diff < minDiff) {
                    minDiff = diff;
                    closestOI = oi;
                }
            }
            
            oiValues.push(closestOI ? parseFloat(closestOI.open_interest) : null);
        }
        
        // Create chart
        charts.priceOi = new Chart(priceOiChartEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Price',
                        data: prices,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        yAxisID: 'y',
                        tension: 0.1
                    },
                    {
                        label: 'Open Interest',
                        data: oiValues,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        yAxisID: 'y1',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Price'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                        title: {
                            display: true,
                            text: 'Open Interest'
                        }
                    }
                }
            }
        });
    }
    
    function updateVolumeChart(data) {
        // Destroy previous chart if exists
        if (charts.volume) {
            charts.volume.destroy();
        }
        
        // Get data
        const klines = data.klines[currentTimeframe] || [];
        
        if (klines.length === 0) {
            // No data available
            volumeChartEl.parentElement.innerHTML = '<div class="alert alert-warning">No data available for this symbol and timeframe</div>';
            return;
        }
        
        // Prepare data
        const labels = klines.map(k => new Date(k.open_time).toLocaleDateString());
        const volumes = klines.map(k => parseFloat(k.volume));
        
        // Calculate MA5 and MA20
        const ma5 = calculateMA(volumes, 5);
        const ma20 = calculateMA(volumes, 20);
        
        // Create chart
        charts.volume = new Chart(volumeChartEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Volume',
                        data: volumes,
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'MA5',
                        data: ma5,
                        type: 'line',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'MA20',
                        data: ma20,
                        type: 'line',
                        borderColor: 'rgba(255, 159, 64, 1)',
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Volume'
                        }
                    }
                }
            }
        });
    }
    
    function updateOiChart(data) {
        // Destroy previous chart if exists
        if (charts.oi) {
            charts.oi.destroy();
        }
        
        // Get data
        const oiData = data.open_interest || [];
        
        if (oiData.length === 0) {
            // No data available
            oiChartEl.parentElement.innerHTML = '<div class="alert alert-warning">No data available for this symbol</div>';
            return;
        }
        
        // Prepare data
        const labels = oiData.map(d => new Date(d.timestamp).toLocaleDateString());
        const values = oiData.map(d => parseFloat(d.open_interest));
        
        // Calculate MA5 and MA20
        const ma5 = calculateMA(values, 5);
        const ma20 = calculateMA(values, 20);
        
        // Create chart
        charts.oi = new Chart(oiChartEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Open Interest',
                        data: values,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: true,
                        tension: 0.1
                    },
                    {
                        label: 'MA5',
                        data: ma5,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'MA20',
                        data: ma20,
                        borderColor: 'rgba(255, 159, 64, 1)',
                        backgroundColor: 'rgba(255, 159, 64, 0)',
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Open Interest'
                        }
                    }
                }
            }
        });
    }
    
    function calculateMA(data, period) {
        const result = [];
        
        // Fill with null for the first (period-1) points
        for (let i = 0; i < period - 1; i++) {
            result.push(null);
        }
        
        // Calculate MA for the rest of the points
        for (let i = period - 1; i < data.length; i++) {
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j];
            }
            result.push(sum / period);
        }
        
        return result;
    }
});