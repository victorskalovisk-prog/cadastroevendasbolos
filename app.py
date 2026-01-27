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
# Mantivemos o v2 para você não perder os dados que já lançou
DB_PATH = os.path.join(BASE_DIR, "sistema_bolos_v2.db")

def conectar():
    return sqlite3.connect(DB_PATH)

def criar_tabelas():
    conn = conectar()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS Clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, endereco TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, tamanho TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_venda TEXT, data_entrega TEXT, id_cliente INTEGER, valor_total REAL, pagamento TEXT, observacoes TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS Pedidos_Itens (id INTEGER PRIMARY KEY AUTOINCREMENT, id_pedido INTEGER, id_produto INTEGER, valor_unitario REAL, quantidade INTEGER, total REAL)""")
    conn.commit()
    conn.close()

criar_tabelas()

def carregar_dados(tabela):
    conn = conectar()
    df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df

# --- BARRA LATERAL ---
st.sidebar.title("🎂 Gestão Completa")
pagina = st.sidebar.radio("Navegação:", ["📊 Dashboard", "🛒 Nova Encomenda", "📂 Histórico & Comprovante", "👥 Clientes", "🍰 Cardápio"])

st.sidebar.markdown("---")
if pagina == "📊 Dashboard":
    st.sidebar.header("🗓️ Filtros")
    filtro_periodo = st.sidebar.selectbox("Período:", ["Todo o Histórico", "Últimos 7 dias", "Hoje"])
else:
    filtro_periodo = "Todo o Histórico"

# =================================================================================
# PÁGINA: DASHBOARD
# =================================================================================
if pagina == "📊 Dashboard":
    st.header("📊 Painel de Controle")

    conn = conectar()
    sql = """
    SELECT 
        Pedidos.id as id_pedido,
        Pedidos.data_venda as data,
        Pedidos.valor_total,
        Pedidos.pagamento,
        Pedidos_Itens.quantidade,
        Produtos.nome as produto
    FROM Pedidos_Itens
    JOIN Pedidos ON Pedidos_Itens.id_pedido = Pedidos.id
    JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id
    ORDER BY Pedidos.data_venda DESC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
        df['dia'] = df['data'].dt.date  
        data_atual = datetime.now()

        if filtro_periodo == "Últimos 7 dias":
            data_corte = data_atual - timedelta(days=7)
            df = df[df['data'] >= data_corte]
        elif filtro_periodo == "Hoje":
            df = df[df['dia'] == data_atual.date()]

        if df.empty:
            st.warning("Sem dados neste período.")
        else:
            df_vendas_unicas = df.drop_duplicates(subset=['id_pedido'])
            faturamento = df_vendas_unicas['valor_total'].sum()
            qtd_pedidos = df_vendas_unicas['id_pedido'].count()

            c1, c2 = st.columns(2)
            c1.metric("💰 Faturamento", f"R$ {faturamento:.2f}")
            c2.metric("📦 Pedidos Feitos", qtd_pedidos)
            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Formas de Pagamento")
                cores = {"Pix": "#00C1AF", "Dinheiro": "#2E7D32", "Cartão de Crédito": "#1565C0", "Cartão de Débito": "#EF6C00"}
                fig = px.pie(df_vendas_unicas, values='valor_total', names='pagamento', color='pagamento', color_discrete_map=cores)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("Mais Vendidos")
                fig2 = px.bar(df.groupby("produto")["quantidade"].sum().reset_index().sort_values("quantidade"), x="quantidade", y="produto", orientation='h', color_discrete_sequence=['#8D6E63'])
                st.plotly_chart(fig2, use_container_width=True)
            
            # Botão Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Excel", csv, "vendas.csv", "text/csv")

    else:
        st.info("Nenhuma venda registrada.")

# =================================================================================
# PÁGINA: NOVA ENCOMENDA
# =================================================================================
elif pagina == "🛒 Nova Encomenda":
    st.header("🛒 Registrar Pedido / Encomenda")
    if 'carrinho' not in st.session_state: st.session_state['carrinho'] = []

    conn = conectar()
    clientes = pd.read_sql_query("SELECT id, nome FROM Clientes", conn)
    produtos = pd.read_sql_query("SELECT id, nome, preco FROM Produtos", conn)
    conn.close()

    if clientes.empty or produtos.empty:
        st.warning("Cadastre clientes e produtos primeiro.")
    else:
        # 1. Dados do Cliente e Entrega
        c1, c2 = st.columns([2, 1])
        with c1:
            cli_map = dict(zip(clientes['nome'], clientes['id']))
            nome_c = st.selectbox("Cliente:", list(cli_map.keys()))
        with c2:
            data_entrega = st.date_input("📅 Data da Entrega/Retirada", min_value=date.today())

        # Campo de Observações
        obs = st.text_area("📝 Observações do Bolo (Ex: Escrever 'Parabéns', Recheio Extra, etc):")
        
        st.divider()
        
        # 2. Produtos
        prod_map = {f"{r['nome']} (R$ {r['preco']:.2f})": r for i, r in produtos.iterrows()}
        c1, c2, c3 = st.columns([3,1,1])
        with c1: 
            p_sel = st.selectbox("Produto:", list(prod_map.keys()))
            dados_p = prod_map[p_sel]
        with c2: qtd = st.number_input("Qtd", 1, 50, 1)
        with c3:
            st.write(""); st.write("")
            if st.button("➕ Add"):
                st.session_state['carrinho'].append({"id": dados_p['id'], "nome": dados_p['nome'], "preco": dados_p['preco'], "qtd": qtd, "total": dados_p['preco']*qtd})

        # 3. Fechamento
        if st.session_state['carrinho']:
            df_c = pd.DataFrame(st.session_state['carrinho'])
            st.dataframe(df_c[['nome', 'qtd', 'preco', 'total']], hide_index=True, use_container_width=True)
            total = df_c['total'].sum()
            st.write(f"### Total: R$ {total:.2f}")
            
            pagamento = st.radio("Pagamento:", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"], horizontal=True)
            
            if st.button("✅ CONFIRMAR ENCOMENDA", type="primary"):
                conn = conectar()
                c = conn.cursor()
                data_venda = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data_entrega_str = data_entrega.strftime("%Y-%m-%d")
                
                c.execute("""
                    INSERT INTO Pedidos (data_venda, data_entrega, id_cliente, valor_total, pagamento, observacoes) 
                    VALUES (?,?,?,?,?,?)""", 
                    (data_venda, data_entrega_str, cli_map[nome_c], total, pagamento, obs))
                
                id_ped = c.lastrowid
                for item in st.session_state['carrinho']:
                    c.execute("INSERT INTO Pedidos_Itens (id_pedido, id_produto, valor_unitario, quantidade, total) VALUES (?,?,?,?,?)",
                              (id_ped, item['id'], item['preco'], item['qtd'], item['total']))
                conn.commit(); conn.close()
                st.session_state['carrinho'] = []
                st.balloons(); st.success("Encomenda Salva! Vá em Histórico para ver o comprovante."); st.rerun()

# =================================================================================
# PÁGINA: HISTÓRICO COM GERADOR DE COMPROVANTE (NOVO!)
# =================================================================================
elif pagina == "📂 Histórico & Comprovante":
    st.header("📂 Histórico & Comprovantes")
    
    conn = conectar()
    df_header = pd.read_sql_query("""
        SELECT Pedidos.id, Pedidos.data_entrega, Clientes.nome as Cliente, 
               Pedidos.valor_total, Pedidos.pagamento, Pedidos.observacoes
        FROM Pedidos 
        JOIN Clientes ON Pedidos.id_cliente = Clientes.id
        ORDER BY Pedidos.id DESC
    """, conn)
    conn.close()

    if not df_header.empty:
        # 1. Seletor de Pedido
        lista_pedidos = df_header.apply(lambda x: f"Pedido #{x['id']} - {x['Cliente']} (Entrega: {x['data_entrega']})", axis=1)
        pedido_selecionado = st.selectbox("🔎 Selecione uma encomenda para ver detalhes e comprovante:", lista_pedidos)
        
        # Pega o ID do texto selecionado
        id_selecionado = pedido_selecionado.split("#")[1].split(" -")[0]
        
        # Filtra os dados desse pedido específico
        dados_pedido = df_header[df_header['id'] == int(id_selecionado)].iloc[0]
        
        # Busca os itens desse pedido
        conn = conectar()
        itens_pedido = pd.read_sql_query(f"""
            SELECT Produtos.nome, Pedidos_Itens.quantidade, Pedidos_Itens.total 
            FROM Pedidos_Itens 
            JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id 
            WHERE id_pedido = {id_selecionado}
        """, conn)
        conn.close()

        st.divider()

        # Colunas: Esquerda (Comprovante), Direita (Ações)
        col_esq, col_dir = st.columns([1, 1])
        
        with col_esq:
            st.subheader("📄 Comprovante para WhatsApp")
            # Montando o texto formatado
            texto_zap = f"*🎂 PEDIDO #{dados_pedido['id']}* - Nossa Que Bolo!\n"
            texto_zap += f"👤 *Cliente:* {dados_pedido['Cliente']}\n"
            texto_zap += f"📅 *Entrega:* {dados_pedido['data_entrega']}\n\n"
            texto_zap += "*🍰 ITENS:*\n"
            
            for index, row in itens_pedido.iterrows():
                texto_zap += f"{row['quantidade']}x {row['nome']} (R$ {row['total']:.2f})\n"
            
            texto_zap += f"\n📝 *Obs:* {dados_pedido['observacoes']}\n"
            texto_zap += f"💰 *TOTAL:* R$ {dados_pedido['valor_total']:.2f}\n"
            texto_zap += f"💳 *Pagamento:* {dados_pedido['pagamento']}\n"
            texto_zap += "--------------------------------"

            # Mostra o texto em uma caixa de código (fácil de copiar)
            st.code(texto_zap, language='markdown')
            st.caption("👆 Clique no ícone de copiar acima e cole no WhatsApp!")

        with col_dir:
            st.subheader("⚙️ Ações")
            st.write(f"**Status:** Pedido Ativo")
            st.write(f"**Valor:** R$ {dados_pedido['valor_total']:.2f}")
            
            st.write("")
            st.write("")
            if st.button("🗑️ Excluir/Cancelar este Pedido", type="secondary"):
                conn = conectar()
                c = conn.cursor()
                c.execute("DELETE FROM Pedidos_Itens WHERE id_pedido = ?", (id_selecionado,))
                c.execute("DELETE FROM Pedidos WHERE id = ?", (id_selecionado,))
                conn.commit()
                conn.close()
                st.error("Pedido cancelado!")
                st.rerun()

    else:
        st.info("Nenhuma encomenda registrada ainda.")

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