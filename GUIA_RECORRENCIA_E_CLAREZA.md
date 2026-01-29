# 🔍 GUIA COMPLETO: RECORRÊNCIA & CLAREZA VISUAL

## 🎯 O Que Mudou?

### ✅ **ANTES (Confuso)**
- Conta recorrente aparecia em TODOS os meses
- Não ficava claro o que era origem vs gerado automaticamente
- Diferença entre pago e não pago era sutil
- Não dava para excluir todas as recorrências de uma vez

### ✅ **DEPOIS (Claro)**
- ✅ Conta recorrente GERA contas separadas para cada mês
- ✅ Badges coloridos mostram EXATAMENTE o que é cada lançamento
- ✅ Cores de fundo nas linhas da tabela
- ✅ Legenda sempre visível
- ✅ Botão "Excluir Série" para apagar tudo de uma vez

---

## 🎨 CLAREZA VISUAL

### **1. Sistema de Badges (Etiquetas)**

Cada lançamento tem **2 badges** que explicam TUDO:

#### **Badge de Status** (Coluna "Status")
```
🟢 Verde "Consolidado"  = Já foi pago/recebido (está no caixa)
🟡 Amarelo "Pendente"   = Ainda não foi pago/recebido
```

#### **Badge de Origem** (Coluna "Origem")
```
🟣 Roxo "Origem"         = Conta original que gera recorrências
🔴 Rosa "Auto"           = Gerado automaticamente por recorrência
⚪ Cinza "Único"         = Lançamento normal, não recorrente
```

### **2. Cores de Fundo nas Linhas**

```
Fundo Verde Claro    = Lançamento consolidado (já pago)
Fundo Rosa Claro     = Gerado automaticamente por recorrência
Fundo Branco         = Lançamento normal pendente
```

### **3. Legenda Sempre Visível**

No topo da página, logo após o filtro de período, há uma **legenda colorida** explicando cada tipo.

---

## 🔄 SISTEMA DE RECORRÊNCIA

### **Como Funciona Agora:**

#### **Criação Automática**

```bash
# PASSO 1: Criar conta recorrente
Nova Despesa
- Descrição: Aluguel
- Valor: R$ 1.500,00
- Data: 05/01/2026
- ☑ Recorrente (mensal)
- Salvar

# PASSO 2: Sistema gera automaticamente!
✅ Janeiro/2026   - R$ 1.500 (Origem 🟣)
✅ Fevereiro/2026 - R$ 1.500 (Auto 🔴)
✅ Março/2026     - R$ 1.500 (Auto 🔴)
✅ Abril/2026     - R$ 1.500 (Auto 🔴)
... até Dezembro/2026 (12 meses)
```

#### **Cada Conta é Independente**

```
✅ Você pode consolidar (pagar) cada mês separadamente
✅ Você pode editar valores diferentes para cada mês
✅ Você pode deletar um mês específico
```

**Exemplo:**
```
Janeiro   - R$ 1.500 🟢 Consolidado (já pago)
Fevereiro - R$ 1.500 🟡 Pendente (a pagar)
Março     - R$ 1.600 🟡 Pendente (você editou o valor!)
```

---

## 🔧 AÇÕES DISPONÍVEIS

### **1. Consolidar/Desfazer** (✅ ↺)

```
Botão Verde ✓  = Marcar como pago/recebido
Botão Amarelo ↺ = Reverter (voltar para pendente)
```

### **2. Editar** (✏️)

- **Origem Recorrente (🟣)**: Pode editar normalmente
- **Gerado Auto (🔴)**: NÃO pode editar (deletar e recriar)
- **Lançamento Único (⚪)**: Pode editar normalmente

### **3. Excluir**

#### **Botão "🗑️" (Lançamento Único)**
```
Deleta apenas este lançamento
```

#### **Botão "🗑️ Série" (Recorrente)**
```
⚠️ Deleta TUDO:
- A conta origem
- Todas as contas geradas automaticamente

Pergunta confirmação antes!
```

---

## 📊 EXEMPLOS PRÁTICOS

### **Exemplo 1: Salário Mensal**

```bash
# Criar:
Nova Receita
- Descrição: Salário
- Valor: R$ 5.000,00
- Data: 05/01/2026
- ☑ Recorrente
- ☑ Já consolidado

# Resultado: 12 meses de salário, todos marcados como recebidos

Jan: R$ 5.000 🟢 Consolidado | 🔴 Auto
Fev: R$ 5.000 🟢 Consolidado | 🔴 Auto
Mar: R$ 5.000 🟢 Consolidado | 🔴 Auto
...
```

### **Exemplo 2: Aluguel Que Varia**

```bash
# Criar aluguel recorrente
Nova Despesa - Aluguel - R$ 1.500 - ☑ Recorrente

# Janeiro pago normalmente
Jan: R$ 1.500 🟢 Consolidado

# Fevereiro teve reajuste - editar manualmente
Fev: [Editar] R$ 1.500 → R$ 1.650
     Depois consolidar: 🟢

# Março ainda não pagou
Mar: R$ 1.650 🟡 Pendente
```

### **Exemplo 3: Academia (Cancelou no Meio)**

```bash
# Criar academia recorrente
Nova Despesa - Academia - R$ 150 - ☑ Recorrente
# Sistema gera 12 meses

# Pagar janeiro e fevereiro
Jan: R$ 150 🟢 Consolidado
Fev: R$ 150 🟢 Consolidado

# Cancelou a partir de março
Mar: [Excluir Série]
# Deleta março até dezembro
# Janeiro e fevereiro ficam (histórico)
```

---

## 🧐 ENTENDENDO OS 3 TIPOS

### **Tipo 1: Lançamento Único (⚪ Cinza)**

**Quando usar:**
- Despesa ou receita que acontece uma vez só
- Exemplos: Presente de aniversário, reparo do carro, bônus

**Características:**
```
✅ Aparece apenas no mês da data
✅ Pode editar tudo
✅ Pode deletar sem efeitos colaterais
```

### **Tipo 2: Origem Recorrente (🟣 Roxo)**

**O que é:**
- A primeira conta que você criou marcando "Recorrente"
- Ela é a "matriz" que gerou as outras

**Características:**
```
✅ Aparece no mês original
✅ Pode editar normalmente
⚠️ Deletar ela = pergunta se quer deletar filhas também
```

**Identificação:**
```
Badge: 🟣 "Origem"
Ícone: 🔁 (sync-alt)
Texto: "Esta é a conta original. Ela gera cópias automaticamente."
```

### **Tipo 3: Gerado Automaticamente (🔴 Rosa)**

**O que é:**
- Conta criada automaticamente pelo sistema
- Filha da "Origem Recorrente"

**Características:**
```
✅ Aparece nos meses seguintes
⚠️ NÃO pode editar (deletar e recriar manualmente se precisar)
✅ Pode consolidar/desfazer normalmente
✅ Pode deletar individualmente
```

**Identificação:**
```
Badge: 🔴 "Auto"
Ícone: 📋 (copy)
Texto: "Esta conta foi gerada automaticamente pela recorrência."
Cor de fundo: Rosa claro
```

---

## ❓ PERGUNTAS FREQUENTES

### **P: Como sei se um lançamento foi pago ou não?**

**R:** Olhe a coluna **"Status"**:
- 🟢 Verde "Consolidado" = Já pago/recebido
- 🟡 Amarelo "Pendente" = Ainda não foi pago/recebido

### **P: O que significa "Origem" vs "Auto"?**

**R:** 
- 🟣 **Origem**: A conta original que você criou
- 🔴 **Auto**: Cópias geradas automaticamente dela

### **P: Posso editar uma conta "Auto"?**

**R:** Não diretamente. Mas você pode:
1. Deletar ela
2. Criar uma nova manualmente com os valores corretos

### **P: Como faço para parar uma recorrência?**

**R:**
```
1. Clique em "Excluir Série" em qualquer mês da recorrência
2. Confirme (vai deletar origem + todos os meses futuros)
3. Os meses já consolidados permanecem como histórico
```

### **P: Criei errado como recorrente, e agora?**

**R:**
```
1. Clique em "Excluir Série" em qualquer instância
2. Crie novamente sem marcar "Recorrente"
```

### **P: Posso ter valores diferentes em cada mês de uma recorrência?**

**R:** Sim! Depois de criada:
```
1. Deletar o mês específico que quer alterar
2. Criar um novo lançamento manualmente com o valor correto
```

### **P: O que acontece se eu consolidar uma "Origem"?**

**R:** Só ela fica consolidada. As instâncias "Auto" continuam pendentes. Você consolida cada mês separadamente.

---

## 🛠️ FLUXOS DE TRABALHO

### **Fluxo 1: Despesa Fixa Mensal**

```bash
# Criar uma vez
Nova Despesa
- Descrição: Internet
- Valor: R$ 100,00
- Data: 10/01/2026
- ☑ Recorrente

# Todo mês quando pagar:
Filtrar mês atual → Procurar "Internet" → Clicar [✓ Consolidar]

# Saldo em Caixa diminui R$ 100
```

### **Fluxo 2: Receita Variável**

```bash
# Janeiro
Nova Receita - Freelance - R$ 2.000 - ⚪ Único
[Receber] ✓

# Fevereiro
Nova Receita - Freelance - R$ 3.500 - ⚪ Único
[Receber] ✓

# Cada mês você cria manualmente com o valor real
```

### **Fluxo 3: Planejamento de Gastos**

```bash
# Início do mês: criar todos os gastos pendentes
Nova Despesa - Supermercado - R$ 800 - 🟡 Pendente
Nova Despesa - Combustível - R$ 400 - 🟡 Pendente
Nova Despesa - Lazer - R$ 200 - 🟡 Pendente

# Olhar "Saldo Total" para ver o previsto:
Saldo Total: R$ 2.600 (se gastar tudo planejado)

# Conforme gasta, consolidar:
[Paguei supermercado] ✓ Saldo em Caixa atualiza
[Paguei combustível] ✓ Saldo em Caixa atualiza

# Fim do mês: ver o que sobrou
Filtrar [Pendentes] = Gastos planejados mas não feitos
```

---

## 📊 INDICADORES VISUAIS COMPLETOS

### **Tabela de Cores e Significados**

| Elemento | Cor | Significado |
|----------|-----|-------------|
| Badge "Consolidado" | 🟢 Verde | Já pago/recebido, está no caixa |
| Badge "Pendente" | 🟡 Amarelo | Ainda não pago/recebido |
| Badge "Origem" | 🟣 Roxo | Conta original de recorrência |
| Badge "Auto" | 🔴 Rosa | Gerado automaticamente |
| Badge "Único" | ⚪ Cinza | Lançamento normal |
| Fundo da linha | Verde claro | Lançamento consolidado |
| Fundo da linha | Rosa claro | Gerado automaticamente |
| Fundo da linha | Branco | Lançamento normal pendente |

### **Ícones e Significados**

| Ícone | Significado |
|--------|-------------|
| ↑ | Receita |
| ↓ | Despesa |
| ✓ | Consolidar (marcar como pago) |
| ↺ | Desfazer consolidação |
| ✏️ | Editar |
| 🗑️ | Excluir |
| 🗑️ Série | Excluir toda a recorrência |
| 🔁 | Origem de recorrência |
| 📋 | Gerado automaticamente |
| 📄 | Lançamento único |
| ✅ | Checkbox "Recorrente" |
| ✅ | Checkbox "Já consolidado" |

---

## ✅ CHECKLIST DE COMPREENSÃO

**Marque cada item quando entender:**

- [ ] Sei a diferença entre Consolidado (🟢) e Pendente (🟡)
- [ ] Sei a diferença entre Origem (🟣), Auto (🔴) e Único (⚪)
- [ ] Entendo que recorrência gera contas separadas
- [ ] Sei como consolidar (pagar) um lançamento
- [ ] Sei como excluir uma série recorrente inteira
- [ ] Entendo a diferença entre "Saldo em Caixa" e "Saldo Total"
- [ ] Sei usar os filtros (Pendentes, Consolidados, Receitas, Despesas)
- [ ] Sei criar uma despesa recorrente
- [ ] Sei criar uma despesa única

---

## 📚 RESUMO RÁPIDO

### **3 Regras de Ouro**

1. **🟢 Verde = Já Está no Caixa**
   - Se está verde (consolidado), já foi pago/recebido
   
2. **🔴 Rosa = Automático, Não Mexer**
   - Se tem fundo rosa, foi gerado automaticamente
   - Pode consolidar, mas não pode editar
   
3. **"Excluir Série" = Apaga Tudo**
   - Use com cuidado!
   - Apaga origem + todas as geradas

### **O Que Fazer em Cada Situação**

| Situação | Ação |
|-----------|-------|
| Paguei uma conta | Clicar [✓] na linha dela |
| Recebi um pagamento | Clicar [✓] na linha dele |
| Paguei errado | Clicar [↺] para desfazer |
| Criar despesa mensal | Marcar ☑ Recorrente |
| Criar despesa uma vez | NãO marcar Recorrente |
| Cancelar assinatura | [Excluir Série] nos meses futuros |
| Ver o que falta pagar | Filtro [Pendentes] |
| Ver o que já paguei | Filtro [Consolidados] |

---

**🎉 Pronto! Agora você domina o sistema de Lançamentos!**