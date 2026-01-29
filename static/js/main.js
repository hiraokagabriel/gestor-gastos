// Funções utilitárias globais

// Formatar moeda brasileira
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Formatar data para pt-BR
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('pt-BR');
}

// Formatar data e hora
function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('pt-BR');
}

// Toast de notificação
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white ${bgClass} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Criar container de toasts
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// Validar formulário
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        showToast('Por favor, preencha todos os campos obrigatórios', 'warning');
        return false;
    }
    return true;
}

// Loading spinner
function showLoading(message = 'Carregando...') {
    const existingSpinner = document.getElementById('loadingSpinner');
    if (existingSpinner) return;
    
    const spinner = document.createElement('div');
    spinner.id = 'loadingSpinner';
    spinner.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
    spinner.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    spinner.style.zIndex = '9998';
    
    spinner.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-light" role="status">
                <span class="visually-hidden">Carregando...</span>
            </div>
            <p class="text-white mt-2">${message}</p>
        </div>
    `;
    
    document.body.appendChild(spinner);
}

function hideLoading() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.remove();
    }
}

// Confirmar ação
function confirmAction(message = 'Tem certeza que deseja realizar esta ação?') {
    return confirm(message);
}

// Obter data atual no formato YYYY-MM-DD
function getTodayDate() {
    return new Date().toISOString().split('T')[0];
}

// Configurar data de hoje como padrão em inputs de data
function setDefaultDates() {
    const today = getTodayDate();
    document.querySelectorAll('input[type="date"]').forEach(input => {
        if (!input.value && !input.hasAttribute('data-no-default')) {
            input.value = today;
        }
    });
}

// Calcular diferença entre datas em dias
function getDaysDifference(date1, date2) {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    const diffTime = d2 - d1;
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

// Formatar número com separadores de milhares
function formatNumber(num) {
    return new Intl.NumberFormat('pt-BR').format(num);
}

// Debounce para inputs de busca
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Copiar texto para clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copiado para a área de transferência!', 'success');
    }).catch(err => {
        console.error('Erro ao copiar:', err);
        showToast('Erro ao copiar', 'error');
    });
}

// Manipular erros de fetch
async function handleFetchError(response) {
    if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Erro desconhecido' }));
        throw new Error(error.message || `Erro ${response.status}`);
    }
    return response;
}

// Fazer requisição fetch com tratamento de erros
async function fetchWithErrorHandling(url, options = {}) {
    try {
        showLoading();
        const response = await fetch(url, options);
        await handleFetchError(response);
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição:', error);
        showToast(error.message || 'Erro na requisição', 'error');
        throw error;
    } finally {
        hideLoading();
    }
}

// Event listeners globais
document.addEventListener('DOMContentLoaded', () => {
    // Configurar datas padrão
    setDefaultDates();
    
    // Adicionar animações aos cards
    document.querySelectorAll('.card').forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Fechar modais ao pressionar ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            });
        }
    });
    
    // Adicionar validação em tempo real para formulários
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Highlighting da página atual no menu
    const currentPath = window.location.pathname;
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});

// Prevenir envio duplicado de formulários
let formSubmitting = false;
function preventDoubleSubmit(callback) {
    if (formSubmitting) {
        showToast('Aguarde, processando...', 'warning');
        return;
    }
    formSubmitting = true;
    
    Promise.resolve(callback()).finally(() => {
        formSubmitting = false;
    });
}

// Exportar funções para uso global
window.utils = {
    formatCurrency,
    formatDate,
    formatDateTime,
    showToast,
    validateForm,
    showLoading,
    hideLoading,
    confirmAction,
    getTodayDate,
    getDaysDifference,
    formatNumber,
    debounce,
    copyToClipboard,
    fetchWithErrorHandling,
    preventDoubleSubmit
};