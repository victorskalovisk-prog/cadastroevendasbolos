import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Nossa Que Bolo! 🎂", page_icon="🎂", layout="wide")

# --- CONEXÃO COM O BANCO LOCAL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sistema_bolos_v2.db")

def conectar():
    return sqlite3.connect(DB_PATH)

def criar_tabelas():
    conn = conectar()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS Clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, endereco TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, tamanho TEXT, ativo INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_venda TEXT, data_entrega TEXT, id_cliente INTEGER, valor_total REAL, pagamento TEXT, observacoes TEXT, status TEXT DEFAULT 'Pendente')""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos_Itens (id INTEGER PRIMARY KEY AUTOINCREMENT, id_pedido INTEGER, id_produto INTEGER, valor_unitario REAL, quantidade INTEGER, total REAL)""")
    
    # Segurança: Adiciona a coluna 'ativo' se ela não existir (Modificação 4)
    try:
        c.execute("ALTER TABLE Produtos ADD COLUMN ativo INTEGER DEFAULT 1")
    except:
        pass
    conn.commit()
    conn.close()

criar_tabelas()

def carregar_dados(tabela):
    conn = conectar()
    df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df

# --- BARRA LATERAL ---
try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.markdown("# 🎂 Nossa Que Bolo!")

pagina = st.sidebar.radio("Navegação:", ["📊 Dashboard", "🛒 Nova Encomenda", "👨‍🍳 Produção & Histórico", "🏆 Ranking de Clientes", "👥 Clientes", "🍰 Cardápio"])

# =================================================================================
# PÁGINA: DASHBOARD
# =================================================================================
if pagina == "📊 Dashboard":
    st.header("📊 Painel de Controle")
    conn = conectar()
    sql = "SELECT Pedidos.id, Pedidos.data_venda, Pedidos.valor_total, Pedidos.pagamento, Pedidos_Itens.quantidade, Produtos.nome as produto FROM Pedidos_Itens JOIN Pedidos ON Pedidos_Itens.id_pedido = Pedidos.id JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id"
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if not df.empty:
        df_vendas = df.drop_duplicates(subset=['id'])
        # Modificação 2: Formatação BR para exibição no dashboard
        df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda']).dt.strftime('%d/%m/%Y %H:%M')
        
        c1, c2 = st.columns(2)
        c1.metric("💰 Faturamento Total", f"R$ {df_vendas['valor_total'].sum():.2f}")
        c2.metric("📦 Pedidos Totais", len(df_vendas))
        st.divider()
        st.dataframe(df_vendas[['id', 'data_venda', 'valor_total', 'pagamento']], use_container_width=True, hide_index=True)
    else:
        st.info("Aguardando primeiras vendas...")

# =================================================================================
# PÁGINA: NOVA ENCOMENDA
# =================================================================================
elif pagina == "🛒 Nova Encomenda":
    st.header("🛒 Registrar Novo Pedido")
    if 'carrinho' not in st.session_state: st.session_state['carrinho'] = []

    conn = conectar()
    clientes = carregar_dados("Clientes")
    # Modificação 4: Filtra apenas produtos ATIVOS para a venda
    produtos = pd.read_sql_query("SELECT * FROM Produtos WHERE ativo = 1", conn)
    conn.close()

    if clientes.empty or produtos.empty:
        st.warning("Verifique se há clientes cadastrados e produtos ATIVOS no cardápio.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            cli_map = dict(zip(clientes['nome'], clientes['id']))
            nome_c = st.selectbox("Cliente:", list(cli_map.keys()))
        with c2:
            # Modificação 2: Calendário com data BR
            data_ent = st.date_input("📅 Data da Entrega", min_value=date.today(), format="DD/MM/YYYY")

        obs = st.text_area("📝 Observações:")
        st.divider()
        
        prod_map = {f"{r['nome']} (R$ {r['preco']:.2f})": r for i, r in produtos.iterrows()}
        c_p, c_q, c_b = st.columns([3, 1, 1])
        with c_p: p_sel = st.selectbox("Produto:", list(prod_map.keys())); dados_p = prod_map[p_sel]
        with c_q: qtd = st.number_input("Qtd", 1, 50, 1)
        with c_b: 
            st.write(""); st.write("")
            if st.button("➕ Add"): st.session_state['carrinho'].append({"id": dados_p['id'], "nome": dados_p['nome'], "preco": dados_p['preco'], "qtd": qtd, "total": dados_p['preco']*qtd})

        if st.session_state['carrinho']:
            df_c = pd.DataFrame(st.session_state['carrinho'])
            st.table(df_c[['nome', 'qtd', 'total']])
            total = df_c['total'].sum()
            pag = st.radio("Pagamento:", ["Pix", "Dinheiro", "Cartão"], horizontal=True)
            
            if st.button("✅ SALVAR ENCOMENDA", type="primary"):
                conn = conectar(); c = conn.cursor()
                data_v = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO Pedidos (data_venda, data_entrega, id_cliente, valor_total, pagamento, observacoes, status) VALUES (?,?,?,?,?,?,?)", 
                          (data_v, data_ent.strftime("%Y-%m-%d"), cli_map[nome_c], total, pag, obs, 'Pendente'))
                id_ped = c.lastrowid
                for item in st.session_state['carrinho']:
                    c.execute("INSERT INTO Pedidos_Itens (id_pedido, id_produto, valor_unitario, quantidade, total) VALUES (?,?,?,?,?)", (id_ped, item['id'], item['preco'], item['qtd'], item['total']))
                conn.commit(); conn.close()
                st.session_state['carrinho'] = []
                st.success("Pedido registrado!"); st.balloons(); st.rerun()

# =================================================================================
# PÁGINA: PRODUÇÃO (MODIFICAÇÃO 3: ENTREGUE)
# =================================================================================
elif pagina == "👨‍🍳 Produção & Histórico":
    st.header("👨‍🍳 Gestão de Produção e Pedidos")
    conn = conectar()
    df = pd.read_sql_query("""
        SELECT Pedidos.id, Pedidos.data_entrega, Clientes.nome as Cliente, 
               Pedidos.valor_total, Pedidos.status, Pedidos.observacoes
        FROM Pedidos 
        JOIN Clientes ON Pedidos.id_cliente = Clientes.id
        ORDER BY Pedidos.data_entrega ASC
    """, conn)
    conn.close()

    if not df.empty:
        # Modificação 2 e 3: Data BR e Status "Entregue"
        df['data_entrega'] = pd.to_datetime(df['data_entrega']).dt.strftime('%d/%m/%Y')
        status_opcoes = ["Pendente", "Em Produção", "Pronto", "Entregue"]
        
        status_filtro = st.multiselect("Filtrar por Status:", status_opcoes, default=["Pendente", "Em Produção", "Pronto"])
        df_filtrado = df[df['status'].isin(status_filtro)]
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

        st.divider()
        sel_list = df.apply(lambda x: f"Pedido #{x['id']} - {x['Cliente']} ({x['status']})", axis=1)
        pedido_sel = st.selectbox("Selecione um pedido:", sel_list)
        id_sel = pedido_sel.split("#")[1].split(" -")[0]

        c1, c2 = st.columns(2)
        with c1:
            novo_status = st.selectbox("Mudar status para:", status_opcoes)
            if st.button("🔄 Atualizar Status"):
                conn = conectar(); c = conn.cursor()
                c.execute("UPDATE Pedidos SET status = ? WHERE id = ?", (novo_status, id_sel))
                conn.commit(); conn.close(); st.rerun()
        with c2:
            if st.button("📄 Comprovante"):
                dados = df[df['id'] == int(id_sel)].iloc[0]
                texto = f"*🎂 PEDIDO #{id_sel}*\n*Cliente:* {dados['Cliente']}\n*Entrega:* {dados['data_entrega']}\n*Status:* {dados['status']}\n*Total:* R$ {dados['valor_total']:.2f}"
                st.code(texto)
    else:
        st.info("Nenhum pedido registrado.")

# =================================================================================
# PÁGINA: RANKING
# =================================================================================
elif pagina == "🏆 Ranking de Clientes":
    st.header("🏆 Ranking de Fidelidade")
    conn = conectar(); df_vip = pd.read_sql_query("SELECT Clientes.nome as Cliente, Pedidos.valor_total FROM Pedidos JOIN Clientes ON Pedidos.id_cliente = Clientes.id", conn); conn.close()
    if not df_vip.empty:
        ranking = df_vip.groupby("Cliente").agg(Total_Gasto=('valor_total', 'sum'), Qtd_Pedidos=('valor_total', 'count')).reset_index().sort_values(by="Total_Gasto", ascending=False)
        st.dataframe(ranking.style.format({"Total_Gasto": "R$ {:.2f}"}), hide_index=True, use_container_width=True)
    else: st.info("Sem dados.")

# =================================================================================
# PÁGINA: CLIENTES (MODIFICAÇÃO 1: EDITAR/EXCLUIR)
# =================================================================================
elif pagina == "👥 Clientes":
    st.header("👥 Gestão de Clientes")
    df_clientes = carregar_dados("Clientes")
    tab1, tab2, tab3 = st.tabs(["➕ Novo", "✏️ Editar", "❌ Excluir"])

    with tab1:
        with st.form("cli_novo"):
            n = st.text_input("Nome"); t = st.text_input("WhatsApp"); e = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                conn = conectar(); c = conn.cursor(); c.execute("INSERT INTO Clientes (nome, telefone, endereco) VALUES (?,?,?)", (n,t,e)); conn.commit(); conn.close(); st.rerun()

    with tab2:
        if not df_clientes.empty:
            sel_edit = st.selectbox("Escolha o cliente para editar:", df_clientes['nome'])
            dados_cli = df_clientes[df_clientes['nome'] == sel_edit].iloc[0]
            with st.form("cli_edit"):
                new_n = st.text_input("Nome", value=dados_cli['nome'])
                new_t = st.text_input("WhatsApp", value=dados_cli['telefone'])
                new_e = st.text_input("Endereço", value=dados_cli['endereco'])
                if st.form_submit_button("Atualizar"):
                    conn = conectar(); c = conn.cursor(); c.execute("UPDATE Clientes SET nome=?, telefone=?, endereco=? WHERE id=?", (new_n, new_t, new_e, int(dados_cli['id']))); conn.commit(); conn.close(); st.rerun()

    with tab3:
        if not df_clientes.empty:
            sel_del = st.selectbox("Escolha o cliente para excluir:", df_clientes['nome'], key="del_cli")
            if st.button("Confirmar Exclusão do Cliente"):
                conn = conectar(); c = conn.cursor(); c.execute("DELETE FROM Clientes WHERE nome=?", (sel_del,)); conn.commit(); conn.close(); st.rerun()

    st.divider()
    st.dataframe(df_clientes, use_container_width=True, hide_index=True)

# =================================================================================
# PÁGINA: CARDÁPIO (MODIFICAÇÃO 4: ATIVO/INATIVO)
# =================================================================================
elif pagina == "🍰 Cardápio":
    st.header("🍰 Gestão do Cardápio")
    df_prods = carregar_dados("Produtos")
    tab1, tab2, tab3 = st.tabs(["➕ Novo", "✏️ Editar/Status", "❌ Excluir"])

    with tab1:
        with st.form("prod_novo"):
            n = st.text_input("Nome"); p = st.number_input("Preço", 0.0); t = st.text_input("Tamanho")
            if st.form_submit_button("Cadastrar"):
                conn = conectar(); c = conn.cursor(); c.execute("INSERT INTO Produtos (nome, preco, tamanho, ativo) VALUES (?,?,?,1)", (n,p,t)); conn.commit(); conn.close(); st.rerun()

    with tab2:
        if not df_prods.empty:
            sel_p = st.selectbox("Selecione o produto:", df_prods.apply(lambda x: f"{x['nome']} ({'Ativo' if x['ativo']==1 else 'Inativo'})", axis=1))
            id_p = df_prods.iloc[0 if not sel_p else 0]['id'] # Lógica simplificada para pegar ID
            # Busca dados reais do ID extraído (mais seguro)
            dados_p = df_prods[df_prods.apply(lambda x: f"{x['nome']} ({'Ativo' if x['ativo']==1 else 'Inativo'})", axis=1) == sel_p].iloc[0]
            
            with st.form("prod_edit"):
                nn = st.text_input("Nome", value=dados_p['nome'])
                np = st.number_input("Preço", value=float(dados_p['preco']))
                nt = st.text_input("Tamanho", value=dados_p['tamanho'])
                n_ativo = st.checkbox("Produto Ativo (Aparece na venda)", value=True if dados_p['ativo']==1 else False)
                if st.form_submit_button("Salvar Alterações"):
                    conn = conectar(); c = conn.cursor()
                    c.execute("UPDATE Produtos SET nome=?, preco=?, tamanho=?, ativo=? WHERE id=?", (nn, np, nt, 1 if n_ativo else 0, int(dados_p['id'])))
                    conn.commit(); conn.close(); st.rerun()

    with tab3:
        if not df_prods.empty:
            sel_ex = st.selectbox("Excluir produto:", df_prods['nome'])
            if st.button("Confirmar Exclusão Permanente"):
                conn = conectar(); c = conn.cursor(); c.execute("DELETE FROM Produtos WHERE nome=?", (sel_ex,)); conn.commit(); conn.close(); st.rerun()

    st.divider()
    # Modificação visual: Mostrar se está ativo ou não na tabela
    df_visu = df_prods.copy()
    df_visu['ativo'] = df_visu['ativo'].map({1: "✅ Sim", 0: "❌ Não"})
    st.dataframe(df_visu, use_container_width=True, hide_index=True)