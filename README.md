# 💰 Gestor de Gastos

Sistema completo de gestão financeira pessoal desenvolvido em Python/Flask para controlar cartões de crédito, boletos e contas gerais.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🎯 Funcionalidades

### 💳 Gestão de Cartões de Crédito
- Cadastro de múltiplos cartões
- Controle de limite total e disponível
- Cálculo automático de fatura atual
- Gerenciamento de compras parceladas
- Configuração de dia de fechamento e vencimento
- Visualização de histórico de transações
- Acompanhamento de uso do limite em tempo real

### 📄 Gestão de Boletos
- Cadastro de boletos com vencimento
- Status automático (pendente, vencido, pago)
- Filtros por status
- Alertas visuais de vencimento
- Código de barras

### 💵 Gestão de Contas Gerais
- Registro de receitas e despesas
- Categorização automática
- Contas recorrentes
- Histórico completo

### 📊 Dashboard Supremo
- Visão consolidada de todas as finanças
- Gráficos de despesas por categoria
- Tendência mensal (últimos 6 meses)
- Indicadores de saúde financeira
- Análise de receitas vs despesas
- Percentual de uso dos cartões

## 🚀 Tecnologias

- **Backend:** Python 3.11+, Flask 3.0.0
- **ORM:** SQLAlchemy
- **Banco de Dados:** SQLite (pode migrar para PostgreSQL)
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **UI Framework:** Bootstrap 5
- **Gráficos:** Chart.js
- **Ícones:** Font Awesome 6

## 📁 Estrutura do Projeto

```
gestor-gastos/
│
├── app.py                 # Aplicação principal Flask
├── models.py              # Modelos do banco de dados
├── database.py            # Configuração do banco
├── requirements.txt       # Dependências Python
│
├── routes/
│   ├── __init__.py
│   ├── cards.py          # Rotas de cartões
│   ├── bills.py          # Rotas de boletos
│   ├── accounts.py       # Rotas de contas
│   └── dashboard.py      # Dashboard
│
├── templates/
│   ├── base.html         # Template base
│   ├── index.html        # Página inicial
│   ├── cards.html        # Gestão de cartões
│   ├── bills.html        # Gestão de boletos
│   ├── accounts.html     # Gestão de contas
│   └── dashboard.html    # Dashboard
│
└── static/
    ├── css/
    │   └── style.css     # Estilos customizados
    └── js/
        └── main.js       # JavaScript global
```

## 🔧 Instalação

### Pré-requisitos
- Python 3.11 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

1. **Clone o repositório:**
```bash
git clone https://github.com/hiraokagabriel/gestor-gastos.git
cd gestor-gastos
```

2. **Crie um ambiente virtual:**
```bash
python -m venv venv
```

3. **Ative o ambiente virtual:**
- **Linux/Mac:**
```bash
source venv/bin/activate
```
- **Windows:**
```bash
venv\Scripts\activate
```

4. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

5. **Execute a aplicação:**
```bash
python app.py
```

6. **Acesse no navegador:**
```
http://localhost:5000
```

## 📊 Banco de Dados

O sistema utiliza SQLite por padrão (arquivo `gestor_gastos.db` criado automaticamente na primeira execução).

### Modelos de Dados

- **CreditCard**: Cartões de crédito
- **Transaction**: Transações dos cartões
- **Installment**: Parcelas de compras
- **Bill**: Boletos
- **Account**: Contas gerais (receitas/despesas)
- **Category**: Categorias de gastos

## 🎨 Screenshots

### Dashboard
Visão consolidada com gráficos e indicadores financeiros

### Cartões
Gerenciamento completo de cartões com limite e fatura

### Boletos
Controle de vencimentos e pagamentos

## 🔐 Segurança

⚠️ **IMPORTANTE:** Antes de colocar em produção:
1. Altere a `SECRET_KEY` em `app.py`
2. Configure variáveis de ambiente
3. Use HTTPS
4. Implemente autenticação de usuários
5. Migre para PostgreSQL ou MySQL

## 🛣️ Roadmap

- [ ] Sistema de autenticação de usuários
- [ ] Multi-usuário com isolamento de dados
- [ ] Exportação de relatórios (PDF, Excel)
- [ ] Gráficos mais avançados
- [ ] Metas de economia
- [ ] Notificações por email
- [ ] App mobile (React Native)
- [ ] Integração com Open Banking
- [ ] Dashboard com IA para previsões

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um Fork do projeto
2. Criar uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abrir um Pull Request

## 📝 API Endpoints

### Cartões
- `GET /cards/api/cards` - Lista todos os cartões
- `POST /cards/api/cards` - Cria novo cartão
- `GET /cards/api/cards/{id}` - Detalhes do cartão
- `PUT /cards/api/cards/{id}` - Atualiza cartão
- `DELETE /cards/api/cards/{id}` - Deleta cartão
- `GET /cards/api/cards/{id}/transactions` - Transações do cartão
- `POST /cards/api/transactions` - Cria transação

### Boletos
- `GET /bills/api/bills` - Lista boletos
- `POST /bills/api/bills` - Cria boleto
- `PUT /bills/api/bills/{id}` - Atualiza boleto
- `POST /bills/api/bills/{id}/pay` - Marca como pago
- `DELETE /bills/api/bills/{id}` - Deleta boleto

### Contas
- `GET /accounts/api/accounts` - Lista contas
- `POST /accounts/api/accounts` - Cria conta
- `PUT /accounts/api/accounts/{id}` - Atualiza conta
- `DELETE /accounts/api/accounts/{id}` - Deleta conta

### Dashboard
- `GET /dashboard/api/summary` - Resumo financeiro
- `GET /dashboard/api/expenses-by-category` - Gastos por categoria
- `GET /dashboard/api/monthly-trend` - Tendência mensal

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

**Gabriel Hiraoka**
- GitHub: [@hiraokagabriel](https://github.com/hiraokagabriel)

## ⭐ Agradecimentos

Se este projeto foi útil para você, considere dar uma ⭐!

---

**Desenvolvido com ❤️ por Gabriel Hiraoka**