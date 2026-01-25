import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema de Bolos (Nuvem)", page_icon="🎂", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
def get_data(worksheet_name):
    # O ttl=0 garante que ele não use cache antigo, sempre pegue dados frescos
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet=worksheet_name, ttl=0)

def save_data(df, worksheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=worksheet_name, data=df)

# --- FUNÇÃO PARA GERAR ID ---
def gerar_novo_id(df):
    if df.empty:
        return 1
    return df['id'].max() + 1

# --- INTERFACE ---
st.sidebar.title("🎂 Menu Nuvem")
pagina = st.sidebar.radio("Ir para:", ["🛒 Nova Venda", "👥 Clientes", "🍰 Produtos", "📊 Relatórios"])

# =================================================================================
# PÁGINA: NOVA VENDA
# =================================================================================
if pagina == "🛒 Nova Venda":
    st.header("🛒 Registrar Venda (Google Sheets)")
    
    if 'carrinho' not in st.session_state:
        st.session_state['carrinho'] = []

    # Carrega dados
    try:
        df_clientes = get_data("Clientes")
        df_produtos = get_data("Produtos")
    except Exception as e:
        st.error("Erro ao conectar na planilha. Verifique os Secrets.")
        st.stop()

    if df_clientes.empty:
        st.warning("Cadastre clientes primeiro!")
    else:
        # Seleção de Cliente
        lista_clientes = df_clientes['nome'].tolist()
        nome_cliente = st.selectbox("Cliente:", lista_clientes)
        # Pega o ID do cliente selecionado
        id_cliente = df_clientes[df_clientes['nome'] == nome_cliente]['id'].values[0]

        st.divider()

        # Seleção de Produto
        opcoes_produtos = {f"{row['nome']} (R$ {row['preco']:.2f})": row for index, row in df_produtos.iterrows()}
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            prod_key = st.selectbox("Produto:", list(opcoes_produtos.keys()))
            dados_prod = opcoes_produtos[prod_key]
        with col2:
            qtd = st.number_input("Qtd:", 1, 100, 1)
        with col3:
            st.write("")
            st.write("")
            if st.button("➕ Add"):
                item = {
                    "id_produto": dados_prod['id'],
                    "nome": dados_prod['nome'],
                    "preco": dados_prod['preco'],
                    "quantidade": qtd,
                    "total": dados_prod['preco'] * qtd
                }
                st.session_state['carrinho'].append(item)
                st.success("Adicionado!")

        # Carrinho
        if st.session_state['carrinho']:
            df_cart = pd.DataFrame(st.session_state['carrinho'])
            st.dataframe(df_cart[['nome', 'quantidade', 'total']], hide_index=True)
            total = df_cart['total'].sum()
            st.write(f"### Total: R$ {total:.2f}")

            if st.button("✅ FINALIZAR VENDA", type="primary"):
                # 1. Salvar Pedido
                df_pedidos = get_data("Pedidos")
                novo_id_pedido = gerar_novo_id(df_pedidos)
                
                novo_pedido = pd.DataFrame([{
                    "id": novo_id_pedido,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "id_cliente": id_cliente,
                    "valor_total": total
                }])
                df_pedidos = pd.concat([df_pedidos, novo_pedido], ignore_index=True)
                save_data(df_pedidos, "Pedidos")

                # 2. Salvar Itens
                df_itens = get_data("Pedidos_Itens")
                lista_itens_salvar = []
                for item in st.session_state['carrinho']:
                    lista_itens_salvar.append({
                        "id_pedido": novo_id_pedido,
                        "id_produto": item['id_produto'],
                        "valor_unitario": item['preco'],
                        "quantidade": item['quantidade'],
                        "total": item['total']
                    })
                
                df_novos_itens = pd.DataFrame(lista_itens_salvar)
                df_itens = pd.concat([df_itens, df_novos_itens], ignore_index=True)
                save_data(df_itens, "Pedidos_Itens")

                st.session_state['carrinho'] = []
                st.balloons()
                st.success("Venda salva no Google Sheets!")
                st.rerun()

# =================================================================================
# PÁGINA: CLIENTES
# =================================================================================
elif pagina == "👥 Clientes":
    st.header("Clientes")
    
    with st.form("novo_cliente"):
        nome = st.text_input("Nome")
        tel = st.text_input("Telefone")
        end = st.text_input("Endereço")
        if st.form_submit_button("Salvar"):
            df = get_data("Clientes")
            novo_id = gerar_novo_id(df)
            novo_cliente = pd.DataFrame([{"id": novo_id, "nome": nome, "telefone": tel, "endereco": end}])
            df = pd.concat([df, novo_cliente], ignore_index=True)
            save_data(df, "Clientes")
            st.success("Cliente Salvo!")
            st.rerun()
            
    st.dataframe(get_data("Clientes"), hide_index=True)

# =================================================================================
# PÁGINA: PRODUTOS
# =================================================================================
elif pagina == "🍰 Produtos":
    st.header("Produtos")
    
    with st.form("novo_prod"):
        nome = st.text_input("Nome")
        preco = st.number_input("Preço", 0.0)
        tamanho = st.text_input("Tamanho")
        if st.form_submit_button("Salvar"):
            df = get_data("Produtos")
            novo_id = gerar_novo_id(df)
            novo_prod = pd.DataFrame([{"id": novo_id, "nome": nome, "preco": preco, "tamanho": tamanho}])
            df = pd.concat([df, novo_prod], ignore_index=True)
            save_data(df, "Produtos")
            st.success("Produto Salvo!")
            st.rerun()
            
    st.dataframe(get_data("Produtos"), hide_index=True)

# =================================================================================
# PÁGINA: RELATÓRIOS
# =================================================================================
elif pagina == "📊 Relatórios":
    st.header("Dashboard")
    
    # Carregando tudo
    df_pedidos = get_data("Pedidos")
    df_clientes = get_data("Clientes")
    
    if not df_pedidos.empty:
        # Merge (Substituto do JOIN do SQL)
        df_completo = pd.merge(df_pedidos, df_clientes, left_on="id_cliente", right_on="id", how="left")
        
        st.metric("Faturamento Total", f"R$ {df_completo['valor_total'].sum():.2f}")
        st.dataframe(df_completo[['id_x', 'data', 'nome', 'valor_total']].rename(columns={'id_x': 'Pedido', 'nome': 'Cliente'}))
    else:
        st.info("Nenhuma venda ainda.")