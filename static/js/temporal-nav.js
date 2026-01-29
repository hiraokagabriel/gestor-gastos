// Controle de Navegação Temporal
// Não executar na página do calendário
if (document.body.classList.contains('calendar-page')) {
    // Página do calendário - não carregar navegação temporal
    console.log('Página do calendário detectada - temporal-nav desabilitado');
} else {
    // Outras páginas - carregar normalmente
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

    async function updateTemporalNav() {
        const display = document.getElementById('temporalMonthDisplay');
        const alert = document.getElementById('temporalAlert');
        const balanceSection = document.getElementById('projectedBalanceSection');
        
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
        
        // Carregar saldo projetado
        if (balanceSection && (viewingMonth !== currentMonth || viewingYear !== currentYear)) {
            await loadProjectedBalance();
        } else if (balanceSection) {
            balanceSection.style.display = 'none';
        }
    }

    async function loadProjectedBalance() {
        const balanceSection = document.getElementById('projectedBalanceSection');
        if (!balanceSection) return;
        
        try {
            const response = await fetch(`/invoices/api/projected-balance?month=${viewingMonth}&year=${viewingYear}`);
            const data = await response.json();
            
            const isPositive = data.projected_balance >= 0;
            const prevMonthName = viewingMonth === 1 ? 'Dezembro' : monthNamesGlobal[viewingMonth - 1];
            
            balanceSection.innerHTML = `
                <div class="alert alert-info shadow-sm">
                    <h6 class="alert-heading">
                        <i class="fas fa-calculator"></i> 
                        Situação Financeira Projetada - ${monthNamesGlobal[viewingMonth]}/${viewingYear}
                    </h6>
                    <hr>
                    <div class="row">
                        <div class="col-md-4">
                            <strong>💵 Saldo Atual:</strong>
                            <h4 class="text-primary">R$ ${data.current_balance.toFixed(2)}</h4>
                        </div>
                        <div class="col-md-4">
                            <strong>💸 A Pagar (até ${prevMonthName}):</strong>
                            <h4 class="text-danger">R$ ${data.total_to_pay.toFixed(2)}</h4>
                        </div>
                        <div class="col-md-4">
                            <strong>📈 Saldo Projetado:</strong>
                            <h4 class="text-${isPositive ? 'success' : 'danger'}">
                                R$ ${data.projected_balance.toFixed(2)}
                                <i class="fas fa-${isPositive ? 'arrow-up' : 'arrow-down'}"></i>
                            </h4>
                        </div>
                    </div>
                    <hr>
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i> 
                        <strong>Este é o saldo que você terá se pagar todas as faturas e boletos até ${prevMonthName}.</strong>
                    </small>
                </div>
            `;
            balanceSection.style.display = 'block';
        } catch (error) {
            console.error('Erro ao carregar saldo projetado:', error);
            balanceSection.style.display = 'none';
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
        // Verificar se os elementos existem antes de tentar carregá-los
        const display = document.getElementById('temporalMonthDisplay');
        if (!display) {
            console.log('Elementos de navegação temporal não encontrados');
            return;
        }
        
        try {
            const response = await fetch('/invoices/api/get-viewing-date');
            const data = await response.json();
            viewingMonth = data.viewing_month;
            viewingYear = data.viewing_year;
            await updateTemporalNav();
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
}