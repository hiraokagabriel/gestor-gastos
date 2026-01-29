# 🔄 Guia de Atualização - Sistema de Faturas

## ✨ Novidades Adicionadas

### 📅 Navegação Temporal
- Visualize faturas de meses passados e futuros
- Navegue mês a mês com setas ◀ ▶
- Botão "Hoje" para voltar ao mês atual
- Alerta visual quando estiver em modo simulação

### 📊 Sistema de Faturas
- Nova página dedicada de Faturas
- Timeline de 12 meses (6 passados + atual + 5 futuros)
- Marcar faturas como pagas ✓
- Desmarcar faturas (despagar) ✗
- Visualização de parcelas por fatura
- Status automático: Paga, Atual, Futura, Atrasada

### 🔮 Projeção de Gastos
- Veja quanto você vai gastar nos próximos meses
- Baseado nas parcelas já cadastradas
- Planejamento financeiro avançado

---

## 🛠️ Como Atualizar Seu Sistema

### 1️⃣ Parar o Servidor

Se o sistema estiver rodando, pare com `Ctrl + C`

### 2️⃣ Baixar Atualizações

```bash
cd gestor-gastos
git pull origin main
```

### 3️⃣ Atualizar Banco de Dados

**IMPORTANTE:** Precisa adicionar a nova tabela `invoices`

```bash
python init_db.py
```

**Ou manualmente no Python:**

```bash
python
```

```python
from app import app
from database import db

with app.app_context():
    db.create_all()
    print("✅ Tabelas atualizadas!")

exit()
```

### 4️⃣ Rodar o Sistema

```bash
python app.py
```

### 5️⃣ Acessar Nova Funcionalidade

Abra o navegador em:
```
http://localhost:5000/invoices
```

---

## 🎯 Como Usar as Novas Funcionalidades

### 📋 Página de Faturas

1. **Acessar:** Menu superior → Faturas
2. **Ver Timeline:** Tabela com 12 meses de faturas
3. **Navegar:** Clique em "Ver" ou use as setas ◀ ▶
4. **Ver Detalhes:** Clique em "Detalhes" para ver parcelas
5. **Pagar Fatura:** Clique em "Pagar" (marca parcelas como pagas)
6. **Despagar:** Clique em "Despagar" se pagou por engano

### 🕰️ Navegação Temporal

**Visível em todas as páginas no topo:**

- **◀ Seta Esquerda:** Mês anterior
- **▶ Seta Direita:** Próximo mês
- **Botão "Hoje":** Volta para o mês atual
- **Badge azul:** Mostra qual mês você está vendo
- **Alerta amarelo:** Aparece quando não está no mês atual

### 📊 Fluxo de Trabalho Recomendado

1. **Cadastre suas compras normalmente** em Cartões
2. **Vá em Faturas** para ver o resumo mensal
3. **Navegue para meses futuros** para ver projeções
4. **Quando pagar a fatura real**, marque como paga
5. **Use o Dashboard** para análise geral

---

## ❓ FAQ - Perguntas Frequentes

### As faturas são criadas automaticamente?
✅ **SIM!** Quando você acessa um mês, o sistema calcula e cria a fatura automaticamente baseado nas parcelas.

### Posso ver faturas de meses passados?
✅ **SIM!** Use as setas ◀ para voltar até 6 meses atrás.

### Posso ver quanto vou gastar nos próximos meses?
✅ **SIM!** O sistema projeta automaticamente baseado nas parcelas futuras. Use as setas ▶.

### O que acontece quando marco como "paga"?
✅ Todas as parcelas daquele mês são marcadas como pagas e o limite é liberado.

### Posso "despagar" uma fatura?
✅ **SIM!** É totalmente reversível. Clique em "Despagar".

### A navegação temporal afeta meus dados reais?
❌ **NÃO!** É apenas visualização. Seus dados continuam intactos.

### Preciso marcar faturas antigas como pagas?
🟡 **Opcional.** Se quiser manter histórico organizado, sim. Caso contrário, foque no presente/futuro.

---

## 📝 Arquivos Novos Adicionados

```
gestor-gastos/
├── models.py (ATUALIZADO - adicionado modelo Invoice)
├── init_db.py (NOVO - script de inicialização)
├── routes/
│   ├── __init__.py (ATUALIZADO)
│   └── invoices.py (NOVO - rotas de faturas)
├── templates/
│   ├── base.html (ATUALIZADO - navegação temporal)
│   ├── index.html (ATUALIZADO - card de faturas)
│   └── invoices.html (NOVO - página de faturas)
└── static/
    └── js/
        └── temporal-nav.js (NOVO - controle temporal)
```

---

## ⚠️ Solução de Problemas

### Erro: "no such table: invoices"
🔧 **Solução:** Execute `python init_db.py`

### Menu "Faturas" não aparece
🔧 **Solução:** Limpe o cache do navegador (Ctrl + Shift + Delete)

### Navegação temporal não funciona
🔧 **Solução:** Verifique se o arquivo `static/js/temporal-nav.js` existe

### Faturas aparecem zeradas
🔧 **Normal** se você ainda não tem compras cadastradas naquele período

---

## 🎉 Aproveite as Novas Funcionalidades!

Agora você tem controle total sobre suas finanças:

- ✅ Veja como suas finanças estavam
- ✅ Veja como estão agora
- ✅ Projete como estarão no futuro
- ✅ Planeje com antecedência
- ✅ Evite surpresas

**Boa gestão financeira! 💰**