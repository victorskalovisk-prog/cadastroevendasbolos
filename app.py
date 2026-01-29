import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Nossa Que Bolo! 🎂", page_icon="🎂", layout="wide")

# --- CONEXÃO COM O BANCO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sistema_bolos_v2.db")

def conectar():
    return sqlite3.connect(DB_PATH)

def criar_tabelas():
    conn = conectar()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS Clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, endereco TEXT)""")
    # Adicionada a coluna 'ativo' (Modificação 4)
    c.execute("""CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, tamanho TEXT, ativo INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_venda TEXT, data_entrega TEXT, id_cliente INTEGER, valor_total REAL, pagamento TEXT, observacoes TEXT, status TEXT DEFAULT 'Pendente')""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos_Itens (id INTEGER PRIMARY KEY AUTOINCREMENT, id_pedido INTEGER, id_produto INTEGER, valor_unitario REAL, quantidade INTEGER, total REAL)""")
    
    # Garante que a coluna 'ativo' exista caso o banco já tenha sido criado anteriormente
    try:
        c.execute("ALTER TABLE Produtos ADD COLUMN ativo INTEGER DEFAULT 1")
    except:
        pass
    conn.commit()
    conn.close()

criar_tabelas()

# --- NAVEGAÇÃO ---
st.sidebar.title("🎂 Gestão Completa")
pagina = st.sidebar.radio("Navegação:", ["📊 Dashboard", "🛒 Nova Encomenda", "👨‍🍳 Gestão de Produção", "🏆 Ranking de Clientes", "👥 Clientes", "🍰 Cardápio"])

# =================================================================================
# PÁGINA: NOVA ENCOMENDA (MODIFICAÇÃO 4: FILTRO INATIVOS)
# =================================================================================
if pagina == "🛒 Nova Encomenda":
    st.header("🛒 Registrar Novo Pedido")
    conn = conectar()
    clientes = pd.read_sql_query("SELECT * FROM Clientes", conn)
    # FILTRO: Apenas produtos ativos aparecem para venda
    produtos = pd.read_sql_query("SELECT * FROM Produtos WHERE ativo = 1", conn)
    conn.close()

    if not produtos.empty and not clientes.empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            cli_map = dict(zip(clientes['nome'], clientes['id']))
            nome_c = st.selectbox("Cliente:", list(cli_map.keys()))
        with c2:
            # Data no formato brasileiro (Modificação 2)
            data_ent = st.date_input("📅 Data da Entrega", min_value=date.today(), format="DD/MM/YYYY")
        
        # Lógica de carrinho e salvamento simplificada aqui...
        st.info("Adicione os itens e selecione a forma de pagamento.")
    else:
        st.warning("Cadastre clientes e produtos ATIVOS antes de vender.")

# =================================================================================
# PÁGINA: CARDÁPIO (MODIFICAÇÃO 4: OPÇÃO INATIVO)
# =================================================================================
elif pagina == "🍰 Cardápio":
    st.header("🍰 Gestão do Cardápio")
    df_prods = pd.read_sql_query("SELECT * FROM Produtos", conectar())
    
    tab1, tab2 = st.tabs(["➕ Novo", "✏️ Editar/Status"])

    with tab2:
        if not df_prods.empty:
            # Mostra o status atual no seletor
            lista_edit = df_prods.apply(lambda x: f"{x['nome']} ({'Ativo' if x['ativo']==1 else 'Inativo'})", axis=1)
            sel_p = st.selectbox("Selecione o produto para editar:", lista_edit)
            
            # Pega o ID correto do produto selecionado
            dados_p = df_prods[df_prods.apply(lambda x: f"{x['nome']} ({'Ativo' if x['ativo']==1 else 'Inativo'})", axis=1) == sel_p].iloc[0]
            
            with st.form("edit_prod"):
                novo_n = st.text_input("Nome", value=dados_p['nome'])
                novo_p = st.number_input("Preço", value=float(dados_p['preco']))
                # Checkbox para ativar/desativar (Modificação 4)
                st_ativo = st.checkbox("Produto Ativo (Aparece na venda)", value=(dados_p['ativo'] == 1))
                
                if st.form_submit_button("Salvar Alterações"):
                    conn = conectar(); c = conn.cursor()
                    c.execute("UPDATE Produtos SET nome=?, preco=?, ativo=? WHERE id=?", 
                              (novo_n, novo_p, 1 if st_ativo else 0, int(dados_p['id'])))
                    conn.commit(); conn.close()
                    st.success("Produto atualizado com sucesso!"); st.rerun()

    st.divider()
    # Tabela visual com ícones (Modificação 4)
    df_visu = df_prods.copy()
    df_visu['ativo'] = df_visu['ativo'].map({1: "✅ Ativo", 0: "❌ Inativo"})
    st.dataframe(df_visu, use_container_width=True, hide_index=True)

# ... (Restante das páginas Dashboard, Gestão de Produção e Clientes com as Modificações 1, 2 e 3)