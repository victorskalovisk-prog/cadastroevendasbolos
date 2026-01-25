import streamlit as st
import sqlite3
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Nossa Que bolo", page_icon="🎂", layout="wide")

# --- CONEXÃO COM O BANCO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "banco_dados.db")

def conectar():
    return sqlite3.connect(DB_PATH)

# --- FUNÇÕES ÚTEIS ---
def carregar_dados(tabela):
    conn = conectar()
    df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df

# --- INTERFACE PRINCIPAL (SIDEBAR) ---
st.sidebar.title("🎂 Menu Principal")
pagina = st.sidebar.radio(
    "Ir para:",
    ["🛒 Nova Venda", "👥 Clientes", "🍰 Produtos", "📊 Relatórios"]
)

# =================================================================================
# PÁGINA: NOVA VENDA
# =================================================================================
if pagina == "🛒 Nova Venda":
    st.header("🛒 Registrar Nova Venda")

    if 'carrinho' not in st.session_state:
        st.session_state['carrinho'] = []

    conn = conectar()

    # Seleção de Cliente
    clientes = pd.read_sql_query("SELECT id, nome FROM Clientes", conn)
    
    if clientes.empty:
        st.warning("Cadastre clientes antes de fazer uma venda!")
    else:
        opcoes_clientes = dict(zip(clientes['nome'], clientes['id']))
        nome_cliente = st.selectbox("Selecione o Cliente:", list(opcoes_clientes.keys()))
        id_cliente_selecionado = opcoes_clientes[nome_cliente]

        st.divider()

        # Seleção de Produtos
        col1, col2, col3 = st.columns([3, 1, 1])
        
        produtos = pd.read_sql_query("SELECT id, nome, preco FROM Produtos", conn)
        
        if produtos.empty:
            st.warning("Cadastre produtos no cardápio primeiro!")
        else:
            opcoes_produtos = {f"{row['nome']} (R$ {row['preco']:.2f})": row for index, row in produtos.iterrows()}
            
            with col1:
                prod_key = st.selectbox("Escolha o Produto:", list(opcoes_produtos.keys()))
                dados_prod = opcoes_produtos[prod_key]
            
            with col2:
                qtd = st.number_input("Qtd:", min_value=1, value=1)
            
            with col3:
                st.write("") 
                st.write("") 
                if st.button("➕ Adicionar"):
                    item = {
                        "id_produto": dados_prod['id'],
                        "nome": dados_prod['nome'],
                        "preco": dados_prod['preco'],
                        "quantidade": qtd,
                        "total": dados_prod['preco'] * qtd
                    }
                    st.session_state['carrinho'].append(item)
                    st.success(f"{dados_prod['nome']} adicionado!")

            # Carrinho e Finalização
            st.subheader("🛍️ Carrinho Atual")
            
            if st.session_state['carrinho']:
                df_carrinho = pd.DataFrame(st.session_state['carrinho'])
                st.dataframe(df_carrinho[['nome', 'preco', 'quantidade', 'total']], hide_index=True, use_container_width=True)
                
                total_venda = df_carrinho['total'].sum()
                st.write(f"### Total a Pagar: R$ {total_venda:.2f}")

                if st.button("✅ FINALIZAR VENDA", type="primary"):
                    cursor = conn.cursor()
                    try:
                        data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("INSERT INTO Pedidos (data, id_cliente, valor_total) VALUES (?, ?, ?)", 
                                    (data_hoje, id_cliente_selecionado, total_venda))
                        id_pedido = cursor.lastrowid

                        for item in st.session_state['carrinho']:
                            cursor.execute("""
                                INSERT INTO Pedidos_Itens (id_pedido, id_produto, valor_unitario, quantidade, total)
                                VALUES (?, ?, ?, ?, ?)
                            """, (id_pedido, item['id_produto'], item['preco'], item['quantidade'], item['total']))
                        
                        conn.commit()
                        st.session_state['carrinho'] = []
                        st.balloons()
                        st.success(f"Venda #{id_pedido} realizada com sucesso!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            else:
                st.info("O carrinho está vazio.")

    conn.close()

# =================================================================================
# PÁGINA: CLIENTES (Com Exclusão)
# =================================================================================
elif pagina == "👥 Clientes":
    st.header("Gerenciar Clientes")
    
    # Abas para separar Cadastro de Exclusão
    tab1, tab2 = st.tabs(["➕ Cadastrar", "🗑️ Excluir"])
    
    with tab1:
        with st.form("form_cliente"):
            nome = st.text_input("Nome Completo")
            tel = st.text_input("Telefone")
            end = st.text_input("Endereço")
            submit = st.form_submit_button("Salvar Cliente")
            
            if submit and nome:
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Clientes (nome, telefone, endereco) VALUES (?, ?, ?)", (nome, tel, end))
                conn.commit()
                conn.close()
                st.success(f"Cliente {nome} cadastrado!")
                st.rerun()

    with tab2:
        st.write("Cuidado: Excluir um cliente pode remover o nome dele do histórico de vendas.")
        conn = conectar()
        clientes_del = pd.read_sql_query("SELECT id, nome FROM Clientes", conn)
        conn.close()
        
        if not clientes_del.empty:
            # Cria um dicionário "Nome (ID)" -> ID Real
            dict_clientes = {f"{row['nome']} (ID: {row['id']})": row['id'] for index, row in clientes_del.iterrows()}
            cliente_selecionado = st.selectbox("Selecione o Cliente para excluir:", list(dict_clientes.keys()))
            
            if st.button("🗑️ Confirmar Exclusão", type="primary"):
                id_para_excluir = dict_clientes[cliente_selecionado]
                
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Clientes WHERE id = ?", (id_para_excluir,))
                conn.commit()
                conn.close()
                
                st.success("Cliente removido com sucesso!")
                st.rerun()
        else:
            st.info("Nenhum cliente cadastrado para excluir.")

    st.divider()
    st.subheader("Lista de Clientes")
    df = carregar_dados("Clientes")
    st.dataframe(df, hide_index=True, use_container_width=True)

# =================================================================================
# PÁGINA: PRODUTOS (Com Exclusão)
# =================================================================================
elif pagina == "🍰 Produtos":
    st.header("Gerenciar Cardápio")
    
    tab1, tab2 = st.tabs(["➕ Cadastrar", "🗑️ Excluir"])
    
    with tab1:
        with st.form("form_produto"):
            nome = st.text_input("Nome do Bolo")
            preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
            tamanho = st.text_input("Tamanho (ex: M, G, 1kg)")
            submit = st.form_submit_button("Salvar Produto")
            
            if submit and nome:
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Produtos (nome, preco, tamanho) VALUES (?, ?, ?)", (nome, preco, tamanho))
                conn.commit()
                conn.close()
                st.success(f"Produto {nome} cadastrado!")
                st.rerun()
                
    with tab2:
        conn = conectar()
        produtos_del = pd.read_sql_query("SELECT id, nome FROM Produtos", conn)
        conn.close()
        
        if not produtos_del.empty:
            dict_produtos = {f"{row['nome']} (ID: {row['id']})": row['id'] for index, row in produtos_del.iterrows()}
            prod_selecionado = st.selectbox("Selecione o Bolo para excluir:", list(dict_produtos.keys()))
            
            if st.button("🗑️ Confirmar Exclusão do Bolo", type="primary"):
                id_prod_del = dict_produtos[prod_selecionado]
                
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Produtos WHERE id = ?", (id_prod_del,))
                conn.commit()
                conn.close()
                
                st.success("Produto removido do cardápio!")
                st.rerun()
        else:
            st.info("Nenhum produto para excluir.")

    st.divider()
    st.subheader("Cardápio Atual")
    df = carregar_dados("Produtos")
    st.dataframe(df, hide_index=True, use_container_width=True)

# =================================================================================
# PÁGINA: RELATÓRIOS
# =================================================================================
elif pagina == "📊 Relatórios":
    st.header("Histórico de Vendas")
    
    conn = conectar()
    # Usamos LEFT JOIN para garantir que, mesmo se o cliente for excluido, a venda apareça (com nome vazio)
    sql = """
    SELECT 
        Pedidos.id as 'ID',
        Pedidos.data as 'Data',
        Clientes.nome as 'Cliente',
        Pedidos.valor_total as 'Total (R$)'
    FROM Pedidos
    LEFT JOIN Clientes ON Pedidos.id_cliente = Clientes.id
    ORDER BY Pedidos.id DESC
    """
    df_vendas = pd.read_sql_query(sql, conn)
    conn.close()
    
    st.dataframe(df_vendas, hide_index=True, use_container_width=True)
    
    total_vendido = df_vendas['Total (R$)'].sum()
    qtde_vendas = len(df_vendas)
    
    colA, colB = st.columns(2)
    colA.metric("Faturamento Total", f"R$ {total_vendido:.2f}")
    colA.metric("Vendas Realizadas", qtde_vendas)

    st.divider()
    st.header("📊 Dashboard de Vendas")
    
    conn = conectar()
    
    # 1. FILTROS NA BARRA LATERAL
    st.sidebar.header("Filtros")
    dias_filtro = st.sidebar.selectbox("Período:", ["Todo o Histórico", "Últimos 7 dias", "Últimos 30 dias"])
    
    # Query Base (Puxando mais dados para os gráficos)
    sql = """
    SELECT 
        Pedidos.id,
        Pedidos.data,
        Clientes.nome as 'Cliente',
        Produtos.nome as 'Produto',
        Pedidos_Itens.quantidade,
        Pedidos_Itens.total as 'Valor_Total'
    FROM Pedidos_Itens
    JOIN Pedidos ON Pedidos_Itens.id_pedido = Pedidos.id
    LEFT JOIN Clientes ON Pedidos.id_cliente = Clientes.id
    JOIN Produtos ON Pedidos_Itens.id_produto = Produtos.id
    ORDER BY Pedidos.data ASC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()

    # Convertendo a coluna 'data' para formato de Data do Pandas (essencial para gráficos)
    df['data'] = pd.to_datetime(df['data'])

    # Aplicando o Filtro de Data (Lógica Python)
    if dias_filtro == "Últimos 7 dias":
        data_corte = datetime.now() - pd.Timedelta(days=7)
        df = df[df['data'] >= data_corte]
    elif dias_filtro == "Últimos 30 dias":
        data_corte = datetime.now() - pd.Timedelta(days=30)
        df = df[df['data'] >= data_corte]

    # SE TIVER DADOS, MOSTRA O DASHBOARD
    if not df.empty:
        # --- 2. INDICADORES (KPIs) ---
        total_faturamento = df['Valor_Total'].sum()
        total_vendas = df['id'].nunique() # Conta pedidos únicos
        ticket_medio = total_faturamento / total_vendas if total_vendas > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Faturamento", f"R$ {total_faturamento:.2f}")
        col2.metric("📦 Vendas Realizadas", total_vendas)
        col3.metric("📈 Ticket Médio", f"R$ {ticket_medio:.2f}", help="Média de quanto cada cliente gasta")
        
        st.divider()

        # --- 3. GRÁFICOS LADO A LADO ---
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("🏆 Bolos Mais Vendidos")
            # Agrupa por nome do produto e soma a quantidade
            df_produtos = df.groupby("Produto")["quantidade"].sum().reset_index()
            # Cria gráfico de barras
            fig_prod = px.bar(df_produtos, x="quantidade", y="Produto", orientation='h', 
                              text="quantidade", color="quantidade", 
                              color_continuous_scale='Blues')
            st.plotly_chart(fig_prod, use_container_width=True)
            
        with col_graf2:
            st.subheader("📅 Faturamento por Dia")
            # Cria uma coluna só com a Data (sem hora) para agrupar
            df['Data_Dia'] = df['data'].dt.date
            df_faturamento = df.groupby("Data_Dia")["Valor_Total"].sum().reset_index()
            # Cria gráfico de linha
            fig_fat = px.line(df_faturamento, x="Data_Dia", y="Valor_Total", markers=True)
            fig_fat.update_layout(xaxis_title="Data", yaxis_title="Valor (R$)")
            st.plotly_chart(fig_fat, use_container_width=True)

        st.divider()
        st.subheader("Detalhes das Vendas")
        st.dataframe(df, hide_index=True, use_container_width=True)
        
    else:
        st.warning("Nenhum dado encontrado para o período selecionado.")