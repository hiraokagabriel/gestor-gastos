// Controle de Navegação Temporal
// Verificar se estamos na página do calendário
const isCalendarPage = () => {
    return document.body.classList.contains('calendar-page') || 
           window.location.pathname.includes('/calendar');
};

if (isCalendarPage()) {
    // Página do calendário - não carregar navegação temporal
    console.log('Página do calendário detectada - temporal-nav desabilitado');
} else {
    // Outras páginas - carregar normalmente (se os elementos existirem)
    if (typeof viewingMonth === 'undefined') {
        var viewingMonth = new Date().getMonth() + 1;   // aplicado
        var viewingYear = new Date().getFullYear();     // aplicado
        var pendingMonth = viewingMonth;               // selecionado (ainda não aplicado)
        var pendingYear = viewingYear;                 // selecionado (ainda não aplicado)
        var currentMonth = new Date().getMonth() + 1;
        var currentYear = new Date().getFullYear();
    }

    if (typeof monthNamesGlobal === 'undefined') {
        var monthNamesGlobal = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    }

    function _fmtMonthYear(month, year) {
        return `${monthNamesGlobal[month]}/${year}`;
    }

    function _pendingDiffersFromApplied() {
        return pendingMonth !== viewingMonth || pendingYear !== viewingYear;
    }

    async function updateTemporalNav() {
        const display = document.getElementById('temporalMonthDisplay');
        const alert = document.getElementById('temporalAlert');
        const balanceSection = document.getElementById('projectedBalanceSection');

        const applyBtn = document.getElementById('temporalApplyBtn');
        const appliedHint = document.getElementById('temporalAppliedHint');
        const appliedDisplay = document.getElementById('temporalAppliedDisplay');

        // Se não existe a barra (contextual por tela), não faz nada.
        if (!display) {
            return;
        }

        // Badge mostra o período selecionado (não aplicado ainda)
        display.textContent = _fmtMonthYear(pendingMonth, pendingYear);

        // Hints e botões (modo filtro explícito)
        const dirty = _pendingDiffersFromApplied();
        if (applyBtn) {
            applyBtn.disabled = !dirty;
        }

        if (appliedHint && appliedDisplay) {
            if (dirty) {
                appliedDisplay.textContent = _fmtMonthYear(viewingMonth, viewingYear);
                appliedHint.style.display = 'inline';
            } else {
                appliedHint.style.display = 'none';
            }
        }

        // Alerta só quando a data APLICADA não é o mês atual
        if (alert) {
            if (viewingMonth !== currentMonth || viewingYear !== currentYear) {
                alert.style.display = 'block';
            } else {
                alert.style.display = 'none';
            }
        }

        // Saldo projetado: baseado no período APLICADO.
        // Se há alteração pendente, não mostra projeção "do mês novo" até aplicar.
        if (balanceSection && (viewingMonth !== currentMonth || viewingYear !== currentYear) && !dirty) {
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

    function saveViewingDate() {
        return fetch('/invoices/api/set-viewing-date', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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

    // API pública para páginas que querem controlar o período pendente (ex.: timeline em /invoices)
    window.getAppliedViewingDate = function() {
        return { month: viewingMonth, year: viewingYear };
    };

    window.getPendingViewingDate = function() {
        return { month: pendingMonth, year: pendingYear };
    };

    window.setPendingViewingDate = function(month, year) {
        const m = parseInt(month, 10);
        const y = parseInt(year, 10);
        if (!m || m < 1 || m > 12 || !y) return;
        pendingMonth = m;
        pendingYear = y;
        updateTemporalNav();
    };

    // Setas mudam só o período SELECIONADO (não aplica imediatamente)
    window.prevMonth = function() {
        pendingMonth--;
        if (pendingMonth < 1) {
            pendingMonth = 12;
            pendingYear--;
        }
        updateTemporalNav();
    };

    window.nextMonth = function() {
        pendingMonth++;
        if (pendingMonth > 12) {
            pendingMonth = 1;
            pendingYear++;
        }
        updateTemporalNav();
    };

    // Aplicar filtro (persistir no servidor e recarregar dados)
    window.applyViewingDate = function() {
        viewingMonth = pendingMonth;
        viewingYear = pendingYear;

        updateTemporalNav();
        saveViewingDate().finally(() => {
            reloadPageData();
        });
    };

    // Limpar (voltar para hoje) e aplicar imediatamente
    window.clearViewingDate = function() {
        viewingMonth = currentMonth;
        viewingYear = currentYear;
        pendingMonth = currentMonth;
        pendingYear = currentYear;

        updateTemporalNav();

        fetch('/invoices/api/reset-viewing-date', {
            method: 'POST'
        }).then(() => {
            reloadPageData();
        }).catch(err => console.error('Erro ao resetar data:', err));
    };

    // Carregar data visualizada ao iniciar
    // Novo comportamento: ao entrar em qualquer página que usa a barra, resetar para o mês vigente.
    async function loadViewingDate() {
        const display = document.getElementById('temporalMonthDisplay');
        if (!display) {
            // Barra não existe nesta tela
            return;
        }

        try {
            // Resetar período aplicado ao entrar na tela (evita levar mês antigo entre abas)
            const response = await fetch('/invoices/api/reset-viewing-date', {
                method: 'POST'
            });
            const data = await response.json();

            if (!data || !data.viewing_month || !data.viewing_year) {
                throw new Error('Resposta inválida do reset-viewing-date');
            }

            viewingMonth = data.viewing_month;
            viewingYear = data.viewing_year;
            pendingMonth = viewingMonth;
            pendingYear = viewingYear;

            await updateTemporalNav();
        } catch (error) {
            console.error('Erro ao resetar data ao carregar página:', error);

            // Fallback: manter o comportamento antigo caso o reset falhe
            try {
                const response = await fetch('/invoices/api/get-viewing-date');
                const data = await response.json();

                viewingMonth = data.viewing_month;
                viewingYear = data.viewing_year;
                pendingMonth = viewingMonth;
                pendingYear = viewingYear;

                await updateTemporalNav();
            } catch (e2) {
                console.error('Erro ao carregar data (fallback):', e2);
            }
        }
    }

    // Inicializar ao carregar a página
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadViewingDate);
    } else {
        loadViewingDate();
    }
}
