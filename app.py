import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Nossa Que Bolo! 🎂", page_icon="🎂", layout="wide")

# --- CONEXÃO COM O BANCO LOCAL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "banco_dados.db")

def conectar():
    return sqlite3.connect(DB_PATH)

def criar_tabelas():
    conn = conectar()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS Clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, endereco TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, tamanho TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, id_cliente INTEGER, valor_total REAL, pagamento TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos_Itens (id INTEGER PRIMARY KEY AUTOINCREMENT, id_pedido INTEGER, id_produto INTEGER, valor_unitario REAL, quantidade INTEGER, total REAL)""")
    conn.commit()
    conn.close()

# Garante que as tabelas existem ao iniciar
criar_tabelas()

def carregar_dados(tabela):
    conn = conectar()
    df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df

# --- BARRA LATERAL (MENU + FILTROS) ---
st.sidebar.title("🎂 Gestão Completa")
pagina = st.sidebar.radio("Navegação:", ["📊 Dashboard & Relatórios", "🛒 Nova Venda", "👥 Clientes", "🍰 Cardápio"])

st.sidebar.markdown("---")
if pagina == "📊 Dashboard & Relatórios":
    st.sidebar.header("🗓️ Filtros do Relatório")
    filtro_periodo = st.sidebar.selectbox("Selecione o Período:", ["Todo o Histórico", "Últimos 7 dias", "Últimos 30 dias", "Hoje"])
else:
    filtro_periodo = "Todo o Histórico"

# =================================================================================
# PÁGINA: DASHBOARD COMPLETO
# =================================================================================
if pagina == "📊 Dashboard & Relatórios":
    st.header("📊 Painel de Controle")

    conn = conectar()
    sql = """
    SELECT 
        Pedidos.id as id_pedido,
        Pedidos.data,
        Pedidos.valor_total,
        Pedidos.pagamento,
        Pedidos_Itens.quantidade,
        Produtos.nome as produto
    FROM Pedidos_Itens
    JOIN Pedidos ON Pedidos_Itens.id_pedido = Pedidos.id
    JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id
    ORDER BY Pedidos.data DESC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if not df.empty:
        # 1. Tratamento de Datas
        df['data'] = pd.to_datetime(df['data'])
        df['dia'] = df['data'].dt.date  
        
        data_atual = datetime.now()

        # 2. Aplicar Filtros
        if filtro_periodo == "Últimos 7 dias":
            data_corte = data_atual - timedelta(days=7)
            df = df[df['data'] >= data_corte]
        elif filtro_periodo == "Últimos 30 dias":
            data_corte = data_atual - timedelta(days=30)
            df = df[df['data'] >= data_corte]
        elif filtro_periodo == "Hoje":
            df = df[df['dia'] == data_atual.date()]

        if df.empty:
            st.warning(f"Nenhuma venda encontrada no período: {filtro_periodo}")
        else:
            # 3. Criar DF Único para Financeiro
            df_vendas_unicas = df.drop_duplicates(subset=['id_pedido'])
            
            # KPIs
            faturamento = df_vendas_unicas['valor_total'].sum()
            qtd_pedidos = df_vendas_unicas['id_pedido'].count()
            ticket_medio = faturamento / qtd_pedidos if qtd_pedidos > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Faturamento", f"R$ {faturamento:.2f}")
            c2.metric("📦 Pedidos", qtd_pedidos)
            c3.metric("📈 Ticket Médio", f"R$ {ticket_medio:.2f}")

            st.divider()

            # 4. GRÁFICOS
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("💳 Formas de Pagamento")
                df_pag = df_vendas_unicas.groupby("pagamento")["valor_total"].sum().reset_index()
                fig_pag = px.pie(df_pag, values='valor_total', names='pagamento', 
                                 title="Receita por Tipo",
                                 color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pag, use_container_width=True)

            with col_g2:
                st.subheader("🏆 Bolos Mais Vendidos")
                df_prod = df.groupby("produto")["quantidade"].sum().reset_index().sort_values("quantidade", ascending=True)
                fig_prod = px.bar(df_prod, x="quantidade", y="produto", orientation='h',
                                  title="Top Produtos (Qtd)", text="quantidade")
                st.plotly_chart(fig_prod, use_container_width=True)

            st.subheader("📅 Evolução Diária")
            df_dia = df_vendas_unicas.groupby("dia")["valor_total"].sum().reset_index()
            fig_line = px.line(df_dia, x="dia", y="valor_total", markers=True, title="Faturamento por Dia")
            st.plotly_chart(fig_line, use_container_width=True)

            with st.expander("🔎 Ver Tabela Detalhada"):
                st.dataframe(df_vendas_unicas[['data', 'valor_total', 'pagamento']], use_container_width=True)
    else:
        st.info("Nenhuma venda registrada no sistema ainda.")

# =================================================================================
# PÁGINA: NOVA VENDA (COM CHECKOUT VISUAL IGUAL À FOTO)
# =================================================================================
elif pagina == "🛒 Nova Venda":
    st.header("🛒 Registrar Pedido")
    if 'carrinho' not in st.session_state: st.session_state['carrinho'] = []

    conn = conectar()
    clientes = pd.read_sql_query("SELECT id, nome FROM Clientes", conn)
    produtos = pd.read_sql_query("SELECT id, nome, preco FROM Produtos", conn)
    conn.close()

    if clientes.empty or produtos.empty:
        st.warning("Cadastre clientes e produtos antes de vender.")
    else:
        cli_map = dict(zip(clientes['nome'], clientes['id']))
        nome_c = st.selectbox("Cliente:", list(cli_map.keys()))
        
        st.divider()
        
        prod_map = {f"{r['nome']} (R$ {r['preco']:.2f})": r for i, r in produtos.iterrows()}
        c1, c2, c3 = st.columns([3,1,1])
        with c1: 
            p_sel = st.selectbox("Produto:", list(prod_map.keys()))
            dados_p = prod_map[p_sel]
        with c2: qtd = st.number_input("Qtd", 1, 50, 1)
        with c3:
            st.write(""); st.write("")
            if st.button("➕ Add"):
                st.session_state['carrinho'].append({
                    "id": dados_p['id'], "nome": dados_p['nome'], "preco": dados_p['preco'],
                    "qtd": qtd, "total": dados_p['preco']*qtd
                })

        # --- AQUI ESTÁ A MÁGICA: SÓ MOSTRA SE TIVER ITENS ---
        if st.session_state['carrinho']:
            df_c = pd.DataFrame(st.session_state['carrinho'])
            st.dataframe(df_c[['nome', 'qtd', 'preco', 'total']], hide_index=True, use_container_width=True)
            total = df_c['total'].sum()
            st.write(f"### Total a Pagar: R$ {total:.2f}")
            
            # Restaurei o texto EXATO da sua imagem:
            pagamento = st.radio("Como o cliente pagou?", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"], horizontal=True)
            
            # Restaurei o botão EXATO da sua imagem:
            if st.button("✅ FECHAR CAIXA", type="primary"):
                conn = conectar()
                c = conn.cursor()
                data_h = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO Pedidos (data, id_cliente, valor_total, pagamento) VALUES (?,?,?,?)", 
                          (data_h, cli_map[nome_c], total, pagamento))
                id_ped = c.lastrowid
                for item in st.session_state['carrinho']:
                    c.execute("INSERT INTO Pedidos_Itens (id_pedido, id_produto, valor_unitario, quantidade, total) VALUES (?,?,?,?,?)",
                              (id_ped, item['id'], item['preco'], item['qtd'], item['total']))
                conn.commit(); conn.close()
                st.session_state['carrinho'] = []
                st.balloons(); st.success("Venda Realizada!"); st.rerun()

# =================================================================================
# PÁGINAS DE CADASTRO
# =================================================================================
elif pagina == "👥 Clientes":
    st.header("Clientes")
    tab1, tab2 = st.tabs(["Novo", "Excluir"])
    with tab1:
        with st.form("f_cli"):
            n = st.text_input("Nome"); t = st.text_input("Tel"); e = st.text_input("End")
            if st.form_submit_button("Salvar") and n:
                c = conectar(); c.execute("INSERT INTO Clientes (nome, telefone, endereco) VALUES (?,?,?)", (n,t,e)); c.commit(); c.close(); st.rerun()
    with tab2:
        df = carregar_dados("Clientes")
        if not df.empty:
            d = st.selectbox("Excluir:", df['nome'])
            if st.button("Apagar"):
                c = conectar(); c.execute("DELETE FROM Clientes WHERE nome=?", (d,)); c.commit(); c.close(); st.rerun()
    st.dataframe(carregar_dados("Clientes"), use_container_width=True)

elif pagina == "🍰 Cardápio":
    st.header("Cardápio")
    tab1, tab2 = st.tabs(["Novo", "Excluir"])
    with tab1:
        with st.form("f_prod"):
            n = st.text_input("Nome"); p = st.number_input("Preço", 0.0); t = st.text_input("Tam")
            if st.form_submit_button("Salvar") and n:
                c = conectar(); c.execute("INSERT INTO Produtos (nome, preco, tamanho) VALUES (?,?,?)", (n,p,t)); c.commit(); c.close(); st.rerun()
    with tab2:
        df = carregar_dados("Produtos")
        if not df.empty:
            d = st.selectbox("Excluir:", df['nome'])
            if st.button("Apagar"):
                c = conectar(); c.execute("DELETE FROM Produtos WHERE nome=?", (d,)); c.commit(); c.close(); st.rerun()
    st.dataframe(carregar_dados("Produtos"), use_container_width=True)