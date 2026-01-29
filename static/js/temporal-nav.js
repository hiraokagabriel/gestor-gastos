// Controle de Navegação Temporal
if (typeof viewingMonth === 'undefined') {
    var viewingMonth = new Date().getMonth() + 1;
    var viewingYear = new Date().getFullYear();
    var currentMonth = new Date().getMonth() + 1;
    var currentYear = new Date().getFullYear();
}

if (typeof monthNamesGlobal === 'undefined') {
    var monthNamesGlobal = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
}

function updateTemporalNav() {
    const display = document.getElementById('temporalMonthDisplay');
    const alert = document.getElementById('temporalAlert');
    
    if (display) {
        display.textContent = `${monthNamesGlobal[viewingMonth]}/${viewingYear}`;
    }
    
    // Mostrar alerta se não estiver no mês atual
    if (alert) {
        if (viewingMonth !== currentMonth || viewingYear !== currentYear) {
            alert.style.display = 'block';
        } else {
            alert.style.display = 'none';
        }
    }
}

function prevMonth() {
    viewingMonth--;
    if (viewingMonth < 1) {
        viewingMonth = 12;
        viewingYear--;
    }
    updateTemporalNav();
    saveViewingDate();
    reloadPageData();
}

function nextMonth() {
    viewingMonth++;
    if (viewingMonth > 12) {
        viewingMonth = 1;
        viewingYear++;
    }
    updateTemporalNav();
    saveViewingDate();
    reloadPageData();
}

function goToToday() {
    viewingMonth = currentMonth;
    viewingYear = currentYear;
    updateTemporalNav();
    
    fetch('/invoices/api/reset-viewing-date', {
        method: 'POST'
    }).then(() => {
        reloadPageData();
    }).catch(err => console.error('Erro ao resetar data:', err));
}

function saveViewingDate() {
    fetch('/invoices/api/set-viewing-date', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            month: viewingMonth,
            year: viewingYear
        })
    }).catch(err => console.error('Erro ao salvar data:', err));
}

function reloadPageData() {
    // Recarregar dados da página atual
    if (typeof loadInvoices === 'function') loadInvoices();
    if (typeof loadCards === 'function') loadCards();
    if (typeof loadBills === 'function') loadBills();
    if (typeof loadDashboard === 'function') loadDashboard();
}

// Carregar data visualizada ao iniciar
async function loadViewingDate() {
    try {
        const response = await fetch('/invoices/api/get-viewing-date');
        const data = await response.json();
        viewingMonth = data.viewing_month;
        viewingYear = data.viewing_year;
        updateTemporalNav();
    } catch (error) {
        console.error('Erro ao carregar data:', error);
    }
}

// Inicializar ao carregar a página
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadViewingDate);
} else {
    loadViewingDate();
}