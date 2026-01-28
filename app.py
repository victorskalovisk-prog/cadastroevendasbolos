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
    c.execute("""CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, tamanho TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_venda TEXT, data_entrega TEXT, id_cliente INTEGER, valor_total REAL, pagamento TEXT, observacoes TEXT, status TEXT DEFAULT 'Pendente')""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos_Itens (id INTEGER PRIMARY KEY AUTOINCREMENT, id_pedido INTEGER, id_produto INTEGER, valor_unitario REAL, quantidade INTEGER, total REAL)""")
    conn.commit()
    conn.close()

criar_tabelas()

def carregar_dados(tabela):
    conn = conectar()
    df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df

# --- BARRA LATERAL (LOGO + MENU) ---
try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.markdown("# 🎂 Nossa Que Bolo!")

pagina = st.sidebar.radio("Navegação:", ["📊 Dashboard", "🛒 Nova Encomenda", "👨‍🍳 Produção & Histórico", "🏆 Ranking de Clientes", "👥 Clientes", "🍰 Cardápio"])

# =================================================================================
# PÁGINA: DASHBOARD (MANTIDA)
# =================================================================================
if pagina == "📊 Dashboard":
    st.header("📊 Painel de Controle")
    conn = conectar()
    sql = "SELECT Pedidos.id, Pedidos.data_venda, Pedidos.valor_total, Pedidos.pagamento, Pedidos_Itens.quantidade, Produtos.nome as produto FROM Pedidos_Itens JOIN Pedidos ON Pedidos_Itens.id_pedido = Pedidos.id JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id"
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if not df.empty:
        df_vendas = df.drop_duplicates(subset=['id'])
        c1, c2 = st.columns(2)
        c1.metric("💰 Faturamento Total", f"R$ {df_vendas['valor_total'].sum():.2f}")
        c2.metric("📦 Pedidos Totais", len(df_vendas))
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_vendas, values='valor_total', names='pagamento', title="Pagamentos", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            df_prod = df.groupby("produto")["quantidade"].sum().reset_index()
            fig2 = px.bar(df_prod, x="quantidade", y="produto", orientation='h', title="Top Produtos", color_discrete_sequence=['#8D6E63'])
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Aguardando primeiras vendas...")

# =================================================================================
# PÁGINA: RANKING DE CLIENTES VIP (NOVIDADE!)
# =================================================================================
elif pagina == "🏆 Ranking de Clientes":
    st.header("🏆 Seus Clientes Mais Fiéis")
    
    conn = conectar()
    # Busca pedidos cruzando com nome dos clientes
    query = """
    SELECT Clientes.nome as Cliente, Pedidos.valor_total
    FROM Pedidos
    JOIN Clientes ON Pedidos.id_cliente = Clientes.id
    """
    df_vip = pd.read_sql_query(query, conn)
    conn.close()

    if not df_vip.empty:
        # Agrupamento por cliente
        ranking = df_vip.groupby("Cliente").agg(
            Total_Gasto=('valor_total', 'sum'),
            Qtd_Pedidos=('valor_total', 'count')
        ).reset_index()
        
        ranking['Ticket_Medio'] = ranking['Total_Gasto'] / ranking['Qtd_Pedidos']
        ranking = ranking.sort_values(by="Total_Gasto", ascending=False)

        # KPIs dos VIPs
        top_cliente = ranking.iloc[0]['Cliente']
        gasto_top = ranking.iloc[0]['Total_Gasto']

        c1, c2 = st.columns(2)
        c1.success(f"🥇 **Cliente Ouro:** {top_cliente}")
        c2.info(f"💰 **Total Gasto por ele:** R$ {gasto_top:.2f}")

        st.divider()
        
        col_graf, col_tab = st.columns([3, 2])
        
        with col_graf:
            st.subheader("Gráfico de Clientes Ouro")
            fig_vip = px.bar(ranking.head(10), x="Total_Gasto", y="Cliente", orientation='h', 
                             text="Total_Gasto", color="Total_Gasto",
                             color_continuous_scale='RdBu', title="Top 10 Clientes (R$)")
            st.plotly_chart(fig_vip, use_container_width=True)
            
        with col_tab:
            st.subheader("Dados Detalhados")
            # Formatação para exibir na tabela
            st.dataframe(ranking.style.format({"Total_Gasto": "R$ {:.2f}", "Ticket_Medio": "R$ {:.2f}"}), 
                         hide_index=True, use_container_width=True)
            
        st.info("💡 **Dica de Gestão:** Clientes que aparecem aqui são ótimos candidatos para receberem brindes ou promoções exclusivas no WhatsApp!")
    else:
        st.warning("Ainda não há dados de vendas suficientes para gerar o ranking.")

# =================================================================================
# PÁGINA: NOVA ENCOMENDA
# =================================================================================
elif pagina == "🛒 Nova Encomenda":
    st.header("🛒 Registrar Novo Pedido")
    if 'carrinho' not in st.session_state: st.session_state['carrinho'] = []

    conn = conectar()
    clientes = carregar_dados("Clientes")
    produtos = carregar_dados("Produtos")
    conn.close()

    if clientes.empty or produtos.empty:
        st.warning("Cadastre clientes e produtos primeiro.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            cli_map = dict(zip(clientes['nome'], clientes['id']))
            nome_c = st.selectbox("Cliente:", list(cli_map.keys()))
        with c2:
            data_ent = st.date_input("📅 Data da Entrega", min_value=date.today())

        obs = st.text_area("📝 Observações (Detalhes do bolo):")
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
# PÁGINA: PRODUÇÃO & HISTÓRICO
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
        status_filtro = st.multiselect("Filtrar por Status:", ["Pendente", "Em Produção", "Pronto", "Finalizado"], default=["Pendente", "Em Produção", "Pronto"])
        df_filtrado = df[df['status'].isin(status_filtro)]
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        st.divider()
        sel_list = df.apply(lambda x: f"Pedido #{x['id']} - {x['Cliente']} ({x['status']})", axis=1)
        pedido_sel = st.selectbox("Selecione um pedido para agir:", sel_list)
        id_sel = pedido_sel.split("#")[1].split(" -")[0]

        c1, c2 = st.columns(2)
        with c1:
            novo_status = st.selectbox("Mudar status para:", ["Pendente", "Em Produção", "Pronto", "Finalizado"])
            if st.button("🔄 Atualizar Status"):
                conn = conectar(); c = conn.cursor()
                c.execute("UPDATE Pedidos SET status = ? WHERE id = ?", (novo_status, id_sel))
                conn.commit(); conn.close()
                st.success(f"Pedido #{id_sel} agora está {novo_status}!"); st.rerun()
        with c2:
            if st.button("📄 Gerar Comprovante"):
                dados = df[df['id'] == int(id_sel)].iloc[0]
                texto = f"*🎂 PEDIDO #{id_sel}*\n*Cliente:* {dados['Cliente']}\n*Entrega:* {dados['data_entrega']}\n*Status:* {dados['status']}\n*Obs:* {dados['observacoes']}\n*Total:* R$ {dados['valor_total']:.2f}"
                st.code(texto)
    else:
        st.info("Nenhum pedido registrado.")

# =================================================================================
# CADASTROS
# =================================================================================
elif pagina == "👥 Clientes":
    st.header("Gerenciar Clientes")
    with st.form("cli"):
        n = st.text_input("Nome"); t = st.text_input("WhatsApp"); e = st.text_input("Endereço")
        if st.form_submit_button("Cadastrar"):
            conn = conectar(); c = conn.cursor(); c.execute("INSERT INTO Clientes (nome, telefone, endereco) VALUES (?,?,?)", (n,t,e)); conn.commit(); conn.close(); st.rerun()
    st.dataframe(carregar_dados("Clientes"), use_container_width=True)

elif pagina == "🍰 Cardápio":
    st.header("Gerenciar Cardápio")
    with st.form("prod"):
        n = st.text_input("Bolo/Doce"); p = st.number_input("Preço", 0.0); t = st.text_input("Tamanho/Peso")
        if st.form_submit_button("Cadastrar"):
            conn = conectar(); c = conn.cursor(); c.execute("INSERT INTO Produtos (nome, preco, tamanho) VALUES (?,?,?)", (n,p,t)); conn.commit(); conn.close(); st.rerun()
    st.dataframe(carregar_dados("Produtos"), use_container_width=True)