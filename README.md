
---

##  Arquitetura do Projeto

O sistema é composto por três módulos principais:
1.  **Backend (Python/SPADE/Flower)**: Onde residem os agentes inteligentes e a lógica de aprendizado federado.
2.  **Frontend (React/Vite)**: Dashboard interativo para visualização em tempo real.
3.  **Infraestrutura (Docker/Prosody)**: Servidor XMPP para troca de mensagens entre agentes.

---

##  Pré-requisitos

*   **Docker** (Para o servidor XMPP)
*   **Python 3.10+**
*   **Node.js 18+** & **npm**

---

##  Quick Start (Automático)

Para facilitar a execução, incluímos um script `run_all.sh` que configura o ambiente, instala dependências e inicia todos os serviços.

1.  **Dataset (Já incluso)**:
    O dataset **NSL-KDD** já está incluso na pasta `nsl-kdd/` dentro deste repositório para facilitar a execução.

2.  **Execute o Script**:
    ```bash
    chmod +x run_all.sh
    sudo ./run_all.sh
    ```
    *O script irá criar um venv, instalar o `requirements.txt`, subir o Docker do XMPP e iniciar o React.*

---

##  Instalação Manual (Passo a Passo)

Se você preferir configurar o ambiente manualmente, siga os passos abaixo.

### 1. Configuração do Servidor XMPP (Docker)
O sistema precisa de um servidor Prosody rodando na porta 5222.
```bash
docker run -d --restart=no --name showcase_xmpp \
    -p 5222:5222 -p 5269:5269 -p 5280:5280 \
    -e PROSODY_ADMIN=admin@localhost \
    -e PROSODY_ADMIN_PASSWORD=password \
    prosody/prosody
```

### 2. Configuração do Backend (Python)

Crie um ambiente virtual e instale as dependências listadas em **requirements.txt**.

```bash
# 1. Crie o ambiente virtual
python3 -m venv backend/venv

# 2. Ative o ambiente
source backend/venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

Para rodar o backend manualmente:
```bash
# Exportar variáveis necessárias
export DATA_PATH="../nsl-kdd"  # Ajuste para onde você baixou os dados
export XMPP_HOST="localhost"
export XMPP_PASS="password"

# Executar a API
python -m backend.api.main
```

### 3. Configuração do Frontend (React)

Entre na pasta `frontend` e instale as dependências do Node.js.

```bash
cd frontend
npm install
npm run dev
```
O dashboard estará acessível em `http://localhost:5173`.

---

##  Estrutura de Arquivos

```
federated-ids-showcase/
├── backend/
│   ├── agents/          # Agentes SPADE (ServerAgent, ClientAgent)
│   ├── fl/              # Lógica de Federated Learning (Flower)
│   ├── ml/              # Modelos PyTorch e Processamento de Dados
│   └── api/             # API FastAPI para o Frontend
├── frontend/            # Aplicação React (Vite)
├── requirements.txt     # Dependências Python
├── run_all.sh           # Script de Orquestração
└── README.md            # Este arquivo
```

##  Notas sobre o Dataset
O projeto foi ajustado para usar o **NSL-KDD**. Certifique-se de que os arquivos `KDDTrain+.txt` e `KDDTest+.txt` estejam acessíveis e íntegros. O pré-processamento (One-Hot Encoding, Scaling) é feito automaticamente pelo módulo `backend.ml.data`.
